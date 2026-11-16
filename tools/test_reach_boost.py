"""(custom, Nov 15) Reach's vehicle boost, from the owner's Boneyard capture (tools/boost_capture.py with
tools/reach_shot_capture.py): the decoded "fire2" entry puts the controller's boost bits and trigger float on a bot's
action; a Ghost's and a Banshee's travel boost is held the whole open leg; a Reach pilot boosts in from past gun range
and out of a run and pulls the throttle back to turn tight; the Reach Ghost's lead uses its bolts' own 29.3 u/s."""
import json
import math
import random
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.bot import AIR_TIGHT_THROTTLE, CANNON_R, REACH_GHOST_BOLT, Aim, Belief  # noqa: E402
from brain.core import PlayerState, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402
from test_demon_vehicles import Act, LowRoofAir, bot  # noqa: E402


def apply_table(act, rows, held):
    """shared.h hb_apply_buttons for one button's rows: its mask bits cleared, then set while held."""
    for r in rows:
        w = struct.unpack_from("<Q", act, r["off"])[0] & ~r["mask"]
        struct.pack_into("<Q", act, r["off"], w | (r["mask"] if held else 0))


class TableTests(unittest.TestCase):
    def setUp(self):
        with open(ROOT / "maps" / "_inputs" / "reach.json", encoding="utf-8") as f:
            self.rows = json.load(f)["fire2"]

    def test_held_it_is_the_controllers_boost(self):
        act = bytearray(0xC0)
        struct.pack_into("<I", act, 0x08, 0x2)                 # (a jump flag botcore wrote is kept)
        apply_table(act, self.rows, True)
        self.assertEqual(struct.unpack_from("<Q", act, 0x08)[0], 0x880048000 | 0x2)
        self.assertEqual(struct.unpack_from("<f", act, 0x24)[0], 1.0)

    def test_let_go_the_persons_own_trigger_is_cleared(self):
        act = bytearray(0xC0)
        struct.pack_into("<Qff", act, 0x08, 0x880048000, 0.0, 0.0)
        struct.pack_into("<ff", act, 0x20, 0.5, 1.0)           # (the template: his strafe, his boost trigger)
        apply_table(act, self.rows, False)
        self.assertEqual(struct.unpack_from("<Q", act, 0x08)[0], 0)
        self.assertLess(abs(struct.unpack_from("<f", act, 0x24)[0]), 1e-30)
        self.assertEqual(struct.unpack_from("<f", act, 0x20)[0], 0.5)   # (the low half, the strafe, untouched)


class Ground:
    def height_over(s, x, y, z):
        return 0.0

    def fly_clear(s, *a, **k):
        return 99.0


def driver(name):
    b = bot("strong", name=name)
    b.seat = "driver"
    b._terrain = Ground()
    b.T = lambda: b._terrain
    me = PlayerState(0, 0, "bot", Vec(0, 0, 0), vel=Vec(8.0, 0, 0), vehicle=20)
    return b, me


class TravelTests(unittest.TestCase):
    def leg(self, name):
        b, me = driver(name)
        v = dict(kind="ghost", fwd=(1.0, 0.0, 0.0))
        on = []
        for i in range(60):
            act = Act(0.0, 0.0)
            b.travel_boost(10.0 + i * 0.1, me, v, act, False)
            on.append(act.fire2)
        return on

    def test_reach_ghost_holds_it_the_whole_leg(self):
        self.assertTrue(all(self.leg("reach_test")))

    def test_elsewhere_the_taps_stay(self):
        on = self.leg("h3_test")
        self.assertTrue(any(on) and not all(on))


def reach_pilot(at, nose):
    b = bot("demon", name="reach_test")
    b._terrain = LowRoofAir()
    b.seat = "driver"
    me = PlayerState(0, 0, "bot", at, vel=Vec(5.0, 0, 0), yaw=math.pi, vehicle=77, weapon="banshee")
    return b, me, dict(kind="banshee", fwd=nose)


class RunTests(unittest.TestCase):
    def run_at(self, at, nose=(-1.0, 0.0, 0.0), phase="in", name=None):
        b, me, v = reach_pilot(at, nose)
        if name:
            b.game = name
        foe = PlayerState(1, 1, "foe", Vec(0, 0, 0))
        b.air_run = [phase, 1, 48.0, math.pi]
        ya = math.atan2(-at.y, -at.x)
        act = Act(ya, math.atan2(0.6 - at.z, math.hypot(at.x, at.y)))
        b.air_pass(50.0, me, 1, Belief(foe.pos, Vec(), 50.0, True, "eyes"), foe.pos, act, v)
        return b, act

    def test_boosted_in_from_past_gun_range(self):
        _, act = self.run_at(Vec(CANNON_R + 10.0, 0, 9.0))
        self.assertTrue(act.fire2)
        self.assertGreater(act.vertical, 0.5)                   # (Bot.boost's +0x3C, as the person's)

    def test_not_in_the_dive(self):
        _, act = self.run_at(Vec(CANNON_R - 8.0, 0, 9.0))
        self.assertFalse(act.fire2)

    def test_turning_back_it_pulls_the_throttle(self):
        b, act = self.run_at(Vec(CANNON_R + 10.0, 0, 9.0), nose=(1.0, 0.0, 0.0))     # (him behind the nose)
        self.assertEqual(act.forward, AIR_TIGHT_THROTTLE)
        self.assertFalse(act.fire2)
        self.assertIn("air: pulled back, turning tight", b.notes)

    def test_boosted_out(self):
        _, act = self.run_at(Vec(3.0, 0, 9.0), phase="out")
        self.assertTrue(act.fire2)

    def test_halo4_unchanged(self):
        _, act = self.run_at(Vec(CANNON_R + 10.0, 0, 9.0), nose=(1.0, 0.0, 0.0), name="h4")
        self.assertNotEqual(act.forward, AIR_TIGHT_THROTTLE)


class LeadTests(unittest.TestCase):
    def test_the_ghost_bolts_own_speed_leads_farther(self):
        me = PlayerState(0, 0, "bot", Vec(0, 0, 0), vehicle=20)
        goal = []
        for speed in (None, REACH_GHOST_BOLT):
            aim = Aim(make_profile("strong", "rusher", random.Random(3)), random.Random(5))   # (Demon's lead is 0)
            aim.step(10.0, 1 / 30, me, 1, Vec(17.0, 0, 0), Vec(0, 3.0, 0), False, gun="plasma_rifle",
                     shot_speed=speed)
            goal.append(aim.goal[0])
        self.assertGreater(goal[1], goal[0])                    # (same rolls: only the flight time differs)


if __name__ == "__main__":
    unittest.main()
