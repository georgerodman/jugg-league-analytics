import unittest

from scripts.rebuild_all import compare_boards


class RebuildWorkflowTests(unittest.TestCase):
    def test_board_comparison_reports_changes(self):
        old = [{"internal_player_id":"p1","player_name":"One","expected_jugg_price":10,
                "draft_probability":.5,"production_value":12,"expected_surplus":2}]
        new = [{"internal_player_id":"p1","player_name":"One","expected_jugg_price":11,
                "draft_probability":.6,"production_value":14,"expected_surplus":3}]
        result = compare_boards(old,new)
        change = result["largest_absolute_surplus_changes"][0]
        self.assertEqual(change["surplus_change"],1)
        self.assertEqual(change["draft_probability_change"],.1)


if __name__ == "__main__":
    unittest.main()
