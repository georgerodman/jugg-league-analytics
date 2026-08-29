import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from espn_salary_cap_values import PipelineError, single_content_page_words, validate


class FakePage:
    def __init__(self, words):
        self.words = words

    def extract_words(self):
        return self.words


class EspnSalaryCapValidationTests(unittest.TestCase):
    def test_ignores_blank_trailing_export_page(self):
        words = [{"text": "player"}]
        self.assertEqual(single_content_page_words([FakePage(words), FakePage([])], "sheet.pdf"), words)

    def test_rejects_multiple_populated_pages(self):
        with self.assertRaises(PipelineError):
            single_content_page_words([FakePage([{"text": "one"}]), FakePage([{"text": "two"}])], "sheet.pdf")

    def test_flags_unmatched_and_bad_count(self):
        rows = [{
            "overall_rank": 1, "position": "RB", "player_name": "Example Player",
            "nfl_team": "DEN", "salary_cap_value": 10, "match_method": "unmatched",
        }]
        flags = validate(rows, 2026)
        self.assertEqual({flag["type"] for flag in flags}, {"row_count", "unmatched"})


if __name__ == "__main__":
    unittest.main()
