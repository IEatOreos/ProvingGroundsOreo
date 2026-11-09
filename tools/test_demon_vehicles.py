"""Banshee pilots under a low roof and their snap shots (Bot.air_pass, air_snap_fire), Demon's Ghost bail (may_drive),
its sidearm retreat (sidearm_cover) and its Slayer pairs (Director.pair_orders).

Run: python tools/test_demon_vehicles.py
"""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Belief, Bot, Order, AIR_ROOF_M
from brain.core import PlayerState, Snapshot, Vec
from brain.director import Director
from brain.profiles import make_profile


def bot(tier="demon", pid=0, name="h4_test"):
    b = Bot(pid, 0, make_profile(tier, "rusher", random.Random(3)), {"name": name}, random.Random(5))
    b.notes = []                                     # (made each tick by Bot.plan)
    return b


class LowRoofAir:
    """Flat floor at z 0, open air, the map's roof (a soft kill) at z 12.18 like Halo 4 Blood Crash's."""
    air_heights = (8.0, 11.0)

    def height_over(s, x, y, z):
        return z

    def air_roof(s, x, y):
        return 12.18

    def los(s, a, b):
        return True


class Act:
    def __init__(s, yaw=0.0, pitch=0.0):
        s.yaw, s.pitch, s.forward, s.strafe, s.fire, s.fire2, s.vertical = yaw, pitch, 1.0, 0.0, False, False, 0.0


BANSHEE = 77


def pilot(tier="demon", at=Vec(0, 0, 9.0), yaw=0.0):
    b = bot(tier)
    b._terrain = LowRoofAir()
    b.seat = "driver"
    me = PlayerState(0, 0, "bot", at, vel=Vec(10.0, 0, 0), yaw=yaw, vehicle=BANSHEE, weapon="banshee")
    return b, me


class AirRoofTests(unittest.TestCase):
    def test_ceiling_is_the_roof_less_its_margin(self):
        b, me = pilot()
        self.assertAlmostEqual(b.air_ceiling(0, 0, b._terrain), 12.18 - AIR_ROOF_M)
        b._terrain = type("NoRoof", (), {})()
        self.assertEqual(b.air_ceiling(0, 0, b._terrain), math.inf)

    def test_way_out_ends_under_a_low_roof(self):
        """25 u past him at 9 u over the floor, the most the roof allows: the turn back into the next run (the start
        height was 11 u, out of reach, and every way out ran its whole 6 s with the guns off)."""
        b, me = pilot(at=Vec(25.0, 0, 9.0))
        foe = PlayerState(1, 1, "foe", Vec(0, 0, 0))
        b.air_run = ["out", 1, 10.0, 0.0]
        act = Act()
        b.air_pass(11.0, me, 1, Belief(foe.pos, Vec(), 11.0, True, "eyes"), foe.pos, act)
        self.assertEqual(b.air_run[0], "in")

    def test_way_out_still_climbs_where_there_is_room(self):
        b, me = pilot(at=Vec(25.0, 0, 5.0))          # 5 u up: under the start height the roof leaves (8.68)
        foe = PlayerState(1, 1, "foe", Vec(0, 0, 0))
        b.air_run = ["out", 1, 10.0, 0.0]
        act = Act()
        b.air_pass(11.0, me, 1, Belief(foe.pos, Vec(), 11.0, True, "eyes"), foe.pos, act)
        self.assertEqual(b.air_run[0], "out")
        self.assertGreater(act.pitch, 0.0)


class DiveTests(unittest.TestCase):
    """The owner's Halo 4 strafe runs (20261108-144947): from 10-19 u, 4.6-9.6 u up, about 6 u/s."""

    def dive(self, speed, at=Vec(12.0, 0, 7.0)):
        b, me = pilot(at=at, yaw=math.pi)            # nosed at him
        me.vel = Vec(-speed, 0, 0)
        foe = PlayerState(1, 1, "foe", Vec(0, 0, 0))
        b.air_run = ["in", 1, 10.0, math.pi]
        act = Act(math.pi, -0.5)
        b.air_pass(12.0, me, 1, Belief(foe.pos, Vec(), 12.0, True, "eyes"), foe.pos, act)
        return b, act

    def test_a_fast_dive_in_gun_range_throttles_down(self):
        b, act = self.dive(12.0)
        self.assertEqual(b.air_run[0], "in")
        self.assertLessEqual(act.forward, 0.2)

    def test_at_his_speed_it_keeps_the_throttle(self):
        b, act = self.dive(5.0)
        self.assertEqual(act.forward, 1.0)

    def test_low_in_the_dive_the_run_goes_on(self):
        b, act = self.dive(6.0, at=Vec(10.0, 0, 3.5))   # 3.5 u up, 10 u off: one of his shots (the old end: 5 u)
        self.assertEqual(b.air_run[0], "in")
        b, act = self.dive(6.0, at=Vec(10.0, 0, 2.0))   # under 2.5 u: out
        self.assertEqual(b.air_run[0], "out")


class RunStartTests(unittest.TestCase):
    """A new man mid-dive, or a fresh run on a man ahead, is dived on, not flown away from (20261108-151434)."""

    def start(self, foe_at, run=None, yaw=math.pi):
        b, me = pilot(at=Vec(12.0, 0, 7.0), yaw=yaw)
        foe = PlayerState(2, 1, "foe", foe_at)
        b.air_run = run
        act = Act(yaw, -0.5)
        b.air_pass(12.0, me, 2, Belief(foe.pos, Vec(), 12.0, True, "eyes"), foe.pos, act)
        return b

    def test_a_new_man_ahead_mid_dive_keeps_the_dive(self):
        b = self.start(Vec(1.0, 2.0, 0.0), run=["in", 1, 10.0, math.pi])    # 11 u ahead, under PASS_START
        self.assertEqual(b.air_run[:2], ["in", 2])
        self.assertEqual(b.air_run[2], 10.0)                                 # (the dive's own clock kept)

    def test_a_fresh_run_on_a_man_ahead_dives(self):
        self.assertEqual(self.start(Vec(2.0, 0.0, 0.0)).air_run[0], "in")    # 10 u ahead

    def test_behind_or_too_close_starts_on_the_way_out(self):
        self.assertEqual(self.start(Vec(22.0, 0.0, 0.0)).air_run[0], "out")  # 10 u behind
        self.assertEqual(self.start(Vec(6.0, 0.0, 0.0)).air_run[0], "out")   # 6 u: under AIR_RUN_FROM


class DriverAimTests(unittest.TestCase):
    """Halo 4 Ghost and Banshee drivers aim from their camera anchor (vehicles.H4_DRIVER_AIM)."""

    def origin(self, kind):
        from brain.bot import h4_origin
        me = PlayerState(0, 0, "bot", Vec(5.0, 5.0, 1.0), vehicle=9)
        v = dict(handle=9, kind=kind, pos=[5.0, 5.0, 1.0], fwd=[1.0, 0.0, 0.0], up=[0.0, 0.0, 1.0], occupied=True)
        return h4_origin(me, Snapshot(1.0, [me], vehicles=[v]), "driver")

    def test_banshee_from_the_camera(self):
        b = self.origin("storm_banshee_mp")
        self.assertAlmostEqual(b.z, 1.0 + 0.595, places=3)
        self.assertAlmostEqual(b.x, 5.0 - 0.104, places=3)

    def test_ghost_and_others_keep_their_seat_view(self):
        for kind in ("storm_ghost", "storm_mongoose"):
            with self.subTest(kind=kind):
                self.assertLess(abs(self.origin(kind).z - 1.0), 0.05)


class PilotRadarTests(unittest.TestCase):
    """A Demon pilot does not leave its dive to check a tracker dot under it (the 3.2 hunt, 20261108-152614)."""

    @classmethod
    def setUpClass(cls):
        from brain.maps import load_map
        cls.map = load_map("reach_cex_headlong")

    def hunts(self, flying):
        b = Bot(0, 0, make_profile("demon", "rusher", random.Random(3)), self.map, random.Random(5))
        b.seat = "driver"
        me = PlayerState(0, 0, "bot", Vec(-27.3, 14.6, 7.6), weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15],
                         vehicle=BANSHEE if flying else -1)
        dot = PlayerState(1, 1, "foe", Vec(-27.3 + 9.0, 14.6, 7.6))
        vs = [dict(handle=BANSHEE, kind="storm_banshee_mp", pos=[me.pos.x, me.pos.y, me.pos.z], occupied=True)]
        snap = Snapshot(100.0, [me, dot], mode="slayer", vehicles=vs if flying else [])
        b.per.beliefs[1] = Belief(dot.pos, Vec(), 100.0, False, "radar")
        b.notes = []
        b.decide(100.0, me, snap)
        return [k for k, v in b.last_scores.items() if k[0] == "hunt" and v >= 3.0]

    def test_piloting(self):
        b, me = pilot()
        snap = Snapshot(1.0, [me], vehicles=[dict(handle=BANSHEE, kind="storm_banshee_mp", pos=[0, 0, 9], occupied=True)])
        self.assertTrue(b.piloting(me, snap))
        b.seat = "gunner"
        self.assertFalse(b.piloting(me, snap))
        me.vehicle = -1
        self.assertFalse(b.piloting(me, snap))

    def test_on_foot_it_still_turns_on_the_dot(self):
        self.assertTrue(self.hunts(False))

    def test_in_the_air_it_does_not(self):
        self.assertFalse(self.hunts(True))


class SnapFireTests(unittest.TestCase):
    def setup(self, tier="demon", foe_at=Vec(15.0, 0.0, 0.0), clear=True, seat="driver"):
        b, me = pilot(tier, at=Vec(0, 0, 6.0))
        b.seat = seat
        foe = PlayerState(1, 1, "foe", foe_at)
        snap = Snapshot(50.0, [me, foe], mode="slayer",
                        vehicles=[dict(handle=BANSHEE, kind="storm_banshee_mp", pos=[0, 0, 6.0], occupied=True)])
        if clear:
            b.per.clear_at[1] = 50.0
        from brain.bot import angles_to, eye, CHEST
        ya, pa = angles_to(eye(me), foe.pos + Vec(0, 0, CHEST))
        return b, me, snap, Act(ya, pa)

    def test_nose_on_him_fires(self):
        b, me, snap, act = self.setup()
        b.air_snap_fire(50.0, me, act, snap)
        self.assertTrue(act.fire)

    def test_every_tier_fires_its_cannons(self):
        for tier in ("novice", "average", "strong", "top"):
            with self.subTest(tier=tier):
                b, me, snap, act = self.setup(tier)
                b.air_snap_fire(50.0, me, act, snap)
                self.assertTrue(act.fire)

    def test_no_shot_off_the_nose_out_of_range_or_without_a_line(self):
        b, me, snap, act = self.setup()
        act.yaw += 0.6                               # the guard turned the nose 34 degrees off him
        b.air_snap_fire(50.0, me, act, snap)
        self.assertFalse(act.fire)
        b, me, snap, act = self.setup(foe_at=Vec(40.0, 0.0, 0.0))
        b.air_snap_fire(50.0, me, act, snap)
        self.assertFalse(act.fire)
        b, me, snap, act = self.setup(clear=False)
        b.air_snap_fire(50.0, me, act, snap)
        self.assertFalse(act.fire)

    def test_not_a_gunner_nor_on_a_bomb_cycle(self):
        b, me, snap, act = self.setup(seat="gunner")
        b.air_snap_fire(50.0, me, act, snap)
        self.assertFalse(act.fire)
        b, me, snap, act = self.setup()
        b.rod = ["to", 49.9]
        b.air_snap_fire(50.0, me, act, snap)
        self.assertFalse(act.fire)


class GhostBailTests(unittest.TestCase):
    def test_demon_leaves_a_spent_ghost(self):
        b = bot()
        snap = Snapshot(10.0, [], mode="slayer")
        for kind in ("ghost", "storm_ghost"):
            with self.subTest(kind=kind):
                self.assertFalse(b.may_drive(dict(handle=1, kind=kind, left=0.18), snap))
                self.assertFalse(b.may_drive(dict(handle=1, kind=kind, left=0.06), snap))
                self.assertTrue(b.may_drive(dict(handle=1, kind=kind, left=0.35), snap))
                self.assertTrue(b.may_drive(dict(handle=1, kind=kind), snap))           # (health unread)

    def test_a_tank_goes_down_with_its_driver(self):
        self.assertTrue(bot().may_drive(dict(handle=1, kind="storm_scorpion", left=0.12), Snapshot(10.0, [])))

    def test_other_tiers_keep_driving(self):
        self.assertTrue(bot("top").may_drive(dict(handle=1, kind="ghost", left=0.1), Snapshot(10.0, [])))


class OpenWall:
    """Flat floor, a wall along x = 2.5: what is west of it does not see east of it."""

    def path_ahead(s, a, b, n=80, **kw):
        d = b - a
        u = d.norm()
        return [a + u * (0.25 * (i + 1)) for i in range(min(n, int(d.flat() / 0.25)))]

    def los(s, a, b):
        return (a.x - 2.5) * (b.x - 2.5) > 0

    def walkable(s, p):
        return True


class SidearmCoverTests(unittest.TestCase):
    def setup(self, tier="demon", guns=("boltshot", "magnum"), foe_x=-10.0):
        b = bot(tier, name="reach_test")
        b._terrain = OpenWall()
        me = PlayerState(0, 0, "bot", Vec(), weapon=guns[0], weapons=list(guns), ammo=[10, 30], mag=[1, 8])
        b.per.beliefs[1] = Belief(Vec(foe_x, 0, 0), Vec(), 50.0, True, "eyes")
        return b, me, Snapshot(50.0, [me], mode="slayer")

    def test_pistols_only_go_to_cover(self):
        b, me, snap = self.setup()
        spot = b.sidearm_cover(me, snap, [1])
        self.assertIsNotNone(spot)
        self.assertGreater(spot.x, 2.5)

    def test_a_rifle_a_man_on_it_or_another_tier_stays(self):
        for kw in (dict(guns=("battle_rifle", "boltshot")), dict(foe_x=-4.0), dict(tier="top")):
            with self.subTest(**{k: str(v) for k, v in kw.items()}):
                b, me, snap = self.setup(**kw)
                self.assertIsNone(b.sidearm_cover(me, snap, [1]))

    def test_nobody_in_sight(self):
        b, me, snap = self.setup()
        self.assertIsNone(b.sidearm_cover(me, snap, []))


class FlatTerrain:
    def nav_z(s, x, y, z):
        return z

    def ground_ok(s, x, y, z, drop=0.6):
        return True

    def los(s, a, b):
        return True


class PairTests(unittest.TestCase):
    def team(self, tiers, mode="slayer"):
        d = Director.__new__(Director)
        d._T = FlatTerrain()
        bots = [bot(t, pid=i) for i, t in enumerate(tiers)]
        d.bots = {b.id: b for b in bots}
        d.roles = {b.id: "mid" for b in bots}
        players = [PlayerState(b.id, 0, "bot", Vec(10.0 * b.id, 0, 0)) for b in bots]
        for k, b in enumerate(bots):
            b.order = Order("mid", Vec(20.0 * k, 40.0, 0), via=(Vec(5.0 * k, 5.0, 0),))
        return d, bots, Snapshot(100.0, players, mode=mode)

    def test_two_demons_share_a_post_and_route(self):
        d, (a, b, c), snap = self.team(["demon", "average", "demon"])
        d.pair_orders(100.0, snap, [a, b, c])
        self.assertEqual(d.pairs, [(0, 2)])
        self.assertEqual(c.order.via, a.order.via)
        self.assertLess((c.order.point - a.order.point).flat(), 5.0)
        self.assertEqual(b.order.point, Vec(20.0, 40.0, 0))   # the others keep their own

    def test_a_lone_demon_takes_a_legendary(self):
        d, (a, b, c), snap = self.team(["strong", "top", "demon"])
        d.pair_orders(100.0, snap, [a, b, c])
        self.assertEqual(d.pairs, [(2, 1)])
        self.assertLess((b.order.point - c.order.point).flat(), 5.0)

    def test_patrol_shared(self):
        d, (a, b), snap = self.team(["demon", "demon"])
        a.infantry_patrol = (Vec(-30, 0, 0), 140.0)
        d.infantry_patrollers = [a]
        d.pair_orders(100.0, snap, [a, b])
        self.assertEqual(b.infantry_patrol, a.infantry_patrol)
        self.assertIn(b, d.infantry_patrollers)

    def test_not_in_a_vehicle_nor_outside_slayer(self):
        d, (a, b), snap = self.team(["demon", "top"])
        snap.players[0].vehicle = 9
        d.pair_orders(100.0, snap, [a, b])
        self.assertEqual(b.order.point, Vec(20.0, 40.0, 0))
        d, (a, b), snap = self.team(["demon", "top"], mode="ctf")
        d.pair_orders(100.0, snap, [a, b])
        self.assertEqual(b.order.point, Vec(20.0, 40.0, 0))

    def test_no_partner_no_pair(self):
        d, (a, b), snap = self.team(["demon", "strong"])
        d.pair_orders(100.0, snap, [a, b])
        self.assertEqual(d.pairs, [])


if __name__ == "__main__":
    unittest.main()
