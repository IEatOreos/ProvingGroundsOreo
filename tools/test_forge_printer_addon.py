"""Reach Forge Printer, phase 4: the Blender add-on's plain modules (no Blender needed).

A Blender object is stood in for by its world matrix, rounded to 32-bit floats as Blender keeps
it. The template is a hand-built Forge World variant (test_forge_printer_turn_test.forge_world).
"""

import io
import json
import math
import os
import struct
import tempfile
import unittest
from contextlib import redirect_stdout

from forge_printer import fit, mvar, pieces, turn_test
from forge_printer.blender_addon import convert, export
from test_forge_printer_turn_test import forge_world

KNOWN = pieces.by_name()
OFFSET = (-40.0, -140.0, 10.0)


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


def blender(matrix):
    """A matrix as Blender holds it: 32-bit floats."""
    return [[f32(v) for v in row] for row in matrix]


def rows_from(x_axis, y_axis, z_axis, origin, scale=(1.0, 1.0, 1.0)):
    return [[x_axis[i] * scale[0], y_axis[i] * scale[1], z_axis[i] * scale[2], origin[i]] for i in range(3)] + [
        [0.0, 0.0, 0.0, 1.0]]


def box(name):
    return KNOWN[name]["min"], KNOWN[name]["max"]


def entry(label, matrix, name, props=None, local=True):
    p, reason, warning = convert.placement_from(blender(matrix), name, KNOWN, props, box(name) if local else None)
    return {"label": label, "placement": p, "reason": reason, "warning": warning}


def flat(name, x, y, z, turn=0.0, **props):
    return entry("%s at %g %g" % (name, x, y), convert.matrix_for({"origin": (x, y, z), "turn": turn}), name, props)


def raw_of(placement):
    """(raw turn, raw up or None) as fit.add_to writes a placement."""
    return (mvar.encode_angle(math.radians(placement["turn"])),
            mvar.up_raw(placement["up"]) if "up" in placement else None)


def turn_steps(a, b):
    d = abs(a - b) % (1 << mvar.ANGLE_BITS)
    return min(d, (1 << mvar.ANGLE_BITS) - d)


def template_file(folder, v=None):
    v = v or forge_world()
    path = os.path.join(folder, "template.mvar")
    mvar.MvarFile(variant=v, chdr=mvar.build_chdr(v.header)).write(path)
    return path


class Conversion(unittest.TestCase):
    def test_box_mesh_is_the_piece_box_with_outward_faces(self):
        piece = KNOWN["Ramp 1x2"]
        verts, quads = convert.box_mesh(piece)
        self.assertEqual([min(v[i] for v in verts) for i in range(3)], piece["min"])
        self.assertEqual([max(v[i] for v in verts) for i in range(3)], piece["max"])
        middle = [(piece["min"][i] + piece["max"][i]) / 2.0 for i in range(3)]
        for q in quads:
            a, b, c = (verts[i] for i in q[:3])
            n = convert._cross([b[i] - a[i] for i in range(3)], [c[i] - b[i] for i in range(3)])
            out = [sum(verts[i][k] for i in q) / 4.0 - middle[k] for k in range(3)]
            self.assertGreater(convert._dot(n, out), 0.0)

    def test_open_then_read_back_gives_the_same_raw_numbers(self):
        cases = [{"piece": "Block 5x5 Flat", "origin": [1.5, -10.0, 17.553], "turn": 0.0},
                 {"piece": "Wall", "origin": [-3.5, -23.6, 17.05], "turn": 90.0},
                 {"piece": "Block 2x1 Flat", "origin": [4.0, 2.0, 16.0], "turn": -179.989},
                 {"piece": "Block 5x1 Flat", "origin": [9.699, -4.198, 16.671], "turn": -179.989,
                  "up": [0.0, 0.351123, 0.936329]},
                 {"piece": "Block 3x1 Flat", "origin": [0.0, 0.0, 0.0], "turn": 33.0,
                  "up": list(mvar.up_vector(mvar.join_up(0, 250, 180)))}]
        for p in cases:
            back, reason, warning = convert.placement_from(blender(convert.matrix_for(p)), p["piece"], KNOWN)
            self.assertIsNone(reason)
            self.assertIsNone(warning)
            for i in range(3):
                self.assertAlmostEqual(back["origin"][i], p["origin"][i], delta=1e-5)
            want, got = raw_of(p), raw_of(back)
            self.assertLessEqual(turn_steps(want[0], got[0]), 1, p)
            self.assertEqual(want[1], got[1], p)
            self.assertEqual("up" in back, "up" in p)                  # untilted stays "the world's up", as print writes

    def test_square_turns_come_back_exactly(self):
        # +90 is a step boundary: Blender's 32-bit 89.99999 must still write print's 12288
        for turn in (0.0, 90.0, 180.0, -90.0, 45.0):
            p = {"piece": "Wall", "origin": [0.0, 0.0, 0.0], "turn": turn}
            back, _, _ = convert.placement_from(blender(convert.matrix_for(p)), "Wall", KNOWN)
            self.assertEqual(raw_of(back)[0], raw_of(p)[0], turn)

    def test_carried_fields_and_added_pieces(self):
        m = convert.matrix_for({"origin": (0, 0, 0), "turn": 0.0})
        p, _, _ = convert.placement_from(m, "Block 1x1 Flat", KNOWN, {"part": "floor", "fill": 1, "size": [1.0, 1.0]})
        self.assertEqual((p["part"], p["fill"], p["size"]), ("floor", 1, [1.0, 1.0]))
        p, _, _ = convert.placement_from(m, "Block 1x1 Flat", KNOWN)
        self.assertEqual(p["part"], "added")

    def test_the_eight_slope_test_cases(self):
        """An object turned in Blender the way each slope-test ramp lies exports what the slope test wrote."""
        written = {label: (turn, up) for label, name, _, turn, up in turn_test.slope_pieces(KNOWN)
                   if name == turn_test.SLOPE_RAMP}
        self.assertEqual(len(written), len(turn_test.SLOPE_CHECKS))
        for label, heading, slope in turn_test.SLOPE_CHECKS:
            around, lean = math.radians(heading), math.radians(slope)
            climb = (math.cos(around), math.sin(around))
            x_axis = (math.cos(lean) * climb[0], math.cos(lean) * climb[1], math.sin(lean))   # up the slope
            z_axis = (-math.sin(lean) * climb[0], -math.sin(lean) * climb[1], math.cos(lean))
            y_axis = convert._cross(z_axis, x_axis)
            p, reason, _ = convert.placement_from(blender(rows_from(x_axis, y_axis, z_axis, (3.0, -4.0, 5.0))),
                                                  turn_test.SLOPE_RAMP, KNOWN)
            self.assertIsNone(reason, label)
            raw_turn, raw_up = raw_of(p)
            want_turn, want_up = written[label]
            self.assertLessEqual(turn_steps(raw_turn, want_turn), 1, label)
            got, want = export._up_parts(raw_up), export._up_parts(want_up)
            self.assertEqual(got[0], want[0], label)
            self.assertLessEqual(max(abs(got[1] - want[1]), abs(got[2] - want[2])), 1, label)

    def test_float_noise_on_an_axis_is_still_that_axis(self):
        # a piece laid on its side, facing +Y, as Blender's rotate leaves it: a hair off the axis
        z_axis, x_axis = (0.0, 0.99999994, -4.37e-8), (1.0, 0.0, 0.0)
        p, reason, warning = convert.placement_from(rows_from(x_axis, convert._cross(z_axis, x_axis), z_axis, (0, 0, 0)),
                                                    "Wall", KNOWN)
        self.assertIsNone(reason)
        self.assertEqual(mvar.up_raw(p["up"]), mvar.join_up(1))
        self.assertIsNone(warning)

    def test_upside_down_is_written_with_a_warning(self):
        p, reason, warning = convert.placement_from(rows_from((1, 0, 0), (0, -1, 0), (0, 0, -1), (0, 0, 0)), "Wall", KNOWN)
        self.assertIsNone(reason)
        self.assertEqual(mvar.up_raw(p["up"]), mvar.join_up(5))
        self.assertIn("-Z", warning)


class Refusals(unittest.TestCase):
    def test_a_scaled_piece(self):
        m = rows_from((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0), scale=(1.2, 1.2, 1.2))
        e = entry("big", m, "Block 2x2 Flat", local=True)
        self.assertIsNone(e["placement"])
        self.assertIn("scaled 1.20 x 1.20 x 1.20", e["reason"])
        e = entry("tall", rows_from((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0), scale=(1, 1, 1.2)), "Block 2x2 Flat")
        self.assertIn("cannot scale", e["reason"])

    def test_a_mirrored_piece(self):
        e = entry("mirror", rows_from((1, 0, 0), (0, -1, 0), (0, 0, 1), (0, 0, 0)), "Block 2x2 Flat")
        self.assertIn("mirrored", e["reason"])

    def test_a_piece_leaning_50_degrees(self):
        lean = math.radians(50.0)
        z_axis = (0.0, -math.sin(lean), math.cos(lean))                 # leaning towards -y: 50 from +Z, 90 from +X
        e = entry("lean", rows_from((1, 0, 0), convert._cross(z_axis, (1, 0, 0)), z_axis, (0, 0, 0)), "Block 5x1 Flat")
        self.assertIsNone(e["placement"])
        self.assertIn("leans 50 degrees", e["reason"])
        # leaning 50 towards +x is 40 from +X: the +X face holds it
        z_axis = (math.sin(lean), 0.0, math.cos(lean))
        x_axis = (math.cos(lean), 0.0, -math.sin(lean))
        e = entry("east", rows_from(x_axis, convert._cross(z_axis, x_axis), z_axis, (0, 0, 0)), "Block 5x1 Flat")
        self.assertIsNone(e["reason"])
        self.assertEqual(mvar.up_raw(e["placement"]["up"]) // mvar.UP_FACE_SPAN, 0)

    def test_a_reshaped_piece_and_an_unknown_one(self):
        m = convert.matrix_for({"origin": (0, 0, 0), "turn": 0.0})
        lo, hi = box("Block 2x2 Flat")
        _, reason, _ = convert.placement_from(m, "Block 2x2 Flat", KNOWN, None, (lo, [hi[0] * 1.2, hi[1], hi[2]]))
        self.assertIn("shape", reason)
        _, reason, _ = convert.placement_from(m, "Block 9x9", KNOWN)
        self.assertIn("not a Forge piece", reason)

    def test_a_piece_outside_the_bounds(self):
        v = forge_world()
        result = export.plan([flat("Block 2x2 Flat", 0.0, 0.0, 0.0), flat("Block 2x2 Flat", 400.0, 0.0, 0.0)], v, OFFSET)
        self.assertEqual(len(result["kept"]), 1)
        self.assertEqual([label for label, _ in result["refused"]], ["Block 2x2 Flat at 400 0"])
        self.assertIn("outside Forge World", result["refused"][0][1])
        self.assertIn("cannot be written", export.lines(result)[0])

    def test_256_pieces_in_one_row(self):
        v = forge_world()                                                  # nothing in row 70 yet
        entries = [flat("Block 1x1 Flat", -50.0 + (n % 16) * 1.1, -50.0 + (n // 16) * 1.1, 0.0) for n in range(256)]
        result = export.plan(entries, v, OFFSET)
        self.assertEqual(len(result["kept"]), 255)
        self.assertEqual(len(result["left_out"]), 1)
        self.assertEqual(result["counts"]["rows_over"], {70: 1})
        text = "\n".join(export.lines(result))
        self.assertIn("Building Blocks (row 70) would hold 256 pieces; a row holds 255", text)
        self.assertIn("room in a palette row", text)

    def test_nothing_to_report_when_everything_fits(self):
        result = export.plan([flat("Wall", 0.0, 0.0, 0.0, 90.0)], forge_world(), OFFSET)
        self.assertEqual(export.lines(result), [])


class Counter(unittest.TestCase):
    """The counter's figures against fit.within_limits for the same scene."""

    def within(self, entries, v):
        free, budget, rows = export.room(v)
        return fit.within_limits([e["placement"] for e in entries], free, budget, rows)

    def test_a_scene_that_fits(self):
        v = forge_world()
        entries = ([flat("Block 2x2 Flat", n * 2.1, 0.0, 0.0) for n in range(30)] +
                   [flat("Wall", n * 2.1, 5.0, 0.0, 90.0) for n in range(10)] +
                   [flat("Bridge Small", 0.0, 10.0, 0.0), flat("Ramp 2x2", 0.0, 15.0, 0.0)])
        counts = export.count([e["placement"] for e in entries], v)
        kept, report = self.within(entries, v)
        self.assertEqual(len(kept), len(entries))
        self.assertEqual(counts["slots_used"] - len(v.placed_objects()), report["kept"])
        self.assertEqual(counts["budget_added"], report["cost"])
        self.assertEqual(counts["budget_spent"], v.budget_spent + report["cost"])
        self.assertEqual(counts["unpriced"], 1)
        self.assertEqual(counts["unpriced_names"], report["unpriced"])
        self.assertEqual(counts["rows"][70], 30)
        self.assertEqual(counts["rows"][74], 10 + v.quotas[74].placed)
        self.assertEqual((counts["rows_over"], counts["slots_over"], counts["budget_over"]), ({}, 0, 0))

    def test_a_row_too_full(self):
        v = forge_world()
        entries = [flat("Block 1x1 Flat", (n % 20) * 1.1, (n // 20) * 1.1, 0.0) for n in range(299)]
        counts = export.count([e["placement"] for e in entries], v)
        _, report = self.within(entries, v)
        self.assertEqual(counts["rows_over"], {70: 44})
        self.assertEqual(report["left_out"], 44)

    def test_too_many_objects(self):
        v = forge_world()                                                    # 2 objects, 649 free slots
        entries = ([flat("Block 1x1 Flat", (n % 20) * 1.1, (n // 20) * 1.1, 0.0) for n in range(250)] +
                   [flat("Wall", (n % 20) * 2.1, 40.0 + (n // 20) * 2.1, 0.0) for n in range(250)] +
                   [flat("Ramp 1x2", (n % 20) * 2.1, -40.0 - (n // 20) * 1.1, 0.0) for n in range(200)])
        counts = export.count([e["placement"] for e in entries], v)
        _, report = self.within(entries, v)
        self.assertEqual(counts["slots_used"], 702)
        self.assertEqual(counts["slots_over"], 51)
        self.assertEqual(report["left_out"], 51)
        self.assertEqual(report["ran_out_of"], "object slots")

    def test_over_budget(self):
        v = forge_world()
        v.budget_max = v.budget_spent + 100                                  # ten pieces at 10
        entries = [flat("Block 2x2 Flat", n * 2.1, 0.0, 0.0) for n in range(12)]
        counts = export.count([e["placement"] for e in entries], v)
        _, report = self.within(entries, v)
        self.assertEqual(counts["budget_over"], 20)
        self.assertEqual(report["left_out"], 2)

    def test_without_a_template(self):
        counts = export.count([flat("Wall", 0, 0, 0)["placement"]])
        self.assertEqual((counts["slots_used"], counts["budget_spent"], counts["budget_max"]), (1, 10, None))


class Export(unittest.TestCase):
    def test_export_equals_print_for_the_same_fit(self):
        """A fit opened as objects and exported at once writes what `forge_printer print` writes."""
        placements = [
            {"part": "floor", "piece": "Block 5x5 Flat", "turn": 0.0, "origin": [1.5, -10.0, 17.553], "size": [5.0, 5.0]},
            {"part": "floor", "piece": "Block 1x1 Flat", "turn": 0.0, "origin": [4.4, -7.0, 17.55], "size": [1.0, 1.0],
             "fill": True},
            {"part": "slope", "piece": "Block 5x1 Flat", "turn": -179.989, "up": [0.0, 0.351123, 0.936329],
             "origin": [9.699, -4.198, 16.671]},
            {"part": "slope", "piece": "Block 3x1 Flat", "turn": 63.4, "up": list(mvar.up_vector(mvar.join_up(2, 260, 236))),
             "origin": [2.0, 3.0, 15.0]},
            {"part": "landing", "piece": "Block 2x1 Flat", "turn": 0.0, "origin": [10.2, -1.952, 16.019]},
            {"part": "wall", "piece": "Wall Double", "turn": 90.0, "origin": [-3.542, -23.64, 17.05]},
            {"part": "wall", "piece": "Wall", "turn": -45.0, "origin": [-6.0, -20.0, 17.05]}]
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "fit.json"), "w", encoding="utf-8") as f:
                json.dump({"source": {"map": "h3_test"}, "placements": placements}, f)
            template = template_file(folder)
            printed = os.path.join(folder, "printed.mvar")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(fit.print_main(folder, template, printed, OFFSET), 0)
            entries = [entry(str(i), convert.matrix_for(p), p["piece"], {k: p.get(k) for k in convert.CARRIED})
                       for i, p in enumerate(placements)]
            v = export.load_template(template).variant
            result = export.plan(entries, v, OFFSET)
            self.assertEqual(export.lines(result), [])
            out = export.free_path(folder, "FP Test edit")
            info = export.write(template, result, OFFSET, out, "FP Test edit")
            self.assertEqual(os.path.basename(out), "FP_Test_edit.mvar")
            self.assertEqual(info["problems"], [])
            self.assertEqual(info["objects"], 2 + len(placements))
            a, b = mvar.MvarFile.read(printed).variant, mvar.MvarFile.read(out).variant
            self.assertEqual(export.differences(a, b), [])
            self.assertEqual(b.budget_spent, a.budget_spent)
            self.assertEqual(mvar.MvarFile.read(out).variant.header.title, "FP Test edit")
            # never over a file: the next name is new, and writing to an existing path refuses
            self.assertEqual(os.path.basename(export.free_path(folder, "FP Test edit")), "FP_Test_edit_2.mvar")
            with self.assertRaises(export.ExportError):
                export.write(template, result, OFFSET, out, "again")

    def test_differences_are_found(self):
        a, b = forge_world(), forge_world()
        obj = b.objects[0]
        x, y, z = b.world_position(obj)
        b.set_world_position(obj, x + 0.01, y, z)
        obj.angle += 2
        self.assertEqual(len(export.differences(a, b)), 1)
        self.assertIn("apart", export.differences(a, b)[0][1])
        b.objects[5] = mvar.ForgeObject()
        self.assertEqual(export.differences(a, b)[-1], (5, "only in the second"))
        # the world's up and the +Z face's middle are the same direction
        b = forge_world()
        b.objects[2].up = mvar.join_up(2)
        self.assertEqual(export.differences(a, b), [])

    def test_template_must_be_forge_world(self):
        with tempfile.TemporaryDirectory() as folder:
            v = forge_world()
            v.map_id = 1000
            with self.assertRaises(export.ExportError):
                export.load_template(template_file(folder, v))
            with self.assertRaises(export.ExportError):
                export.load_template(os.path.join(folder, "none.mvar"))
            with self.assertRaises(export.ExportError):
                export.load_template("")


if __name__ == "__main__":
    unittest.main()
