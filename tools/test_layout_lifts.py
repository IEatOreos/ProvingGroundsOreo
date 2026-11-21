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


@unittest.skipUnless(os.path.isdir(ROOT / "maps" / DAMNATION), "no Damnation Anniversary data")
class LiftChanceTests(unittest.TestCase):
    """(Nov 18, "CAn we just make it to where the bots take the lifts more? Like add a scoring chance") Bot.lift_detour."""

    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.m = maps.get_map(DAMNATION)
        cls.T = maps.terrain(cls.m)
        ls, js, is_ = np.nonzero(cls.T.reach & cls.T.lwalk)
        pts = [cls.T._center(int(ls[k]), int(js[k]), int(is_[k])) for k in range(0, len(ls), max(1, len(ls) // 400))]
        rng = random.Random(1)
        low, high = [p for p in pts if p.z < 1.0], [p for p in pts if p.z > 2.5]
        cls.trips = [(rng.choice(low), rng.choice(high)) for _ in range(120)]

    def bot(self, roll):
        b = Bot(0, 0, make_profile("strong", "rusher", random.Random(3)), self.m, random.Random(5))
        b._terrain, b.notes, b.now = self.T, [], 0.0
        b.rng.random = lambda: roll
        return b

    def test_won_rolls_go_up_the_tall_lift(self):
        took = []
        for a, g in self.trips:
            r = self.bot(0.0).lift_detour(PlayerState(0, 0, "bot", a), g)
            if r is not None:
                took.append(r)
        self.assertGreater(len(took), len(self.trips) // 6)        # (88 of 300 such trips offline)
        self.assertTrue(all(math.hypot(t.x - TALL[0], t.y - TALL[1]) < 2.0 for t in took))

    def test_a_lost_roll_holds_and_the_ride_starts_at_the_take_off(self):
        a, g = next((a, g) for a, g in self.trips if self.bot(0.0).lift_detour(PlayerState(0, 0, "bot", a), g))
        b = self.bot(0.99)
        self.assertIsNone(b.lift_detour(PlayerState(0, 0, "bot", a), g))
        b.rng.random = lambda: 0.0
        b.now = 5.0                                                # (the same goal, inside LIFT_ROLL_S: no new roll)
        self.assertIsNone(b.lift_detour(PlayerState(0, 0, "bot", a), g))
        b = self.bot(0.0)
        take = b.lift_detour(PlayerState(0, 0, "bot", a), g)
        self.assertIs(b.lift_detour(PlayerState(0, 0, "bot", take), g), True)
        self.assertEqual(b.lift_ride[0].x, TALL[0])
        self.assertIsNone(b.via_lift)

    def test_no_roll_for_a_goal_not_above(self):
        a = next(a for a, _ in self.trips)
        self.assertIsNone(self.bot(0.0).lift_detour(PlayerState(0, 0, "bot", a), a + Vec(8.0, 0.0, 0.0)))


class MapRideTests(unittest.TestCase):
    """maps.map_lift_rides: a lift nobody rode gets its solved ride in matches (Launch Station had none)."""

    @unittest.skipUnless(os.path.exists(ROOT / "maps" / "reach_45_launch_station" / "phantoms.json")
                         and os.path.exists(ROOT / "maps" / "reach_45_launch_station" / "heightmap.npz"), "no data")
    def test_launch_stations_lift_is_in_the_nav(self):
        T = maps.terrain(maps.get_map("reach_45_launch_station"))
        self.assertTrue([k for _, _, k, _ in T.hjumps if k.get("found_by") == "map" and k.get("ride")])

    @unittest.skipUnless(os.path.isdir(ROOT / "maps" / DAMNATION), "no Damnation Anniversary data")
    def test_a_ridden_lift_or_a_gone_one_gets_none(self):
        T = maps.terrain(maps.get_map(DAMNATION))
        self.assertFalse([k for _, _, k, _ in T.hjumps if k.get("found_by") == "map"])

    def test_not_a_lift_game(self):
        self.assertEqual(maps.map_lift_rides("bloodgulch", None, []), [])


CAGE = "reach_forge_halo/variants/vd7eaef53"


class ForgePadTests(unittest.TestCase):
    """(Nov 18, "What about the cage the forge map?") maps.forge_pads / forge_throws: Forge-placed cannons and lifts."""

    def test_forge_pieces_become_markers(self):
        v = dict(pieces=[piece("ff_man_cannon_forge", 1, 2, 3), piece("ff_grav_lift", 10, 0, 0),
                         piece("heh_red_airlift_paneldoor", 20, 0, 0), piece("ff_block", 30, 0, 0),
                         piece("gravity_lift", 40.2, 0, 0)])
        old = [dict(kind="lift", name="gravity_lift", pos=[40.0, 0.0, 0.0], group="crates")]
        out = maps.forge_pads(old, v)
        self.assertEqual([(f["kind"], f["name"]) for f in out[1:]], [("launcher", "ff_man_cannon_forge"),
                                                                     ("lift", "ff_grav_lift")])
        self.assertEqual(out[1]["group"], "forge")

    def test_a_long_link_off_a_forge_cannon_is_its_throw(self):
        feats = [dict(kind="launcher", name="ff_man_cannon_forge", pos=[0.0, 0.0, 0.0], group="forge")]
        throw = dict(take_off=[0.0, 0.8, 0.1], land=[0.6, -14.7, 2.5], air_s=3.17)
        hop = dict(take_off=[0.0, 0.8, 0.1], land=[0.0, -0.4, 0.9])
        far = dict(take_off=[5.0, 0.0, 0.0], land=[5.0, -15.0, 0.0])
        out = maps.forge_throws([throw, hop, far], feats)
        self.assertEqual((out[0]["ride"], out[0]["launch"], out[0]["air_s"]), (1, 1, 3.17))
        self.assertEqual(out[1:], [hop, far])
        self.assertEqual(maps.forge_throws([throw], [dict(feats[0], group="crates")]), [throw])   # (a base map's)


@unittest.skipUnless(os.path.isdir(ROOT / "maps" / CAGE), "no The Cage data")
class CageTests(unittest.TestCase):
    TAKE, LAND = (17.8, 181.6, 35.5), (18.4, 166.1, 37.9)

    @classmethod
    def setUpClass(cls):
        cls.m = maps.get_map(CAGE)
        cls.T = maps.terrain(cls.m)

    def test_the_cannon_is_a_marker_and_its_throw_a_launch(self):
        self.assertEqual([f["name"] for f in self.m["features"] if f.get("group") == "forge"], ["ff_man_cannon_forge"])
        throws = [(k, w) for _, _, k, w in self.T.hjumps if k.get("launch")]
        self.assertEqual(len(throws), 1)
        k, w = throws[0]
        self.assertLess(math.dist(k["take_off"][:2], self.TAKE[:2]), 0.2)
        self.assertLess(w, 10.0)                                # (by its 3.2 s airtime: 24 as a 15.5 u jump)

    def bot(self):
        b = Bot(0, 0, make_profile("strong", "rusher", random.Random(3)), self.m, random.Random(5))
        b._terrain, b.notes, b.now = self.T, [], 0.0
        b.rng.random = lambda: 0.0
        return b

    def test_the_nav_and_the_chance_ride_it(self):
        a, g = Vec(18.2, 184.6, 35.1), Vec(16.7, 168.8, 37.9)   # (north of the pad to past its landing)
        b = self.bot()
        pos = a                                                 # (the nav's own way: the throw, ridden as a cannon)
        for _ in range(10):
            nxt = self.T.nav(pos, g, human=True)
            if hasattr(nxt, "sx"):
                break
            pos = nxt
        self.assertTrue(hasattr(nxt, "sx"))
        self.assertAlmostEqual(b.cannon_of(nxt), 3.17)
        take = b.lift_detour(PlayerState(0, 0, "bot", a), g)
        self.assertLess(math.dist((take.x, take.y), self.TAKE[:2]), 0.2)
        self.assertIs(b.lift_detour(PlayerState(0, 0, "bot", take), g), True)
        self.assertIsNotNone(b.cannon_ride)
        self.assertIn("lift chance: on the man cannon", b.notes)


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
