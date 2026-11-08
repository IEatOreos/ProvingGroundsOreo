"""The owner's Halo 4 reports of Nov 8 (custom): boarders froze by a tilted Ghost (Canyon), a Forge canvas read as a
built-in map by its one camera (Ravine), and Cliffside's hot spots and patrol areas."""
import json
import os
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import maps, profiles, variants                 # noqa: E402
from brain.bot import BOARD_UPRIGHT, Bot, Order            # noqa: E402
from brain.core import PlayerState, Snapshot, Vec          # noqa: E402

RAVINE = "h4_ca_forge_ravine/variants/vc736941c"


class TiltedBoardTests(unittest.TestCase):
    def chosen(self, up_z):
        b = Bot(0, 0, profiles.make_profile("strong", "rusher", random.Random(3)), {"name": "h4_test"},
                random.Random(5))
        b.order, b.notes = Order("mid", Vec(80, 0, 0)), []
        v = dict(handle=30, kind="storm_ghost", pos=(3.0, 0.0, 0.0), fwd=(1.0, 0.0, 0.0), up=(0.0, 0.8, up_z),
                 occupied=True, team=1, riders=1)
        me = PlayerState(0, 0, "me", Vec(0, 0, 0))
        him = PlayerState(1, 1, "him", Vec(3.0, 0.0, 0.0), vehicle=30)
        scores = {("roam", None): 0.5}
        b.board_check(me, Snapshot(10.0, [me, him], vehicles=[v]), scores)
        return ("board", 30) in scores

    def test_a_tilted_vehicle_is_not_boarded(self):
        for z in (0.43, 0.5, 0.57):          # (Canyon's Ghost on its ledge: 0.43-0.57)
            self.assertFalse(self.chosen(z), z)

    def test_an_upright_one_is(self):
        self.assertTrue(self.chosen(0.95))
        self.assertTrue(self.chosen(BOARD_UPRIGHT + 0.01))


class CanvasTests(unittest.TestCase):
    def test_a_camera_is_no_layout(self):
        objs = {"placed": [dict(name="mp_cinematic_fallback_camera", pos=[0, 0, 30])], "equipment": []}
        self.assertEqual(variants.base_area(objs), [])
        objs["placed"].append(dict(name="ca_basin_windmill", pos=[5, 5, 0]))
        self.assertEqual(variants.base_area(objs), [(5, 5, 0)])
        self.assertEqual(variants.base_area({"equipment": [dict(item="rockets", pos=[1, 2, 3])]}), [(1, 2, 3)])

    def test_halo4_forge_canvases(self):
        for name in ("h4_ca_forge_erosion", "h4_ca_forge_ravine", "h4_dlc_forge_island"):
            f = os.path.join(maps.ROOT, name, "objects.json")
            if os.path.exists(f):
                self.assertEqual(variants.base_area(json.load(open(f, encoding="utf-8"))), [], name)

    @unittest.skipUnless(os.path.exists(os.path.join(variants.ROOT, RAVINE, "positions.json")), "no local Ravine layout")
    def test_ravine_layout_has_its_own_positions(self):
        m = maps.get_map(RAVINE)
        self.assertGreater(len(m["positions"]), 1)


class CliffsideTests(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(os.path.join(maps.ROOT, "h4_z05_cliffside", "objects.json")), "no map data")
    def test_owner_spots(self):
        m = maps.get_map("h4_z05_cliffside")
        self.assertEqual([p for p, _team in m["infantry_patrols"]],
                         [Vec(13.46, 0.05, 3.36), Vec(53.28, -12.25, 3.27), Vec(4.54, 0.2, 2.0)])
        rows = json.load(open(os.path.join(maps.ROOT, "h4_z05_cliffside", "positions.json"), encoding="utf-8"))
        owner = [r["pos"] for r in rows if r.get("owner")]
        for p in ([13.46, 0.05, 3.36], [45.42, 15.24, 2.39], [40.84, -6.51, 3.36], [40.71, -7.63, 6.56],
                  [30.34, 9.71, 5.72]):
            self.assertIn(p, owner)
        self.assertEqual(len(rows) - len(owner), 8)            # (the scored rows kept)


if __name__ == "__main__":
    unittest.main()
