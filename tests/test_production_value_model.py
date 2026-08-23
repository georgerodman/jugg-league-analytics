import unittest

from scripts.production_value_model import ALLOCATION, production_values


class ProductionValueModelTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
