"""Gravity lifts and man cannons the owner draws in the LiDAR view (custom, Nov 9: brain/maps.py owner_rides,
owner_ride_links, owner_ride_pads; tools/spots.py "ride")."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brain import maps                         # noqa: E402
from brain.core import Vec                     # noqa: E402

HEADLONG = "reach_cex_headlong"
HAVE = os.path.exists(os.path.join(maps.ROOT, HEADLONG, "heightmap.npz"))


class PadTests(unittest.TestCase):
    def test_pads_and_links(self):
        rides = [dict(name="Back lift", kind="lift", take_off=[1.0, 2.0, 3.0], land=[1.5, 2.5, 9.0]),
                 dict(name="Cannon", kind="cannon", take_off=[10.0, 0.0, 3.0], land=[30.0, 0.0, 8.0])]
        feats = [dict(kind="launcher", name="its own cannon", pos=[10.5, 0.2, 3.1])]
        with mock.patch.object(maps, "owner_rides", lambda nm: rides):
            out = maps.owner_ride_pads(feats, ["x"])
            links = maps.owner_ride_links(["x"])
        self.assertEqual(len(out), 2)                        # the cannon already has its marker: no second one
        self.assertEqual(out[1], dict(kind="lift", name="Back lift", pos=[1.0, 2.0, 3.0], owner=True))
        self.assertEqual([(k["ride"], k["human"], k["take_off"], k["land"]) for k in links],
                         [(1, 1, [1.0, 2.0, 3.0], [1.5, 2.5, 9.0]), (1, 1, [10.0, 0.0, 3.0], [30.0, 0.0, 8.0])])
        from brain.terrain import jump_ways
        self.assertTrue(all(jump_ways(k) == "one-way" for k in links))

    def test_malformed_rides_left_out(self):
        import json
        import tempfile
        d = tempfile.mkdtemp(prefix="rides_")
        os.makedirs(os.path.join(d, "m"))
        with open(os.path.join(d, "m", maps.OWNER_RIDES), "w", encoding="utf-8") as f:
            json.dump(dict(rides=[dict(kind="lift", take_off=[0, 0, 0], land=[0, 0, 5]), dict(kind="jetpack", take_off=[0, 0, 0],
                                  land=[1, 1, 1]), dict(kind="cannon", take_off=[0, 0], land=[1, 1, 1]), "junk"]), f)
        with mock.patch.object(maps, "ROOT", d):
            self.assertEqual([r["kind"] for r in maps.owner_rides("m")], ["lift"])
            self.assertEqual(maps.owner_rides("none"), [])


class CannonTests(unittest.TestCase):
    """(Nov 13: "Do bots use man cannons much? I've seen on adrift halo 4 they've never used them") A drawn man cannon
    is a launch, by its airtime, and a bot rides it: onto the pad, thrown, on for the landing (Bot.ride_cannon)."""

    def test_a_cannon_link_is_a_launch_by_its_airtime(self):
        rides = [dict(name="Lift", kind="lift", take_off=[1.0, 2.0, 3.0], land=[1.5, 2.5, 9.0]),
                 dict(name="Cannon", kind="cannon", take_off=[10.0, 0.0, 3.0], land=[25.0, 0.0, 3.0])]
        with mock.patch.object(maps, "owner_rides", lambda nm: rides):
            lift, cannon = maps.owner_ride_links(["x"])
        self.assertNotIn("launch", lift)
        self.assertEqual((cannon["launch"], cannon["air_s"]), (1, 2.0))     # 15 u at 7.5 u/s

    def bot(self):
        import random
        from brain.bot import Bot
        from brain.profiles import make_profile
        b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), {"name": "h4_test"}, random.Random(5))
        b.notes = []
        return b

    def ride(self, b, x, z, now):
        from brain.core import Action
        b.now, act = now, Action()
        me = mock.Mock(pos=Vec(x, 0.0, z))
        return b.ride_cannon(me, act), act

    def test_onto_the_pad_thrown_and_down_at_the_landing(self):
        b = self.bot()
        b.cannon_ride = (Vec(0, 0, 0), Vec(17, 0, 0), 0.0, 2.3, None)
        going, act = self.ride(b, -3.0, 0.0, 0.1)
        self.assertTrue(going)
        self.assertGreater(act.forward, 0.9)                 # (yaw 0: +x) at the pad
        self.assertFalse(act.jump)
        self.assertTrue(self.ride(b, 0.2, 0.0, 0.6)[0])
        self.assertEqual(b.cannon_ride[4], 0.6)              # on it
        going, act = self.ride(b, 6.0, 3.0, 1.4)
        self.assertTrue(going and act.forward > 0.9)         # in the air: for the landing
        self.assertTrue(b.on_cannon(1.4))
        self.assertFalse(self.ride(b, 16.4, 0.3, 2.9)[0])
        self.assertIsNone(b.cannon_ride)
        self.assertIn("man cannon: landed", b.notes)
        self.assertEqual(getattr(b, "jump_fails", {}), {})

    def test_never_thrown_leaves_that_take_off(self):
        from brain.terrain import JumpVec
        b = self.bot()
        b.cannon_ride = (Vec(0, 0, 0), Vec(17, 0, 0), 0.0, 2.3, None)
        self.ride(b, 0.1, 0.0, 0.5)
        self.assertTrue(self.ride(b, 0.1, 0.0, 4.0)[0])
        self.assertFalse(self.ride(b, 0.1, 0.0, 4.6)[0])     # 4 s on the pad, not thrown
        self.assertIn("man cannon: not thrown", b.notes)
        self.assertTrue(b.jump_blocked(JumpVec(17, 0, 0, 0.0, 0.0)))

    def test_a_ride_left_long_ago_is_dropped_with_no_verdict(self):
        b = self.bot()
        b.cannon_ride = (Vec(0, 0, 0), Vec(17, 0, 0), 0.0, 2.3, None)
        self.assertFalse(b.on_cannon(10.4))
        self.assertFalse(self.ride(b, 40.0, 0.0, 10.4)[0])
        self.assertIsNone(b.cannon_ride)
        self.assertEqual(getattr(b, "jump_fails", {}), {})


ADRIFT = "h4_ca_warhouse"


@unittest.skipUnless(os.path.exists(os.path.join(maps.ROOT, ADRIFT, maps.OWNER_RIDES))
                     and os.path.exists(os.path.join(maps.ROOT, ADRIFT, "heightmap.npz")), "Adrift's drawn cannon not here")
class AdriftCannonTests(unittest.TestCase):
    def test_the_nav_takes_the_cannon_and_the_bot_knows_it(self):
        import random
        from brain.bot import Bot
        from brain.profiles import make_profile
        from brain.terrain import JumpVec
        m = maps.get_map(ADRIFT)
        T = maps.terrain(m)
        mine = [(k, w) for f, t, k, w in T.hjumps if k.get("found_by") == "owner" and k.get("launch")]
        self.assertEqual(len(mine), 1)
        k, w = mine[0]
        self.assertLess(w, 10.0)                             # (a 17.8 u jump's 27.6 lost to the 23.9 walk round)
        n = T.nav(Vec(13.4, -12.9, 2.7), Vec(17.0, 8.0, 2.4), jump=True, human=True)
        self.assertIsInstance(n, JumpVec)
        self.assertEqual((n.sx, n.sy), tuple(k["take_off"][:2]))
        b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), m, random.Random(5))
        self.assertAlmostEqual(b.cannon_of(n), k["air_s"])


@unittest.skipUnless(HAVE, "map data not here")
class NavTests(unittest.TestCase):
    def test_a_drawn_lift_is_a_ride_the_nav_takes(self):
        import numpy as np
        import spots
        fl = np.array(spots.level_floor(HEADLONG)["points"]).reshape(-1, 3)
        a = fl[np.argmin(fl[:, 2])]                          # the lowest floor, a ride to a floor 4+ u over it nearby
        up = fl[(fl[:, 2] > a[2] + 4.0)]
        b = up[np.argmin(np.hypot(up[:, 0] - a[0], up[:, 1] - a[1]))]
        ride = dict(name="Test lift", kind="lift", take_off=[round(float(v), 2) for v in a], land=[round(float(v), 2) for v in b])
        with mock.patch.object(maps, "owner_rides", lambda nm: [ride] if nm == HEADLONG else []):
            m = maps.load_map(HEADLONG)
            T = maps._build(m, None)
        self.assertTrue(any(f.get("owner") and f["kind"] == "lift" and f["pos"] == ride["take_off"] for f in m["features"]))
        mine = [(f, t, k) for f, t, k, w in T.hjumps if k.get("found_by") == "owner"]
        self.assertEqual(len(mine), 1)
        f, t, k = mine[0]
        self.assertEqual((f, t), (T._node(Vec(*ride["take_off"])), T._node(Vec(*ride["land"]))))
        self.assertFalse(any(k2.get("found_by") == "owner" and f2 == t for f2, t2, k2, w in T.hjumps))   # one way only


if __name__ == "__main__":
    unittest.main()
