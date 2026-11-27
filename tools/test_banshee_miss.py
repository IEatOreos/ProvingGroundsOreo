"""(custom, Nov 26) DMR shots at a Banshee's pilot go wide by tier and by the Banshee flipping (brain/banshee_miss.py).
The owner: "right now they all laser beam even the lower levels ... for the higher difficulty bots they can only miss
when the banshee is backflipping with a percentage.. You can make the rest miss with a base chance on flips. and Normal
and easy can just have a base chance to miss the banshee completely. (Dmr shots)"; "Use your numbers"."""
import math
import random
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import banshee_miss as BM  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to, eye  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

UPRIGHT, TIPPED = (0.0, 0.0, 1.0), (0.0, 0.8, -0.6)


def scene(tier, up=UPRIGHT, weapon="dmr", seed=1):
    bot = types.SimpleNamespace(p=make_profile(tier, "rusher", random.Random(3)), rng=random.Random(seed), notes=[],
                                goal=("fight", 1), shot_part=(1, True))
    me = PlayerState(0, 0, "b", Vec(), weapon=weapon, yaw=0.0)
    pilot = PlayerState(1, 1, "e", Vec(20, 0, 5), vehicle=77)
    snap = Snapshot(10.0, [me, pilot], vehicles=[dict(handle=77, kind="banshee", pos=(20.0, 0.0, 5.0), up=up)])
    return bot, me, snap


def rate(tier, up=UPRIGHT, n=2000):
    bot, me, snap = scene(tier, up)
    missed = 0
    for k in range(n):
        y, p = angles_to(eye(me), Vec(20, 0, 5))
        missed += BM.apply(bot, 10.0 + k * 0.4, me, snap, Action(fire=True, yaw=y, pitch=p))
        BM.apply(bot, 10.2 + k * 0.4, me, snap, Action(fire=False))        # (the release between presses)
    return missed / n


class BansheeMissTests(unittest.TestCase):
    def test_rates_by_tier(self):
        # (the owner, later: Heroic a 25% base, Legendary, Blind and Tactician 15%)
        for tier, (base, flip) in (("top", (0.15, 0.5)), ("blind", (0.15, 0.5)), ("tactician", (0.15, 0.5)),
                                   ("demon", (0.0, 0.25)), ("noble", (0.0, 0.25)), ("mythic", (0.0, 0.25)),
                                   ("strong", (0.25, 0.65)), ("average", (0.35, 0.7)), ("novice", (0.5, 1.0))):
            self.assertAlmostEqual(rate(tier), base, delta=0.04, msg=f"{tier} level")
            self.assertAlmostEqual(rate(tier, TIPPED), flip, delta=0.04, msg=f"{tier} flipping")

    def test_a_miss_goes_just_past_the_craft(self):
        bot, me, snap = scene("novice", TIPPED, seed=4)
        for k in range(40):
            a = Action(fire=True)
            if BM.apply(bot, 10.0 + k, me, snap, a):
                break
            BM.apply(bot, 10.5 + k, me, snap, Action())
        c = Vec(20, 0, 5)
        o = eye(me)
        d = Vec(math.cos(a.yaw) * math.cos(a.pitch), math.sin(a.yaw) * math.cos(a.pitch), math.sin(a.pitch))
        t = (c - o).x * d.x + (c - o).y * d.y + (c - o).z * d.z
        off = (c - (o + d * t)).length()
        self.assertAlmostEqual(off, BM.MISS_R, delta=0.05)          # (the round's nearest pass: 1.6 u off its middle)

    def test_only_a_dmr_press_and_only_a_banshee(self):
        bot, me, snap = scene("novice", TIPPED, weapon="assault_rifle")
        self.assertFalse(any(BM.apply(bot, 10.0 + k, me, snap, Action(fire=k % 2 == 0)) for k in range(200)))
        bot, me, snap = scene("novice", TIPPED)
        snap.vehicles[0]["kind"] = "warthog"
        self.assertFalse(any(BM.apply(bot, 10.0 + k, me, snap, Action(fire=k % 2 == 0)) for k in range(200)))
        bot, me, snap = scene("novice", TIPPED)
        held = [BM.apply(bot, 10.0 + k * 0.03, me, snap, Action(fire=True)) for k in range(50)]
        self.assertLessEqual(sum(held), 1)                         # (one roll a press, not a tick)

    def test_the_flip_is_held_a_moment(self):
        bot, me, snap = scene("top", TIPPED)
        BM.flipping(bot, 10.0, snap.vehicles[0])
        snap.vehicles[0]["up"] = UPRIGHT
        self.assertTrue(BM.flipping(bot, 10.0 + BM.FLIP_HOLD - 0.1, snap.vehicles[0]))
        self.assertFalse(BM.flipping(bot, 10.0 + BM.FLIP_HOLD + 0.1, snap.vehicles[0]))

    def test_scaling_keeps_its_own_aim(self):
        prof = make_profile("top", "rusher", random.Random(1))
        self.assertEqual(BM.tier_key(prof), "legendary")
        self.assertIsNone(BM.tier_key(types.SimpleNamespace(extra={"aim": 1.0}, tier="top")))


if __name__ == "__main__":
    unittest.main()
