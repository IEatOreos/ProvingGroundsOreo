"""Hurt, a Demon opens no new fight: cover first, until its shield is full (custom, Nov 18: Bot.demon_no_new_fight).

The owner, of the survival ideas: "the full shield bullet" ("Only start fights at full shield. A Demon that is hurt
doesn't open on a new man; it waits or repositions first").

    python\\python.exe tools\\test_demon_no_new_fight.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Belief, Bot, DEMON_FULL, DEMON_RECHARGE_SCORE  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


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


class Open(Wall):
    """No wall anywhere: nowhere out of his sight."""

    def los(s, a, b):
        return True


class NoNewFightTests(unittest.TestCase):
    def setup(self, tier="demon", shield=0.5, at=Vec(4, -12, 0), terrain=Wall, mode="slayer"):
        """A Demon at x = 4 (3 s after its last hit, its shield refilling) and a man in view at `at` on its own side of
        the wall, whom it has not fought."""
        b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
        b._terrain = terrain()
        me = PlayerState(0, 0, "bot", Vec(4, 0, 0), weapon="dmr", weapons=["dmr", "assault_rifle"], ammo=[45, 160],
                         mag=[15, 32])
        me.shield = shield
        foe = PlayerState(1, 1, "foe", at, weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        snap = Snapshot(50.0, [me, foe], mode=mode)
        b.per.hurt_at = 47.0
        b.per.beliefs[1] = Belief(at, Vec(), 50.0, True, "eyes")
        b.per.last_seen[1] = 50.0
        b.per.visible_enemies = lambda: [1]
        b.notes = []
        return b, me, foe, snap

    def test_hurt_it_takes_cover_from_a_new_man(self):
        b, me, foe, snap = self.setup()
        chose = b.decide(50.0, me, snap)
        self.assertEqual(chose[0], "retreat", b.last_scores)
        self.assertFalse([k for k in b.last_scores if k[0] in ("fight", "hunt")], b.last_scores)
        self.assertEqual(b.last_scores[chose], DEMON_RECHARGE_SCORE)
        self.assertFalse(Wall().los(foe.pos, chose[1]))       # out of his sight

    def test_full_it_fights(self):
        b, me, foe, snap = self.setup(shield=DEMON_FULL)
        self.assertEqual(b.decide(50.0, me, snap)[0], "fight")

    def test_the_man_it_fights_is_the_fights_own(self):
        b, me, foe, snap = self.setup()
        b.goal = ("fight", 1)
        self.assertNotEqual(b.decide(50.0, me, snap), ("retreat", b.fresh_cover or me.pos))
        self.assertIn(("fight", 1), b.last_scores)

    def test_the_man_who_hurt_it_is_the_fights_own(self):
        b, me, foe, snap = self.setup()
        b.per.attacker_id, b.per.attacker_t = 1, 47.0
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)

    def test_a_man_on_it_is_fought(self):
        b, me, foe, snap = self.setup(at=Vec(4, -4, 0))
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)

    def test_shot_just_now_the_usual_rules(self):
        b, me, foe, snap = self.setup()
        b.per.hurt_at = 49.7
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)

    def test_no_cover_in_reach_it_fights(self):
        b, me, foe, snap = self.setup(terrain=Open)
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)

    def test_then_the_recharge_hold_keeps_it_there(self):
        b, me, foe, snap = self.setup()
        spot = b.decide(50.0, me, snap)[1]
        me.pos = spot                                          # in cover: out of his sight
        b.per.beliefs[1].seen = False
        b.per.visible_enemies = lambda: []
        b.decide(50.2, me, snap)
        chose = b.decide(50.8, me, snap)
        self.assertEqual(chose[0], "retreat", b.last_scores)
        self.assertIsNotNone(getattr(b, "recharge_hold", None))

    def test_other_tiers_and_modes_as_before(self):
        for tier, mode in (("top", "slayer"), ("demon", "race")):
            with self.subTest(tier=tier, mode=mode):
                b, me, foe, snap = self.setup(tier=tier, mode=mode)
                b.decide(50.0, me, snap)
                self.assertIn(("fight", 1), b.last_scores)


if __name__ == "__main__":
    unittest.main()
