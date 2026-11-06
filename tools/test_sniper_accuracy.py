"""Offline checks for sniper accuracy, action delivery and difficulty isolation."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Aim, Bot, SNIPER_HIT_CHANCE, percentage_sniper
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to, eye
from brain.profiles import make_profile
from brain.scaling import profile as scaling_profile


def scene(tier="strong", mag=4):
    prof = (scaling_profile(0.5, "sniper", random.Random(2)) if tier == "scaling"
            else make_profile(tier, "sniper", random.Random(2)))
    bot = Bot(0, 0, prof, {"name": "reach_test"}, random.Random(123))
    bot.notes, bot.shot_part, bot.next_fire = [], (1, True), 0.0
    me = PlayerState(0, 0, "bot", Vec(), weapon="sniper", weapons=["sniper"], mag=[mag])
    target = PlayerState(1, 1, "target", Vec(20, 0, 0), head_pos=Vec(20, 0, 0.7))
    return bot, me, target, Snapshot(0, [me, target])


class SniperAccuracy(unittest.TestCase):
    def test_distribution_per_consumed_round(self):
        for tier, chance in SNIPER_HIT_CHANCE.items():
            bot, me, target, snap = scene(tier, 10001)
            hits = 0
            for k in range(10000):
                me.mag[0] -= 1
                act = Action(fire=True)
                bot.percentage_sniper_shot(k, me, snap, act)
                hits += bot.sniper_roll["hit"]
                exact = angles_to(eye(me), target.head_pos)
                if bot.sniper_roll["hit"]:
                    self.assertAlmostEqual(act.yaw, exact[0])
                    self.assertAlmostEqual(act.pitch, exact[1])
                else:
                    # The bullet crosses the target's range well outside its body.
                    self.assertGreater(abs(math.tan(act.yaw) * 20), 0.85)
            self.assertAlmostEqual(hits / 10000, chance, delta=0.02)

    def test_rejected_attempts_do_not_reroll(self):
        bot, me, _, snap = scene()
        bot.percentage_sniper_shot(0, me, snap, Action(fire=True))
        original, rng = bot.sniper_roll, bot.rng.getstate()
        for now in (0.03, 0.1, 1, 3, 10):
            bot.percentage_sniper_shot(now, me, snap, Action(fire=False))
            bot.percentage_sniper_shot(now, me, snap, Action(fire=True))
            self.assertIs(bot.sniper_roll, original)
            self.assertEqual(bot.rng.getstate(), rng)
        me.mag[0] -= 1
        bot.percentage_sniper_shot(11, me, snap, Action(fire=True))
        self.assertIsNot(bot.sniper_roll, original)

    def test_consumption_and_reload_observed_between_requests(self):
        bot, me, _, snap = scene()
        bot.percentage_sniper_shot(0, me, snap, Action(fire=True))
        me.mag[0] = 3
        bot.percentage_sniper_shot(1, me, snap, Action())
        self.assertIsNone(bot.sniper_roll)
        me.mag[0] = 4
        bot.percentage_sniper_shot(3, me, snap, Action(fire=True))
        self.assertEqual(bot.sniper_roll["mag"], 4)

    def test_grenade_melee_switch_and_empty_do_not_spend_roll(self):
        for action in (Action(), Action(fire=True, grenade=True), Action(fire=True, melee=True),
                       Action(fire=True, weapon=1)):
            bot, me, _, snap = scene()
            before = bot.rng.getstate()
            bot.percentage_sniper_shot(0, me, snap, action)
            self.assertEqual(before, bot.rng.getstate())
        bot, me, _, snap = scene(mag=0)
        before = bot.rng.getstate()
        bot.percentage_sniper_shot(0, me, snap, Action(fire=True))
        self.assertEqual(before, bot.rng.getstate())

    def test_unknown_magazine_retries_are_bounded(self):
        bot, me, _, snap = scene(mag=-1)
        bot.percentage_sniper_shot(0, me, snap, Action(fire=True))
        original = bot.sniper_roll
        bot.nade_retry = {"until": 2}
        bot.percentage_sniper_shot(1, me, snap, Action(fire=True))
        self.assertIs(bot.sniper_roll, original)
        bot.nade_retry = None
        bot.percentage_sniper_shot(2, me, snap, Action(fire=True))
        self.assertIsNot(bot.sniper_roll, original)

    def test_legendary_scaling_other_weapons_and_vehicles_are_exempt(self):
        for tier in ("top", "scaling"):
            bot, me, _, snap = scene(tier)
            act = Action(fire=True, yaw=0.3, pitch=0.4)
            before = bot.rng.getstate()
            bot.percentage_sniper_shot(0, me, snap, act)
            self.assertEqual((act.yaw, act.pitch), (0.3, 0.4))
            self.assertEqual(before, bot.rng.getstate())
        bot, me, _, snap = scene()
        me.weapon = "dmr"
        self.assertFalse(percentage_sniper(bot.p, me))
        me.weapon, me.vehicle = "sniper", 42
        self.assertFalse(percentage_sniper(bot.p, me))
        me.vehicle = -1
        snap.players[1].vehicle = 50
        act = Action(fire=True, yaw=0.3, pitch=0.4)
        before = bot.rng.getstate()
        bot.percentage_sniper_shot(0, me, snap, act)
        self.assertTrue(act.fire)
        self.assertEqual((act.yaw, act.pitch), (0.3, 0.4))
        self.assertEqual(before, bot.rng.getstate())

    def test_perfect_tracking_bypasses_old_aim_errors(self):
        for tier in SNIPER_HIT_CHANCE:
            bot, me, target, _ = scene(tier)
            aim = Aim(bot.p, random.Random(5))
            got = aim.step(0, 1/30, me, target.id, target.pos, Vec(3, 2, 0), True, precise=True)
            self.assertEqual(got, angles_to(eye(me), target.pos + Vec(0, 0, 0.62)))
            self.assertIsNone(aim.flick)

    def test_final_think_path_uses_live_head_and_preserves_world_movement(self):
        bot, me, target, snap = scene()
        bot.sniper_roll = dict(mag=4, hit=True, side=1, margin=1, next_roll=1)
        def plan(*args):
            bot.shot_part = (target.id, True)
            return Action(fire=True, yaw=1, forward=0.3, strafe=0.2)
        bot.plan = plan
        act = bot.think(0, 1/30, snap, None, None, [])
        self.assertEqual((act.yaw, act.pitch), angles_to(eye(me), target.head_pos))
        self.assertAlmostEqual(math.cos(act.yaw)*act.forward-math.sin(act.yaw)*act.strafe,
                               math.cos(1)*0.3-math.sin(1)*0.2)

    def test_deliberate_miss_does_not_learn_false_wall(self):
        bot, me, target, _ = scene()
        bot.fired_last, bot.sniper_missed_last, bot.now = True, True, 5
        bot.aim = SimpleNamespace(on_target=lambda *a: True)
        bot.dry_fire_check(me, target, target.id)
        self.assertEqual(bot.dry_shots[target.id][0], 0)


if __name__ == "__main__":
    unittest.main()
