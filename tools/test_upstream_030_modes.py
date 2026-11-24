"""(custom, Nov 24) Upstream 0.3.0's game-mode, Invasion, director and live-read notes as ported into Project Noble
(logs/upstream_0.3.0_answers.md): each class is one note, its build stamp in the docstring."""
import struct
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain import live as livemod                                   # noqa: E402
from brain.live import NONE, LiveReach                              # noqa: E402
import test_reach_stockpile_flags as stock                          # noqa: E402


class FreedMidRead(unittest.TestCase):
    """#39 (build 20261119-0039): an object freed while its table is read (its header read fails) is skipped, not the
    whole tick."""

    def live(self):
        live, _ = stock.reach([(stock.FLAG, stock.STANDS[0]), (stock.FLAG, stock.STANDS[2])])
        freed = stock.OBJ                                 # the first flag's header

        class Gone(stock.Memory):
            def read(s, addr, n):
                return None if addr == freed else super().read(addr, n)

        g = Gone()
        g.buf = live.g.buf
        live.g = g
        return live

    def test_loose_named_skips_it(self):
        got = self.live().loose_named("flag")
        self.assertEqual([round(p[0], 2) for p in got], [round(stock.STANDS[2][0], 2)])

    def test_objects_skips_it(self):
        live = self.live()
        live._names = {}
        live._was_held = lambda h: False
        live._learn = lambda tag, pos: None
        got = live.objects(types=(2,))
        self.assertEqual(len(got), 1)
        self.assertAlmostEqual(got[0][3][0], stock.STANDS[2][0], places=3)

    def test_halo_4_guard_is_there(self):
        import inspect
        self.assertIn("if head is None", inspect.getsource(livemod.LiveH4F.objects))


class WreckStays(unittest.TestCase):
    """#80 (build 20261120-1802): a vehicle read alive and then at 0 health or below stays a wreck for the match, in every
    game; the game's destroyed bit is still read; a new reader (a new match) remembers no wreck."""

    def reader(self, cls, healths, dead_bit=False):
        r = object.__new__(cls)
        seq = iter(healths)
        r.vehicle_left = lambda h: next(seq)
        r.object = lambda h: 0x100
        r.g = type("G", (), {"read": lambda s, a, n: bytes([4 if dead_bit else 0])})()
        return r

    def test_burning_warthog_stays_a_wreck(self):
        for cls in (livemod.LiveH2, LiveReach, livemod.Live):
            r = self.reader(cls, [1.0, -0.8, 0.25, 1.0])
            got = [r.vehicle_dead(7) for _ in range(4)]
            self.assertEqual(got, [False, True, True, True], cls.__name__)

    def test_zero_from_the_start_is_no_wreck(self):
        r = self.reader(LiveReach, [0.0, 0.0, 0.0])
        self.assertEqual([r.vehicle_dead(7) for _ in range(3)], [False, False, False])

    def test_destroyed_bit_still_read(self):
        r = self.reader(LiveReach, [1.0, 1.0], dead_bit=True)
        self.assertTrue(r.vehicle_dead(7))

    def test_a_new_match_remembers_no_wreck(self):
        r = self.reader(LiveReach, [1.0, 0.0])
        r.vehicle_dead(7)
        self.assertTrue(r.vehicle_dead(7))
        fresh = self.reader(LiveReach, [1.0])
        self.assertFalse(fresh.vehicle_dead(7))
        self.assertFalse(hasattr(LiveReach, "_veh_wrecked"))     # per reader, never on the class


class FirefightDeadCovenant(unittest.TestCase):
    """#12 (build 20261114-0323, GitHub #29): a Covenant unit with the game's destroyed bit set is dead, whatever its
    damage field reads; bots kept shooting dead Grunts."""

    def units(self, bit=True):
        r = object.__new__(LiveReach)
        r.g = stock.Memory()
        rows = [(0.4, 0), (0.4, 4), (0.0, 0)]            # (body damage, damage flags): alive, dead by the bit, alive
        for k, (dmg, flags) in enumerate(rows):
            e, o = stock.ENTS + k * 0x18, stock.OBJ + k * stock.OBJ_SIZE
            struct.pack_into("<H", r.g.buf, e, 0x100 + k)
            r.g.buf[e + 4] = 0                            # a biped
            struct.pack_into("<Q", r.g.buf, e + 0x10, o)
            struct.pack_into("<2f", r.g.buf, o + 0x124, 0.0, dmg)
            struct.pack_into("<I", r.g.buf, o + 0x14, NONE)
            struct.pack_into("<I", r.g.buf, o + 0x1D0, NONE)
            r.g.buf[o + LiveReach.UNIT_TEAM] = 3          # Covenant
            r.g.buf[o + LiveReach.DEAD_AT] = flags
        r._array = lambda off: (stock.ENTS, len(rows), 0x18)
        r._vitals = lambda h, sd, bd, player=False: (1.0 - sd, 1.0 - bd)
        old = livemod.AI_DEAD_BIT
        livemod.AI_DEAD_BIT = bit
        try:
            return [d["index"] for d in r.ai_units([])]
        finally:
            livemod.AI_DEAD_BIT = old

    def test_dead_by_the_bit_is_left_out(self):
        self.assertEqual(self.units(), [1000, 1002])

    def test_switch_off_reads_the_damage_alone(self):
        self.assertEqual(self.units(bit=False), [1000, 1001, 1002])


class CEFreeForAll(unittest.TestCase):
    """#14 (build 20261114-0323): in a CE free for all every player is his own side (team = his slot), even with the
    lobby's red and blue left on; a team game keeps the lobby's teams."""

    def players(self, teams):
        r = object.__new__(livemod.Live)
        r.g = stock.Memory(0x10000)
        r.g.base = 0
        base, size = 0x1000, 0x200
        struct.pack_into("<i", r.g.buf, 0x8000 + 0x34, 1 if teams else 0)
        r.VARIANT = 0x8000
        for i, team in enumerate((0, 1, 1, 0)):
            p = base + i * size
            struct.pack_into("<H", r.g.buf, p, 0x100 + i)
            struct.pack_into("<I", r.g.buf, p + 0x64, NONE)
            struct.pack_into("<i", r.g.buf, p + 0x4C, team)
        r._array = lambda at: (base, 4, size)
        r.object = lambda h: 0
        r.tracker = lambda p: []
        return [d["team"] for d in r.players()]

    def test_free_for_all_every_player_his_own_side(self):
        self.assertEqual(self.players(teams=False), [0, 1, 2, 3])

    def test_team_game_keeps_the_lobby_teams(self):
        self.assertEqual(self.players(teams=True), [0, 1, 1, 0])


if __name__ == "__main__":
    unittest.main()
