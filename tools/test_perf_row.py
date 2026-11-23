"""(custom, Nov 22) The brain's pass and think times summed up in each world row (tools/live_bots.py PERF, perf_row)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import live_bots as lb  # noqa: E402


class PerfRowTests(unittest.TestCase):
    def setUp(self):
        lb.PERF.update({"pass": [], "think_sum": [], "think": {}, "think_pass": 0.0})

    def test_nothing_yet(self):
        self.assertIsNone(lb.perf_row())

    def test_summed_and_reset(self):
        lb.PERF["pass"] += [30.0, 150.0, 40.0, 33.0]
        lb.PERF["think_sum"] += [20.0, 120.0, 25.0, 22.0]
        lb.PERF["think"].update({3: 60.0, 5: 12.5})
        self.assertEqual(lb.perf_row(), [4, 40.0, 150.0, 1, 120.0, {"3": 60.0, "5": 12.5}])
        self.assertIsNone(lb.perf_row())


if __name__ == "__main__":
    unittest.main()
