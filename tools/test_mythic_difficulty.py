"""(custom, Nov 13) Mythic: between Legendary and Demon. The owner: "a hybrid difficulty between Legendary and Demon",
then: aim halfway and fixed, Demon's awareness only, named Mythic, 10 matchmaking points. Legendary's game sense and
rules (tier "top", label "mythic") and its protected head / turret precision; its aim, hands and decision time halfway
from Legendary's to Demon's; Demon's eyes (profiles.demon_eyes: the wide view, every radar dot noticed). Demon's other
rules stay Demon's."""
import math
import random
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from brain import profiles  # noqa: E402
from brain.bot import Perception  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import DEMON_AIM, PERSONALITIES, TIERS, TURN, make_profile  # noqa: E402
import botctl  # noqa: E402


class HandsTests(unittest.TestCase):
    def test_halfway_between_legendary_and_demon(self):
        mid = profiles.mythic_hands()
        # (Nov 19) Legendary's former 0.154 s reaction: Mythic unchanged when Legendary got quicker
        leg = dict(TIERS["top"], overshoot=0.0, turn=TURN["top"], reaction=profiles.LEGENDARY_BASE_REACTION)
        dem = dict(TIERS["demon"], **DEMON_AIM, reaction=0.0, decide=0.01, turn=TURN["demon"])
        self.assertEqual(set(mid), set(profiles.MYTHIC_HANDS) | {"turn"})
        for k, v in mid.items():
            if k != "turn":                                             # (Nov 23: every bot's 400, below)
                self.assertAlmostEqual(v, (leg[k] + dem[k]) / 2, msg=k)
        self.assertAlmostEqual(mid["reaction"], 0.077, places=6)        # Legendary 0.154 s, Demon 0
        self.assertAlmostEqual(mid["decide"], 0.055, places=6)          # 0.10 s, 0.01 s
        self.assertAlmostEqual(mid["aim_err"], 0.003, places=6)         # 0.006 rad, 0
        self.assertAlmostEqual(math.degrees(mid["turn"]), 400.0)        # (Nov 23, owner: every bot 400 deg/s; was 675)

    def test_every_bot_is_legendary_with_jittered_middle_hands(self):
        mid = profiles.mythic_hands()
        for style in PERSONALITIES:
            for seed in range(10):
                p = make_profile("mythic", style, random.Random(seed))
                top = make_profile("top", style, random.Random(seed))
                self.assertEqual((p.tier, p.label, p.extra), ("top", "mythic", None))
                self.assertTrue(profiles.fixed_high(p) and profiles.fixed_mythic(p) and profiles.high_ground(p))
                self.assertTrue(profiles.demon_eyes(p))
                self.assertTrue(profiles.protected_aim(p))               # Legendary's head / turret precision kept
                self.assertFalse(profiles.own_hands(p) or profiles.fixed_demon(p) or profiles.fixed_blind(p)
                                 or profiles.fixed_tactician(p))
                self.assertEqual(p.turn, mid["turn"])                     # (TURN is never jittered)
                for k in profiles.MYTHIC_HANDS:
                    v = mid[k]
                    self.assertTrue(0.9 * v - 1e-12 <= getattr(p, k) <= 1.1 * v + 1e-12, k)
                for k in ("memory", "radar", "teamwork", "jump", "strafe", "juke", "routes", "map_iq", "tactics", "aware",
                          "lead", "aggression", "objective"):
                    self.assertEqual(getattr(p, k), getattr(top, k), k)   # Legendary's own (same seed)

    def test_others_keep_their_eyes(self):
        for tier in ("novice", "average", "strong", "top", "blind", "tactician"):
            self.assertFalse(profiles.demon_eyes(make_profile(tier, "camper", random.Random(3))), tier)
        self.assertTrue(profiles.demon_eyes(make_profile("demon", "camper", random.Random(3))))


class EyesTests(unittest.TestCase):
    """As tools/test_demon_awareness.py, for Mythic."""

    def perception(self, tier, angle, distance=10):
        p = Perception(make_profile(tier, "rusher", random.Random(2)), random.Random(4))
        me = PlayerState(0, 0, "bot", Vec())
        a = math.radians(angle)
        enemy = PlayerState(1, 1, "enemy", Vec(distance * math.cos(a), distance * math.sin(a), 0))
        return p, me, enemy, Snapshot(10, [me, enemy])

    def test_demon_wide_view(self):
        for tier in ("mythic", "demon"):
            p, me, _, snap = self.perception(tier, 80)                  # past Legendary's 60 degrees
            p.update(10, me, snap, lambda *a: True, [])
            self.assertIn(1, p.pending, tier)
        p, me, _, snap = self.perception("top", 80)
        p.update(10, me, snap, lambda *a: True, [])
        self.assertNotIn(1, p.pending)
        p, me, _, snap = self.perception("mythic", 95)                   # Demon's edge, not past it
        p.update(10, me, snap, lambda *a: True, [])
        self.assertNotIn(1, p.pending)

    def test_every_radar_dot_noticed(self):
        hits = {"mythic": 0, "top": 0}
        for tier in hits:
            for seed in range(20):
                p, me, enemy, snap = self.perception(tier, 180)          # behind: radar only
                p.rng = random.Random(seed)
                me.tracker = True
                enemy.vel = Vec(1, 0, 0)
                p.update(10, me, snap, lambda *a: False, [])
                hits[tier] += 1 in p.beliefs and p.beliefs[1].source == "radar"
        self.assertEqual(hits["mythic"], 20)
        self.assertLess(hits["top"], 20)                                 # Legendary: radar x 0.15 a read


class NativeTests(unittest.TestCase):
    """The native menu's tables (read from the source: the DLL cannot run here)."""

    def test_menu_launch_and_points(self):
        panel = (ROOT / "native" / "bots_panel.cpp").read_text(encoding="utf-8", errors="replace")
        header = (ROOT / "native" / "bots_panel.h").read_text(encoding="utf-8", errors="replace")
        self.assertIn("#define HB_TIER_MYTHIC 8", header)
        keys = re.findall(r'"([^"]*)"', re.search(r"TIER_KEY\[HB_TIERS\]\s*=\s*\{([^}]*)\}", panel).group(1))
        self.assertEqual(keys[8], "mythic")
        self.assertEqual(tuple(keys), botctl.TIER_KEYS)
        self.assertEqual(botctl.DIFFICULTY_TIERS[9], "mythic")
        self.assertIn("d == 9 ? HB_TIER_MYTHIC", panel)
        # (Nov 23: the points became skill ratings, native/skill_rating.cpp: each difficulty's base, Mythic 1600)
        rating = (ROOT / "native" / "skill_rating.cpp").read_text(encoding="utf-8", errors="replace")
        rows = re.search(r"RANGE\[HB_TIERS\]\s*=\s*\{(.*?)\n\};", rating, re.S).group(1)
        bases = [int(b) for b in re.findall(r"\{\s*(\d+),", rows)]
        self.assertEqual(bases, [400, 600, 800, 1300, 1300, 1650, 1300, 950, 1600, 1700])
        overlay = (ROOT / "native" / "overlay.cpp").read_text(encoding="utf-8", errors="replace")
        names = re.findall(r'"([^"]*)"', re.search(r"DIFF_NAME\[HB_TIERS \+ 1\]\s*=\s*\{([^}]*)\}", overlay).group(1))
        self.assertEqual(names[8:], ["Mythic", "Noble", "Mixed"])

    def test_names_in_the_tools(self):
        import match_export  # noqa: F401
        import observer
        import player_stats
        self.assertEqual(observer.TIER_NAME["mythic"], "Mythic")
        self.assertEqual(player_stats.TIER_NAME["mythic"], "Mythic")


if __name__ == "__main__":
    unittest.main(verbosity=2)
