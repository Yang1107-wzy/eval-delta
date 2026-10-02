import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CLITests(unittest.TestCase):
    def cli(self, a, b, *args):
        with tempfile.TemporaryDirectory() as d:
            left, right = Path(d) / "a.jsonl", Path(d) / "b.jsonl"
            left.write_text("".join(json.dumps(row) + "\n" for row in a), encoding="utf-8")
            right.write_text("".join(json.dumps(row) + "\n" for row in b), encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-m", "eval_delta", str(left), str(right), *args],
                capture_output=True,
                text=True,
            )

    def test_pass(self):
        r = self.cli(
            [{"id": 1, "x": 2}], [{"id": 1, "x": 1}], "--metric", "x:lower", "--format", "json"
        )
        self.assertEqual(r.returncode, 0)
        self.assertTrue(json.loads(r.stdout)["passed"])

    def test_regression_exit_one(self):
        r = self.cli([{"id": 1, "x": 2}], [{"id": 1, "x": 3}], "--metric", "x:lower")
        self.assertEqual(r.returncode, 1)

    def test_invalid_data_exit_two(self):
        self.assertEqual(
            self.cli([{"id": 1}], [{"id": 1, "x": 3}], "--metric", "x:lower").returncode, 2
        )

    def test_markdown(self):
        r = self.cli(
            [{"id": 1, "x": 2}], [{"id": 1, "x": 3}], "--metric", "x:lower", "--format", "markdown"
        )
        self.assertIn("| Metric |", r.stdout)
        self.assertIn("**FAIL**", r.stdout)

    def test_duplicate_metric_exit_two(self):
        self.assertEqual(
            self.cli([], [], "--metric", "x:lower", "--metric", "x:higher").returncode, 2
        )

    def test_invalid_tolerance_exit_two(self):
        self.assertEqual(
            self.cli([], [], "--metric", "x:lower", "--tolerance", "nan").returncode, 2
        )

    def test_corrupt_gzip_exit_two_no_traceback(self):
        import gzip

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.jsonl.gz"
            blob = bytearray(gzip.compress(b"{}\n"))
            blob[10] = 255
            p.write_bytes(blob)
            r = subprocess.run(
                [sys.executable, "-m", "eval_delta", str(p), str(p), "--metric", "x:lower"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(r.returncode, 2)
            self.assertNotIn("Traceback", r.stderr)
