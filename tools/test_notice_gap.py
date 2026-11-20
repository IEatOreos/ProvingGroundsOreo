"""(custom, Nov 19) A man half in view (a head over a ledge, a chest flickering behind it) is still being noticed: the
notice timer (Perception.pending) runs on through gaps up to NOTICE_GAP s while he is in view; not through active camo's
misses nor once he leaves the view. The owner's F9 "Partyland doesnt shoot at me again when he can clearly see my head"
(Sword Base 20261119-211332, 143.6-145 s: a Demon 7-9 u from him, 5-14 degrees off its view, never noticed him)."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                     # noqa: E402
from brain.bot import Perception                    # noqa: E402
from brain.core import PlayerState, Snapshot, Vec   # noqa: E402
from brain.profiles import make_profile             # noqa: E402

DT = 1 / 30


def setup(tier="demon", angle=10.0, d=8.0):
    p = Perception(make_profile(tier, "rusher", random.Random(2)), random.Random(4))
    me = PlayerState(0, 0, "bot", Vec())
    a = math.radians(angle)
    him = PlayerState(1, 1, "him", Vec(d * math.cos(a), d * math.sin(a), 0))
    return p, me, him, Snapshot(10, [me, him])


def run(p, me, snap, pattern, t0=10.0):
    """pattern: per tick, whether the line to him is clear. The first tick he is noticed, else None."""
    for k, clear in enumerate(pattern):
        t = t0 + k * DT
        snap.time = t
        p.update(t, me, snap, (lambda *a, c=clear: c), [])
        if 1 in p.visible_enemies():
            return k
    return None


class NoticeGap(unittest.TestCase):
    def test_a_flickering_man_is_noticed(self):
        """Seen every other tick (his chest behind the ledge's edge): before, each unseen tick dropped the notice and a
        Demon never noticed him; now within a few ticks."""
        p, me, him, snap = setup()
        k = run(p, me, snap, [True, False] * 30)
        self.assertIsNotNone(k)
        self.assertLessEqual(k, 4)

    def test_a_long_gap_starts_it_again(self):
        """Out of sight longer than NOTICE_GAP: the notice starts again."""
        p, me, him, snap = setup("top")
        gap = int(botmod.NOTICE_GAP / DT) + 3
        run(p, me, snap, [True])
        self.assertIn(1, p.pending)
        run(p, me, snap, [False] * gap, t0=10.0 + DT)
        self.assertNotIn(1, p.pending)

    def test_short_gaps_keep_the_timer(self):
        """Legendary (a real reaction time): seen 4 ticks, hidden 3, over and over, he is noticed once the seen time
        passes the reaction, the deadline set by the first sight kept."""
        p, me, him, snap = setup("top")
        run(p, me, snap, [True])
        due = p.pending[1]
        k = run(p, me, snap, ([True] * 4 + [False] * 3) * 20, t0=10.0 + DT)
        self.assertIsNotNone(k)
        self.assertGreaterEqual(10.0 + DT + k * DT, due - 1e-9)

    def test_leaving_the_view_drops_it(self):
        p, me, him, snap = setup("top")
        run(p, me, snap, [True])
        self.assertIn(1, p.pending)
        me.yaw = math.pi                       # turned away: he is behind us
        run(p, me, snap, [False], t0=10.0 + DT)
        self.assertNotIn(1, p.pending)

    def test_active_camo_misses_drop_it(self):
        """Active camo's misses past 4 u are still only a shimmer: the notice starts again each time."""
        p, me, him, snap = setup("top")
        him.camo_until = 99.0
        p.rng = random.Random(0)
        p.rng.random = lambda: 0.95            # the first tick: the shimmer caught
        run(p, me, snap, [True])
        self.assertIn(1, p.pending)
        p.rng.random = lambda: 0.0             # then missed
        run(p, me, snap, [True], t0=10.0 + DT)
        self.assertNotIn(1, p.pending)


if __name__ == "__main__":
    unittest.main()
