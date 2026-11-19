"""(custom, Nov 18) A Reach Banshee's room under a soft roof (Boneyard, PwnageTV's ride in
trace_reach_70_boneyard_20261118-185212: held under 0 z by the 4.0 z soft_safe top less 2.5 u and a 1.5 u no-climb
band, 0.5-1 u over the structures' tops, its run's ground look ended 13 of 15 runs 22-29 u off, two bomb tries in 84 s).
A soft roof (a countdown over it) keeps AIR_ROOF_SOFT_M off with AIR_ROOF_SOFT_BAND of no climb; a hard one, and every
other game, as before."""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import oob as O  # noqa: E402
from brain.bot import AIR_ROOF_M, AIR_ROOF_SOFT_M  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.terrain import Terrain  # noqa: E402
from test_demon_vehicles import Act, bot  # noqa: E402


def roof_of(vols, x, y, floor=-10.0):
    """Terrain._air_roof on a one-cell stand-in whose only floor is `floor`."""
    t = SimpleNamespace(_oob_vols=vols, lz=np.full((1, 1, 1), floor), _cell=lambda p: (0, 0),
                        ground=lambda x, y: floor)
    return Terrain._air_roof(t, x, y)


class SoftRoofTests(unittest.TestCase):
    def setUp(self):
        self.vols = O.volumes("reach_70_boneyard")
        if not self.vols:
            self.skipTest("no Boneyard volumes")

    def test_boneyards_safe_top_is_soft(self):
        roof, soft = roof_of(self.vols, 285.0, 110.0)
        self.assertAlmostEqual(roof, 4.0, delta=0.05)
        self.assertTrue(soft)

    def test_a_hard_safe_zones_top_is_not(self):
        hard = [dict(copy.deepcopy(v), kind="safe") if v["kind"] == "soft_safe" else v for v in self.vols]
        roof, soft = roof_of(hard, 285.0, 110.0)
        self.assertAlmostEqual(roof, 4.0, delta=0.05)
        self.assertFalse(soft)

    def test_margins(self):
        soft = SimpleNamespace(air_roof=lambda x, y: 4.0, air_roof_soft=lambda x, y: True)
        hard = SimpleNamespace(air_roof=lambda x, y: 4.0, air_roof_soft=lambda x, y: False)
        old = SimpleNamespace(air_roof=lambda x, y: 4.0)          # (a stand-in with no soft answer: as before)
        b = bot("demon", name="reach_test")
        self.assertAlmostEqual(b.air_ceiling(0, 0, soft), 4.0 - AIR_ROOF_SOFT_M)
        self.assertAlmostEqual(b.air_ceiling(0, 0, hard), 4.0 - AIR_ROOF_M)
        self.assertAlmostEqual(b.air_ceiling(0, 0, old), 4.0 - AIR_ROOF_M)
        self.assertAlmostEqual(bot("demon", name="h4_test").air_ceiling(0, 0, soft), 4.0 - AIR_ROOF_M)   # (Reach only)

    def test_no_climb_band_under_a_soft_roof(self):
        b = bot("demon", name="reach_test")
        b._terrain = SimpleNamespace(air_roof=lambda x, y: 4.0, air_roof_soft=lambda x, y: True)
        b.T = lambda: b._terrain
        b.seat = "driver"
        me = PlayerState(0, 0, "bot", Vec(0.0, 0.0, 1.8), vehicle=77, weapon="banshee")   # (0.7 u under its 2.5 z limit)
        snap = Snapshot(50.0, [me], mode="slayer", vehicles=[dict(handle=77, kind="banshee", pos=(0.0, 0.0, 1.8))])
        act = Act(0.0, 0.3)
        b.air_roof_guard(me, act, snap)
        self.assertEqual(act.pitch, 0.3)                       # (still climbing: the soft band is 0.5 u)
        b._terrain = SimpleNamespace(air_roof=lambda x, y: 4.0, air_roof_soft=lambda x, y: False)
        act = Act(0.0, 0.3)
        b.air_roof_guard(me, act, snap)                        # (a hard roof: 1.5 z, over it: nose down)
        self.assertLess(act.pitch, 0.0)


if __name__ == "__main__":
    unittest.main()
