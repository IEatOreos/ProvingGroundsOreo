"""Exercise actual vehicle assignment paths with mixed difficulties."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain.core import Snapshot, Vec
from brain.bot import Order
from brain.director import Director
from brain.profiles import resource_priority, gunner_priority
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
    def test_scaling_equals_heroic_and_gunner_weights_tie_legendary(self):
        profiles = {tier: participant(tier, 2)[0].p for tier in ('demon', 'top', 'strong', 'scaling', 'average')}
        self.assertEqual(resource_priority(profiles['scaling']), resource_priority(profiles['strong']))
        self.assertLess(resource_priority(profiles['scaling']), resource_priority(profiles['average']))
        self.assertEqual({gunner_priority(profiles[tier]) for tier in ('top', 'strong', 'scaling')}, {1})
        for tiers in (('top', 'strong'), ('top', 'scaling'), ('strong', 'scaling')):
            d, snap, bots, players = scene('warthog', tiers=tiers)
            snap.honks = [10]
            snap.vehicles[0].update(occupied=True, riders=1)
            d.honk_orders(100, snap, bots, players)
            self.assertEqual(bots[1].order.role, 'ride')

    def test_demon_fetch_is_not_diverted_to_any_new_gunner_call(self):
        for path in ('honk', 'rider', 'direct', 'pickup'):
            d, snap, bots, players = scene('warthog', distances=(10, 2))
            bots[0].fetch = (Vec(30, 0, 0), 'rockets', 125, None)
            snap.vehicles[0].update(occupied=True, riders=1)
            d.rider_ok = lambda *a: True
            if path == 'honk':
                snap.honks = [10]
                d.honk_orders(100, snap, bots, players)
            elif path == 'rider':
                d.rider_calls(100, snap, bots, players)
            elif path == 'direct':
                for name in ('honk_orders', 'rider_calls', 'ferry_orders', 'vehicle_jobs'):
                    setattr(d, name, lambda *a: None)
                d.vehicle_orders(100, snap, bots)
            else:
                driver, me = participant('average', 0, pid=3)
                me.vehicle = 10
                self.assertEqual(d.gunner_pickup(100, driver, me, snap, bots, players), players[1].pos)
            self.assertNotEqual(bots[0].order.role, 'ride')
            self.assertIsNotNone(bots[0].fetch)

    def test_power_vehicle_is_reserved_before_honked_gunner(self):
        d, snap, bots, players = scene(distances=(12, 2))
        snap.vehicles.append(dict(handle=20, kind='warthog', pos=(0, 0, 0), occupied=True, team=0, riders=1))
        snap.honks = [20]
        for name in ('rider_calls', 'ferry_orders', 'vehicle_jobs'):
            setattr(d, name, lambda *a: None)
        d.vehicle_orders(100, snap, bots)
        self.assertEqual(bots[0].order.role, 'drive')
        self.assertEqual(bots[0].order.target, 10)
        self.assertEqual(bots[1].order.role, 'ride')

    def test_honk_does_not_steal_any_assigned_driver(self):
        for tier in ('demon', 'top', 'strong', 'scaling', 'average'):
            d, snap, bots, players = scene('warthog', tiers=(tier, 'average'))
            bots[0].order = Order('drive', Vec(20, 0, 0), target=30)
            snap.honks = [10]
            snap.vehicles[0].update(occupied=True, riders=1)
            d.honk_orders(100, snap, bots, players)
            self.assertEqual(bots[0].order.role, 'drive')
            self.assertEqual(bots[1].order.role, 'ride')

    def test_weapon_call_is_reserved_before_vehicle_orders(self):
        d, snap, bots, players = scene('warthog', distances=(12, 2))
        d.map['items'] = [dict(name='rockets', kind='weapon', value=1.0, pos=Vec())]
        d.item_up = {}
        snap.ground_weapons = [('rockets', Vec())]
        snap.honks = [10]
        snap.vehicles[0].update(occupied=True, riders=1)
        d.role_slots = lambda *a: []
        d.backup_orders = lambda *a: None
        for name in ('rider_calls', 'ferry_orders', 'vehicle_jobs'):
            setattr(d, name, lambda *a: None)
        d.assign_roles(100, snap)
        self.assertIsNotNone(bots[0].fetch)
        self.assertNotEqual(bots[0].order.role, 'ride')
        self.assertEqual(bots[1].order.role, 'ride')

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
