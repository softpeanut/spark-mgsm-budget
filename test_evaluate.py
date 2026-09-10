import json
from pathlib import Path
import tempfile
import unittest

from evaluate import build_plan, preserve_identity, score_output


class ScoringTests(unittest.TestCase):
    def test_requires_delivered_answer_after_thinking(self):
        self.assertFalse(score_output("reasoning FINAL: 18", True, 18)["correct"])
        self.assertTrue(score_output("18 is correct.</think>FINAL: 18", True, 18)["correct"])
        self.assertFalse(score_output("FINAL: 18\n<think>more reasoning", False, 18)["correct"])

    def test_reference_comparison_and_unicode(self):
        self.assertTrue(score_output("答案\nＦＩＮＡＬ： １８", False, 18)["correct"])
        self.assertEqual(score_output("FINAL: -2", False, -3)["status"], "wrong_integer")
        self.assertTrue(score_output("FINAL: 0", False, 0)["correct"])
        self.assertTrue(score_output("FINAL: -2", False, -2)["correct"])

    def test_does_not_recover_ambiguous_or_malformed_answers(self):
        for output in ("FINAL: 18 dollars", "FINAL: 18\nDone", "FINAL: 9\nFINAL: 18",
                       "FINAL: 1,800", "Answer: 18", "<think>FINAL: 18"):
            with self.subTest(output=output):
                self.assertIsNone(score_output(output, False, 18)["prediction"])

    def test_nested_thinking_is_not_silently_accepted(self):
        self.assertIsNone(score_output("<think>x</think>FINAL: 18", True, 18)["prediction"])


class PlanAndResumeTests(unittest.TestCase):
    def test_same_problems_and_references_in_all_four_conditions(self):
        plan = build_plan()
        self.assertEqual(len(plan["cases"]), 96)
        self.assertEqual(len({c["id"] for c in plan["cases"]}), 96)
        for row in plan["selected_rows_zero_based"]:
            paired = [c for c in plan["cases"] if c["row"] == row]
            self.assertEqual({(c["language"], c["thinking"]) for c in paired},
                             {("en", False), ("en", True), ("zh", False), ("zh", True)})
            self.assertEqual(len({c["expected"] for c in paired}), 1)
        self.assertEqual(plan, build_plan())

    def test_changed_identity_is_rejected_and_original_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            preserve_identity(path, {"revision": "first"})
            preserve_identity(path, {"revision": "first"})
            with self.assertRaises(ValueError):
                preserve_identity(path, {"revision": "different"})
            self.assertEqual(json.loads(path.read_text()), {"revision": "first"})


if __name__ == "__main__":
    unittest.main()
