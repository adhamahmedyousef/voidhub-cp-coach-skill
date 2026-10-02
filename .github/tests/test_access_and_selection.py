import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_archive_client import (
    ArchiveClient,
    ClientError,
    Clock,
    Opener,
    Reply,
    TOKEN,
    summary,
)
from test_progress_store import ProgressStore, assignment, outcome
import archive_client
import setup_access


class AccessAndSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def private_key(self, value=TOKEN):
        path = self.directory / "trial.token"
        path.write_text(value, encoding="ascii")
        path.chmod(0o600)
        return path

    def test_saved_key_loads_in_a_new_process_environment(self):
        self.private_key()
        with patch.dict(os.environ, {}, clear=True), patch.object(
            setup_access, "credential_directory", return_value=self.directory
        ):
            client = ArchiveClient(self.directory / "client")
        self.assertEqual(client.token, TOKEN)
        self.assertNotIn(TOKEN, client.bucket)

    def test_environment_overrides_saved_key_and_invalid_override_does_not_fall_back(
        self,
    ):
        self.private_key()
        with patch.object(
            setup_access, "credential_directory", return_value=self.directory
        ):
            with patch.dict(os.environ, {"VOIDHUB_COACH_API_KEY": "z" * 40}):
                self.assertEqual(
                    ArchiveClient(self.directory / "client").token, "z" * 40
                )
            with patch.dict(os.environ, {"VOIDHUB_COACH_API_KEY": ""}):
                with self.assertRaises(ClientError):
                    ArchiveClient(self.directory / "client")

    def test_bad_or_oversized_local_key_is_not_disclosed(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            setup_access, "credential_directory", return_value=self.directory
        ):
            for value in ("secret fixture!", TOKEN + " " * 300):
                self.private_key(value)
                with self.assertRaises(ClientError) as raised:
                    ArchiveClient(self.directory / "client")
                self.assertNotIn(value.strip(), str(raised.exception))

    @unittest.skipIf(os.name == "nt", "POSIX mode enforcement; Windows setup uses ACLs")
    def test_public_or_symlinked_local_key_is_rejected(self):
        path = self.private_key()
        with patch.object(
            setup_access, "credential_directory", return_value=self.directory
        ):
            path.chmod(0o644)
            with self.assertRaises(RuntimeError):
                setup_access.read_credential()
            path.chmod(0o600)
            alternate = self.directory / "actual.private"
            path.rename(alternate)
            path.symlink_to(alternate)
            with self.assertRaises(RuntimeError):
                setup_access.read_credential()

    def test_candidates_cli_skips_seen_problems_and_saves_public_output(self):
        learner = self.directory / "learner"
        store = ProgressStore(learner)
        store.init()
        store.assign(assignment())
        store.record(outcome(transfer=False))
        clock = Clock()
        opener = Opener(
            [
                Reply(
                    {"api_version": 1, "items": [summary()], "next_cursor": "1" * 32}
                ),
                Reply(
                    {
                        "api_version": 1,
                        "items": [summary("2" * 32)],
                        "next_cursor": None,
                    }
                ),
            ]
        )
        client = ArchiveClient(
            learner / ".client", TOKEN, opener, clock.time, clock.sleep
        )
        output = learner / "candidates.json"
        with patch.object(archive_client, "ArchiveClient", return_value=client), patch(
            "sys.argv",
            [
                "archive_client.py",
                "candidates",
                "--state-dir",
                str(learner),
                "--output",
                str(output),
            ],
        ):
            archive_client.main()
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual([p["id"] for p in data["items"]], ["2" * 32])
        self.assertEqual(json.loads(opener.calls[1].data)["after"], "1" * 32)
        self.assertNotIn(TOKEN, output.read_text(encoding="utf-8"))

    def test_active_problem_or_corrupt_history_blocks_selection_before_network(self):
        learner = self.directory / "learner"
        store = ProgressStore(learner)
        store.init()
        store.assign(assignment())
        for corrupt in (False, True):
            if corrupt:
                store.path.write_text("broken fixture", encoding="utf-8")
            before = store.path.read_bytes()
            with patch.object(archive_client, "ArchiveClient") as client, patch(
                "sys.argv",
                ["archive_client.py", "candidates", "--state-dir", str(learner)],
            ), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    archive_client.main()
                client.assert_not_called()
            self.assertEqual(store.path.read_bytes(), before)

    def test_exhausted_selection_reports_a_gap_without_creating_a_problem(self):
        store = ProgressStore(self.directory / "learner")
        store.init()
        with patch.object(archive_client, "ArchiveClient") as client, patch(
            "sys.argv",
            ["archive_client.py", "candidates", "--state-dir", str(store.directory)],
        ), contextlib.redirect_stderr(io.StringIO()) as error:
            client.return_value.candidates.return_value = []
            with self.assertRaises(SystemExit):
                archive_client.main()
            self.assertIn("No unseen candidate", error.getvalue())
        self.assertEqual(store.read()["problems"], {})

    def test_progress_totals_separate_viewing_assistance_and_independent_resolve(self):
        store = ProgressStore(self.directory / "learner")
        store.init()
        store.assign(assignment())
        store.hint("full_solution")
        store.record(
            outcome(result="solution_viewed", transfer=False, review="2026-10-08")
        )
        totals = store.resume()["totals"]
        self.assertEqual(
            (
                totals["independent_solved"],
                totals["assisted_only_solved"],
                totals["solutions_viewed"],
            ),
            (0, 0, 1),
        )
        store.assign(assignment("2" * 32))
        store.record(
            outcome(assistance="observation", transfer=False, review="2026-10-08")
        )
        store.assign(assignment("2" * 32, mode="review"))
        store.record(outcome(transfer=False))
        totals = store.resume()["totals"]
        self.assertEqual(
            (
                totals["independent_solved"],
                totals["assisted_only_solved"],
                totals["solutions_viewed"],
            ),
            (1, 0, 1),
        )

    def test_unwritable_output_exits_cleanly_without_disclosing_response(self):
        with patch.object(archive_client, "ArchiveClient") as client, patch(
            "sys.argv",
            [
                "archive_client.py",
                "search",
                "--state-dir",
                str(self.directory),
                "--output",
                str(self.directory),
            ],
        ), contextlib.redirect_stderr(io.StringIO()) as error:
            client.return_value.call.return_value = {
                "api_version": 1,
                "items": [summary()],
                "next_cursor": None,
            }
            with self.assertRaises(SystemExit) as raised:
                archive_client.main()
            self.assertEqual(raised.exception.code, 1)
            self.assertIn("local path and permissions", error.getvalue())
            self.assertNotIn(TOKEN, error.getvalue())


if __name__ == "__main__":
    unittest.main()
