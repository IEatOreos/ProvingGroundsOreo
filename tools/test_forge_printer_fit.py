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
        placements, _ = fitted(slab(0, 0, 2, 4, z=0.0), slab(2, 0, 4, 4, z=0.1))       # a kerb: levelled
        self.assertEqual([p["piece"] for p in placements], ["Block 4x4 Flat"])
        placements, _ = fitted(slab(0, 0, 2, 4, z=0.0), slab(2, 0, 4, 4, z=0.3))       # a ledge: kept
        self.assertEqual(sorted({p["top"] for p in placements}), [0.0, 0.3])
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

    def test_blocks_of_one_level_all_sit_at_one_height(self):
        # most of the floor at 0, a strip a tenth higher: one level, every block's top where most of it is
        placements, _ = fitted(slab(0, 0, 6, 4, z=0.0), slab(6, 0, 8, 4, z=0.1))
        self.assertEqual({p["top"] for p in placements if not p["tucked"]}, {0.0})
        self.assertGreater(len(placements), 1)

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

    def ends(self, placements):
        """[(low end height, high end height)] of each placed ramp's sloping face."""
        table = pieces.by_name()
        out = []
        for p in placements:
            piece = table[p["piece"]]
            if "slope" in piece:
                out.append((p["origin"][2] + piece["slope"]["low"], p["origin"][2] + piece["slope"]["high"]))
            else:
                out.append((p["origin"][2] + piece["max"][2],) * 2)                  # a flat block: its top
        return out

    def test_a_slope_between_two_ramp_angles_mixes_them_and_they_still_join(self):
        # 20 degrees, where the owner's screenshot showed two 26.6-degree ramps stepping: 1.456 up over 4
        placements, _ = fit.fit_slopes(analysed(court(ramp=(8, 3, 12, 4, 1.456))))
        self.assertEqual([p["piece"] for p in placements], ["Ramp 1x2", "Ramp 1x2 Shallow"])   # from the bottom up
        (low1, high1), (low2, high2) = self.ends(placements)
        self.assertAlmostEqual(low1, 0.0, delta=0.03)                                 # starts on the lower floor
        self.assertAlmostEqual(high1, low2, delta=0.02)                               # no step between the two
        self.assertAlmostEqual(high2, 1.456, delta=0.03)                              # ends at the upper floor

    def test_a_very_gentle_slope_takes_a_level_step_now_and_then(self):
        # 10.6 degrees: 0.75 up over 4 is a flat block's worth and a shallow ramp, or the other way round
        placements, _ = fit.fit_slopes(analysed(court(ramp=(8, 3, 12, 4, 0.72))))
        # 0.72 up over 4: a shallow ramp, a level step, and a third piece that takes the foot under the lower floor
        self.assertEqual([p["piece"] for p in placements], ["Ramp 1x2 Shallow", "Block 2x1 Flat", "Ramp 1x2 Shallow"])
        ends = self.ends(placements)
        for (_, high), (low, _) in zip(ends, ends[1:]):
            self.assertAlmostEqual(high, low, delta=0.02)
        self.assertAlmostEqual(ends[-1][1], 0.72, delta=0.02)        # its top is exactly at the upper floor
        self.assertAlmostEqual(ends[1][0], 0.22, delta=0.02)         # at the lower floor's edge it is above the floor,
        self.assertLess(ends[0][0], 0.0)                             # and its foot is under it: no lip either way
        placements, _ = fit.fit_slopes(analysed(court(ramp=(8, 3, 14, 4, 1.1))))      # 10.4 degrees over 6
        names = [p["piece"] for p in placements]
        self.assertIn(len(names), (3, 4))
        self.assertIn("Block 2x1 Flat", names)
        ends = self.ends(placements)
        for (_, high), (low, _) in zip(ends, ends[1:]):
            self.assertAlmostEqual(high, low, delta=0.02)
        self.assertAlmostEqual(ends[-1][1], 1.1, delta=0.03)

    def test_a_steeper_slope_uses_the_wide_ramps_and_they_join_too(self):
        placements, report = fit.fit_slopes(analysed(court(ramp=(8, 3, 12, 5, 2.9))))   # 35.9 degrees
        # a steep and a 2x2 ramp drop 3.0, which would leave 0.05 of floor proud at each end; so instead the
        # run drops 2.5 by the lower floor's edge and a third row takes it down into that floor (bottom up):
        self.assertEqual([p["piece"] for p in placements],
                         ["Ramp 2x2", "Ramp 1x2 Shallow", "Ramp 1x2 Shallow", "Ramp 2x2 Steep"])
        ends = self.ends(placements)
        self.assertAlmostEqual(ends[-1][1], 2.9, delta=0.02)         # its top is at the upper floor
        self.assertAlmostEqual(ends[-1][0], ends[1][1], delta=0.02)  # the steep ramp stands on the shallow pair,
        self.assertAlmostEqual(ends[1][1], ends[2][1], delta=0.001)  # which are side by side,
        self.assertAlmostEqual(ends[1][0], ends[0][1], delta=0.02)   # and they stand on the bottom ramp
        self.assertAlmostEqual(ends[0][1], 0.4, delta=0.02)          # at the lower floor's edge it is above the floor
        self.assertLess(ends[0][0], 0.0)                             # and its foot is under it
        self.assertGreater(report["coverage"], 0.9)

    def test_two_lanes_of_shallow_ramps_stay_two_pieces_wide(self):
        placements, _ = fit.fit_slopes(analysed(court(ramp=(8, 3, 12, 5, 1.0))))      # 14 degrees, 2 wide
        self.assertEqual([p["piece"] for p in placements], ["Ramp 1x2 Shallow"] * 4)
        self.assertEqual(sorted({p["origin"][1] for p in placements}), [3.5, 4.5])

    def test_a_ramp_that_is_not_a_whole_number_of_pieces_long_is_tied_to_its_floors(self):
        # 2.9 long and 1.56 up, like the one in the owner's screenshot that stopped short of its floor
        a = analysed(court(ramp=(8, 3, 10.9, 5, 1.56)))
        floors, _ = fit.fit_floors(a)
        everything, report = fit.fit_slopes(a, floors=floors)
        table = pieces.by_name()
        placements = [p for p in everything if p["part"] == "slope"]
        self.assertEqual(len(placements), 2)                         # two pieces: 4 units for a 2.9-unit slope
        # the upper floor's blocks are on the quarter-unit grid and start at 11.0, a slit past the ramp's top
        # at 10.9: a landing turned across the ramp goes under the join, a hair below the floor
        (landing,) = [p for p in everything if p["part"] == "landing"]
        self.assertEqual((landing["piece"], landing["turn"], landing["top"], report["landings"]),
                         ("Block 2x1 Flat", 90.0, 1.555, 1))
        self.assertAlmostEqual(landing["origin"][0], 10.9 + 0.5, delta=0.03)
        self.assertAlmostEqual(landing["origin"][1], 4.0, delta=0.01)
        ends = self.ends(placements)
        self.assertAlmostEqual(ends[-1][1], 1.56, delta=0.13)        # its top is at the upper floor
        top = placements[-1]
        face = table[top["piece"]]["slope"]
        self.assertAlmostEqual(top["origin"][0] + face["run"] / 2.0, 10.9, delta=0.02)   # ... and at its edge
        self.assertAlmostEqual(ends[0][1], ends[1][0], delta=0.02)   # the two join
        self.assertLess(ends[0][0], 0.0)                             # its foot is under the lower floor, not above it
        foot = placements[0]
        self.assertLess(foot["origin"][0] - table[foot["piece"]]["slope"]["run"] / 2.0, 8.0)   # ... and reaches past its edge

    def test_ramp_ends_take_the_height_of_the_floor_blocks_beside_them(self):
        a = analysed(court(ramp=(8, 3, 12, 5, 2.0)))
        floors, _ = fit.fit_floors(a)
        for p in floors:
            if p["top"] == 2.0:
                p["top"] = 2.2                                       # say the upper floor was built a little high
        placements, report = fit.fit_slopes(a, floors=floors)
        self.assertAlmostEqual(self.ends(placements)[-1][1], 2.2, delta=0.13)
        self.assertEqual(report["landings"], 0)                      # the floor blocks reach the ramp: nothing to add

    def test_a_landing_fills_the_gap_where_the_floor_blocks_stop_short_of_a_ramp(self):
        a = analysed(court(ramp=(8, 3, 12, 5, 2.0)))
        floors, _ = fit.fit_floors(a)
        whole, _ = fit.fit_slopes(a, floors=floors)
        self.assertEqual({p["part"] for p in whole}, {"slope"})
        # take away the lower floor's blocks beside the ramp's foot: the ramp would end in a hole
        kept = [p for p in floors if not (p["top"] == 0.0 and p["centre"][0] + p["size"][0] / 2.0 > 6.5
                                          and abs(p["centre"][1] - 4.0) < 1.0 + p["size"][1] / 2.0)]
        self.assertLess(len(kept), len(floors))
        placements, report = fit.fit_slopes(a, floors=kept)
        (landing,) = [p for p in placements if p["part"] == "landing"]
        self.assertEqual((landing["piece"], landing["turn"], landing["top"]), ("Block 2x1 Flat", 90.0, -0.005))
        self.assertAlmostEqual(landing["origin"][0], 8.0 - 0.5, delta=0.03)      # the unit of floor before the ramp
        self.assertAlmostEqual(landing["origin"][1], 4.0, delta=0.01)

    def test_no_landing_where_the_reference_has_no_floor(self):
        m = Mesh()                                                   # a ramp that ends in mid air: nothing at its top
        m.quad(*slab(0, 0, 8, 8))
        m.quad((8, 3, 0), (12, 3, 2.0), (12, 5, 2.0), (8, 5, 0))
        a = analysed(m)
        floors, _ = fit.fit_floors(a)
        placements, report = fit.fit_slopes(a, floors=floors)
        self.assertEqual([p["part"] for p in placements], ["slope", "slope"])
        self.assertEqual(report["landings"], 0)

    def test_a_slope_that_dives_under_a_floor_is_not_a_ramp(self):
        m = court()
        m.quad((2, 3, -1.9), (2, 5, -1.9), (6, 5, 0.1), (6, 3, 0.1))    # a brace coming up through the lower floor
        a = analysed(m)
        floors, _ = fit.fit_floors(a)
        with_floors, _ = fit.fit_slopes(a, floors=floors)
        self.assertEqual({p["origin"][0] > 8.0 for p in with_floors}, {True})          # only the real ramp
        self.assertEqual(len(with_floors), 2)

    def test_best_run(self):
        gentle, all_four = [0.0, 0.5, 1.0], [0.0, 0.5, 1.0, 2.0]
        self.assertEqual(fit._best_run(gentle, 4.0, 2.0), ([1.0, 1.0], 0.0))          # a slope the pieces fit exactly
        run, lift = fit._best_run(gentle, 4.0, 1.456)                                 # 20 degrees: 0.044 too much drop
        self.assertEqual(run, [0.5, 1.0])                                             # top piece first
        self.assertAlmostEqual(lift, 0.022, places=3)                                 # half of it moved to the top
        self.assertEqual(fit._best_run(all_four, 4.0, 2.5), ([0.5, 2.0], 0.0))        # 1 + 1 would stop half a unit short
        # the slope from the owner's screenshot, 4.15 long and 1.42 up: nothing fits within a small lip, so the
        # run stays above the lower floor at its edge and a third piece takes the foot under it
        run, lift = fit._best_run(gentle, 4.15, 1.42)
        self.assertEqual((run, lift), ([0.5, 0.5, 0.5], 0.0))                         # and that piece keeps the angle
        self.assertGreaterEqual(sum(run), 1.42)
        long_run, long_lift = fit._best_run(gentle, 18.0, 4.5)                        # a long slope is followed from the top
        self.assertEqual((len(long_run), sum(long_run), long_lift), (9, 4.5, 0.0))

    def test_the_floor_never_stands_proud_of_a_ramp_by_more_than_a_hair(self):
        # every length and rise a walkway ramp might have: where the run stands at the lower floor's edge
        for tenths in range(13, 60, 3):
            length = tenths / 10.0
            for rise_hundredths in range(30, int(length * 45), 17):
                rise = rise_hundredths / 100.0
                run, lift = fit._best_run([0.0, 0.5, 1.0], length, rise)
                whole = int(length // 2)
                at_edge = sum(run[:whole]) + (run[whole] * (length - whole * 2) / 2.0 if whole < len(run) else 0.0)
                under = (at_edge - lift) - rise                                       # the floor proud of the ramp
                self.assertLessEqual(under, 0.07, (length, rise, run))
                self.assertLessEqual(lift, 0.07, (length, rise, run))                 # the ramp's top proud of its floor
                self.assertGreaterEqual(sum(run) + 0.02, rise - lift, (length, rise, run))   # the foot gets down

    def test_slopes_no_ramp_can_follow_are_left(self):
        steep = analysed(court(ramp=(8, 3, 9.2, 5, 2.0)))                             # 59 degrees: a wall to the fitter
        self.assertEqual(fit.fit_slopes(steep)[0], [])
        cliff = analysed(court(ramp=(8, 3, 10, 5, 2.3)))                              # 49 degrees: steeper than any ramp
        placements, report = fit.fit_slopes(cliff)
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


class Limits(unittest.TestCase):
    def pieces_for_a_yard(self):
        floors, _ = fitted(slab(0, 0, 5, 5), slab(6, 0, 8, 2), slab(9, 0, 10, 1))      # a 5x5, a 2x2 and a 1x1
        ramp = {"part": "slope", "piece": "Ramp 1x2", "turn": 0.0, "origin": [0.0, 0.0, 0.0]}
        wall = {"part": "wall", "piece": "Wall", "turn": 0.0, "origin": [0.0, 0.0, 0.0]}
        return [wall, ramp] + floors[::-1]                                             # in no helpful order

    def test_everything_fits_when_there_is_room(self):
        placements = self.pieces_for_a_yard()
        kept, report = fit.within_limits(placements, 600, 29000)
        self.assertEqual(kept, placements)
        self.assertEqual(report, {"kept": 5, "left_out": 0, "by_part": {}, "ran_out_of": None, "cost": 50,
                                  "unpriced": []})

    def test_slots_run_out_walls_first_then_ramps_then_the_smallest_floors(self):
        placements = self.pieces_for_a_yard()
        kept, report = fit.within_limits(placements, 3, 29000)
        self.assertEqual(sorted(p["piece"] for p in kept), ["Block 1x1 Flat", "Block 2x2 Flat", "Block 5x5 Flat"])
        self.assertEqual((report["left_out"], report["by_part"], report["ran_out_of"]),
                         (2, {"slope": 1, "wall": 1}, "object slots"))
        kept, report = fit.within_limits(placements, 1, 29000)
        self.assertEqual([p["piece"] for p in kept], ["Block 5x5 Flat"])
        self.assertEqual(report["by_part"], {"floor": 2, "slope": 1, "wall": 1})

    def test_budget_runs_out_the_same_way(self):
        placements = self.pieces_for_a_yard()
        kept, report = fit.within_limits(placements, 600, 40)
        self.assertEqual([p["part"] for p in kept], ["slope", "floor", "floor", "floor"])   # kept in their own order
        self.assertEqual((report["cost"], report["left_out"], report["ran_out_of"]), (40, 1, "budget"))
        self.assertEqual(fit.within_limits(placements, 600, 5)[0], [])

    def test_a_piece_with_no_known_price_is_named(self):
        dish = {"part": "floor", "piece": "Dish", "turn": 0.0, "origin": [0.0, 0.0, 0.0], "size": [11.7, 5.9]}
        kept, report = fit.within_limits([dish], 10, 0)
        self.assertEqual((len(kept), report["unpriced"], report["cost"]), (1, ["Dish"], 0))


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
        cost, unpriced = pieces.cost([p["piece"] for p in out["placements"]])
        self.assertEqual(back.variant.budget_spent, 130 + cost)                               # the stored figure follows
        self.assertEqual(unpriced, ["Block 4x4 Flat"])                                        # not yet seen on the HUD
        self.assertIn("budget %d of 30000 spent" % back.variant.budget_spent, buf.getvalue())
        self.assertIn("no price known for Block 4x4 Flat", buf.getvalue())
        self.assertNotIn("LEFT OUT", buf.getvalue())

    def test_print_says_what_it_left_out_when_the_budget_runs_short(self):
        with folder_with(yard()) as folder:
            out = fit.build(folder)
            v = forge_world()
            v.budget_max = v.budget_spent + 50                     # room for five pieces
            template, printed = os.path.join(folder, "template.mvar"), os.path.join(folder, "printed.mvar")
            mvar.MvarFile(variant=v, chdr=mvar.build_chdr(v.header)).write(template)
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(fit.print_main(folder, template, printed, (-40.0, -140.0, 10.0)), 0)
            back = mvar.MvarFile.read(printed)
        added = len(back.variant.placed_objects()) - 2
        free = sum(1 for p in out["placements"] if p["piece"] == "Block 4x4 Flat")            # no price known: not counted
        self.assertEqual(added, 5 + free)
        self.assertEqual(back.variant.budget_spent, back.variant.budget_max)
        self.assertIn("LEFT OUT %d pieces, out of budget" % (out["report"]["pieces"] - added), buf.getvalue())
        self.assertEqual(back.variant.quotas[75].placed, 0)                                   # floors are kept first

    def test_missing_things_end_in_one_line(self):
        with tempfile.TemporaryDirectory() as empty:
            for run in (lambda: fit.main(empty), lambda: fit.print_main(empty, "none.mvar", os.path.join(empty, "o.mvar"), (0, 0, 0))):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    self.assertEqual(run(), 1)
                self.assertEqual(buf.getvalue().strip().count("\n"), 0)


if __name__ == "__main__":
    unittest.main()
