import unittest

from scripts.build_canonical_projections import index_ffa, normalize_name, normalize_position, normalize_team, parse_value
from scripts.evaluate_projection_sources import ffa_standard_points, metrics


class CanonicalProjectionTests(unittest.TestCase):
    def test_name_normalization_handles_punctuation_accents_and_suffixes(self):
        self.assertEqual(normalize_name("D'Andre Swift Jr."), "dandreswift")
        self.assertEqual(normalize_name("José Núñez III"), "josenunez")

    def test_provider_position_and_team_aliases(self):
        self.assertEqual(normalize_position("DST"), "DEF")
        self.assertEqual(normalize_team("JAC"), "JAX")

    def test_ffa_na_is_missing(self):
        self.assertIsNone(parse_value("NA"))
        self.assertEqual(parse_value("12.5"), 12.5)

    def test_ffa_standard_scoring(self):
        stats = {"pass_yds": 250, "pass_tds": 2, "pass_ints": 1, "rush_yds": 20,
                 "rush_tds": 1, "fumbles_lost": 1, "2pt_tds": 1}
        self.assertEqual(ffa_standard_points(stats, "QB"), 24.0)

    def test_evaluation_metrics(self):
        rows = [{"prediction": 10, "actual_points_std": 8}, {"prediction": 5, "actual_points_std": 9}]
        self.assertEqual(metrics(rows, "prediction"), {"n": 2, "mae": 3.0, "rmse": 3.162, "bias": -1.0})

    def test_identical_ffa_rows_are_deduplicated(self):
        row = {"player": "Example Player", "position": "RB", "team": "EX", "id": "1"}
        by_name_pos, _, _, duplicate_count = index_ffa([row, dict(row)], {})
        self.assertEqual(len(by_name_pos[("exampleplayer", "RB")]), 1)
        self.assertEqual(duplicate_count, 1)


if __name__ == "__main__":
    unittest.main()
