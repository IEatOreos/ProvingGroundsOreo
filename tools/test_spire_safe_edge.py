"""(custom, Nov 25) Spire's soft safe box is an aircraft's edge, whatever its 150 u soft safe sphere covers. Live
20261125-183258: a Banshee left the box's east side at 216 s, inside the sphere throughout, and died to the
return-to-battlefield countdown at 226.3 s; Terrain.kill_hit read it in bounds, so Bot.oob_escape never turned it back.
And Terrain.height_over past the level data's edge: over the map's lowest known ground, not 0.0."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import oob as O  # noqa: E402
from brain.core import Vec  # noqa: E402
from brain.terrain import Terrain, air_safes  # noqa: E402


def stand_in(vols):
    safes = {k: [v for v in vols if v["kind"] == k] for k in O.SAFES}
    return SimpleNamespace(_oob_kills=[(v, *O.bounds(v)) for v in vols if v["kind"] in O.KILLS],
                           _oob_safes=air_safes({k: vs for k, vs in safes.items() if vs}))


class SpireEdgeTests(unittest.TestCase):
    def setUp(self):
        self.vols = O.volumes("reach_35_island")
        if not self.vols:
            self.skipTest("no Spire volumes")
        self.t = stand_in(self.vols)

    def out(self, x, y, z):
        return bool(Terrain.kill_hit(self.t, [x], [y], z)[0])

    def test_the_sphere_is_left_out(self):
        self.assertEqual([v.get("shape") for v in self.t._oob_safes["soft_safe"]], ["box"])

    def test_past_the_east_side_is_out(self):
        self.assertTrue(self.out(-113.1, -370.1, -39.0))      # (where it climbed, 218 s)

    def test_the_fight_is_in(self):
        self.assertFalse(self.out(-182.7, -391.7, -55.0))
        self.assertFalse(self.out(-150.0, -390.0, -40.0))

    def test_a_lone_sphere_still_counts(self):
        only = {"soft_safe": [v for v in self.vols if v.get("shape") == "sphere"]}
        self.assertEqual(air_safes(only), only)


class NoGroundTests(unittest.TestCase):
    def test_height_past_the_data_is_over_the_lowest_ground(self):
        low = np.array([[-60.0, np.nan]])
        t = SimpleNamespace(low=low, lz=np.full((1, 1, 2), np.nan), inside=lambda x, y: True,
                            _cell=lambda p: (0, 1), _ij=lambda x, y: (0, 1), ground=lambda x, y: 0.0)
        t._ground_known = lambda x, y: Terrain._ground_known(t, x, y)
        self.assertAlmostEqual(Terrain.height_over(t, 5.0, 0.0, -43.6), 16.4)


if __name__ == "__main__":
    unittest.main()
