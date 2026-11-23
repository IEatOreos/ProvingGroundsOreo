"""(custom, Nov 23) Noble turns at most 400 deg/s, the owner's and his friend's own top speed on controller
(profiles.NOBLE_TURN), and a late update turns no more than TURN_STEP_MAX_S's worth (Bot.turn_cap). Live Asylum
20261123-000210: RiotRed whipped 60 degrees in 0.1 s to a radar dot; SpaghettiBandit's update 0.123 s late sent 84
degrees at once. Demon is unchanged."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B  # noqa: E402
from brain import profiles  # noqa: E402
from brain.core import Action, PlayerState, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


def turned(tier, dt, want=math.radians(120)):
    b = B.Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    me = PlayerState(0, 0, "b", Vec(), yaw=0.0)
    act = Action(yaw=want, pitch=0.0, forward=1.0)
    b.turn_cap(me, act, dt)
    return math.degrees(act.yaw)


class NobleTurnTests(unittest.TestCase):
    def test_400_degrees_a_second(self):
        self.assertAlmostEqual(math.degrees(make_profile("noble", "rusher", random.Random(1)).turn), 400.0)
        self.assertAlmostEqual(turned("noble", 1 / 30), 400 / 30, places=6)

    def test_a_late_update_does_not_jump(self):
        self.assertAlmostEqual(turned("noble", 0.123), 400 * B.TURN_STEP_MAX_S, places=6)    # (20 degrees, not 49)

    def test_demon_unchanged(self):
        self.assertAlmostEqual(math.degrees(make_profile("demon", "rusher", random.Random(1)).turn), 700.0)
        self.assertAlmostEqual(turned("demon", 0.123), 700 * 0.123, places=6)

    def test_slower_than_the_old_noble_never_faster_than_people(self):
        self.assertLess(profiles.NOBLE_TURN, profiles.TURN["demon"])
        for dt in (1 / 60, 1 / 30, 0.05, 0.1, 0.4):
            self.assertLessEqual(turned("noble", dt) / max(min(dt, B.TURN_STEP_MAX_S), 1e-3), 400 + 1e-6)


if __name__ == "__main__":
    unittest.main()
