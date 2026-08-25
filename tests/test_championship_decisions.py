import unittest

from scripts.championship_decisions import completion_path, decision_band, legal_roster


class ChampionshipDecisionTests(unittest.TestCase):
    def setUp(self):
        self.players=[]
        for position,count in {"QB":3,"WR":10,"RB":8,"TE":4,"K":3,"DEF":3}.items():
            for index in range(count):
                self.players.append({"internal_player_id":f"{position}-{index}","player_name":f"{position} {index}","position":position,
                    "projected_points":250-index*5,"expected_jugg_price":max(1,18-index*3),"price_range_low":max(1,14-index*3),
                    "price_range_high":max(1,22-index*3),"production_value_high":30-index})

    def test_completion_is_legal_and_respects_budget(self):
        path=completion_path([],self.players,200,"expected_jugg_price","lineup")
        self.assertIsNotNone(path);self.assertLessEqual(path["spend"],200);self.assertEqual(len(path["players"]),14)
        chosen=[next(row for row in self.players if row["internal_player_id"]==item["internal_player_id"]) for item in path["players"]]
        self.assertTrue(legal_roster(chosen))

    def test_decision_bands_default_to_neutral_under_disagreement(self):
        self.assertEqual(decision_band([-.03,.04,-.02,.03,0])["band"],"neutral")
        self.assertEqual(decision_band([.04,.03,.05,.035,.045])["band"],"strong_pursue")
        self.assertEqual(decision_band([-.04,-.03,-.05,-.035,-.045])["band"],"strong_pass")


if __name__=="__main__":unittest.main()
