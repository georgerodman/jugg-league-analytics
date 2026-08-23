import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class SqliteSchemaTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript((ROOT/"db/migrations/001_initial.sql").read_text())

    def tearDown(self): self.db.close()

    def seed(self):
        self.db.execute("INSERT INTO drafts(id,season,name,team_count,budget_per_team,minimum_bid,required_players_per_team) VALUES('d',2026,'JUGG',10,200,1,14)")
        self.db.execute("INSERT INTO owners(id,display_name) VALUES('o','Owner')")
        self.db.execute("INSERT INTO teams(id,draft_id,owner_id,display_name,starting_budget) VALUES('t','d','o','Team',200)")
        self.db.execute("INSERT INTO players(id,display_name,position,identity_status) VALUES('p','Player','RB','stable')")
        self.db.execute("INSERT INTO draft_events(id,draft_id,sequence,event_type,aggregate_type,aggregate_id,idempotency_key,payload_json,occurred_at) VALUES('e','d',1,'nomination_opened','nomination','n','key','{}','2026-08-01T00:00:00Z')")

    def test_single_open_nomination_and_event_immutability(self):
        self.seed()
        self.db.execute("INSERT INTO nominations(id,draft_id,player_id,status,opened_event_id,opened_at) VALUES('n','d','p','open','e','2026-08-01T00:00:00Z')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO nominations(id,draft_id,player_id,status,opened_event_id,opened_at) VALUES('n2','d','p','open','e','2026-08-01T00:00:01Z')")
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("DELETE FROM draft_events WHERE id='e'")

    def test_event_idempotency_and_json_validation(self):
        self.seed()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO draft_events(id,draft_id,sequence,event_type,aggregate_type,aggregate_id,idempotency_key,payload_json,occurred_at) VALUES('e2','d',2,'draft_started','draft','d','key','{}','x')")
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("INSERT INTO owners(id,display_name,profile_json) VALUES('bad','Bad','not-json')")

if __name__ == '__main__': unittest.main()
