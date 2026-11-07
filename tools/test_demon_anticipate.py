"""Demon radar heading, out-of-sight prediction (brain/anticipate.py) and corner discipline (Bot.corner_plan)."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import anticipate
from brain.bot import Belief, Bot, Perception, CORNER_HOLD, CORNER_STANDOFF
from brain.core import PlayerState, Snapshot, Vec
from brain.profiles import make_profile


class OpenFloor:
    """Flat open floor: every way is the straight line; a wall along x = wall_x hides what is past it."""

    def __init__(s, wall_x=None, cover=()):
        s.wall_x = wall_x
        s.cover_spots = [list(c) for c in cover]

    def path_ahead(s, a, b, n=80, **kw):
        d = (b - a)
        steps = int(d.flat() / 0.25)
        u = d.norm()
        return [a + u * (0.25 * (i + 1)) for i in range(min(n, steps))]

    def los(s, a, b):
        if s.wall_x is None:
            return True
        return (a.x - s.wall_x) * (b.x - s.wall_x) > 0      # both on the same side of the wall

    def walkable(s, p):
        return True


def demon_bot(name="reach_test"):
    bot = Bot(0, 0, make_profile("demon", "rusher", random.Random(3)), {"name": name}, random.Random(5))
    return bot


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.me = PlayerState(0, 0, "bot", Vec())
        self.me.tracker = True

    def run_dots(self, tier, xs, crouch=False, shoot=False):
        p = Perception(make_profile(tier, "rusher", random.Random(2)), random.Random(4))
        enemy = PlayerState(1, 1, "enemy", Vec(-10, 0, 0))
        for i, x in enumerate(xs):
            enemy.pos, enemy.vel, enemy.crouching = Vec(x, 5, 0), Vec(1.5, 0, 0), crouch
            if shoot:
                enemy.weapons, enemy.weapon, enemy.mag = ["dmr"], "dmr", [10 - i]
            p.update(1.0 + i / 30, self.me, Snapshot(1.0 + i / 30, [self.me, enemy]), lambda *a: False, [])
        return p

    def test_demon_reads_dot_heading(self):
        p = self.run_dots("demon", [-10 + 0.05 * i for i in range(8)])
        b = p.beliefs[1]
        self.assertEqual(b.source, "radar")
        self.assertAlmostEqual(b.vel.x, 1.5, delta=0.05)
        self.assertAlmostEqual(b.vel.y, 0.0, delta=0.05)

    def test_other_tiers_get_no_heading(self):
        p = self.run_dots("top", [-10 + 0.05 * i for i in range(60)])
        if 1 in p.beliefs and p.beliefs[1].source == "radar":
            self.assertEqual(p.beliefs[1].vel.flat(), 0.0)

    def test_demon_sees_crouched_shooter_on_radar_but_not_silent_crouch(self):
        p = self.run_dots("demon", [-10, -10, -10], crouch=True, shoot=True)
        self.assertEqual(p.beliefs[1].source, "radar")
        p = self.run_dots("demon", [-10, -10, -10], crouch=True, shoot=False)
        self.assertNotIn(1, p.beliefs)


class PredictTests(unittest.TestCase):
    def test_fresh_trace_is_where_he_is(self):
        b = Belief(Vec(5, 0, 0), Vec(2, 0, 0), 10.0, False, "eyes")
        self.assertEqual(anticipate.predict(OpenFloor(), Vec(), b, 10.05), b.pos)

    def test_runs_on_along_heading(self):
        b = Belief(Vec(5, 0, 0), Vec(0, 2.25, 0), 10.0, False, "eyes")
        p = anticipate.predict(OpenFloor(), Vec(), b, 11.0)
        self.assertAlmostEqual(p.x, 5.0, delta=0.3)
        self.assertGreater(p.y, 1.5)

    def test_quiet_dot_inside_range_stays_put(self):
        # he dropped off the tracker 8 u away: crouched or stopped, not gone
        b = Belief(Vec(8, 0, 0), Vec(0, 1.5, 0), 10.0, False, "radar")
        p = anticipate.predict(OpenFloor(), Vec(), b, 12.0, tracker=True)
        self.assertEqual(p, b.pos)

    def test_prefers_hidden_cover_near_him(self):
        # a wall at x = 6: cover behind it is hidden from us at the origin
        T = OpenFloor(wall_x=6.0, cover=[(7.0, 1.0, 0.0, 1.0, 0.0)])
        b = Belief(Vec(5, 0, 0), Vec(), 10.0, False, "eyes")
        p = anticipate.predict(T, Vec(), b, 11.5)
        self.assertGreater(p.x, 6.0)

    def test_no_terrain_falls_back(self):
        b = Belief(Vec(5, 0, 0), Vec(0, 2, 0), 10.0, False, "eyes")
        self.assertEqual(anticipate.predict(None, Vec(), b, 12.0), b.pos)


class GuessTests(unittest.TestCase):
    def test_only_demon_guesses(self):
        b = Belief(Vec(5, 0, 0), Vec(0, 2.25, 0), 10.0, False, "eyes")
        me = PlayerState(0, 0, "bot", Vec())
        top = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
        top._terrain = OpenFloor()
        self.assertEqual(top.guess(11.0, me, 1, b), b.pos)
        demon = demon_bot()
        demon._terrain = OpenFloor()
        self.assertGreater(demon.guess(11.0, me, 1, b).y, 1.5)


class CornerTests(unittest.TestCase):
    def setup(self, shield, d=6.0, weapon="dmr"):
        bot = demon_bot()
        bot._terrain = OpenFloor()
        bot.man_appears = lambda me, p: Vec(p.x, 0.0, 0.0)   # he comes out at the corner on our side
        me = PlayerState(0, 0, "bot", Vec())
        me.weapon = weapon
        enemy = PlayerState(1, 1, "enemy", Vec(d, 0, 0))
        snap = Snapshot(20.0, [me, enemy])
        bot.per.last_seen[1] = 19.0
        bot.per.last_vitals[1] = (shield, 1.0, 19.0)
        b = Belief(Vec(d, 0, 0), Vec(), 19.0, False, "eyes")
        return bot, me, enemy, snap, b

    def test_healthy_close_break_is_held_then_swung(self):
        bot, me, enemy, snap, b = self.setup(shield=1.0)
        how, point = bot.corner_plan(20.0, me, b, enemy, 1, 6.0, 1.0, snap)
        self.assertEqual(how, "hold")
        self.assertGreaterEqual((point - Vec(6, 0, 0)).flat(), CORNER_STANDOFF[0] - 1e-6)
        how, point = bot.corner_plan(20.0 + CORNER_HOLD[1] + 0.01, me, b, enemy, 1, 6.0, 1.0, snap)
        self.assertEqual(how, "swing")
        self.assertGreater(abs(point.y), 3.0)       # wide of the corner, not along the wall

    def test_cracked_is_pushed(self):
        bot, me, enemy, snap, b = self.setup(shield=0.1)
        self.assertEqual(bot.corner_plan(20.0, me, b, enemy, 1, 6.0, 1.0, snap)[0], "push")

    def test_far_or_sword_is_pushed(self):
        bot, me, enemy, snap, b = self.setup(shield=1.0, d=15.0)
        self.assertEqual(bot.corner_plan(20.0, me, b, enemy, 1, 15.0, 1.0, snap)[0], "push")
        bot, me, enemy, snap, b = self.setup(shield=1.0, weapon="sword")
        self.assertEqual(bot.corner_plan(20.0, me, b, enemy, 1, 6.0, 1.0, snap)[0], "push")

    def test_hold_too_close_backs_off(self):
        bot, me, enemy, snap, b = self.setup(shield=1.0, d=2.0)
        how, point = bot.corner_plan(20.0, me, b, enemy, 1, 2.0, 1.0, snap)
        self.assertEqual(how, "hold")
        self.assertLess(point.x, 0.0)               # backed away from the corner at x = 2

    def test_cracked_then_recharged_becomes_a_hold(self):
        # live Forge World 480 s: seen at half shields, pushed; his shield was full again a second later
        bot, me, enemy, snap, b = self.setup(shield=0.5)
        self.assertEqual(bot.corner_plan(19.5, me, b, enemy, 1, 6.0, 0.5, snap)[0], "push")
        later = 19.0 + bot.per.regen_delay + 0.6 / bot.per.regen_rate
        self.assertEqual(bot.corner_plan(later, me, b, enemy, 1, 6.0, later - 19.0, snap)[0], "hold")

    def test_hit_restarts_his_recharge_clock(self):
        p = demon_bot().per
        e = PlayerState(1, 1, "enemy", Vec())
        e.shield, e.health = 1.0, 1.0
        p.seen_vitals(e, 10.0)
        e.shield = 0.2
        p.seen_vitals(e, 11.0)
        self.assertAlmostEqual(p.est_shield(1, 11.0 + p.regen_delay), 0.2)
        self.assertGreater(p.est_shield(1, 11.0 + p.regen_delay + 1.0), 0.6)

    def test_at_the_corner_still_holds(self):
        # no reappearance spot found (standing at the corner): hold back from where he is reckoned to be
        bot, me, enemy, snap, b = self.setup(shield=1.0, d=4.5)
        bot.man_appears = lambda me, p: None
        how, point = bot.corner_plan(20.0, me, b, enemy, 1, 4.5, 1.0, snap)
        self.assertEqual(how, "hold")
        self.assertLess(point.x, 0.0)

    def test_ledge_without_a_way_up_is_held_even_cracked(self):
        bot, me, enemy, snap, b = self.setup(shield=0.1, d=4.8)
        b.pos = enemy.pos = Vec(4.8, 0, 1.9)
        bot._terrain.path_ahead = lambda a, p, n=80, **kw: []
        self.assertEqual(bot.corner_plan(20.0, me, b, enemy, 1, 4.8, 1.0, snap)[0], "hold")
        how, _ = bot.corner_plan(20.0 + CORNER_HOLD[1] + 0.01, me, b, enemy, 1, 4.8, 1.0, snap)
        self.assertEqual(how, "push")             # no swing onto a ledge

    def test_learns_this_matchs_recharge_from_own_shield(self):
        p = demon_bot().per
        me = PlayerState(0, 0, "bot", Vec())
        me.shield, me.health = 1.0, 1.0
        p.update(0.0, me, Snapshot(0.0, [me]), lambda *a: True, [])
        me.shield = 0.0
        p.update(1.0, me, Snapshot(1.0, [me]), lambda *a: True, [])   # hit at 1.0
        t = 1.0
        for i in range(1, 40):                                         # refill from 4.0 s at 0.25 a second
            t = 4.0 + i / 30
            me.shield = min(1.0, 0.25 * (t - 4.0))
            p.update(t, me, Snapshot(t, [me]), lambda *a: True, [])
        self.assertAlmostEqual(p.regen_delay, 3.0 + 1 / 30, delta=0.05)
        self.assertAlmostEqual(p.regen_rate, 0.25, delta=0.03)

    def test_hold_lengths_vary(self):
        lengths = set()
        for seed in range(6):
            bot, me, enemy, snap, b = self.setup(shield=1.0)
            bot.rng = random.Random(seed)
            bot.corner_plan(20.0, me, b, enemy, 1, 6.0, 1.0, snap)
            lengths.add(round(bot.corner["until"] - 20.0, 3))
        self.assertGreater(len(lengths), 3)


class MendTests(unittest.TestCase):
    def setup(self, tier="demon", shield=0.3, health=1.0):
        bot = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
        bot._terrain = OpenFloor(wall_x=2.5)          # anything past x = 2.5 is hidden from the dead man at x = -8
        me = PlayerState(0, 0, "bot", Vec())
        me.shield, me.health = shield, health
        dead = PlayerState(1, 1, "enemy", Vec(-8, 0, 0))
        dead.alive = False
        snap = Snapshot(30.0, [me, dead])
        bot.goal, bot.last_shot_t = ("fight", 1), 29.6
        bot.per.hurt_at = 29.0
        return bot, me, dead, snap

    def test_won_fight_mends_in_cover_and_ends_when_full(self):
        bot, me, dead, snap = self.setup()
        spot = bot.mend_point(30.0, me, snap, [])
        self.assertIsNotNone(spot)
        self.assertGreater(spot.x, 2.5)              # out of the kill spot's line
        bot.goal = ("retreat", spot)
        me.shield = 0.8
        self.assertEqual(bot.mend_point(32.0, me, snap, []), spot)   # still not full: stays
        me.shield = 1.0
        self.assertIsNone(bot.mend_point(33.0, me, snap, []))        # full: done

    def test_body_that_stops_refilling_counts_as_full(self):
        bot, me, dead, snap = self.setup(shield=1.0, health=0.6)
        self.assertIsNotNone(bot.mend_point(30.0, me, snap, []))
        bot.goal = ("retreat", bot.mend["spot"])
        self.assertIsNone(bot.mend_point(30.0 + 1.6, me, snap, []))

    def test_full_after_the_kill_or_other_tiers_do_not_mend(self):
        bot, me, dead, snap = self.setup(shield=1.0, health=1.0)
        self.assertIsNone(bot.mend_point(30.0, me, snap, []))
        bot, me, dead, snap = self.setup(tier="top")
        self.assertIsNone(bot.mend_point(30.0, me, snap, []))

    def test_capped(self):
        bot, me, dead, snap = self.setup()
        bot.mend_point(30.0, me, snap, [])
        bot.goal = ("retreat", bot.mend["spot"])
        bot.per.hurt_at = 30.0 + 14.0                  # kept getting chipped: the shield never read full
        self.assertIsNone(bot.mend_point(30.0 + 15.1, me, snap, []))


if __name__ == "__main__":
    unittest.main()
