"""(custom, Nov 18) Lifts a map variant's layout does not have. The owner's bug report "Bots stuck on damnation" (Damnation
Anniversary, reach_cex_damnation v08b84b0d): its .mvar has the tall grav lift, not the short one, and three bots stood in
the short one's spot 105-157 s each, waiting for a push. brain/maps.py layout_lifts / off_gone_pads leave such a lift and
its rides out; tools/lidar_rides.py layout the same for LiDAR runs and the simulator; Bot.ride_lift gives up on a column
that does not lift it (LIFT_DEAD_S) and leaves its take-offs (LIFT_DEAD_BAN).

    python\\python.exe -I -m unittest tools.test_layout_lifts
"""
import math
import os
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from brain import maps  # noqa: E402
from brain.bot import LIFT_DEAD_BAN, LIFT_DEAD_S, Bot  # noqa: E402
from brain.core import Action, PlayerState, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

DAMNATION = "reach_cex_damnation/variants/v08b84b0d"
SHORT, TALL = (-7.291, -7.419, -0.199), (2.49, -3.798, 0.179)


def piece(name, x, y, z):
    return [name, x, y, z, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]


class LayoutTests(unittest.TestCase):
    FEATS = [dict(kind="lift", name="short_lift", pos=[0.0, 0.0, 0.0], group="crates"),
             dict(kind="lift", name="gravity_lift", pos=[10.0, 0.0, 0.0], group="crates"),
             dict(kind="launcher", name="inv_mancannon", pos=[20.0, 0.0, 0.0], group=None),   # (a netgame flag's)
             dict(kind="lift", name="elevator", pos=[30.0, 0.0, 0.0], group="machines"),
             dict(kind="weapon", name="dmr", pos=[0.5, 0.0, 0.0], group="crates")]

    def test_a_lift_with_no_piece_on_its_pad_is_gone(self):
        v = dict(pieces=[piece("crate_a", 5, 5, 0), piece("gravity_lift_blue", 10.3, 0.2, 0.1)])
        keep, gone = maps.layout_lifts(self.FEATS, v, placed={"crate_a", "short_lift", "gravity_lift"})
        self.assertEqual(gone, [("short_lift", [0.0, 0.0, 0.0])])
        self.assertEqual([f["name"] for f in keep], ["gravity_lift", "inv_mancannon", "elevator", "dmr"])

    def test_no_layout_or_none_of_the_bases_objects_keeps_all(self):
        self.assertEqual(maps.layout_lifts(self.FEATS, None), (self.FEATS, []))
        v = dict(pieces=[piece("forge_block", 5, 5, 0)])               # (a layout read without the scenario's)
        self.assertEqual(maps.layout_lifts(self.FEATS, v, placed={"crate_a"}), (self.FEATS, []))

    def test_rides_from_a_gone_pad_are_dropped(self):
        gone = [("short_lift", [0.0, 0.0, 0.0])]
        ride = dict(take_off=[0.0, 0.1, 0.0], land=[1.8, -1.6, 3.4], ride=True)
        up = dict(take_off=[1.0, 0.5, 0.0], land=[2.0, 0.5, 3.4])        # a climb of 3.4 from by its base
        hop = dict(take_off=[1.0, 0.5, 0.0], land=[2.5, 0.5, 0.8])       # a hop up 0.8: a jump, kept
        far = dict(take_off=[10.0, 0.0, 0.0], land=[11.0, 0.0, 3.4], ride=True)
        self.assertEqual(maps.off_gone_pads([ride, up, hop, far], gone), [hop, far])
        self.assertEqual(maps.off_gone_pads([ride], []), [ride])


@unittest.skipUnless(os.path.isdir(ROOT / "maps" / DAMNATION), "no Damnation Anniversary data")
class DamnationTests(unittest.TestCase):
    def test_the_short_lift_is_gone_the_tall_one_kept(self):
        m = maps.get_map(DAMNATION)
        lifts = [f["name"] for f in m["features"] if f.get("kind") == "lift"]
        self.assertEqual(lifts, ["tall_grav_lift"])
        T = maps.terrain(m)
        near = lambda k, p: math.hypot(k["take_off"][0] - p[0], k["take_off"][1] - p[1]) < 2.0
        rises = lambda k: k["land"][2] - k["take_off"][2] >= 2.0
        self.assertFalse([k for _, _, k, _ in T.hjumps if near(k, SHORT) and rises(k)])
        self.assertTrue([k for _, _, k, _ in T.hjumps if near(k, TALL) and rises(k)])
        base = maps.get_map("reach_cex_damnation")             # (the base map keeps both)
        self.assertEqual(sorted(f["name"] for f in base["features"] if f.get("kind") == "lift"),
                         ["short_grav_lift", "tall_grav_lift"])

    def test_lidar_and_the_simulator_push_only_the_tall_lift(self):
        import lidar_rides
        self.assertEqual([o["name"] for o in lidar_rides.layout(DAMNATION)["objects"]], ["tall_grav_lift"])
        self.assertEqual(sorted(o["name"] for o in lidar_rides.layout("reach_cex_damnation")["objects"]),
                         ["short_grav_lift", "tall_grav_lift"])


class Floor:
    """A floor at z 0 with a lift's take-off at the origin (a people's ride to (2, 0, 3.4))."""
    def __init__(s):
        s.hjumps = [((0, 0, 0), (0, 0, 1), dict(take_off=[0.0, 0.0, 0.0], land=[2.0, 0.0, 3.4], ride=1), 3.0)]


class DeadLiftTests(unittest.TestCase):
    def bot(self):
        b = Bot(0, 0, make_profile("strong", "rusher", random.Random(3)), {"name": "reach_test", "features": []},
                random.Random(5))
        b._terrain, b.notes = Floor(), []
        return b

    def ride(self, b, zs, dt=0.1):
        """Rides from t 0 in the column's middle at heights zs, a tick each: (ticks ridden, last answer)."""
        b.lift_ride, b.lift_from = (Vec(0.0, 0.0, 0.0), Vec(2.0, 0.0, 3.4), 0.0), (0.0, (0.0, 0.0))
        for n, z in enumerate(zs):
            b.now = n * dt
            me = PlayerState(0, 0, "bot", Vec(0.1, 0.0, z))
            if not b.ride_lift(me, Action()):
                return n, False
        return len(zs), True

    def test_not_lifted_gives_up_and_leaves_the_take_off(self):
        b = self.bot()
        n, on = self.ride(b, [0.0] * 200)
        self.assertFalse(on)
        self.assertAlmostEqual(n * 0.1, LIFT_DEAD_S, delta=0.25)          # (not the 12 s ride limit)
        f = b.jump_fails[(0.0, 0.0)]
        self.assertEqual(f[0], 2)
        self.assertAlmostEqual(f[1], n * 0.1 + LIFT_DEAD_BAN, delta=0.01)
        self.assertIn("lift: in it and not lifted, no lift here", b.notes)

    def test_a_working_lift_rides_on(self):
        b = self.bot()
        n, on = self.ride(b, [min(3.0, 0.5 * k) for k in range(60)])      # up at once, then held at the top
        self.assertTrue(on)
        self.assertFalse(getattr(b, "jump_fails", {}))


if __name__ == "__main__":
    unittest.main()
