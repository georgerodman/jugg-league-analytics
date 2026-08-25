import unittest

from scripts.championship_equity import lineup_score, position_volatility, replacement_access_backtest, simulate_league, weekly_projection_rows, wilson_interval


class ChampionshipEquityTests(unittest.TestCase):
    def test_lineup_optimizer_values_starters_not_total_bench(self):
        roster=[{"position":"QB","points":20},{"position":"K","points":8},{"position":"DEF","points":7},
            {"position":"RB","points":18},{"position":"RB","points":14},{"position":"RB","points":3},
            {"position":"WR","points":17},{"position":"WR","points":16},{"position":"WR","points":12},
            {"position":"TE","points":15},{"position":"TE","points":4}]
        self.assertEqual(lineup_score(roster),127)

    def test_weekly_rows_reconcile_to_season_and_zero_the_bye(self):
        players=[{"internal_player_id":"p","player_name":"Player","position":"RB","nfl_team":"DEN","projected_points":160,"bye_week":10}]
        rows=weekly_projection_rows(players,{}, {"RB":0.5},2026)
        self.assertAlmostEqual(sum(row["projected_points"] for row in rows),160,places=3)
        self.assertEqual(next(row for row in rows if row["week"]==10)["projected_points"],0)

    def test_volatility_is_bounded(self):
        rows=[]
        for position in ("QB","RB","WR","TE","K","DEF"):
            rows += [{"position":position,"league_points":value,"internal_player_id":position,"season":2025} for value in (5,10,12,15,20,30)]
        values=position_volatility(rows)
        self.assertTrue(all(0.15<=value<=1.5 for value in values.values()))

    def test_simulation_allocates_four_playoff_spots_and_one_title(self):
        rosters={}
        for team in range(10):
            positions=["QB","K","DEF","RB","RB","RB","WR","WR","WR","TE","TE"]
            rosters[str(team)]=[{"position":position,"weekly":{week:{"mean":10+team/10,"cv":0.3} for week in range(1,18)}} for position in positions]
        result=simulate_league(rosters,simulations=20,seed=7)
        self.assertAlmostEqual(sum(row["playoff_equity"] for row in result["teams"]),4,places=4)
        self.assertAlmostEqual(sum(row["championship_equity"] for row in result["teams"]),1,places=4)
        self.assertEqual(len(result["teams"][0]["championship_equity_interval_90"]),2)

    def test_replacement_policy_uses_prior_weeks_and_is_bounded(self):
        sales=[]; players=[]
        for owner in range(10):
            for position in ("QB","K","DEF","RB","RB","RB","WR","WR","WR","TE","TE"):
                player_id=f"{owner}-{position}-{len(sales)}"; players.append({"internal_player_id":player_id,"player_name":player_id,"position":position,"projected_points":160})
                sales.append({"season":2025,"owner":str(owner),"internal_player_id":player_id,"player_name":player_id,"position":position,"salary":1})
        players.append({"internal_player_id":"free-rb","player_name":"Free RB","position":"RB","projected_points":400})
        actual={(row["internal_player_id"],week):10 for row in players for week in range(1,16)}
        result=replacement_access_backtest(sales,players,actual,2025,max_adds=1)
        self.assertTrue(all(len(row["acquisitions"])<=1 for row in result))
        self.assertEqual(sum(len(row["acquisitions"]) for row in result),1)

    def test_wilson_interval_contains_estimate(self):
        low,high=wilson_interval(10,100)
        self.assertLessEqual(low,0.1); self.assertGreaterEqual(high,0.1)


if __name__ == "__main__": unittest.main()
