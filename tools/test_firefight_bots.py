"""(Nov 24) Reach Classic Firefight takes up to 7 bot teammates (upstream 0.3.0's note #13, GitHub #28, build
20261114-0323), ODST kept at 4 players: botctl.player_cap, Firefight's own lists in botcore.ini (Reach's ffbot=, ODST's
odbot=, an old list read for ODST), the native caps agreeing with botctl, and the Service Record reading odbot= tiers.
Only made-up copies of the files are touched.

usage: python -I tools/test_firefight_bots.py
"""
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import botctl  # noqa: E402
import service_record as sr  # noqa: E402

INI = ("roster=1\nteams=2\nbot=0,top,any,Red One\nbot=1,novice,any,Blue One\n"
       "ffroster=1\n" + "".join(f"ffbot=0,strong,any,Reach {k}\n" for k in range(7)) +
       "odroster=1\nodbot=0,demon,any,Dare\nodbot=0,top,any,Buck\n")


def write(tmp, text):
    p = os.path.join(tmp, "botcore.ini")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


class FirefightBots(unittest.TestCase):
    def test_player_caps(self):
        self.assertEqual(botctl.player_cap("reach", firefight=True), 8)    # you and 7 bots
        self.assertEqual(botctl.player_cap("odst"), 4)                      # ODST kept: more crashed it
        self.assertEqual(botctl.player_cap("odst", firefight=True), 4)
        self.assertEqual(botctl.player_cap("reach"), botctl.MAX_PLAYERS)    # other modes untouched
        self.assertEqual(botctl.player_cap("h3"), botctl.MAX_PLAYERS)

    def test_lists_by_game(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, INI)
            reach = botctl.roster(p, firefight=True, game="reach")
            self.assertEqual([b["name"] for b in reach], [f"Reach {k}" for k in range(7)])
            self.assertTrue(all(b["team"] == 0 for b in reach))
            odst = botctl.roster(p, firefight=True, game="odst")
            self.assertEqual([(b["name"], b["tier"]) for b in odst], [("Dare", "demon"), ("Buck", "top")])
            self.assertEqual(botctl.roster(p, firefight=True), reach)          # (the default: Reach's)
            self.assertEqual([b["name"] for b in botctl.roster(p)], ["Red One", "Blue One"])

    def test_old_list_read_for_odst(self):
        with tempfile.TemporaryDirectory() as tmp:     # (a list saved before ODST had its own: the one Firefight list)
            p = write(tmp, "roster=1\nbot=0,top,any,A\nffroster=1\nffbot=0,strong,any,Old\n")
            self.assertEqual([b["name"] for b in botctl.roster(p, firefight=True, game="odst")], ["Old"])
            p = write(tmp, "roster=1\nbot=0,top,any,A\n")
            self.assertIsNone(botctl.roster(p, firefight=True, game="odst"))

    def test_native_caps_agree(self):
        panel = open(os.path.join(ROOT, "native", "bots_panel.cpp"), encoding="utf-8").read()
        core = open(os.path.join(ROOT, "native", "botcore.cpp"), encoding="utf-8").read()
        for src in (panel, core):
            m = re.search(r"FF_REACH_BOTS = (\d+), FF_ODST_BOTS = (\d+)", src)
            self.assertIsNotNone(m)
            self.assertEqual(int(m.group(1)) + 1, botctl.player_cap("reach", firefight=True))
            self.assertEqual(int(m.group(2)) + 1, botctl.player_cap("odst"))
        self.assertIn('roster_write(f, g_od_roster, "od")', core)

    def test_service_record_reads_odst_tiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, tiers = sr.read_lobby(write(tmp, INI))
            self.assertEqual(tiers.get("dare"), "demon")
            self.assertEqual(tiers.get("reach 6"), "strong")
            self.assertEqual(tiers.get("red one"), "top")


if __name__ == "__main__":
    unittest.main()
