"""(custom, Nov 24) Upstream 0.3.0's Halo: Reach third person (#53), its switches' home, the BOTS panel's Experimental tab
(#56a), and what came with them. The owner: "third person: Reach only, off by default, hand-merged at our Reach hook
spots", "controller button: no, keyboard keys are fine", "Experimental tab: take it (home for the #53/#55 switches; CE
body block left out)", "Vehicle Warfare: skip for now". Source checks: the native side has no Python to run."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"


def src(name):
    return (NATIVE / name).read_text(encoding="utf-8", errors="replace")


def body(text, head):
    """The braces' body of the function whose definition starts with `head`."""
    i = text.index(head)
    j = text.index("{", i)
    depth = 0
    for k in range(j, len(text)):
        depth += {"{": 1, "}": -1}.get(text[k], 0)
        if depth == 0:
            return text[j:k + 1]
    raise AssertionError(head)


class ExperimentalTabTests(unittest.TestCase):
    def test_tab_and_pad(self):
        panel = src("bots_panel.cpp")
        self.assertIn('if (tab("Experimental", g_tab == 3)) g_tab = 3;', panel)
        self.assertIn("g_tab = g_tab < 3 ? g_tab + 1 : 3;", panel)
        self.assertIn("else experimental_settings(e, changed, b0, inner,", panel)
        self.assertIn("if (g_goto_settings) { g_tab = 1; g_goto_settings = false; }", panel)   # (ours kept)

    def test_switches_off_by_default_and_nothing_else(self):
        panel = src("bots_panel.cpp")
        self.assertIn("static uint32_t g_exp_passenger_fp, g_exp_third_person, g_exp_tp_reticle = 1;", panel)
        save = body(panel, "static void exp_save()")
        for key in ("passenger_fp", "third_person", "tp_reticle", "shoulder", "distance", "shoulder_vk", "distance_vk"):
            self.assertIn(key + "=", save)
        page = body(panel, "static void experimental_settings(")
        for gone in ("vehicle_warfare", "unfair", "Vehicle Warfare", "Unfair", "Ragdoll", "ce_settings"):
            self.assertNotIn(gone, save + body(panel, "static void exp_load()") + page)
        self.assertIn("Halo: Reach only", page)


class ThirdPersonTests(unittest.TestCase):
    def test_built(self):
        self.assertRegex(src("build.bat"), r" reach\.cpp third_person\.cpp ")
        self.assertTrue((NATIVE / "third_person.cpp").exists())

    def test_reach_only(self):
        for name in ("h2.cpp", "h3.cpp", "odst.cpp", "h4f.cpp", "botcore.cpp"):
            self.assertNotIn("tp_view(", src(name), name)
            self.assertNotIn("tp_on()", src(name), name)

    def test_hooks_only_when_on_and_checked(self):
        reach = src("reach.cpp")
        hook = body(reach, "static void hr_tp_hook(uint8_t* mod)")
        self.assertIn("!tp_on()) return;", hook.splitlines()[1])          # nothing made while the switch is off
        # each hooked target's first bytes are compared before its hook is made
        for target, prologue in (("HR_CAM_FOLLOW_UPDATE", "HR_CAM_FOLLOW_PROLOGUE"), ("HR_CAM_SET", "HR_CAM_SET_PROLOGUE"),
                                 ("HR_CAM_FIRST_UPDATE", "HR_CAM_FIRST_PROLOGUE")):
            check = hook.index(f"memcmp(mod + {target}, {prologue}")
            make = hook.index(f"MH_CreateHook(mod + {target},")
            self.assertLess(check, make, target)
        self.assertLess(hook.index("MH_EnableHook(mod + HR_CAM_SET)"), hook.index("gr_tp_ok = true;"))
        # the functions it calls without a hook: first bytes checked too
        self.assertIn("memcmp(mod + HR_LINE, HR_LINE_HEAD", hook)
        self.assertIn("memcmp(mod + HR_UNIT_EYE, HR_UNIT_EYE_HEAD", hook)
        watch = body(reach, "void reach_watch()")
        self.assertIn("hr_tp_unhook();", watch)
        self.assertIn("hr_chk_hook(h3);", watch)                          # (ours kept)
        self.assertIn("if (g_hr) MH_RemoveHook(g_hr + HR_PLAYERS_UPDATE);", watch)
        self.assertEqual(len(re.findall(r"MH_CreateHook\(", watch)), 1)    # the players update only, as before

    def test_tick_and_film(self):
        update = body(src("reach.cpp"), "static void __fastcall h_hr_update(uint8_t* actions)")
        self.assertIn("if (!g_playback) hr_tp_apply(tls, actions); else hr_tp_film();", update)
        for ours in ("hr_wear_armory(tls, gg);", "hr_net_watch(tls, gg);", "hr_net_pump(gg);",
                     "hr_net_relay(tls, actions);"):
            self.assertIn(ours, update)

    def test_keys_no_pad(self):
        tp = src("third_person.cpp")
        self.assertIn("GetAsyncKeyState(vk)", tp)
        self.assertNotIn("XInput", tp)
        self.assertNotIn("Gamepad", tp)


if __name__ == "__main__":
    unittest.main()
