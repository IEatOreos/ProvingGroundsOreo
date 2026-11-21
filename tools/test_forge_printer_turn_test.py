"""Reach Forge Printer, phase 3: the test map that shows in the game how turns and tilts are stored.

The variant the pieces are added to is built by hand here (a bare Forge World palette).
"""

import io
import math
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from forge_printer import mvar, pieces, turn_test

ORIGIN = (-31.0, -131.5, 5.21)


def forge_world():
    v = mvar.MapVariant()
    v.version, v.v32_block, v.map_id = 32, 0xD1 << 120, pieces.FORGE_WORLD_MAP_ID
    v.header = mvar.ContentHeader(map_id=v.map_id, title="Yard")
    v.bounds = (-203.6, 277.66, -360.83, 324.92, -25.01, 117.79)
    v.budget_max, v.budget_spent = 30000, 130
    v.quotas = [mvar.Quota() for _ in range(pieces.FORGE_WORLD_QUOTA_ROWS)]
    wall = mvar.ForgeObject(type_index=74, variant_index=8, placement_flags=204, up=mvar.join_up(1), angle=4096)
    v.set_world_position(wall, -36.6, -132.1, 4.95)
    v.objects[0] = wall
    v.objects[2] = mvar.ForgeObject(type_index=54, variant_index=0, mp_type=15, placement_flags=12)
    v.recount_quotas()
    return v


class UpVector(unittest.TestCase):
    def test_join_is_the_reverse_of_split(self):
        for face in range(6):
            raw = mvar.join_up(face)
            self.assertEqual(mvar.split_up(raw), (face, 0.0, 0.0))
        raw = mvar.join_up(2, 208 + 104, 208 - 52)
        face, u, v = mvar.split_up(raw)
        self.assertEqual(face, 2)
        self.assertAlmostEqual(u, 0.5)
        self.assertAlmostEqual(v, -0.25)
        self.assertLess(mvar.join_up(5, 416, 416), 1 << mvar.UP_BITS)

    def test_values_off_the_grid_are_refused(self):
        for bad in ((6, 208, 208), (-1, 208, 208), (0, 417, 0), (0, 0, -1)):
            with self.assertRaises(ValueError):
                mvar.join_up(*bad)


class AddingObjects(unittest.TestCase):
    def test_new_objects_take_the_first_free_slots(self):
        v = forge_world()
        self.assertEqual(v.add_object(mvar.ForgeObject(type_index=70)), 1)
        self.assertEqual(v.add_object(mvar.ForgeObject(type_index=70)), 3)
        self.assertEqual(v.quotas[70].placed, 0)             # quotas wait for recount_quotas()
        v.recount_quotas()
        self.assertEqual((v.quotas[70].placed, v.quotas[70].maximum), (2, 2))

    def test_a_full_variant_takes_no_more(self):
        v = forge_world()
        v.objects = [mvar.ForgeObject(type_index=70) for _ in range(mvar.OBJECT_SLOTS)]
        with self.assertRaises(ValueError):
            v.add_object(mvar.ForgeObject(type_index=70))


class TurnTest(unittest.TestCase):
    def test_pieces_turns_and_tilts(self):
        v = forge_world()
        placed = turn_test.add_to(v, ORIGIN)
        self.assertEqual([p[0] for p in placed], ["A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5", "pillar", "pillar", "pillar"])
        self.assertEqual([p[1] for p in placed], [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])       # around the used slots
        by = {label: v.objects[slot] for label, slot, _, _ in placed if label != "pillar"}
        ramp = pieces.by_name()["Ramp 1x2"]
        for label in ("A1", "A2", "A3"):
            self.assertEqual((by[label].type_index, by[label].variant_index), (ramp["row"], ramp["item"]))
            self.assertIsNone(by[label].up)
        self.assertEqual([by[l].angle for l in ("A1", "A2", "A3")], [8192, 12288, 10240])   # 0, +90, +45 degrees
        self.assertEqual([mvar.split_up(by[l].up)[0] for l in ("B1", "B2", "B3", "B4", "B5")], [0, 1, 5, 2, 2])
        for label in ("B1", "B2", "B3"):
            self.assertEqual(mvar.split_up(by[label].up)[1:], (0.0, 0.0))
        lean = turn_test.TILT_STEPS / 208.0
        self.assertEqual(mvar.split_up(by["B4"].up)[1:], (lean, 0.0))
        self.assertEqual(mvar.split_up(by["B5"].up)[1:], (0.0, lean))
        self.assertEqual((by["B1"].type_index, by["B1"].variant_index), (73, 0))

    def test_positions_quotas_and_budget(self):
        v = forge_world()
        placed = turn_test.add_to(v, ORIGIN)
        for label, slot, _, want in placed:
            for got, value in zip(v.world_position(v.objects[slot]), want):
                self.assertAlmostEqual(got, value, delta=0.001, msg=label)
        a1, a2 = placed[0][3], placed[1][3]
        self.assertEqual((round(a2[0] - a1[0], 6), a2[1] - a1[1]), (-5.0, 0.0))
        self.assertTrue(all(p[3][1] > a1[1] for p in placed if p[0] == "pillar"))           # pillars on the +y side
        self.assertTrue(all(p[3][1] < a1[1] for p in placed if p[0].startswith("B")))       # antennas on the -y side
        self.assertEqual((v.quotas[75].placed, v.quotas[73].placed, v.quotas[70].placed, v.quotas[74].placed), (3, 5, 3, 1))
        self.assertEqual(v.budget_spent, 130 + 11 * turn_test.PRICE_GUESS)
        self.assertEqual(v.problems(), [])
        self.assertEqual(v.objects[0].up, mvar.join_up(1))                                  # what was there is untouched
        self.assertEqual(v.objects[2].mp_type, 15)

    def test_the_file_reads_back(self):
        v = forge_world()
        f = mvar.MvarFile(variant=v, chdr=mvar.build_chdr(v.header))
        with tempfile.TemporaryDirectory() as tmp:
            source, out = os.path.join(tmp, "yard.mvar"), os.path.join(tmp, "test.mvar")
            f.write(source)
            before = open(source, "rb").read()
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(turn_test.main(source, out, ORIGIN), 0)
                self.assertEqual(turn_test.main(source, out, ORIGIN), 1)      # it never overwrites
            with open(source, "rb") as handle:
                self.assertEqual(handle.read(), before)                       # the source is not changed
            back = mvar.MvarFile.read(out)
        self.assertEqual(back.variant.header.title, "FP Turn Test")
        self.assertEqual(len(back.variant.placed_objects()), 13)
        self.assertTrue(back.hash_is_valid())
        self.assertEqual(back.variant.problems(), [])
        self.assertIn("refusing to overwrite", buf.getvalue())
        self.assertAlmostEqual(math.degrees(mvar.decode_angle(back.variant.objects[3].angle)), 90.0, delta=0.05)

    def test_the_tilt_test_pieces(self):
        v = forge_world()
        placed = turn_test.add_to(v, ORIGIN, "tilt")
        self.assertEqual([p[0] for p in placed], ["C1", "C2", "C3", "C4", "D1", "D2", "D3", "pillar", "pillar", "pillar"])
        by = {label: v.objects[slot] for label, slot, _, _ in placed if label != "pillar"}
        self.assertEqual(mvar.split_up(by["C1"].up), (2, 1.0, 0.0))             # the face's +u edge
        self.assertEqual(mvar.split_up(by["C2"].up), (2, 0.5, 0.0))
        self.assertEqual(mvar.split_up(by["C3"].up), (0, 0.5, 0.0))
        self.assertEqual(mvar.split_up(by["C4"].up), (0, 0.0, 0.5))
        self.assertEqual([(mvar.split_up(by[l].up)[0], by[l].angle) for l in ("D1", "D2", "D3")],
                         [(0, 8192), (0, 12288), (1, 8192)])
        self.assertEqual(v.problems(), [])
        with tempfile.TemporaryDirectory() as tmp:
            source, out = os.path.join(tmp, "yard.mvar"), os.path.join(tmp, "tilt.mvar")
            mvar.MvarFile(variant=forge_world(), chdr=mvar.build_chdr(v.header)).write(source)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(turn_test.main(source, out, ORIGIN, test="tilt"), 0)
            self.assertEqual(mvar.MvarFile.read(out).variant.header.title, "FP Tilt Test")

    def test_only_todays_forge_world_palette(self):
        v = forge_world()
        v.quotas.pop()
        with self.assertRaises(ValueError):
            turn_test.add_to(v, ORIGIN)


if __name__ == "__main__":
    unittest.main()
