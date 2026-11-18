"""(custom, Nov 18) Grenade throws solved like Halo Infinite's bots (brain/nade.py, Bot.nade_steer / nade_release /
nade_plan). The owner: Infinite's bots "throw really good grenades ... try to copy what they did but in a way that works
with our code and doesn't break it". Infinite's rule, read from its executable: a landing point short of the man (8 /
3 / 0.8), a ballistic solve from the grenade's speed and gravity, the throw within 30 degrees of the facing, the arc
walked in 0.2 s steps through the level. Our physics are learned from the bots' own throws (FlightWatch); until a game
has them, every throw is as before."""
import math
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot as botmod                                # noqa: E402
from brain import nade, profiles                               # noqa: E402
from brain.bot import Belief, Bot                              # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, dist, eye  # noqa: E402
from test_h4_pickup_board import Flat                          # noqa: E402

G, V = 6.0, 10.0          # a made-up game's grenade: gravity, speed
M = dict(speed=V, gravity=G, pitch_off=0.0, yaw_off=0.0, delay=0.1, n=5)


class Ceiling(Flat):
    """A lid HEIGHT u over the floor: a line rising above it is shut."""
    HEIGHT = 2.2

    def point_los(s, a, b, mode=None):
        return a.z < s.HEIGHT and b.z < s.HEIGHT


def land_of(origin, yaw, pitch, t):
    return nade.arc_points(origin, yaw, pitch, V, G, t)[-1]


class LandingTests(unittest.TestCase):
    def test_infinite_rule_as_decompiled(self):
        src, man = Vec(0, 0, 0), Vec(20, 0, 0.2)
        far = nade.landing_point(src, man, **{k: nade.INFINITE[k] for k in ("long_r", "short")},
                                 close_frac=nade.INFINITE["close_frac"], drop=nade.INFINITE["drop"])
        self.assertAlmostEqual(far.x, 17.0, places=4)          # 3 in front of him (past 8)
        near = nade.landing_point(src, Vec(5, 0, 0.2), long_r=8, short=3, close_frac=0.8, drop=0.2)
        self.assertAlmostEqual(near.x, 1.0, places=4)          # 80% of the way back to the thrower (within 8)
        self.assertAlmostEqual(near.z, 0.0, places=4)          # (0.2 under)

    def test_ours_short_of_him_on_our_side(self):
        src = Vec(0, 0, 0)
        far = nade.landing_point(src, Vec(0, 20, 0))
        self.assertAlmostEqual(far.y, 20 - nade.LANDING_SHORT, places=4)
        near = nade.landing_point(src, Vec(6, 0, 0))
        self.assertAlmostEqual(near.x, 6 * (1 - nade.LANDING_CLOSE_FRAC), places=4)
        self.assertGreater(dist(src, near), 4.0)                 # (never at our own feet from the fight's 4 u up)


class SolveTests(unittest.TestCase):
    def test_lands_where_asked(self):
        o = Vec(0, 0, 1.0)
        for at in (Vec(8, 0, 0), Vec(3, 9, 0), Vec(-6, -4, 2.0), Vec(12, 1, -1.5)):
            for high in (False, True):
                sol = nade.solve(o, at, V, G, high=high)
                self.assertIsNotNone(sol, (at, high))
                got = land_of(o, *sol)
                self.assertLess(dist(got, at), 0.05, (at, high, got))

    def test_high_arc_higher_and_out_of_reach_none(self):
        o, at = Vec(0, 0, 0), Vec(10, 0, 0)
        lo, hi = nade.solve(o, at, V, G), nade.solve(o, at, V, G, high=True)
        self.assertGreater(hi[1], lo[1])
        self.assertGreater(hi[2], lo[2])
        self.assertIsNone(nade.solve(o, Vec(V * V / G + 2, 0, 0), V, G))   # past the 45-degree range
        self.assertIsNone(nade.solve(o, Vec(0, 0, 5), V, G))               # straight up: no throw

    def test_arc_walk_catches_a_ceiling(self):
        o, at = Vec(0, 0, 0.62), Vec(14, 0, 0)
        ceil = Ceiling()
        lo, hi = nade.solve(o, at, V, G), nade.solve(o, at, V, G, high=True)
        self.assertTrue(nade.arc_clear(ceil.point_los, o, lo[0], lo[1], V, G, lo[2]))
        self.assertFalse(nade.arc_clear(ceil.point_los, o, hi[0], hi[1], V, G, hi[2]))
        self.assertTrue(nade.arc_clear(Flat().point_los, o, hi[0], hi[1], V, G, hi[2]))


def flight(t0, p0, v, g, n=12, dt=1 / 30):
    return [(t0 + i * dt, Vec(p0.x + v.x * i * dt, p0.y + v.y * i * dt, p0.z + v.z * i * dt - 0.5 * g * (i * dt) ** 2))
            for i in range(n)]


class LearnTests(unittest.TestCase):
    def test_fit_recovers_speed_and_gravity_past_a_bounce(self):
        pts = flight(5.0, Vec(1, 2, 3), Vec(6, 3, 4), 7.0)
        r = nade.fit(pts)
        self.assertAlmostEqual(r["gravity"], 7.0, places=2)
        self.assertAlmostEqual(r["vel"].x, 6.0, places=2)
        bounced = pts + [(pts[-1][0] + k / 30, Vec(pts[-1][1].x + 0.2 * k, pts[-1][1].y, pts[-1][1].z + 0.3 * k))
                         for k in range(1, 4)]                        # off the floor: dropped until it fits
        r2 = nade.fit(bounced)
        self.assertAlmostEqual(r2["gravity"], 7.0, places=1)

    def test_watch_learns_a_bots_throw_and_model_waits_for_three(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "grenade_flights.json")
            w = nade.FlightWatch("testgame", path)
            eye_at = Vec(0, 0, 0.62)
            bullet = (999, Vec(1.0, 0.0, 0.6))                      # already there: not the bot's
            for k in range(3):
                t = 10.0 * (k + 1)
                w.pressed(t, 3, eye_at, 0.0, 0.1, known={bullet[0]})
                track = flight(t + 0.1, Vec(0.3, 0, 0.7), Vec(9.0, 0.0, 2.0), 6.5, n=20)
                w.observe(t, [bullet])
                for tt, q in track:
                    w.observe(tt, [bullet, (500 + k, q)])
                w.observe(track[-1][0] + 1.0, [bullet])
                self.assertEqual(nade.model("testgame", path=path, flights=nade.load(path).get("testgame")) is None,
                                 k < nade.MIN_FLIGHTS - 1)
            m = nade.model("testgame", path=path, flights=nade.load(path)["testgame"])
            self.assertAlmostEqual(m["gravity"], 6.5, places=1)
            self.assertAlmostEqual(m["speed"], math.hypot(9.0, 2.0 - 6.5 * 0.0), delta=0.4)
            self.assertAlmostEqual(m["delay"], 0.1, places=2)
            self.assertAlmostEqual(m["pitch_off"], math.atan2(2.0, 9.0) - 0.1, delta=0.03)

    def test_not_a_grenade_not_kept(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.json")
            w = nade.FlightWatch("g", path)
            w.pressed(1.0, 1, Vec(0, 0, 0.6), 0.0, 0.0)
            for tt, q in flight(1.05, Vec(0.5, 0, 0.6), Vec(300, 0, 0), 0.0, n=6):   # a bullet: straight and fast
                w.observe(tt, [(7, q)])
            w.observe(3.0, [])
            self.assertEqual(nade.load(path), {})


def scene(foe_at=Vec(14, 0, 0), mate_at=None, terrain=None, yaw=0.0):
    b = Bot(0, 0, profiles.make_profile("strong", "rusher", random.Random(1)), {"name": "reach_test"}, random.Random(2))
    t = terrain or Flat()
    b.T = lambda: t
    b.notes = []
    me = PlayerState(0, 0, "bot", Vec(), weapon="dmr")
    me.yaw = yaw
    foe = PlayerState(7, 1, "foe", foe_at, weapon="dmr")
    b.per.beliefs[7] = Belief(foe.pos, Vec(), 0.0, True, "eyes")
    b.per.recognized.add(7)
    players = [me, foe]
    if mate_at is not None:
        players.append(PlayerState(2, 0, "mate", mate_at))
    snap = Snapshot(0.0, players, mode="slayer")
    return b, me, snap


def press(b, me, snap, now=1.0, yaw=None):
    act = Action()
    act.grenade = True
    act.yaw, act.pitch = (me.yaw if yaw is None else yaw), 0.0
    b.nade_steer(now, me, snap, act)
    return act


class BotThrowTests(unittest.TestCase):
    def test_as_before_until_the_physics_are_learned(self):
        b, me, snap = scene()
        with mock.patch.object(nade, "model", return_value=None):
            act = press(b, me, snap)
        self.assertTrue(act.grenade)                              # untouched: thrown along the plan's aim
        self.assertIsNone(getattr(b, "nade_job", None))

    def test_turns_onto_the_arc_then_throws_and_holds(self):
        b, me, snap = scene()
        with mock.patch.object(nade, "model", return_value=M):
            act = press(b, me, snap)
            self.assertFalse(act.grenade)                         # held back while the view comes onto the launch
            view = b.nade_job["view"]
            sol = nade.solve(eye(me), nade.landing_point(eye(me), Vec(14, 0, 0)), V, G)
            self.assertAlmostEqual(view[1], sol[1], places=3)
            act.yaw, act.pitch = view                             # (the capped view on it)
            b.nade_release(1.0, me, act)
            self.assertTrue(act.grenade)
            self.assertIn("grenade: thrown on its arc", b.notes)
            later = Action()
            later.fire = True
            b.nade_steer(1.05, me, snap, later)                   # held on the launch while it leaves the hand
            self.assertEqual((later.yaw, later.pitch), view)
            self.assertFalse(later.grenade or later.fire)
            b.nade_steer(1.0 + M["delay"] + botmod.NADE_HOLD + 0.01, me, snap, Action())
            self.assertIsNone(b.nade_job)

    def test_no_throw_off_the_view_or_shut_or_onto_a_mate(self):
        with mock.patch.object(nade, "model", return_value=M):
            b, me, snap = scene(foe_at=Vec(10, 10, 0), yaw=-0.3)  # 45 deg + 0.3 rad off: past Infinite's 30
            b.per.beliefs[7] = Belief(Vec(10, 10, 0), Vec(), 0.0, True, "eyes")
            act = press(b, me, snap, yaw=math.atan2(10, 10))
            self.assertFalse(act.grenade)
            self.assertIsNone(b.nade_job)
            class Shut(Flat):
                def point_los(s, *a, **k):
                    return False
            b, me, snap = scene(terrain=Shut())
            act = press(b, me, snap)
            self.assertFalse(act.grenade)
            self.assertIn("grenade: no open arc, not thrown", b.notes)
            b, me, snap = scene(mate_at=Vec(13, 0.5, 0))
            act = press(b, me, snap)
            self.assertFalse(act.grenade)
            self.assertLessEqual(b.grenade_ready_at, 1.0 + botmod.NADE_RETRY)   # (another try soon)

    def test_high_arc_when_the_low_one_is_shut(self):
        class Low(Flat):        # a wall a little ahead below 2.5 u: the flat throw hits it, a lob clears it
            def point_los(s, a, b, mode=None):
                return not (min(a.x, b.x) <= 4.0 <= max(a.x, b.x) and min(a.z, b.z) < 2.5)
        b, me, snap = scene(terrain=Low())
        with mock.patch.object(nade, "model", return_value=M):
            press(b, me, snap)
        job = b.nade_job
        self.assertIsNotNone(job)
        lo = nade.solve(eye(me), nade.landing_point(eye(me), Vec(14, 0, 0)), V, G)
        self.assertGreater(job["view"][1], lo[1])                 # the high arc

    def test_untouched_without_a_man_or_in_a_vehicle_or_prenade(self):
        with mock.patch.object(nade, "model", return_value=M):
            b, me, snap = scene(foe_at=Vec(40, 0, 0))             # past NADE_PICK_R
            b.per.beliefs[7] = Belief(Vec(40, 0, 0), Vec(), 0.0, True, "eyes")
            self.assertTrue(press(b, me, snap).grenade)
            b, me, snap = scene()
            me.vehicle = 9
            self.assertTrue(press(b, me, snap).grenade)
            b, me, snap = scene()
            b.prenade_st = (Vec(5, 0, 0), 9.0, "throw", 0)
            self.assertTrue(press(b, me, snap).grenade)
            b, me, snap = scene()
            with mock.patch.object(botmod, "NADE_ARC", False):
                self.assertTrue(press(b, me, snap).grenade)

    def test_wired_into_think_around_the_turn_cap(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index("    def think(s, now, dt, snap, los, nav, callouts, items=None):")
        body = src[i:src.index("    def ", i + 10)]
        self.assertLess(body.index("s.nade_steer(now, me, snap, act)"), body.index("s.turn_cap(me, act, dt)"))
        self.assertLess(body.index("s.turn_cap(me, act, dt)"), body.index("s.nade_release(now, me, act)"))
        self.assertLess(body.index("s.nade_release(now, me, act)"), body.index("s.nade_retry = dict("))


if __name__ == "__main__":
    unittest.main(verbosity=2)
