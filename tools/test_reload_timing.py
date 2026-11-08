"""Reloads out of a fight (Bot.reload_check, choose_weapon's empty pocket gun): topped off at RELOAD_TOP_OFF, in a
retreat too, never with a man in view or rounds coming in.

Run: python tools/test_reload_timing.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot, RELOAD_TOP_OFF, RELOAD_QUIET
from brain.core import Action, PlayerState, Snapshot, Vec
from brain.profiles import make_profile


def setup(tier="strong", mag=10, reserve=45):
    b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    b.notes = []
    b.mag_max = {"dmr": 15}
    me = PlayerState(0, 0, "bot", Vec(), weapon="dmr", weapons=["dmr", "magnum"], ammo=[mag + reserve, 40],
                     mag=[mag, 8])
    return b, me


class ReloadTimingTests(unittest.TestCase):
    def test_tops_off_a_part_spent_magazine(self):
        for tier in ("novice", "average", "strong", "top", "demon"):
            with self.subTest(tier=tier):
                b, me = setup(tier, mag=10)              # 10 of 15: 67%, under the 80% top-off (the old rule: 40%)
                act = Action()
                b.reload_check(50.0, me, act)
                self.assertTrue(act.reload)

    def test_a_nearly_full_one_waits(self):
        b, me = setup(mag=13)                            # 87%
        act = Action()
        b.reload_check(50.0, me, act)
        self.assertFalse(act.reload)
        self.assertGreater(13 / 15, RELOAD_TOP_OFF)

    def test_not_with_a_man_in_view_nor_while_being_hit(self):
        b, me = setup(mag=5)
        b.per.visible_enemies = lambda: [1]
        act = Action()
        b.reload_check(50.0, me, act)
        self.assertFalse(act.reload)
        b, me = setup(mag=5)
        b.per.hurt_at = 50.0 - RELOAD_QUIET / 2
        act = Action()
        b.reload_check(50.0, me, act)
        self.assertFalse(act.reload)
        b.per.hurt_at = 50.0 - RELOAD_QUIET - 0.1
        b.reload_check(50.0, me, act)
        self.assertTrue(act.reload)

    def test_no_reserve_no_reload(self):
        b, me = setup(mag=5, reserve=0)
        act = Action()
        b.reload_check(50.0, me, act)
        self.assertFalse(act.reload)

    def test_empty_pocket_gun_comes_out_in_a_retreat(self):
        b = Bot(0, 0, make_profile("strong", "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
        b.notes = []
        me = PlayerState(0, 0, "bot", Vec(), weapon="magnum", weapons=["dmr", "magnum"], ammo=[45, 40], mag=[0, 8])
        snap = Snapshot(50.0, [me], mode="slayer")
        slot = b.choose_weapon(50.0, me, "retreat", Vec(5, 0, 0), snap)
        self.assertEqual(slot, 0)
        self.assertIn("switch: reload the empty one", b.notes)


if __name__ == "__main__":
    unittest.main()
