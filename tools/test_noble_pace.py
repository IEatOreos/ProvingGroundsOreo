"""(custom, Nov 22) Noble's DMR pace within 7 u (Bot.fire_gap, NOBLE_DMR_FAST / NOBLE_KILL_PACE): the owner's own
measured fastest pace while the shield holds, his paced fifth shot once it is down. The owner: "I want the Noble
difficulty to shoot at that pace from within 7u ... shoot 4 as fast as possible and pace the last one for a headshot"."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B  # noqa: E402
from brain.core import PlayerState, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


def mk(tier="noble"):
    b = B.Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    b.game = "reach"
    return b


def man(shield=1.0, health=1.0):
    return PlayerState(1, 1, "e", Vec(5, 0, 0), shield=shield, health=health)


class NoblePaceTests(unittest.TestCase):
    def test_fastest_while_his_shield_holds(self):
        b = mk()
        for d in (1.0, 4.0, 7.0):
            self.assertEqual(b.fire_gap("dmr", d, man(shield=0.6)), B.NOBLE_DMR_FAST)
        self.assertAlmostEqual(B.NOBLE_DMR_FAST, 0.367)

    def test_the_kill_shot_paced(self):
        b = mk()
        self.assertEqual(b.fire_gap("dmr", 5.0, man(shield=0.0)), B.NOBLE_KILL_PACE)
        self.assertEqual(b.fire_gap("dmr", 5.0, man(shield=0.0, health=1.0), shieldless=True), B.NOBLE_DMR_FAST)
        self.assertEqual(b.fire_gap("dmr", 5.0, man(shield=0.0, health=0.4), shieldless=True), B.NOBLE_KILL_PACE)

    def test_past_7_u_and_other_tiers_and_guns_as_before(self):
        b = mk()
        self.assertNotEqual(b.fire_gap("dmr", 9.0, man()), B.NOBLE_DMR_FAST)
        self.assertNotEqual(b.fire_gap("magnum", 5.0, man()), B.NOBLE_DMR_FAST)
        for tier in ("demon", "top"):
            g = mk(tier).fire_gap("dmr", 5.0, man())
            self.assertNotIn(g, (B.NOBLE_DMR_FAST, B.NOBLE_KILL_PACE), tier)


if __name__ == "__main__":
    unittest.main()
