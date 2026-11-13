"""Banshee attack runs (custom, Nov 13: "We have to make the banshee work. They're almost near useless when a bot is
driving them"): the run's man is kept out of sight (Bot.air_keep) and held as the target in sight (Bot.run_target)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.bot import AIR_KEEP_R, AIR_KEEP_S, Belief  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from test_demon_vehicles import pilot  # noqa: E402


def keep_scene(age=2.0, alive=True, far=20.0):
    b, me = pilot(at=Vec(0, 0, 9.0))
    foe = PlayerState(1, 1, "foe", Vec(far, 0, 0), alive=alive)
    b.air_run = ["out", 1, 10.0, 0.0]
    b.per.beliefs[1] = Belief(foe.pos, Vec(), 50.0 - age, False, "eyes")
    return b, me, Snapshot(50.0, [me, foe])


class KeepTests(unittest.TestCase):
    def test_the_runs_man_is_kept_out_of_sight(self):
        b, me, snap = keep_scene(age=2.0)
        self.assertEqual(b.air_keep(50.0, me, snap), 1)

    def test_not_after_air_keep_s(self):
        b, me, snap = keep_scene(age=AIR_KEEP_S + 0.5)
        self.assertIsNone(b.air_keep(50.0, me, snap))

    def test_not_dead_or_far(self):
        b, me, snap = keep_scene(alive=False)
        self.assertIsNone(b.air_keep(50.0, me, snap))
        b, me, snap = keep_scene(far=AIR_KEEP_R + 5.0)
        self.assertIsNone(b.air_keep(50.0, me, snap))

    def test_no_run_no_keep(self):
        b, me, snap = keep_scene()
        b.air_run = None
        self.assertIsNone(b.air_keep(50.0, me, snap))

    def test_run_target_held_while_in_sight(self):
        b, me, snap = keep_scene()
        self.assertEqual(b.run_target([3, 1, 5]), 1)
        self.assertIsNone(b.run_target([3, 5]))


class BombTests(unittest.TestCase):
    """(Nov 13: "use the bomb a lot more") a bomb about every run, with the nose within BOMB_GUN_R of him."""

    def run_at(self, off_yaw, now=50.0):
        import math
        from test_demon_vehicles import Act
        b, me = pilot(at=Vec(15.0, 0, 9.0), yaw=math.pi)
        b.can_cycle, b.veh_kind = True, "banshee"
        foe = PlayerState(1, 1, "foe", Vec(0, 0, 0))
        b.air_run = ["in", 1, now - 2.0, math.pi]
        ya, pa = math.pi, math.atan2(0.6 - 9.0, 15.0)           # (at his middle)
        act = Act(ya + off_yaw, pa)
        b.air_pass(now, me, 1, Belief(foe.pos, Vec(), now, True, "eyes"), foe.pos, act)
        return b

    def test_the_bomb_goes_with_the_nose_2_u_off_him(self):
        b = self.run_at(math.atan2(2.0, 17.4))                   # outside the cannons' 1.5 u, inside the bomb's 3 u
        self.assertIsNotNone(b.rod)

    def test_not_with_the_nose_4_u_off(self):
        self.assertIsNone(getattr(self.run_at(math.atan2(4.0, 17.4)), "rod", None))

    def test_about_one_a_run(self):
        from brain.bot import FUELROD_EVERY
        self.assertLessEqual(FUELROD_EVERY, 6.0)


if __name__ == "__main__":
    unittest.main()
