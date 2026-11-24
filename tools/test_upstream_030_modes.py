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


if __name__ == "__main__":
    unittest.main()
