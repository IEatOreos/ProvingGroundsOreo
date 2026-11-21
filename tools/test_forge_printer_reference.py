"""Reach Forge Printer, phase 2: the Halo 3 reference export.

Every input here is built in this file (a tiny OBJ, placement dicts, a fake
bsp2obj). One last test exports the real Guardian and skips on a PC without
MCC's Halo 3 or the map tools.
"""

import io
import json
import math
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from forge_printer import h3_reference as ref

OBJ = "v 0 0 0\nv 10 0 0\nv 0 20 0\nv 0 0 5\nf 1 2 3\nf 1 3 4\n"
OBJECTS = {"spawns": [{"pos": [1.0, 2.0, 3.0], "team": 0, "facing": 90.0, "games": ["all games"]}],
           "netgame_flags": [{"type": "ctf - flag", "id": 0, "team": 1, "pos": [4.0, 5.0, 1.0], "facing": 180.0}],
           "equipment": []}
FEATURES = {"features": [
    {"kind": "weapon", "name": "shotgun", "pos": [2.0, 2.0, 2.0], "team": 8, "respawn": 180},
    {"kind": "objective", "role": "flag", "name": "ctf - flag", "pos": [4.0, 5.0, 1.0], "team": 1},
    {"kind": "lift", "name": "lift_a", "pos": [3.0, 3.0, 0.0]},
    {"kind": "powerup", "name": "overshield", "pos": [50.0, 0.0, 0.0], "team": 8, "respawn": 90}],
    "teleporters": [[[1.0, 1.0, 1.0], [8.0, 8.0, 1.0]]]}


def put(path, text):
    with open(path, "w") as f:
        f.write(text)


def get(path, mode="r"):
    with open(path, mode) as f:
        return f.read()


def put_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def fake_bsp2obj(folder):
    """A python script standing in for bsp2obj.exe: writes OBJ to argv[2] and bsp2obj's summary line."""
    script = os.path.join(folder, "fake_bsp2obj.py")
    with open(script, "w") as f:
        f.write("import sys\nopen(sys.argv[2], 'w').write(%r)\nprint('1 bsps, 2 triangles (0 see-through), 4 vertices')\n" % OBJ)
    if os.name == "nt":
        bat = os.path.join(folder, "fake_bsp2obj.bat")
        with open(bat, "w") as f:
            f.write('@"%s" "%s" %%*\n' % (sys.executable, script))
        return bat
    return script


class Placements(unittest.TestCase):
    def test_groups_and_counts(self):
        p = ref.placements(OBJECTS, FEATURES)
        self.assertEqual(len(p["spawns"]), 1)
        self.assertEqual(len(p["weapons"]), 1)
        self.assertEqual(len(p["objectives"]), 1)           # from netgame_flags; features' copy is skipped
        self.assertEqual([o["kind"] for o in p["other"]], ["lift", "powerup", "teleporter_pair"])

    def test_facing_degrees_to_radians(self):
        p = ref.placements(OBJECTS, FEATURES)
        self.assertAlmostEqual(p["spawns"][0]["facing"], math.pi / 2, places=6)
        self.assertAlmostEqual(p["objectives"][0]["facing"], math.pi, places=6)

    def test_scale_applies_to_positions(self):
        with mock.patch.object(ref, "H3_TO_REACH_SCALE", 2.0):
            p = ref.placements(OBJECTS, FEATURES)
        self.assertEqual(p["spawns"][0]["pos"], [2.0, 4.0, 6.0])
        self.assertEqual(p["other"][-1]["to"], [16.0, 16.0, 2.0])

    def test_outside_box(self):
        p = ref.placements(OBJECTS, FEATURES)
        out = ref.outside(p, ([0, 0, 0], [10, 20, 5]))
        self.assertEqual([(g, i["name"]) for g, i in out], [("other", "overshield")])


class ScaleObj(unittest.TestCase):
    def test_bounds_and_triangles(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = os.path.join(tmp, "a.obj"), os.path.join(tmp, "b.obj")
            put(src, OBJ)
            with mock.patch.object(ref, "H3_TO_REACH_SCALE", 0.5):
                tris, (lo, hi) = ref.scale_obj(src, dst)
            self.assertEqual(tris, 2)
            # bsp2obj's Y-up (x, y, z) is the game's (x, -z, y)
            self.assertEqual((lo, hi), ([0, -2.5, 0], [5.0, 0, 10.0]))
            text = get(dst)
            self.assertIn("v 5.0000 0.0000 0.0000\n", text)
            self.assertIn("v 0.0000 0.0000 10.0000\n", text)      # obj (0, 20, 0): 20 up
            self.assertIn("v 0.0000 -2.5000 0.0000\n", text)      # obj (0, 0, 5)
            self.assertNotIn("-0.0000", text)

    def test_turning_z_up_keeps_the_winding(self):
        # a floor triangle seen from above, counter-clockwise in the game's axes, written Y up by bsp2obj
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = os.path.join(tmp, "a.obj"), os.path.join(tmp, "b.obj")
            put(src, "v 0 3 0\nv 1 3 0\nv 0 3 -1\nf 1 2 3\n")
            with mock.patch.object(ref, "H3_TO_REACH_SCALE", 1.0):
                ref.scale_obj(src, dst)
            v = [[float(c) for c in line.split()[1:]] for line in get(dst).splitlines() if line.startswith("v ")]
            self.assertEqual(v, [[0, 0, 3], [1, 0, 3], [0, 1, 3]])
            (ax, ay, _), (bx, by, _), (cx, cy, _) = v
            self.assertGreater((bx - ax) * (cy - ay) - (by - ay) * (cx - ax), 0)   # the normal points up

    def test_no_triangles_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "a.obj")
            put(src, "v 0 0 0\n")
            with self.assertRaises(ref.ReferenceError):
                ref.scale_obj(src, os.path.join(tmp, "b.obj"))


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.maps = os.path.join(t, "maps")
        os.makedirs(os.path.join(self.maps, "h3_yard"))
        put_json(os.path.join(self.maps, "h3_yard", "objects.json"), OBJECTS)
        put_json(os.path.join(self.maps, "h3_yard", "features.json"), FEATURES)
        self.mcc = os.path.join(t, "mcc")
        os.makedirs(os.path.join(self.mcc, "halo3", "maps"))
        put(os.path.join(self.mcc, "halo3", "maps", "yard.map"), "")
        self.tool = fake_bsp2obj(t)
        self.out = os.path.join(t, "out")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, name="h3_yard", **kw):
        args = dict(out_dir=self.out, mcc_dir=self.mcc, bsp2obj=self.tool, maps_dir=self.maps)
        args.update(kw)
        return ref.build(name, **args)

    def test_writes_files_and_is_repeatable(self):
        r1, rep = self.build()
        self.assertEqual(rep["triangles"], 2)
        self.assertEqual(rep["bsp2obj_triangles"], 2)
        k = ref.H3_TO_REACH_SCALE
        self.assertEqual(r1["bounds"], {"min": [0, round(-5 * k, 4), 0], "max": [round(10 * k, 4), 0, round(20 * k, 4)]})
        self.assertEqual(r1["spawns"][0]["pos"], [round(c * k, 4) for c in (1.0, 2.0, 3.0)])
        files = {n: get(os.path.join(self.out, n), "rb") for n in ("h3_yard.obj", "reference.json")}
        self.build()
        for n, data in files.items():
            self.assertEqual(get(os.path.join(self.out, n), "rb"), data, n)
        self.assertEqual(sorted(os.listdir(self.out)), ["h3_yard.obj", "reference.json"])
        saved = json.loads(get(os.path.join(self.out, "reference.json")))
        self.assertEqual(saved["source"], {"game": "halo3", "map": "h3_yard", "scale_from_source": ref.H3_TO_REACH_SCALE})

    def test_missing_map_folder(self):
        with self.assertRaisesRegex(ref.ReferenceError, "no map folder"):
            self.build("h3_nowhere")

    def test_missing_map_file(self):
        os.makedirs(os.path.join(self.maps, "h3_gone"))
        for n in ("objects.json", "features.json"):
            put_json(os.path.join(self.maps, "h3_gone", n), {})
        with self.assertRaisesRegex(ref.ReferenceError, "gone.map is not in this MCC"):
            self.build("h3_gone")

    def test_not_halo3(self):
        os.makedirs(os.path.join(self.maps, "reach_x"))
        for n in ("objects.json", "features.json"):
            put_json(os.path.join(self.maps, "reach_x", n), {})
        with self.assertRaisesRegex(ref.ReferenceError, "only Halo 3"):
            self.build("reach_x")

    def test_missing_tool_and_mcc(self):
        fake = mock.Mock(mcc=lambda: None, map_tool=lambda name: None)
        with mock.patch.object(ref, "_paths", return_value=fake):
            with self.assertRaisesRegex(ref.ReferenceError, "MCC was not found"):
                self.build(mcc_dir=None, bsp2obj=None)
            with self.assertRaisesRegex(ref.ReferenceError, "bsp2obj.exe was not found"):
                self.build(bsp2obj=None)

    def test_main_prints_one_line_on_error(self):
        buf = io.StringIO()
        with mock.patch.object(ref, "MAPS", self.maps), redirect_stdout(buf):
            code = ref.main("h3_nowhere", self.out)
        self.assertEqual(code, 1)
        self.assertEqual(buf.getvalue().strip().count("\n"), 0)


class RealGuardian(unittest.TestCase):
    def test_guardian(self):
        paths = ref._paths()
        mcc, tool = paths.mcc(), paths.map_tool("bsp2obj")
        if not (mcc and tool and os.path.isfile(os.path.join(mcc, "halo3", "maps", "guardian.map"))):
            self.skipTest("MCC's Halo 3 or the map tools are not on this PC")
        with tempfile.TemporaryDirectory() as tmp:
            r, rep = ref.build("h3_guardian", out_dir=tmp, mcc_dir=mcc, bsp2obj=tool)
        self.assertEqual(rep["triangles"], rep["bsp2obj_triangles"])
        self.assertEqual((len(r["spawns"]), len(r["weapons"]), len(r["objectives"])), (58, 21, 23))
        self.assertEqual(rep["outside"], [])


if __name__ == "__main__":
    unittest.main()
