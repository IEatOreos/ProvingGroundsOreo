"""(custom, Nov 20) Vehicle guns and men they cannot hit (Bot.gun_reach, Bot.boarded_by, GUN_DEPRESS). The owner's F9s on
Boneyard 20261120-164229: a Warthog gunner aimed straight down at the enemy who had boarded its own Warthog, and a
Scorpion driver backed away from a man walking onto it without firing and was jacked."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                                        # noqa: E402
from brain.bot import Belief, Bot, Order                               # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec              # noqa: E402
from brain.profiles import make_profile                                # noqa: E402
from test_warthog_spin import HIM, gunner, tick                        # noqa: E402


def see(b, pid, pos, t=10.0):
    b.per.beliefs[pid] = Belief(pos, Vec(), t, True, "eyes")
    b.per.recognized.add(pid)
    b.per.last_seen[pid] = b.per.clear_at[pid] = t


class GunnerReach(unittest.TestCase):
    def test_not_a_man_in_our_own_vehicle_nor_one_under_the_gun(self):
        b, me, snap = gunner()
        see(b, 1, HIM)
        self.assertTrue(b.gun_reach(me, snap.vehicles[0], 1, snap))
        under = snap.player(2)
        under.pos = Vec(-0.3, 0.45, 0.0)                   # at the wheel beside the gun: 0.66 rad under its pivot
        see(b, 2, under.pos)
        self.assertFalse(b.gun_reach(me, snap.vehicles[0], 2, snap))
        inside = snap.player(3)
        inside.pos, inside.vehicle = Vec(0.0, 0.0, 0.0), 20
        see(b, 3, inside.pos)
        self.assertFalse(b.gun_reach(me, snap.vehicles[0], 3, snap))
        self.assertEqual(b.crew_target(me, snap, snap.vehicles[0], [2, 3, 1], own=True), 1)

    def test_a_boarded_gunner_gets_out(self):
        """An enemy in our Warthog: Use held to get out, no fire, no lock on him."""
        b, me, snap = gunner()
        boarder = snap.player(3)
        boarder.pos, boarder.vehicle = Vec(0.0, 0.0, 0.0), 20
        see(b, 3, boarder.pos)
        act = tick(b, me, snap, 10.0)
        self.assertTrue(act.action)
        self.assertFalse(act.fire)
        self.assertIn("vehicle: boarded by an enemy, out to fight him", b.notes)

    def test_no_boarder_no_exit(self):
        b, me, snap = gunner()
        see(b, 1, HIM)
        act = tick(b, me, snap, 10.0)
        self.assertFalse(act.action)


def tank(tier="demon", foe_at=Vec(3.0, 0.5, 0.0), lock=False):
    b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    b.order, b.notes = Order("mid", Vec(80, 0, 0)), []
    b.seat, b.seat_for, b.seat_since = "driver", 20, 9.0
    b.drive_to = b.order.point
    b._terrain = SimpleNamespace(vnav=lambda s, g: g, los=lambda *a, **k: True, height_over=lambda *a: 0.0,
                                 clearance=lambda *a, **k: 9.0, drive_clear=lambda *a, **k: None,
                                 sees=lambda *a, **k: True)
    b.T = lambda: b._terrain
    own = dict(handle=20, kind="scorpion", pos=(0.0, 0.0, 0.0), fwd=(1.0, 0.0, 0.0), up=(0.0, 0.0, 1.0),
               occupied=True, team=0, riders=1, turrets=[], manned=[])
    me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0), vehicle=20, weapon="unknown", weapons=[])
    foe = PlayerState(1, 1, "him", foe_at, vehicle=-1, weapon="dmr", weapons=["dmr"])
    if lock:
        foe.equipment, foe.ability_on = "armor_lock", True
    snap = Snapshot(10.0, [me, foe], vehicles=[own])
    see(b, 1, foe_at)
    act = Action()
    try:
        b.drive(10.0, 1 / 30, me, snap, act, lambda a, c: c)
    except Exception as e:                                  # (a stand-in world)
        raise AssertionError(f"drive failed: {e!r}")
    return b, act


class TankBoarder(unittest.TestCase):
    def test_runs_a_close_man_down_without_a_shell(self):
        b, act = tank()
        self.assertEqual((b.att or [None])[0], "splatter")
        self.assertEqual(act.forward, 1.0)
        self.assertAlmostEqual(act.yaw, math.atan2(0.5, 3.0), places=3)
        self.assertFalse(act.fire)

    def test_easy_and_armor_lock_back_off_as_before(self):
        for kw in (dict(tier="novice"), dict(lock=True)):
            b, act = tank(**kw)
            self.assertNotEqual((b.att or [None])[0], "splatter", kw)

    def test_far_men_are_shelled_as_before(self):
        b, act = tank(foe_at=Vec(20.0, 0.0, 0.0))
        self.assertNotEqual((b.att or [None])[0], "splatter")


if __name__ == "__main__":
    unittest.main()
