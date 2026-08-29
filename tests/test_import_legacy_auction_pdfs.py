import unittest

from scripts.import_legacy_auction_pdfs import validate


def rows(season: int, salaries: list[int], source: str = "yahoo"):
    return [
        {
            "Season": str(season), "FF Team": f"Team {index // 14}",
            "Pos": "RB", "Player": f"Player {index}", "Team": "",
            "Salary": f"${salary}", "_pick": str(index + 1), "_source": source,
        }
        for index, salary in enumerate(salaries)
    ]


class LegacyAuctionValidationTests(unittest.TestCase):
    def test_accepts_complete_yahoo_draft(self):
        validate(rows(2015, [15] * 130 + [5] * 10), 2015)

    def test_rejects_zero_price_even_when_row_count_is_complete(self):
        values = [15] * 130 + [5] * 9 + [0]
        with self.assertRaisesRegex(ValueError, "non-positive"):
            validate(rows(2013, values), 2013)

    def test_accepts_plausible_espn_unspent_budget(self):
        validate(rows(2019, [14] * 139 + [43], source="espn"), 2019)


if __name__ == "__main__":
    unittest.main()
