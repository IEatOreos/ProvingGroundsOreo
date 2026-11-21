"""(custom, Nov 20) Noble: the testing difficulty. The owner: "Add a new difficulty only to our in game. It's our new
testing difficulty We will call it Noble. Make its base the same as a demon bot and then we will train it." A Demon
(tier "demon", extra None: every Demon rule, its aim and hands) under its own label "noble", in the BOTS panel, botcore
and botctl; not offered on the Service Record site."""
import math
import random
import re
import sys
import types
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
from brain import noble  # noqa: E402
import tempfile  # noqa: E402

_TMP = None


def setUpModule():
    """(Nov 20) Noble's learned files in a folder of the tests' own: user/ is never read or written."""
    global _TMP
    _TMP = tempfile.TemporaryDirectory()
    noble.STORE_DIR, noble.OVERRIDE = _TMP.name, None
    noble.reload()


def tearDownModule():
    noble.OVERRIDE = None
    noble.STORE_DIR = noble.os.path.join(noble.ROOT, "user")
    noble.reload()
    _TMP.cleanup()


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
        a.step(1.0, 1 / 30, me, 1, foe, Vec(), True)
        y, p = a.goal                                                  # (where the lock settles: the swing ends there)
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
        y, p = a.goal
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
        a.step(1.0, 1 / 30, me, 1, foe, Vec(), False)
        y, p = a.goal
        self.assertLess(miss(eye(me), y, p, foe + Vec(0, 0, 0.05)), 1e-9)

    def test_caller_point_kept(self):
        # a caller's own point (a led head ray, Halo 4's real point) is aimed at as given, on foot not led again
        a, me = self.aim(), shooter()
        o, pt = Vec(0, 0, 0.6), Vec(12, 3, 0.7)
        y, p = a.step(1.0, 1 / 30, me, 1, Vec(12, 3, 0), Vec(0, 2, 0), True, origin=o, target_point=pt)
        y, p = a.goal
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

    def test_swings_smoothly_onto_a_man_behind_it(self):
        # (Nov 20, the owner's Forge World report: "flick directly at the ground ... It doesn't make their aim look
        # smooth") a man 120 degrees round: no jump onto him, every tick's turn within Demon's turn speed, the steps
        # easing off as the view gets there, then locked on him exactly
        a, me = self.aim(), shooter()
        foe = Vec(-10, 17.32, 0)
        head = foe + Vec(0, 0, aim_height(True, False))
        dt, steps, locked_at = 1 / 30, [], None
        for k in range(40):
            y, p = a.step(k * dt, dt, me, 1, foe, Vec(), True)
            steps.append(math.hypot(bot.wrap(y - me.yaw), p - me.pitch))
            me.yaw, me.pitch = y, p
            if locked_at is None and miss(eye(me), y, p, head) < 1e-9:
                locked_at = k
        self.assertEqual(profiles.NOBLE_TURN, profiles.TURN["demon"])
        self.assertTrue(all(st <= profiles.NOBLE_TURN * dt + 1e-9 for st in steps))
        self.assertLess(steps[0], math.radians(120) / 2)                # (no snap)
        self.assertIsNotNone(locked_at)
        self.assertLess(locked_at * dt, 0.45)                          # on him inside half a second
        tail = steps[3:locked_at]
        self.assertTrue(all(b <= a2 + 1e-9 for a2, b in zip(tail, tail[1:])))   # eased in, slowing to the end

    def test_locks_on_a_man_circling_it_up_close(self):
        # (Nov 21, the owner's report "Cedercare doesnt shoot while jetpacking": a man 2.5 u off crossing its view at
        # 4 u/s; the game's view read back a tick behind what was sent) the swing catches him and the lock holds:
        # the trigger is free (noble_on) inside 0.3 s and stays free. Live before: on target 30% of DMR fight ticks
        # under 3 u, Demon 100%
        for dt in (1 / 30, 0.1):
            with self.subTest(dt=dt):
                a, me = self.aim(), shooter()
                r, w = 2.5, 4.0 / 2.5
                sent, first, held = (0.0, 0.0), None, 0
                n = int(1.5 / dt)
                for k in range(n):
                    ang = math.radians(40) + w * k * dt
                    pos = Vec(r * math.cos(ang), r * math.sin(ang), 0)
                    vel = Vec(-r * w * math.sin(ang), r * w * math.cos(ang), 0)
                    me.yaw, me.pitch = sent                       # (last tick's angles, as the game reads them back)
                    sent = a.step(k * dt, dt, me, 1, pos, vel, True)
                    if a.noble_on == 1:
                        first = k if first is None else first
                        held += 1
                self.assertIsNotNone(first)
                self.assertLess(first * dt, 0.3)
                self.assertEqual(held, n - first)                 # (never lost once on)

    def test_holds_fire_until_on_him(self):
        a, me = self.aim(), shooter()
        foe = Vec(-10, 17.32, 0)
        a.step(0.0, 1 / 30, me, 1, foe, Vec(), True)
        self.assertFalse(a.on_target(me, foe))                          # (the view not there yet: no shot)

    def test_head_always_with_a_precision_gun(self):
        b = bot.Bot.__new__(bot.Bot)
        b.p, b.rng = make_profile("noble", "camper", random.Random(1)), random.Random(1)
        me, foe = shooter(weapon="battle_rifle"), shooter(Vec(10, 0, 0))
        foe.shield = 1.0
        self.assertTrue(b.aim_head(0.0, me, foe, 1))
        b.p = make_profile("demon", "camper", random.Random(1))
        b.head_key = None
        self.assertFalse(b.aim_head(0.0, me, foe, 1))                  # (Demon: the chest until his shield is down)


class NeverMissTests(unittest.TestCase):
    """(Nov 20, owner: "never miss a shot from here on out with precision weapons")"""

    def test_paced_every_range(self):
        b = bot.Bot.__new__(bot.Bot)
        b.p, b.rng = make_profile("noble", "rusher", random.Random(1)), random.Random(2)
        noble.OVERRIDE = dict(shot_learn=0)                              # (its learned pace: test_noble_learning.py)
        try:
            for w in ("dmr", "magnum", "needle_rifle", "battle_rifle", "sniper"):
                paced = bot.FIRE_GAP.get(w, 0.2)
                self.assertEqual(b.fire_gap(w, 2.0), paced, w)           # (no Short band spam: the bloom settles)
                self.assertEqual(b.fire_gap(w, 8.0), paced, w)
                self.assertAlmostEqual(b.fire_gap(w, 30.0), paced * bot.NOBLE_LONG_PACE, msg=w)
        finally:
            noble.OVERRIDE = None
        self.assertEqual(noble.DEFAULTS["long_pace"], bot.NOBLE_LONG_PACE)
        b.p = make_profile("demon", "rusher", random.Random(1))
        self.assertLess(b.fire_gap("dmr", 2.0), bot.FIRE_GAP["dmr"])    # (Demon spams up close, as before)
        self.assertEqual(b.fire_gap("assault_rifle", 2.0) <= bot.FIRE_GAP["assault_rifle"] * 1.2, True)

    def test_presses_only_when_locked(self):
        src = (ROOT / "brain" / "bot.py").read_text(encoding="utf-8")
        self.assertIn('on = on and getattr(s.aim, "noble_on", None) == tid', src)
        a = Aim(make_profile("noble", "rusher", random.Random(5)), random.Random(6))
        me = shooter()
        a.step(0.0, 1 / 30, me, 7, Vec(-10, 17.32, 0), Vec(), True)
        self.assertIsNone(a.noble_on)                                   # swinging on: no press
        me.yaw, me.pitch = a.goal
        a.step(1 / 30, 1 / 30, me, 7, Vec(-10, 17.32, 0), Vec(), True)
        self.assertEqual(a.noble_on, 7)                                 # on him: the press goes


class PushTests(unittest.TestCase):
    """(Nov 20, the owner's Forge World report: "they should be killing me quicker") Noble fights the man in view, as
    hard as its tune says (brain/noble.py: push 0 by default since the 4v4 sims and live games, Demon 4-0 and 3-0)."""

    def bot(self, tier):
        b = bot.Bot.__new__(bot.Bot)
        b.p = make_profile(tier, "camper", random.Random(1))
        return b

    def tearDown(self):
        noble.OVERRIDE = None

    def test_man_in_view_first(self):
        me, snap = shooter(), types.SimpleNamespace(mode="koth")
        me.shield = 1.0
        scores = {("fight", 4): 1.0, ("objective", Vec(1, 1, 0)): 2.6, ("retreat", Vec(3, 0, 0)): 3.0,
                  ("fight", 9): 0.5}
        plain = dict(scores)
        self.bot("noble").noble_push(me, snap, plain, {4})
        self.assertEqual(plain, scores)                                 # (its default tune: no push, Demon's choice)
        noble.OVERRIDE = dict(push=0.25)
        self.bot("noble").noble_push(me, snap, scores, {4})
        self.assertAlmostEqual(scores[("fight", 4)], 3.0 + 0.25)
        self.assertEqual(scores[("fight", 9)], 0.5)                     # (not in view)
        same = dict(scores)
        self.bot("demon").noble_push(me, snap, same, {4})
        self.assertEqual(same, scores)                                  # (Demon: its own rules)
        hurt = {("fight", 4): 1.0, ("retreat", Vec(3, 0, 0)): 3.0}
        me.shield = 0.5
        self.bot("noble").noble_push(me, snap, hurt, {4})
        self.assertEqual(hurt[("fight", 4)], 1.0)                       # (under push_shield: no push)
        me.shield, me.has_flag = 1.0, True
        carried = {("fight", 4): 1.0, ("objective", Vec(1, 1, 0)): 2.6}
        self.bot("noble").noble_push(me, snap, carried, {4})
        self.assertEqual(carried[("fight", 4)], 1.0)                    # (carrying: the flag first)

    def test_back_off_rules_by_tune(self):
        src = (ROOT / "brain" / "bot.py").read_text(encoding="utf-8")
        for fn, rule in (("demon_recharge", "recharge"), ("demon_no_new_fight", "no_new_fight"),
                         ("demon_break_second", "break_second"), ("peek_timing", "peek"),
                         ("demon_objective", "objective"), ("chase_ok", "chase"), ("demon_odds_rules", "odds")):
            body = src[src.index(f"    def {fn}("):]
            body = body[:body.index("\n    def ", 10)]
            self.assertIn(f'noble.skips(s.p, "{rule}"', body, fn)
        n, d = make_profile("noble", "camper", random.Random(1)), make_profile("demon", "camper", random.Random(1))
        for rule in noble.RULES:
            self.assertFalse(noble.skips(n, rule))                      # (by default Noble keeps every Demon rule)
            noble.OVERRIDE = {rule: 0}
            self.assertTrue(noble.skips(n, rule), rule)
            self.assertFalse(noble.skips(d, rule), rule)                # (Demon never)
        noble.OVERRIDE = dict(chase=0)
        b = self.bot("noble")
        self.assertTrue(b.chase_ok(0.0, shooter(), None, 1))


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
