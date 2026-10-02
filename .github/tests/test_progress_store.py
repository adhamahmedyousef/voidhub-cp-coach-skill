from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_archive_client import summary
from progress_store import ProgressStore, SKILL_DIR, StoreError
import progress_store


def assignment(pid="1" * 32, mode="topic", stage=1):
    return {
        "problem": summary(pid),
        "topic": "implementation",
        "stage": stage,
        "mode": mode,
    }


def outcome(assistance="none", transfer=True, result="accepted_reported", review=None):
    return {
        "session_id": "fixture-session",
        "result": result,
        "assistance": assistance,
        "failure": None,
        "transfer": transfer,
        "evidence": "Learner reports acceptance; no submission integration.",
        "revisit_on": review,
    }


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProgressStore(self.tmp.name)
        self.store.init()

    def tearDown(self):
        self.tmp.cleanup()

    def test_formatted_state_size_limit_preserves_readable_history(self):
        before = self.store.path.read_bytes()
        limit = len(before) + 50
        with patch.object(progress_store, "MAX_STATE_BYTES", limit):
            with self.assertRaisesRegex(StoreError, "size limit"):
                self.store.set_next("A concrete next action. " * 30)
            self.assertEqual(self.store.path.read_bytes(), before)
            self.assertEqual(self.store.read()["revision"], 0)

    def test_resume_is_bounded_without_discarding_history_or_evidence(self):
        for i in range(12):
            self.store.assign(assignment(f"{i:032x}"))
            attempt = outcome(assistance="observation", review="2026-10-08")
            attempt["evidence"] = "Checked observation. " * 80
            self.store.record(attempt)
        before = self.store.path.read_bytes()
        compact = self.store.resume()
        self.assertEqual(
            compact["totals"],
            {
                "seen_problems": 12,
                "attempts": 12,
                "independent_solved": 0,
                "assisted_only_solved": 12,
                "solutions_viewed": 0,
            },
        )
        self.assertEqual(len(compact["recent_attempts"]), 3)
        self.assertEqual(len(compact["scheduled_reviews"]), 10)
        self.assertEqual(compact["scheduled_review_count"], 12)
        self.assertLessEqual(len(compact["recent_attempts"][0]["evidence"]), 600)
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(
            self.store.read()["problems"]["voidhub:" + f"{11:032x}"]["attempts"][0][
                "evidence"
            ],
            attempt["evidence"],
        )

    def test_resume_keeps_active_context_and_resolved_review_disappears(self):
        self.store.assign(assignment())
        self.store.record(outcome(assistance="observation", review="2026-10-08"))
        self.store.assign(assignment(mode="review"))
        active = self.store.resume()["current_problem"]
        self.assertEqual(active["problem"]["id"], "1" * 32)
        self.assertEqual(active["mode"], "review")
        self.store.record(outcome(transfer=False, result="wrong"))
        self.assertEqual(self.store.resume()["scheduled_review_count"], 1)
        self.store.assign(assignment(mode="review"))
        self.store.record(outcome(transfer=False))
        compact = self.store.resume()
        self.assertEqual(compact["scheduled_reviews"], [])
        self.assertEqual(
            compact["mastery"]["implementation"]["stages"]["1"]["independent"], 1
        )

    def test_cli_writes_receipt_and_full_history_remains_available(self):
        output = io.StringIO()
        args = [
            "progress_store.py",
            "next",
            "--data-dir",
            self.tmp.name,
            "--text",
            "Resume diagnosis.",
        ]
        with contextlib.redirect_stdout(output), patch("sys.argv", args):
            progress_store.main()
        receipt = json.loads(output.getvalue())
        self.assertTrue(receipt["saved"])
        self.assertNotIn("problems", receipt)
        self.assertEqual(receipt["next_step"], self.store.read()["next_step"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch("sys.argv", args + ["--full"]):
            progress_store.main()
        self.assertIn("problems", json.loads(output.getvalue()))

    def test_resume_keeps_active_identity_and_assistance(self):
        self.store.assign(assignment())
        self.store.hint("observation")
        resumed = ProgressStore(self.tmp.name).init()
        self.assertEqual(resumed["current_problem"]["key"], "voidhub:" + "1" * 32)
        self.assertEqual(resumed["current_problem"]["assistance"], "observation")

    def test_assistance_cannot_be_downgraded_and_requires_review_date(self):
        self.store.assign(assignment())
        self.store.hint("algorithm")
        self.store.hint("clarification")
        before = self.store.path.read_bytes()
        with self.assertRaises(StoreError):
            self.store.record(outcome())
        self.assertEqual(before, self.store.path.read_bytes())
        data = self.store.record(outcome(review="2026-10-08"))
        attempt = data["problems"]["voidhub:" + "1" * 32]["attempts"][0]
        self.assertEqual(attempt["assistance"], "algorithm")
        self.assertEqual(data["mastery"]["implementation"]["completed_stage"], 0)

    def test_prevent_repeat_and_overwriting_unfinished_problem(self):
        self.store.assign(assignment())
        with self.assertRaises(StoreError):
            self.store.assign(assignment("2" * 32))
        self.store.record(outcome())
        with self.assertRaises(StoreError):
            self.store.assign(assignment())
        self.store.assign(assignment(mode="review"))
        with self.assertRaises(StoreError):
            self.store.record(outcome(transfer=True))
        self.store.record(outcome(transfer=False))

    def test_mastery_needs_three_distinct_unassisted_and_transfer(self):
        for i in range(1, 4):
            self.store.assign(assignment(str(i) * 32))
            self.store.record(outcome(transfer=i == 3))
        self.assertEqual(
            self.store.read()["mastery"]["implementation"]["completed_stage"], 1
        )

    def test_three_successes_without_transfer_do_not_unlock(self):
        for i in range(1, 4):
            self.store.assign(assignment(str(i) * 32))
            self.store.record(outcome(transfer=False))
        self.assertEqual(
            self.store.read()["mastery"]["implementation"]["completed_stage"], 0
        )

    def test_later_stage_cannot_skip_prerequisite_stage(self):
        for i in range(1, 4):
            self.store.assign(assignment(str(i) * 32, stage=2))
            self.store.record(outcome())
        self.assertTrue(
            self.store.read()["mastery"]["implementation"]["stages"]["2"]["eligible"]
        )
        self.assertEqual(
            self.store.read()["mastery"]["implementation"]["completed_stage"], 0
        )

    def test_corrupt_and_unknown_version_preserved(self):
        for raw in ('{"schema_version":99}', "broken json"):
            self.store.path.write_text(raw)
            with self.assertRaises(StoreError):
                self.store.init()
            self.assertEqual(self.store.path.read_text(), raw)

    def test_atomic_failure_leaves_previous_valid_file(self):
        before = self.store.path.read_bytes()
        with patch(
            "archive_client.os.replace",
            side_effect=OSError("fixture power interruption"),
        ):
            with self.assertRaises(OSError):
                self.store.set_next("Next task")
        self.assertEqual(before, self.store.path.read_bytes())
        self.assertFalse(list(Path(self.tmp.name).glob(".coach-*")))

    def test_concurrent_writes_have_no_lost_revision(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(
                pool.map(
                    lambda i: ProgressStore(self.tmp.name).set_next(f"Next task {i}"),
                    range(12),
                )
            )
        self.assertEqual(self.store.read()["revision"], 12)

    def test_corrupt_mastery_cache_is_not_trusted(self):
        data = self.store.read()
        data["mastery"]["implementation"]["completed_stage"] = 3
        self.store.path.write_text(json.dumps(data))
        before = self.store.path.read_bytes()
        with self.assertRaises(StoreError):
            self.store.set_next("Next task")
        self.assertEqual(before, self.store.path.read_bytes())

    def test_data_inside_installed_skill_rejected(self):
        with self.assertRaises(StoreError):
            ProgressStore(SKILL_DIR / "learner")

    def test_profile_plan_updates_do_not_touch_history(self):
        before = self.store.path.read_bytes()
        self.store.write_notes("profile.md", "# Profile\nGoal: ECPC\n")
        self.store.write_notes("plan.md", "# Plan\nTwo focused sessions this week.\n")
        self.assertEqual(before, self.store.path.read_bytes())

    def test_abandonment_is_recorded_and_question_is_still_seen(self):
        self.store.assign(assignment())
        self.store.record(outcome(result="abandoned", transfer=False))
        self.assertIsNone(self.store.read()["current_problem"])
        with self.assertRaises(StoreError):
            self.store.assign(assignment())


if __name__ == "__main__":
    unittest.main()
