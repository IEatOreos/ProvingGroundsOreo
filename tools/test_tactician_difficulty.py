"""(custom, Nov 10) Tactician: Legendary's game sense and decisions, its aim and hands halfway between Heroic's and
Legendary's (the owner: "make its stats between legendary and heroic"); its own hands aim everywhere (no protected
precision, no head snap)."""
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from brain import profiles  # noqa: E402
from brain.profiles import PERSONALITIES, TIERS, make_profile  # noqa: E402
import botctl  # noqa: E402


class TacticianTests(unittest.TestCase):
    def test_hands_halfway_between_heroic_and_legendary(self):
        mid = profiles.tactician_hands()
        her, leg = TIERS["strong"], dict(TIERS["top"], overshoot=0.0)
        # (Nov 12) reaction pinned where it was before Heroic's got quicker
        self.assertAlmostEqual(mid.pop("reaction"), 0.22 * (0.85 + 0.70) / 2)
        for k, v in mid.items():
            self.assertAlmostEqual(v, (her[k] + leg[k]) / 2, msg=k)
            self.assertTrue(min(her[k], leg[k]) <= v <= max(her[k], leg[k]), k)
            if her[k] != leg[k]:
                self.assertNotAlmostEqual(v, her[k], msg=k)
                self.assertNotAlmostEqual(v, leg[k], msg=k)

    def test_legendary_brain_own_hands(self):
        mid = profiles.tactician_hands()
        for style in PERSONALITIES:
            for seed in range(10):
                p = make_profile("tactician", style, random.Random(seed))
                top = make_profile("top", style, random.Random(seed))
                self.assertEqual((p.tier, p.label, p.extra), ("top", "tactician", None))
                self.assertTrue(profiles.fixed_high(p) and profiles.fixed_tactician(p) and profiles.own_hands(p))
                self.assertTrue(profiles.high_ground(p))
                self.assertFalse(profiles.protected_aim(p) or profiles.fixed_demon(p) or profiles.fixed_blind(p))
                self.assertIs(profiles.precision_profile(p), p)
                for k, v in mid.items():                       # jittered 0.9-1.1 like every tier
                    self.assertTrue(0.9 * v - 1e-12 <= getattr(p, k) <= 1.1 * v + 1e-12, k)
                for k in ("memory", "radar", "teamwork", "jump", "strafe", "juke", "routes", "map_iq", "tactics", "aware",
                          "decide", "lead", "turn", "aggression"):
                    self.assertEqual(getattr(p, k), getattr(top, k), k)   # Legendary's own (same seed)

    def test_others_unchanged(self):
        self.assertTrue(profiles.protected_aim(make_profile("top", "camper", random.Random(3))))
        self.assertTrue(profiles.protected_aim(make_profile("demon", "camper", random.Random(3))))
        self.assertFalse(profiles.protected_aim(make_profile("blind", "camper", random.Random(3))))

    def test_roster_and_launch_keys(self):
        self.assertIn("tactician", botctl.TIER_KEYS)
        self.assertEqual(botctl.DIFFICULTY_TIERS[8], "tactician")
        panel = (ROOT / "native" / "bots_panel.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn("static const uint32_t DIFF_SHOWN[9] = { 0, 1, 2, 8, 3, 7, 6, 4, 5 };", panel)
        self.assertIn("d == 8 ? HB_TIER_TACTICIAN", panel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
