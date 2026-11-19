"""(custom, Nov 18) A Reach Warthog's chaingun stays spun up only on the man it was aimed at once he goes out of sight,
and fires only with the gun on where he went (Bot.spin_target, SPIN_*). The owner's F9 "Majorgunner in the turret
shooting the ground why" (reach_dlc_medium 20261118-220316, 615.9-616.2 s): the gun swung between three men it never saw,
whoever's radar dot was newest each tick, 12 degrees down with the trigger held."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                                        # noqa: E402
from brain.bot import Belief, Bot, Order                               # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to  # noqa: E402
from brain.profiles import make_profile                                # noqa: E402

PIVOT = Vec(-0.536, 0.0, 0.92)
HIM = Vec(12.0, 3.0, 0.38)


def gunner():
    b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    b.order, b.notes = Order("mid", Vec(80, 0, 0)), []
    b.seat, b.seat_for, b.seat_since = "gunner", 20, 9.0
    b.drive_to = b.order.point
    b._terrain = SimpleNamespace(vnav=lambda s, g: g, los=lambda *a, **k: True, height_over=lambda *a: 0.0,
                                 clearance=lambda *a, **k: 9.0, drive_clear=lambda *a, **k: None)
    b.T = lambda: b._terrain
    own = dict(handle=20, kind="warthog", pos=(0.0, 0.0, 0.0), fwd=(1.0, 0.0, 0.0), up=(0.0, 0.0, 1.0),
               occupied=True, team=0, riders=2, turrets=[], manned=[])
    me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0), vehicle=20, weapon="unknown", weapons=[])
    me.gunner_seat, me.turret, me.turret_origin = True, "warthog_chaingun", PIVOT
    players = [me, PlayerState(1, 1, "him", HIM, vehicle=-1),
               PlayerState(2, 1, "dot a", Vec(-10.0, 8.0, 0.4), vehicle=-1),
               PlayerState(3, 1, "dot b", Vec(4.0, -15.0, 0.4), vehicle=-1)]
    return b, me, Snapshot(10.0, players, vehicles=[own])


def tick(b, me, snap, now):
    snap.time = now
    act = Action()
    b.drive(now, 1 / 30, me, snap, act, lambda a, c: c)
    return act


class Spin(unittest.TestCase):
    def setUp(self):
        self.b, self.me, self.snap = gunner()
        b = self.b
        b.per.beliefs[1] = Belief(HIM, Vec(), 10.0, True, "eyes")       # on him, in sight
        b.per.recognized.add(1)
        b.per.last_seen[1] = b.per.clear_at[1] = 10.0
        tick(b, self.me, self.snap, 10.0)
        self.assertEqual(b.spin_on, (1, 10.0))
        b.per.beliefs[1] = Belief(HIM, Vec(), 10.0, False, "eyes")      # gone round a corner
        for k, q in ((2, Vec(-10.0, 8.0, 0.4)), (3, Vec(4.0, -15.0, 0.4))):  # newer radar dots
            b.per.beliefs[k] = Belief(q, Vec(), 10.8, False, "radar")

    def view_on(self, pos):
        self.me.yaw, self.me.pitch = angles_to(PIVOT, pos)

    def test_stays_on_him_not_the_newest_dot(self):
        self.view_on(HIM)
        act = tick(self.b, self.me, self.snap, 10.9)
        self.assertEqual(self.b.att[:2], ["spin", 1])
        self.assertTrue(act.fire)

    def test_no_fire_while_the_gun_swings_there(self):
        self.view_on(Vec(-10.0, 8.0, 0.4))           # pointed at a dot, far off his spot
        act = tick(self.b, self.me, self.snap, 10.9)
        self.assertEqual(self.b.att[:2], ["spin", 1])
        self.assertFalse(act.fire)

    def test_not_past_spin_keep_nor_dead(self):
        self.view_on(HIM)
        act = tick(self.b, self.me, self.snap, 10.0 + botmod.SPIN_KEEP + 0.1)
        self.assertFalse(act.fire)
        self.assertNotEqual((self.b.att or [None])[0], "spin")
        b, me, snap = self.b, self.me, self.snap
        b.spin_on = (1, 10.5)
        snap.player(1).alive = False
        self.assertIsNone(b.spin_target(10.9, me, snap))

    def test_dots_alone_spin_nothing(self):
        b, me, snap = gunner()
        b.per.beliefs[2] = Belief(Vec(-10.0, 8.0, 0.4), Vec(), 10.8, False, "radar")
        act = tick(b, me, snap, 10.9)
        self.assertFalse(act.fire)
        self.assertNotEqual((b.att or [None])[0], "spin")


if __name__ == "__main__":
    unittest.main()
