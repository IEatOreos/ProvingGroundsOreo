"""Demon stays in cover until its shield is full once it is out of sight (custom, Nov 17: Bot.demon_recharge).

The owner: "They need to stay in cover and fully recharge their sheilds. currently they do break line of sight, but they
seem to re challenge when the shields start to recharge, Not at full. Or even 75%".

    python\\python.exe tools\\test_demon_recharge.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Belief, Bot, DEMON_FULL, DEMON_RECHARGE_SCORE, SHIELD_BACK
from brain.core import PlayerState, Snapshot, Vec
from brain.profiles import make_profile


class Wall:
    """Open floor with a wall along x = 2.5: what is on the other side of it is hidden."""
    cover_spots = []

    def path_ahead(s, a, b, n=80, **kw):
        d = b - a
        u = d.norm()
        return [a + u * (0.25 * (i + 1)) for i in range(min(n, int(d.flat() / 0.25)))]

    def los(s, a, b):
        return (a.x - 2.5) * (b.x - 2.5) > 0

    def walkable(s, p):
        return True


class RechargeTests(unittest.TestCase):
    def setup(self, tier="demon", shield=0.55, dot=Vec(-9, 0, 0), mode="slayer"):
        """A Demon at x = 4, behind the wall from a man last seen at x = -9 (out of sight, on its tracker), its shield
        refilling; it was last hurt at t = 47."""
        b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
        b._terrain = Wall()
        me = PlayerState(0, 0, "bot", Vec(4, 0, 0), weapon="dmr", weapons=["dmr", "assault_rifle"], ammo=[45, 160],
                         mag=[15, 32])
        me.shield, me.tracker = shield, True
        foe = PlayerState(1, 1, "foe", dot, weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        snap = Snapshot(50.0, [me, foe], mode=mode)
        b.per.hurt_at = 47.0
        b.per.beliefs[1] = Belief(dot, Vec(), 50.0, False, "radar")
        b.per.visible_enemies = lambda: []
        b.notes = []
        return b, me, foe, snap

    def decide(self, b, me, snap, t):
        snap.t = t
        b.per.beliefs[1].t = t                                # (the dot stays fresh)
        b.notes = []
        return b.decide(t, me, snap)

    def test_no_hunt_back_out_until_the_shield_is_full(self):
        b, me, foe, snap = self.setup()
        self.decide(b, me, snap, 50.0)                        # out of sight: the hold arms after 0.5 s
        chose = self.decide(b, me, snap, 50.6)
        self.assertEqual(chose[0], "retreat", b.last_scores)
        self.assertFalse([k for k in b.last_scores if k[0] in ("fight", "hunt")], b.last_scores)
        self.assertEqual(b.last_scores[chose], DEMON_RECHARGE_SCORE)
        self.assertEqual(chose[1], me.pos)                    # hidden where it stands: it stays there
        me.shield = 0.85
        self.assertEqual(self.decide(b, me, snap, 52.0)[0], "retreat")     # 0.85 is not full
        me.shield = DEMON_FULL
        self.assertEqual(self.decide(b, me, snap, 53.0)[0], "hunt")        # full: back to him

    def test_a_blink_out_of_sight_is_no_break(self):
        b, me, foe, snap = self.setup()
        self.decide(b, me, snap, 50.0)
        self.assertNotEqual(self.decide(b, me, snap, 50.3)[0], "retreat")  # under DEMON_RECHARGE_ARM out of sight
        self.assertIsNone(getattr(b, "recharge_hold", None))

    def test_a_man_who_comes_into_view_is_not_taken_on(self):
        b, me, foe, snap = self.setup(dot=Vec(4, -12, 0))     # 12 u off on its own side of the wall
        self.decide(b, me, snap, 50.0)
        self.decide(b, me, snap, 50.6)
        b.per.beliefs[1] = Belief(foe.pos, Vec(), 51.0, True, "eyes")
        b.per.last_seen[1] = 51.0
        b.per.visible_enemies = lambda: [1]
        chose = b.decide(51.0, me, Snapshot(51.0, [me, foe], mode="slayer"))
        self.assertEqual(chose[0], "retreat", b.last_scores)
        self.assertNotIn(("fight", 1), b.last_scores)
        self.assertFalse(Wall().los(foe.pos, chose[1]))       # behind the wall from him

    def test_a_man_on_it_is_still_fought(self):
        b, me, foe, snap = self.setup(dot=Vec(4, -4, 0))      # 4 u off: stand_ground's distance
        self.decide(b, me, snap, 50.0)
        self.decide(b, me, snap, 50.6)
        self.assertIn(self.decide(b, me, snap, 50.7)[0], ("fight", "hunt"))

    def test_shot_while_waiting_the_usual_rules_decide(self):
        b, me, foe, snap = self.setup()
        self.decide(b, me, snap, 50.0)
        self.decide(b, me, snap, 50.6)
        b.per.hurt_at = 50.5                                  # hit 0.2 s ago: it is not hidden
        self.decide(b, me, snap, 50.7)
        self.assertNotEqual(b.last_scores.get(("retreat", me.pos)), DEMON_RECHARGE_SCORE)

    def test_untouched_past_shield_back_counts_as_full(self):
        b, me, foe, snap = self.setup()
        b.per.hurt_at = 50.6 - SHIELD_BACK - 0.1              # (a 0 read: the shield is full by now)
        self.decide(b, me, snap, 50.0)
        self.assertNotEqual(self.decide(b, me, snap, 50.6)[0], "retreat")

    def test_other_tiers_and_modes_as_before(self):
        for tier, mode in (("top", "slayer"), ("demon", "race")):
            with self.subTest(tier=tier, mode=mode):
                b, me, foe, snap = self.setup(tier=tier, mode=mode)
                self.decide(b, me, snap, 50.0)
                self.decide(b, me, snap, 50.6)
                self.assertNotEqual(b.last_scores.get(("retreat", me.pos)), DEMON_RECHARGE_SCORE)


if __name__ == "__main__":
    unittest.main()
