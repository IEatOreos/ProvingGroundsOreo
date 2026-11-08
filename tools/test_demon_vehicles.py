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
