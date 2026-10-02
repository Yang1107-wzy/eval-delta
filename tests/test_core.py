import tempfile
import unittest
from pathlib import Path

from eval_delta.core import compare, load_run, markdown_report


class DeltaTests(unittest.TestCase):
    def test_lower_is_better_regression(self):
        r = compare([{"id": "a", "error": 2}], [{"id": "a", "error": 3}], {"error": "lower"})
        self.assertFalse(r["passed"])
        self.assertEqual(r["metrics"]["error"]["regressions"], 1)
        self.assertEqual(r["metrics"]["error"]["mean_change"], 1)

    def test_higher_is_better(self):
        r = compare(
            [{"id": 1, "accuracy": 0.5}], [{"id": 1, "accuracy": 0.8}], {"accuracy": "higher"}
        )
        self.assertTrue(r["passed"])
        self.assertEqual(r["metrics"]["accuracy"]["improvements"], 1)

    def test_tolerance_boundary(self):
        r = compare([{"id": "a", "x": 1}], [{"id": "a", "x": 1.5}], {"x": "lower"}, tolerance=0.5)
        self.assertTrue(r["passed"])
        self.assertEqual(r["metrics"]["x"]["unchanged"], 1)

    def test_aligns_by_id_not_order(self):
        a = [{"id": "a", "x": 1}, {"id": "b", "x": 2}]
        b = [{"id": "b", "x": 2}, {"id": "a", "x": 1}]
        self.assertTrue(compare(a, b, {"x": "lower"})["passed"])

    def test_missing_rows_fail(self):
        r = compare(
            [{"id": "a", "x": 1}, {"id": "b", "x": 2}], [{"id": "a", "x": 1}], {"x": "lower"}
        )
        self.assertFalse(r["passed"])
        self.assertEqual(r["missing_in_candidate"], ["b"])

    def test_duplicate_ids_fail(self):
        with self.assertRaises(ValueError):
            compare([{"id": "a", "x": 1}] * 2, [{"id": "a", "x": 1}], {"x": "lower"})

    def test_numeric_and_string_ids_are_distinct(self):
        r = compare([{"id": 1, "x": 1}], [{"id": "1", "x": 1}], {"x": "lower"})
        self.assertEqual(r["paired"], 0)
        self.assertFalse(r["passed"])

    def test_invalid_metric_values(self):
        for value in [True, "1", None, float("nan"), float("inf")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare([{"id": 1, "x": value}], [{"id": 1, "x": 1}], {"x": "lower"})

    def test_missing_metrics(self):
        with self.assertRaises(ValueError):
            compare([{"id": 1}], [{"id": 1, "x": 1}], {"x": "lower"})

    def test_empty_runs_fail(self):
        self.assertFalse(compare([], [], {"x": "lower"})["passed"])

    def test_aggregate_does_not_hide_regressions(self):
        a = [{"id": 1, "x": 5}, {"id": 2, "x": 5}]
        b = [{"id": 1, "x": 1}, {"id": 2, "x": 6}]
        r = compare(a, b, {"x": "lower"})
        self.assertLess(r["metrics"]["x"]["mean_change"], 0)
        self.assertFalse(r["passed"])

    def test_multiple_metrics(self):
        r = compare(
            [{"id": 1, "x": 1, "y": 3}], [{"id": 1, "x": 1, "y": 4}], {"x": "lower", "y": "higher"}
        )
        self.assertEqual(len(r["metrics"]), 2)
        self.assertTrue(r["passed"])

    def test_report_escapes_markdown(self):
        r = compare([{"id": "a|b", "x": 1}], [{"id": "a|b", "x": 2}], {"x": "lower"})
        self.assertIn("a\\|b", markdown_report(r))

    def test_rejects_invalid_tolerance(self):
        for t in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                compare([], [], {"x": "lower"}, tolerance=t)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "run.jsonl"
            p.write_text('{"id":1,"x":1,"x":2}\n')
            with self.assertRaises(ValueError):
                load_run(p)

    def test_underflow_and_high_precision_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "run.jsonl"
            for literal in ["1e-400", "0.12345678901234567890123456789", "1e400"]:
                p.write_text('{"id":1,"x":' + literal + "}\n")
                with self.subTest(literal=literal), self.assertRaises(ValueError):
                    load_run(p)

    def test_large_mixed_numeric_regression_not_hidden(self):
        r = compare(
            [{"id": 1, "x": 9007199254740993}],
            [{"id": 1, "x": 9007199254740992.0}],
            {"x": "higher"},
        )
        self.assertFalse(r["passed"])
        self.assertEqual(r["metrics"]["x"]["regressions"], 1)

    def test_huge_zero_exponent_is_input_error(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "run.jsonl"
            p.write_text('{"id":1,"x":0e999999999999999999999999}\n')
            with self.assertRaises(ValueError):
                load_run(p)
