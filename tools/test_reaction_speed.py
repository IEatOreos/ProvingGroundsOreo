"""(custom, Nov 12, owner) Easy, Normal and Heroic react faster ("when you shoot at a bot it just doesnt shoot back"),
their aim unchanged; the man hurting them is found without the off-to-the-side delay. Legendary, Demon, Blind,
Tactician and Scaling unchanged."""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain import profiles, scaling  # noqa: E402
from brain.bot import Perception  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402

AIM = ("track", "lead", "decide", "overshoot", "aim_err", "lag", "flick", "turn")


class ReactionSpeedTests(unittest.TestCase):
    def test_base_reaction(self):
        # (Nov 19, owner: "make them Faster but counter weight it with bad accuracy") Easy 135, Normal 125, Heroic
        # 115, Legendary 100 ms (were 220, 194, 172, 154); Tactician halfway between Heroic and Legendary
        want = {"novice": 0.135, "average": 0.125, "strong": 0.115, "top": 0.100, "demon": 0.154}
        for tier, v in want.items():
            self.assertAlmostEqual(profiles.TIERS[tier]["reaction"], v, msg=tier)
        order = [profiles.TIERS[t]["reaction"] for t in ("novice", "average", "strong", "top")]
        self.assertEqual(order, sorted(order, reverse=True))
        self.assertAlmostEqual(profiles.tactician_hands()["reaction"], 0.1075)
        self.assertAlmostEqual(profiles.blind_ranges()["reaction"][0], 0.154)     # Blind and Mythic unchanged
        self.assertAlmostEqual(profiles.mythic_hands()["reaction"], 0.077)

    def test_rougher_aim_pays_for_it(self):
        # (Nov 19) Easy, Normal, Heroic: aim error x1.8 / x1.6 / x1.5, overshoot 50 / 45 / 40%; Legendary's aim as it was
        for tier, err, over in (("novice", 0.009 * 1.8, 0.50), ("average", 0.009 * 1.6, 0.45),
                                ("strong", 0.0068 * 1.5, 0.40), ("top", 0.006, 0.30)):
            self.assertAlmostEqual(profiles.TIERS[tier]["aim_err"], err, msg=tier)
            self.assertAlmostEqual(profiles.TIERS[tier]["overshoot"], over, msg=tier)

    def test_aim_unchanged(self):
        h = profiles.HANDS
        self.assertEqual((h["aim_err"], h["lag"], h["track"], h["flick"], h["overshoot"], h["lead"]),
                         (0.009, 0.09, 0.10, 1.0, 0.30, 0.8))
        self.assertEqual(profiles.SHARP["strong"], dict(lag=0.058, flick=0.80, aim_err=0.0068, track=0.085))
        for style in profiles.PERSONALITIES:
            for tier in ("novice", "average", "strong"):
                a = profiles.make_profile(tier, style, random.Random(4))
                for k in AIM:
                    stock = {**profiles.TIERS[tier], "turn": None}.get(k)
                    if stock is not None:
                        self.assertTrue(0.9 * stock - 1e-12 <= getattr(a, k) <= 1.1 * stock + 1e-12, (tier, k))

    def test_arc_spot_tiers(self):
        for tier in ("novice", "average", "strong"):
            self.assertTrue(profiles.arc_spot(profiles.make_profile(tier, "rusher", random.Random(1))), tier)
        for tier in ("top", "demon", "blind", "tactician"):
            self.assertFalse(profiles.arc_spot(profiles.make_profile(tier, "rusher", random.Random(1))), tier)
        self.assertFalse(profiles.arc_spot(scaling.profile(0.5, "rusher", random.Random(1))))

    def _pending(self, tier, hurting):
        """Seconds until a man 45 degrees to the side (past Easy-Heroic's 35 degree centre, inside the 55 degree edge)
        is recognized, median over seeds."""
        out = []
        for seed in range(200):
            p = profiles.make_profile(tier, "rusher", random.Random(seed))
            per = Perception(p, random.Random(seed))
            me = PlayerState(0, 0, "bot", Vec(0, 0, 0))
            e = PlayerState(1, 1, "enemy", Vec(12, 12, 0), yaw=3.9)
            if hurting:
                per.attacker_id, per.attacker_t = 1, 0.0
            per.update(0.0, me, Snapshot(0.0, [me, e]), lambda a, b: True, [])
            out.append(per.pending[1])
        return sorted(out)[len(out) // 2]

    def test_attacker_found_without_side_delay(self):
        for tier in ("novice", "average", "strong"):
            plain, hurt = self._pending(tier, False), self._pending(tier, True)
            self.assertAlmostEqual(plain / hurt, 1.6, delta=0.05, msg=tier)
        top_plain, top_hurt = self._pending("top", False), self._pending("top", True)
        self.assertAlmostEqual(top_plain, top_hurt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
