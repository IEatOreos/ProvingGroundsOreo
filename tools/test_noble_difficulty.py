"""(custom, Nov 20) Noble: the testing difficulty. The owner: "Add a new difficulty only to our in game. It's our new
testing difficulty We will call it Noble. Make its base the same as a demon bot and then we will train it." A Demon
(tier "demon", extra None: every Demon rule, its aim and hands) under its own label "noble", in the BOTS panel, botcore
and botctl; not offered on the Service Record site."""
import math
import random
import re
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from brain import bot, odds, profiles  # noqa: E402
from brain.bot import Aim, aim_height, eye  # noqa: E402
from brain.core import PlayerState, Vec  # noqa: E402
from brain.profiles import PERSONALITIES, make_profile  # noqa: E402
import botctl  # noqa: E402
import service_record  # noqa: E402


class ProfileTests(unittest.TestCase):
    def test_exactly_a_demon_under_its_own_name(self):
        for style in PERSONALITIES:
            for seed in range(10):
                n = make_profile("noble", style, random.Random(seed))
                d = make_profile("demon", style, random.Random(seed))
                self.assertEqual((n.tier, n.label, n.extra), ("demon", "noble", None))
                # (Nov 20, the aimbot) its turn speed its own; every other number Demon's
                self.assertEqual(dict(asdict(n), label=None, turn=None), dict(asdict(d), label=None, turn=None),
                                 (style, seed))
                self.assertEqual(n.turn, profiles.NOBLE_TURN)
                self.assertTrue(profiles.fixed_noble(n) and profiles.fixed_demon(n) and profiles.demon_rules(n))
                self.assertTrue(profiles.demon_eyes(n) and profiles.fixed_high(n) and profiles.protected_aim(n))
                self.assertFalse(profiles.fixed_noble(d))
                self.assertNotEqual(n.personality, "wheelman")            # (a Demon is never a Wheelman)

    def test_only_noble_is_noble(self):
        for tier in ("novice", "average", "strong", "top", "demon", "blind", "tactician", "mythic"):
            self.assertFalse(profiles.fixed_noble(make_profile(tier, "camper", random.Random(1))), tier)

    def test_odds_as_demon(self):
        n = make_profile("noble", "rusher", random.Random(2))
        d = make_profile("demon", "rusher", random.Random(2))
        self.assertEqual(odds.own_acc(n), odds.own_acc(d))
        self.assertEqual(odds.REACH_ACC["noble"], odds.REACH_ACC["demon"])


def shooter(pos=None, vel=None, vehicle=-1, weapon="dmr"):
    me = PlayerState(0, 0, "bot", pos or Vec())
    me.vel, me.vehicle, me.weapon, me.yaw, me.pitch = vel or Vec(), vehicle, weapon, 0.0, 0.0
    return me


def miss(o, yaw, pitch, point):
    """How far (u) a ray from o along (yaw, pitch) passes from point."""
    d = point - o
    u = Vec(math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))
    t = d.x * u.x + d.y * u.y + d.z * u.z
    return (d - u * t).length()


class AimbotTests(unittest.TestCase):
    """(Nov 20, owner: "practically be an aimbot ... close to 100%. With all vehicles and all weapons that are precision
    based") Aim.noble_lock: Noble's view on the point every tick, led by the shot's flight."""

    def aim(self, tier="noble"):
        return Aim(make_profile(tier, "rusher", random.Random(5)), random.Random(6))

    def test_dead_on_a_still_head_at_once(self):
        a, me = self.aim(), shooter()
        foe = Vec(25, 9, 0)
        y, p = a.step(1.0, 1 / 30, me, 1, foe, Vec(), True)
        self.assertLess(miss(eye(me), y, p, foe + Vec(0, 0, aim_height(True, False))), 1e-9)
        self.assertIsNone(a.flick)

    def test_strafing_man_with_a_hitscan_rifle(self):
        # a man crossing at 3 u/s, 20 u off: the DMR (hitscan) leads by the read delay only, the head well inside 0.05 u
        a, me = self.aim(), shooter(weapon="dmr")
        foe, vel = Vec(20, 0, 0), Vec(0, 3, 0)
        y, p = a.step(1.0, 1 / 30, me, 1, foe, vel, True)
        there = foe + vel * bot.DEMON_LEAD_S + Vec(0, 0, aim_height(True, False))
        self.assertLess(miss(eye(me), y, p, there), 1e-6)

    def test_projectile_led_to_where_he_will_be(self):
        # a Banshee's bolts (shot_speed) at a man running 4 u/s across, 30 u off: the bolt and he meet
        a, me = self.aim(), shooter(vehicle=3, weapon="dmr")
        foe, vel, speed = Vec(30, 0, 0), Vec(0, 4, 0), 60.0
        o = Vec(0, 0, 1.0)
        y, p = a.step(1.0, 1 / 30, me, 1, foe, vel, False, gun="plasma_rifle", origin=o, shot_speed=speed,
                      splash_at_feet=False)
        chest = foe + Vec(0, 0, aim_height(False, False))
        t = bot.DEMON_LEAD_S
        for _ in range(20):
            t = bot.DEMON_LEAD_S + (chest + vel * t - o).length() / speed
        self.assertLess(miss(o, y, p, chest + vel * t), 0.02)
        demon = self.aim("demon")
        y2, p2 = demon.step(1.0, 1 / 30, me, 1, foe, vel, False, gun="plasma_rifle", origin=o, shot_speed=speed,
                            splash_at_feet=False)
        self.assertGreater(miss(o, y2, p2, chest + vel * t), 1.0)   # (Demon does not lead: lead 0)

    def test_explosive_at_his_feet(self):
        a, me = self.aim(), shooter(weapon="rockets")
        foe = Vec(15, 0, 0)
        y, p = a.step(1.0, 1 / 30, me, 1, foe, Vec(), False)
        self.assertLess(miss(eye(me), y, p, foe + Vec(0, 0, 0.05)), 1e-9)

    def test_caller_point_kept(self):
        # a caller's own point (a led head ray, Halo 4's real point) is aimed at as given, on foot not led again
        a, me = self.aim(), shooter()
        o, pt = Vec(0, 0, 0.6), Vec(12, 3, 0.7)
        y, p = a.step(1.0, 1 / 30, me, 1, Vec(12, 3, 0), Vec(0, 2, 0), True, origin=o, target_point=pt)
        self.assertLess(miss(o, y, p, pt), 1e-6)

    def test_looking_around_unchanged(self):
        a, b = self.aim(), self.aim("demon")
        me = shooter()
        self.assertEqual(a.step(1.0, 1 / 30, me, None, Vec(5, 5, 0), Vec(), False),
                         b.step(1.0, 1 / 30, me, None, Vec(5, 5, 0), Vec(), False))

    def test_tracks_a_juking_man_every_tick(self):
        # a man juking left and right at 3.5 u/s, 18 u off, for 3 s: the view (its turn speed, Bot.turn_cap) stays on
        # his head every tick the lock sends
        a, me = self.aim(), shooter()
        rng, pos, worst = random.Random(9), Vec(18, 0, 0), 0.0
        vel = Vec(0, 3.5, 0)
        dt = 1 / 30
        for k in range(90):
            if k % 12 == 0:
                vel = Vec(0, rng.choice((-3.5, 3.5)), 0)
            pos = pos + vel * dt
            y, p = a.step(k * dt, dt, me, 1, pos, vel, True)
            most = profiles.NOBLE_TURN * dt
            self.assertLessEqual(math.hypot(y - me.yaw, p - me.pitch), most)   # (a turn the cap lets through)
            me.yaw, me.pitch = y, p
            worst = max(worst, miss(eye(me), y, p, pos + vel * bot.DEMON_LEAD_S + Vec(0, 0, aim_height(True, False))))
        self.assertLess(worst, 1e-6)

    def test_head_always_with_a_precision_gun(self):
        b = bot.Bot.__new__(bot.Bot)
        b.p, b.rng = make_profile("noble", "camper", random.Random(1)), random.Random(1)
        me, foe = shooter(weapon="battle_rifle"), shooter(Vec(10, 0, 0))
        foe.shield = 1.0
        self.assertTrue(b.aim_head(0.0, me, foe, 1))
        b.p = make_profile("demon", "camper", random.Random(1))
        b.head_key = None
        self.assertFalse(b.aim_head(0.0, me, foe, 1))                  # (Demon: the chest until his shield is down)


class InGameOnlyTests(unittest.TestCase):
    def test_panel_and_launch(self):
        panel = (ROOT / "native" / "bots_panel.cpp").read_text(encoding="utf-8", errors="replace")
        header = (ROOT / "native" / "bots_panel.h").read_text(encoding="utf-8", errors="replace")
        self.assertIn("#define HB_TIER_NOBLE 9", header)
        self.assertIn("tier == HB_TIER_NOBLE) && style == HB_STYLE_WHEELMAN", header)
        keys = re.findall(r'"([^"]*)"', re.search(r"TIER_KEY\[HB_TIERS\]\s*=\s*\{([^}]*)\}", panel).group(1))
        self.assertEqual(keys[9], "noble")
        self.assertEqual(tuple(keys), botctl.TIER_KEYS)
        self.assertEqual(botctl.DIFFICULTY_TIERS[10], "noble")
        self.assertIn("d == 10 ? HB_TIER_NOBLE", panel)
        self.assertIn("tier == HB_TIER_NOBLE ? 10u", panel)
        shown = re.search(r"DIFF_SHOWN\[DIFF_CHOICES\]\s*=\s*\{([^}]*)\}", panel).group(1)
        self.assertEqual([int(x) for x in shown.split(",")], [0, 1, 2, 8, 3, 7, 9, 6, 10, 4, 5])
        self.assertIn("#define DIFF_CHOICES 11", panel)
        self.assertEqual(panel.count('"Noble", "Mixed", "Scaling" };'), 2)   # Quick setup and the footer
        self.assertNotIn("<= 9 ?", panel)
        self.assertIn('segmented("tier_nb"', panel)                      # the inspector's Noble row

    def test_not_on_the_site(self):
        self.assertNotIn("noble", service_record.TIER_KEYS)
        app = (ROOT / "tools" / "service_record_site" / "app.js").read_text(encoding="utf-8", errors="replace")
        names = re.search(r"const TIER_NAMES = \{([^}]*)\}", app).group(1)
        self.assertIn("mythic", names)
        self.assertNotIn("noble", names)                                 # (the site's difficulty editor)


if __name__ == "__main__":
    unittest.main(verbosity=2)
