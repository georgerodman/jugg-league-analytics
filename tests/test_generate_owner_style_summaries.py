import unittest

from scripts.generate_owner_style_summaries import validate_summary, word_count


class OwnerStyleSummaryGenerationTests(unittest.TestCase):
    def test_accepts_one_paragraph_with_target_length(self):
        summary = " ".join(f"word{index}" for index in range(100))
        self.assertEqual(word_count(validate_summary(summary)), 100)

    def test_rejects_multiline_or_out_of_range_summary(self):
        with self.assertRaisesRegex(ValueError, "90-110"):
            validate_summary("too short")
        with self.assertRaisesRegex(ValueError, "one paragraph"):
            validate_summary(" ".join(["word"] * 50) + "\n" + " ".join(["word"] * 50))


if __name__ == "__main__":
    unittest.main()
