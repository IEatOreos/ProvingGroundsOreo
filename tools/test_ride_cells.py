"""(custom, Nov 23) The drive-path refresh's floors found all at once (brain/terrain.py _nodes_at, _ride_cells; add_rides
only the samples not seen before): the very nodes the one-at-a-time _node_at found. The owner's Boneyard 8v8
(20261124-003150): "a couple of long hangups", 7 s every minute with every bot stopped; "Yes, fix it"."""
import random
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.terrain import NAV_CELL, Terrain      # noqa: E402


class Grid:
    """A small stand-in Terrain: 3 floor levels, gaps (no floor), ties between levels, some floor not walkable."""
    _cell, inside, _node_at, _nodes_at, _ride_cells, add_rides = (Terrain._cell, Terrain.inside, Terrain._node_at,
                                                                  Terrain._nodes_at, Terrain._ride_cells, Terrain.add_rides)

    def __init__(s, seed=1):
        rng = np.random.default_rng(seed)
        s.L, s.nh, s.nw, s.x0, s.y0 = 3, 40, 40, 0.0, 0.0
        s.window = (0.0, 0.0, s.nw * NAV_CELL, s.nh * NAV_CELL)
        s.lz = rng.choice([0.0, 0.3, 2.0, 2.4, np.nan], size=(s.L, s.nh, s.nw)).astype(np.float32)
        s.lz[1, ::5, ::5] = s.lz[0, ::5, ::5]                  # (ties: the lowest layer wins)
        s.lwalk = np.isfinite(s.lz) & (rng.random((s.L, s.nh, s.nw)) > 0.1)

    def _vreset(s):
        pass


def old_cells(T, drive):
    foot = [(dx * NAV_CELL, dy * NAV_CELL) for dx in range(-2, 3) for dy in range(-2, 3) if dx * dx + dy * dy <= 5]
    return {n for c in drive for dx, dy in foot if T.inside(c[0] + dx, c[1] + dy)
            for n in [T._node_at(c[0] + dx, c[1] + dy, c[2], tol=0.6)] if n is not None and T.lwalk[n]}


def samples(n, seed):
    rng = random.Random(seed)
    return [[rng.uniform(-1, 11), rng.uniform(-1, 11), rng.choice([0.1, 0.5, 2.1, 2.9])] for _ in range(n)]


class RideCells(unittest.TestCase):
    def test_the_same_nodes_as_one_at_a_time(self):
        for seed in range(4):
            T, drive = Grid(seed), samples(400, seed)
            self.assertEqual(T._ride_cells(drive), old_cells(T, drive), seed)

    def test_each_point_as_node_at(self):
        T = Grid(7)
        pts = samples(300, 7)
        ok, l, j, i = T._nodes_at([p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts], tol=0.6)
        for k, p in enumerate(pts):
            want = T._node_at(p[0], p[1], p[2], tol=0.6)
            self.assertEqual((int(l[k]), int(j[k]), int(i[k])) if ok[k] else None, want)

    def test_only_new_samples_and_a_reset_keeps_them(self):
        T = Grid(3)
        a, b = samples(200, 1), samples(200, 2)
        T.add_rides(a, {})
        first = set(T.drive_paint)
        self.assertEqual(first, old_cells(T, a))
        T.add_rides(a + b, {})                                 # (the next minute: everything, the new ones too)
        self.assertEqual(set(T.drive_paint), old_cells(T, a + b))
        self.assertEqual(len(T._ride_done), len({tuple(c) for c in a + b}))
        T.drive_paint = []                                     # (a repaint's reset: apply_paint)
        T.add_rides(a + b, {})
        self.assertEqual(set(T.drive_paint), old_cells(T, a + b))


if __name__ == "__main__":
    unittest.main()
