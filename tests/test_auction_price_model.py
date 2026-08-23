import math
import unittest

from scripts.auction_price_model import (
    evaluate, fit_line, fit_ridge, metrics, percentile, position_adjustments,
    predict_ridge, probability_metrics, solve_linear_system,
)


class AuctionPriceModelTests(unittest.TestCase):
    def test_metrics_preserve_prediction_minus_actual_bias(self):
        self.assertEqual(
            metrics([(10, 8), (5, 9)]),
            {"n": 2, "mae": 3.0, "rmse": 3.162, "bias": -1.0},
        )

    def test_linear_calibration_recovers_known_relationship(self):
        rows = [
            {"drafted": True, "espn_salary_cap_value": 1, "jugg_salary": 5},
            {"drafted": True, "espn_salary_cap_value": 2, "jugg_salary": 7},
            {"drafted": True, "espn_salary_cap_value": 3, "jugg_salary": 9},
        ]
        intercept, slope = fit_line(rows)
        self.assertAlmostEqual(intercept, 3.0)
        self.assertAlmostEqual(slope, 2.0)

    def test_evaluation_requires_held_out_seasons(self):
        rows = []
        for season in range(2020, 2026):
            rows.extend([
                {"season": season, "position": "RB", "drafted": True, "jugg_salary": season - 2010,
                 "espn_salary_cap_value": season - 2019, "player_pool_source": "espn_and_jugg"},
                {"season": season, "position": "WR", "drafted": False, "jugg_salary": None,
                 "espn_salary_cap_value": 1, "player_pool_source": "espn"},
            ])
        report = evaluate(rows)
        self.assertEqual(report["dataset"]["row_count"], 12)
        self.assertEqual(report["baselines"]["espn_calibrated_leave_one_season_out"]["n"], 6)
        self.assertEqual(report["neutral_model_tournament"]["row_count"], 5)
        self.assertNotIn("2020", report["neutral_model_tournament"]["by_test_season"])

    def test_percentile_interpolates(self):
        self.assertEqual(percentile([1, 2, 3, 4], 0.5), 2.5)

    def test_position_adjustment_shrinks_toward_global_mean(self):
        rows = [
            {"position": "QB", "jugg_salary": 15, "espn_salary_cap_value": 10},
            {"position": "RB", "jugg_salary": 10, "espn_salary_cap_value": 10},
        ]
        adjustments = position_adjustments(rows, prior_weight=0)
        self.assertEqual(adjustments, {"QB": 5.0, "RB": 0.0})

    def test_linear_solver(self):
        self.assertEqual(solve_linear_system([[2, 0], [0, 4]], [6, 8]), [3.0, 2.0])

    def test_ridge_handles_missing_features(self):
        rows = [
            {"position": "QB", "adp_espn": 1, "jugg_salary": 20},
            {"position": "RB", "adp_espn": None, "jugg_salary": 10},
            {"position": "WR", "adp_espn": 30, "jugg_salary": 5},
        ]
        model = fit_ridge(rows, ("adp_espn",))
        prediction = predict_ridge(model, {"position": "RB", "adp_espn": None})
        self.assertTrue(math.isfinite(prediction))

    def test_probability_metrics_reward_correct_ranking(self):
        result = probability_metrics([(0.9, 1), (0.8, 1), (0.2, 0), (0.1, 0)])
        self.assertEqual(result["auc"], 1.0)
        self.assertLess(result["brier"], 0.05)


if __name__ == "__main__":
    unittest.main()
