"""Terrain.learn_shot_through learns no shoot-through inside a tall solid run (LEARN_SOLID_BELOW / ABOVE): a pillar is
not a railing. The owner's report, Haven 20261109-192854: "Bots try to shoot through this massive pillar".

Run: python tools/test_learn_shot_through.py
"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import Vec
from brain.terrain import Terrain


def grid(lo, hi):
    """A 10 x 10 u map (0.25 u cells), floor z 0, one wall across x = 5 u from height lo to hi."""
    T = Terrain.__new__(Terrain)
    T.x0 = T.y0 = 0.0
    T.cell, T.h, T.w = 0.25, 40, 40
    T.window = (0.0, 0.0, 10.0, 10.0)
    T.wall_z0, T.wall_bin = -1.0, 0.125
    T.walls = np.zeros((40, 40, 1), np.uint64)
    for b in range(int((lo - T.wall_z0) / T.wall_bin), int((hi - T.wall_z0) / T.wall_bin) + 1):
        T.walls[:, 20, 0] |= np.uint64(1) << np.uint64(b)
    T.floors = np.full((1, 40, 40), np.nan, np.float32)
    T.shot_los = lambda a, b: False               # (the round's line reads blocked: the case learning is for)
    return T


class LearnShotThroughTests(unittest.TestCase):
    def learn3(self, T):
        a, b = Vec(1.0, 5.0, 0.0), Vec(9.0, 5.0, 0.0)
        return [c for _ in range(3) for c in T.learn_shot_through(a, b)]

    def test_a_pillar_is_never_learned_shoot_through(self):
        self.assertEqual(self.learn3(grid(-1.0, 3.0)), [])

    def test_a_railing_is_learned_as_before(self):
        learned = self.learn3(grid(0.4, 0.8))         # (waist high: the round's line at eye height 0.62 crosses it)
        self.assertTrue(learned)
        self.assertTrue(all(c[4] == 0 for c in learned))


if __name__ == "__main__":
    unittest.main()
