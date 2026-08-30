import unittest

from scripts.build_canonical_projections import index_ffa, normalize_name, normalize_position, normalize_team, parse_value, stable_internal_id


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

    def test_identical_ffa_rows_are_deduplicated(self):
        row = {"player": "Example Player", "position": "RB", "team": "EX", "id": "1"}
        by_name_pos, _, _, duplicate_count = index_ffa([row, dict(row)], {})
        self.assertEqual(len(by_name_pos[("exampleplayer", "RB")]), 1)
        self.assertEqual(duplicate_count, 1)

    def test_stable_identity_prefers_gsis_with_provisional_fallback(self):
        self.assertEqual(stable_internal_id(17298, "00-0034857"), ("nfl:gsis:00-0034857", "stable"))
        self.assertEqual(stable_internal_id(1, "team:BUF"), ("nfl:def:BUF", "stable"))
        self.assertEqual(stable_internal_id(99, None), ("provisional:fantasypros:99", "provisional"))


if __name__ == "__main__":
    unittest.main()
