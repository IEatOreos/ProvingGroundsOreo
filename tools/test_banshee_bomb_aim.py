"""(custom, Nov 17) A Banshee's bomb goes at his feet: the owner, "It should try to shoot it similarly like a rocket or
fuel rod. At their legs or ground below them?" Bot.drive: while the bomb is selected (Bot.rod, Bot.fuel_rod) the aim
is an explosive's (Aim.step SPLASH, his feet), its lead the bomb's own speed; the cannons keep his chest."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.bot import H2A_FEET, Belief, Order  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to  # noqa: E402
from test_demon_vehicles import LowRoofAir, bot  # noqa: E402


class Air(LowRoofAir):
    def fly_way(s, a, b, layer="high", ahead=6):
        return None

    def point_los(s, *a, **k):
        return True

    def vnav(s, a, b, **k):
        return b


def banshee(handle=77):
    return dict(handle=handle, kind="banshee", pos=(15.0, 0.0, 9.0), fwd=(-1.0, 0.0, 0.0), up=(0.0, 0.0, 1.0),
                occupied=True, team=0, riders=1, turrets=[], manned=[])


def aim_goal(game, bombing):
    b = bot("demon", name=game)
    b._terrain = Air()
    b.T = lambda: b._terrain
    b.air_terrain = lambda: b._terrain
    b.order = Order("mid", Vec(0, 0, 0))
    b.seat, b.seat_for, b.seat_since = "driver", 77, 0.0
    b.drive_to = Vec(0, 0, 0)
    b.can_cycle, b.veh_kind = True, "banshee"
    b.air_run = ["in", 1, 48.0, math.pi]
    b.rod = ["to", 50.0] if bombing else None
    b.rod_next = 99.0                                       # (no new bomb this tick)
    me = PlayerState(0, 0, "bot", Vec(15.0, 0.0, 9.0), vel=Vec(-6.0, 0.0, 0.0), yaw=math.pi, pitch=-0.5,
                     vehicle=77, weapon="banshee")
    foe = PlayerState(1, 1, "foe", Vec(0.0, 0.0, 0.0), vehicle=-1, weapon="assault_rifle", weapons=["assault_rifle"])
    snap = Snapshot(50.0, [me, foe], vehicles=[banshee()], mode="slayer")
    b.per.beliefs[1] = Belief(foe.pos, Vec(), 50.0, True, "eyes")
    b.per.recognized.add(1)
    b.per.last_seen[1] = b.per.clear_at[1] = 50.0
    b.drive(50.0, 1 / 30, me, snap, Action(), lambda a, c: c)
    return b.aim.goal, me, foe


class BombAimTests(unittest.TestCase):
    def check(self, game):
        cannon, me, foe = aim_goal(game, False)
        bomb, _, _ = aim_goal(game, True)
        if game.startswith("reach"):
            # (custom, Nov 25) Reach's pilot has no other shot: his feet before the bomb is selected too
            self.assertAlmostEqual(cannon[1], bomb[1], delta=0.004, msg=game)
        else:
            self.assertLess(bomb[1], cannon[1] - 0.008, game)        # lower: his feet, not his chest
        floor = foe.pos - Vec(0.0, 0.0, H2A_FEET if game.startswith("h4") else 0.0)    # (Halo 4: its place 0.38 up)
        self.assertAlmostEqual(bomb[1], angles_to(me.pos, floor)[1], delta=0.05, msg=game)
        self.assertAlmostEqual(bomb[0], cannon[0], delta=0.02, msg=game)   # (the same way: he stands still)

    def test_reach(self):
        self.check("reach_test")

    def test_halo4(self):
        self.check("h4_test")


if __name__ == "__main__":
    unittest.main()
