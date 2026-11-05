"""Offline regressions for Reach ammo integration; no running game required.

Run: python tools/test_reach_ammo.py
"""
import random
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot
from brain.core import Action, PlayerState, Snapshot, Vec
from brain.live import LiveReach
from brain.profiles import make_profile
from brain.scaling import profile as scaling_profile


def reader(weapon, reserve, magazine, dll='haloreach.dll'):
    live = LiveReach.__new__(LiveReach)
    live.object = lambda handle: 0x1000
    live.weapon_name = lambda handle: weapon
    live.g = SimpleNamespace(dll=dll, read=lambda address, size: struct.pack('<hxxh', reserve, magazine))
    return live


def bot_for(tier):
    rng = random.Random(7)
    prof = scaling_profile(1.0, 'rusher', rng) if tier == 'scaling' else make_profile(tier, 'rusher', rng)
    bot = Bot(0, 0, prof, {'name': 'reach_test'}, rng)
    bot.notes = []
    return bot


class ReachAmmoTests(unittest.TestCase):
    def test_controlled_live_sequences(self):
        # Values observed in the same DMR/sniper objects during the live experiment.
        for weapon, reserve, mag in [('dmr', 30, 15), ('dmr', 30, 12), ('dmr', 27, 15),
                                     ('sniper', 4, 4), ('sniper', 4, 3), ('sniper', 3, 4),
                                     ('sniper', 0, 0)]:
            with self.subTest(weapon=weapon, reserve=reserve, mag=mag):
                self.assertEqual(reader(weapon, reserve, mag).rounds(1), (reserve + mag, mag))

    def test_non_magazine_weapons_remain_unknown(self):
        for weapon in ['plasma_rifle', 'plasma_pistol', 'focus_rifle', 'spartan_laser',
                       'plasma_launcher', 'sword', 'flag', 'unknown']:
            with self.subTest(weapon=weapon):
                self.assertEqual(reader(weapon, 0, 0).rounds(1), (-1, -1))

    def test_missing_invalid_or_incomplete_reads_remain_unknown(self):
        live = reader('dmr', -1, 15)
        self.assertEqual(live.rounds(1), (-1, -1))
        live = reader('sniper', 0, 0)
        for data in [None, b'', b'\0' * 4]:
            live.g.read = lambda address, size, data=data: data
            self.assertEqual(live.rounds(1), (-1, -1))
        live.object = lambda handle: None
        self.assertEqual(live.rounds(1), (-1, -1))

    def test_other_games_do_not_read_reach_offsets(self):
        for dll in ['halo4.dll', 'groundhog.dll']:
            live = reader('sniper', 0, 0, dll)
            live.g.read = lambda *args: self.fail('Read a Reach ammo field in another game')
            self.assertEqual(live.rounds(1), (-1, -1))

    def test_empty_sniper_switches_to_loaded_dmr_across_difficulties(self):
        for tier in ['novice', 'average', 'strong', 'top', 'scaling']:
            with self.subTest(tier=tier):
                bot = bot_for(tier)
                me = PlayerState(0, 0, 'test', Vec(), weapon='sniper',
                                 weapons=['sniper', 'dmr'], ammo=[0, 42], mag=[0, 15])
                snap = Snapshot(10, [me])
                if tier == 'novice':
                    # Easy retains its intentional hesitation with an entirely dry gun.
                    bot.dry_since = 8.0
                self.assertEqual(bot.choose_weapon(10, me, 'roam', None, snap), 1)

    def test_combat_observation_enables_later_low_mag_reload(self):
        for tier in ['novice', 'average', 'strong', 'top', 'scaling']:
            with self.subTest(tier=tier):
                bot = bot_for(tier)
                me = PlayerState(0, 0, 'test', Vec(), weapon='dmr',
                                 weapons=['dmr', 'sniper'], ammo=[45, 8], mag=[15, 4])
                snap = Snapshot(1, [me])
                # Isolate the per-tick ammo observation from navigation/combat simulation.
                bot.plan = lambda *args: Action()
                bot.turn_cap = lambda *args: None
                bot.think(1, 1 / 30, snap, None, None, [])
                me.mag[0], me.ammo[0] = 3, 33
                act = Action()
                bot.reload_check(2, me, act)
                self.assertTrue(act.reload)
                bot.reload_at = 0
                me.ammo[0] = 3  # no reserves: reloading cannot help
                act = Action()
                bot.reload_check(3, me, act)
                self.assertFalse(act.reload)
                me.ammo[0] = 33
                bot.per.visible_enemies = lambda: [1]
                act = Action()
                bot.reload_check(4, me, act)
                self.assertFalse(act.reload)


if __name__ == '__main__':
    unittest.main(verbosity=2)
