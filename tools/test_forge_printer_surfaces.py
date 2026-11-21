"""Reach Forge Printer, phase 3: the play space cut out of a reference mesh and sorted into
floors, slopes, walls and ceilings.

Every mesh here is built in this file: a small two-level yard with a ramp, a wall and a roof,
standing in a "forest" of far-off ground, tall trunks and loose leaves.
"""

import io
import json
import math
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import numpy as np

from forge_printer import surfaces as s


class Mesh:
    def __init__(self):
        self.v, self.t = [], []

    def quad(self, a, b, c, d):
        """Corners in order; the outward side is the one that sees them counter-clockwise."""
        n = len(self.v)
        self.v += [a, b, c, d]
        self.t += [(n, n + 1, n + 2), (n, n + 2, n + 3)]

    def tri(self, a, b, c):
        n = len(self.v)
        self.v += [a, b, c]
        self.t.append((n, n + 1, n + 2))

    def arrays(self):
        return np.array(self.v, dtype=float), np.array(self.t, dtype=np.int64)

    def obj(self):
        return "".join("v %.4f %.4f %.4f\n" % tuple(v) for v in self.v) + \
               "".join("f %d %d %d\n" % (a + 1, b + 1, c + 1) for a, b, c in self.t)


def yard(backdrop=True):
    m = Mesh()
    m.quad((0, 0, 0), (8, 0, 0), (8, 8, 0), (0, 8, 0))             # lower floor, 8 x 8
    m.quad((8, 0, 0), (12, 0, 2), (12, 8, 2), (8, 8, 0))           # ramp up towards +x, 26.6 degrees
    m.quad((12, 0, 2), (16, 0, 2), (16, 8, 2), (12, 8, 2))         # upper floor, 4 x 8
    m.quad((0, 0, 0), (0, 8, 0), (0, 8, 3), (0, 0, 3))             # wall at x = 0, facing +x
    m.quad((0, 0, 3), (0, 8, 3), (8, 8, 3), (8, 0, 3))             # roof over the lower floor, facing down
    if backdrop:
        m.quad((-60, -60, -30), (60, -60, -30), (60, 60, -30), (-60, 60, -30))   # forest floor far below
        m.quad((40, 0, -40), (40, 8, -40), (40, 8, 80), (40, 0, 80))             # a trunk well off to the side
        m.quad((4, 9, -40), (6, 9, -40), (6, 9, 80), (4, 9, 80))                 # a trunk beside the yard
        for i in range(12):                                                      # loose leaves above the roof
            x, y = 1 + (i % 4) * 2.0, 1 + (i // 4) * 2.5
            m.tri((x, y, 6), (x + 0.1, y, 6.02), (x, y + 0.1, 6.02))
    return m


SPAWNS = [[2.0, 2.0, 0.05], [14.0, 4.0, 2.05]]
REFERENCE = {"source": {"game": "halo3", "map": "h3_yard", "scale_from_source": 1.0},
             "mesh": "h3_yard.obj",
             "spawns": [{"pos": p, "facing": 0.0, "team": 0, "games": []} for p in SPAWNS],
             "weapons": [{"name": "shotgun", "pos": [6.0, 6.0, 0.1], "respawn": 180, "team": 8}],
             "objectives": [], "other": []}


def folder_with(mesh, reference=REFERENCE):
    tmp = tempfile.TemporaryDirectory()
    with open(os.path.join(tmp.name, "h3_yard.obj"), "w") as f:
        f.write(mesh.obj())
    with open(os.path.join(tmp.name, "reference.json"), "w") as f:
        json.dump(reference, f)
    return tmp


class Kinds(unittest.TestCase):
    def test_kind_follows_the_lean(self):
        def normal(deg):
            return [math.sin(math.radians(deg)), 0.0, math.cos(math.radians(deg))]
        leans = [0, 9, 11, 30, 54, 56, 90, 124, 126, 180]
        kinds = s.classify(np.array([normal(d) for d in leans]))
        self.assertEqual([s.KINDS[k] for k in kinds],
                         ["floor", "floor", "slope", "slope", "slope", "wall", "wall", "wall", "ceiling", "ceiling"])

    def test_the_yards_surfaces(self):
        v, t = yard(backdrop=False).arrays()
        normals, areas, _ = s.geometry(v, t)
        kinds = [s.KINDS[k] for k in s.classify(normals)]
        self.assertEqual(kinds, ["floor"] * 2 + ["slope"] * 2 + ["floor"] * 2 + ["wall"] * 2 + ["ceiling"] * 2)
        self.assertAlmostEqual(float(areas[:2].sum()), 64.0)
        self.assertAlmostEqual(float(s.lean(normals)[2]), math.degrees(math.atan2(2, 4)), places=4)


class ObjFiles(unittest.TestCase):
    def test_faces_with_more_corners_and_relative_indices(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.obj")
            with open(path, "w") as f:
                f.write("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1/1/1 2/2/2 3/3/3 4/4/4\nf -4 -3 -2\n")
            v, t = s.load_obj(path)
            self.assertEqual(v.shape, (4, 3))
            self.assertEqual(t.tolist(), [[0, 1, 2], [0, 2, 3], [0, 1, 2]])

    def test_an_obj_without_triangles_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.obj")
            with open(path, "w") as f:
                f.write("v 0 0 0\n")
            with self.assertRaises(s.SurfaceError):
                s.load_obj(path)

    def test_saved_mesh_is_grouped_and_shares_corners(self):
        v, t = yard(backdrop=False).arrays()
        normals, _, _ = s.geometry(v, t)
        kinds = s.classify(normals)
        order = np.argsort(kinds, kind="stable")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.obj")
            self.assertEqual(s.save_obj(path, v, t[order], kinds[order]), 10)
            with open(path) as f:
                lines = f.read().splitlines()
            self.assertEqual([l for l in lines if l.startswith("g ")], ["g floor", "g slope", "g wall", "g ceiling"])
            self.assertEqual(sum(1 for l in lines if l.startswith("v ")), 12)     # 20 corners, 12 distinct points
            back_v, back_t = s.load_obj(path)
            back_n, back_a, _ = s.geometry(back_v, back_t)
            self.assertAlmostEqual(float(back_a.sum()), float(s.geometry(v, t)[1].sum()), places=3)
            self.assertEqual(sorted(s.classify(back_n).tolist()), sorted(kinds.tolist()))


class PlaySpace(unittest.TestCase):
    def setUp(self):
        self.v, self.t = yard().arrays()
        self.normals, self.areas, _ = s.geometry(self.v, self.t)
        self.cells = s.ground_levels(self.v, self.t, self.normals, self.areas)

    def test_floors_are_ground_and_leaves_are_not(self):
        self.assertEqual(s.grounded(self.cells, SPAWNS), 2)
        heights = [z for levels in self.cells.values() for z in levels]
        self.assertFalse(any(5.5 < z < 6.5 for z in heights))        # the leaves
        self.assertTrue(any(abs(z + 30) < 0.01 for z in heights))    # the forest floor is ground, just far away

    def test_a_point_in_the_air_is_not_on_ground(self):
        self.assertEqual(s.grounded(self.cells, [[2.0, 2.0, 1.5], [30.0, 30.0, 0.0]]), 0)

    def test_the_walk_climbs_the_ramp_and_stays_out_of_the_forest(self):
        reached = s.walk(self.cells, [SPAWNS[0]])
        heights = [z for _, z in reached]
        self.assertAlmostEqual(max(heights), 2.0, delta=0.05)         # the upper floor, by the ramp
        self.assertGreater(min(heights), -0.01)                       # not the forest floor 30 below
        xs = [c[0] * s.CELL for c, _ in reached]
        self.assertLessEqual(min(xs), 0.5)
        self.assertGreaterEqual(max(xs), 15.0)

    def test_a_drop_too_deep_and_a_gap_too_wide_are_not_crossed(self):
        m = Mesh()
        m.quad((0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0))
        m.quad((4 + s.GAP + 1.5, 0, 0), (12, 0, 0), (12, 4, 0), (4 + s.GAP + 1.5, 4, 0))   # across a wide gap
        m.quad((0, 4, -s.DROP - 1), (4, 4, -s.DROP - 1), (4, 8, -s.DROP - 1), (0, 8, -s.DROP - 1))   # a deep drop
        m.quad((0, -4, -1.5), (4, -4, -1.5), (4, 0, -1.5), (0, 0, -1.5))                   # a drop that is fine
        v, t = m.arrays()
        normals, areas, _ = s.geometry(v, t)
        reached = s.walk(s.ground_levels(v, t, normals, areas), [[2.0, 2.0, 0.05]])
        self.assertEqual(sorted({round(z, 2) for _, z in reached}), [-1.5, 0.0])
        self.assertLess(max(c[0] * s.CELL for c, _ in reached), 4.5)

    def test_the_box_is_the_walked_ground_grown(self):
        reached = s.walk(self.cells, SPAWNS)
        lo, hi = s.play_box(reached, SPAWNS, side=4.0, below=3.0, above=8.0)
        for got, want in zip(lo + hi, [-4.0, -4.0, -3.0, 20.0, 12.0, 10.05]):
            self.assertAlmostEqual(got, want, delta=0.51)


class Cut(unittest.TestCase):
    def test_backdrop_goes_and_crossing_triangles_are_cut_at_the_box(self):
        v, t = yard().arrays()
        lo, hi = [-4.0, -4.0, -3.0], [20.0, 12.0, 10.0]
        cv, ct = s.cut_to_box(v, t, lo, hi)
        used = cv[ct.reshape(-1)]
        self.assertTrue(np.all(used >= np.array(lo) - 1e-9) and np.all(used <= np.array(hi) + 1e-9))
        normals, areas, centres = s.geometry(cv, ct)
        kinds = s.classify(normals)
        # the yard is whole: 96 of floor, a ramp, a wall, a roof
        self.assertAlmostEqual(float(areas[kinds == s.FLOOR].sum()), 96.0, places=6)
        self.assertAlmostEqual(float(areas[kinds == s.CEILING].sum()), 64.0, places=6)
        # of the walls, the yard's own (24) plus the near trunk cut to the box's height (2 wide, 13 tall)
        self.assertAlmostEqual(float(areas[kinds == s.WALL].sum()), 24.0 + 2.0 * 13.0, places=6)
        # the leaves are inside the box and stay; the forest floor and the far trunk are gone
        self.assertFalse(np.any(centres[:, 2] < -3.0))
        self.assertFalse(np.any(centres[:, 0] > 20.0))

    def test_cutting_keeps_which_way_a_triangle_faces(self):
        v = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0]], dtype=float)
        t = np.array([[0, 1, 2]])
        cv, ct = s.cut_to_box(v, t, [-1, -1, -1], [4, 4, 1])
        normals, areas, _ = s.geometry(cv, ct)
        self.assertTrue(np.all(normals[:, 2] > 0.999))
        self.assertAlmostEqual(float(areas.sum()), 16.0, places=9)     # the 4 x 4 corner of the triangle

    def test_a_box_that_misses_everything_leaves_nothing(self):
        v, t = yard().arrays()
        cv, ct = s.cut_to_box(v, t, [200, 200, 200], [210, 210, 210])
        self.assertEqual(len(ct), 0)


class Patches(unittest.TestCase):
    def found(self, mesh):
        v, t = mesh.arrays()
        normals, areas, centres = s.geometry(v, t)
        return s.patches(v, t, normals, areas, centres, s.classify(normals))

    def test_the_yards_patches(self):
        found, owner = self.found(yard(backdrop=False))
        got = sorted((p["kind"], p["area"], p["triangles"]) for p in found)
        self.assertEqual(got, [("ceiling", 64.0, 2), ("floor", 32.0, 2), ("floor", 64.0, 2),
                               ("slope", round(8 * math.hypot(4, 2), 3), 2), ("wall", 24.0, 2)])
        self.assertEqual(len(set(owner.tolist())), 5)
        ramp = next(p for p in found if p["kind"] == "slope")
        self.assertAlmostEqual(ramp["tilt"], 26.6, delta=0.05)
        self.assertAlmostEqual(ramp["uphill"], 0.0, delta=0.05)         # it rises towards +x
        self.assertEqual((ramp["min"], ramp["max"]), ([8.0, 0.0, 0.0], [12.0, 8.0, 2.0]))
        low = next(p for p in found if p["kind"] == "floor" and p["area"] == 64.0)
        self.assertEqual((low["normal"], low["offset"], low["tilt"]), ([0.0, 0.0, 1.0], 0.0, 0.0))

    def test_uphill_direction(self):
        m = Mesh()
        m.quad((0, 0, 0), (4, 0, 0), (4, 4, 2), (0, 4, 2))               # rises towards +y
        found, _ = self.found(m)
        self.assertAlmostEqual(found[0]["uphill"], 90.0, delta=0.05)

    def test_level_floors_that_do_not_touch_are_separate(self):
        m = Mesh()
        m.quad((0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0))
        m.quad((5, 0, 0), (7, 0, 0), (7, 2, 0), (5, 2, 0))
        found, _ = self.found(m)
        self.assertEqual([p["area"] for p in found], [4.0, 4.0])

    def test_a_step_splits_a_floor_and_a_gentle_bend_does_not(self):
        m = Mesh()
        m.quad((0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0))
        m.quad((2, 0, 0), (4, 0, 0.05), (4, 2, 0.05), (2, 2, 0))          # 1.4 degrees: the same floor
        found, _ = self.found(m)
        self.assertEqual(len(found), 1)
        m = Mesh()
        m.quad((0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0))
        m.quad((2, 0, 0.5), (4, 0, 0.5), (4, 2, 0.5), (2, 2, 0.5))        # a step up
        found, _ = self.found(m)
        self.assertEqual(len(found), 2)


class Build(unittest.TestCase):
    def test_writes_the_play_mesh_and_the_surface_list(self):
        with folder_with(yard()) as folder:
            out = s.build(folder)
            self.assertEqual(sorted(os.listdir(folder)), ["h3_yard.obj", "h3_yard_play.obj", "reference.json", "surfaces.json"])
            with open(os.path.join(folder, "surfaces.json")) as f:
                self.assertEqual(json.load(f), out)
            self.assertEqual(out["spawns_on_ground"], [2, 2])
            self.assertEqual(out["mesh"], "h3_yard_play.obj")
            self.assertEqual(out["kinds"]["floor"]["area"], 96.0)
            self.assertEqual(out["kinds"]["slope"]["patches"], 13)          # the ramp and twelve leaves
            self.assertEqual(out["kinds"]["slope"]["listed_patches"], 1)    # only the ramp is big enough to list
            self.assertEqual(out["kinds"]["ceiling"]["area"], 64.0)
            self.assertLess(out["play_mesh"]["area"], out["whole_mesh"]["area"] / 10)   # the forest is gone
            self.assertLess(out["box"]["max"][2], 12.0)
            self.assertGreater(out["box"]["min"][2], -4.0)
            self.assertEqual([p["area"] for p in out["patches"]], sorted((p["area"] for p in out["patches"]), reverse=True))
            self.assertTrue(all(p["area"] >= s.PATCH_LISTED for p in out["patches"]))   # the leaves are counted, not listed
            v, t = s.load_obj(os.path.join(folder, "h3_yard_play.obj"))
            self.assertEqual(len(t), out["play_mesh"]["triangles"])

    def test_walked_ground_is_told_from_other_floors(self):
        m = yard()
        m.quad((1, 1, 5), (3, 1, 5), (3, 3, 5), (1, 3, 5))               # a ledge nobody can reach
        with folder_with(m) as folder:
            out = s.build(folder)
        floors = {p["area"]: p["walked"] for p in out["patches"] if p["kind"] == "floor"}
        self.assertEqual(floors, {64.0: True, 32.0: True, 4.0: False})
        self.assertTrue(next(p for p in out["patches"] if p["kind"] == "slope")["walked"])
        self.assertEqual(out["kinds"]["floor"]["area"], 100.0)
        self.assertEqual(out["kinds"]["floor"]["walked_area"], 96.0)
        self.assertEqual(out["kinds"]["wall"]["walked_area"], 0.0)
        self.assertNotIn("walked", next(p for p in out["patches"] if p["kind"] == "wall"))

    def test_a_second_run_writes_the_same_bytes(self):
        with folder_with(yard()) as folder:
            def files():
                out = {}
                for name in ("h3_yard_play.obj", "surfaces.json"):
                    with open(os.path.join(folder, name), "rb") as f:
                        out[name] = f.read()
                return out
            s.build(folder)
            first = files()
            s.build(folder)
            self.assertEqual(files(), first)

    def test_the_cut_can_be_made_tighter(self):
        with folder_with(yard()) as folder:
            wide = s.build(folder)
            tight = s.build(folder, side=1.0, below=0.5, above=4.0)
            self.assertLess(tight["box"]["max"][0], wide["box"]["max"][0])
            self.assertEqual(tight["cut"], {"side": 1.0, "below": 0.5, "above": 4.0})

    def test_a_mesh_that_does_not_line_up_with_the_spawns_is_refused(self):
        # the yard still written Y up, as bsp2obj leaves it: nothing is under the spawns
        tipped = Mesh()
        m = yard()
        tipped.v = [(x, z, -y) for x, y, z in m.v]
        tipped.t = m.t
        with folder_with(tipped) as folder:
            with self.assertRaisesRegex(s.SurfaceError, "do not line up"):
                s.build(folder)
            self.assertNotIn("surfaces.json", os.listdir(folder))

    def test_missing_files_end_in_one_line(self):
        with tempfile.TemporaryDirectory() as empty:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = s.main(empty)
            self.assertEqual(code, 1)
            self.assertEqual(buf.getvalue().strip().count("\n"), 0)
            self.assertIn("reference.json", buf.getvalue())
        with folder_with(yard()) as folder:
            os.remove(os.path.join(folder, "h3_yard.obj"))
            with self.assertRaisesRegex(s.SurfaceError, "is missing"):
                s.build(folder)
        no_spawns = dict(REFERENCE, spawns=[])
        with folder_with(yard(), no_spawns) as folder:
            with self.assertRaisesRegex(s.SurfaceError, "no spawns"):
                s.build(folder)


if __name__ == "__main__":
    unittest.main()
