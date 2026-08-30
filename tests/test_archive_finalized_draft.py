import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.archive_finalized_draft import create_archive


class FinalizedDraftArchiveTest(unittest.TestCase):
    def test_creates_verified_database_and_readable_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "draft.sqlite"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE drafts(id TEXT PRIMARY KEY,season INTEGER,name TEXT,status TEXT,state_version INTEGER,finalized_at TEXT,finalized_backup_path TEXT,google_sheets_sync_enabled INTEGER);
                CREATE TABLE owners(id TEXT PRIMARY KEY,display_name TEXT);
                CREATE TABLE teams(id TEXT PRIMARY KEY,draft_id TEXT,owner_id TEXT,display_name TEXT);
                CREATE TABLE team_draft_state(team_id TEXT,remaining_budget INTEGER,rostered_player_count INTEGER,open_slot_count INTEGER);
                CREATE TABLE players(id TEXT PRIMARY KEY,display_name TEXT,position TEXT,nfl_team TEXT);
                CREATE TABLE draft_player_pool(draft_id TEXT,player_id TEXT,status TEXT);
                CREATE TABLE draft_events(id TEXT PRIMARY KEY,draft_id TEXT,sequence INTEGER,event_type TEXT,aggregate_type TEXT,aggregate_id TEXT,idempotency_key TEXT,payload_json TEXT,occurred_at TEXT,recorded_at TEXT);
                CREATE TABLE nominations(id TEXT,draft_id TEXT,status TEXT);
                CREATE TABLE roster_slots(id TEXT PRIMARY KEY,team_id TEXT,slot_type TEXT,ordinal INTEGER,player_id TEXT,filled_sale_id TEXT);
                CREATE TABLE sales(id TEXT PRIMARY KEY,draft_id TEXT,player_id TEXT,winner_team_id TEXT,price INTEGER,recorded_event_id TEXT,roster_slot_id TEXT,voided_event_id TEXT,recorded_at TEXT);
                INSERT INTO drafts VALUES('d',2026,'Test Draft','complete',2,'2026-08-30T00:00:00Z',NULL,0);
                INSERT INTO owners VALUES('o','Owner');
                INSERT INTO teams VALUES('t','d','o','Team');
                INSERT INTO team_draft_state VALUES('t',199,1,0);
                INSERT INTO players VALUES('p','Player','RB','CHI');
                INSERT INTO draft_events VALUES('e','d',1,'sale_recorded','sale','s','sale-key','{}','2026-08-30T00:00:00Z','2026-08-30T00:00:00Z');
                INSERT INTO roster_slots VALUES('slot','t','RB',1,'p','s');
                INSERT INTO sales VALUES('s','d','p','t',1,'e','slot',NULL,'2026-08-30T00:00:00Z');
                """
            )
            connection.commit()
            connection.close()

            archive = create_archive(database, root / "archives", "d")
            self.assertTrue((archive / "draft.sqlite").exists())
            self.assertIn("Player", (archive / "rosters.csv").read_text())
            self.assertIn('"rosters.csv": 1', (archive / "manifest.json").read_text())
            archived = sqlite3.connect(archive / "draft.sqlite")
            self.assertEqual(archived.execute("SELECT status FROM drafts").fetchone()[0], "complete")
            archived.close()


if __name__ == "__main__":
    unittest.main()
