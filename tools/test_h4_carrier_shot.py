"""Halo 4 CTF: the flag carrier shoots its magnum on the way home (custom, Nov 10, the owner: "Halo 4 is the only halo
where you have a weapon wielded while carrying flag, but they currently do not shoot the magnum at all when carrying
the flag in halo 4"). Live Adrift: bot carriers ran home 5,600 ticks with men listed and never fired."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import CARRIER_SHOOT_R, Belief, Bot             # noqa: E402
from brain.core import PlayerState, Snapshot, Vec              # noqa: E402
from brain.profiles import make_profile                        # noqa: E402

HOME = Vec(40, 0, 0)


def scene(game_map="h4_ca_warhouse", tier="strong", foe=Vec(10, 0, 0), seen=True):
    b = Bot(0, 0, make_profile(tier, "rusher", random.Random(2)), {"name": game_map}, random.Random(4))
    b.notes = []
    me = PlayerState(0, 0, "bot", Vec(), has_flag=True, weapon="unknown")
    b.per.beliefs[5] = Belief(foe, Vec(), 10.0, seen, "eyes")
    b.per.recognized.add(5)
    b.pick_target = lambda now, me, snap, ks: ks[0]
    return b, me, Snapshot(10.0, [me, PlayerState(5, 1, "foe", foe)], mode="ctf")


class CarrierShotTests(unittest.TestCase):
    def test_a_halo_4_carrier_shoots_a_man_in_view_on_its_way_home(self):
        for tier in ("novice", "average", "strong", "top", "demon"):
            b, me, snap = scene(tier=tier)
            self.assertEqual(b.game, "h4")
            self.assertEqual(b.carrier_shot(10.0, me, snap, "objective", HOME), 5, tier)

    def test_not_out_of_range_or_out_of_view(self):
        b, me, snap = scene(foe=Vec(CARRIER_SHOOT_R + 5, 0, 0))
        self.assertIsNone(b.carrier_shot(10.0, me, snap, "objective", HOME))
        b, me, snap = scene(seen=False)          # a radar dot or his emblem: no shot through the wall
        self.assertIsNone(b.carrier_shot(10.0, me, snap, "objective", HOME))

    def test_only_carrying_in_halo_4_ctf_on_foot(self):
        b, me, snap = scene(game_map="reach_70_boneyard")       # Reach: the flag is the carrier's only weapon
        self.assertIsNone(b.carrier_shot(10.0, me, snap, "objective", HOME))
        b, me, snap = scene()
        me.has_flag = False                                      # not carrying: its usual fights
        self.assertIsNone(b.carrier_shot(10.0, me, snap, "objective", HOME))
        b, me, snap = scene()
        snap.mode = "oddball"                                    # the ball: no gun with it
        self.assertIsNone(b.carrier_shot(10.0, me, snap, "objective", HOME))
        b, me, snap = scene()
        me.vehicle = 3
        self.assertIsNone(b.carrier_shot(10.0, me, snap, "objective", HOME))
        b, me, snap = scene()
        self.assertIsNone(b.carrier_shot(10.0, me, snap, "retreat", HOME))   # only on its run home


if __name__ == "__main__":
    unittest.main()
