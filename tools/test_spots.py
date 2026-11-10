"""Edit spots (custom, Nov 8): the LiDAR view's hot spots, patrol points and team holds (tools/spots.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spots                                   # noqa: E402


class SpotsTests(unittest.TestCase):
    def test_selftest(self):
        spots.selftest()                       # owner rows, patrols, holds, refused edits, backups, a real map's files

    def test_files_follow_the_brain(self):
        if not spots.map_ok("reach_cex_headlong"):
            self.skipTest("map data not here")
        f = spots.load("reach_cex_headlong")["files"]
        self.assertEqual(f, {"hot": "maps/reach_cex_headlong/positions.json",
                             "patrol": "maps/reach_cex_headlong/infantry_patrols.json",
                             "hold": "maps/reach_cex_headlong/callouts.json",
                             "ride": "maps/reach_cex_headlong/owner_rides.json"})

    def test_refuses_other_paths_and_sites(self):
        self.assertEqual(spots.handle("GET", "/spots", "..\\brain")[0], 404)
        self.assertEqual(spots.handle("GET", "/spots", "reach_cex_headlong/../../tools")[0], 404)
        if spots.map_ok("reach_cex_headlong"):
            self.assertEqual(spots.handle("POST", "/spots", "reach_cex_headlong", b"{}", header="sim")[0], 403)


if __name__ == "__main__":
    unittest.main()
