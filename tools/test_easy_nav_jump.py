"""Easy and Normal walk the jumps people take on their way (Bot.nav_jumps, EASY_NAV_JUMP), Easy's other jumps still
off. The owner, Nov 8: "make easy bots jump, they get stuck alot without jumping".

Run: python tools/test_easy_nav_jump.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod
from brain.bot import Bot
from brain.profiles import make_profile


def bot(tier):
    return Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "h4_test"}, random.Random(5))


class EasyNavJumpTests(unittest.TestCase):
    def tearDown(self):
        botmod.EASY_NAV_JUMP = True

    def test_every_tier_takes_the_jump_routes(self):
        for tier in ("novice", "average", "strong", "top", "demon"):
            with self.subTest(tier=tier):
                self.assertTrue(bot(tier).nav_jumps())

    def test_easy_keeps_no_jump_skill(self):
        self.assertEqual(bot("novice").p.jump, 0.0)        # (hops, fight jumps, jump shots: still none)

    def test_normal_under_the_line_by_jitter_still_takes_them(self):
        b = bot("average")
        self.assertLess(b.p.jump, 0.5)                    # (this seed: 0.497)
        self.assertTrue(b.nav_jumps())

    def test_off_easy_and_jittered_normal_walk_round_as_before(self):
        botmod.EASY_NAV_JUMP = False
        self.assertFalse(bot("novice").nav_jumps())
        self.assertFalse(bot("average").nav_jumps())
        self.assertTrue(bot("strong").nav_jumps())


if __name__ == "__main__":
    unittest.main()
