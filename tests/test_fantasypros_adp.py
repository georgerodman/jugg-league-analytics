import unittest

from scripts.fantasypros_adp import PipelineError, extract_source


class FantasyProsAdpTests(unittest.TestCase):
    def test_extracts_platform_value_from_experts_map(self):
        payload = {"players": [{
            "player_id": 123, "player_name": "Example Player", "player_position_id": "RB",
            "player_team_id": "EX", "experts": {"236": "12.5", "79": "14"},
        }]}
        self.assertEqual(extract_source(payload, "yahoo")[123]["adp_yahoo"], 12.5)
        self.assertEqual(extract_source(payload, "espn")[123]["adp_espn"], 14.0)

    def test_retains_valid_id_when_historical_metadata_is_missing(self):
        payload = {"players": [{"player_id": 123, "experts": {"79": "236"}}]}
        result = extract_source(payload, "espn")[123]
        self.assertIsNone(result["name"])
        self.assertEqual(result["adp_espn"], 236.0)

    def test_rejects_response_without_requested_source(self):
        with self.assertRaisesRegex(PipelineError, "No yahoo rows"):
            extract_source({"players": [{"player_id": 1, "experts": {"79": "1"}}]}, "yahoo")


if __name__ == "__main__":
    unittest.main()
