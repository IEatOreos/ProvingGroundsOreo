"""Breakpoint (reach_dlc_invasion): sight from the tower ledge to the bridge below.

The exported level data has no ground in the gap between the tower and the bridge, only a thin sloped surface 16-26 u
overhead (x 1.9-6.6, y 11-23). The sight rays treated the air under it as inside a hill, so bots on the bridge never
saw a person on the ledge (BTB match 20261105-192945, seconds 171-213, while that person's DMR rounds hit them).
maps/reach_dlc_invasion/sight_open.json marks that space open (Terrain.set_open_under).

Needs the installed map pack (heightmap.npz): prints SKIP without it. Run: python tools/test_breakpoint_sight.py
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.core import Vec

HEIGHTMAP = ROOT / "maps" / "reach_dlc_invasion" / "heightmap.npz"

# (person on the ledge, bot on the bridge) from the match trace
PAIRS = [
    (Vec(-2.47, 19.99, -3.74), Vec(11.46, 23.06, -8.65)),   # t 172.7, PwnageTV, hit by the person's DMR
    (Vec(-2.47, 19.99, -3.74), Vec(13.03, 17.63, -8.04)),   # t 172.7, LilWraith, aiming straight at the ledge
    (Vec(-2.47, 19.99, -3.74), Vec(19.62, 4.82, -7.37)),    # t 172.7, OutlawMarine
    (Vec(-1.80, 19.38, -4.06), Vec(23.41, -3.21, -7.08)),   # t 182.1, LilWraith
]


@unittest.skipUnless(HEIGHTMAP.exists(), "SKIP: no Breakpoint heightmap (map pack not installed)")
class BreakpointSightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from brain import maps
        cls.T = maps.terrain(maps.get_map("reach_dlc_invasion"))

    def test_bridge_sees_ledge(self):
        for me, bot in PAIRS:
            chest, head = self.T.target_parts(bot, me, 0.62, 0.35, 0.62, mode="see")
            self.assertTrue(head, f"bot at {bot} cannot see the head of {me}")
            self.assertTrue(any(self.T.target_parts(me, bot, 0.62, 0.35, 0.62, mode="see")),
                            f"ledge {me} cannot see bot at {bot}")

    def test_only_the_overhead_strip_opens(self):
        import numpy as np
        rl = self.T.ray_low
        self.assertIsNotNone(rl)
        changed = np.isfinite(self.T.low) & ~np.isfinite(rl)
        self.assertGreater(int(changed.sum()), 300)
        self.assertFalse((changed & np.isfinite(self.T.floors).any(axis=0)).any(), "a cell with a floor was opened")
        self.assertTrue((self.T.low[changed] > 5.0).all())
        ys, xs = np.nonzero(changed)
        X = self.T.x0 + (xs + 0.5) * self.T.cell
        Y = self.T.y0 + (ys + 0.5) * self.T.cell
        self.assertTrue(((X > 1.0) & (X < 7.5) & (Y > 10.0) & (Y < 24.0)).all())

    def test_ground_elsewhere_still_blocks(self):
        # a line dipping under the real ground beside the strip stays blocked
        a, b = Vec(8.0, 21.0, -10.2), Vec(8.0, 13.0, -10.2)   # 0.6 u under the -10 ground floor at x 8
        self.assertFalse(self.T.los(a + Vec(0, 0, -1.5), b + Vec(0, 0, -1.5), "see"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
