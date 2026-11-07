"""Regression scenarios for Reach weapon pickups and selection.

Run: python tools/test_reach_loadout.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Belief, Bot, loadout_value, proficiency
from brain.core import PlayerState, Snapshot, Vec
from brain.profiles import make_profile
from brain.scaling import profile as scaling_profile


def bot_for(tier='top', game='reach'):
    rng = random.Random(7)
    prof = scaling_profile(1.0, 'rusher', rng) if tier == 'scaling' else make_profile(tier, 'rusher', rng)
    bot = Bot(0, 0, prof, {'name': game + '_test'}, rng)
    bot.notes = []
    return bot


def player_with(primary='dmr', secondary='assault_rifle'):
    return PlayerState(0, 0, 'test', Vec(), weapon=primary,
                       weapons=[primary, secondary], ammo=[45, 32], mag=[15, 8])


class ReachLoadoutTests(unittest.TestCase):
    def test_readies_loaded_rockets_after_close_radar_contact_ages_out(self):
        bot = bot_for(tier='average')
        me = player_with(secondary='rockets')
        me.weapon = 'rockets'
        me.mag[1] = 2
        enemy = PlayerState(1, 1, 'enemy', Vec(3.9, 0, 0))
        bot.per.beliefs[enemy.id] = Belief(enemy.pos, Vec(), 10, False, 'radar')
        self.assertEqual(bot.choose_weapon(10, me, 'hold', None, Snapshot(10, [me, enemy])), 0)
        me.weapon = 'dmr'
        self.assertEqual(bot.choose_weapon(14, me, 'hold', None, Snapshot(14, [me, enemy])), 1)

    def test_readies_rockets_in_range_when_loaded(self):
        for magazine, slot in [(2, 1), (0, -1)]:
            with self.subTest(magazine=magazine):
                bot = bot_for(tier='average')
                me = player_with(secondary='rockets')
                me.mag[1] = magazine
                enemy = PlayerState(1, 1, 'enemy', Vec(14, 0, 0))
                bot.per.beliefs[enemy.id] = Belief(enemy.pos, Vec(), 10, True, 'eyes')
                self.assertEqual(bot.choose_weapon(10, me, 'fight', enemy.id, Snapshot(10, [me, enemy])), slot)

    def test_reach_prefers_dmr_shotgun_and_selects_ar_to_drop(self):
        for tier in ['novice', 'average', 'strong', 'top', 'scaling']:
            with self.subTest(tier=tier):
                bot = bot_for(tier)
                me = player_with()
                point = Vec(1, 0, 0)
                snap = Snapshot(10, [me], ground_weapons=[('shotgun', point)])
                self.assertAlmostEqual(loadout_value(me.weapons, bot.rank, bot.game), 0.91)
                self.assertAlmostEqual(loadout_value(['dmr', 'shotgun'], bot.rank, bot.game), 0.97)
                self.assertEqual(bot.upgrade_point(me, snap, reach=14), point)
                self.assertEqual(bot.gun_to_drop(me, 'item', point), 1)
                # The real selection path equips the AR for replacement, retaining the DMR.
                self.assertEqual(bot.choose_weapon(10, me, 'item', point, snap), 1)

    def test_reach_keeps_shotgun_when_offered_ar(self):
        bot = bot_for()
        me = player_with(secondary='shotgun')
        snap = Snapshot(10, [me], ground_weapons=[('assault_rifle', Vec(1, 0, 0))])
        self.assertIsNone(bot.upgrade_point(me, snap, reach=14))

    def test_focus_replaces_dmr_and_keeps_the_short_range_secondary(self):
        for tier in ['novice', 'average', 'strong', 'top', 'scaling']:
            for secondary, before, after in [('assault_rifle', 0.91, 0.98), ('shotgun', 0.97, 1.04)]:
                with self.subTest(tier=tier, secondary=secondary):
                    bot = bot_for(tier)
                    me = player_with(secondary=secondary)
                    me.weapon = secondary
                    point = Vec(1, 0, 0)
                    snap = Snapshot(10, [me], ground_weapons=[('focus_rifle', point)])
                    self.assertAlmostEqual(loadout_value(me.weapons, bot.rank, bot.game), before)
                    self.assertAlmostEqual(loadout_value(['focus_rifle', secondary], bot.rank, bot.game), after)
                    self.assertAlmostEqual(loadout_value(['dmr', 'focus_rifle'], bot.rank, bot.game), 0.92)
                    self.assertEqual(bot.upgrade_point(me, snap, reach=14), point)
                    self.assertEqual(bot.gun_to_drop(me, 'item', point), 0)
                    self.assertEqual(bot.choose_weapon(10, me, 'item', point, snap), 0)

    def test_loaded_focus_ar_does_not_swap_back_for_a_dmr(self):
        bot = bot_for()
        me = player_with(primary='focus_rifle')
        me.ammo[0], me.mag[0] = -1, -1  # battery remains unknown, not empty
        snap = Snapshot(10, [me], ground_weapons=[('dmr', Vec(1, 0, 0))])
        self.assertIsNone(bot.upgrade_point(me, snap, reach=14))

    def test_other_games_keep_original_ar_rating_and_pickups(self):
        for game, primary in [('ce', 'pistol'), ('h3', 'battle_rifle'), ('h4', 'dmr')]:
            with self.subTest(game=game):
                bot = bot_for(game=game)
                self.assertEqual(proficiency('assault_rifle', game=game)[0], 1.0)
                self.assertEqual(bot.rank('dmr'), 3.6)
                self.assertEqual(bot.rank('focus_rifle'), 3.2)
                me = player_with(primary=primary)
                snap = Snapshot(10, [me], ground_weapons=[('shotgun', Vec(1, 0, 0))])
                self.assertIsNone(bot.upgrade_point(me, snap, reach=14))

    def test_pickup_distance_and_recent_swap_restrictions_remain(self):
        bot = bot_for()
        me = player_with()
        far = Snapshot(10, [me], ground_weapons=[('shotgun', Vec(20, 0, 0))])
        self.assertIsNone(bot.upgrade_point(me, far, reach=14))
        point = Vec(1, 0, 0)
        bot.swap_rest = [(point, 30)]
        nearby = Snapshot(10, [me], ground_weapons=[('shotgun', point)])
        self.assertIsNone(bot.upgrade_point(me, nearby, reach=14))


if __name__ == '__main__':
    unittest.main(verbosity=2)
