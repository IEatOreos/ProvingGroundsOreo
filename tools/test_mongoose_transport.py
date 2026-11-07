"""Finite Mongoose trips through the real director and driver entry points."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Belief, Bot, Order
from brain.core import Action, FlagState, PlayerState, Snapshot, Vec
from brain.director import Director
from brain.profiles import make_profile
from brain import vehicles


def scene(kind='mongoose', mode='slayer'):
    mapdata = dict(name='reach_test', flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)},
                   points={'mid': Vec(80, 0, 0)})
    bot = Bot(0, 0, make_profile('demon', 'rusher', random.Random(3)), mapdata)
    bot.order = Order('mid', Vec(80, 0, 0))
    bot.seat = 'driver'
    bot.drive_to = bot.order.point
    bot._terrain = SimpleNamespace(vnav=lambda start, goal: goal)
    bot.notes = []
    me = PlayerState(0, 0, 'driver', Vec(), vehicle=10)
    v = dict(handle=10, kind=kind, pos=(0, 0, 0), occupied=True, team=0, riders=1, fwd=(1, 0, 0))
    snap = Snapshot(100, [me], vehicles=[v], mode=mode)
    director = Director.__new__(Director)
    director.team = director.side = 0
    director.map, director.bots, director.roles = mapdata, {0: bot}, {0: 'mid'}
    director.event = lambda *args: None
    director.getaway_park = lambda *args: None
    director.carry_point = lambda *args: Vec(100, 0, 0)
    director.enemy_vehicles = lambda *args: []
    return director, bot, me, snap


def jobs(director, bot, me, snap, now=100):
    director.vehicle_jobs(now, snap, [bot], {bot.id: me})


def drive(bot, me, snap, now=100):
    act = Action()
    bot.drive(now, 1/30, me, snap, act, lambda a, b: b)
    return act


class MongooseTransportTests(unittest.TestCase):
    def test_transport_role_and_crew_need_a_useful_trip(self):
        self.assertEqual(vehicles.roles_of('mongoose'), ('transport',))
        for point, retry, expected in ((None, 0, False), (Vec(10, 0, 0), 0, False),
                                       (Vec(80, 0, 0), 0, True), (Vec(80, 0, 0), 120, False)):
            d, b, me, snap = scene()
            me.vehicle = -1
            snap.vehicles[0]['occupied'] = False
            b.order = Order('mid', point)
            b.vehicle_retry_at = retry
            b.set_order = lambda order, **kwargs: setattr(b, 'order', order)
            d.crew_orders(100, snap, {0: me}, [b])
            self.assertEqual(b.order.role == 'drive', expected)
            if expected:
                self.assertEqual(b.drive_to, point)

    def test_multiple_mongooses_do_not_fill_harasser_roles(self):
        d, b, me, snap = scene()
        other = Bot(1, 0, b.p, d.map)
        other.order = Order('mid', Vec(80, 0, 0))
        other.set_order = lambda order, **kwargs: setattr(other, 'order', order)
        b.set_order = lambda order, **kwargs: setattr(b, 'order', order)
        p = PlayerState(1, 0, 'other', Vec())
        me.vehicle = -1
        snap.players.append(p)
        snap.vehicles[0]['occupied'] = False
        snap.vehicles.append(dict(snap.vehicles[0], handle=20))
        d.bots[1] = other
        d.crew_orders(100, snap, {0: me, 1: p}, [b, other])
        self.assertEqual(sum(x.order.role == 'drive' for x in (b, other)), 1)

    def test_assigned_driver_arrives_and_dismounts(self):
        d, b, me, snap = scene()
        b.order = Order('drive', Vec(), target=10)
        jobs(d, b, me, snap)
        self.assertEqual(b.vjob, 'taxi')
        drive(b, me, snap)
        self.assertIsNone(b.crew_ride)
        me.pos = Vec(78, 0, 0)
        snap.vehicles[0]['pos'] = (78, 0, 0)
        jobs(d, b, me, snap, 101)
        act = drive(b, me, snap, 101)
        self.assertTrue(act.action)
        self.assertEqual(act.forward, 0)
        self.assertEqual(b.vjob, 'dismount')
        self.assertGreaterEqual(b.vehicle_retry_at, 131)
        self.assertNotEqual(b.goal[0], 'vehicle')
        # A role pass while Use is held cannot turn the finished trip into another patrol.
        jobs(d, b, me, snap, 103)
        self.assertEqual(b.vjob, 'dismount')

    def test_empty_short_trip_exits_and_stale_destination_is_cleared(self):
        d, b, me, snap = scene()
        b.order = Order('free')
        b.drive_to = None
        jobs(d, b, me, snap)
        self.assertEqual(b.vjob, 'dismount')
        self.assertTrue(drive(b, me, snap).action)
        self.assertIsNone(b.drive_to)

    def test_moving_destination_cannot_restart_trip_deadline(self):
        d, b, me, snap = scene()
        jobs(d, b, me, snap)
        deadline = b.mongoose_trip['until']
        b.order = Order('hunter', Vec(200, 0, 0))
        jobs(d, b, me, snap, 110)
        self.assertEqual(b.mongoose_trip['until'], deadline)
        jobs(d, b, me, snap, deadline)
        self.assertEqual(b.vjob, 'dismount')

    def test_carrier_pickup_wait_is_bounded(self):
        d, b, me, snap = scene(mode='ctf')
        carrier = PlayerState(1, 0, 'carrier', Vec(4, 0, 0), has_flag=True)
        snap.players.append(carrier)
        b.order = Order('ferry', Vec(100, 0, 0), target=1)
        jobs(d, b, me, snap)
        self.assertEqual(b.vjob, 'pickup')
        self.assertFalse(drive(b, me, snap).action)
        self.assertEqual(drive(b, me, snap).forward, 0)
        # The next role assignment does not erase the pickup timer.
        b.order = Order('mid', Vec(80, 0, 0))
        jobs(d, b, me, snap, 108)
        self.assertEqual(b.vjob, 'dismount')
        self.assertTrue(drive(b, me, snap, 108).action)

    def test_carrier_aboard_keeps_ferry_home_until_arrival(self):
        d, b, me, snap = scene(mode='ctf')
        carrier = PlayerState(1, 0, 'carrier', Vec(4, 0, 0), has_flag=True)
        snap.players.append(carrier)
        b.order = Order('ferry', Vec(100, 0, 0), target=1)
        jobs(d, b, me, snap)
        carrier.vehicle = 10
        snap.vehicles[0]['riders'] = 2
        b.order = Order('mid', Vec(80, 0, 0))
        jobs(d, b, me, snap, 109)
        self.assertEqual(b.vjob, 'taxi')
        self.assertEqual(b.order.role, 'ferry')
        self.assertEqual(b.drive_to, Vec(100, 0, 0))
        self.assertFalse(drive(b, me, snap, 109).action)
        me.pos = Vec(98, 0, 0)
        jobs(d, b, me, snap, 110)
        self.assertTrue(drive(b, me, snap, 110).action)

    def test_invalid_carrier_cancels_pickup(self):
        for reason in ('dead', 'dropped', 'other_vehicle', 'mode'):
            d, b, me, snap = scene(mode='ctf')
            carrier = PlayerState(1, 0, 'carrier', Vec(20, 0, 0), has_flag=True)
            snap.players.append(carrier)
            b.order = Order('ferry', Vec(100, 0, 0), target=1)
            jobs(d, b, me, snap)
            if reason == 'dead': carrier.alive = False
            if reason == 'dropped': carrier.has_flag = False
            if reason == 'other_vehicle': carrier.vehicle = 20
            if reason == 'mode': snap.mode = 'slayer'
            jobs(d, b, me, snap, 101)
            self.assertEqual(b.vjob, 'dismount', reason)

    def test_getaway_wait_and_objective_change(self):
        for change in (False, True):
            d, b, me, snap = scene(mode='ctf')
            d.getaway_park = lambda *args: Vec()
            snap.flags[1] = FlagState(1, Vec(200, 0, 0), Vec(200, 0, 0))
            jobs(d, b, me, snap)
            self.assertEqual(b.vjob, 'getaway')
            self.assertEqual(drive(b, me, snap).forward, 0)
            self.assertFalse(drive(b, me, snap).action)
            if change: snap.flags[1].state = 'dropped'
            jobs(d, b, me, snap, 101 if change else 120)
            self.assertEqual(b.vjob, 'dismount')
            self.assertTrue(drive(b, me, snap, 121).action)

    def test_getaway_approach_reaches_parking_radius_before_dismount(self):
        d, b, me, snap = scene(mode='ctf')
        d.getaway_park = lambda *args: Vec(5, 0, 0)
        jobs(d, b, me, snap)
        act = drive(b, me, snap)
        self.assertFalse(act.action)
        self.assertGreater(act.forward, 0)
        me.pos = Vec(4, 0, 0)
        jobs(d, b, me, snap, 101)
        act = drive(b, me, snap, 101)
        self.assertFalse(act.action)
        self.assertEqual(act.forward, 0)

    def test_getaway_carrier_death_cancels_even_before_flag_state_updates(self):
        d, b, me, snap = scene(mode='ctf')
        runner = PlayerState(1, 0, 'runner', Vec(200, 0, 0), has_flag=True)
        snap.players.append(runner)
        snap.flags[1] = FlagState(1, Vec(200, 0, 0), runner.pos, 'carried', 1)
        d.getaway_park = lambda *args: Vec()
        jobs(d, b, me, snap)
        self.assertEqual(b.vjob, 'getaway')
        runner.alive = False
        jobs(d, b, me, snap, 101)
        self.assertEqual(b.vjob, 'dismount')

    def test_gunner_vehicles_keep_their_crew_patrol(self):
        d, b, me, snap = scene(kind='warthog')
        b.order = Order('drive', Vec(), target=10)
        b.patrol_point = lambda *args: Vec(80, 0, 0)
        drive(b, me, snap)
        self.assertEqual(b.crew_ride, 10)
        me.pos = Vec(79, 0, 0)
        self.assertFalse(drive(b, me, snap, 110).action)
        self.assertEqual(b.drive_to, Vec(80, 0, 0))

    def test_race_stays_on_checkpoint_course(self):
        d, b, me, snap = scene(mode='race')
        snap.race_next[0] = Vec(2, 0, 0)
        jobs(d, b, me, snap)
        self.assertEqual(b.vjob, 'taxi')
        self.assertFalse(drive(b, me, snap).action)

    def test_opportunistic_splatter_stays_in_front_of_trip(self):
        d, b, me, snap = scene()
        enemy = PlayerState(1, 1, 'enemy', Vec(10, 0, 0), weapon='assault_rifle')
        snap.players.append(enemy)
        b.per.beliefs[1] = Belief(enemy.pos, Vec(), 100, True, 'eyes')
        b.per.recognized.add(1)
        jobs(d, b, me, snap)
        act = drive(b, me, snap)
        self.assertEqual(b.att[0], 'splatter')
        self.assertEqual(act.forward, 1)
        enemy.pos = Vec(0, 10, 0)
        belief = Belief(enemy.pos, Vec(), 100, True, 'eyes')
        self.assertFalse(b.ram_ok(me, snap.vehicles[0], vehicles.strategy('mongoose'), snap, enemy, belief))

    def test_emergency_evade_and_stuck_reverse_still_work(self):
        d, b, me, snap = scene()
        enemy = PlayerState(1, 1, 'enemy', Vec(4, 0, 0), weapon='plasma_pistol')
        snap.players.append(enemy)
        b.per.beliefs[1] = Belief(enemy.pos, Vec(), 100, True, 'eyes')
        b.per.recognized.add(1)
        jobs(d, b, me, snap)
        drive(b, me, snap)
        act = drive(b, me, snap, 101)
        self.assertEqual(b.att[0], 'evade')
        self.assertEqual(act.forward, 1)
        d, b, me, snap = scene()
        jobs(d, b, me, snap)
        drive(b, me, snap)
        drive(b, me, snap, 103)
        self.assertGreater(b.reverse_until, 103)
        self.assertEqual(drive(b, me, snap, 103.1).forward, -1)

    def test_other_vehicle_and_on_foot_clear_mongoose_trip_state(self):
        d, b, me, snap = scene()
        jobs(d, b, me, snap)
        me.vehicle = -1
        jobs(d, b, me, snap, 101)
        self.assertIsNone(b.mongoose_trip)
        self.assertIn('harasser', vehicles.roles_of('gungoose'))


if __name__ == '__main__':
    unittest.main()
