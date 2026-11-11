"""(custom, Nov 10) Bot Matchmaking: the native wiring of the pool (native/bots_panel.cpp, botcore.cpp, overlay.cpp) and
the brain still reading the BOTS panel's list with the new botcore.ini line. The pool's own behaviour (queue order,
the file's rules, saved settings, wrap-round, a small pool) is checked by native/pool_test.cpp
(native\\build_pool_test.bat, Visual Studio's C++ tools)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import botctl  # noqa: E402

NATIVE = ROOT / "native"


def src(name):
    return (NATIVE / name).read_text(encoding="utf-8", errors="replace")


class WiringTests(unittest.TestCase):
    def test_setting_saved_and_read(self):
        core = src("botcore.cpp")
        self.assertIn('fprintf(f, "matchmaking=%u\\n", hb_matchmaking);', core)
        self.assertIn('sscanf_s(line, "matchmaking=%u", &v) == 1) hb_matchmaking = v != 0;', core)
        self.assertIn("bot_pool_load(g_dir);", core)
        self.assertIn("bot_pool_save();", core)

    def test_rotation_after_a_match_with_bots_on_the_panel_thread(self):
        core, overlay = src("botcore.cpp"), src("overlay.cpp")
        self.assertIn("if (g_last_menu == 1 && g_brain) InterlockedExchange(&g_pool_due, 1);", core)
        self.assertIn("e.matchmaking = &hb_matchmaking;", overlay)
        self.assertIn("pool_after_match();", overlay)
        self.assertIn("bot_pool_rotate(g_roster, g_shm->difficulty)", overlay)
        # not after Firefight, in LiDAR mode or with bots off
        self.assertIn("if (!hb_matchmaking || g_ff_lobby || !g_shm || !g_shm->bots_enabled || g_shm->lidar_mode) return;",
                      overlay)

    def test_panel_names_from_the_pool_and_saves_edits(self):
        panel = src("bots_panel.cpp")
        self.assertIn("uint32_t hb_matchmaking = 1;", panel)          # on unless switched off
        self.assertIn("if (hb_matchmaking && !hb_panel_firefight && pool_take(r, i)) return;", panel)
        self.assertEqual(panel.count("bot_pool_remember(b);"), 3)      # the two difficulty rows and the play style
        self.assertIn('caption("Bot Matchmaking");', panel)
        self.assertIn("POOL_SEED_N = 60", panel)

    def test_brain_reads_the_list_with_the_new_line(self):
        with tempfile.TemporaryDirectory() as d:
            ini = Path(d) / "botcore.ini"
            ini.write_text("enabled=1\ndifficulty=2\nmatchmaking=1\nroster=1\nteams=2\n"
                           "bot=0,strong,any,xX_DeadlyAssass\nbot=1,demon,flanker,Reaper343\n", encoding="utf-8")
            bots = botctl.roster(str(ini))
            self.assertEqual([b["name"] for b in bots], ["xX_DeadlyAssass", "Reaper343"])
            self.assertEqual(bots[1]["tier"], "demon")
            self.assertEqual(botctl.setting(str(ini), "matchmaking", "0"), "1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
