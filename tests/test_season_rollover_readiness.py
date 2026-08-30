import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.season_rollover_readiness import readiness


class SeasonRolloverReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "config").mkdir()
        (self.root / ".local" / "backups").mkdir(parents=True)
        self.backup = self.root / ".local" / "backups" / "final.sqlite"
        self.backup.touch()
        active = {"schemaVersion": 1, "season": 2026, "draftId": "jugg-2026", "draftName": "2026 JUGG Auction", "databasePath": ".local/current.sqlite", "googleSheetsConfigPath": "config/google_sheets.json"}
        (self.root / "config" / "active-season.json").write_text(json.dumps(active))
        connection = sqlite3.connect(self.root / ".local" / "current.sqlite")
        connection.execute("CREATE TABLE drafts(id TEXT,season INTEGER,status TEXT,finalized_at TEXT,finalized_backup_path TEXT,google_sheets_sync_enabled INTEGER)")
        connection.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?)", ("jugg-2026", 2026, "complete", "2026-08-30T00:00:00Z", str(self.backup), 0))
        connection.commit()
        connection.close()

    def tearDown(self):
        self.temporary.cleanup()

    def test_missing_future_artifacts_are_reported_without_creating_state(self):
        report = readiness(self.root, 2027)
        self.assertFalse(report["ready"])
        self.assertEqual(report["target"]["draftId"], "jugg-2027")
        self.assertFalse((self.root / report["target"]["databasePath"]).exists())
        self.assertTrue(any(item["name"] == "artifact_canonical_projections" and item["status"] == "blocker" for item in report["checks"]))
        self.assertIn("No configuration", report["safety"])

    def test_reusing_active_season_is_blocked(self):
        report = readiness(self.root, 2026)
        blockers = {item["name"] for item in report["checks"] if item["status"] == "blocker"}
        self.assertIn("target_is_future", blockers)
        self.assertIn("target_draft_distinct", blockers)


if __name__ == "__main__":
    unittest.main()
