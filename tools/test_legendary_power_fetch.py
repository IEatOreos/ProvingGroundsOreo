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
    def test_difficulty_priority_and_fallback_override_distance(self):
        tiers = ['demon', 'top', 'strong', 'average']
        for start in range(len(tiers)):
            group = [participant(tier, 30-i*4, pid=i) for i, tier in enumerate(tiers[start:])]
            director, snap = scenario(list(reversed(group)))
            director.power_runs(snap.time, snap)
            self.assertIsNotNone(getattr(group[0][0], 'fetch', None))
            self.assertEqual(sum(getattr(b, 'fetch', None) is not None for b, p in group), 1)

    def test_ineligible_demon_does_not_block_legendary(self):
        demon, dp = participant('demon', 81, pid=0)
        top, tp = participant('top', 70, pid=1)
        director, snap = scenario([(demon, dp), (top, tp)])
        director.power_runs(snap.time, snap)
        self.assertIsNone(getattr(demon, 'fetch', None))
        self.assertIsNotNone(top.fetch)

    def test_fixed_legendary_receives_distant_call(self):
        for tier in ('top','demon'):
            bot, player = participant(tier, 60)
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


class UnreachableGunTests(unittest.TestCase):
    """(Custom) no fixed Legendary or Demon run at a gun the nav has no way to (Director.fetch_reachable)."""

    def test_unreachable_gun_gets_no_fixed_high_fetcher(self):
        for tier in ('demon', 'top'):
            with self.subTest(tier=tier):
                bot, player = participant(tier, 20)
                director, snap = scenario([(bot, player)])
                director.fetch_reachable = lambda a, q: False
                director.power_runs(snap.time, snap)
                self.assertIsNone(getattr(bot, 'fetch', None))

    def test_reachable_gun_still_called_and_other_tiers_unchanged(self):
        bot, player = participant('demon', 20)
        director, snap = scenario([(bot, player)])
        director.fetch_reachable = lambda a, q: True
        director.power_runs(snap.time, snap)
        self.assertIsNotNone(bot.fetch)
        heroic, hp = participant('strong', 20)
        director, snap = scenario([(heroic, hp)])
        director.fetch_reachable = lambda a, q: False     # (not consulted for Heroic)
        director.power_runs(snap.time, snap)
        self.assertIsNotNone(heroic.fetch)

    def test_unreachable_for_the_demon_falls_to_a_legendary_who_can(self):
        demon, dp = participant('demon', 10, pid=0)
        top, tp = participant('top', 30, pid=1)
        director, snap = scenario([(demon, dp), (top, tp)])
        director.fetch_reachable = lambda a, q: a.x > 20      # only the Legendary 30 u off has a way
        director.power_runs(snap.time, snap)
        self.assertIsNone(getattr(demon, 'fetch', None))
        self.assertIsNotNone(top.fetch)

    def test_bare_director_without_terrain_keeps_calling(self):
        director, snap = scenario([participant('demon', 20)])
        self.assertTrue(director.fetch_reachable(Vec(20, 0, 0), Vec()))


class DemonFetchCommitTests(unittest.TestCase):
    """(Custom) a Demon a few steps from the gun it was sent for takes it before a new fight (Bot.decide, a real map)."""

    @classmethod
    def setUpClass(cls):
        from brain.maps import load_map
        cls.map = load_map("reach_cex_headlong")

    def decide(self, tier, gun_off):
        from brain.bot import Bot, Belief
        b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), self.map, random.Random(5))
        me = PlayerState(0, 0, "bot", Vec(-27.3 + gun_off, 14.6, 7.6), weapon="dmr", weapons=["dmr", "assault_rifle"],
                         ammo=[45, 160], mag=[15, 32])
        foe = PlayerState(1, 1, "foe", Vec(me.pos.x, me.pos.y - 14.0, 7.6), weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        foe.yaw = 3.14
        snap = Snapshot(100.0, [me, foe], mode="slayer")
        b.per.beliefs[1] = Belief(foe.pos, Vec(), 100.0, True, "eyes")
        b.per.recognized.add(1)
        b.per.last_seen[1] = 100.0
        b.fetch = (Vec(-27.3, 14.6, 7.6), "rockets", 130.0, None)
        return b.decide(100.0, me, snap)[0]

    def test_demon_takes_the_gun_close_by_over_a_man_in_view(self):
        self.assertEqual(self.decide("demon", 6.0), "item")

    def test_far_gun_and_other_tiers_keep_the_fight(self):
        self.assertEqual(self.decide("demon", 20.0), "fight")
        self.assertEqual(self.decide("top", 6.0), "fight")


if __name__ == '__main__':
    unittest.main(verbosity=2)
