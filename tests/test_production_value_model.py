import unittest

from scripts.production_value_model import ALLOCATION, assign_position_tiers, production_values, training_seasons


class ProductionValueModelTests(unittest.TestCase):
    def test_target_season_defines_completed_training_window(self):
        self.assertEqual(training_seasons(2027), tuple(range(2020, 2027)))

    def test_values_respect_allocation_and_budget(self):
        rows = []
        for position, count in ALLOCATION.items():
            for rank in range(count + 2):
                rows.append({"position": position, "player_name": f"{position}{rank}", "points": 200-rank})
        valued = production_values(rows, "points")
        rostered = [row for row in valued if row["modeled_roster_slot"]]
        self.assertEqual(len(rostered), 140)
        self.assertAlmostEqual(sum(row["production_value"] for row in rostered), 2000, places=1)
        for position, count in ALLOCATION.items():
            self.assertEqual(sum(row["modeled_roster_slot"] for row in valued if row["position"] == position), count)

    def test_position_tiers_split_natural_gaps_and_limit_span(self):
        rows = [
            {"position":"RB","player_name":"A","projected_points":240},
            {"position":"RB","player_name":"B","projected_points":236},
            {"position":"RB","player_name":"C","projected_points":215},
            {"position":"RB","player_name":"D","projected_points":203},
            {"position":"RB","player_name":"E","projected_points":199},
        ]
        assign_position_tiers(rows,"projected_points","production",maximum_span=16,minimum_natural_gap=6)
        self.assertEqual([row["production_tier"] for row in rows],[1,1,2,2,2])
        self.assertEqual(rows[0]["production_tier_size"],2)
        self.assertEqual(rows[2]["production_tier_high"],215)
        self.assertEqual(rows[4]["production_tier_low"],199)


if __name__ == "__main__":
    unittest.main()
