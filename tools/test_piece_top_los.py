"""(custom, Nov 22) A line over a placed piece's real wall top passes it (Terrain._ray, piece_top, PIECE_TOP_EPS). Wall
bins are steps (here 0.25 u, Asylum's): a face topping out mid-step filled the whole step, and a line just over the
top of a Forge platform or lip read as blocked. The owner: "If I can see any part of a spartan as long as its not
through a glass wall, I can shoot them". Live Asylum 20261122-195647: the model's wrongly blocked kill lines 54 -> 42."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import Vec  # noqa: E402
from brain.terrain import Terrain  # noqa: E402

IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
# a wall piece across y at x = 10, 0.5 thick, its top at 0.6 (inside the 0.5-0.75 bin)
WALL = [("metal", [-0.25, -4, 0.0, -0.25, 4, 0.0, -0.25, 4, 0.6, -0.25, -4, 0.6]),
        ("metal", [0.25, -4, 0.0, 0.25, -4, 0.6, 0.25, 4, 0.6, 0.25, 4, 0.0]),
        ("metal", [-0.25, -4, 0.6, -0.25, 4, 0.6, 0.25, 4, 0.6, 0.25, -4, 0.6])]     # (its top: a floor)


def flat():
    T = Terrain.__new__(Terrain)
    T.x0 = T.y0 = 0.0
    T.cell, T.h, T.w = 0.25, 32, 80
    T.window = (0.0, 0.0, 20.0, 8.0)
    T.wall_z0, T.wall_bin = -1.0, 0.25
    T.walls = np.zeros((32, 80, 1), np.uint64)
    T.floors = np.zeros((1, 32, 80), np.float32)
    T.top = np.zeros((32, 80), np.float32)
    T.low = np.zeros((32, 80), np.float32)
    T.slope = T.piece = None
    T.blocked = set()
    return T


def ray(T, z):
    """A level line at height z across the wall (EYE-free: from z to z)."""
    return T._ray(Vec(4.0, 4.1, z), Vec(16.0, 4.1, z), 0.0, "shot", source_height=0.0)


class PieceTopTests(unittest.TestCase):
    def test_over_the_real_top_passes(self):
        T = flat()
        T.add_faces([((10.0, 4.0, 0.0), IDENT, WALL)])
        self.assertTrue(ray(T, 0.70))           # (over 0.6, inside the 0.5-0.75 step the wall filled)
        self.assertFalse(ray(T, 0.55))          # (under it: the wall)
        self.assertFalse(ray(T, 0.3))

    def test_the_step_alone_blocked_before(self):
        T = flat()
        T.add_faces([((10.0, 4.0, 0.0), IDENT, WALL)])
        T.piece_top = None                      # (as before the fix)
        self.assertFalse(ray(T, 0.70))

    def test_the_levels_own_wall_stays(self):
        T = flat()
        b = int(np.floor((0.70 - T.wall_z0) / T.wall_bin))      # the level's own wall in the same cells, at 0.7
        T.walls[:, 39:42, 0] |= np.uint64(1) << np.uint64(b)
        T.add_faces([((10.0, 4.0, 0.0), IDENT, WALL)])
        self.assertFalse(ray(T, 0.70))


if __name__ == "__main__":
    unittest.main()
