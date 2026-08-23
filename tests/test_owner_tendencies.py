import unittest
from scripts.owner_tendencies import build_profiles, markdown_report

class OwnerTendencyTests(unittest.TestCase):
    def test_profiles_do_not_claim_timing(self):
        sales=[]
        positions=["QB"]+["RB"]*4+["WR"]*5+["TE","K","DEF"]+["WR"]
        for season in range(2020,2026):
            for owner in ("A","B"):
                for i,pos in enumerate(positions):sales.append({"owner":owner,"season":season,"position":pos,"salary":200//14,"internal_player_id":f"{pos}{i}","player_name":f"P{i}","nfl_team":"X"})
        profiles=build_profiles(sales)
        self.assertEqual(len(profiles),2)
        self.assertTrue(all(profile["evidence_strength"]=="high" for profile in profiles))
        self.assertTrue(all("timing" in profile["limitations"][0].lower() for profile in profiles))
        report=markdown_report(profiles,"test")
        self.assertIn("## A",report)
        self.assertIn("Market behavior",report)
        self.assertIn("## League summary",report)
        self.assertIn("## Strong stylistic trends",report)
        self.assertIn("## Strong personnel trends",report)

if __name__=="__main__":unittest.main()
