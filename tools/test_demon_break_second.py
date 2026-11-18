"""A second man with eyes on it: the Demon steps out of his sight (custom, Nov 18: Bot.demon_break_second).

The owner: "a good player knows how to shorten angles, or force an angle that allows them to make a 2v1 their
advantage", then "make that rule".

    python\\python.exe tools\\test_demon_break_second.py
"""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Belief, Bot, DEMON_BREAK_SCORE  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


class Pillar:
    """Open floor with one wall piece at x 2-6, y 2-3: a line through it is blocked."""
    cover_spots = []

    def path_ahead(s, a, b, n=80, **kw):
        d = b - a
        u = d.norm()
        return [a + u * (0.25 * (i + 1)) for i in range(min(n, int(d.flat() / 0.25)))]

    def los(s, a, b):
        for k in range(61):
            x, y = a.x + (b.x - a.x) * k / 60, a.y + (b.y - a.y) * k / 60
            if 2.0 <= x <= 6.0 and 2.0 <= y <= 3.0:
                return False
        return True

    def walkable(s, p):
        return not (2.0 <= p.x <= 6.0 and 2.0 <= p.y <= 3.0)


class Open(Pillar):
    def los(s, a, b):
        return True


def facing(e, at):
    e.yaw = math.atan2(at.y - e.pos.y, at.x - e.pos.x)


class BreakSecondTests(unittest.TestCase):
    def setup(self, tier="demon", terrain=Pillar, b_at=Vec(4, 12, 0), mode="slayer"):
        """A Demon at (7, 0) fighting A at (12, 0); B at (4, 12) north of the wall piece, both looking at it. From
        (6, 0) the piece stands between B and the Demon, and A still sees it."""
        b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
        b._terrain = terrain()
        me = PlayerState(0, 0, "bot", Vec(7, 0, 0), weapon="dmr", weapons=["dmr", "assault_rifle"], ammo=[45, 160],
                         mag=[15, 32])
        a = PlayerState(1, 1, "A", Vec(12, 0, 0), weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        c = PlayerState(2, 1, "B", b_at, weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        facing(a, me.pos)
        facing(c, me.pos)
        snap = Snapshot(50.0, [me, a, c], mode=mode)
        for e in (a, c):
            b.per.beliefs[e.id] = Belief(e.pos, Vec(), 50.0, True, "eyes")
            b.per.last_seen[e.id] = 50.0
        b.per.visible_enemies = lambda: [1, 2]
        b.goal = ("fight", 1)
        b.notes = []
        return b, me, a, c, snap

    def test_out_of_the_second_mans_sight_onto_the_first_mans_line(self):
        b, me, a, c, snap = self.setup()
        chose = b.decide(50.0, me, snap)
        self.assertEqual(chose[0], "retreat", b.last_scores)
        self.assertEqual(b.last_scores[chose], DEMON_BREAK_SCORE)
        self.assertFalse([k for k in b.last_scores if k[0] in ("fight", "hunt")], b.last_scores)
        self.assertFalse(Pillar().los(c.pos, chose[1]))       # B cannot see it there
        self.assertTrue(Pillar().los(a.pos, chose[1]))        # A still can: a 1v1
        self.assertLess((chose[1] - me.pos).flat(), 2.5)

    def test_the_spot_is_kept(self):
        b, me, a, c, snap = self.setup()
        first = b.decide(50.0, me, snap)
        self.assertEqual(b.decide(50.3, me, snap), first)

    def test_second_man_looking_away_it_fights(self):
        b, me, a, c, snap = self.setup()
        c.yaw += math.pi
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)

    def test_a_kill_about_to_land_goes_first(self):
        b, me, a, c, snap = self.setup()
        a.shield = 0.2
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)

    def test_a_man_on_it_the_fight_decides(self):
        b, me, a, c, snap = self.setup(b_at=Vec(7, 1.5, 0))
        b.decide(50.0, me, snap)
        self.assertNotEqual(b.last_scores.get(b.goal), DEMON_BREAK_SCORE)
        self.assertFalse([k for k, v in b.last_scores.items() if v == DEMON_BREAK_SCORE], b.last_scores)

    def test_nowhere_out_of_his_sight_it_fights(self):
        b, me, a, c, snap = self.setup(terrain=Open)
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)

    def test_other_tiers_and_modes_as_before(self):
        for tier, mode in (("top", "slayer"), ("demon", "race")):
            with self.subTest(tier=tier, mode=mode):
                b, me, a, c, snap = self.setup(tier=tier, mode=mode)
                b.decide(50.0, me, snap)
                self.assertFalse([k for k, v in b.last_scores.items() if v == DEMON_BREAK_SCORE], b.last_scores)


if __name__ == "__main__":
    unittest.main()
