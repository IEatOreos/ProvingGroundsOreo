"""(custom, Nov 13) Easy keeps moving. The owner: "make easy actually move a lot and not stall so much. They don't have to
be able to shoot or retrieve obj, or drive. Just to where they roam a lot more actively without stopping". Seven live
matches (Nov 12): Easy stood 18-60% of its time on foot, 37-65% of its fight time, and an Easy Camper 203 s on Spire
with a roam point it made no headway to. Bot.roam gives one up; Easy fights walking on to where it roams."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                                 # noqa: E402
from brain.bot import ROAM_MIN_D, ROAM_STALL_S, Bot             # noqa: E402
from brain.core import PlayerState, Snapshot, Vec               # noqa: E402
from brain.profiles import make_profile                         # noqa: E402

ZONES = SimpleNamespace(zones=[SimpleNamespace(center=Vec(x, y, 0.0))
                               for x, y in ((0.0, 40.0), (40.0, 40.0), (-40.0, 0.0), (2.0, 1.0), (0.0, -40.0))])


def make(tier, style="rusher"):
    rng = random.Random(3)
    b = Bot(0, 0, make_profile(tier, style, rng), {"name": "reach_test", "zones": ZONES}, rng)
    b.notes = []                                                              # (think starts each tick's)
    return b


class RoamStallTests(unittest.TestCase):
    def test_no_headway_gives_the_point_up(self):
        b = make("novice", "camper")
        me = PlayerState(0, 0, "bot", Vec(0, 0, 0))
        first = b.roam(me, 0.0)
        self.assertGreaterEqual((me.pos - first).flat(), ROAM_MIN_D)          # (not the zone 2 u off)
        t = 0.0
        while t <= ROAM_STALL_S + 0.2 and b.roam(me, t) == first:
            t += 0.1
        self.assertGreater(t, ROAM_STALL_S - 0.2)                             # kept it while it could still go
        second = b.roam(me, t)
        self.assertNotEqual(second, first)
        self.assertIn("roam: no headway, somewhere else", b.notes)
        self.assertIn((round(first.x), round(first.y)), b.roam_bad)

    def test_headway_keeps_it(self):
        b = make("novice")
        me = PlayerState(0, 0, "bot", Vec(0, 0, 0))
        first = b.roam(me, 0.0)
        for k in range(1, 80):                                                # walking 1 u/s toward it, 8 s
            t = k / 10
            d = (first - Vec(0, 0, 0)).flat()
            me.pos = Vec(first.x * t / d, first.y * t / d, 0.0)
            self.assertEqual(b.roam(me, t), first, t)

    def test_without_now_as_before(self):
        b = make("novice")
        me = PlayerState(0, 0, "bot", Vec(0, 0, 0))
        p = b.roam(me)
        for _ in range(50):
            self.assertEqual(b.roam(me), p)


class FightMovingTests(unittest.TestCase):
    def fight(self, tier, ticks=20):
        b = make(tier)
        b._terrain = SimpleNamespace(sees=lambda *a, **k: True, shot_los=lambda *a, **k: True,
                                     target_parts=lambda *a, **k: (True, True), point_los=lambda *a, **k: True)
        for name in ("no_wall_jump", "edge_guard", "obstacle_guard", "unstuck"):
            setattr(b, name, lambda *a, **k: None)
        walked = []

        def move_to(me, p, act, nav, **kw):                                   # (no map: straight at it, full speed)
            walked.append(p)
            act.yaw, act.forward, act.strafe = math.atan2(p.y - me.pos.y, p.x - me.pos.x), 1.0, 0.0
        b.move_to = move_to
        b.goal, b.next_decide = ("fight", 1), 99.0
        b.per.recognized.add(1)
        me = PlayerState(0, 0, "bot", Vec(), weapon="assault_rifle", weapons=["assault_rifle"], mag=[32], ammo=[96])
        him = PlayerState(1, 1, "enemy", Vec(10, 0, 0))
        act = None
        for k in range(ticks):
            act = b.think(1.0 + k / 30, 1 / 30, Snapshot(1.0 + k / 30, [me, him]), lambda a, c, **kw: True,
                          lambda a, c, **kw: c, [])
        return b, act, walked, me

    def test_easy_walks_on_to_its_roam_point_while_it_fights(self):
        b, act, walked, me = self.fight("novice")
        self.assertIsNotNone(b.engaged_since)                                 # (its fight ran: the aim, the trigger)
        self.assertTrue(walked and walked[-1] == b.roam_point)
        speed = math.hypot(act.forward, act.strafe)
        self.assertGreater(speed, 0.9)
        way = act.yaw + math.atan2(act.strafe, act.forward)                   # the walk in the world's frame
        want = math.atan2(b.roam_point.y - me.pos.y, b.roam_point.x - me.pos.x)
        self.assertLess(abs(math.atan2(math.sin(way - want), math.cos(way - want))), 0.05)
        self.assertFalse(act.sprint)

    def test_normal_fights_as_before(self):
        b, act, walked, me = self.fight("average")
        self.assertFalse(any(p == b.roam_point for p in walked if b.roam_point is not None))

    def test_switch_off(self):
        botmod.EASY_FIGHT_MOVING = False
        try:
            b, act, walked, me = self.fight("novice")
            self.assertFalse(any(p == b.roam_point for p in walked if b.roam_point is not None))
        finally:
            botmod.EASY_FIGHT_MOVING = True


if __name__ == "__main__":
    unittest.main(verbosity=2)
