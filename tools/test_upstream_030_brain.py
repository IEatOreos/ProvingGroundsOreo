"""(custom, Nov 24) Upstream 0.3.0's brain notes as ported into Project Noble (logs/upstream_0.3.0_answers.md): each
class is one note, its build stamp in the docstring."""
import random
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain import bot as botmod                                 # noqa: E402
from brain.bot import Bot                                       # noqa: E402
from brain.core import Action, PlayerState, Vec                 # noqa: E402
from brain.profiles import make_profile                        # noqa: E402


def make_bot(tier="strong", mapname="reach_t", style="rusher", bid=0, team=0):
    return Bot(bid, team, make_profile(tier, style, random.Random(1)), {"name": mapname, "items": []},
               random.Random(2))


class TakeTapTests(unittest.TestCase):
    """#6 (build 20261112-2117): Halo 2 takes the ball on a press of Use, so Bot.take taps it there."""

    def take(self, mapname, now):
        b = make_bot(mapname=mapname)
        b.now = now
        me = PlayerState(id=0, team=0, name="b", pos=Vec(0, 0, 0))
        act = Action()
        b.take(me, act, Vec(1, 0, 0))
        return act.action

    def test_halo_2_taps(self):
        beat = botmod.TAKE_TAP_S
        self.assertTrue(self.take("h2_t", 0.0))
        self.assertFalse(self.take("h2_t", beat * 0.75))
        self.assertTrue(self.take("h2_t", beat * 1.1))

    def test_every_other_game_holds(self):
        for m in ("reach_t", "h3_t", "h4_t", "h2a_t", "ce_map"):
            for now in (0.0, botmod.TAKE_TAP_S * 0.75):
                self.assertTrue(self.take(m, now), (m, now))

    def test_no_static_calls_left(self):
        src = Path(botmod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("Bot.take(", src)


class _NoField:
    hjumps = hroutes = None

    def field_from(self, *a):
        raise RuntimeError("no level data in this test")


class HeadwayTests(unittest.TestCase):
    """#41 (build 20261118-2355): a bot's weapon patience restarts each life (no headway call for over a second)."""

    def walk(self, times, tier="strong"):
        b = make_bot(tier=tier)
        b._terrain = _NoField()
        me = PlayerState(id=0, team=0, name="b", pos=Vec(0, 0, 0))
        goal = ("item", Vec(20, 0, 0))
        for t in times:
            b.headway(t, me, goal)
        return b, b._goal_key(goal)

    def test_six_seconds_with_no_headway_still_bans(self):
        b, key = self.walk([i * 0.1 for i in range(80)])
        self.assertIn(key, getattr(b, "goal_ban", {}))

    def test_a_gap_starts_the_clock_again(self):
        # 5 s walking, dead 5 s (no call), then 3 s more: 8 s of calls, never 6 s since the respawn
        times = [i * 0.1 for i in range(50)] + [10.0 + i * 0.1 for i in range(30)]
        b, key = self.walk(times)
        self.assertNotIn(key, getattr(b, "goal_ban", {}))

    def test_easy_keeps_its_shorter_patience(self):
        times = [i * 0.1 for i in range(int(botmod.EASY_HEADWAY_S * 10) + 6)]
        b, key = self.walk(times, tier="novice")
        self.assertIn(key, getattr(b, "goal_ban", {}))


if __name__ == "__main__":
    unittest.main()
