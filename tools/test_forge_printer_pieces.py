"""Reach Forge Printer, phase 3: the Forge World pieces and their sizes.

The measuring tests use a stand-in for model2obj that writes small boxes; the last group checks
the table kept in the repository (names and sizes only) against a few things that must hold.
"""

import io
import os
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stdout
from unittest import mock

from forge_printer import pieces


def box_obj(lo, hi):
    return "".join("v %s %s %s\n" % (x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])) + "f 1 2 3\n"


FAKE = r'''import sys
model = sys.argv[2].strip("\\").split("\\")[0]
if model == "ff_rock_small":
    sys.exit(3)
shown = "ff_tower_tall" if model == "ff_tower" and WRONG else model
sizes = {"ff_plat_1x1": ((-0.51, -0.51, -0.5), (0.51, 0.51, 0.5)), "ff_plat_2x2": ((-1.00005, -1, -0.5), (1.00005, 1, 0.5))}
lo, hi = sizes.get(model, ((-1, -2, 0), (1, 2, 3)))
with open(sys.argv[3], "w") as f:
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]):
            for z in (lo[2], hi[2]):
                f.write("v %s %s %s\n" % (x, y, z))
    f.write("f 1 2 3\n")
print("objects\\levels\\forge\\%s\\%s: 1 regions, 1 meshes, 1 bones" % (shown, shown))
'''


def fake_model2obj(folder, wrong=False):
    """A stand-in for model2obj.exe; `wrong` makes it export a different model than asked for ff_tower."""
    stem = os.path.join(folder, "fake_model2obj_wrong" if wrong else "fake_model2obj")
    script = stem + ".py"
    with open(script, "w") as f:
        f.write("WRONG = %r\n" % wrong + FAKE)
    if os.name == "nt":
        bat = stem + ".bat"
        with open(bat, "w") as f:
            f.write('@"%s" "%s" %%*\n' % (sys.executable, script))
        return bat
    return script


class Catalogue(unittest.TestCase):
    def test_the_owners_97_pieces_by_category(self):
        cat = pieces.catalogue()
        noted = Counter(p["category"] for p in cat if p["name_from"] == pieces.NOTED)
        self.assertEqual(dict(noted), {"Building Blocks": 25, "Bridges and Platforms": 21, "Buildings": 11,
                                       "Decorative": 6, "Doors, Windows and Walls": 11, "Inclines": 15, "Nature": 8})
        self.assertEqual(sum(noted.values()), 97)
        self.assertEqual(len(cat), 109)

    def test_rows_and_items_as_saved_variants_use_them(self):
        # ten Forge World variants on the owner's PC use rows 70-76, and in each the highest item is one
        # less than these counts
        cat = pieces.catalogue()
        per_row = Counter(p["row"] for p in cat)
        self.assertEqual(dict(per_row), {70: 26, 71: 21, 72: 11, 73: 16, 74: 12, 75: 15, 76: 8})
        for row in per_row:
            self.assertEqual(sorted(p["item"] for p in cat if p["row"] == row), list(range(per_row[row])))
        self.assertEqual(len({p["category"] for p in cat}), 7)

    def test_names_and_models_are_each_used_once(self):
        cat = pieces.catalogue()
        self.assertEqual(len({p["name"] for p in cat}), len(cat))
        self.assertEqual(len({p["model"] for p in cat}), len(cat))
        for p in cat:
            if p["name_from"] == pieces.MODEL:
                self.assertEqual(p["name"], p["model"])

    def test_wall_coliseum_is_the_ninth_wall(self):
        # the one pairing a saved variant has confirmed: type 74, item 8
        walls = [p["name"] for p in pieces.catalogue() if p["category"] == "Doors, Windows and Walls"]
        self.assertEqual(walls.index("Wall Coliseum"), 8)


class Measuring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.mcc = os.path.join(self.tmp.name, "mcc")
        os.makedirs(os.path.join(self.mcc, "haloreach", "maps"))
        with open(os.path.join(self.mcc, *pieces.MAP), "w"):
            pass
        self.keep = os.path.join(self.tmp.name, "keep")

    def tearDown(self):
        self.tmp.cleanup()

    def measure(self, models, **kw):
        args = dict(keep=self.keep, mcc_dir=self.mcc, model2obj=fake_model2obj(self.tmp.name), models=models)
        args.update(kw)
        return pieces.measure(**args)

    def test_box_of_an_obj(self):
        path = os.path.join(self.tmp.name, "a.obj")
        with open(path, "w") as f:
            f.write(box_obj((-1, -2, 0), (1, 2, 3)))
        self.assertEqual(pieces.obj_box(path), ([-1, -2, 0], [1, 2, 3], 8))
        with open(path, "w") as f:
            f.write("f 1 2 3\n")
        with self.assertRaises(pieces.PieceError):
            pieces.obj_box(path)

    def test_measures_the_asked_pieces_in_menu_order(self):
        table = self.measure({"ff_plat_2x2", "ff_plat_1x1", "ff_tower"})
        self.assertEqual([p["model"] for p in table["pieces"]], ["ff_plat_1x1", "ff_plat_2x2", "ff_tower"])
        block = table["pieces"][0]
        self.assertEqual((block["name"], block["category"], block["name_from"]), ("Block 1x1", "Building Blocks", "noted"))
        self.assertEqual((block["min"], block["max"], block["size"]), ([-0.51, -0.51, -0.5], [0.51, 0.51, 0.5], [1.02, 1.02, 1.0]))
        self.assertEqual(table["pieces"][1]["size"], [2.0, 2.0, 1.0])              # the exporter's 0.00005 is rounded off
        self.assertEqual(table["pieces"][2]["size"], [2.0, 4.0, 3.0])
        self.assertEqual(sorted(os.listdir(self.keep)), ["ff_plat_1x1.obj", "ff_plat_2x2.obj", "ff_tower.obj"])

    def test_a_failing_export_names_the_piece(self):
        with self.assertRaisesRegex(pieces.PieceError, "model2obj failed on ff_rock_small"):
            self.measure({"ff_rock_small"})

    def test_an_export_of_the_wrong_model_is_refused(self):
        with self.assertRaisesRegex(pieces.PieceError, "ff_tower_tall.* for ff_tower"):
            self.measure({"ff_tower"}, model2obj=fake_model2obj(self.tmp.name, wrong=True))

    def test_missing_mcc_tool_or_map_is_one_clear_reason(self):
        with self.assertRaisesRegex(pieces.PieceError, "MCC was not found"):
            self.measure({"ff_tower"}, mcc_dir=os.path.join(self.tmp.name, "nowhere"))
        os.remove(os.path.join(self.mcc, *pieces.MAP))
        with self.assertRaisesRegex(pieces.PieceError, "forge_halo.map is not in this MCC"):
            self.measure({"ff_tower"})
        fake = mock.Mock(mcc=lambda: self.mcc, map_tool=lambda name: None)
        with mock.patch.dict(sys.modules, {"brain": mock.Mock(paths=fake), "brain.paths": fake}):
            with self.assertRaisesRegex(pieces.PieceError, "model2obj.exe was not found"):
                pieces.measure(keep=self.keep, mcc_dir=self.mcc)

    def test_table_survives_saving_one_piece_per_line(self):
        table = self.measure({"ff_plat_2x2", "ff_plat_1x1"})
        path = os.path.join(self.tmp.name, "table.json")
        pieces.save(table, path)
        self.assertEqual(pieces.load(path), table)
        with open(path) as f:
            self.assertEqual(sum(1 for line in f if line.startswith("  {")), 2)

    def test_a_missing_table_ends_in_one_line(self):
        buf = io.StringIO()
        with mock.patch.object(pieces, "TABLE", os.path.join(self.tmp.name, "none.json")), redirect_stdout(buf):
            code = pieces.main()
        self.assertEqual(code, 1)
        self.assertEqual(buf.getvalue().strip().count("\n"), 0)


class KeptTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = pieces.load()
        cls.named = pieces.by_name(cls.table)

    def test_it_is_the_catalogue_measured(self):
        keys = ("category", "row", "item", "name", "model", "name_from")
        self.assertEqual([{k: p[k] for k in keys} for p in self.table["pieces"]], pieces.catalogue())
        for p in self.table["pieces"]:
            for i in range(3):
                self.assertGreater(p["size"][i], 0.0, p["name"])
                self.assertAlmostEqual(p["size"][i], p["max"][i] - p["min"][i], delta=0.0015, msg=p["name"])

    def test_doors_windows_and_walls_as_the_owner_named_them_from_a_picture(self):
        got = [(p["name"], p["model"]) for p in self.table["pieces"] if p["category"] == "Doors, Windows and Walls"][:6]
        self.assertEqual(got, [("Door", "ff_door_2"), ("Door Double", "ff_wall_2x1_door"),
                               ("Window", "ff_wall_2x1_window"), ("Window Double", "ff_wall_2x2_window"),
                               ("Wall", "ff_wall_2x2"), ("Wall Double", "ff_wall_2x4")])
        # "the door is taller than the double door"; a double wall is a wall twice as wide
        self.assertGreater(self.named["Door"]["size"][2], self.named["Door Double"]["size"][2])
        self.assertAlmostEqual(self.named["Wall Double"]["size"][0], 2 * self.named["Wall"]["size"][0], delta=0.01)
        self.assertAlmostEqual(self.named["Wall Double"]["size"][2], self.named["Wall"]["size"][2], delta=0.01)

    def test_a_variants_type_and_item_find_the_piece(self):
        self.assertEqual(pieces.at(74, 8, self.table)["name"], "Wall Coliseum")     # the owner's own variant
        self.assertEqual(pieces.at(70, 0, self.table)["name"], "Block 1x1")
        self.assertEqual(pieces.at(75, 4, self.table)["name"], "Ramp 1x2")
        self.assertIsNone(pieces.at(74, 12, self.table))
        self.assertIsNone(pieces.at(54, 0, self.table))                             # a spawn point: not a building piece

    def test_info_names_the_pieces_of_a_forge_world_variant(self):
        from forge_printer import __main__ as cli
        from forge_printer import mvar
        v = mvar.MapVariant()
        v.version, v.v32_block, v.map_id = 32, 0, pieces.FORGE_WORLD_MAP_ID
        v.header = mvar.ContentHeader(map_id=v.map_id, title="Yard")
        v.bounds = (-200.0, 280.0, -360.0, 325.0, -25.0, 118.0)
        v.quotas = [mvar.Quota() for _ in range(pieces.FORGE_WORLD_QUOTA_ROWS)]
        v.objects[0] = mvar.ForgeObject(type_index=74, variant_index=8)
        v.objects[1] = mvar.ForgeObject(type_index=54, variant_index=0)
        v.recount_quotas()
        self.assertTrue(pieces.is_forge_world(v))
        f = mvar.MvarFile(variant=v, chdr=mvar.build_chdr(v.header))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "yard.mvar")
            f.write(path)
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(cli.main(["info", path, "--objects"]), 0)
        lines = buf.getvalue().splitlines()
        self.assertTrue(any(line.rstrip().endswith("Wall Coliseum") for line in lines))
        self.assertEqual(sum(1 for line in lines if "Wall Coliseum" in line), 1)
        v.quotas.pop()
        self.assertFalse(pieces.is_forge_world(v))                                  # an older palette: rows differ

    def test_pieces_known_only_by_model_are_not_offered_by_name(self):
        self.assertEqual(len(self.named), 99)
        self.assertNotIn("ff_antenna", self.named)

    def test_block_names_give_their_footprints(self):
        # "Block AxB": A and B world units on the ground, give or take the 0.02 of trim on the smallest ones
        for name, piece in self.named.items():
            if not name.startswith("Block ") or "Thin" in name:
                continue
            a, b = sorted(int(n) for n in name.split()[1].split("x"))
            got = sorted(piece["size"][:2])
            self.assertAlmostEqual(got[0], a, delta=0.04, msg=name)
            self.assertAlmostEqual(got[1], b, delta=0.04, msg=name)

    def test_block_heights_follow_their_names(self):
        for name, piece in self.named.items():
            if not name.startswith("Block ") or "Thin" in name:
                continue
            height = piece["size"][2]
            if name.endswith("Flat"):
                self.assertLessEqual(height, 0.3, name)
            elif name.endswith("Short"):
                self.assertAlmostEqual(height, 0.5, delta=0.01, msg=name)
            elif name.endswith("Tall"):
                self.assertGreaterEqual(height, 2.5, name)
            else:
                self.assertAlmostEqual(height, 1.0, delta=0.03, msg=name)

    def test_a_few_sizes_other_data_already_agrees_with(self):
        # the owner's own variant lays Coliseum walls flat as a floor, about 10 by 12 apart
        def close(name, want):
            for got, value in zip(self.named[name]["size"], want):
                if value is not None:
                    self.assertAlmostEqual(got, value, delta=0.01, msg=name)
        close("Wall Coliseum", (10.0, 0.5, 12.0))
        for name, length in (("Small", 1.0), ("Medium", 2.0), ("Long", 3.0)):
            close("Railing " + name, (None, length, None))
        for name, length in (("Small", 1.0), ("Medium", 2.0), ("Large", 3.0), ("XLarge", 5.0)):
            close("Bridge " + name, (length, 2.0, None))
        close("Ramp 1x2", (2.0, 1.0, 1.0))
        close("Ramp 1x2 Shallow", (2.0, 1.0, 0.5))


if __name__ == "__main__":
    unittest.main()
