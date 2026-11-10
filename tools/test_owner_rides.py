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
