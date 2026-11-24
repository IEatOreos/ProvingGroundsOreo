"""(custom, Nov 22) Forge maps by their in-game names (brain/variants.title, brain/mvar.layout_name) and modded maps made
mappable (tools/mod_maps.py, tools/reach_tag_names.source)."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

from brain import mvar, variants  # noqa: E402
import mod_maps  # noqa: E402
import reach_tag_names  # noqa: E402


class Title(unittest.TestCase):
    def test_mcc_keys(self):
        self.assertEqual(variants.title("$HReach_MPMap_R-21_Title"), "Asylum")
        self.assertEqual(variants.title("$HReach_MPMap_R-25_Title"), "The Cage")
        self.assertEqual(variants.title("$HReach_MPMap_R-11_Title"), "Tempest")
        self.assertEqual(variants.title("$hr_mvar_Hardcore_Countdown"), "Hardcore Countdown")
        self.assertEqual(variants.title("$HReach_MPMap_R-99_Title"), "R-99")

    def test_own_name_kept(self):
        self.assertEqual(variants.title("HEMORRHAGE btb"), "HEMORRHAGE btb")
        self.assertEqual(variants.title(" Renegade"), "Renegade")

    def test_from_file(self):
        self.assertEqual(variants.title(None, "hr_forgeWorld_theCage.mvar"), "The Cage")
        self.assertEqual(variants.title("", r"C:\x\hr_forgeWorld_pinnacle.mvar"), "Pinnacle")
        self.assertIsNone(variants.title(None, None))


def _v(title, path="x.mvar"):
    return dict(title=title, path=path)


class LayoutName(unittest.TestCase):
    def setUp(self):
        self._c = mvar.candidates
        self.pieces = [("p", (float(i), 0.0, 0.0), None) for i in range(40)]

    def tearDown(self):
        mvar.candidates = self._c

    def test_clear_match(self):
        mvar.candidates = lambda *a, **k: [(1.0, 2, _v("$HReach_MPMap_R-21_Title")), (1.0, 1, _v("$HReach_MPMap_R-21_Title")),
                                           (0.3, 3, _v("Other"))]
        name, v, share = mvar.layout_name("reach_forge_halo", self.pieces)
        self.assertEqual((name, v["title"], share), ("Asylum", "$HReach_MPMap_R-21_Title", 1.0))

    def test_tie_between_names(self):
        mvar.candidates = lambda *a, **k: [(1.0, 2, _v("MLG Countdown v7")), (0.98, 1, _v("$hr_mvar_Hardcore_Countdown"))]
        self.assertIsNone(mvar.layout_name("reach_45_launch_station", self.pieces)[0])

    def test_weak_or_small(self):
        mvar.candidates = lambda *a, **k: [(0.8, 1, _v("Spire"))]
        self.assertIsNone(mvar.layout_name("reach_35_island", self.pieces)[0])
        mvar.candidates = lambda *a, **k: [(1.0, 1, _v("Dreadnought"))]
        self.assertIsNone(mvar.layout_name("reach_forge_halo", self.pieces[:20])[0])


class ModMaps(unittest.TestCase):
    def make(self, root, mod, engine, stem, title, with_map=True):
        d = os.path.join(root, mod)
        os.makedirs(os.path.join(d, "multiplayer"))
        for path, data in ((os.path.join(d, "ModInfo.json"),
                            dict(Engine=engine, Title=dict(Neutral=mod.upper()),
                                 GameModContents=dict(MultiplayerMaps=[f"multiplayer\\{stem}.json"]))),
                           (os.path.join(d, "multiplayer", stem + ".json"),
                            dict(ScenarioFile=f"levels\\multi\\{stem}\\{stem}", Title=dict(Neutral=title)))):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        if with_map:
            os.makedirs(os.path.join(d, "Maps"))
            open(os.path.join(d, "Maps", stem + ".map"), "wb").close()

    def test_finds_mod_maps(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as mcc:
            self.make(root, "fp_test", "HaloReach", "fp_test", "FP_TEST")
            self.make(root, "swap", "HaloReach", "20_sword_slayer", "Sword Base again")
            self.make(root, "nomap", "Halo3", "h3_only", "No map", with_map=False)
            self.make(root, "ce", "Halo1", "bloody", "Not read")
            os.makedirs(os.path.join(mcc, "haloreach", "maps"))
            open(os.path.join(mcc, "haloreach", "maps", "20_sword_slayer.map"), "wb").close()
            rows = {m["folder"]: m for m in mod_maps.mod_maps(roots=[root], mcc=mcc)}
            self.assertEqual(set(rows), {"reach_fp_test", "reach_20_sword_slayer", "h3_h3_only"})
            self.assertEqual(rows["reach_fp_test"]["title"], "FP_TEST")
            self.assertTrue(rows["reach_fp_test"]["map"].endswith("fp_test.map"))
            self.assertFalse(rows["reach_fp_test"]["stock"])
            self.assertTrue(rows["reach_20_sword_slayer"]["stock"])
            self.assertIsNone(rows["h3_h3_only"]["map"])
            self.assertIn("stock", mod_maps.build(rows["reach_20_sword_slayer"]))
            self.assertIn("no .map", mod_maps.build(rows["h3_h3_only"]))

    def test_floor_points_skip_sky_floor(self):
        # a 4 x 4 grid of 2 u floor tiles at z 0 (two triangles each), a sky box floor 60 u under them (one big pair)
        v, f = [], []
        for i in range(4):
            for j in range(4):
                k = len(v)
                v += [(i * 2, j * 2, 0), (i * 2 + 2, j * 2, 0), (i * 2 + 2, j * 2 + 2, 0), (i * 2, j * 2 + 2, 0)]
                f += [(k, k + 1, k + 2), (k, k + 2, k + 3)]
        k = len(v)
        v += [(-50, -50, -60), (60, -50, -60), (60, 60, -60), (-50, 60, -60)]
        f += [(k, k + 1, k + 2), (k, k + 2, k + 3)]
        pts = mod_maps.floor_points(np.array(v, float), np.array(f))
        self.assertTrue(pts)
        self.assertTrue(all(abs(p[2]) < 1e-6 for p in pts))

    def test_stand_ins_and_callouts(self):
        pts = [(x * 3.0, y * 3.0, 1.0) for x in range(10) for y in range(4)]
        objs = mod_maps.stand_ins(pts)
        self.assertTrue(objs["stand_in"])
        self.assertEqual(len(objs["spawns"]), mod_maps.STAND_INS)
        a, b = (f["pos"] for f in objs["netgame_flags"])
        self.assertGreater(abs(a[0] - b[0]), 20)              # the far ends
        c = mod_maps.callouts("reach_x", objs)
        self.assertTrue(c["generated"])
        self.assertEqual(set(c["zones"]), {"West side", "Mid", "East side"})
        self.assertEqual(len(c["holds"]["red"]), 3)
        with self.assertRaises(ValueError):
            mod_maps.stand_ins([])


class StudioExport(unittest.TestCase):
    """(custom, Nov 24) Upstream 0.3.0's note #84: our build uses MCC Map Studio's own bot export (ppg/<name>) when the
    mod has one, never reading the .map (no bsp2obj), and keeps what is ours by hand."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.mod = os.path.join(root, "mods", "my_map")
        os.makedirs(os.path.join(self.mod, "maps"))
        open(os.path.join(self.mod, "maps", "My_Map.map"), "wb").close()
        self.maps = os.path.join(root, "maps")
        os.makedirs(self.maps)
        self.old_maps, mod_maps.MAPS = mod_maps.MAPS, self.maps
        self.row = dict(folder="h3_my_scenario", game="h3", stem="my_scenario", title="My Map", mod="MY MAP",
                        mod_dir=self.mod, map=os.path.join(self.mod, "maps", "My_Map.map"), stock=False, built=False,
                        stale=False)

    def tearDown(self):
        mod_maps.MAPS = self.old_maps
        self.tmp.cleanup()

    def export(self, name, files):
        d = os.path.join(self.mod, "ppg", name)
        os.makedirs(d)
        for fn, data in files.items():
            with open(os.path.join(d, fn), "wb" if fn.endswith(".npz") else "w") as fh:
                fh.write(data if fn.endswith(".npz") else json.dumps(data))
        return d

    def load(self, *p):
        with open(os.path.join(*p), encoding="utf-8") as fh:
            return json.load(fh)

    def test_none_without_an_export(self):
        self.assertIsNone(mod_maps.studio_export(self.row))

    def test_built_from_the_export(self):
        made = self.export("h3_my_map", {"heightmap.npz": b"studio", "objects.json": {"spawns": [1]},
                                         "callouts.json": {"zones": {}}, "paint.json": {"layers": {}}})
        self.assertEqual(mod_maps.studio_export(self.row), made)     # (by the .map's name, as Map Studio names it)
        from unittest import mock
        with mock.patch.object(mod_maps.paths, "map_tool", side_effect=AssertionError("no bsp2obj")):
            self.assertEqual(mod_maps.build(self.row, log=lambda *a: None), "built")
        d = os.path.join(self.maps, "h3_my_scenario")
        with open(os.path.join(d, "heightmap.npz"), "rb") as fh:
            self.assertEqual(fh.read(), b"studio")
        self.assertEqual(self.load(d, "objects.json")["spawns"], [1])
        self.assertTrue(os.path.exists(os.path.join(d, "paint.json")))
        with open(os.path.join(d, ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("*", fh.read())
        mod = self.load(d, "mod.json")
        self.assertEqual((mod["title"], mod["studio_export"]), ("My Map", made))

    def test_ours_by_hand_kept(self):
        self.export("h3_my_scenario", {"heightmap.npz": b"studio", "objects.json": {"spawns": [1]},
                                       "callouts.json": {"zones": {"x": 1}}, "paint.json": {"layers": {"walk": 1}}})
        d = os.path.join(self.maps, "h3_my_scenario")
        os.makedirs(d)
        for fn, data in (("objects.json", {"spawns": [9], "by_hand": True}), ("callouts.json", {"generated": True}),
                         ("paint.json", {"layers": {"mine": 1}})):
            with open(os.path.join(d, fn), "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        self.assertEqual(mod_maps.build(dict(self.row, built=True, stale=True), log=lambda *a: None), "built")
        self.assertEqual(self.load(d, "objects.json")["spawns"], [9])          # (made by hand: kept)
        self.assertEqual(self.load(d, "callouts.json")["zones"], {"x": 1})     # (generated: Map Studio's instead)
        self.assertEqual(self.load(d, "paint.json")["layers"], {"mine": 1})    # (the owner's paint kept)


class TagSource(unittest.TestCase):
    def test_mod_fallback(self):
        old = mod_maps.map_file
        try:
            mod_maps.map_file = lambda stem, game="reach": r"C:\mods\fp_x\maps\fp_x.map" if stem == "fp_x" else None
            self.assertEqual(reach_tag_names.source("fp_x"), (r"C:\mods\fp_x\maps\fp_x.map", True))
            src, mod = reach_tag_names.source("no_such_map_anywhere")
            self.assertFalse(mod)
            self.assertTrue(src.endswith("no_such_map_anywhere.map"))
        finally:
            mod_maps.map_file = old


if __name__ == "__main__":
    unittest.main()
