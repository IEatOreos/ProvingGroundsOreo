"""(custom, Nov 22) Noble shoots any part of a Spartan that shows (NOBLE_BODY, noble_body_point, Bot.fight). The owner:
"I want to make the Noble bots able to shoot at any part of the spartans model it sees. Legs, feet, head,Chest,
shoulders"."""
import math
import random
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B  # noqa: E402
from brain.bot import Belief  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


def man(pos, **kw):
    return PlayerState(1, 1, "e", pos, weapon="dmr", **kw)


class BodyPointTests(unittest.TestCase):
    def test_order_head_first(self):
        me, e = PlayerState(0, 0, "b", Vec()), man(Vec(10, 0, 0))
        got = B.noble_body_point(me, e, lambda o, p: True)
        self.assertEqual(got[0], "head")

    def test_what_shows_below_a_ledge_lip(self):
        me, e = PlayerState(0, 0, "b", Vec()), man(Vec(10, 0, 0))
        name, h, lat, p = B.noble_body_point(me, e, lambda o, p: p.z < 0.15)
        self.assertEqual(name, "knee")
        name, h, lat, p = B.noble_body_point(me, e, lambda o, p: p.z < 0.1)
        self.assertEqual(name, "leg")
        name, h, lat, p = B.noble_body_point(me, e, lambda o, p: p.z < 0.05)
        self.assertEqual(name, "foot")

    def test_top_and_sides_of_the_head(self):
        me, e = PlayerState(0, 0, "b", Vec()), man(Vec(10, 0, 0))
        name, h, lat, p = B.noble_body_point(me, e, lambda o, p: p.z > 0.66)        # (over a wall: his helmet's top)
        self.assertEqual(name, "top of the head")
        name, h, lat, p = B.noble_body_point(me, e, lambda o, p: p.y < -0.05 and p.z > 0.6)   # (round a corner)
        self.assertEqual(name, "side of the head")
        self.assertLess(p.y, -0.05)

    def test_the_whole_outline(self):
        names = {n for n, _, _ in B.NOBLE_BODY}
        for part in ("head", "top of the head", "side of the head", "chest", "shoulder", "arm", "hand", "hips",
                     "hip", "knee", "leg", "foot"):
            self.assertIn(part, names)

    def test_a_shoulder_past_a_corner(self):
        me, e = PlayerState(0, 0, "b", Vec()), man(Vec(10, 0, 0))
        name, h, lat, p = B.noble_body_point(me, e, lambda o, p: p.y > 0.1 and p.z > 0.4)   # (his left edge only)
        self.assertEqual(name, "shoulder")
        self.assertGreater(p.y, 0.1)

    def test_crouched_lower(self):
        me = PlayerState(0, 0, "b", Vec())
        e = man(Vec(10, 0, 0), crouching=True)
        name, h, lat, p = B.noble_body_point(me, e, lambda o, p: abs(p.z - 0.35) > 0.01 and p.z > 0.2)
        self.assertLess(h, 0.62)

    def test_nothing_shows(self):
        me, e = PlayerState(0, 0, "b", Vec()), man(Vec(10, 0, 0))
        self.assertIsNone(B.noble_body_point(me, e, lambda o, p: False))


class FightOnTheLegsTests(unittest.TestCase):
    def scene(self, tier="noble"):
        rng = random.Random(1)
        b = B.Bot(0, 0, make_profile(tier, "rusher", rng), {"name": "reach_test"}, rng)
        b.game, b.notes = "reach", []
        terrain = types.SimpleNamespace(point_los=lambda o, p, mode=None: p.z < 0.15, los=lambda a, c, *k: False)
        b.T = lambda: terrain
        me = PlayerState(0, 0, "b", Vec(), weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        e = man(Vec(10, 0, 0))
        b.per.beliefs[1] = Belief(e.pos, Vec(), 10.0, True, "eyes")
        b.per.target_parts = {1: (False, False)}
        b.per.last_seen[1] = 10.0
        b.line_clear = lambda now, me_, k, snap, head=None: False
        return b, me, e, Snapshot(10.0, [me, e])

    def test_noble_aims_and_fires_at_his_legs(self):
        b, me, e, sn = self.scene()
        a = Action()
        b.fight(10.0, 1 / 30, me, sn, 1, a, lambda x, y, **k: y)
        self.assertIsNotNone(b.noble_point)
        self.assertLess(b.aim.goal[1], math.atan2(0.15 - 0.62, 10.0) + 0.02)      # (the view down at his legs)
        a2 = Action(fire=True)
        b.fire_gate(10.0, me, a2, sn)
        self.assertTrue(a2.fire)

    def test_demon_unchanged(self):
        b, me, e, sn = self.scene("demon")
        a = Action()
        b.fight(10.0, 1 / 30, me, sn, 1, a, lambda x, y, **k: y)
        self.assertIsNone(getattr(b, "noble_point", None))


if __name__ == "__main__":
    unittest.main()
