"""Behavioral integration checks for customizations on installed upstream 0.2.2-s181."""
import math
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
from brain.loadouts import Palette


def bot_scene():
    bot = Bot(0, 0, make_profile('top', 'rusher', random.Random(5)), {'name': 'reach_test'}, random.Random(8))
    me = PlayerState(0, 0, 'bot', Vec(), weapon='dmr')
    bot.notes = []
    return bot, me


def ammo_reader(name, reserve, mag):
    live = LiveReach.__new__(LiveReach)
    live.object = lambda handle: 0x1000
    live.weapon_name = lambda handle: name
    data = {0x1000: struct.pack('<I', 17), 0x12C6: struct.pack('<hxxh', reserve, mag),
            0x12CA: struct.pack('<h', mag)}
    live.g = SimpleNamespace(dll='haloreach.dll', read=lambda addr, size: data[addr][:size])
    return live


class UpstreamMigrationTests(unittest.TestCase):
    def test_new_hazard_routes_reach_the_planner(self):
        bot, me = bot_scene()
        hazard = ((2.0, 0.0, 0.0, 3.0),)
        bot.kit.hazards = lambda *args: hazard
        snap = Snapshot(0, [me], deployed=[{'kind': 'trip_mine'}])
        received = []
        def nav(a, b, **kw):
            received.append(kw)
            return b
        def plan(now, dt, snap, los, nav, callouts, items):
            nav(me.pos, Vec(4, 0, 0), safe=True)
            return Action()
        bot.plan = plan
        bot.think(0, 1/30, snap, None, nav, [])
        self.assertEqual(received, [dict(hazards=hazard, safe=True)])

    def test_new_melee_guard_blocks_teammate_and_keeps_clear_enemy(self):
        bot, me = bot_scene()
        foe = PlayerState(1, 1, 'enemy', Vec(1, 0, 0))
        mate = PlayerState(2, 0, 'mate', Vec(0.5, 0, 0))
        bot.plan = lambda *args: Action(melee=True, yaw=0)
        self.assertFalse(bot.think(0, 1/30, Snapshot(0, [me, foe, mate]), None, None, []).melee)
        self.assertTrue(bot.think(1, 1/30, Snapshot(1, [me, foe]), None, None, []).melee)

    def test_live_ammo_populates_upstream_tag_caches(self):
        live = ammo_reader('sniper', 4, 3)
        self.assertEqual(live.rounds(1), (7, 3))
        self.assertEqual(live._rounds_seen[17], 4)
        self.assertEqual(live._mag_seen[17], 3)

    def test_first_seen_empty_named_sniper_is_known_empty(self):
        self.assertEqual(ammo_reader('sniper', 0, 0).rounds(1), (0, 0))

    def test_unknown_weapon_retains_upstream_magazine_learning(self):
        live = ammo_reader('unknown', 4, 3)
        self.assertEqual(live.rounds(1), (7, 3))
        self.assertEqual(live._mag_seen[17], 3)

    def test_live_animated_head_layout_and_invalid_layout(self):
        live = LiveReach.__new__(LiveReach)
        unit = bytearray(0x400)
        struct.pack_into('<HH', unit, 0x178, 82 * 52, 0xF1C)
        matrix = struct.pack('<13f', 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 4, 5, 0.65)
        live.g = SimpleNamespace(read=lambda address, size: matrix)
        point = live.spartan_head_position(0x1000, unit, (4, 5, 0))
        self.assertAlmostEqual(point[0], 4.01772663)
        self.assertAlmostEqual(point[1], 4.9936855733)
        struct.pack_into('<H', unit, 0x178, 0)
        self.assertIsNone(live.spartan_head_position(0x1000, unit, (4, 5, 0)))

    def test_new_species_palettes_remain_separate(self):
        kits = Palette()
        a, b = kits.side('spartan'), kits.side('elite')
        a.learn(1, ['dmr', 'assault_rifle'])
        b.learn(1, ['needle_rifle', 'plasma_pistol'])
        self.assertNotEqual(a.seen[1], b.seen[1])


if __name__ == '__main__':
    unittest.main()
