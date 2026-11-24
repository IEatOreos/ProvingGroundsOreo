"""(custom, Nov 23) A runner never bans the objective it is sent for: a stalled way reroutes round the spot it stalled at
(brain/bot.py headway, reroute, reroute_hazards, runner_objective). The owner: "They need to have the ability to reroute.
If the route they take fails they go the next route that makes it reachable. I think they shouldnt ban runners anymore";
live Renegade CTF 20261123-223329, three runners by their flag on its stand, the flag banned as unreachable."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B                              # noqa: E402
from brain.bot import Bot, Order                        # noqa: E402
from brain.core import PlayerState, Snapshot, Vec       # noqa: E402
from brain.profiles import make_profile                 # noqa: E402

STAND = Vec(-50.1, -92.2, 3.2)


class NoField:
    def field_from(s, *a, **k):
        raise RuntimeError("no nav here")            # (headway falls back to the straight line)


def scene(role="runner"):
    b = Bot(1, 0, make_profile("top", "rusher", random.Random(1)), {"name": "reach_test"}, random.Random(2))
    b._terrain = NoField()
    b.order = Order(role, STAND)
    me = PlayerState(1, 0, "b", Vec(-56.0, -94.0, 3.0))
    snap = Snapshot(100, [me], mode="ctf")
    b.wp = Vec(-53.0, -93.5, 3.0)          # (its next waypoint, 3 u on: the spot it stalled at)
    b.notes = []                           # (as a think starts it)
    return b, me, snap


def stall(b, me, snap, goal, t0=100.0, secs=7.0):
    # (Nov 24) a call every tick, as plan makes them: a gap over a second restarts the clock (upstream 0.3.0's
    # note #41, headway's way_seen)
    for i in range(int(secs * 10) + 1):
        b.headway(t0 + i * 0.1, me, goal, snap)


class Reroute(unittest.TestCase):
    def test_a_stalled_runner_reroutes_not_bans(self):
        b, me, snap = scene()
        goal = ("objective", STAND)
        stall(b, me, snap, goal)
        self.assertFalse(getattr(b, "goal_ban", {}))
        haz = b.reroute_hazards(108.0)
        self.assertEqual(haz, ((-53.0, -93.5, 3.0, B.REROUTE_R),))
        self.assertTrue(any("another way in" in n for n in b.notes))

    def test_spots_add_up_then_expire(self):
        b, me, snap = scene()
        goal = ("objective", STAND)
        for k in range(B.REROUTE_MAX + 1):
            b.wp = Vec(-53.0 + k, -93.5, 3.0)
            stall(b, me, snap, goal, t0=100.0 + 10 * k)
        self.assertEqual(len(b.reroute_hazards(140.0)), B.REROUTE_MAX)
        self.assertEqual(b.reroute_hazards(140.0 + B.REROUTE_S + 10), ())

    def test_a_new_objective_drops_them(self):
        b, me, snap = scene()
        stall(b, me, snap, ("objective", STAND))
        b.order = Order("runner", Vec(0, 0, 0))
        self.assertEqual(b.reroute_hazards(108.0), ())

    def test_others_still_give_up(self):
        b, me, snap = scene(role="mid")
        goal = ("objective", STAND)
        stall(b, me, snap, goal)
        self.assertTrue(b.goal_ban)
        self.assertEqual(b.reroute_hazards(108.0), ())
        b, me, snap = scene()
        stall(b, me, snap, ("item", Vec(-51.7, -90.8, 1.3)))             # (a runner's side trip: still dropped)
        self.assertTrue(b.goal_ban)

    def test_runner_objective(self):
        b, me, snap = scene()
        self.assertTrue(b.runner_objective(("objective", STAND)))
        self.assertFalse(b.runner_objective(("item", STAND)))
        b.order = Order("defender", STAND)
        self.assertFalse(b.runner_objective(("objective", STAND)))


if __name__ == "__main__":
    unittest.main()
