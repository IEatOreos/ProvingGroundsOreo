"""(custom, Nov 20) Noble: the testing difficulty. The owner: "Add a new difficulty only to our in game. It's our new
testing difficulty We will call it Noble. Make its base the same as a demon bot and then we will train it." A Demon
(tier "demon", extra None: every Demon rule, its aim and hands) under its own label "noble", in the BOTS panel, botcore
and botctl; not offered on the Service Record site."""
import random
import re
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from brain import odds, profiles  # noqa: E402
from brain.profiles import PERSONALITIES, make_profile  # noqa: E402
import botctl  # noqa: E402
import service_record  # noqa: E402


class ProfileTests(unittest.TestCase):
    def test_exactly_a_demon_under_its_own_name(self):
        for style in PERSONALITIES:
            for seed in range(10):
                n = make_profile("noble", style, random.Random(seed))
                d = make_profile("demon", style, random.Random(seed))
                self.assertEqual((n.tier, n.label, n.extra), ("demon", "noble", None))
                self.assertEqual(dict(asdict(n), label=None), dict(asdict(d), label=None), (style, seed))
                self.assertTrue(profiles.fixed_noble(n) and profiles.fixed_demon(n) and profiles.demon_rules(n))
                self.assertTrue(profiles.demon_eyes(n) and profiles.fixed_high(n) and profiles.protected_aim(n))
                self.assertFalse(profiles.fixed_noble(d))
                self.assertNotEqual(n.personality, "wheelman")            # (a Demon is never a Wheelman)

    def test_only_noble_is_noble(self):
        for tier in ("novice", "average", "strong", "top", "demon", "blind", "tactician", "mythic"):
            self.assertFalse(profiles.fixed_noble(make_profile(tier, "camper", random.Random(1))), tier)

    def test_odds_as_demon(self):
        n = make_profile("noble", "rusher", random.Random(2))
        d = make_profile("demon", "rusher", random.Random(2))
        self.assertEqual(odds.own_acc(n), odds.own_acc(d))
        self.assertEqual(odds.REACH_ACC["noble"], odds.REACH_ACC["demon"])


class InGameOnlyTests(unittest.TestCase):
    def test_panel_and_launch(self):
        panel = (ROOT / "native" / "bots_panel.cpp").read_text(encoding="utf-8", errors="replace")
        header = (ROOT / "native" / "bots_panel.h").read_text(encoding="utf-8", errors="replace")
        self.assertIn("#define HB_TIER_NOBLE 9", header)
        self.assertIn("tier == HB_TIER_NOBLE) && style == HB_STYLE_WHEELMAN", header)
        keys = re.findall(r'"([^"]*)"', re.search(r"TIER_KEY\[HB_TIERS\]\s*=\s*\{([^}]*)\}", panel).group(1))
        self.assertEqual(keys[9], "noble")
        self.assertEqual(tuple(keys), botctl.TIER_KEYS)
        self.assertEqual(botctl.DIFFICULTY_TIERS[10], "noble")
        self.assertIn("d == 10 ? HB_TIER_NOBLE", panel)
        self.assertIn("tier == HB_TIER_NOBLE ? 10u", panel)
        shown = re.search(r"DIFF_SHOWN\[DIFF_CHOICES\]\s*=\s*\{([^}]*)\}", panel).group(1)
        self.assertEqual([int(x) for x in shown.split(",")], [0, 1, 2, 8, 3, 7, 9, 6, 10, 4, 5])
        self.assertIn("#define DIFF_CHOICES 11", panel)
        self.assertEqual(panel.count('"Noble", "Mixed", "Scaling" };'), 2)   # Quick setup and the footer
        self.assertNotIn("<= 9 ?", panel)
        self.assertIn('segmented("tier_nb"', panel)                      # the inspector's Noble row

    def test_not_on_the_site(self):
        self.assertNotIn("noble", service_record.TIER_KEYS)
        app = (ROOT / "tools" / "service_record_site" / "app.js").read_text(encoding="utf-8", errors="replace")
        names = re.search(r"const TIER_NAMES = \{([^}]*)\}", app).group(1)
        self.assertIn("mythic", names)
        self.assertNotIn("noble", names)                                 # (the site's difficulty editor)


if __name__ == "__main__":
    unittest.main(verbosity=2)
