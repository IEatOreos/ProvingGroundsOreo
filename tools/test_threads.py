"""(custom, Nov 23) The bots' thinking on several threads (brain/threads.py Pass) gives the very match one thread gives:
every man's place, facing, shield, health and life on every tick the same, Pass(4) against Pass(1) (upstream 0.3.0's rule
for its threads; the owner: "Yes, start the port"). The match: tools/real_sim.py on a small layout, 4 against 4, the
game's read delays off (they read the wall clock), from a clean start each time (the map, its terrain and every table
the bots share loaded afresh)."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]

MAP = "reach_cex_hangemhigh"
TICKS = 240
RED = "demon,mythic,top,strong,top,mythic,tactician,top"
BLUE = "demon,mythic,top,strong,blind,top,demon,strong"


def clean():
    """Everything a match leaves behind that the next one would read: the loaded map and terrain, the bots' shared
    tables, the learning stores (read again from disk)."""
    from brain import bot as botmod, lore, maps, noble, noble_habits, terrain as termod, threads
    maps._MAPS.clear()
    maps._TERRAIN.clear()
    for n in threads.NESTED + threads.FLAT:
        getattr(botmod, n).clear()
    for d in (lore._BOOKS, noble._BOOK, noble_habits._STORES):
        d.clear()
    termod._BORN.clear()


def play(workers):
    import real_sim as RS
    from brain.threads import Pass
    clean()
    m = RS.RealMatch(MAP, 3, BLUE, 50, 8, quiet=True, red_tiers=RED, delay=False, time_limit=600.0)
    m.think_pass = Pass(workers)
    out = []
    try:
        for _ in range(TICKS):
            m.tick()
            out.append(tuple((p, round(x.pos.x, 4), round(x.pos.y, 4), round(x.pos.z, 4), round(getattr(x, "yaw", 0.0), 4),
                              round(x.shield, 4), round(getattr(x, "body", 0.0), 4), x.alive)
                             for p, x in sorted(m.men.items())))
    finally:
        m.think_pass.close()
    return out


@unittest.skipUnless((ROOT / "maps" / MAP / "heightmap.npz").exists(),      # (a git-archive copy has the folder, not the map pack)
                     "no map data")
class SameMatch(unittest.TestCase):
    def test_four_threads_play_the_one_threads_match(self):
        one = play(1)
        four = play(4)
        moved = sum(1 for a, b in zip(one, one[1:]) if a != b)
        self.assertGreater(moved, TICKS // 2)                  # (a match that plays, not one standing still)
        for t, (a, b) in enumerate(zip(one, four)):
            self.assertEqual(a, b, f"tick {t}: the threaded pass played another match")


if __name__ == "__main__":
    unittest.main()
