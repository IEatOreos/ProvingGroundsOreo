"""(upstream 0.3.0, builds 20261115-0350 and 20261116-2330; custom tests, Nov 24) A layout built past its level's
grid: the grid grows out to its pieces within the window (brain/terrain.py Terrain.__init__), never to the whole
window, never to a sky warship (GROW_PIECE_R) or past GROW_MAX, and add_faces takes a piece with no surface left."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import Vec  # noqa: E402
from brain.terrain import Terrain  # noqa: E402

N = 80                      # cells a side (0.25 u: the level is 0 to 20 u)
AXES = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def level(path):
    floors = np.full((2, N, N), np.nan)
    floors[0] = 0.0
    np.savez(path, top=np.zeros((N, N)), low=np.zeros((N, N)), floors=floors,
             walls=np.zeros((N, N, 1), np.uint64), wall_z0=-10.0, wall_bin=0.25, x0=0.0, y0=0.0, cell=0.25)


def deck(x, y, half, z=0.0, up=True):
    """A flat square piece at (x, y, z), its one face up (a floor) or down (an underside: no surface)."""
    q = [-half, -half, 0.0, half, -half, 0.0, half, half, 0.0, -half, half, 0.0]
    if not up:
        q = q[9:12] + q[6:9] + q[3:6] + q[0:3]
    return ((x, y, z), AXES, (-half, -half, 0.0), (half, half, 0.0), "deck", [("m", q)])


class GridGrowth(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.npz = os.path.join(self.tmp.name, "heightmap.npz")
        level(self.npz)

    def tearDown(self):
        self.tmp.cleanup()

    def T(self, blocks=(), window=(-100.0, -100.0, 120.0, 120.0)):
        return Terrain(self.npz, [], blocks=list(blocks), window=window)

    def test_no_piece_past_the_level_the_same_grid(self):
        T = self.T([deck(10.0, 10.0, 2.0, z=1.0)])
        self.assertEqual((T.h, T.w, T.x0, T.y0), (N, N, 0.0, 0.0))
        self.assertEqual(T.full, (0.0, 0.0, 20.0, 20.0))
        cut = self.T(window=(4.0, 4.0, 16.0, 16.0))                       # (a window inside the level: cut, as before)
        self.assertEqual((cut.h, cut.w, cut.x0, cut.y0), (48, 48, 4.0, 4.0))

    def test_the_grid_grows_to_a_piece_past_the_level_and_bots_walk_it(self):
        T = self.T([deck(30.0, 10.0, 3.0)])
        self.assertLessEqual(T.window[2], 30.0 + 3.0 * 2 ** 0.5 + 2.0 + 0.25)   # (out to the piece, not the window)
        self.assertGreater(T.window[2], 33.0)
        self.assertEqual((T.x0, T.y0, T.h), (0.0, 0.0, N))
        self.assertEqual(T.floors.shape[1:], (T.h, T.w))
        self.assertEqual(T.walls.shape[:2], (T.h, T.w))
        j, i = (int(v) for v in T._ij(np.asarray(30.0), np.asarray(10.0)))
        self.assertTrue(np.isfinite(T.floors[:, j, i]).any())
        self.assertTrue(T.reaches(Vec(29.0, 10.0, 0.0), Vec(31.0, 11.0, 0.0)))
        jj, ii = (int(v) for v in T._ij(np.asarray(33.5), np.asarray(18.0)))
        self.assertFalse(np.isfinite(T.floors[:, jj, ii]).any())           # (the grown cells: no data, as the sea)

    def test_growth_west_and_south_moves_the_origin(self):
        T = self.T([deck(-10.0, -6.0, 2.0)])
        self.assertLess(T.x0, -10.0)
        self.assertLess(T.y0, -6.0)
        j, i = (int(v) for v in T._ij(np.asarray(5.0), np.asarray(5.0)))
        self.assertEqual(T.floors[0, j, i], 0.0)                           # (the level's own cells where they were)
        self.assertEqual(T.full[2:], (20.0, 20.0))

    def test_never_past_the_window(self):
        T = self.T([deck(30.0, 10.0, 3.0)], window=(-8.0, -8.0, 24.0, 28.0))
        self.assertLessEqual(T.window[2], 24.0 + 0.25)

    def test_no_growth_to_a_sky_warship_or_a_piece_far_out(self):
        ship = deck(60.0, 10.0, 60.0, z=150.0)                            # (Condemned's corvette: 170 u)
        far = deck(400.0, 10.0, 2.0)
        T = self.T([ship, far], window=(-500.0, -500.0, 500.0, 500.0))
        self.assertEqual((T.h, T.w), (N, N))

    def test_a_piece_with_no_surface_left_builds(self):
        """His GitHub #33: every surface buried (only an underside over grown cells): the brain stopped there."""
        T = self.T([deck(30.0, 10.0, 3.0, z=2.0, up=False)])
        j, i = (int(v) for v in T._ij(np.asarray(30.0), np.asarray(10.0)))
        self.assertFalse(np.isfinite(T.floors[:, j, i]).any())
        self.assertGreater(T.w, N)


if __name__ == "__main__":
    unittest.main()
