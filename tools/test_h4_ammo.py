"""Halo 4 gun rounds (brain/live.py LiveH4F.H4_AMMO: reserve +0x5AA, loaded +0x5AE), on fake memory; H2A stays unread.
The bot's dry switch and reload rules then see a Halo 4 gun's real state (Bot.choose_weapon, reload_check).

Run: python tools/test_h4_ammo.py
"""
import random
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot
from brain.core import PlayerState, Snapshot, Vec
from brain.live import LiveH4F
from brain.profiles import make_profile


class FakeMem:
    def __init__(s, dll):
        s.dll, s.mem = dll, {}

    def gun(s, addr, tag, reserve, loaded):
        s.mem[addr] = struct.pack("<I", tag)
        s.mem[addr + 0x5AA] = struct.pack("<h", reserve)
        s.mem[addr + 0x5AE] = struct.pack("<h", loaded)

    def read(s, addr, n):
        return s.mem.get(addr, b"\0" * n)[:n]


def reader(dll="halo4.dll"):
    L = LiveH4F.__new__(LiveH4F)
    L.g = FakeMem(dll)
    L.object = lambda h: h          # (handles are the fake addresses)
    return L


class H4AmmoTests(unittest.TestCase):
    def test_reads_reserve_and_loaded(self):
        L = reader()
        L.g.gun(0x1000, 7, 72, 36)                 # a spawn BR: 36 loaded, 72 more
        self.assertEqual(L.rounds(0x1000), (108, 36))
        L.g.gun(0x2000, 8, 0, 0)                   # the same kind emptied ...
        L.g.gun(0x2100, 8, 20, 10)                 # (a Boltshot of that kind seen loaded once)
        L.rounds(0x2100)
        self.assertEqual(L.rounds(0x2000), (0, 0))   # ... reads empty: a known dry gun

    def test_a_kind_never_loaded_is_unknown(self):
        L = reader()
        L.g.gun(0x3000, 9, 0, 0)                   # a sword: never a round
        self.assertEqual(L.rounds(0x3000), (-1, -1))

    def test_battery_guns_read_unknown_not_empty(self):
        """Nov 9: the owner's Beam Rifle read 0 + 0 and no bot ever saw it on the ground."""
        L = reader()
        names = {0x1000: "battle_rifle", 0x4000: "beam_rifle", 0x4100: "sword", 0x4200: "storm_rifle"}
        L.weapon_name = lambda h: names.get(h, "unknown")
        L.g.gun(0x1000, 7, 72, 36)                 # a BR: its kind has held rounds
        L.rounds(0x1000)
        for h in (0x4000, 0x4100, 0x4200):
            L.g.gun(h, 7, 0, 0)                    # (the same tag word as the BR: read by tag, it would be "empty")
            with self.subTest(gun=names[h]):
                self.assertEqual(L.rounds(h), (-1, -1))
        self.assertEqual(L.rounds(0x1000), (108, 36))

    def test_h2a_stays_unread(self):
        L = reader("groundhog.dll")
        L.g.gun(0x1000, 7, 72, 36)
        self.assertIsNone(L.AMMO_AT)
        self.assertEqual(L.rounds(0x1000), (-1, -1))

    def test_an_empty_rocket_launcher_is_switched_off(self):
        """The F9 of 20261108-141550: a Legendary pressed an empty launcher 9 times; read empty, it takes its rifle."""
        b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), {"name": "h4_test"}, random.Random(5))
        b.notes = []
        me = PlayerState(0, 0, "bot", Vec(), weapon="rockets", weapons=["battle_rifle", "rockets"], ammo=[108, 0],
                         mag=[36, 0])
        slot = b.choose_weapon(50.0, me, "fight", 1, Snapshot(50.0, [me], mode="slayer"))
        self.assertEqual(slot, 0)
        self.assertIn("switch: dry", b.notes)


if __name__ == "__main__":
    unittest.main()
