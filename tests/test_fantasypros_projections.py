import json
import unittest
from pathlib import Path

from scripts.fantasypros_projections import PipelineError, normalize_player, score_player, validate_response

ROOT = Path(__file__).resolve().parents[1]
LEAGUE = json.loads((ROOT / "config" / "league.json").read_text(encoding="utf-8"))


class FantasyProsProjectionTests(unittest.TestCase):
    def test_custom_offense_scoring(self):
        stats = {"pass_yds": 250, "pass_tds": 2, "pass_ints": 1, "rush_yds": 20,
                 "rush_tds": 1, "fumbles": 1, "2pt_tds": 1}
        self.assertEqual(score_player("QB", stats, LEAGUE), 27.0)

    def test_normalizes_dst_to_def(self):
        source = {"fpid": 999, "name": "Example DST", "position_id": "DST", "team_id": "EX",
                  "stats": {"def_sack": 40, "def_int": 12, "def_td": 3}}
        result = normalize_player(source, "DST", LEAGUE)
        self.assertEqual(result["position"], "DEF")
        self.assertEqual(result["league_projected_points"], 82.0)

    def test_rejects_truncated_response(self):
        payload = {"season": "2026", "week": "0", "count": "2", "players": [{}]}
        with self.assertRaisesRegex(PipelineError, "incomplete response"):
            validate_response(payload, 2026, "QB")

    def test_kicker_uses_conservative_aggregate_field_goal_value(self):
        self.assertEqual(score_player("K", {"fg": 25, "xpt": 40}, LEAGUE), 115.0)

    def test_defense_includes_points_allowed_buckets_and_return_tds(self):
        stats = {"def_sack": 40, "def_pa_a": 1, "def_pa_g": 2, "def_retd": 1}
        self.assertEqual(score_player("DEF", stats, LEAGUE), 46.0)

    def test_accepts_single_element_stats_array(self):
        source = {"fpid": 123, "name": "Example Player", "position_id": "RB", "team_id": "EX",
                  "stats": [{"rush_yds": 1000, "rush_tds": 10}]}
        result = normalize_player(source, "RB", LEAGUE)
        self.assertEqual(result["league_projected_points"], 160.0)


if __name__ == "__main__":
    unittest.main()
