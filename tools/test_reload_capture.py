"""(custom, Nov 20) tools/reload_capture.py's summary: the bit pressed before each reload stands out from one that is
pressed all the time (fire) and one never near a reload."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reload_capture as rc  # noqa: E402


def act(*bits):
    b = bytearray(rc.ACT_N)
    for off, bit in bits:
        w = struct.unpack_from("<Q", b, off)[0] | (1 << bit)
        struct.pack_into("<Q", b, off, w)
    return bytes(b).hex()


class SummaryTests(unittest.TestCase):
    def rows(self):
        out, t, mag = [], 0.0, 15
        for k in range(6):
            for j in range(60 * 6):                       # 6 s a round, 60 ticks a second
                t = k * 6 + j / 60.0
                on = []
                if j % 40 == 0 and j < 160:
                    on.append((0x08, 30))                 # fire: three rounds
                    mag -= 1 if mag > 0 else 0
                if 200 <= j < 206:
                    on.append((0x40, 7))                  # the reload tap
                if j == 320:
                    mag = 15                              # its magazine full again 2 s later
                if k == 5 and j in (100, 101):
                    on.append((0x10, 3))                  # something else, away from any reload
                out.append(dict(t=t, act=act(*on), w="dmr", mag=mag))
        return out

    def test_the_reload_bit_first(self):
        done, cands, n = rc.analyse(self.rows())
        self.assertEqual(len(done), 6)
        top = cands[0]
        self.assertEqual(top[0], "+0x40 bit 7")
        self.assertEqual((top[1], top[2]), (6, 0))
        self.assertAlmostEqual(top[3], 0.1, places=2)      # held 6 ticks
        other = next(c for c in cands if c[0] == "+0x10 bit 3")
        self.assertEqual(other[1:3], (0, 1))

    def test_a_switch_is_not_a_reload(self):
        ds = [dict(t=0.0, act=act(), w="dmr", mag=3), dict(t=0.1, act=act(), w="magnum", mag=8),
              dict(t=0.2, act=act(), w="dmr", mag=3)]
        self.assertEqual(rc.reloads(ds), [])


if __name__ == "__main__":
    unittest.main()
