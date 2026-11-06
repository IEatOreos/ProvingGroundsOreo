"""Regression scenarios for Reach's AR-to-shotgun loadout upgrade.

Run: python tools/test_reach_loadout.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot, loadout_value, proficiency
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
    def test_reach_prefers_dmr_shotgun_and_selects_ar_to_drop(self):
        for tier in ['novice', 'average', 'strong', 'top', 'scaling']:
            with self.subTest(tier=tier):
                bot = bot_for(tier)
                me = player_with()
                point = Vec(1, 0, 0)
                snap = Snapshot(10, [me], ground_weapons=[('shotgun', point)])
                self.assertAlmostEqual(loadout_value(me.weapons, bot.rank, bot.game), 0.95)
                self.assertAlmostEqual(loadout_value(['dmr', 'shotgun'], bot.rank, bot.game), 1.01)
                self.assertEqual(bot.upgrade_point(me, snap, reach=14), point)
                self.assertEqual(bot.gun_to_drop(me, 'item', point), 1)
                # The real selection path equips the AR for replacement, retaining the DMR.
                self.assertEqual(bot.choose_weapon(10, me, 'item', point, snap), 1)

    def test_reach_keeps_shotgun_when_offered_ar(self):
        bot = bot_for()
        me = player_with(secondary='shotgun')
        snap = Snapshot(10, [me], ground_weapons=[('assault_rifle', Vec(1, 0, 0))])
        self.assertIsNone(bot.upgrade_point(me, snap, reach=14))

    def test_other_games_keep_original_ar_rating_and_pickups(self):
        for game, primary in [('ce', 'pistol'), ('h3', 'battle_rifle'), ('h4', 'dmr')]:
            with self.subTest(game=game):
                bot = bot_for(game=game)
                self.assertEqual(proficiency('assault_rifle', game=game)[0], 1.0)
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
