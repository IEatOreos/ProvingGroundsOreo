"""(custom, Nov 10) Blind: Legendary's brain, its aim and hands drawn per bot between Legendary's base and nearly
Demon's; its own hands aim everywhere (no protected precision, no head snap). Also the Nov 10 turn speeds and Halo 4
Demon's melee reach."""
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from brain import profiles  # noqa: E402
from brain.profiles import PERSONALITIES, make_profile  # noqa: E402
import botctl  # noqa: E402


class BlindTests(unittest.TestCase):
    def test_turn_speeds(self):
        deg = {t: round(math.degrees(make_profile(t, "rusher", random.Random(0)).turn))
               for t in ("average", "strong", "top", "demon")}
        self.assertEqual(deg, dict(average=435, strong=650, top=650, demon=700))
        self.assertNotIn("turn", profiles.LEGENDARY_AIM)   # protected aim keeps Legendary's own turn speed

    def test_blind_is_legendary_with_drawn_hands(self):
        ranges = profiles.blind_ranges()
        self.assertAlmostEqual(ranges["reaction"][0], 0.154)
        self.assertAlmostEqual(ranges["reaction"][1], 0.154 * 0.15)
        self.assertAlmostEqual(math.degrees(ranges["turn"][1]), 650 + 0.85 * 50)
        seen = {k: set() for k in ranges}
        for style in PERSONALITIES:
            for seed in range(20):
                p = make_profile("blind", style, random.Random(seed))
                top = make_profile("top", style, random.Random(seed))
                self.assertEqual((p.tier, p.label, p.extra), ("top", "blind", None))
                self.assertTrue(profiles.fixed_high(p) and profiles.fixed_blind(p))
                self.assertFalse(profiles.protected_aim(p) or profiles.fixed_demon(p))
                self.assertIs(profiles.precision_profile(p), p)
                for k, (a, b) in ranges.items():
                    v = getattr(p, k)
                    self.assertGreaterEqual(v, min(a, b) - 1e-12, k)
                    self.assertLessEqual(v, max(a, b) + 1e-12, k)
                    seen[k].add(round(v, 6))
                # the rest is Legendary's own (same seed: same jittered game sense)
                for k in ("memory", "radar", "teamwork", "jump", "routes", "map_iq", "aggression", "lead"):
                    self.assertEqual(getattr(p, k), getattr(top, k), k)
        for k, vals in seen.items():
            if k != "overshoot":                     # (Legendary and Demon both 0)
                self.assertGreater(len(vals), 15, k)  # drawn per bot (20 seeds), not one fixed value

    def test_legendary_and_demon_unchanged_by_blind(self):
        top = make_profile("top", "camper", random.Random(3))
        self.assertTrue(profiles.protected_aim(top))
        self.assertIsNot(profiles.precision_profile(top), top)
        self.assertTrue(profiles.protected_aim(make_profile("demon", "camper", random.Random(3))))

    def test_roster_keeps_blind(self):
        self.assertIn("blind", botctl.TIER_KEYS)


class MeleeReachTests(unittest.TestCase):
    def test_h4_demon_melee_reach(self):
        from brain import bot
        b = bot.Bot.__new__(bot.Bot)
        b.p = make_profile("demon", "rusher", random.Random(1))
        b.game = "h4"
        self.assertEqual(b.melee_r(), bot.H4_DEMON_MELEE_R)
        b.game = "reach"
        self.assertEqual(b.melee_r(), bot.MELEE_R)
        b.game, b.p = "h4", make_profile("top", "rusher", random.Random(1))
        self.assertEqual(b.melee_r(), bot.MELEE_R)


if __name__ == "__main__":
    unittest.main(verbosity=2)
