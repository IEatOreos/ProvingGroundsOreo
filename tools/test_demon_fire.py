"""Reach Demon fires at the exposed part through the normal think/plan path."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot
from brain.core import PlayerState, Snapshot, Vec, angles_to, eye
from brain.profiles import make_profile


class Cover:
    see_clear = True

    def __init__(self, sight, shot, live_head):
        self.sight, self.shot, self.live_head = sight, shot, live_head
        self.head_rays = []

    def sees(self, *args):
        return any(self.sight)

    def shot_los(self, *args):
        return False  # the old generic ray can disagree with a clear ray to a specific part

    def target_parts(self, *args, mode=None):
        return self.shot if mode == "shot" else self.sight

    def point_los(self, origin, point, mode=None):
        self.head_rays.append((origin, point, mode))
        return self.live_head[mode == "shot"]


class DemonFireTests(unittest.TestCase):
    def scene(self, sight, shot, *, weapon="dmr", tier="demon", live_head=None, game="reach"):
        cover = Cover(sight, shot, live_head)
        rng = random.Random(1)
        bot = Bot(0, 0, make_profile(tier, "rusher", rng), {"name": game + "_test"}, rng)
        bot._terrain = cover
        bot.goal, bot.next_decide = ("fight", 1), 10.0
        bot.per.recognized.add(1)
        # Keep map navigation out of the constructed lane. Perception, fight, trigger and final aim are real.
        for name in ("no_wall_jump", "edge_guard", "obstacle_guard", "unstuck"):
            setattr(bot, name, lambda *args: None)
        me = PlayerState(0, 0, "bot", Vec(), weapon=weapon, weapons=[weapon], mag=[15], ammo=[45])
        target = PlayerState(1, 1, "enemy", Vec(10, 0, 0))
        if live_head is not None:
            target.head_pos = Vec(10, 0.08, 0.52)
        return bot, me, target, cover

    def step(self, bot, me, target, cover, now=1.0, vehicles=()):
        snap = Snapshot(now, [me, target], vehicles=vehicles)
        return bot.think(now, 1 / 30, snap, cover.sees, lambda a, b, **kw: b, [])

    def test_dmr_fires_at_clear_chest_and_keeps_cadence(self):
        bot, me, target, cover = self.scene((True, True), (True, False), live_head=(True, False))
        action = self.step(bot, me, target, cover)
        self.assertTrue(action.fire)
        self.assertEqual(bot.fx["part"], "chest")
        self.assertEqual((action.yaw, action.pitch), angles_to(eye(me), target.pos + Vec(0, 0, 0.35)))
        self.assertFalse(self.step(bot, me, target, cover, now=1.1).fire)

    def test_dmr_uses_animated_head_for_sight_ballistics_and_final_aim(self):
        bot, me, target, cover = self.scene((False, False), (False, False), live_head=(True, True))
        action = self.step(bot, me, target, cover)
        self.assertTrue(action.fire)
        self.assertEqual(bot.fx["part"], "head")
        self.assertEqual((action.yaw, action.pitch), angles_to(eye(me), target.head_pos))
        self.assertIn((eye(me), target.head_pos, "see"), cover.head_rays)
        self.assertIn((eye(me), target.head_pos, "shot"), cover.head_rays)

    def test_assault_rifle_fires_when_only_head_is_exposed(self):
        bot, me, target, cover = self.scene((False, True), (False, True), weapon="assault_rifle")
        self.assertTrue(self.step(bot, me, target, cover).fire)
        self.assertEqual(bot.fx["part"], "head")

    def test_sniper_keeps_animated_head_priority_and_cadence(self):
        bot, me, target, cover = self.scene((True, True), (True, True), weapon="sniper", live_head=(True, True))
        action = self.step(bot, me, target, cover)
        self.assertTrue(action.fire)
        self.assertEqual(bot.fx["part"], "head")
        self.assertEqual((action.yaw, action.pitch), angles_to(eye(me), target.head_pos))
        self.assertFalse(self.step(bot, me, target, cover, now=1.1).fire)

    def test_visibility_alone_does_not_clear_bulletproof_cover(self):
        bot, me, target, cover = self.scene((True, True), (False, False))
        self.assertFalse(self.step(bot, me, target, cover).fire)
        self.assertIn(target.id, bot.per.visible_enemies())
        self.assertFalse(bot.fx["line"])

    def test_vehicle_blocks_otherwise_clear_shot(self):
        bot, me, target, cover = self.scene((True, True), (True, True))
        blocker = {"handle": 42, "pos": Vec(5, 0, 0)}
        self.assertFalse(self.step(bot, me, target, cover, vehicles=(blocker,)).fire)

    def test_firing_stops_on_lost_sight_even_with_tracker_contact(self):
        bot, me, target, cover = self.scene((True, True), (True, True), weapon="assault_rifle")
        self.assertTrue(self.step(bot, me, target, cover).fire)
        cover.sight, cover.shot = (False, False), (False, False)
        target.vel = Vec(1, 0, 0)
        self.assertFalse(self.step(bot, me, target, cover, now=1.05).fire)
        self.assertEqual(bot.per.beliefs[target.id].source, "radar")

    def test_armor_lock_stops_an_automatic_burst(self):
        bot, me, target, cover = self.scene((True, True), (True, True), weapon="assault_rifle")
        self.assertTrue(self.step(bot, me, target, cover).fire)
        target.equipment, target.ability_on = "armor_lock", True
        self.assertFalse(self.step(bot, me, target, cover, now=1.05).fire)

    def test_legendary_and_demon_in_other_games_keep_existing_trigger(self):
        for tier, game in (("top", "reach"), ("demon", "h4")):
            with self.subTest(tier=tier, game=game):
                scene = self.scene((True, False), (True, False), tier=tier, game=game)
                self.assertFalse(self.step(*scene).fire)


if __name__ == "__main__":
    unittest.main()
