"""(custom, Nov 17) Banshee bombs as the owner's 21 Boneyard bomb kills had them (tools/owner_bomb_kills.py): Reach's
bomb from REACH_BOMB_R (6-18 u, Halo 4 keeps FUELROD_R); with the bomb ready, in over him at REACH_BOMB_OVER and then
the dive (Bot.air_pass bomb_dive); and a run kept on its man just out of sight while another is in it (Bot.run_hold)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.bot import AIR_BOMBER_DROP_R, AIR_RUN_HOLD_S, FUELROD_R, REACH_BOMB_OVER, REACH_BOMB_R, Belief  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec, angles_to  # noqa: E402
from test_demon_vehicles import Act, bot, LowRoofAir  # noqa: E402

BANSHEE = 77


def pilot(game, at):
    b = bot("demon", name=game)
    b._terrain = LowRoofAir()
    b.seat = "driver"
    b.can_cycle, b.veh_kind = True, "banshee"
    me = PlayerState(0, 0, "bot", at, vel=Vec(-6.0, 0, 0), yaw=math.pi, vehicle=BANSHEE, weapon="banshee")
    return b, me


def run(game, at, now=50.0, ready=True, foe_at=Vec(0, 0, 0)):
    """One air_pass tick, the nose on him (as drive aims it); returns (bot, act)."""
    b, me = pilot(game, at)
    b.air_run = ["in", 1, now - 2.0, math.pi]
    b.rod_next = now - 1.0 if ready else now + 5.0
    ya, pa = angles_to(me.pos + Vec(0, 0, 0.6), foe_at)
    act = Act(ya, pa)
    b.air_pass(now, me, 1, Belief(foe_at, Vec(), now, True, "eyes"), foe_at, act)
    return b, act


class RangeTests(unittest.TestCase):
    def test_reach_bombs_from_his_range(self):
        self.assertEqual(REACH_BOMB_R, (6.0, 18.0))
        self.assertIsNotNone(run("reach_test", Vec(6.0, 0, 6.5))[0].rod)       # 8.8 u: was never (10 u at least)
        self.assertIsNotNone(run("reach_test", Vec(8.0, 0, 7.0))[0].rod)       # 10.6 u
        # (custom, Nov 20) a Reach Banshee's bomb no farther than AIR_BOMBER_DROP_R (sim: 15-18 u flat killed 1 in 14,
        # the 2-3 kill bombs came from 8-9 u flat)
        self.assertEqual(AIR_BOMBER_DROP_R, 11.0)
        self.assertIsNone(getattr(run("reach_test", Vec(11.0, 0, 7.0))[0], "rod", None))   # 13.0 u
        self.assertIsNone(getattr(run("reach_test", Vec(14.0, 0, 7.0))[0], "rod", None))   # 15.7 u: was a bomb
        self.assertIsNone(getattr(run("reach_test", Vec(20.0, 0, 7.0))[0], "rod", None))   # 21.2 u: was a bomb

    def test_halo4_keeps_its_range(self):
        self.assertIsNone(getattr(run("h4_test", Vec(6.0, 0, 6.5))[0], "rod", None))
        self.assertEqual(FUELROD_R, (10.0, 31.0))


class DiveTests(unittest.TestCase):
    def test_low_with_the_bomb_ready_it_climbs_over_him(self):
        b, act = run("reach_test", Vec(14.0, 0, 3.0))
        self.assertGreater(act.pitch, 0.0)
        self.assertIn("air: bomb ready, climbing over him", b.notes)
        self.assertIsNone(getattr(b, "rod", None))                  # (no bomb while climbing: the nose is off him)

    def test_not_without_a_bomb_ready_or_in_halo4(self):
        self.assertLess(run("reach_test", Vec(14.0, 0, 3.0), ready=False)[1].pitch, 0.0)
        self.assertLess(run("h4_test", Vec(14.0, 0, 3.0))[1].pitch, 0.0)

    def test_over_him_it_dives_and_stays_diving(self):
        b, act = run("reach_test", Vec(14.0, 0, REACH_BOMB_OVER + 1.0))
        self.assertLess(act.pitch, -0.3)                            # the nose on him: the dive
        self.assertEqual(b.bomb_dive, 48.0)                         # (this run's start)
        me = PlayerState(0, 0, "bot", Vec(12.0, 0, 4.0), vel=Vec(-6.0, 0, 0), yaw=math.pi, vehicle=BANSHEE,
                         weapon="banshee")
        b.rod, b.rod_next = None, 49.0                              # (lower now, the bomb ready: still diving)
        ya, pa = angles_to(me.pos + Vec(0, 0, 0.6), Vec(0, 0, 0))
        act = Act(ya, pa)
        b.air_pass(50.1, me, 1, Belief(Vec(0, 0, 0), Vec(), 50.1, True, "eyes"), Vec(0, 0, 0), act)
        self.assertLess(act.pitch, -0.2)


class HoldTests(unittest.TestCase):
    def scene(self, unseen_for):
        b, me = pilot("reach_test", Vec(0, 0, 9.0))
        foe = PlayerState(1, 1, "foe", Vec(20.0, 0, 0))
        other = PlayerState(2, 1, "other", Vec(-10.0, 0, 0))
        b.air_run = ["in", 1, 45.0, 0.0]
        b.per.beliefs[1] = Belief(foe.pos, Vec(), 50.0 - unseen_for, False, "eyes")
        b.per.last_seen[1] = 50.0 - unseen_for
        return b, me, Snapshot(50.0, [me, foe, other])

    def test_kept_just_out_of_sight(self):
        b, me, snap = self.scene(1.0)
        self.assertEqual(b.run_hold(50.0, me, snap), 1)

    def test_let_go_after_the_hold(self):
        b, me, snap = self.scene(AIR_RUN_HOLD_S + 0.5)
        self.assertIsNone(b.run_hold(50.0, me, snap))


if __name__ == "__main__":
    unittest.main()
