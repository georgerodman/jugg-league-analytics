import json
import tempfile
import unittest
from pathlib import Path

from scripts.season_refresh_plan import build_plan


class SeasonRefreshPlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "active-season.json").write_text(
            json.dumps({"season": 2026, "draftId": "jugg-2026"}), encoding="utf-8"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_future_plan_is_ordered_and_does_not_create_state(self):
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        plan = build_plan(self.root, 2027)
        after = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(plan["targetSeason"], 2027)
        self.assertFalse(plan["executableNow"])
        self.assertEqual(plan["steps"][0]["status"], "ready")
        names = [item["name"] for item in plan["steps"]]
        self.assertLess(names.index("fantasypros_projections"), names.index("canonical_projections"))
        self.assertLess(names.index("canonical_projections"), names.index("auction_price_model"))
        self.assertIn("No downloads ran", plan["safety"])

    def test_current_season_is_blocked(self):
        plan = build_plan(self.root, 2026)
        target = next(item for item in plan["steps"] if item["name"] == "validate_target_season")
        self.assertEqual(target["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
