"""(custom, Nov 23) Turn speeds. The owner: "Change all the bots speeds to 400. Demon and Noble to 450" (profiles.TURN,
NOBLE_TURN, blind_ranges, mythic_hands); he and his friend peak at 400-413 deg/s on controller. And a late update turns
no more than TURN_STEP_MAX_S's worth, every tier (Bot.turn_cap). Live Asylum 20261123-000210: RiotRed whipped 60
degrees in 0.1 s to a radar dot; SpaghettiBandit's update 0.123 s late sent 84 degrees at once. Scaling keeps its own
turn scale (brain/scaling.py)."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B  # noqa: E402
from brain import scaling  # noqa: E402
from brain.core import Action, PlayerState, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

SPEEDS = dict(novice=400, average=400, strong=400, top=400, blind=400, tactician=400, mythic=400, demon=450, noble=450)


def bot(tier):
    return B.Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))


def turned(tier, dt, want=math.radians(120)):
    me = PlayerState(0, 0, "b", Vec(), yaw=0.0)
    act = Action(yaw=want, pitch=0.0, forward=1.0)
    bot(tier).turn_cap(me, act, dt)
    return math.degrees(act.yaw)


class TurnSpeedTests(unittest.TestCase):
    def test_every_tier(self):
        for tier, deg in SPEEDS.items():
            for seed in range(5):
                p = make_profile(tier, "rusher", random.Random(seed))
                self.assertAlmostEqual(math.degrees(p.turn), deg, msg=tier)          # (never jittered)
            self.assertAlmostEqual(turned(tier, 1 / 30), deg / 30, places=6, msg=tier)

    def test_a_late_update_does_not_jump(self):
        for tier, deg in SPEEDS.items():
            self.assertAlmostEqual(turned(tier, 0.123), deg * B.TURN_STEP_MAX_S, places=6, msg=tier)   # (not deg x 0.123)
            for dt in (1 / 60, 1 / 30, 0.05, 0.1, 0.4):
                self.assertLessEqual(turned(tier, dt) / max(min(dt, B.TURN_STEP_MAX_S), 1e-3), deg + 1e-6)

    def test_scaling_keeps_its_own_scale(self):
        self.assertAlmostEqual(math.degrees(scaling.TURN), 435.0)
        self.assertAlmostEqual(math.degrees(scaling.TURN_MAX), 1300.0)


if __name__ == "__main__":
    unittest.main()
