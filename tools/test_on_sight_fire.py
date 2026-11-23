"""(custom, Nov 22) A man in the crosshair is shot (Bot.on_sight_fire), and reloads wait while a man is near
(Bot.reload_check). The owner: "when an enemy peaks I want the bot to instantly shoot them at whatever body part they
see no matter what"; "reloading as soon as they get a kill with over more than half a mag"; "reloading with ammo in the
mag when people are shooting them and are on radar"."""
import math
import random
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B  # noqa: E402
from brain.bot import Belief  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


def mk(tier="demon", los=lambda a, b: True):
    b = B.Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    b.game, b.notes = "reach", []
    b.T = lambda: types.SimpleNamespace(los=los)
    b.line_clear = lambda now, me, k, snap: True
    return b


def scene(tier="demon", foe_at=Vec(12, 0, 0), yaw=0.0, los=lambda a, b: True, parts=(True, True)):
    b = mk(tier, los)
    me = PlayerState(0, 0, "b", Vec(), weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15], yaw=yaw)
    foe = PlayerState(1, 1, "e", foe_at, weapon="dmr")
    b.per.beliefs[1] = Belief(foe.pos, Vec(), 10.0, True, "eyes")
    b.per.recognized.add(1)
    b.per.visible_enemies = lambda: [1]
    b.per.target_parts = {1: parts}
    me.pitch = math.atan2(0.62 - 0.62, 12.0)          # (level: his eye height)
    return b, me, foe, Snapshot(10.0, [me, foe])


class OnSightTests(unittest.TestCase):
    def test_fires_at_a_man_in_the_crosshair(self):
        for tier in ("top", "mythic", "demon", "noble"):
            b, me, foe, sn = scene(tier)
            a = Action()
            b.on_sight_fire(10.0, me, a, sn)
            self.assertTrue(a.fire, tier)
            self.assertEqual(b.shot_part, (1, True))
            b.fire_gate(10.0, me, a, sn)
            self.assertTrue(a.fire, tier)

    def test_whatever_part_it_sees(self):
        b, me, foe, sn = scene(parts=(True, False))             # (the chest only: the shot's part the chest)
        a = Action()
        b.on_sight_fire(10.0, me, a, sn)
        self.assertTrue(a.fire)
        self.assertEqual(b.shot_part, (1, False))
        low = lambda a_, p: p.z < 0.3                            # (his legs only, below a ledge's lip)
        b, me, foe, sn = scene(los=low, parts=(False, False))
        me.pitch = math.atan2(0.2 - 0.62, 12.0)
        a = Action()
        b.on_sight_fire(10.0, me, a, sn)
        self.assertTrue(a.fire)

    def test_not_off_him_nor_through_a_wall_nor_the_low_tiers(self):
        b, me, foe, sn = scene(yaw=0.3)                          # (the view 17 deg off him)
        a = Action()
        b.on_sight_fire(10.0, me, a, sn)
        self.assertFalse(a.fire)
        b, me, foe, sn = scene(los=lambda a_, p: False)
        a = Action()
        b.on_sight_fire(10.0, me, a, sn)
        self.assertFalse(a.fire)
        for tier in ("novice", "average", "strong"):
            b, me, foe, sn = scene(tier)
            a = Action()
            b.on_sight_fire(10.0, me, a, sn)
            self.assertFalse(a.fire, tier)

    def test_the_man_hurting_it_needs_a_line_too(self):
        # (Nov 22: trusting his hits blind shot into a platform's edge; Terrain._ray's piece tops fixed the false blocks)
        b, me, foe, sn = scene(los=lambda a_, p: False)
        b.per.attacker_id, b.per.attacker_t = 1, 9.6
        a = Action()
        b.on_sight_fire(10.0, me, a, sn)
        self.assertFalse(a.fire)
        b, me, foe, sn = scene()
        b.per.visible_enemies = lambda: []                       # (not in its eyes, but hitting it, with a line)
        b.per.attacker_id, b.per.attacker_t = 1, 9.6
        a = Action()
        b.on_sight_fire(10.0, me, a, sn)
        self.assertTrue(a.fire)

    def test_paced_and_released(self):
        b, me, foe, sn = scene()
        a = Action()
        b.on_sight_fire(10.0, me, a, sn)
        b.fired_last = True
        a2 = Action()
        b.on_sight_fire(10.03, me, a2, sn)                      # (the semi-auto's release)
        self.assertFalse(a2.fire)
        b.fired_last = False
        a3 = Action()
        b.on_sight_fire(10.06, me, a3, sn)                      # (its gun's pace)
        self.assertFalse(a3.fire)
        a4 = Action()
        b.on_sight_fire(11.0, me, a4, sn)
        self.assertTrue(a4.fire)

    def test_not_with_a_blade_an_empty_magazine_or_a_throw(self):
        b, me, foe, sn = scene()
        me.mag = [0]
        a = Action()
        b.on_sight_fire(10.0, me, a, sn)
        self.assertFalse(a.fire)
        b, me, foe, sn = scene()
        a = Action(grenade=True)
        b.on_sight_fire(10.0, me, a, sn)
        self.assertFalse(a.fire)


def rsetup(mag):
    b = mk("demon")
    b.mag_max = {"dmr": 15}
    me = PlayerState(0, 0, "b", Vec(), weapon="dmr", weapons=["dmr"], ammo=[mag + 45], mag=[mag])
    b.per.visible_enemies = lambda: []
    return b, me


class ReloadThreatTests(unittest.TestCase):
    def test_a_man_on_radar_keeps_the_magazine(self):
        b, me = rsetup(9)
        b.per.beliefs[1] = Belief(Vec(20, 0, 0), Vec(), 49.0, False, "radar")
        foe = PlayerState(1, 1, "e", Vec(20, 0, 0))
        a = Action()
        b.reload_check(50.0, me, a, Snapshot(50.0, [me, foe]))
        self.assertFalse(a.reload)
        b, me = rsetup(3)                                        # (nearly empty: reloaded)
        b.per.beliefs[1] = Belief(Vec(20, 0, 0), Vec(), 49.0, False, "radar")
        a = Action()
        b.reload_check(50.0, me, a, Snapshot(50.0, [me, foe]))
        self.assertTrue(a.reload)

    def test_after_a_kill_half_or_less(self):
        b, me = rsetup(9)
        b.kill_seen = (49.0, Vec(5, 0, 0))
        a = Action()
        b.reload_check(50.0, me, a, Snapshot(50.0, [me]))
        self.assertFalse(a.reload)                               # (9 of 15: over half, kept)
        b, me = rsetup(7)
        b.kill_seen = (49.0, Vec(5, 0, 0))
        a = Action()
        b.reload_check(50.0, me, a, Snapshot(50.0, [me]))
        self.assertTrue(a.reload)
        b, me = rsetup(11)                                       # (quiet, no kill lately: the 80% top-off)
        a = Action()
        b.reload_check(50.0, me, a, Snapshot(50.0, [me]))
        self.assertTrue(a.reload)

    def test_a_dead_mans_belief_is_no_threat(self):
        b, me = rsetup(9)
        b.per.beliefs[1] = Belief(Vec(20, 0, 0), Vec(), 49.9, True, "eyes")
        foe = PlayerState(1, 1, "e", Vec(20, 0, 0), alive=False)
        a = Action()
        b.reload_check(50.0, me, a, Snapshot(50.0, [me, foe]))
        self.assertTrue(a.reload)


if __name__ == "__main__":
    unittest.main()
