"""Halo 4 Forge pieces' shapes read from MCC's own .map files (tools/h4_forge_shapes.py): hulls to faces, the shape
loader (brain/forge.py) and, where this PC has them, known pieces read from Forge Ravine and the owner's Ravine
layout, whose round base bots walked through (Nov 8: "Bots arent reading this as a wall. Or a base.")."""
import json
import math
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import h4_forge_shapes as H                          # noqa: E402
from brain import forge, maps                         # noqa: E402
from brain.core import Vec                            # noqa: E402

RAVINE_MAP = os.path.join(H.reach_tag_names.MCC or "", "halo4", "maps", "ca_forge_ravine.map")
RAVINE = "h4_ca_forge_ravine/variants/vc736941c"
SHAPES = os.path.join(H.SHAPES, "h4.json")


def box(lo, hi):
    """A box's planes (normal . p <= offset)."""
    return [((1.0, 0.0, 0.0), hi[0]), ((-1.0, 0.0, 0.0), -lo[0]), ((0.0, 1.0, 0.0), hi[1]),
            ((0.0, -1.0, 0.0), -lo[1]), ((0.0, 0.0, 1.0), hi[2]), ((0.0, 0.0, -1.0), -lo[2])]


def area(flat):
    return H._area([tuple(flat[k:k + 3]) for k in range(0, len(flat), 3)])


def centre(flat):
    pts = [flat[k:k + 3] for k in range(0, len(flat), 3)]
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


def normal(flat):
    p = [tuple(flat[k:k + 3]) for k in range(0, len(flat), 3)]
    s = [0.0, 0.0, 0.0]
    for k in range(1, len(p) - 1):
        c = H._cross(tuple(p[k][i] - p[0][i] for i in range(3)), tuple(p[k + 1][i] - p[0][i] for i in range(3)))
        s = [s[i] + c[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in s))
    return tuple(v / n for v in s)


class HullTests(unittest.TestCase):
    def test_a_box_has_six_faces_wound_outward(self):
        fs = H.faces([("default", box((-1, -2, 0), (1, 2, 0.5)))])
        self.assertEqual(len(fs), 6)
        for _mat, flat in fs:
            n, c = normal(flat), centre(flat)
            self.assertGreater(sum(n[i] * c[i] for i in range(2)) + n[2] * (c[2] - 0.25), 0)   # away from the middle
        self.assertAlmostEqual(sum(area(f) for _, f in fs), 2 * (4 * 2 + 4 * 0.5 + 2 * 0.5))

    def test_faces_between_hulls_are_inside_the_piece(self):
        side = H.faces([("default", box((-1, 0, 0), (0, 1, 1))), ("metal", box((0, 0, 0), (1, 1, 1)))])
        self.assertEqual(len(side), 10)                 # (the shared x = 0 faces, back to back, are gone)
        self.assertFalse([f for _, f in side if abs(centre(f)[0]) < 1e-6 and abs(normal(f)[0]) > 0.99])
        self.assertEqual({m for m, _ in side}, {"default", "metal"})
        stack = H.faces([("default", box((0, 0, 0), (1, 1, 1))), ("default", box((0, 0, 1), (1, 1, 2)))])
        tops = [f for _, f in stack if normal(f)[2] > 0.99]
        self.assertEqual(len(tops), 1)                  # (no floor left inside the stack)
        self.assertAlmostEqual(centre(tops[0])[2], 2.0)

    def test_overlapping_hulls_give_their_union_surface(self):
        fs = H.faces([("default", box((0, 0, 0), (2, 2, 2))), ("default", box((1, 1, 1), (3, 3, 3)))])
        self.assertAlmostEqual(sum(area(f) for _, f in fs), 42.0, places=3)

    def test_flush_faces_stay(self):
        fs = H.faces([("default", box((0, 0, 0), (1, 1, 1))), ("default", box((1, 0, 0), (2, 1, 1)))])
        self.assertAlmostEqual(sum(area(f) for _, f in fs if normal(f)[2] > 0.99), 2.0)

    def test_shape_entry(self):
        s = H.shape([("metal", box((-0.5, -0.25, 0), (0.5, 0.25, 1)))], "x.physics_model")
        self.assertEqual((s["min"], s["max"], s["material"], s["source"]),
                         ([-0.5, -0.25, 0.0], [0.5, 0.25, 1.0], "metal", "physics_model"))

    def test_string_ids(self):
        cf = H.CacheFile.__new__(H.CacheFile)
        cf.namespaces, cf.strings = (3, 2, 1), ["", "default", "a", "b0", "b1", "c0", "late0", "late1"]
        self.assertEqual([cf.string(s) for s in (1, 4, (1 << 17) | 1, (2 << 17), 3)], ["default", "late1", "b1", "c0", "late0"])


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.saved = forge._SHAPES.pop("h4", None), forge._FACES.pop("h4", None)

    def tearDown(self):
        for cache, v in zip((forge._SHAPES, forge._FACES), self.saved):
            cache.pop("h4", None)
            if v is not None:
                cache["h4"] = v

    def test_a_piece_read_from_the_map_goes_in_face_by_face(self):
        flat = H.faces([("default", box((-1, -1, 0), (1, 1, 0.2)))])
        forge._SHAPES["h4"] = {"fw_test": H.shape([("default", box((-1, -1, 0), (1, 1, 0.2)))], "t", flat)}
        forge._FACES["h4"] = {"fw_test": [[m, f] for m, f in flat]}
        axes = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        b = forge.block("fw_test", (5, 5, 0), axes, game="h4")
        self.assertEqual(b[4], "fw_test")
        self.assertEqual(len(b[5]), 6)
        blocks, _ = forge.nav_pieces([("fw_test", (5, 5, 0), axes), ("fw_unknown", (0, 0, 0), axes)], game="h4")
        self.assertEqual([x[4] for x in blocks], ["fw_test"])

    @unittest.skipUnless(os.path.exists(SHAPES), "no Halo 4 shape file (map pack)")
    def test_the_owners_ravine_pieces_have_shapes(self):
        shapes = forge._shapes("h4")
        if "fw_unsc_c_base_round" not in shapes:
            self.skipTest("shapes not added yet (python -I tools/h4_forge_shapes.py)")
        for name in ("fw_unsc_c_base_round", "fw_unsc_c_tower_3_story", "fw_unsc_c_wall_2x2_window", "fw_unsc_c_plat_2x4",
                     "fw_unsc_c_bridge_2x3", "fw_unsc_c_ramp_1x2_shallow", "fw_ravine_catwalk02", "fw_space_crate_small"):
            self.assertIn(name, shapes, name)
            self.assertTrue(forge._faces("h4").get(name), name)
        s = shapes["fw_unsc_c_base_round"]
        self.assertEqual((s["min"], s["max"]), ([-6.0, -3.305, -0.9], [6.0, 2.75, 1.789]))
        with open(SHAPES, encoding="utf-8") as f:
            self.assertIn("ca_forge_ravine_sky", json.load(f)["no_collision"])


@unittest.skipUnless(os.path.exists(RAVINE_MAP), "no Halo 4 Forge Ravine .map file")
class RavineMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pieces = H.pieces(H.CacheFile(RAVINE_MAP))

    def box_of(self, name):
        s = H.shape(self.pieces[name][2], self.pieces[name][1])
        return s["min"], s["max"]

    def test_known_pieces(self):
        self.assertEqual(self.box_of("fw_unsc_c_plat_1x1_flat"), ([-0.5, -0.5, -0.1], [0.5, 0.5, 0.1]))   # (the kit's)
        self.assertEqual(self.box_of("fw_unsc_c_base_round"), ([-6.0, -3.305, -0.9], [6.0, 2.75, 1.789]))  # (its twin's)
        lo, hi = self.box_of("fw_unsc_c_tower_3_story")
        for a, b in zip(lo + hi, [-3.476, -2.474, -2.21, 3.365, 2.642, 4.015]):
            self.assertAlmostEqual(a, b, delta=0.01)
        self.assertEqual(self.pieces["fw_unsc_c_plat_1x1_flat"][2][0][0], "default")

    def test_volumes_and_skies_are_not_solid(self):
        for name in ("fw_global_grav_5x5", "ca_forge_ravine_sky"):
            self.assertFalse(self.pieces[name][2], name)
        lift = H.faces(self.pieces["fw_gravity_lift"][2])            # (its base only, not the pull above it)
        self.assertLess(max(max(f[2::3]) for _, f in lift), 0.2)


@unittest.skipUnless(os.path.exists(os.path.join(maps.ROOT, RAVINE, "variant.json")), "no local Ravine layout")
class RavineNavTests(unittest.TestCase):
    def test_the_round_base_is_a_wall(self):
        if "fw_unsc_c_base_round" not in forge._shapes("h4"):
            self.skipTest("shapes not added yet (python -I tools/h4_forge_shapes.py)")
        maps._TERRAIN.pop(RAVINE, None)
        m = maps.get_map(RAVINE)
        m["live_blocks"] = None
        T = maps.terrain(m)
        self.assertIn("fw_unsc_c_base_round", {b[4] for b in m["live_blocks"]})
        c, f, l = (27.016, 17.279, -2.719), (0.5, -0.866), (0.866, 0.5)
        at = lambda a, b: (c[0] + a * f[0] + b * l[0], c[1] + a * f[1] + b * l[1])
        for b in (-1.5, 0.0, 1.5):                     # chest-high sight lines across it
            p, q = at(-9, b), at(9, b)
            self.assertFalse(T.sees(Vec(p[0], p[1], c[2] + 0.9), Vec(q[0], q[1], c[2] + 0.9)), b)
        p = at(-9, 0)
        self.assertLess(T.clearance(Vec(p[0], p[1], T.nav_z(p[0], p[1])), math.atan2(f[1], f[0]), far=12.0), 6.0)


if __name__ == "__main__":
    unittest.main()
