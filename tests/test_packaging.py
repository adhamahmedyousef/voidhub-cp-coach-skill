import contextlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_archive_client import SCRIPTS
import setup_access

ROOT = SCRIPTS.parents[2]
SKILL = SCRIPTS.parent


class PackagingTests(unittest.TestCase):
    def test_required_frontmatter_references_and_no_unfinished_scaffold(self):
        entry = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(entry.startswith("---\nname: voidhub-cp-coach\n"))
        self.assertIn("description:", entry)
        for document in [ROOT / "README.md", *SKILL.rglob("*.md")]:
            for relative in re.findall(
                r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")
            ):
                if "://" not in relative and not relative.startswith("#"):
                    target = document.parent / relative.split("#", 1)[0]
                    self.assertTrue(target.exists(), f"{document.name}: {relative}")
        for path in SKILL.rglob("*.md"):
            self.assertNotIn("[TODO:", path.read_text(encoding="utf-8"))
        schema = json.loads((SKILL / "progress.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema_version"]["const"], 2)

    def test_installed_copy_starts_and_resumes_outside_a_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            installed = base / "installed" / "voidhub-cp-coach"
            shutil.copytree(
                SKILL, installed, ignore=shutil.ignore_patterns("__pycache__")
            )
            workspace = base / "training"
            workspace.mkdir()
            command = [
                sys.executable,
                "-B",
                str(installed / "scripts" / "progress_store.py"),
            ]
            subprocess.run(
                command + ["init"], cwd=workspace, check=True, capture_output=True
            )
            data = workspace / "voidhub-coach-data"
            (data / "profile.md").write_text(
                "# Profile\nProgramming language: Python (requested).\n",
                encoding="utf-8",
            )
            before = (data / "progress.json").read_bytes()
            result = subprocess.run(
                command + ["resume"],
                cwd=workspace,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(result.stdout)["totals"]["attempts"], 0)
            subprocess.run(
                command + ["init"], cwd=workspace, check=True, capture_output=True
            )
            self.assertIn("Python", (data / "profile.md").read_text(encoding="utf-8"))
            self.assertEqual(before, (data / "progress.json").read_bytes())
            self.assertFalse((installed / "voidhub-coach-data").exists())

    def test_provision_never_prints_raw_key_and_reuses_then_rotates(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                setup_access, "credential_directory", return_value=Path(directory)
            ), patch.object(setup_access, "secure_directory"):
                path, digest = setup_access.provision()
                raw = path.read_text()
                path2, digest2 = setup_access.provision()
                self.assertEqual(digest, digest2)
                output = io.StringIO()
                with contextlib.redirect_stdout(output), patch(
                    "sys.argv", ["setup_access.py"]
                ):
                    setup_access.main()
                self.assertNotIn(raw, output.getvalue())
                self.assertIn(digest, output.getvalue())
                _, new_digest = setup_access.provision(rotate=True)
                self.assertNotEqual(new_digest, digest)


if __name__ == "__main__":
    unittest.main()
