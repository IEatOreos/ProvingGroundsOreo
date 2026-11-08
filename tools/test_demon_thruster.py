"""Demon uses no thruster in a gunfight outside Infection (custom, Nov 7): no charge in, no thrust to cover. Its grenade,
lunge, sniper-lane and flag thrusts, the other tiers and Infection keep theirs."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Belief, Bot                 # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.equipment import Energy                 # noqa: E402
from brain.profiles import make_profile            # noqa: E402

CHARGE = "dash in to close"


def scene(tier="demon", mode="slayer", shield=0.0, weapon="dmr", my_shield=1.0, hit=False, cover=None):
    bot = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "h4_test"}, random.Random(5))
    me = PlayerState(0, 0, "bot", Vec(), weapon=weapon, equipment="thruster", shield=my_shield)
    foe = PlayerState(1, 1, "enemy", Vec(5.0, 0, 0), weapon="battle_rifle", shield=shield, yaw=3.14)
    bot.goal = ("fight", 1)
    bot.hit_at = 10 if hit else -99
    bot.cover_from = lambda *args: cover
    bot.per.beliefs[1] = Belief(foe.pos, Vec(), 10, True, "eyes")
    bot.per.recognized.add(1)
    bot.kit.kind = "thruster"
    bot.kit.energy = Energy("h4", "thruster")
    snap = Snapshot(10, [me, foe])
    snap.mode = mode
    if mode == "infection":
        snap.infected = 1
    return bot, me, snap


def why(bot, me, snap):
    plan = bot.kit.plan(bot, 10, me, snap)
    return plan[4] if plan else None


class DemonThrusterChargeTests(unittest.TestCase):
    def test_no_charge_for_demon_in_every_mode_but_infection(self):
        for mode in ("slayer", "ctf", "oddball", "king", "assault", "invasion"):
            for setup in (dict(shield=0.0), dict(shield=1.0, weapon="shotgun")):
                with self.subTest(mode=mode, **setup):
                    b, me, snap = scene(mode=mode, **setup)
                    self.assertNotEqual(why(b, me, snap), CHARGE)

    def test_demon_still_charges_in_infection(self):
        b, me, snap = scene(mode="infection")
        self.assertEqual(why(b, me, snap), CHARGE)

    def test_other_tiers_keep_the_charge(self):
        for tier in ("average", "strong", "top"):
            with self.subTest(tier=tier):
                b, me, snap = scene(tier)
                self.assertEqual(why(b, me, snap), CHARGE)

    def test_no_thrust_to_cover_for_demon_but_in_infection(self):
        cracked = dict(my_shield=0.1, hit=True, cover=Vec(1.5, 2.0, 0), shield=1.0)
        for mode in ("slayer", "ctf", "king"):
            with self.subTest(mode=mode):
                b, me, snap = scene(mode=mode, **cracked)
                self.assertIsNone(why(b, me, snap))
        b, me, snap = scene(mode="infection", **cracked)
        self.assertEqual(why(b, me, snap), "thruster to cover")
        for tier in ("strong", "top"):
            b, me, snap = scene(tier, **cracked)
            self.assertEqual(why(b, me, snap), "thruster to cover")

    def test_demon_still_thrusts_out_of_a_grenade(self):
        b, me, snap = scene(shield=1.0)
        b.nade_at = (Vec(0.5, 0.0, 0.0), 99.0)
        self.assertEqual(why(b, me, snap), "dash out of the grenade")


if __name__ == "__main__":
    unittest.main()
