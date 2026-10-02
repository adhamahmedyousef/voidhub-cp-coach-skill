import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_progress_store import assignment, outcome
from progress_store import (
    CURRICULUM,
    LEGACY_TOPICS,
    TOPICS,
    ProgressStore,
    StoreError,
    compute_mastery,
)


def decision(stage=1, action="advance", target="implementation", target_stage=2):
    return {
        "topic": "implementation",
        "stage": stage,
        "action": action,
        "target_topic": target,
        "target_stage": target_stage,
        "checks": {
            name: True
            for name in ("understanding", "complexity", "coverage", "prerequisites")
        },
        "reason": "Learner explained the invariant, cost and edge cases without help.",
    }


def resource():
    return {
        "topic": "binary_search",
        "title": "SYNTHETIC video fixture",
        "channel": "TEST FIXTURE",
        "url": "https://www.youtube.com/watch?v=00000000000",
        "language": "Arabic",
        "level": "beginner",
        "purpose": "Synthetic metadata for a storage test; not a real recommendation.",
        "verification": "metadata",
        "verified_at": "2026-10-02",
        "status": "suggested",
        "duration_seconds": None,
        "start_seconds": None,
    }


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProgressStore(self.tmp.name)
        self.store.init()

    def tearDown(self):
        self.tmp.cleanup()

    def successes(self, stage=1):
        for i in range(3):
            self.store.assign(assignment(f"{stage * 10 + i:032x}", stage=stage))
            self.store.record(outcome(transfer=i == 2))

    def legacy(self):
        self.store.assign(assignment())
        self.store.hint("observation")
        state = self.store.read()
        state.pop("learning")
        state["schema_version"] = 1
        state["mastery"] = compute_mastery(state["problems"], LEGACY_TOPICS)
        self.store.path.write_text(json.dumps(state), encoding="utf-8")
        return state

    def test_legacy_history_upgrades_with_backup_and_keeps_active_assistance(self):
        old = self.legacy()
        before = self.store.path.read_bytes()
        self.assertEqual(self.store.resume()["schema_version"], 1)
        self.assertEqual(self.store.path.read_bytes(), before)
        state = self.store.upgrade()
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["problems"], old["problems"])
        self.assertEqual(state["current_problem"], old["current_problem"])
        self.assertEqual(state["current_problem"]["assistance"], "observation")
        self.assertEqual(
            json.loads(
                (self.store.directory / "progress.v1.backup.json").read_text(
                    encoding="utf-8"
                )
            ),
            old,
        )
        self.assertEqual(state["mastery"]["digit_dp"]["completed_stage"], 0)

    def test_failed_upgrade_leaves_original_and_backup_intact(self):
        old = self.legacy()
        before = self.store.path.read_bytes()
        real_atomic = __import__("progress_store").atomic_json

        def fail_final(path, value):
            if Path(path) == self.store.path:
                raise OSError("fixture interruption after backup")
            return real_atomic(path, value)

        with patch("progress_store.atomic_json", side_effect=fail_final):
            with self.assertRaises(OSError):
                self.store.upgrade()
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(
            json.loads(
                (self.store.directory / "progress.v1.backup.json").read_text(
                    encoding="utf-8"
                )
            ),
            old,
        )
        self.store.upgrade()
        self.assertEqual(self.store.read()["schema_version"], 2)

    def test_backup_conflict_blocks_upgrade(self):
        self.legacy()
        before = self.store.path.read_bytes()
        (self.store.directory / "progress.v1.backup.json").write_text("{}")
        with self.assertRaises(StoreError):
            self.store.upgrade()
        self.assertEqual(self.store.path.read_bytes(), before)

    def test_video_status_is_saved_without_awarding_mastery(self):
        before = self.store.read()["mastery"]
        video = resource()
        self.store.resource(video)
        video["status"] = "watched"
        self.store.resource(video)
        state = self.store.read()
        self.assertEqual(len(state["learning"]["resources"]), 1)
        self.assertEqual(state["learning"]["resources"][0]["status"], "watched")
        self.assertEqual(state["mastery"], before)
        self.assertEqual(state["problems"], {})
        self.assertEqual(
            self.store.resume()["recent_resources"][0]["verification"], "metadata"
        )

    def test_invalid_video_link_or_timestamp_preserves_state(self):
        before = self.store.path.read_bytes()
        for field, value in (
            ("url", "https://evil.example/watch?v=00000000000"),
            ("verification", "watched_entire_video"),
            ("verified_at", "not-a-date"),
            ("start_seconds", -1),
        ):
            payload = resource()
            payload[field] = value
            with self.assertRaises(StoreError):
                self.store.resource(payload)
            self.assertEqual(self.store.path.read_bytes(), before)

    def test_advance_requires_independent_evidence_and_all_understanding_checks(self):
        before = self.store.path.read_bytes()
        with self.assertRaises(StoreError):
            self.store.decision(decision())
        self.assertEqual(self.store.path.read_bytes(), before)
        self.successes()
        payload = decision()
        payload["checks"]["understanding"] = False
        with self.assertRaises(StoreError):
            self.store.decision(payload)
        state = self.store.decision(decision())
        recorded = state["learning"]["decisions"][-1]
        self.assertEqual(len(recorded["independent_ids"]), 3)
        self.assertEqual(len(recorded["transfer_ids"]), 1)
        self.assertIn("stage 2", state["next_step"])

    def test_advance_blocks_stage_skips_new_topics_and_unfinished_work(self):
        self.successes()
        for payload in (
            decision(target_stage=3),
            decision(target="arrays_strings", target_stage=1),
        ):
            with self.assertRaises(StoreError):
                self.store.decision(payload)
        self.store.assign(assignment("9" * 32))
        with self.assertRaises(StoreError):
            self.store.decision(decision())

    def test_topic_transition_checks_prerequisites_and_preserves_evidence(self):
        for stage in (1, 2, 3):
            self.successes(stage)
        with self.assertRaises(StoreError):
            self.store.decision(
                decision(stage=3, target="segment_tree", target_stage=1)
            )
        state = self.store.decision(
            decision(stage=3, target="arrays_strings", target_stage=1)
        )
        self.assertEqual(state["mastery"]["implementation"]["completed_stage"], 3)
        self.assertEqual(
            self.store.resume()["latest_decision"][0]["decision"]["target_topic"],
            "arrays_strings",
        )

    def test_continue_and_prerequisite_review_are_explicit(self):
        self.store.decision(decision(action="continue", target_stage=1))
        payload = decision(
            action="review_prerequisite", target="sorting_frequency", target_stage=1
        )
        payload["topic"] = "binary_search"
        self.store.decision(payload)
        self.assertIn("review_prerequisite", self.store.resume()["next_step"])

    def test_advanced_topic_assignment_keeps_its_own_mastery(self):
        payload = assignment()
        payload["topic"] = "digit_dp"
        self.store.assign(payload)
        self.store.record(outcome())
        state = self.store.read()
        self.assertEqual(
            len(state["mastery"]["digit_dp"]["stages"]["1"]["independent_ids"]), 1
        )
        self.assertEqual(state["mastery"]["dp"]["stages"]["1"]["independent_ids"], [])

    def test_catalog_dependencies_are_acyclic_and_legacy_ids_remain(self):
        self.assertEqual(len(TOPICS), 38)
        self.assertTrue(set(LEGACY_TOPICS) <= set(TOPICS))
        done, visiting = set(), set()

        def visit(topic):
            self.assertNotIn(topic, visiting)
            if topic in done:
                return
            visiting.add(topic)
            for parent in CURRICULUM[topic]["prerequisites"]:
                self.assertIn(parent, TOPICS)
                visit(parent)
            visiting.remove(topic)
            done.add(topic)

        for topic in TOPICS:
            visit(topic)


if __name__ == "__main__":
    unittest.main()
