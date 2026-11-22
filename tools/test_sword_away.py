"""(custom, Nov 22) The sword or hammer away between fights (choose_weapon, LUNGE_AWAY). The owner: "Change holding
sword out when enemy isnt close". The blade still comes out for a man close by."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B  # noqa: E402
from brain.bot import Belief  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


def mk(tier):
    b = B.Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    b.game, b.notes = "reach", []
    return b


def me_with(weapon):
    return PlayerState(0, 0, "b", Vec(), weapon=weapon, weapons=["dmr", "sword"], ammo=[45, 1], mag=[15, 1])


class SwordAwayTests(unittest.TestCase):
    def test_gun_out_with_nobody_near(self):
        for tier in ("novice", "strong", "top", "demon", "noble"):
            self.assertEqual(mk(tier).choose_weapon(10.0, me_with("sword"), "roam", None, None), 0, tier)
            self.assertEqual(mk(tier).choose_weapon(10.0, me_with("dmr"), "hunt", Vec(30, 0, 0), None), -1, tier)

    def test_blade_out_for_a_man_close_by(self):
        for tier in ("top", "demon"):
            b, me = mk(tier), me_with("dmr")
            foe = PlayerState(1, 1, "e", Vec(2.0, 0, 0), weapon="dmr")
            b.per.beliefs[1] = Belief(foe.pos, Vec(), 10.0, True, "eyes")
            self.assertEqual(b.choose_weapon(10.0, me, "fight", 1, Snapshot(10.0, [me, foe])), 1, tier)

    def test_a_sword_alone_stays_out(self):
        me = PlayerState(0, 0, "b", Vec(), weapon="sword", weapons=["dmr", "sword"], ammo=[0, 1], mag=[0, 1])
        self.assertEqual(mk("top").choose_weapon(10.0, me, "roam", None, None), -1)    # (the rifle is dry)


if __name__ == "__main__":
    unittest.main()
