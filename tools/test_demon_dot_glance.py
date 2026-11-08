"""Demon glances at a close radar dot outside its view on its runs (custom, Nov 7)."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Belief, Bot                   # noqa: E402
from brain.core import PlayerState, Vec             # noqa: E402
from brain.profiles import make_profile             # noqa: E402


def scene(tier="demon", dot=Vec(-10.0, 0.0, 0.0), source="radar", age=0.1, seen=False):
    b = Bot(0, 0, make_profile(tier, "rusher", random.Random(2)), {"name": "h4_test"}, random.Random(4))
    b.notes = []
    me = PlayerState(0, 0, "bot", Vec(), yaw=0.0)          # facing +x, the dot behind at -x
    b.per.beliefs[1] = Belief(dot, Vec(), 10.0 - age, seen, source)
    return b, me


class DotGlanceTests(unittest.TestCase):
    def test_glances_at_a_close_dot_behind(self):
        b, me = scene()
        p = b.dot_glance(10.0, me)
        self.assertIsNotNone(p)
        self.assertAlmostEqual(p.x, -10.0)
        self.assertIn("radar: glance at #1", b.notes)
        self.assertEqual(b.att[0], "glance")
        self.assertEqual(b.aim.whip, 1.0)

    def test_the_glance_lasts_then_waits(self):
        b, me = scene()
        self.assertIsNotNone(b.dot_glance(10.0, me))
        self.assertIsNotNone(b.dot_glance(10.0 + b.DOT_GLANCE_S - 0.05, me))     # held, though the view turns
        b.per.beliefs[1].t = 11.0
        self.assertIsNone(b.dot_glance(10.0 + b.DOT_GLANCE_S + 0.1, me))         # over: not again yet
        b.per.beliefs[1].t = 12.05
        self.assertIsNotNone(b.dot_glance(10.0 + b.DOT_GLANCE_EVERY + 0.1, me))  # again after its wait

    def test_ends_when_its_eyes_have_him(self):
        b, me = scene()
        self.assertIsNotNone(b.dot_glance(10.0, me))
        b.per.beliefs[1] = Belief(Vec(-10.0, 0.0, 0.0), Vec(), 10.2, True, "eyes")
        self.assertIsNone(b.dot_glance(10.2, me))

    def test_not_for_a_dot_in_view_far_or_old(self):
        for dot, age in ((Vec(8.0, 6.0, 0.0), 0.1),      # 37 degrees off: in view
                         (Vec(-25.0, 0.0, 0.0), 0.1),    # past 20 u
                         (Vec(-10.0, 0.0, 0.0), 1.5)):   # stale
            b, me = scene(dot=dot, age=age)
            self.assertIsNone(b.dot_glance(10.0, me), (dot, age))

    def test_not_for_other_sources_tiers_carriers_or_riders(self):
        b, me = scene(source="callout")
        self.assertIsNone(b.dot_glance(10.0, me))
        b, me = scene(tier="top")
        self.assertIsNone(b.dot_glance(10.0, me))
        b, me = scene()
        me.has_flag = True
        self.assertIsNone(b.dot_glance(10.0, me))
        b, me = scene()
        me.vehicle = 7
        self.assertIsNone(b.dot_glance(10.0, me))

    def test_the_nearest_dot_first(self):
        b, me = scene(dot=Vec(-15.0, 0.0, 0.0))
        b.per.beliefs[2] = Belief(Vec(-6.0, 3.0, 0.0), Vec(), 9.9, False, "radar")
        p = b.dot_glance(10.0, me)
        self.assertAlmostEqual(p.x, -6.0)
        self.assertIn("radar: glance at #2", b.notes)


if __name__ == "__main__":
    unittest.main()
