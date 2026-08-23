import json
import unittest
from pathlib import Path

from scripts.nflverse_pipeline import points_allowed_score, score_defense, score_player

ROOT = Path(__file__).resolve().parents[1]
LEAGUE = json.loads((ROOT / "config" / "league.json").read_text())


class NflversePipelineTests(unittest.TestCase):
    def test_scores_custom_offense(self):
        row = {"passing_yards": "250", "passing_tds": "2", "passing_interceptions": "1",
               "rushing_yards": "20", "rushing_tds": "1", "passing_2pt_conversions": "1",
               "fumbles_lost_total": "1"}
        self.assertEqual(score_player("QB", row, LEAGUE), 27.0)

    def test_scores_kicker_distance_buckets_and_misses(self):
        row = {"fg_made_20_29": "1", "fg_made_40_49": "1", "fg_made_50_59": "1",
               "fg_missed_30_39": "1", "pat_made": "3", "pat_missed": "1"}
        self.assertEqual(score_player("K", row, LEAGUE), 12.0)

    def test_points_allowed_buckets(self):
        settings = LEAGUE["scoring"]["defense_special_teams"]
        self.assertEqual(points_allowed_score(0, settings), 10)
        self.assertEqual(points_allowed_score(35, settings), -4)

    def test_scores_team_defense(self):
        row = {"def_sacks": "3", "def_interceptions": "2", "fumble_recovery_opp": "1",
               "def_tds": "1", "def_safeties": "1", "def_fg_blocks": "1", "special_teams_tds": "1"}
        self.assertEqual(score_defense(row, 17, LEAGUE), 24.0)


if __name__ == "__main__":
    unittest.main()
