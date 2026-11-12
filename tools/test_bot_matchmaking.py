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


class LobbyProfileTests(unittest.TestCase):
    """(Nov 11) every lobby bot can be dressed (profile_ensure) and is drawn in MCC's MY GAME SESSION list."""

    def test_pool_bot_seed_is_the_brains(self):
        # native/pool_test.cpp holds name_look_seed to these: a pool bot given a profile keeps the look it had
        sys.path.insert(0, str(ROOT))
        from brain import looks
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "bot_profiles.ini"
            prof.write_text("experience=original\neffects=none\nbot=Alpha,111,TBK\n", encoding="utf-8")
            for name, seed in (("MadPistol", 999176086), ("Sword117", 4220511441), ("xX_DeadlyAssass", 2723695146)):
                self.assertEqual(looks.seed_of(name, str(prof)), seed)
                self.assertEqual(looks.clan_of(name, str(prof)), "")      # (no clan till one is set)
            # given its profile line (as profile_ensure writes it), the same seed: the same look and emblem
            prof.write_text(prof.read_text() + "bot=MadPistol,999176086,\n", encoding="utf-8")
            self.assertEqual(looks.seed_of("MadPistol", str(prof)), 999176086)
            self.assertEqual(looks.read_profiles(str(prof))[0][-1], ("MadPistol", 999176086, ""))

    def test_emblems_for_named_bots(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import looks_export
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "bot_profiles.ini"
            prof.write_text("experience=original\n", encoding="utf-8")
            self.assertIsInstance(looks_export.export_emblems(str(prof), []), int)
        self.assertIn('looks_export.py\\" --emblems', src("bots_panel.cpp"))       # (bot_emblems_frame asks for them)

    def test_settings_page_and_session_rows(self):
        panel, overlay, layout = src("bots_panel.cpp"), src("overlay.cpp"), src("ui_layout.h")
        self.assertIn('caption("Bot profiles: in your lobby");', panel)
        self.assertIn("int k = profile_ensure(lr.bot[open_k].name);", panel)
        self.assertIn('button("Edit look and clan tag"', panel)
        self.assertIn("for (int k = PROF_INSTALL; k < g_nprof; k++)", panel)          # the re-roll keeps them
        self.assertIn("PROF_MAX = 1024", panel)
        # (Nov 11, the owner's video) drawn wherever MCC's list stands: the lobby's corner, the slide-out, a player picked
        self.assertIn("if (sess) draw_session(", overlay)
        self.assertIn("else if (sframe++ % 4 == 0) probe_session(sc);", overlay)
        self.assertIn("if (best >= 120 * s && best_end > 600 * s) found = (float)best_end + 1;", overlay)
        self.assertIn("inline ui_rect mcc_session_row(float H, float x1, int k)", layout)

    def test_bots_can_be_picked(self):
        """(Nov 11) a bot row's click opens its menu (MCC's player menu), PLAYER DETAILS its card; while either is open
        MCC gets no input and Esc closes it."""
        overlay, panel = src("overlay.cpp"), src("bots_panel.cpp")
        self.assertIn("if (g_sess_hover >= 0 && ImGui::IsMouseClicked(0)) {", overlay)
        self.assertIn('items[n] = "PLAYER DETAILS"; act[n++] = 0;', overlay)
        self.assertIn("if (bot_pool_swap(g_roster, i, g_shm->difficulty))", overlay)
        self.assertIn("if (g_bot_card) draw_card();", overlay)
        self.assertIn("if (((g_panel || bots_ui) && (mouse || keys)) ||", overlay)
        self.assertIn("bool ours = (g_show_tile && g_panel) || bot_ui();", overlay)
        self.assertIn("bool ImGui::GetFrameCount() != g_menu_frame".split(" ", 1)[1], overlay)   # (its opening click)
        self.assertIn("bool bot_card(bots_panel_env& e, const hb_bot& b) {", panel)
        self.assertIn("mv = ed_model(&e, G, sp, g_card_yaw,", panel)

    def test_mcc_nameplates(self):
        """(Nov 11) MCC's own nameplates, read from its folder: the bots' rows, card and editor, and MCC's screens (the
        player lookup's +0x18). native/pool_test.cpp checks the catalog and the PNGs against a real MCC."""
        panel, overlay, report, core, build = (src("bots_panel.cpp"), src("overlay.cpp"), src("report.cpp"),
                                               src("botcore.cpp"), src("build.bat"))
        self.assertIn('L"Data\\\\UI\\\\NamePlates\\\\Images\\\\"', panel)
        self.assertIn('L"Data\\\\UI\\\\playercustomization.xml"', panel)
        self.assertIn('int v = profile_over_get(k, "mcc.nameplate");', panel)
        self.assertIn('ed_caption("Nameplate", set);', panel)
        self.assertIn("unsigned long long npt = np > 0 ? nameplate_tex(np, make_texture) : 0;", overlay)
        self.assertIn("if (np > 0) out[6] = np;                                       // +0x18: its nameplate", report)
        self.assertIn("nameplates_load(nullptr);", core)
        self.assertIn("ole32.lib windowscodecs.lib", build)
        # the brain's looks read only "<game>." keys: the editor's "mcc.nameplate" is not a game's
        sys.path.insert(0, str(ROOT))
        from brain import looks
        with tempfile.TemporaryDirectory() as d:
            prof = Path(d) / "bot_profiles.ini"
            prof.write_text("experience=original\nbot=MadPistol,999176086,,mcc.nameplate=42;h4.primary=3\n", encoding="utf-8")
            self.assertEqual(looks.overrides_of("MadPistol", str(prof)), {"mcc.nameplate": 42, "h4.primary": 3})
            self.assertEqual(looks.seed_of("MadPistol", str(prof)), 999176086)

    def test_session_geometry_from_the_video(self):
        """ui_layout.h's numbers, as the owner's 2556x1436 recording and the probe on its frames gave them (scratchpad
        probe_sim.py): the player's box 82-126, 332 wide; rows 50 apart; the bar 346-334 left of the box's right edge."""
        layout = src("ui_layout.h")
        for line in ("inline float mcc_session_probe_y0(float H) { return 78 * (H / 1080.0f); }",
                     "inline float mcc_session_probe_y1(float H) { return 87 * (H / 1080.0f); }",
                     "float s = H / 1080.0f, y = (k ? 87 + 50 * k : 82) * s;",   # (the first bot 6 under his row)
                     "return { x1 - 332 * s, y, x1, y + 44 * s };",
                     "return x1 - 346 * (H / 1080.0f);"):
            self.assertIn(line, layout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
