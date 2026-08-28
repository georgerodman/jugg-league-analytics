import unittest

from scripts.nflverse_depth_charts import DepthChartError, fantasy_group, normalize_latest, parse_rows


HEADER = "dt,team,player_name,espn_id,gsis_id,pos_grp_id,pos_grp,pos_id,pos_name,pos_abb,pos_slot,pos_rank\n"


class DepthChartTests(unittest.TestCase):
    def test_schema_validation(self):
        with self.assertRaises(DepthChartError):
            parse_rows(b"dt,team\n2026-01-01T00:00:00Z,ARI\n")

    def test_fantasy_position_normalization(self):
        self.assertEqual(fantasy_group({"pos_abb": "LWR", "pos_name": "Left Wide Receiver"}), "WR")
        self.assertEqual(fantasy_group({"pos_abb": "FB", "pos_name": "Fullback"}), "RB")
        self.assertIsNone(fantasy_group({"pos_abb": "LDE", "pos_name": "Left Defensive End"}))

    def test_latest_snapshot_is_selected_and_gsis_identity_is_used(self):
        rows = []
        for team_number in range(32):
            team = f"T{team_number:02d}"
            rows.append({"dt": "2026-08-20T00:00:00Z", "team": team, "player_name": "Old Player",
                         "espn_id": "1", "gsis_id": "old", "pos_grp_id": "1", "pos_grp": "Offense",
                         "pos_id": "1", "pos_name": "Quarterback", "pos_abb": "QB", "pos_slot": "1", "pos_rank": "1"})
            rows.append({"dt": "2026-08-27T00:00:00Z", "team": team, "player_name": f"Player {team}",
                         "espn_id": str(team_number), "gsis_id": f"00-{team_number:07d}", "pos_grp_id": "1",
                         "pos_grp": "Offense", "pos_id": "1", "pos_name": "Quarterback", "pos_abb": "QB",
                         "pos_slot": "1", "pos_rank": "1"})
        artifact = normalize_latest(rows, 2026, "2026-08-27T01:00:00+00:00")
        self.assertEqual(artifact["metadata"]["team_count"], 32)
        self.assertEqual(artifact["metadata"]["snapshot_at"], "2026-08-27T00:00:00Z")
        self.assertEqual(artifact["players"][0]["internal_player_id"], "nfl:gsis:00-0000000")
        self.assertEqual(len(artifact["teams"][0]["fantasy_offense"]["QB"]), 1)


if __name__ == "__main__":
    unittest.main()
