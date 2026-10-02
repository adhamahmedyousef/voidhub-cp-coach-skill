"""Executable session-state rehearsals; not a model-quality evaluation."""

from pathlib import Path
import tempfile
import unittest

from test_archive_client import (
    ArchiveClient,
    ClientError,
    Clock,
    Opener,
    Reply,
    statement,
    summary,
)
from test_progress_store import assignment, outcome
from progress_store import ProgressStore, StoreError


class SessionScenarios(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProgressStore(self.tmp.name)
        self.store.init()

    def tearDown(self):
        self.tmp.cleanup()

    def test_beginner_profile_three_diagnoses_recorded_one_at_a_time(self):
        self.store.write_notes(
            "profile.md",
            "# Profile\nGoal: ECPC. Beginner. Four hours/week. Egyptian Arabic.\n",
        )
        for i in range(1, 4):
            self.store.assign(assignment(str(i) * 32, mode="diagnostic"))
            self.store.record(
                outcome(
                    transfer=False, result="unsolved" if i == 3 else "accepted_reported"
                )
            )
        state = ProgressStore(self.tmp.name).read()
        self.assertEqual(sum(len(p["attempts"]) for p in state["problems"].values()), 3)
        self.assertEqual(state["mastery"]["implementation"]["completed_stage"], 0)

    def test_intermediate_mixed_practice_preserves_internal_context(self):
        task = assignment(mode="mixed", stage=2)
        task["topic"] = "binary_search"
        self.store.assign(task)
        state = self.store.record(outcome())
        recorded = next(iter(state["problems"].values()))["attempts"][0]
        self.assertEqual(
            (recorded["mode"], recorded["topic"]), ("mixed", "binary_search")
        )

    def test_hint_then_wrong_attempt_then_resume_revisit(self):
        self.store.assign(assignment())
        self.store.hint("observation")
        resumed = ProgressStore(self.tmp.name)
        attempt = outcome(review="2026-10-08", result="wrong", transfer=False)
        attempt.update(
            failure="proof", evidence="Counterexample demonstrated; no judge claim."
        )
        resumed.record(attempt)
        resumed.assign(assignment(mode="review"))
        self.assertFalse(resumed.read()["current_problem"]["first_exposure"])

    def test_explicit_full_solution_never_counts_as_independent(self):
        self.store.assign(assignment())
        self.store.hint("full_solution")
        viewed = outcome(review="2026-10-08", result="solution_viewed", transfer=False)
        viewed["evidence"] = (
            "Complete solution delivered; no independent learner attempt."
        )
        state = self.store.record(viewed)
        self.assertEqual(
            state["mastery"]["implementation"]["stages"]["1"]["independent_ids"], []
        )
        attempt = next(iter(state["problems"].values()))["attempts"][0]
        self.assertEqual(attempt["result"], "solution_viewed")
        self.assertEqual(attempt["assistance"], "full_solution")
        self.store.assign(assignment(mode="review"))
        self.assertFalse(self.store.read()["current_problem"]["first_exposure"])
        state = self.store.record(outcome(transfer=False))
        self.assertEqual(len(next(iter(state["problems"].values()))["attempts"]), 2)
        self.assertEqual(
            state["mastery"]["implementation"]["stages"]["1"]["transfer_ids"], []
        )

    def test_full_solution_cannot_be_recorded_as_a_solve(self):
        self.store.assign(assignment())
        self.store.hint("full_solution")
        before = self.store.read()
        for result in ("accepted_reported", "verified_correct"):
            with self.assertRaises(StoreError):
                self.store.record(
                    outcome(result=result, transfer=False, review="2026-10-08")
                )
            self.assertEqual(self.store.read(), before)

    def test_solution_viewing_requires_actual_help_and_no_transfer(self):
        self.store.assign(assignment())
        with self.assertRaises(StoreError):
            self.store.record(outcome(result="solution_viewed", transfer=False))
        self.store.hint("full_solution")
        with self.assertRaises(StoreError):
            self.store.record(
                outcome(result="solution_viewed", transfer=True, review="2026-10-08")
            )

    def test_api_unavailable_saves_pending_next_step_without_fake_assignment(self):
        with self.assertRaises(ClientError):
            ArchiveClient(Path(self.tmp.name) / ".client", token="")
        self.store.set_next(
            "API access pending. Complete onboarding, then diagnose with real CPC questions."
        )
        self.assertEqual(self.store.read()["problems"], {})
        self.assertIsNone(self.store.read()["current_problem"])

    def test_read_client_to_assignment_to_persistent_reported_result(self):
        clock = Clock()
        fake = Opener([Reply(statement(), "problem")])
        client = ArchiveClient(
            Path(self.tmp.name) / ".client",
            "fixture_" + "x" * 40,
            fake,
            clock.time,
            clock.sleep,
        )
        problem = client.call("problem", {"id": "1" * 32})["problem"]
        metadata = {k: problem[k] for k in summary()}
        self.store.assign(
            {
                "problem": metadata,
                "topic": "implementation",
                "stage": 1,
                "mode": "topic",
            }
        )
        self.store.record(outcome())
        history = ProgressStore(self.tmp.name).read()["problems"]["voidhub:" + "1" * 32]
        self.assertEqual(
            history["metadata"]["contest"]["name"], "TEST FIXTURE — not a real CPC"
        )
        self.assertEqual(history["attempts"][0]["result"], "accepted_reported")


if __name__ == "__main__":
    unittest.main()
