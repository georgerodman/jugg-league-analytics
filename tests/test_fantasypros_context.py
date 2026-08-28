import unittest

from scripts.fantasypros_context import clean_text, normalize_injury, normalize_news, normalize_rank, validate_collection
from scripts.fantasypros_projections import PipelineError


class FantasyProsContextTests(unittest.TestCase):
    def test_validates_declared_count(self):
        with self.assertRaisesRegex(PipelineError, "declared count"):
            validate_collection({"count": 2, "items": [{}]}, "items", "news")

    def test_normalizes_and_links_all_context_types(self):
        identities = {10: "nfl:gsis:00-1"}
        rank = normalize_rank({"player_id": 10, "player_name": "Player", "rank_ecr": 8, "pos_rank": "RB4"}, "RB", identities)
        injury = normalize_injury({"player_id": 10, "name": "Player", "comment": "<b>Limited</b> today"}, identities)
        news = normalize_news({"player_id": 10, "title": "Update", "desc": "Line one<br>line two"}, identities)
        self.assertEqual(rank["internal_player_id"], "nfl:gsis:00-1")
        self.assertEqual(injury["comment"], "Limited today")
        self.assertEqual(news["description"], "Line one line two")

    def test_clean_text_handles_missing_values(self):
        self.assertIsNone(clean_text(None))


if __name__ == "__main__":
    unittest.main()
