"""Bot.ground_guard: a ground or hover driver's look ahead for walls (Terrain.drive_clear), on a fake straight wall, and
Terrain.drive_clear itself on Boneyard where the map data is present."""
import math
import os
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.bot import Bot  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


class Wall:
    """A wall along x = wall_x (None: open floor); drive_clear as the terrain's, flat."""

    def __init__(s, wall_x=None):
        s.wall_x, s.calls = wall_x, 0

    def drive_clear(s, p, yaw, far=6.0):
        s.calls += 1
        c = math.cos(yaw)
        if s.wall_x is None or c <= 1e-6 or p.x >= s.wall_x:
            return far
        return min(far, (s.wall_x - p.x) / c)


def scene(kind="warthog", wall_x=None, att=("path", None, 20.0, 0.0), speed=5.0, seat="driver"):
    bot = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    bot._terrain = Wall(wall_x)
    bot.seat, bot.now, bot.notes, bot.game = seat, 10.0, [], "reach"
    bot.att = list(att)
    me = PlayerState(0, 0, "bot", Vec(), vehicle=7, vel=Vec(speed, 0.0, 0.0))
    snap = Snapshot(10.0, [me], vehicles=[dict(handle=7, kind=kind, fwd=(1, 0, 0))])
    act = Action()
    act.forward, act.yaw = 1.0, 0.0
    return bot, me, snap, act


class GroundGuardTests(unittest.TestCase):
    def test_open_floor_is_left_alone(self):
        bot, me, snap, act = scene()
        bot.ground_guard(me, act, snap)
        self.assertEqual((act.forward, act.yaw, act.strafe), (1.0, 0.0, 0.0))
        self.assertEqual(bot.notes, [])

    def test_trip_steers_round_a_wall_short_of_its_next_point(self):
        bot, me, snap, act = scene(wall_x=2.5)            # next point 20 u on, the wall 2.5 u ahead
        bot.ground_guard(me, act, snap)
        self.assertGreater(abs(act.yaw), 0.3)              # turned off the wall
        self.assertIn("vehicle: wall ahead, steering round", bot.notes)
        self.assertLess(act.forward, 1.0)                  # and slowed: 2.5 u at 5 u/s is inside 0.5 s of contact

    def test_turn_is_kept_to_one_side(self):
        bot, me, snap, act = scene(wall_x=2.5)
        bot.ground_guard(me, act, snap)
        first = math.copysign(1.0, act.yaw)
        bot.now += 0.1
        act2 = Action()
        act2.forward, act2.yaw = 1.0, 0.0
        bot.ground_guard(me, act2, snap)
        self.assertEqual(math.copysign(1.0, act2.yaw), first)

    def test_wall_past_the_next_point_only_slows(self):
        # a corner: its next point 1 u on, the wall 2 u ahead past it; no turn off the trip's line
        bot, me, snap, act = scene(wall_x=2.0, att=("path", None, 1.0, 0.0))
        bot.ground_guard(me, act, snap)
        self.assertEqual(act.yaw, 0.0)
        self.assertLess(act.forward, 1.0)

    def test_throttle_eases_by_time_to_contact(self):
        far_bot, me, snap, far_act = scene(wall_x=3.4, att=("through", None, 0, 0))
        far_bot.GROUND_OFFS = ()                           # (nowhere to turn: only the throttle)
        far_bot.ground_guard(me, far_act, snap)
        near_bot, me2, snap2, near_act = scene(wall_x=1.2, att=("through", None, 0, 0))
        near_bot.GROUND_OFFS = ()
        near_bot.ground_guard(me2, near_act, snap2)
        self.assertLess(near_act.forward, far_act.forward)
        self.assertGreaterEqual(near_act.forward, Bot.GROUND_CRAWL)
        self.assertLess(far_act.forward, 1.0)

    def test_boost_is_dropped_near_a_wall(self):
        bot, me, snap, act = scene(kind="ghost", wall_x=1.5, att=("through", None, 0, 0))
        bot.GROUND_OFFS = ()
        act.fire2, act.vertical = True, 1.0                # (Bot.boost: Reach's boost goes out as vertical)
        bot.tboost_until = 99.0
        bot.ground_guard(me, act, snap)
        self.assertFalse(act.fire2)
        self.assertEqual(act.vertical, 0.0)
        self.assertEqual(bot.tboost_until, 0.0)

    def test_splatter_looks_only_as_far_as_its_man(self):
        bot, me, snap, act = scene(kind="ghost", wall_x=4.0, att=("splatter", 3, 2.0, 0.0))
        bot.ground_guard(me, act, snap)
        self.assertEqual((act.forward, act.yaw), (1.0, 0.0))

    def test_aiming_keeps_the_gun_on_and_turns_the_strafe(self):
        bot, me, snap, act = scene(kind="ghost", att=("aim", 3, 0.0, 10.0), speed=0.5)
        bot._terrain = Wall(1.0)                           # the wall on its right (yaw +pi/2 faces y; right is +x)
        act.forward, act.strafe, act.yaw = 0.0, -0.8, math.pi / 2
        bot.strafe_dir = -1
        bot.ground_guard(me, act, snap)
        self.assertEqual(act.yaw, math.pi / 2)             # never turned off its aim
        self.assertGreater(act.strafe, 0.0)                # strafing left instead
        self.assertEqual(bot.strafe_dir, 1)

    def test_aiming_drops_forward_into_a_wall(self):
        bot, me, snap, act = scene(kind="scorpion", wall_x=1.2, att=("aim", 3, 10.0, 0.0), speed=1.0)
        bot.ground_guard(me, act, snap)
        self.assertEqual(act.yaw, 0.0)
        self.assertEqual(act.forward, 0.0)

    def test_not_for_aircraft_gunners_or_reversing(self):
        for kind, seat, rev in (("banshee", "driver", 0.0), ("warthog", "gunner", 0.0), ("warthog", "driver", 99.0)):
            bot, me, snap, act = scene(kind=kind, wall_x=1.5, seat=seat)
            bot.reverse_until = rev
            bot.ground_guard(me, act, snap)
            self.assertEqual((act.forward, act.yaw), (1.0, 0.0), (kind, seat, rev))
            self.assertEqual(bot._terrain.calls, 0)

    def test_think_runs_it_for_drivers(self):
        src = (ROOT / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index("s.drive(now, dt, me, snap, act, nav)")
        self.assertIn("s.ground_guard(me, act, snap)", src[i:i + 200])


BONEYARD = ROOT / "maps" / "reach_70_boneyard"


@unittest.skipUnless((BONEYARD / "heightmap.npz").exists() and (BONEYARD / "objects.json").exists(),
                     "Boneyard map data not present")
class DriveClearTests(unittest.TestCase):
    """On the real Boneyard terrain: a Ghost's line toward the wall it hit (live 20261107-153418, bot 7 at 35.7 s) reads
    the wall about where it stopped; open field reads clear."""

    @classmethod
    def setUpClass(cls):
        from brain.maps import get_map, terrain
        cls.T = terrain(get_map("reach_70_boneyard"))

    def test_wall_ahead_of_the_crash(self):
        d = self.T.drive_clear(Vec(272.84, 111.34, -10.23), 0.67, 6.0)
        self.assertLess(d, 6.0)
        self.assertGreater(d, 4.0)                         # it stopped 5.4 u on, at (277.2, 115.0)

    def test_short_look_is_capped(self):
        self.assertLessEqual(self.T.drive_clear(Vec(272.84, 111.34, -10.23), 0.67, 2.0), 2.0)

    def test_off_the_grid_is_clear(self):
        self.assertEqual(self.T.drive_clear(Vec(1e5, 1e5, 0.0), 0.0, 3.0), 3.0)


if __name__ == "__main__":
    unittest.main()
