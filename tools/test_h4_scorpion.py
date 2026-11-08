"""The Scorpion tank fix in Halo 4 (custom, Nov 8): every fixed tier's driver turns at most vehicles.SCORPION_TURN,
holds the cannon until its aim has settled, and shoots a man on foot in his real chest; Easy keeps its shots on the
move. Reach keeps the fix for fixed Legendary and Demon only, and Scaling keeps its own aim in both."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import scaling, vehicles                                   # noqa: E402
from brain.bot import Belief, Bot, Order, h4_chest                    # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to  # noqa: E402
from brain.profiles import make_profile                                # noqa: E402

DT = 1 / 30


def tank(kind="storm_scorpion", handle=20):
    return dict(handle=handle, kind=kind, pos=(0.0, 0.0, 0.0), fwd=(1.0, 0.0, 0.0), up=(0.0, 0.0, 1.0),
                occupied=True, team=0, riders=1, turrets=[], manned=[])


def bot(tier, game_map):
    prof = scaling.profile(1, "rusher", random.Random(3)) if tier == "scaling" else \
        make_profile(tier, "rusher", random.Random(3))
    b = Bot(0, 0, prof, {"name": game_map}, random.Random(5))
    b.order = Order("mid", Vec(80, 0, 0))
    b.notes = []
    b.seat, b.seat_for, b.seat_since = "driver", 20, 0.0
    b.drive_to = b.order.point
    b._terrain = SimpleNamespace(vnav=lambda s, g: g, los=lambda *a, **k: True, height_over=lambda *a: 0.0,
                                 clearance=lambda *a, **k: 9.0, drive_clear=lambda *a, **k: None)
    b.T = lambda: b._terrain
    return b


def world(kind="storm_scorpion", him_at=(15.0, 0.0, 0.38), riding=False):
    me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0), vehicle=20, weapon="battle_rifle", weapons=["battle_rifle"])
    vs = [tank(kind)]
    him = PlayerState(1, 1, "him", Vec(*him_at), vehicle=30 if riding else -1)
    if riding:
        vs.append(dict(handle=30, kind="storm_warthog", pos=him_at, fwd=(0.0, 1.0, 0.0), up=(0.0, 0.0, 1.0),
                       occupied=True, team=1, riders=1, turrets=[], manned=[]))
        him.head_pos = None
    else:
        him.head_pos = Vec(him_at[0], him_at[1], him_at[2] + 0.25)
    him.view_pos = None
    return me, him, vs


def tick(b, now, me, him, vs):
    snap = Snapshot(now, [me, him], vehicles=vs)
    b.per.beliefs[1] = Belief(him.pos, Vec(), now, True, "eyes")
    b.per.recognized.add(1)
    b.per.last_seen[1] = b.per.clear_at[1] = now
    b.scorpion_turn = False                  # (Bot.plan clears it each tick)
    act = Action(yaw=me.yaw, pitch=me.pitch)
    b.drive(now, DT, me, snap, act, lambda a, c: c)
    return act


class GateTests(unittest.TestCase):
    def capped(self, tier, game_map, kind="storm_scorpion"):
        b = bot(tier, game_map)
        me, him, vs = world(kind)
        tick(b, 10.0, me, him, vs)
        return b.scorpion_turn

    def test_every_fixed_halo4_tier_is_capped(self):
        for tier in ("novice", "average", "strong", "top", "demon"):
            self.assertTrue(self.capped(tier, "h4_ca_blood_crash"), tier)

    def test_halo4_scaling_and_other_vehicles_are_not(self):
        self.assertFalse(self.capped("scaling", "h4_ca_blood_crash"))
        self.assertFalse(self.capped("strong", "h4_ca_blood_crash", "storm_ghost"))

    def test_reach_unchanged(self):
        self.assertFalse(self.capped("strong", "reach_test"))
        self.assertTrue(self.capped("top", "reach_test"))
        self.assertTrue(self.capped("demon", "reach_test"))
        self.assertFalse(self.capped("scaling", "reach_test"))

    def test_the_turn_is_capped(self):
        for tier in ("strong", "demon"):
            b = bot(tier, "h4_ca_blood_crash")
            b.scorpion_turn = True
            me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0), vehicle=20)
            act = Action(yaw=2.0, pitch=0.0)
            b.turn_cap(me, act, DT)
            self.assertAlmostEqual(act.yaw, vehicles.SCORPION_TURN * DT, places=6)
            b.scorpion_turn = False
            act = Action(yaw=2.0, pitch=0.0)
            b.turn_cap(me, act, DT)
            self.assertAlmostEqual(act.yaw, b.p.turn * DT, places=6)


class AimTests(unittest.TestCase):
    def test_a_man_on_foot_in_his_real_chest(self):
        b = bot("top", "h4_ca_blood_crash")
        me, him, vs = world()
        tick(b, 10.0, me, him, vs)
        cam = me.pos + Vec(0.0, 0.0, vehicles.DRIVER_VIEW["scorpion"][0])
        want = angles_to(cam, h4_chest(him))
        over = angles_to(cam, him.pos + Vec(0.0, 0.0, 0.35))     # the generic chest: over his head
        feet = angles_to(cam, him.pos + Vec(0.0, 0.0, 0.05))     # the splash aim it had
        self.assertGreater(him.pos.z + 0.35, him.head_pos.z)
        self.assertAlmostEqual(b.aim.goal[1], want[1], delta=0.0005)
        self.assertGreater(abs(over[1] - want[1]), 0.01)
        self.assertGreater(abs(feet[1] - b.aim.goal[1]), 0.002)

    def test_a_vehicle_keeps_its_aim(self):
        b = bot("top", "h4_ca_blood_crash")
        me, him, vs = world(riding=True)
        tick(b, 10.0, me, him, vs)
        cam = me.pos + Vec(0.0, 0.0, vehicles.DRIVER_VIEW["scorpion"][0])
        self.assertAlmostEqual(b.aim.goal[1], angles_to(cam, him.pos + Vec(0.0, 0.0, 0.05))[1], delta=0.002)


class FireTests(unittest.TestCase):
    def test_holds_until_settled(self):
        b = bot("top", "h4_ca_blood_crash")
        me, him, vs = world()
        tick(b, 10.0, me, him, vs)
        me.yaw, me.pitch = b.aim.goal                     # the view arrives on him
        fired = []
        for i in range(1, 8):
            fired.append(tick(b, 10.0 + i * DT, me, him, vs).fire)
        self.assertFalse(fired[0])
        self.assertFalse(fired[1])
        self.assertTrue(fired[-1])
        first = fired.index(True)
        self.assertGreaterEqual(first * DT, vehicles.SCORPION_SETTLE - 1e-9)

    def test_close_range_still_settles(self):
        b = bot("strong", "h4_ca_blood_crash")
        me, him, vs = world(him_at=(6.0, 4.0, 0.38))
        me.yaw = -1.5                                      # well off him, inside 15 u
        self.assertFalse(tick(b, 10.0, me, him, vs).fire)

    def test_easy_keeps_its_shots_on_the_move(self):
        b = bot("novice", "h4_ca_blood_crash")
        me, him, vs = world(him_at=(12.0, 0.5, 0.38))
        act = tick(b, 10.0, me, him, vs)
        self.assertTrue(b.scorpion_turn)
        self.assertTrue(act.fire)


if __name__ == "__main__":
    unittest.main()
