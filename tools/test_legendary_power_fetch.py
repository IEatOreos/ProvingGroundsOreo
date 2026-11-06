"""Power-weapon call scenarios through the real director assignment method.

Run: python tools/test_legendary_power_fetch.py
"""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import PlayerState, Snapshot, Vec
from brain.director import Director
from brain.profiles import make_profile
from brain.scaling import profile as scaling_profile


def participant(tier, distance, pid=0, height=0.0):
    rng = random.Random(pid)
    prof = scaling_profile(1.0, 'rusher', rng) if tier == 'scaling' else make_profile(tier, 'rusher', rng)
    bot = SimpleNamespace(id=pid, p=prof, urgent=lambda *args: False, pressing=lambda *args: False)
    player = PlayerState(pid, 0, 'test', Vec(distance, 0, height), weapon='dmr',
                         weapons=['dmr', 'assault_rifle'], ammo=[45, 160], mag=[15, 32])
    return bot, player


def scenario(participants, loose=True):
    point = Vec()
    director = Director.__new__(Director)
    director.map = {'items': [dict(name='rockets', kind='weapon', value=1.0, pos=point)]}
    director.bots = {bot.id: bot for bot, player in participants}
    director.item_up = {}
    snap = Snapshot(100, [player for bot, player in participants],
                    ground_weapons=[('rockets', point)] if loose else [])
    return director, snap


class LegendaryPowerFetchTests(unittest.TestCase):
    def test_fixed_legendary_receives_distant_call(self):
        bot, player = participant('top', 60)
        director, snap = scenario([(bot, player)])
        director.power_runs(snap.time, snap)
        self.assertEqual(bot.fetch[:2], (Vec(), 'rockets'))

    def test_other_difficulties_and_scaling_keep_original_range(self):
        for tier in ['novice', 'average', 'strong', 'scaling']:
            with self.subTest(tier=tier):
                bot, player = participant(tier, 60)
                director, snap = scenario([(bot, player)])
                director.power_runs(snap.time, snap)
                self.assertIsNone(getattr(bot, 'fetch', None))
        for tier in ['average', 'strong', 'scaling']:
            with self.subTest(nearby=tier):
                bot, player = participant(tier, 39)
                director, snap = scenario([(bot, player)])
                director.power_runs(snap.time, snap)
                self.assertIsNotNone(getattr(bot, 'fetch', None))

    def test_radius_and_height_limits(self):
        for tier, distance, height, expected in [('top', 79.9, 0, True), ('top', 80, 0, False),
                                                  ('average', 40, 0, False), ('top', 30, 6, False)]:
            with self.subTest(tier=tier, distance=distance, height=height):
                bot, player = participant(tier, distance, height=height)
                director, snap = scenario([(bot, player)])
                director.power_runs(snap.time, snap)
                self.assertEqual(getattr(bot, 'fetch', None) is not None, expected)

    def test_distant_order_survives_the_old_timeout(self):
        bot, player = participant('top', 79)
        director, snap = scenario([(bot, player)])
        director.power_runs(snap.time, snap)
        original = bot.fetch
        self.assertGreater(original[2], 100 + 79 / 2.3)
        snap.time = 126  # old 25-second lifetime would already have elapsed
        director.power_runs(snap.time, snap)
        self.assertEqual(bot.fetch, original)
        for tier in ['top', 'average', 'strong', 'scaling']:
            bot, player = participant(tier, 10)
            director, snap = scenario([(bot, player)])
            director.power_runs(snap.time, snap)
            self.assertEqual(bot.fetch[2], snap.time + 25)

    def test_nearest_eligible_bot_is_the_only_fetcher(self):
        near_bot, near_player = participant('top', 60, pid=0)
        far_bot, far_player = participant('top', 70, pid=1)
        director, snap = scenario([(far_bot, far_player), (near_bot, near_player)])
        director.power_runs(snap.time, snap)
        self.assertIsNotNone(getattr(near_bot, 'fetch', None))
        self.assertIsNone(getattr(far_bot, 'fetch', None))
        director.power_runs(snap.time + 1, snap)
        self.assertIsNone(getattr(far_bot, 'fetch', None))

    def test_existing_eligibility_restrictions_remain(self):
        for reason in ['dead', 'carrier', 'vehicle', 'power_weapon', 'urgent', 'pressing']:
            with self.subTest(reason=reason):
                bot, player = participant('top', 60)
                if reason == 'dead':
                    player.alive = False
                elif reason == 'carrier':
                    player.has_flag = True
                elif reason == 'vehicle':
                    player.vehicle = 12
                elif reason == 'power_weapon':
                    player.weapons.append('rockets')
                elif reason == 'urgent':
                    bot.urgent = lambda *args: True
                elif reason == 'pressing':
                    bot.pressing = lambda *args: True
                director, snap = scenario([(bot, player)])
                director.press_fetch_ok = lambda *args: False
                director.power_runs(snap.time, snap)
                self.assertIsNone(getattr(bot, 'fetch', None))

    def test_missing_weapon_cancels_call_and_spawn_deadline_is_unchanged(self):
        bot, player = participant('top', 60)
        director, snap = scenario([(bot, player)])
        director.power_runs(snap.time, snap)
        snap.ground_weapons = []
        director.power_runs(snap.time + 1, snap)
        self.assertIsNone(bot.fetch)
        director.item_up[0] = 105
        director.power_runs(100, snap)
        self.assertEqual(bot.fetch[2], 113)  # respawn + existing eight-second wait
        self.assertEqual(bot.fetch[3], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
