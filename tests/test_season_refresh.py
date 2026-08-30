import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.season_refresh import RefreshError, executable_commands, execution_preflight, run_commands
from scripts.season_refresh_plan import build_plan


class SeasonRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "active-season.json").write_text(
            json.dumps({"season": 2026, "draftId": "jugg-2026"}), encoding="utf-8"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_execution_requires_explicit_confirmation_and_prerequisites(self):
        with self.assertRaisesRegex(RefreshError, "Confirmation"):
            execution_preflight(self.root, 2027, "", False, {})
        with self.assertRaisesRegex(RefreshError, "archive"):
            execution_preflight(self.root, 2027, "REFRESH-2027", False, {})

    def test_plan_commands_exclude_activation_and_sheet_operations(self):
        commands = executable_commands(build_plan(self.root, 2027))
        flattened = " ".join(part for _, command in commands for part in command)
        self.assertNotIn("active-season.json", flattened)
        self.assertNotIn("google", flattened.lower())
        self.assertNotIn("season_rollover_readiness", flattened)

    def test_failed_stage_restores_existing_pointers(self):
        pointer = self.root / "data" / "processed" / "example" / "latest.json"
        pointer.parent.mkdir(parents=True)
        pointer.write_text('{"artifact":"old.json"}\n', encoding="utf-8")

        calls = 0
        def fake_runner(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            pointer.write_text('{"artifact":"new.json"}\n', encoding="utf-8")
            return subprocess.CompletedProcess([], 1, "out", "failure")

        with self.assertRaisesRegex(RefreshError, "Stage failed"):
            run_commands(self.root, [("fake", ["python3", "fake.py"])], self.root / ".local" / "run", fake_runner)
        self.assertEqual(calls, 1)
        self.assertEqual(json.loads(pointer.read_text())["artifact"], "old.json")


if __name__ == "__main__":
    unittest.main()
