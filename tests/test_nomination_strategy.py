import unittest

from scripts.nomination_strategy import recommend_nominations


class NominationStrategyTests(unittest.TestCase):
    def test_returns_intent_grouped_explanations(self):
        result=recommend_nominations([
            {"player_name":"Wanted Star","championship_equity_delta":1.2,"expected_price":40,"price_low":36,"likely_bidder_count":2,"accidental_win_risk":0.2},
            {"player_name":"Opponent Magnet","championship_equity_delta":-0.2,"expected_price":45,"likely_bidder_count":5,"opponent_budget_pressure":5,"accidental_win_risk":0.05},
        ])
        rows=[row for bucket in result.values() for row in bucket]
        self.assertEqual(len(rows),2)
        self.assertTrue(all(row["reason"] for row in rows))
        self.assertIn("Opponent Magnet",[row["player_name"] for row in result["budget_drain"]])


if __name__ == "__main__": unittest.main()
