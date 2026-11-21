"""Reach Forge Printer, phase 3: flat Forge blocks fitted to a reference's walked floors.

Floors here are built by hand (the same little yard as the surfaces tests, and single slabs);
the piece sizes come from the table kept in the repository.
"""

import io
import json
import math
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import numpy as np

from forge_printer import fit, mvar, pieces, surfaces
from test_forge_printer_surfaces import Mesh, folder_with, yard
from test_forge_printer_turn_test import forge_world


def slab(x0, y0, x1, y1, z=0.0):
    return (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)


def analysis_of(*quads):
    """What surfaces.analyse() gives the fitter, for floors given as quads: all of it walked."""
    m = Mesh()
    for q in quads:
        m.quad(*q)
    v, t = m.arrays()
    normals, _, _ = surfaces.geometry(v, t)
    kinds = surfaces.classify(normals)
    return {"verts": v, "tris": t, "kinds": kinds, "walked": np.ones(len(t), dtype=bool)}


def fitted(*quads):
    return fit.fit_floors(analysis_of(*quads))


class Grid(unittest.TestCase):
    def test_a_slab_becomes_cells_at_its_height(self):
        a = analysis_of(slab(1.0, 2.0, 3.0, 2.5, z=1.2))
        x0, y0, layers = fit.floor_layers(a["verts"], a["tris"], np.arange(len(a["tris"])))
        self.assertEqual((x0, y0), (1.0, 2.0))
        self.assertEqual(list(layers), [12])
        cells = np.isfinite(layers[12])
        self.assertEqual(int(cells.sum()), 8 * 2)                       # 2.0 x 0.5 at a quarter unit
        self.assertTrue(np.allclose(layers[12][cells], 1.2))

    def test_window_sums(self):
        grid = np.zeros((4, 5), dtype=bool)
        grid[1:3, 1:4] = True
        sums = fit._window_sums(grid, 3, 2)
        self.assertEqual(sums.shape, (3, 3))
        self.assertEqual(int(sums[1, 1]), 6)
        self.assertEqual(int(sums[0, 0]), 2)
        self.assertEqual(fit._window_sums(grid, 9, 9).size, 0)


class Floors(unittest.TestCase):
    def test_a_floor_the_size_of_a_block_takes_that_block(self):
        placements, report = fitted(slab(0, 0, 5, 5))
        self.assertEqual(placements, [{"part": "floor", "piece": "Block 5x5 Flat", "centre": [2.5, 2.5], "top": 0.0,
                                       "turn": 0.0, "size": [5.0, 5.0], "tucked": 0, "origin": [2.5, 2.5, -0.1]}])
        self.assertEqual((report["coverage"], report["pieces"], report["overhang_area"]), (1.0, 1, 0.0))

    def test_a_long_block_turns_to_lie_along_the_floor(self):
        placements, _ = fitted(slab(0, 0, 1, 5, z=2.0))
        self.assertEqual([(p["piece"], p["turn"], p["centre"], p["top"]) for p in placements],
                         [("Block 5x1 Flat", 90.0, [0.5, 2.5], 2.0)])
        placements, _ = fitted(slab(0, 0, 5, 1))
        self.assertEqual([(p["piece"], p["turn"]) for p in placements], [("Block 5x1 Flat", 0.0)])

    def test_largest_blocks_first_and_nothing_overlaps(self):
        placements, report = fitted(slab(0, 0, 8, 8))
        self.assertEqual(report["coverage"], 1.0)
        self.assertEqual(placements[0]["piece"], "Block 5x5 Flat")
        self.assertEqual(report["tucked"], 0)
        self.assertAlmostEqual(sum(p["size"][0] * p["size"][1] for p in placements), 64.0)   # no overlap, no overhang
        for p in placements:
            self.assertTrue(0 <= p["centre"][0] - p["size"][0] / 2 and p["centre"][0] + p["size"][0] / 2 <= 8)
            self.assertTrue(0 <= p["centre"][1] - p["size"][1] / 2 and p["centre"][1] + p["size"][1] / 2 <= 8)

    def test_floors_one_above_another_are_fitted_apart(self):
        placements, report = fitted(slab(0, 0, 4, 4, z=0.0), slab(0, 0, 4, 4, z=3.0))
        self.assertEqual(sorted((p["piece"], p["top"]) for p in placements),
                         [("Block 4x4 Flat", 0.0), ("Block 4x4 Flat", 3.0)])
        self.assertEqual(report["floor_area"], 32.0)

    def test_a_small_step_is_one_level_and_a_real_step_is_two(self):
        placements, _ = fitted(slab(0, 0, 2, 4, z=0.0), slab(2, 0, 4, 4, z=0.15))
        self.assertEqual([p["piece"] for p in placements], ["Block 4x4 Flat"])
        placements, _ = fitted(slab(0, 0, 2, 4, z=0.0), slab(2, 0, 4, 4, z=0.5))
        self.assertEqual(sorted(p["top"] for p in placements), [0.0, 0.0, 0.5, 0.5])
        self.assertEqual({p["piece"] for p in placements}, {"Block 2x2 Flat"})

    def test_a_little_of_a_block_may_hang_past_the_edge(self):
        # a 1 x 1 floor with one quarter-unit corner missing: 15 of the block's 16 cells are floor
        placements, report = fitted(slab(0, 0, 1, 0.75), slab(0, 0.75, 0.75, 1))
        self.assertEqual([(p["piece"], p["tucked"]) for p in placements], [("Block 1x1 Flat", 0)])
        self.assertEqual(report["overhang_area"], 0.1)                  # 0.0625 u2
        # with half of it missing nothing fits
        placements, report = fitted(slab(0, 0, 1, 0.5))
        self.assertEqual((placements, report["coverage"]), ([], 0.0))

    def test_a_strip_left_over_is_filled_by_a_block_tucked_under_its_neighbour(self):
        placements, report = fitted(slab(0, 0, 2.5, 1))
        self.assertEqual(report["coverage"], 1.0)
        self.assertEqual([(p["piece"], p["tucked"], p["top"]) for p in placements],
                         [("Block 2x1 Flat", 0, 0.0), ("Block 1x1 Flat", 1, -fit.TUCK_DROP)])
        self.assertEqual(placements[1]["centre"], [2.0, 0.5])            # wholly on the floor, half under the first
        self.assertEqual(report["tucked"], 1)

    def test_a_strip_too_thin_to_be_worth_a_block_is_left(self):
        placements, report = fitted(slab(0, 0, 2.25, 1))
        self.assertEqual([p["piece"] for p in placements], ["Block 2x1 Flat"])
        self.assertLess(report["coverage"], 1.0)

    def test_only_walked_floor_is_fitted(self):
        a = analysis_of(slab(0, 0, 4, 4), slab(10, 0, 14, 4))
        a["walked"][2:] = False
        placements, report = fit.fit_floors(a)
        self.assertEqual([p["centre"] for p in placements], [[2.0, 2.0]])
        self.assertEqual(report["floor_area"], 16.0)


def analysed(mesh, spawns=((2.0, 2.0, 0.05),)):
    """surfaces.analyse() run for real on a hand-built mesh."""
    reference = {"source": {"game": "halo3", "map": "h3_yard", "scale_from_source": 1.0}, "mesh": "h3_yard.obj",
                 "spawns": [{"pos": list(p), "facing": 0.0, "team": 0, "games": []} for p in spawns],
                 "weapons": [], "objectives": [], "other": []}
    with folder_with(mesh, reference) as folder:
        return surfaces.analyse(folder)


def court(ramp=(8, 3, 12, 5, 2.0)):
    """An 8 x 8 floor, a ramp up from its +x edge (x0, y0, x1, y1, rise) and a floor at the top."""
    m = Mesh()
    m.quad(*slab(0, 0, 8, 8))
    x0, y0, x1, y1, rise = ramp
    m.quad((x0, y0, 0), (x1, y0, rise), (x1, y1, rise), (x0, y1, 0))
    m.quad(*slab(x1, 0, x1 + 4, 8, z=rise))
    return m


class Slopes(unittest.TestCase):
    def test_a_ramp_sized_slope_takes_ramps_that_climb_the_same_way(self):
        placements, report = fit.fit_slopes(analysed(court()))
        self.assertEqual([(p["part"], p["piece"], p["turn"]) for p in placements],
                         [("slope", "Ramp 2x2", 0.0), ("slope", "Ramp 2x2", 0.0)])     # 4 long, 2 wide, 26.6 degrees
        # each ramp's sloping face lies in the slope: middles at x 9 and 11, heights 0.5 and 1.5
        face = pieces.by_name()["Ramp 2x2"]["slope"]
        for p, (x, z) in zip(placements, ((9.0, 0.5), (11.0, 1.5))):
            self.assertAlmostEqual(p["origin"][0], x, delta=0.01)
            self.assertAlmostEqual(p["origin"][1], 4.0, delta=0.01)
            self.assertAlmostEqual(p["origin"][2] + (face["low"] + face["high"]) / 2.0, z, delta=0.01)
        self.assertEqual(report["pieces"], 2)
        self.assertAlmostEqual(report["coverage"], 1.0, delta=0.01)

    def test_a_narrow_slope_takes_the_narrow_ramp_and_a_gentle_one_the_shallow_ramp(self):
        placements, _ = fit.fit_slopes(analysed(court(ramp=(8, 3, 12, 4, 2.0))))
        self.assertEqual([p["piece"] for p in placements], ["Ramp 1x2", "Ramp 1x2"])
        placements, _ = fit.fit_slopes(analysed(court(ramp=(8, 3, 12, 4, 1.0))))
        self.assertEqual([p["piece"] for p in placements], ["Ramp 1x2 Shallow", "Ramp 1x2 Shallow"])

    def test_a_slope_the_other_way_turns_the_ramp(self):
        m = Mesh()
        m.quad(*slab(0, 0, 8, 8))
        m.quad((3, 8, 0), (5, 8, 0), (5, 12, 2), (3, 12, 2))                          # climbs towards +y
        m.quad(*slab(0, 12, 8, 16, z=2.0))
        placements, _ = fit.fit_slopes(analysed(m))
        self.assertEqual([(p["piece"], p["turn"]) for p in placements], [("Ramp 2x2", 90.0), ("Ramp 2x2", 90.0)])
        self.assertAlmostEqual(placements[0]["origin"][1], 9.0, delta=0.01)

    def test_slopes_no_ramp_matches_are_left(self):
        steep = analysed(court(ramp=(8, 3, 9.2, 5, 2.0)))                             # 59 degrees: a wall to the fitter
        self.assertEqual(fit.fit_slopes(steep)[0], [])
        between = analysed(court(ramp=(8, 3, 12, 5, 2.9)))                            # 35.9 degrees: between ramps
        placements, report = fit.fit_slopes(between)
        self.assertEqual(placements, [])
        self.assertGreater(report["slope_area"], 0.0)
        self.assertEqual(report["coverage"], 0.0)


class Walls(unittest.TestCase):
    def mesh(self, length=8.0, height=3.0):
        m = Mesh()
        m.quad(*slab(0, 0, 8, 8))
        m.quad((0, 0, 0), (0, length, 0), (0, length, height), (0, 0, height))        # at x = 0, facing +x
        return m

    def test_a_wall_beside_the_floor_takes_wall_pieces_along_it(self):
        placements, report = fit.fit_walls(analysed(self.mesh()))
        self.assertEqual([(p["part"], p["piece"], p["turn"]) for p in placements],
                         [("wall", "Wall Double", 90.0), ("wall", "Wall Double", 90.0)])
        thick = pieces.by_name()["Wall Double"]["size"][1]
        self.assertEqual([p["origin"][1] for p in placements], [2.0, 6.0])
        for p in placements:
            self.assertAlmostEqual(p["origin"][0], -thick / 2.0, delta=0.001)         # its face on the wall's face
            self.assertAlmostEqual(p["origin"][2], 1.0, delta=0.01)                   # standing on the floor
        self.assertEqual(report, {"pieces": 2, "length": 8.0})

    def test_length_and_height_choose_the_pieces(self):
        got = lambda length, height: [p["piece"] for p in fit.fit_walls(analysed(self.mesh(length, height)))[0]]
        self.assertEqual(got(6.0, 2.0), ["Wall Double", "Wall"])
        self.assertEqual(got(2.0, 2.0), ["Wall"])
        self.assertEqual(got(8.0, 4.0), ["Wall Double"] * 4)                          # two rows
        self.assertEqual(got(8.0, 12.0), ["Wall Double"] * 4)                         # no higher than two rows
        self.assertEqual(got(8.0, 1.0), [])                                           # a kerb, not a wall
        self.assertEqual(got(1.0, 3.0), [])

    def test_both_faces_of_a_thin_wall_make_one_wall(self):
        m = self.mesh()
        m.quad((-0.2, 0, 0), (-0.2, 0, 3), (-0.2, 8, 3), (-0.2, 8, 0))                # its back, facing -x
        placements, _ = fit.fit_walls(analysed(m))
        self.assertEqual(len(placements), 2)

    def test_a_wall_nobody_walks_beside_is_left(self):
        m = Mesh()
        m.quad(*slab(0, 0, 8, 8))
        m.quad((4, 0, 5), (4, 8, 5), (4, 8, 8), (4, 0, 8))                            # hanging 5 above the floor
        self.assertEqual(fit.fit_walls(analysed(m))[0], [])

    def test_a_leaning_wall_is_left(self):
        m = Mesh()
        m.quad(*slab(0, 0, 8, 8))
        m.quad((0, 0, 0), (0, 8, 0), (-0.5, 8, 3), (-0.5, 0, 3))                      # 9.5 degrees off upright
        self.assertEqual(fit.fit_walls(analysed(m))[0], [])


class Placing(unittest.TestCase):
    def test_the_placing_point_allows_for_a_piece_that_is_not_centred(self):
        table = pieces.load()
        piece = pieces.by_name(table)["Block 2x1 Flat"]
        mid_y = (piece["min"][1] + piece["max"][1]) / 2.0
        self.assertNotEqual(mid_y, 0.0)                                  # the table's 2x1 Flat is a little off centre
        flat = {"piece": "Block 2x1 Flat", "centre": [10.0, 20.0], "top": 5.0, "turn": 0.0}
        x, y, z = fit.origin_of(flat, piece)
        self.assertAlmostEqual(x, 10.0, places=6)
        self.assertAlmostEqual(y, 20.0 - mid_y, places=6)
        self.assertAlmostEqual(z, 5.0 - piece["max"][2], places=6)
        x, y, _ = fit.origin_of(dict(flat, turn=90.0), piece)
        self.assertAlmostEqual(x, 10.0 + mid_y, places=6)               # the same shift, turned a quarter
        self.assertAlmostEqual(y, 20.0, places=6)

    def test_pieces_go_into_a_variant_moved_by_the_offset(self):
        placements, _ = fitted(slab(0, 0, 5, 5), slab(0, 5, 1, 10, z=1.0))
        v = forge_world()
        before = len(v.placed_objects())
        slots = fit.add_to(v, placements, (-40.0, -140.0, 8.0))
        self.assertEqual(len(v.placed_objects()), before + 2)
        table = pieces.by_name()
        big, long = v.objects[slots[0]], v.objects[slots[1]]
        self.assertEqual((big.type_index, big.variant_index), (70, table["Block 5x5 Flat"]["item"]))
        self.assertEqual((long.type_index, long.variant_index), (70, table["Block 5x1 Flat"]["item"]))
        self.assertEqual((big.angle, long.angle), (8192, 12288))        # 0 and +90 degrees
        self.assertIsNone(long.up)
        x, y, z = v.world_position(big)
        self.assertAlmostEqual(x, -37.5, delta=0.001)
        self.assertAlmostEqual(y, -137.5, delta=0.001)
        self.assertAlmostEqual(z, 8.0 - table["Block 5x5 Flat"]["max"][2], delta=0.001)
        self.assertEqual(v.quotas[70].placed, 2)
        self.assertEqual(v.problems(), [])

    def test_too_many_pieces_or_a_place_outside_the_map_is_refused(self):
        placements, _ = fitted(slab(0, 0, 5, 5))
        v = forge_world()
        with self.assertRaisesRegex(fit.FitError, "outside Forge World"):
            fit.add_to(v, placements, (5000.0, 0.0, 0.0))
        v = forge_world()
        v.objects = [mvar.ForgeObject(type_index=70) for _ in range(mvar.OBJECT_SLOTS)]
        v.recount_quotas()
        with self.assertRaisesRegex(fit.FitError, "free slots"):
            fit.add_to(v, placements, (0.0, 0.0, 0.0))
        old = forge_world()
        old.quotas.pop()
        with self.assertRaisesRegex(fit.FitError, "Forge World palette"):
            fit.add_to(old, placements, (0.0, 0.0, 0.0))


class Commands(unittest.TestCase):
    def test_fit_writes_the_list_and_the_boxes(self):
        with folder_with(yard()) as folder:
            out = fit.build(folder)
            with open(os.path.join(folder, "fit.json")) as f:
                self.assertEqual(json.load(f), out)
            floors = out["report"]["floors"]
            self.assertEqual(floors["floor_area"], 96.0)                 # the 8 x 8 floor and the 4 x 8 one
            self.assertEqual(floors["coverage"], 1.0)
            self.assertEqual(sorted({p["top"] for p in out["placements"] if p["part"] == "floor"}), [0.0, 2.0])
            # the yard's ramp (4 long, 8 wide, 26.6 degrees) takes eight Ramp 2x2, its wall two Wall Double
            self.assertEqual(out["report"]["slopes"]["pieces"], 8)
            self.assertEqual(out["report"]["walls"]["pieces"], 2)
            self.assertEqual(out["report"]["pieces"], floors["pieces"] + 10)
            self.assertEqual({(p["part"], p["piece"]) for p in out["placements"] if p["part"] != "floor"},
                             {("slope", "Ramp 2x2"), ("wall", "Wall Double")})
            v, t = surfaces.load_obj(os.path.join(folder, out["mesh"]))
            self.assertEqual(len(v), 8 * out["report"]["pieces"])
            self.assertEqual(len(t), 12 * out["report"]["pieces"])       # six faces a box, two triangles each
            self.assertAlmostEqual(float(v[:, 2].max()), 2.0, places=3)  # box tops are the floors
            first = {n: open(os.path.join(folder, n), "rb").read() for n in ("fit.json", out["mesh"])}
            fit.build(folder)
            for name, data in first.items():
                with open(os.path.join(folder, name), "rb") as f:
                    self.assertEqual(f.read(), data, name)

    def test_print_adds_the_fit_to_a_copy_of_the_template(self):
        with folder_with(yard()) as folder:
            out = fit.build(folder)
            v = forge_world()
            template, printed = os.path.join(folder, "template.mvar"), os.path.join(folder, "printed.mvar")
            mvar.MvarFile(variant=v, chdr=mvar.build_chdr(v.header)).write(template)
            with open(template, "rb") as f:
                before = f.read()
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(fit.print_main(folder, template, printed, (-40.0, -140.0, 10.0), "Yard print"), 0)
                self.assertEqual(fit.print_main(folder, template, printed, (-40.0, -140.0, 10.0)), 1)   # never overwrites
            with open(template, "rb") as f:
                self.assertEqual(f.read(), before)
            back = mvar.MvarFile.read(printed)
        self.assertEqual(back.variant.header.title, "Yard print")
        self.assertEqual(len(back.variant.placed_objects()), 2 + out["report"]["pieces"])
        self.assertEqual(back.variant.problems(), [])
        self.assertEqual(back.variant.quotas[70].placed, out["report"]["floors"]["pieces"])   # Building Blocks
        self.assertEqual(back.variant.quotas[75].placed, 8)                                   # Inclines
        self.assertEqual(back.variant.quotas[74].placed, 1 + 2)                               # the template's wall and two

    def test_missing_things_end_in_one_line(self):
        with tempfile.TemporaryDirectory() as empty:
            for run in (lambda: fit.main(empty), lambda: fit.print_main(empty, "none.mvar", os.path.join(empty, "o.mvar"), (0, 0, 0))):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    self.assertEqual(run(), 1)
                self.assertEqual(buf.getvalue().strip().count("\n"), 0)


if __name__ == "__main__":
    unittest.main()
