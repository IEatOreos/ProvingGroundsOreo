"""Teleporters by gametype label (custom, Nov 7): Gore Valley's Dominion pads held bots in Slayer ("Bots get stuck
here"); the nav keeps only the pads a mode has. And the owner's Gore Valley patrol and hot spot."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import maps                         # noqa: E402
from brain.core import Vec                     # noqa: E402

HAVE = lambda name: os.path.exists(os.path.join(maps.ROOT, name, "objects.json"))


class LabelTests(unittest.TestCase):
    def test_modes(self):
        self.assertTrue(maps.tele_in_mode(set(), None))
        self.assertFalse(maps.tele_in_mode({"dominion"}, None))
        self.assertFalse(maps.tele_in_mode({"dominion"}, "ctf"))
        self.assertTrue(maps.tele_in_mode({"dominion"}, "territories"))
        self.assertTrue(maps.tele_in_mode({"no_dom"}, None))
        self.assertFalse(maps.tele_in_mode({"no_dom"}, "territories"))
        self.assertFalse(maps.tele_in_mode({"ctf_delete"}, "ctf"))
        self.assertTrue(maps.tele_in_mode({"ctf_delete"}, "king"))

    def test_nearest_label(self):
        objs = {"netgame_flags": [dict(type="no_dom", pos=[1.1, 0.0, 0.0]), dict(type="dominion", pos=[1.0, 0.01, 0.0]),
                                  dict(type="slayer", pos=[1.0, 0.0, 0.0])]}
        self.assertEqual(maps.teleporter_tag(objs, Vec(1.0, 0.0, 0.0)), "dominion")
        self.assertIsNone(maps.teleporter_tag(objs, Vec(5.0, 0.0, 0.0)))


@unittest.skipUnless(HAVE("h4_ca_gore_valley") and HAVE("h4_ca_canyon"), "map data not here")
class MapTests(unittest.TestCase):
    def kept(self, name, mode):
        m = maps.get_map(name)
        maps.set_mode(m, mode)
        return [(round(a.x, 1), round(a.y, 1)) for a, b in m["teleporters"]], m

    def tearDown(self):
        for name in ("h4_ca_gore_valley", "h4_ca_canyon"):
            maps.set_mode(maps.get_map(name), "territories")   # (others reading the cached maps get every pad back)
            m = maps.get_map(name)
            m["teleporters"] = list(m["teleporters_all"])

    def test_gore_valley_dominion_pads_only_in_dominion(self):
        self.assertEqual(self.kept("h4_ca_gore_valley", None)[0], [])
        self.assertEqual(self.kept("h4_ca_gore_valley", "ctf")[0], [])
        self.assertEqual(len(self.kept("h4_ca_gore_valley", "territories")[0]), 2)

    def test_canyon_keeps_its_one_way_pads_outside_dominion(self):
        slayer, m = self.kept("h4_ca_canyon", None)
        self.assertEqual(sorted(slayer), [(-3.9, -30.4), (3.9, 30.3)])
        self.assertEqual(sorted(self.kept("h4_ca_canyon", "territories")[0]), [(-10.9, 21.8), (10.8, -22.0)])

    def test_gore_valley_patrol_and_hot_spot(self):
        m = maps.get_map("h4_ca_gore_valley")
        self.assertIn((Vec(9.28, 18.75, 2.43), None), m["infantry_patrols"])
        import json
        with open(os.path.join(maps.ROOT, "h4_ca_gore_valley", "positions.json"), encoding="utf-8") as f:
            rows = json.load(f)
        top = rows[0]
        self.assertEqual(top["pos"], [9.28, 18.75, 2.43])
        self.assertTrue(top.get("owner"))


@unittest.skipUnless(HAVE("h4_ca_gore_valley") and os.path.exists(os.path.join(maps.ROOT, "h4_ca_gore_valley",
                                                                                  "heightmap.npz")), "no heightmap")
class StuckSpotTests(unittest.TestCase):
    def test_no_pad_by_reds_spawn_in_slayer(self):
        m = maps.get_map("h4_ca_gore_valley")
        maps.set_mode(m, None)
        try:
            T = maps.terrain(m)
            p = Vec(-1.05, -6.1, -1.08)
            for z in m["zones"].zones:
                w = T.nav(p, z.center)
                self.assertFalse(w is not None and (w - Vec(-1.03, -6.09, w.z)).flat() < 0.05, z.name)
        finally:
            m["teleporters"] = list(m["teleporters_all"])
            maps._TERRAIN.pop(m["name"], None)


if __name__ == "__main__":
    unittest.main()
