"""Bots crouch on floor people walked crouched only under a low ceiling (maps.terrain CROUCH_LOW_ONLY,
Terrain.low_overhead). The owner, Nov 8: "why do the demons crouch so much now": the live LiDAR had painted his fight
crouches on Haven, 535 cells, 11 under a low ceiling.

Run: python tools/test_crouch_floor.py
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import maps
from brain.maps import get_map, terrain
from brain.terrain import crouch_key

HAVEN = "h4_wraparound"
LIDAR = os.path.join(maps.ROOT, HAVEN, "lidar.json")


@unittest.skipUnless(os.path.exists(LIDAR) and os.path.exists(os.path.join(maps.ROOT, HAVEN, "heightmap.npz")),
                     "no local Haven LiDAR")
class CrouchFloorTests(unittest.TestCase):
    def setUp(self):
        maps.CROUCH_LOW_ONLY = True

    def tearDown(self):
        maps.CROUCH_LOW_ONLY = True

    def painted(self):
        d = json.load(open(LIDAR, encoding="utf-8"))
        return [(x * 0.25, y * 0.25, z * 0.1) for x, y, z, k, n in d.get("walk", []) if k == 3]

    def test_only_cells_under_a_low_ceiling_make_bots_crouch(self):
        pts = self.painted()
        T = terrain(get_map(HAVEN))
        low = T.low_overhead(pts)
        self.assertEqual(T.crouch_cells, {crouch_key(*p) for p, ok in zip(pts, low) if ok})
        self.assertLess(len(T.crouch_cells), max(1, len({crouch_key(*p) for p in pts})) * 0.2)

    def test_low_overhead_empty(self):
        self.assertEqual(len(terrain(get_map(HAVEN)).low_overhead([])), 0)


if __name__ == "__main__":
    unittest.main()
