"""Reach: the Needle Rifle takes the DMR's place, and gives way to a power gun (bot.NEEDLE_OVER_DMR, NEEDLE_SWAP_GAIN,
NEEDLE_YIELDS_TO). The owner, Nov 12: "I want bots to pick up the needler rifle over a dmr cause its better. but I dont
want them to pick it up over a power weapon".

Run: python tools/test_needle_over_dmr.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod
from brain.bot import Bot
from brain.core import PlayerState, Snapshot, Vec
from brain.profiles import make_profile

POWER = ("rockets", "sniper", "focus_rifle", "spartan_laser", "fuelrod", "plasma_launcher", "sword", "gravity_hammer",
         "shotgun")


def pickup(inv, ground, game_map="reach_test"):
    """What a Legendary carrying inv takes from guns lying 3, 4, ... u off (in that order), and the gun it drops."""
    b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), {"name": game_map}, random.Random(5))
    b.notes = []
    me = PlayerState(0, 0, "me", Vec(0, 0, 0), weapon=inv[0], weapons=list(inv), ammo=[50] * len(inv),
                     mag=[10] * len(inv))
    pts = [(n, Vec(3.0 + i, 0.0, 0.0)) for i, n in enumerate(ground)]
    q = b.upgrade_point(me, Snapshot(50.0, [me], mode="slayer", ground_weapons=pts))
    took = next((n for n, p in pts if q is not None and p == q), None)
    return took, (inv[b.drop_slot(list(inv), [50] * len(inv), took)] if took else None)


class NeedleOverDmrTests(unittest.TestCase):
    def test_the_needle_rifle_replaces_the_dmr(self):
        self.assertEqual(pickup(["dmr", "assault_rifle"], ["needle_rifle"]), ("needle_rifle", "dmr"))

    def test_no_swap_back_to_a_dmr(self):
        self.assertEqual(pickup(["needle_rifle", "assault_rifle"], ["dmr"]), (None, None))

    def test_a_power_gun_carried_is_kept(self):
        for p in POWER:
            with self.subTest(power=p):
                self.assertEqual(pickup([p, "dmr"], ["needle_rifle"]), ("needle_rifle", "dmr"))

    def test_a_power_gun_is_still_taken_from_needle_rifle_and_ar(self):
        for p in POWER:
            with self.subTest(power=p):
                self.assertEqual(pickup(["needle_rifle", "assault_rifle"], [p])[0], p)

    def test_a_power_gun_lying_there_wins_over_a_nearer_needle_rifle(self):
        for p in POWER:
            with self.subTest(power=p):
                self.assertEqual(pickup(["dmr", "assault_rifle"], ["needle_rifle", p])[0], p)

    def test_launcher_and_concussion_take_the_ars_place(self):
        """Nov 12: "I do want every weapon to pretty much outweigh the ar combo" (OVER_AR_GUNS)."""
        for game_map, rifle, guns in (("reach_test", "dmr", ("grenade_launcher", "concussion_rifle")),
                                      ("h4_test", "battle_rifle", ("concussion_rifle",))):
            for gun in guns:
                with self.subTest(game=game_map, gun=gun):
                    self.assertEqual(pickup([rifle, "assault_rifle"], [gun], game_map), (gun, "assault_rifle"))
                    self.assertEqual(pickup(["assault_rifle", "magnum"], [gun], game_map)[1], "assault_rifle")

    def test_a_power_gun_comes_before_them(self):
        for game_map, rifle, gun, powers in (
                ("reach_test", "dmr", "grenade_launcher", ("rockets", "sniper", "spartan_laser", "sword")),
                ("h4_test", "battle_rifle", "concussion_rifle", ("rockets", "sniper", "beam_rifle", "spartan_laser"))):
            for p in powers:
                with self.subTest(game=game_map, power=p):
                    self.assertEqual(pickup([gun, rifle], [p], game_map)[0], p)          # (carried: still taken)
                    self.assertEqual(pickup([rifle, "assault_rifle"], [gun, p], game_map)[0], p)
                    self.assertEqual(pickup([p, "assault_rifle"], [gun], game_map)[1], "assault_rifle")

    def test_halo4_power_guns_over_the_ar_for_every_tier_but_easy(self):
        """Nov 12: a bot on BR + AR took no sword, hammer or SAW (POWER_PICKUP_GAMES); Easy keeps its walk-over rule."""
        for gun in ("sword", "gravity_hammer", "lmg"):
            with self.subTest(gun=gun):
                self.assertEqual(pickup(["battle_rifle", "assault_rifle"], [gun], "h4_test"), (gun, "assault_rifle"))
                self.assertEqual(pickup(["battle_rifle", "boltshot"], [gun], "h4_test"), (gun, "boltshot"))

    def test_a_power_gun_carried_is_not_traded_for_another_unless_empty(self):
        self.assertEqual(pickup(["lmg", "battle_rifle"], ["sword"], "h4_test"), (None, None))
        b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), {"name": "h4_test"}, random.Random(5))
        me = PlayerState(0, 0, "me", Vec(0, 0, 0), weapon="lmg", weapons=["lmg", "battle_rifle"], ammo=[0, 50],
                         mag=[0, 10])
        q = Vec(3.0, 0.0, 0.0)
        self.assertEqual(b.upgrade_point(me, Snapshot(50.0, [me], mode="slayer", ground_weapons=[("sword", q)])), q)

    def test_the_better_power_gun_wins(self):
        self.assertEqual(pickup(["battle_rifle", "assault_rifle"], ["sword", "rockets"], "h4_test")[0], "rockets")

    def test_halo4_has_no_rule(self):
        self.assertNotIn("h4", botmod.NEEDLE_OVER_DMR)
        self.assertEqual(botmod.RANK_GAME["reach"]["needle_rifle"], botmod.RANK_GAME["reach"]["dmr"])


if __name__ == "__main__":
    unittest.main()
