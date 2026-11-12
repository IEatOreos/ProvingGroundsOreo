"""(custom, Nov 11) tools/mcc_ranks.py: MCC's account ranks read from its own pak (the tour shields, the level insignia,
DA_AccountProgression's order), for the bots' rank badges (native/bots_panel.cpp bot_rank, rank_badge). The pak checks run
against this machine's MCC (MCC_ROOT, else the Steam copy) and are skipped without one."""
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mcc_ranks  # noqa: E402

MCC = os.environ.get("MCC_ROOT", r"F:\SteamLibrary\steamapps\common\Halo The Master Chief Collection")
HAVE = os.path.exists(os.path.join(MCC, mcc_ranks.PAK))


class Names(unittest.TestCase):
    def test_pretty(self):
        self.assertEqual(mcc_ranks.pretty("T_Im_GunerySergent"), "Gunnery Sergeant")
        self.assertEqual(mcc_ranks.pretty("T_Im_Private2ndClass"), "Private 2nd Class")
        self.assertEqual(mcc_ranks.pretty("T_Im_Lieutenant-Colonel"), "Lieutenant Colonel")
        self.assertEqual(mcc_ranks.pretty("T_Im_Warrantofficer"), "Warrant Officer")
        self.assertEqual(mcc_ranks.pretty("T_Im_2ndLieutenant"), "2nd Lieutenant")
        self.assertEqual(mcc_ranks.pretty("T_Im_CommandSergentMajor"), "Command Sergeant Major")
        self.assertEqual(len(mcc_ranks.LEVELS), 30)
        self.assertEqual(mcc_ranks.LEVELS[25], "Colonel")                 # (the owner's: Tour 6, Level 26 Colonel)

    def test_native_ranges(self):
        src = (ROOT / "native" / "bots_panel.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn("RANK_TOURS[HB_TIERS][2] = { {1, 2}, {2, 4}, {4, 6}, {6, 9}, {5, 8}, {10, 11}, {6, 9}, {5, 7} };", src)
        self.assertIn('\\\\tools\\\\mcc_ranks.py\\" extract', src)
        overlay = (ROOT / "native" / "overlay.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn("rank_badge(dl, ImVec2(r.x - 38 * u, (r.y + r.w) * 0.5f), 46 * u, rtour, rlevel, a);", overlay)


@unittest.skipUnless(HAVE, "no MCC here")
class FromMcc(unittest.TestCase):
    def test_progression_read(self):
        pak = mcc_ranks.Pak(os.path.join(MCC, mcc_ranks.PAK))
        self.assertEqual(pak.version, 7)
        levels, tours = mcc_ranks.progression(pak)
        self.assertEqual(levels, mcc_ranks.LEVELS)
        self.assertEqual(tours, mcc_ranks.TOURS)
        self.assertEqual(tours[5], ("Tier06", True))                         # (his Tour 6: the gold shield, spears)
        self.assertEqual(tours[10], ("Tier01", False))                       # (the eagle: no levels)

    def test_extract(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(mcc_ranks.extract(MCC, d), 41)
            for name in ("tour_01", "tour_11", "level_01", "level_26", "level_30"):
                b = (Path(d) / (name + ".rgba")).read_bytes()
                self.assertEqual(struct.unpack_from("<II", b), (128, 128))
                self.assertEqual(len(b), 8 + 128 * 128 * 4)
            index = (Path(d) / "index.txt").read_text(encoding="utf-8").splitlines()
            self.assertIn("level=26|Colonel", index)
            self.assertIn("tour=11|max", index)
            self.assertIn("tour=6|levels", index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
