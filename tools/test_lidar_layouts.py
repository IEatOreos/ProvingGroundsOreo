"""(custom, Nov 24) Upstream 0.3.0's notes #19 / #19b: a Layouts choice in our Simulator panel (tools/lidar_sim.py
Control "all" with layouts, tools/lidar_view.html), and his layout import (tools/h3_forge_import.py) for Halo 3, Halo 4
and H2A only: a Reach .mvar is never read or filed (the owner: it would rewrite variant.json pieces the bots' nav reads,
e.g. Renegade, and file his Forge Printer saves as layouts)."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import h3_forge_import  # noqa: E402
import lidar_sim  # noqa: E402
from brain import mvar, variants  # noqa: E402

NAMES = ["bloodgulch", "h3_construct", "h3_construct/variants/v1537b1e3", "reach_70_boneyard",
         "reach_forge_halo", "reach_forge_halo/variants/v1234abcd", "h4_ca_blood_crash",
         "h4_ca_blood_crash/variants/v1ee02df3"]


class LayoutsRunTests(unittest.TestCase):
    def test_layouts_of_one_game(self):
        c = lidar_sim.Control(NAMES)
        self.assertEqual(c.command(dict(action="all", game="h3", layouts=True)), (200, dict(ok=True, queued=1)))
        self.assertEqual(c.queue, ["h3_construct/variants/v1537b1e3"])

    def test_layouts_of_every_game(self):
        c = lidar_sim.Control(NAMES)
        self.assertEqual(c.command(dict(action="all", layouts=True))[1]["queued"], 3)
        self.assertTrue(all("/variants/" in m for m in c.queue))

    def test_maps_unchanged_and_refusals(self):
        c = lidar_sim.Control(NAMES)
        self.assertEqual(c.command(dict(action="all", game="reach")), (200, dict(ok=True, queued=2)))
        self.assertEqual(c.queue, ["reach_70_boneyard", "reach_forge_halo"])             # (our Nov 13 run, no layouts)
        code, ans = c.command(dict(action="all", game="ce", layouts=True))
        self.assertEqual((code, ans["error"]), (404, "no layouts for that game"))
        self.assertEqual(c.queue, ["reach_70_boneyard", "reach_forge_halo"])             # (a refused one changed nothing)

    def test_panel_has_the_choice(self):
        page = (ROOT / "tools" / "lidar_view.html").read_text(encoding="utf-8")
        for part in ('id="sim-all-kind"', 'value="layouts"', "body.layouts = true", 'id="sim-all-game"', 'id="sim-all"',
                     'id="sim-mappers"'):
            self.assertIn(part, page)


class NeverReachTests(unittest.TestCase):
    REACH = os.path.join("C:\\", "Users", "x", "AppData", "LocalLow", "MCC", "LocalFiles", "0009", "HaloReach", "Map",
                         "renegade.mvar")

    def test_no_reach_reader(self):
        self.assertEqual(h3_forge_import.GAMES, ("h3", "h4", "h2a"))
        self.assertNotIn("reach", h3_forge_import.READERS)
        self.assertTrue(callable(mvar.read_h4))

    def test_a_reach_file_is_skipped_unread(self):
        reads = []
        with mock.patch.dict(h3_forge_import.READERS, {g: (lambda p, g=g: reads.append(p)) for g in ("h3", "h4", "h2a")}), \
                mock.patch.object(variants, "save", side_effect=AssertionError("nothing filed")):
            self.assertIsNone(h3_forge_import.file_one(self.REACH, "reach"))
            self.assertIsNone(h3_forge_import.file_one(self.REACH, "h4"))          # (in a HaloReach folder)
            mcc = os.path.join("D:\\", "MCC", "haloreach", "map_variants", "hr_forgeWorld_asylum.mvar")
            self.assertIsNone(h3_forge_import.file_one(mcc, "h3"))
        self.assertEqual(reads, [])

    def test_a_reach_base_is_not_filed(self):
        got = dict(ok=True, map="reach_forge_halo", title="FP Guardian", objects=[])
        with mock.patch.dict(h3_forge_import.READERS, {"h4": lambda p: dict(got)}), \
                mock.patch.object(variants, "save", side_effect=AssertionError("nothing filed")):
            self.assertIsNone(h3_forge_import.file_one(os.path.join("C:\\", "x", "Halo4", "Map", "a.mvar"), "h4"))

    def test_main_never_lists_reach(self):
        asked, read = [], []

        def library(game="reach", **_):
            asked.append(game)
            return [self.REACH] if game == "reach" else []
        with mock.patch.object(mvar, "library", library), mock.patch.object(mvar, "read", side_effect=read.append), \
                mock.patch.object(h3_forge_import, "filed", lambda base: read.append(base) if base.startswith("reach_")
                                  else {}):
            h3_forge_import.main()
        self.assertEqual(sorted(asked), ["h2a", "h3", "h4"])
        self.assertEqual(read, [])


if __name__ == "__main__":
    unittest.main()
