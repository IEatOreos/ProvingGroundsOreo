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
    def test_easy_walks_on_from_an_empty_hunt_spot(self):
        for tier in ("novice", "average"):
            b, act, walked, me = self.fight(tier, goal=("hunt", Vec(1.5, 0.0, 0.0)), enemy_at=Vec(60, 60, 0))
            if tier == "novice":
                self.assertEqual(walked[-1], b.roam_point)
            else:
                self.assertEqual(walked[-1], Vec(1.5, 0.0, 0.0))              # (as before: to the spot)

    def fight(self, tier, ticks=20, goal=("fight", 1), enemy_at=Vec(10, 0, 0)):
        b = make(tier)
        b._terrain = SimpleNamespace(sees=lambda *a, **k: True, shot_los=lambda *a, **k: True,
                                     target_parts=lambda *a, **k: (True, True), point_los=lambda *a, **k: True)
        for name in ("no_wall_jump", "edge_guard", "obstacle_guard", "unstuck"):
            setattr(b, name, lambda *a, **k: None)
        b.look_point = lambda me, p, nav=None, post=None: p                   # (no map: looks where it goes)
        walked = []

        def move_to(me, p, act, nav, **kw):                                   # (no map: straight at it, full speed)
            walked.append(p)
            act.yaw, act.forward, act.strafe = math.atan2(p.y - me.pos.y, p.x - me.pos.x), 1.0, 0.0
        b.move_to = move_to
        b.goal, b.next_decide = goal, 99.0
        b.per.recognized.add(1)
        me = PlayerState(0, 0, "bot", Vec(), weapon="assault_rifle", weapons=["assault_rifle"], mag=[32], ammo=[96])
        him = PlayerState(1, 1, "enemy", enemy_at)
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


class Ground:
    """Terrain stand-in: floor everywhere, clear lines, no path field (headway falls back to the straight line)."""

    def ground_ok(self, *a, **k):
        return True

    def los(self, *a, **k):
        return True

    def _field(self, *a, **k):
        raise KeyError


class MoreMovingTests(unittest.TestCase):
    """(Nov 13, the owner's items 1-5) hunts, posts, headway and roam choice."""

    def test_easy_roams_to_a_neighbouring_zone(self):
        zones = SimpleNamespace(zones=[SimpleNamespace(center=Vec(x, 0.0, 0.0)) for x in (12.0, 25.0, 60.0, -55.0)])
        for tier, allowed in (("novice", {12.0, 25.0}), ("average", {12.0, 25.0, 60.0, -55.0})):
            seen = set()
            for seed in range(40):
                b = Bot(0, 0, make_profile(tier, "rusher", random.Random(1)), {"name": "reach_test", "zones": zones},
                        random.Random(seed))
                b.notes = []
                seen.add(b.roam(PlayerState(0, 0, "bot", Vec()), 0.0).x)
            self.assertTrue(seen <= allowed, (tier, seen))
            if tier == "average":
                self.assertTrue(seen & {60.0, -55.0}, seen)                   # (others: anywhere, as before)

    def test_easy_does_not_go_back_and_forth(self):
        zones = SimpleNamespace(zones=[SimpleNamespace(center=Vec(x, y, 0.0)) for x, y in
                                       ((0.0, 0.0), (15.0, 0.0), (15.0, 15.0), (0.0, 15.0))])
        b = Bot(0, 0, make_profile("novice", "rusher", random.Random(1)), {"name": "reach_test", "zones": zones},
                random.Random(5))
        b.notes = []
        me = PlayerState(0, 0, "bot", Vec())
        trail = [Vec()]
        for k in range(12):
            p = b.roam(me, float(k))
            me.pos = p                                                        # (there)
            trail.append(p)
        for a, c in zip(trail, trail[2:]):
            self.assertGreater((a - c).flat(), 1.0)                           # never straight back where it came from

    def test_brisk_loiter_never_stops(self):
        for brisk in (True, False):
            b = make("novice")
            b._terrain = Ground()
            me = PlayerState(0, 0, "bot", Vec())
            first = b.loiter(0.0, me, Vec(), 6.0, brisk=brisk)
            me.pos = first                                                    # at the spot it went to
            nxt = b.loiter(0.1, me, Vec(), 6.0, brisk=brisk)
            (self.assertNotEqual if brisk else self.assertEqual)(nxt, first)  # brisk: the next one at once

    def test_easy_gives_a_goal_up_sooner(self):
        for tier, ban_by in (("novice", 3.6), ("average", 6.1)):
            b = make(tier)
            b._terrain = Ground()
            me = PlayerState(0, 0, "bot", Vec())
            goal = ("item", Vec(20.0, 0.0, 0.0))
            t = 0.0
            while t < 7.0 and not getattr(b, "goal_ban", {}):
                b.headway(t, me, goal)
                t += 0.1
            self.assertAlmostEqual(t, ban_by, delta=0.25, msg=tier)


if __name__ == "__main__":
    unittest.main(verbosity=2)
