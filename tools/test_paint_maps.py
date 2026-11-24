"""(custom, Nov 24) Upstream 0.3.0's note #57 (build 20261114-2230): Paint the nav's map list (M key), organized as the
LiDAR tools' (tools/paint.py maps_list, tools/paint_view.html): each map with its game and real name, the modded maps
after them (tools/lidar.py modded), the game logos and map pictures served from view_art only."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lidar  # noqa: E402
import paint  # noqa: E402


class PaintMapListTests(unittest.TestCase):
    def test_maps_have_their_game_and_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("h3_construct", "reach_70_boneyard"):
                os.makedirs(os.path.join(tmp, name))
                open(os.path.join(tmp, name, "heightmap.npz"), "w").close()
            open(os.path.join(tmp, "reach_70_boneyard", "paint.json"), "w").close()
            extra = [dict(name="reach_fp_guardian", title="FP_GUARDIAN", game="reach", modded=True, ready=True)]
            with mock.patch.object(paint, "MAPS", tmp), mock.patch.object(lidar, "modded", lambda known: extra):
                got = paint.maps_list()
        by = {m["name"]: m for m in got}
        self.assertEqual((by["h3_construct"]["game"], by["reach_70_boneyard"]["game"]), ("h3", "reach"))
        self.assertEqual(by["h3_construct"]["title"], lidar.map_title("h3_construct"))
        self.assertTrue(by["reach_70_boneyard"]["painted"])
        self.assertEqual(got[-1]["name"], "reach_fp_guardian")                 # (the modded ones after the game's own)

    def test_art_route_is_view_art_only(self):
        import re
        pat = r"/art/(games|maps)/([a-z0-9_]+\.(png|jpg))"
        self.assertTrue(re.fullmatch(pat, "/art/games/reach.png"))
        for bad in ("/art/games/../../x.png", "/art/maps/a/b.jpg", "/art/other/x.png", "/art/games/x.exe"):
            self.assertIsNone(re.fullmatch(pat, bad))
        self.assertIn(pat, (ROOT / "tools" / "paint.py").read_text(encoding="utf-8"))

    def test_page_has_the_list(self):
        page = (ROOT / "tools" / "paint_view.html").read_text(encoding="utf-8")
        for part in ('id="mapbtn"', 'id="maps"', 'id="maplist"', 'e.key === "m"', "the owner, Nov 6"):
            self.assertIn(part, page)


if __name__ == "__main__":
    unittest.main()
