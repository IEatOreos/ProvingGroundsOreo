"""(custom, Nov 26) The wall-ahead step-around (Bot.redirect) leaves a bot on the nav's own step when the nav's next
point is short of the "wall", wherever the bot looks: the owner's Boneyard report 20261126-200759, "they dont use the
stairs properly. Just roam the bottom". The way onto the sniper's stairs passes a block's corner 0.25-0.5 u off; bots
watching the enemy were stepped aside there, and 9 of 318 tries at the stairs' foot went up.

Run: python -m unittest discover -s tools -p test_stair_corner.py
"""
import math
import os
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.core import Action, PlayerState, Vec                    # noqa: E402

BONEYARD = "reach_70_boneyard"
FOOT = Vec(279.32, 112.19, -10.21)          # where the owner's bots shuffled (trace 20261126-200304, bot 8 at 75-83 s)
NEXT = Vec(279.72, 111.77, -10.15)          # the nav's next point there, onto the stairs
ROCKETS = Vec(267.059, 89.637, -4.966)      # its goal: the rockets, up top in the middle
ENEMY = Vec(274.0, 85.0, -10.1)             # the man it watched


@unittest.skipUnless(os.path.exists(ROOT / "maps" / BONEYARD / "heightmap.npz"), "no Boneyard level data")
class StairCorner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from brain.maps import get_map, terrain
        cls.m = get_map(BONEYARD)
        cls.T = terrain(cls.m)

    def walk(self, nav_step=True, wp=NEXT):
        from brain.bot import Bot
        from brain.profiles import make_profile
        b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), self.m, random.Random(5))
        b._terrain, b.feet_off, b.goal, b.route = self.T, 0.0, ("item", ROCKETS), None
        b.notes = []
        me = PlayerState(0, 0, "bot", FOOT)
        look = math.atan2(ENEMY.y - FOOT.y, ENEMY.x - FOOT.x)
        way = math.atan2(NEXT.y - FOOT.y, NEXT.x - FOOT.x)
        act = Action(yaw=look, pitch=0.0)
        act.forward, act.strafe = math.cos(way - look), math.sin(way - look)
        b.wp = wp
        b.nav_cmd = (act.forward, act.strafe) if nav_step else (0.0, 0.0)
        b.att = ("watch", "#5 radar", ENEMY.x, ENEMY.y)
        before = (act.forward, act.strafe)
        b.redirect(10.0, me, act)
        return b, before, (act.forward, act.strafe)

    def test_the_corner_reads_as_a_wall(self):
        way = math.atan2(NEXT.y - FOOT.y, NEXT.x - FOOT.x)
        from brain.bot import Bot
        self.assertLess(self.T.clearance(FOOT, way, 1.5), Bot.REDIRECT_D)   # (the case: without it, no test)

    def test_on_the_navs_step_it_walks_on(self):
        b, before, after = self.walk()
        self.assertEqual(after, before)
        self.assertNotIn("wall ahead: stepping around", b.notes)

    def test_off_the_navs_step_it_still_steps_around(self):
        b, before, after = self.walk(nav_step=False)
        self.assertNotEqual(after, before)
        self.assertIn("wall ahead: stepping around", b.notes)

    def test_a_next_point_past_the_wall_still_steps_around(self):
        b, before, after = self.walk(wp=Vec(278.2, 110.5, -9.1))
        self.assertNotEqual(after, before)
        self.assertIn("wall ahead: stepping around", b.notes)


if __name__ == "__main__":
    unittest.main()
