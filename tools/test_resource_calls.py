"""Exercise actual vehicle assignment paths with mixed difficulties."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain.core import Snapshot, Vec
from brain.bot import Order
from brain.director import Director
from test_legendary_power_fetch import participant


def scene(kind='banshee', distances=(12, 2), tiers=('demon', 'top')):
    entries = [participant(tier, d, pid=i) for i, (tier, d) in enumerate(zip(tiers, distances))]
    bots = [b for b, p in entries]
    players = {p.id:p for b, p in entries}
    for b in bots:
        b.order = Order('mid', Vec(100, 0, 0))
        b.set_order = lambda order, sure=False, b=b: setattr(b, 'order', order)
    d = Director.__new__(Director)
    d.team, d.map, d.roles, d.bots = 0, {}, {}, {b.id:b for b in bots}
    d.event = lambda *a: None
    d.enemy_vehicles = lambda *a: []
    v = dict(handle=10, kind=kind, pos=(0, 0, 0), occupied=False, team=0, riders=0)
    snap = Snapshot(100, list(players.values()), vehicles=[v])
    return d, snap, bots, players


class ResourceCallTests(unittest.TestCase):
    def test_power_vehicle_prefers_difficulty_with_range_fallback(self):
        for distances, expected in (((40, 2), 0), ((46, 2), 1)):
            d, snap, bots, players = scene(distances=distances)
            d.crew_orders(100, snap, players, bots)
            self.assertEqual(d.crews[10][0], expected)

    def test_nearby_busy_demon_can_receive_power_vehicle_before_free_legendary(self):
        for distance, expected in ((14, 0), (16, 1)):
            d, snap, bots, players = scene(distances=(distance, 2))
            d.crew_orders(100, snap, players, [bots[1]], [bots[0]])
            self.assertEqual(d.crews[10][0], expected)

    def test_existing_vehicle_assignment_is_preserved(self):
        d, snap, bots, players = scene()
        d.crews = {10:(1, 99)}
        d.crew_orders(100, snap, players, bots)
        self.assertEqual(d.crews[10][0], 1)

    def test_transport_still_selects_nearest(self):
        d, snap, bots, players = scene('mongoose')
        d.crew_orders(100, snap, players, bots)
        self.assertEqual(d.crews[10][0], 1)

    def test_honked_gunner_uses_difficulty_priority(self):
        d, snap, bots, players = scene('warthog')
        snap.honks = [10]
        snap.vehicles[0].update(occupied=True, riders=1)
        d.honk_orders(100, snap, bots, players)
        self.assertEqual(bots[0].order.role, 'ride')
        self.assertEqual(bots[1].order.role, 'board')

    def test_driver_calls_demon_to_gun_and_nearest_to_passenger(self):
        d, snap, bots, players = scene('warthog', distances=(10, 2))
        snap.vehicles[0].update(occupied=True, riders=1)
        d.rider_ok = lambda *a: True
        d.rider_calls(100, snap, bots, players)
        self.assertEqual(bots[0].order.role, 'ride')
        self.assertEqual(bots[1].order.role, 'board')

    def test_direct_gunner_call_filters_range_before_priority(self):
        for distance, expected in ((24, 0), (26, 1)):
            d, snap, bots, players = scene('warthog', distances=(distance, 2))
            snap.vehicles[0].update(occupied=True, riders=1)
            for name in ('honk_orders', 'crew_orders', 'rider_calls', 'ferry_orders', 'vehicle_jobs'):
                setattr(d, name, lambda *a: None)
            d.vehicle_orders(100, snap, bots)
            self.assertEqual(bots[expected].order.role, 'ride')

    def test_driver_pickup_filters_range_before_priority(self):
        for distance, expected in ((50, 0), (61, 1)):
            d, snap, bots, players = scene('warthog', distances=(distance, 2))
            driver, me = participant('average', 0, pid=3)
            me.vehicle = 10
            players[3] = me
            d.rider_ok = lambda *a: True
            result = d.gunner_pickup(100, driver, me, snap, bots, players)
            self.assertEqual(result, players[expected].pos)


if __name__ == '__main__':
    unittest.main()
