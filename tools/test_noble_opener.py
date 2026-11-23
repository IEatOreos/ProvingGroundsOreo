"""(custom, Nov 23) Noble's opening shot goes just wide NOBLE_OPENER_MISS of the time, more on a big swing or a man
strafing (Bot.noble_opener_miss), its DMR and Needle Rifle; the first press ends the opener and a planned miss stays out
of the shot book (noble_fired). The owner: "add the ability for the bots to miss on their opening shot but keep it
realistic", "Is 1 in 4 a good start?", "First shot"."""
import math
import random
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


class Roll:
    def __init__(s, v):
        s.v = v

    def random(s):
        return s.v


def scene(yaw=0.0, foe_vel=Vec(), roll=0.0):
    b = B.Bot(0, 0, make_profile("noble", "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    b.notes, b.rng = [], Roll(roll)
    me = PlayerState(0, 0, "b", Vec(), weapon="dmr", weapons=["dmr"], yaw=yaw)
    foe = PlayerState(1, 1, "e", Vec(12, 0, 0), vel=foe_vel)
    return b, me, foe


class OpenerTests(unittest.TestCase):
    def test_a_miss_goes_just_wide_on_the_swing_side(self):
        b, me, foe = scene(yaw=-0.6, roll=0.0)           # (turning left onto him: +lat is his left as we see him)
        h, lat = b.noble_opener_miss(10.0, me, foe, 1, False)
        self.assertAlmostEqual(lat, B.NOBLE_MISS_BODY_LAT)
        self.assertGreater(h, 0.2)
        b, me, foe = scene(yaw=0.6, roll=0.0)
        _, lat = b.noble_opener_miss(10.0, me, foe, 1, True)
        self.assertAlmostEqual(lat, -B.NOBLE_MISS_HEAD_LAT)

    def test_chance_by_the_shot(self):
        # (the roll is compared with the chance: just under it misses, just over hits)
        easy = 0.25 * 0.6 * 0.8                            # dead ahead, he stands
        b, me, foe = scene(yaw=0.0, roll=easy - 1e-3)
        self.assertIsNotNone(b.noble_opener_miss(10.0, me, foe, 1, False))
        b, me, foe = scene(yaw=0.0, roll=easy + 1e-3)
        self.assertIsNone(b.noble_opener_miss(10.0, me, foe, 1, False))
        hard = 0.25 * (0.6 + 0.4 * 2.0) * 1.2               # 60 degrees off, he runs across
        b, me, foe = scene(yaw=math.radians(60), foe_vel=Vec(0, 2.5, 0), roll=hard - 1e-3)
        self.assertIsNotNone(b.noble_opener_miss(10.0, me, foe, 1, False))

    def test_only_the_opener(self):
        b, me, foe = scene(roll=0.0)
        b.noble_shot_at = {1: 9.0}                           # (shot at him 1 s ago: no opener)
        self.assertIsNone(b.noble_opener_miss(10.0, me, foe, 1, False))
        b.noble_shot_at = {1: 9.0 - B.NOBLE_OPENER_GAP - 0.1}
        self.assertIsNotNone(b.noble_opener_miss(10.0, me, foe, 1, False))
        self.assertIsNone(b.noble_opener_miss(10.0 + B.NOBLE_OPENER_HOLD + 0.1, me, foe, 1, False))   # (never fired)

    def test_the_first_press_ends_it_and_skips_the_shot_book(self):
        b, me, foe = scene(roll=0.0)
        b.noble_opener_miss(10.0, me, foe, 1, False)
        b.shot_part = (1, False)
        watched = []
        b.noble_watch = types.SimpleNamespace(pressed=lambda *a: watched.append(a))
        b.noble_fired(10.1, Snapshot(10.1, [me, foe]), Action(fire=True), False)
        self.assertIsNone(b.noble_opener)
        self.assertEqual(watched, [])
        self.assertEqual(b.noble_shot_at[1], 10.1)
        self.assertIsNone(b.noble_opener_miss(10.2, me, foe, 1, False))     # (the next shot is no opener)

    def test_only_noble_guns(self):
        self.assertEqual(B.NOBLE_MISS_GUNS, ("dmr", "needle_rifle"))
        self.assertAlmostEqual(B.NOBLE_OPENER_MISS, 0.25)


if __name__ == "__main__":
    unittest.main()
