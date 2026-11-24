"""(custom, Nov 23) A Forge layout's nav window cut to its play area inside its kill zones (brain/variants.py
play_limit, clip; brain/maps.py load_map, grow). The owner: "Remove the waste from renegade and see what you can do"."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import variants              # noqa: E402

NAME = "reach_forge_halo/variants/vtest"


class PlayWindow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, variants.ROOT = variants.ROOT, self.tmp.name
        d = os.path.join(self.tmp.name, NAME)
        os.makedirs(d)
        with open(os.path.join(d, "variant.json"), "w") as f:
            json.dump(dict(id="vtest", window=[-128.0, -256.0, 32.0, 32.0]), f)
        self.kz = os.path.join(d, "killzones.json")
        with open(self.kz, "w") as f:
            json.dump(dict(volumes=[1]), f)

    def tearDown(self):
        variants.ROOT = self.root
        self.tmp.cleanup()

    def test_kept_and_used_while_the_kill_zones_are_the_same(self):
        pw = variants.play_window_of([-91.7, -8.0], [-217.8, -61.8])      # (Renegade's in-bounds floor)
        self.assertEqual(pw, (-100.0, -224.0, 0.0, -52.0))
        self.assertTrue(variants.save_play_window(NAME, pw))
        self.assertEqual(variants.play_limit(NAME), pw)
        self.assertEqual(variants.clip((-128.0, -256.0, 32.0, 32.0), pw), pw)
        with open(self.kz, "w") as f:                                  # (the layout's kill zones edited in Forge)
            json.dump(dict(volumes=[1, 2]), f)
        self.assertIsNone(variants.play_limit(NAME))

    def test_no_limit_no_cut(self):
        self.assertIsNone(variants.play_limit(NAME))
        self.assertEqual(variants.clip((0.0, 0.0, 10.0, 10.0), None), (0.0, 0.0, 10.0, 10.0))
        self.assertEqual(variants.clip((0.0, 0.0, 10.0, 10.0), (20.0, 20.0, 30.0, 30.0)), (0.0, 0.0, 10.0, 10.0))

    def test_a_grown_cut_window_never_shrinks_the_kept_one(self):
        variants.save_window(NAME, (-100.0, -224.0, 16.0, -36.0))
        self.assertEqual(variants.info(NAME)["window"], [-128.0, -256.0, 32.0, 32.0])

    def test_the_background_build_cuts_as_the_match_will(self):
        """(tools/terrain_prebuild.py play_cut) a layout given a play window since its last match is built cut."""
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import terrain_prebuild
        pw = (-100.0, -224.0, 0.0, -52.0)
        variants.save_play_window(NAME, pw)
        m = dict(name=NAME, window=(-128.0, -256.0, 32.0, 32.0), variant=dict(id="vtest", window=[-128.0, -256.0, 32.0, 32.0]))
        terrain_prebuild.play_cut(m)
        self.assertEqual((m["window"], m["play_window"]), (pw, pw))
        self.assertEqual(m["variant"].get("play_window"), list(pw))
        base = dict(name="reach_forge_halo", window=None, variant=None)
        self.assertIs(terrain_prebuild.play_cut(base), base)

    def test_growth_stops_at_the_play_area(self):
        pw = (-100.0, -224.0, 0.0, -52.0)
        full = variants.clip((-1000.0, -1000.0, 1000.0, 1000.0), pw)
        self.assertIsNone(variants.grown(pw, (-3.0, -150.0), full))            # (at its edge: no growing past it)
        self.assertIsNotNone(variants.grown(pw, (-3.0, -150.0), (-1000.0, -1000.0, 1000.0, 1000.0)))


if __name__ == "__main__":
    unittest.main()
