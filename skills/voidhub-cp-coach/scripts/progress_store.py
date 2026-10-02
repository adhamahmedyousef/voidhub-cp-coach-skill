"""Validated local coaching state with exclusive writes and atomic replacement."""

import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
import os

from archive_client import ClientError, atomic_json, locked, summary_valid

SKILL_DIR = Path(__file__).resolve().parents[1]
ASSISTANCE = ("none", "clarification", "observation", "algorithm", "full_solution")
RESULTS = (
    "accepted_reported",
    "verified_correct",
    "wrong",
    "timeout",
    "unsolved",
    "abandoned",
)
FAILURES = (
    "statement",
    "recognition",
    "proof",
    "knowledge",
    "complexity",
    "implementation",
    "debugging",
    "time_management",
)
TOPICS = (
    "implementation",
    "arrays_strings",
    "sorting_frequency",
    "math",
    "prefix_sums",
    "two_pointers",
    "binary_search",
    "greedy",
    "backtracking",
    "bfs_dfs",
    "dsu",
    "dijkstra",
    "dp",
)


class StoreError(Exception):
    pass


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise StoreError("Unexpected or missing state fields.")


def text(value, maximum=5000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise StoreError("Expected bounded nonempty text.")


def context(value):
    if (
        not isinstance(value["topic"], str)
        or value["topic"] not in TOPICS
        or type(value["stage"]) is not int
        or value["stage"] not in (1, 2, 3)
    ):
        raise StoreError("Invalid learning topic/stage.")
    if (
        not isinstance(value["mode"], str)
        or not isinstance(value["assistance"], str)
        or value["mode"] not in ("topic", "diagnostic", "mixed", "review")
        or value["assistance"] not in ASSISTANCE
    ):
        raise StoreError("Invalid training mode/assistance.")


def compute_mastery(problems):
    mastery = {}
    for topic in TOPICS:
        stages = {}
        for stage in (1, 2, 3):
            independent, transfer = set(), set()
            for key, problem in problems.items():
                for attempt in problem["attempts"]:
                    if (
                        attempt["topic"] == topic
                        and attempt["stage"] == stage
                        and attempt["assistance"] == "none"
                        and attempt["result"]
                        in ("accepted_reported", "verified_correct")
                    ):
                        independent.add(key)
                        if attempt["transfer"]:
                            transfer.add(key)
            stages[str(stage)] = {
                "independent_ids": sorted(independent),
                "transfer_ids": sorted(transfer),
                "eligible": len(independent) >= 3 and bool(transfer),
            }
        # A later stage cannot skip the evidence required by the earlier one.
        completed = 0
        for stage in (1, 2, 3):
            if not stages[str(stage)]["eligible"]:
                break
            completed = stage
        mastery[topic] = {"completed_stage": completed, "stages": stages}
    return mastery


def validate(state):
    exact(
        state,
        (
            "schema_version",
            "revision",
            "current_problem",
            "problems",
            "mastery",
            "next_step",
        ),
    )
    if type(state["schema_version"]) is not int or state["schema_version"] != 1:
        raise StoreError("Unsupported state version; preserved without migration.")
    if (
        type(state["revision"]) is not int
        or state["revision"] < 0
        or not isinstance(state["problems"], dict)
    ):
        raise StoreError("Invalid revision/problem history.")
    text(state["next_step"])
    for key, problem in state["problems"].items():
        exact(problem, ("metadata", "attempts"))
        try:
            summary_valid(problem["metadata"])
        except ClientError as exc:
            raise StoreError(str(exc)) from None
        if key != "voidhub:" + problem["metadata"]["id"] or not isinstance(
            problem["attempts"], list
        ):
            raise StoreError("Problem identity mismatch.")
        for attempt in problem["attempts"]:
            exact(
                attempt,
                (
                    "recorded_at",
                    "session_id",
                    "result",
                    "assistance",
                    "failure",
                    "topic",
                    "stage",
                    "mode",
                    "transfer",
                    "evidence",
                    "revisit_on",
                ),
            )
            context(attempt)
            if (
                attempt["result"] not in RESULTS
                or attempt["failure"] is not None
                and attempt["failure"] not in FAILURES
                or type(attempt["transfer"]) is not bool
            ):
                raise StoreError("Invalid attempt result/evidence.")
            text(attempt["session_id"], 120)
            text(attempt["evidence"])
            try:
                datetime.fromisoformat(attempt["recorded_at"])
                if attempt["revisit_on"] is not None:
                    date.fromisoformat(attempt["revisit_on"])
            except (TypeError, ValueError):
                raise StoreError("Invalid attempt date.") from None
            if attempt["assistance"] != "none" and attempt["revisit_on"] is None:
                raise StoreError("Assisted attempts need an explicit review date.")
    current = state["current_problem"]
    if current is not None:
        exact(
            current, ("key", "topic", "stage", "mode", "assistance", "first_exposure")
        )
        context(current)
        if (
            current["key"] not in state["problems"]
            or type(current["first_exposure"]) is not bool
        ):
            raise StoreError("Invalid current problem.")
    if state["mastery"] != compute_mastery(state["problems"]):
        raise StoreError("Mastery must match recorded evidence; state preserved.")
    return state


class ProgressStore:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        if self.directory == SKILL_DIR or SKILL_DIR in self.directory.parents:
            raise StoreError("Learner data must be outside the installed skill.")
        if Path(directory).is_symlink():
            raise StoreError("Learner state directory cannot be a symlink.")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "progress.json"

    def read(self):
        if self.path.is_symlink():
            raise StoreError("State file cannot be a symlink.")
        try:
            if self.path.stat().st_size > 8 * 1024 * 1024:
                raise StoreError(
                    "Progress exceeds the v1 size limit; archive history deliberately."
                )
            return validate(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise StoreError(
                "Progress is missing or malformed; preserved for review."
            ) from None

    def init(self):
        with locked(self.directory / ".progress.lock"):
            if self.path.exists():
                return self.read()
            state = {
                "schema_version": 1,
                "revision": 0,
                "current_problem": None,
                "problems": {},
                "mastery": compute_mastery({}),
                "next_step": "Collect learner profile, then start three-problem diagnosis.",
            }
            atomic_json(self.path, validate(state))
            for name, content in (
                (
                    "profile.md",
                    "# Learner profile\n\n## Goal and experience\n\nNot recorded yet.\n\n## Availability and preferences\n\nRecord weekly time, language, timezone and preferred coaching style.\n\n## Self-reported topics\n\nAsk which topics feel comfortable, studied but not practiced, or difficult. Not assessed yet.\n\n## Observed strengths and difficulties\n\nRecord demonstrated ability and recurring gaps with a problem ID/date and assistance context; keep these separate from self-reports.\n",
                ),
                (
                    "plan.md",
                    "# Training plan\n\n## Current focus\n\nComplete onboarding, then diagnose with three real CPC problems, one at a time.\n\n## This week\n\nSet a realistic workload after onboarding.\n\n## Session handoff\n\nNo training session completed yet. Progress JSON owns the active problem and next step.\n",
                ),
            ):
                path = self.directory / name
                if not path.exists():
                    self._markdown(path, content)
            return state

    def resume(self):
        """Return bounded session context without copying the full history."""
        state = self.read()
        recent = []
        reviews = []
        attempt_count = 0
        for key, problem in state["problems"].items():
            attempts = problem["attempts"]
            attempt_count += len(attempts)
            revisit_on = None
            for attempt in attempts:
                if attempt["revisit_on"] is not None:
                    revisit_on = attempt["revisit_on"]
                elif attempt["assistance"] == "none" and attempt["result"] in (
                    "accepted_reported",
                    "verified_correct",
                ):
                    revisit_on = None
                recent.append(
                    {
                        "key": key,
                        "title": problem["metadata"]["title"],
                        "recorded_at": attempt["recorded_at"],
                        "topic": attempt["topic"],
                        "result": attempt["result"],
                        "assistance": attempt["assistance"],
                        "failure": attempt["failure"],
                        "evidence": attempt["evidence"][:600],
                    }
                )
            if revisit_on is not None:
                reviews.append(
                    {
                        "key": key,
                        "title": problem["metadata"]["title"],
                        "revisit_on": revisit_on,
                    }
                )
        recent.sort(key=lambda item: item["recorded_at"], reverse=True)
        reviews.sort(key=lambda item: (item["revisit_on"], item["key"]))
        current = state["current_problem"]
        if current is not None:
            current = {
                **current,
                "problem": state["problems"][current["key"]]["metadata"],
            }
        mastery = {}
        for topic, data in state["mastery"].items():
            if any(stage["independent_ids"] for stage in data["stages"].values()):
                mastery[topic] = {
                    "completed_stage": data["completed_stage"],
                    "stages": {
                        number: {
                            "independent": len(stage["independent_ids"]),
                            "transfer": len(stage["transfer_ids"]),
                            "eligible": stage["eligible"],
                        }
                        for number, stage in data["stages"].items()
                    },
                }
        return {
            "schema_version": state["schema_version"],
            "revision": state["revision"],
            "current_problem": current,
            "next_step": state["next_step"],
            "totals": {
                "seen_problems": len(state["problems"]),
                "attempts": attempt_count,
            },
            "mastery": mastery,
            "recent_attempts": recent[:3],
            "scheduled_reviews": reviews[:10],
            "scheduled_review_count": len(reviews),
            "history_file": str(self.path),
        }

    def _mutate(self, operation):
        with locked(self.directory / ".progress.lock"):
            state = self.read()
            operation(state)
            state["revision"] += 1
            state["mastery"] = compute_mastery(state["problems"])
            validate(state)
            if len(json.dumps(state, ensure_ascii=False).encode()) > 8 * 1024 * 1024:
                raise StoreError(
                    "Progress exceeds the v1 size limit; no history was overwritten."
                )
            atomic_json(self.path, state)
            return state

    def assign(self, payload):
        exact(payload, ("problem", "topic", "stage", "mode"))
        try:
            summary_valid(payload["problem"])
        except ClientError as exc:
            raise StoreError(str(exc)) from None

        def change(state):
            key = "voidhub:" + payload["problem"]["id"]
            if state["current_problem"] is not None:
                raise StoreError(
                    "Resume or record the current attempt before assigning another problem."
                )
            first = key not in state["problems"]
            if not first and payload["mode"] != "review":
                raise StoreError(
                    "Problem already seen. Use explicit review mode for an intentional repeat."
                )
            current = {
                "key": key,
                "topic": payload["topic"],
                "stage": payload["stage"],
                "mode": payload["mode"],
                "assistance": "none",
                "first_exposure": first,
            }
            context(current)
            state["problems"].setdefault(
                key, {"metadata": payload["problem"], "attempts": []}
            )
            state["current_problem"] = current
            state["next_step"] = (
                "Attempt the current problem; do not reveal unsolicited hints."
            )

        return self._mutate(change)

    def hint(self, level):
        if level not in ASSISTANCE[1:]:
            raise StoreError("Invalid assistance level.")

        def change(state):
            current = state["current_problem"]
            if current is None:
                raise StoreError("No current problem.")
            if ASSISTANCE.index(level) > ASSISTANCE.index(current["assistance"]):
                current["assistance"] = level

        return self._mutate(change)

    def record(self, payload):
        exact(
            payload,
            (
                "session_id",
                "result",
                "assistance",
                "failure",
                "transfer",
                "evidence",
                "revisit_on",
            ),
        )
        if payload["assistance"] not in ASSISTANCE:
            raise StoreError("Invalid assistance level.")

        def change(state):
            current = state["current_problem"]
            if current is None:
                raise StoreError("No current attempt to record.")
            if payload["transfer"] and not current["first_exposure"]:
                raise StoreError("A repeated question is not an unseen transfer task.")
            level = max(
                (current["assistance"], payload["assistance"]), key=ASSISTANCE.index
            )
            attempt = {
                **payload,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "assistance": level,
                "topic": current["topic"],
                "stage": current["stage"],
                "mode": current["mode"],
            }
            state["problems"][current["key"]]["attempts"].append(attempt)
            state["current_problem"] = None
            state["next_step"] = (
                "Review recorded evidence and select the next unseen task or scheduled review."
            )

        return self._mutate(change)

    def set_next(self, value):
        text(value)
        return self._mutate(lambda state: state.update(next_step=value))

    @staticmethod
    def _markdown(path, content):
        text(content, 30000)
        if path.is_symlink():
            raise StoreError("Markdown target cannot be a symlink.")
        fd, temporary = tempfile.mkstemp(prefix=".coach-", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def write_notes(self, name, content):
        if name not in ("profile.md", "plan.md"):
            raise StoreError("Only profile.md and plan.md can be updated.")
        with locked(self.directory / ".progress.lock"):
            self.read()
            self._markdown(self.directory / name, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=(
            "init",
            "resume",
            "show",
            "assign",
            "hint",
            "record",
            "next",
            "profile",
            "plan",
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print full state after a write; show always prints full state",
    )
    parser.add_argument("--data-dir", default="voidhub-coach-data")
    parser.add_argument(
        "--input", help="JSON input for assign/record, Markdown for profile/plan"
    )
    parser.add_argument("--level", choices=ASSISTANCE[1:])
    parser.add_argument("--text")
    args = parser.parse_args()
    try:
        store = ProgressStore(args.data_dir)
        if args.operation in ("assign", "record", "profile", "plan"):
            if not args.input:
                raise StoreError("--input is required.")
            raw = Path(args.input).read_text(encoding="utf-8")
            result = (
                getattr(store, args.operation)(json.loads(raw))
                if args.operation in ("assign", "record")
                else store.write_notes(args.operation + ".md", raw)
            )
        elif args.operation == "hint":
            result = store.hint(args.level)
        elif args.operation == "next":
            result = store.set_next(args.text)
        elif args.operation == "resume":
            result = store.resume()
        else:
            result = store.init() if args.operation == "init" else store.read()
        if (
            isinstance(result, dict)
            and args.operation not in ("show", "resume")
            and not args.full
        ):
            result = {
                "saved": True,
                "revision": result["revision"],
                "current_problem": result["current_problem"],
                "next_step": result["next_step"],
            }
        print(
            json.dumps(
                result if result is not None else {"saved": True},
                ensure_ascii=False,
                indent=2,
            )
        )
    except (StoreError, ClientError, OSError, ValueError) as exc:
        parser.exit(1, "State operation failed: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
