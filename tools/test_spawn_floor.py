"""(upstream 0.3.0, build 20261114-1215; custom tests, Nov 24) Floor where the game puts players (brain/terrain.py
Terrain.spawn_floor, exit_floor; brain/maps.py _build): people's walk round a spawn point with no floor under it, and
round a teleporter's pad and exit, becomes floor, so a bot there has a nav node under it and a way off."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import Vec  # noqa: E402
from brain.terrain import Terrain  # noqa: E402

N = 80                      # cells a side (0.25 u: a 20 u square)
HOLE = (30, 50)             # cells with no floor in the level data (a deck the export missed), 7.5 to 12.5 u


def level(path):
    """A flat floor at z 0, but no floor at all in a 5 u square in the middle."""
    floors = np.full((2, N, N), np.nan)
    floors[0] = 0.0
    floors[:, HOLE[0]:HOLE[1], HOLE[0]:HOLE[1]] = np.nan
    np.savez(path, top=np.zeros((N, N)), low=np.zeros((N, N)), floors=floors,
             walls=np.zeros((N, N, 1), np.uint64), wall_z0=-10.0, wall_bin=0.25, x0=0.0, y0=0.0, cell=0.25)


def walk(x0, x1, y, z=0.0):
    """People's LiDAR walk keys (0.25 u x 0.1 u) along a line at y."""
    return {(int(round(x / 0.25)), int(round(y / 0.25)), int(round(z / 0.1))) for x in np.arange(x0, x1, 0.25)}


class SpawnFloor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.npz = os.path.join(self.tmp.name, "heightmap.npz")
        level(self.npz)

    def tearDown(self):
        self.tmp.cleanup()

    def T(self, **k):
        return Terrain(self.npz, [], **k)

    def floor_at(self, T, p):
        j, i = (int(v) for v in T._ij(np.asarray(p.x), np.asarray(p.y)))
        col = T.floors[:, j, i]
        fin = col[np.isfinite(col)]
        return bool(fin.size and np.min(np.abs(fin - p.z)) <= 1.0)

    def test_a_spawn_with_no_floor_gets_people_s_walk_as_floor_and_a_way_off(self):
        sp = Vec(10.0, 10.0, 0.0)
        walked = set().union(*(walk(4.0, 16.0, y) for y in np.arange(9.0, 11.25, 0.25)))   # a 2 u lane through it
        old = self.T(walked=walked)
        self.assertFalse(self.floor_at(old, sp))
        self.assertFalse(old.reaches(sp, Vec(2.0, 10.0, 0.0)))
        new = self.T(walked=walked, spawns=[sp])
        self.assertTrue(self.floor_at(new, sp))
        self.assertTrue(new.reaches(sp, Vec(2.0, 10.0, 0.0)))     # off the spawn, out onto the level's floor
        self.assertTrue(new.reaches(Vec(2.0, 10.0, 0.0), sp))

    def test_nobody_walked_there_no_island(self):
        sp = Vec(10.0, 10.0, 0.0)
        far = walk(0.0, 3.0, 2.0)                                   # people's walk, but 11 u away
        T = self.T(walked=far, spawns=[sp])
        self.assertFalse(self.floor_at(T, sp))
        self.assertEqual(T.spawn_floor([sp], set()), [])

    def test_a_spawn_on_the_level_s_floor_adds_nothing(self):
        T = self.T(walked=walk(0.0, 6.0, 3.0), spawns=[Vec(3.0, 3.0, 0.0)])
        self.assertEqual(T.spawn_floor([Vec(3.0, 3.0, 0.0)], walk(0.0, 6.0, 3.0)), [])

    def test_the_fill_round_the_walk_is_floor_the_walls_still_judge(self):
        sp = Vec(10.0, 10.0, 0.0)
        lane = walk(4.0, 16.0, 10.0)
        walk_sp, fill = self.T().spawn_floor([sp], lane, split=True)
        self.assertIn((10.0, 10.0, 0.0), walk_sp)
        self.assertTrue(fill)
        T = self.T(walked=lane, spawns=[sp])
        self.assertEqual(set(T.walked_ok), set(walk_sp))           # (forced walkable: the walk and the spawn only)
        self.assertTrue(self.floor_at(T, Vec(10.0, 10.5, 0.0)))   # (the fill: floor all the same)

    def test_a_spawn_on_a_layout_s_piece_adds_nothing(self):
        """(custom, Nov 24) After the pieces: a Forge layout's floor is its pieces (The Cage: 10,864 cells before)."""
        deck = [("m", [-2.5, -2.5, 0.0, 2.5, -2.5, 0.0, 2.5, 2.5, 0.0, -2.5, 2.5, 0.0])]       # a 5 u floor, facing up
        piece = ((10.0, 10.0, 0.0), ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), (-2.5, -2.5, 0.0),
                 (2.5, 2.5, 0.0), "deck", deck)
        lane = walk(4.0, 16.0, 10.0)
        T = self.T(walked=lane, spawns=[Vec(10.0, 10.0, 0.0)], blocks=[piece])
        self.assertTrue(self.floor_at(T, Vec(10.0, 10.0, 0.0)))
        self.assertEqual(T.walked_ok, [])

    def test_floor_added_after_the_pieces_keeps_their_slopes_with_their_levels(self):
        T = self.T()
        j, i = (int(v) for v in T._ij(np.asarray(2.0), np.asarray(2.0)))
        T.slope = np.zeros(T.floors.shape, np.float32)
        T.piece = np.zeros(T.floors.shape, bool)
        T.floors[1, j, i], T.slope[1, j, i], T.piece[1, j, i] = 4.0, 0.3, True     # a piece's ramp at 4
        T._add_floor([(2.0, 2.0, 2.0)], more=True, forced=False)                   # walked floor between
        self.assertEqual(T.floors.shape[0], 3)
        self.assertEqual(list(T.floors[:, j, i]), [0.0, 2.0, 4.0])
        self.assertEqual([round(float(v), 2) for v in T.slope[:, j, i]], [0.0, 0.0, 0.3])
        self.assertEqual(list(T.piece[:, j, i]), [False, False, True])
        self.assertEqual(T.slope.shape, T.floors.shape)

    def test_a_teleporter_exit_s_walked_cells_are_floor_within_3_u(self):
        T = self.T()
        ex = Vec(10.0, 10.0, 0.0)
        cells = T.exit_floor([ex], walk(4.0, 16.0, 10.0) | walk(4.0, 16.0, 10.0, z=2.0))
        xs = sorted(round(c[0], 2) for c in cells)
        self.assertEqual((xs[0], xs[-1]), (7.0, 13.0))              # within EXIT_FLOOR_R of the exit
        self.assertTrue(all(abs(c[2]) < 1e-9 for c in cells))       # and EXIT_FLOOR_DZ of its height: not the 2 u row
        new = self.T(walked=walk(4.0, 16.0, 10.0), exits=[ex])
        self.assertTrue(self.floor_at(new, ex))
        self.assertIn((10.0, 10.0, 0.0), new.walked_ok)            # (walkable whatever the wall bits say: _build_nav)


if __name__ == "__main__":
    unittest.main()
