"""Halo 4, every tier: shots at riders and their vehicles go to the real point (custom, Nov 7): a rider's seated head or
chest, a vehicle killer's at the vehicle's body; from the real view on foot, a passenger's eye, a Ghost driver's camera
point. Reach is unchanged."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import vehicles                                             # noqa: E402
from brain.bot import (Belief, Bot, H4_RIDER_CHEST, H4_RIDER_HEAD, H4_VIEW_OVER_PLACE, Order,   # noqa: E402
                       h4_aim_point, h4_origin)
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to  # noqa: E402
from brain.profiles import make_profile                                # noqa: E402


def hog(kind="storm_warthog", pos=(10.0, 0.0, 0.0), yaw=0.0, handle=10, team=1):
    return dict(handle=handle, kind=kind, pos=pos, fwd=(math.cos(yaw), math.sin(yaw), 0.0), up=(0.0, 0.0, 1.0),
                occupied=True, team=team, riders=1, turrets=[], manned=[])


def rider(head=True, vehicle=10, pos=(10.0, 0.0, 0.0)):
    p = PlayerState(1, 1, "him", Vec(*pos), vel=Vec(0.0, 0.0, 0.0), vehicle=vehicle)
    p.head_pos = Vec(pos[0] + 0.06, pos[1] - 0.19, pos[2] + 0.43) if head else None   # the passenger's seat
    p.view_pos = None
    return p


class PointTests(unittest.TestCase):
    def test_rider_head_and_chest(self):
        him, snap = rider(), Snapshot(0, [], vehicles=[hog()])
        self.assertEqual(h4_aim_point(him, snap, "battle_rifle", True), him.head_pos)
        c = h4_aim_point(him, snap, "battle_rifle", False)
        self.assertAlmostEqual(c.z, him.head_pos.z - H4_RIDER_CHEST)

    def test_rider_without_a_head_read(self):
        him, snap = rider(head=False), Snapshot(0, [], vehicles=[hog()])
        self.assertAlmostEqual(h4_aim_point(him, snap, "dmr", True).z, H4_RIDER_HEAD)
        self.assertAlmostEqual(h4_aim_point(him, snap, "dmr", False).z, H4_RIDER_HEAD - H4_RIDER_CHEST)

    def test_vehicle_killers_go_at_the_body(self):
        him, snap = rider(), Snapshot(0, [], vehicles=[hog()])
        for gun in ("rockets", "spartan_laser", "sticky_detonator", "incineration_cannon", "gauss"):
            self.assertEqual(h4_aim_point(him, snap, gun, False), Vec(10.0, 0.0, 0.0), gun)

    def test_a_tank_from_behind_its_hatch(self):
        him, snap = rider(), Snapshot(0, [], vehicles=[hog("storm_scorpion")])
        me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0))       # behind it (it faces +x)
        p = h4_aim_point(him, snap, "rockets", False, me)
        self.assertAlmostEqual(p.x, 9.2)
        me.pos = Vec(20.0, 0.0, 0.0)                             # in front of it
        self.assertEqual(h4_aim_point(him, snap, "rockets", False, me), Vec(10.0, 0.0, 0.0))

    def test_on_foot(self):
        him = PlayerState(1, 1, "him", Vec(5.0, 0.0, 0.38), vehicle=-1)
        self.assertAlmostEqual(h4_aim_point(him, Snapshot(0, []), "dmr", True).z, 0.38 + H4_VIEW_OVER_PLACE)
        him.head_pos = Vec(5.0, 0.0, 0.63)
        self.assertEqual(h4_aim_point(him, Snapshot(0, []), "dmr", True), him.head_pos)

    def test_origins(self):
        me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.38))
        snap = Snapshot(0, [me], vehicles=[hog(handle=20, team=0, pos=(0.0, 0.0, 0.0))])
        self.assertAlmostEqual(h4_origin(me, snap).z, 0.38 + H4_VIEW_OVER_PLACE)
        me.view_pos = Vec(0.0, 0.0, 0.6)
        self.assertEqual(h4_origin(me, snap), me.view_pos)
        me.vehicle = 20
        o = h4_origin(me, snap, "passenger")
        self.assertAlmostEqual(o.z, 0.428)
        self.assertAlmostEqual(o.y, -0.247)
        self.assertIsNone(h4_origin(me, snap, "gunner"))
        snap.vehicles[0]["kind"] = "storm_ghost"
        self.assertAlmostEqual(h4_origin(me, snap, "driver").z, 0.003)


def bot(tier, game_map="h4_test"):
    b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": game_map}, random.Random(5))
    b.order = Order("mid", Vec(80, 0, 0))
    b.notes = []
    return b


class OnFootTests(unittest.TestCase):
    def aim_goal(self, tier, game_map):
        b = bot(tier, game_map)
        me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.38), weapon="battle_rifle", weapons=["battle_rifle"],
                         view_pos=Vec(0.0, 0.0, 0.6))
        him = rider()
        snap = Snapshot(10.0, [me, him], vehicles=[hog()])
        b.T = lambda: SimpleNamespace(los=lambda *a, **k: True, point_los=lambda *a, **k: True)
        b._terrain = b.T()
        b.per.beliefs[1] = Belief(him.pos, him.vel, 10.0, True, "eyes")
        b.per.recognized.add(1)
        b.per.last_seen[1] = b.per.clear_at[1] = 10.0
        b.engaged_since, b.strafing, b.plant, b.nade_open, b.press_fight = 9.0, False, False, False, False
        b.grenade_ready_at = 99.0
        act = Action()
        b.fight(10.0, 1 / 30, me, snap, 1, act, lambda *a, **k: None)
        return b, me, him, snap

    def test_heroic_aims_at_the_passengers_chest_from_its_view(self):
        b, me, him, snap = self.aim_goal("strong", "h4_test")
        want = angles_to(me.view_pos, h4_aim_point(him, snap, "battle_rifle", False))
        old = angles_to(me.pos + Vec(0, 0, 0.62), him.pos + Vec(0, 0, 0.35))   # the generic pair: into the body
        self.assertGreater(abs(old[1] - want[1]), 0.03)
        self.assertAlmostEqual(b.aim.goal[1], want[1], delta=0.012)    # the tier's own small error
        self.assertAlmostEqual(b.aim.goal[0], want[0], delta=0.03)

    def test_reach_keeps_its_aim(self):
        b, me, him, snap = self.aim_goal("strong", "reach_test")
        old = angles_to(me.pos + Vec(0, 0, 0.62), him.pos + Vec(0, 0, 0.35))
        self.assertAlmostEqual(b.aim.goal[1], old[1], delta=0.03)


class SeatedShooterTests(unittest.TestCase):
    def seated(self, seat, kind, tier="top", origin=None):
        # (Legendary's seat aim has no error, protected: the geometry alone is checked; every tier takes this path)
        b = bot(tier)
        b.seat, b.seat_for, b.seat_since = seat, 20, 9.0
        b.drive_to = b.order.point
        b._terrain = SimpleNamespace(vnav=lambda s, g: g, los=lambda *a, **k: True, height_over=lambda *a: 0.0,
                                     clearance=lambda *a, **k: 9.0, drive_clear=lambda *a, **k: None)
        b.T = lambda: b._terrain
        own = hog(kind, pos=(0.0, 0.0, 0.0), handle=20, team=0)
        own["riders"] = 2
        me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0), vehicle=20, weapon="battle_rifle", weapons=["battle_rifle"])
        if seat == "gunner":
            me.gunner_seat, me.turret, me.turret_origin = True, "warthog_chaingun", origin
        him = PlayerState(1, 1, "him", Vec(12.0, 3.0, 0.38), vehicle=-1)
        him.head_pos = Vec(12.0, 3.0, 0.63)
        snap = Snapshot(10.0, [me, him], vehicles=[own])
        b.per.beliefs[1] = Belief(him.pos, Vec(), 10.0, True, "eyes")
        b.per.recognized.add(1)
        b.per.last_seen[1] = b.per.clear_at[1] = 10.0
        act = Action()
        try:
            b.drive(10.0, 1 / 30, me, snap, act, lambda a, c: c)
        except Exception as e:          # (a stand-in world: the aim is what is checked)
            self.fail(f"drive failed: {e!r}")
        return b, me, him, snap

    def test_gunner_from_the_pivot_at_his_real_torso(self):
        pivot = Vec(-0.616, 0.0, 0.924)
        b, me, him, snap = self.seated("gunner", "storm_warthog", origin=pivot)
        want = angles_to(pivot, h4_aim_point(him, snap, "assault_rifle", False))
        old = angles_to(pivot, him.pos + Vec(0, 0, 0.35))        # his place's generic chest: over his shoulders
        self.assertGreater(abs(old[1] - want[1]), 0.015)
        self.assertAlmostEqual(b.aim.goal[1], want[1], delta=0.008)

    def test_passenger_from_his_eye(self):
        b, me, him, snap = self.seated("passenger", "storm_warthog")
        eye = vehicles.h4_seat_view(snap.vehicles[0], "passenger")
        want = angles_to(eye, h4_aim_point(him, snap, "battle_rifle", False))
        old = angles_to(me.pos + Vec(0, 0, 0.62), him.pos + Vec(0, 0, 0.35))
        self.assertGreater(abs(old[1] - want[1]) + abs(old[0] - want[0]), 0.015)
        self.assertAlmostEqual(b.aim.goal[1], want[1], delta=0.008)
        self.assertAlmostEqual(b.aim.goal[0], want[0], delta=0.03)


if __name__ == "__main__":
    unittest.main()
