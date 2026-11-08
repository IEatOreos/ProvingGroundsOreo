"""Halo 4 Demon at riders (custom, Nov 7): the seated head read, the vehicle hulls, and the Demon seeing, leading and
firing at an exposed rider's head, not through his vehicle."""
import math
import random
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import vehicles                                       # noqa: E402
from brain.bot import Action, DEMON_LEAD_S, h4_demon_fire, h4_ray, h4_rider   # noqa: E402
from brain.core import PlayerState, Snapshot, Vec                # noqa: E402
from brain.live import LiveH4F                                   # noqa: E402
from test_h4_demon import OpenTerrain, ready_fight, scene        # noqa: E402

MK = (-6.9422384e-8, 0.02300628, -0.006868857)


def seated_live(head=(10.0, 20.0, 1.25), scale=1.0, dll="halo4.dll"):
    unit = bytearray(0x668)
    struct.pack_into("<HH", unit, 0x1BC, 120 * 52, 0x145C)
    node = struct.pack("<13f", scale, 1, 0, 0, 0, 1, 0, 0, 0, 1,
                       head[0] - MK[0] * scale, head[1] - MK[1] * scale, head[2] - MK[2] * scale)
    mem = {0x10000 + 0x145C + 54 * 52: node}
    live = LiveH4F.__new__(LiveH4F)
    live.g = SimpleNamespace(dll=dll, read=lambda a, n: mem.get(a))
    return live, bytes(unit)


class SeatedHeadReaderTests(unittest.TestCase):
    def test_reads_the_seated_head(self):
        live, unit = seated_live()
        h = live.h4_seated_head(0x10000, unit, (10.0, 20.0, 1.42), (10.1, 20.0, 1.0))
        self.assertAlmostEqual(h[2], 1.25, places=5)

    def test_guards(self):
        live, unit = seated_live()
        self.assertIsNone(live.h4_seated_head(0x10000, unit, (12.0, 20.0, 1.4), (10.1, 20.0, 1.0)))   # off his place
        self.assertIsNone(live.h4_seated_head(0x10000, unit, (10.0, 20.0, 1.4), (14.0, 20.0, 1.0)))   # off the vehicle
        self.assertIsNone(live.h4_seated_head(0x10000, unit, (10.0, 20.0, 1.4), None))
        live, unit = seated_live(scale=1.3)
        self.assertIsNone(live.h4_seated_head(0x10000, unit, (10.0, 20.0, 1.4), (10.1, 20.0, 1.0)))
        live, unit = seated_live(dll="groundhog.dll")
        self.assertIsNone(live.h4_seated_head(0x10000, unit, (10.0, 20.0, 1.4), (10.1, 20.0, 1.0)))


def hog(kind="storm_warthog", yaw=0.0, pos=(0.0, 0.0, 0.0)):
    return dict(handle=10, kind=kind, pos=pos, fwd=(math.cos(yaw), math.sin(yaw), 0.0), up=(0.0, 0.0, 1.0),
                occupied=True, team=1, riders=1)


class HullTests(unittest.TestCase):
    def test_warthog_driver_open_from_the_side_and_above(self):
        v, head = hog(), (0.01, 0.13, 0.24)
        self.assertFalse(vehicles.hull_blocks(v, (0.0, 10.0, 0.3), head))       # beside him, head height
        self.assertFalse(vehicles.hull_blocks(v, (8.0, 3.0, 2.0), head))        # ahead, from above
        self.assertFalse(vehicles.hull_blocks(v, (-10.0, 0.0, 0.8), (-0.55, 0.0, 0.65)))   # the gunner, from behind

    def test_warthog_body_takes_low_rounds(self):
        v, head = hog(), (0.01, 0.13, 0.24)
        self.assertTrue(vehicles.hull_blocks(v, (2.0, 0.13, -0.2), head))       # low ahead, through the hood
        self.assertFalse(vehicles.hull_blocks(v, (10.0, 0.13, 0.0), head))      # from far ahead it clears the hood
        self.assertTrue(vehicles.hull_blocks(v, (0.0, -2.0, -1.0), head))       # from below, through the far side
        self.assertTrue(vehicles.hull_blocks(hog(yaw=math.pi / 2), (-0.13, 2.0, -0.2), (-0.13, 0.01, 0.24)))  # turned

    def test_ghost_canopy_covers_the_front(self):
        v, head = hog("storm_ghost"), (-0.25, 0.01, 0.17)
        self.assertTrue(vehicles.hull_blocks(v, (10.0, 0.0, 0.15), head))
        self.assertFalse(vehicles.hull_blocks(v, (-10.0, 0.0, 0.3), head))

    def test_no_hull_no_block(self):
        self.assertFalse(vehicles.hull_blocks(hog("scorpion"), (10.0, 0.0, 0.0), (0.0, 0.0, 0.3)))
        v = hog()
        v["fwd"] = None
        self.assertFalse(vehicles.hull_blocks(v, (10.0, 0.0, 0.0), (0.0, 0.0, 0.3)))


def rider_scene(tier="demon", game_map="h4_test", vehicle_pos=(12.0, 0.0, 0.0), yaw=0.0, speed=10.0):
    bot, me, him, snap = scene(tier, game_map)
    v = hog(yaw=yaw, pos=vehicle_pos)
    him.vehicle = 10
    him.view_pos = None
    c, sn = math.cos(yaw), math.sin(yaw)
    # the driver's seat: 0.13 u to the vehicle's left, head 0.24 over its origin; his place 0.17 over his head
    hx, hy = vehicle_pos[0] - sn * 0.13, vehicle_pos[1] + c * 0.13
    him.head_pos = Vec(hx, hy, vehicle_pos[2] + 0.24)
    him.pos = Vec(hx, hy, vehicle_pos[2] + 0.41)
    him.vel = Vec(0.0, speed, 0.0)
    snap = Snapshot(0, [me, him], vehicles=[v])
    return bot, me, him, snap


class DemonRiderTests(unittest.TestCase):
    def test_gate(self):
        bot, me, him, snap = rider_scene()
        self.assertTrue(h4_rider(me, him))
        self.assertTrue(h4_demon_fire(bot.p, "h4", me, him))
        self.assertFalse(h4_demon_fire(bot.p, "reach", me, him))
        top, *_ = rider_scene("top")
        self.assertFalse(h4_demon_fire(top.p, "h4", me, him))
        me.vehicle = 4
        self.assertFalse(h4_rider(me, him))

    def test_lead_takes_the_vehicle_speed(self):
        bot, me, him, snap = rider_scene(speed=11.0)
        o, p = h4_ray(me, him, True, lead=True)
        self.assertAlmostEqual(p.y, him.head_pos.y + 11.0 * DEMON_LEAD_S)

    def test_perception_shoots_the_head_and_sees_the_vehicle(self):
        bot, me, him, snap = rider_scene()
        terrain = OpenTerrain()
        bot.per.update(0.0, me, snap, terrain.sees, [], game="h4")
        self.assertEqual(bot.per.target_parts[1], (True, True))
        self.assertIn((me.view_pos, him.head_pos, "see"), terrain.calls)

    # the Warthog on a ledge 2.5 u up, 6 u ahead, its passenger side to us: a round up at the driver's head on the far
    # side crosses its body first
    FAR_SIDE = dict(vehicle_pos=(6.0, 0.0, 2.5), yaw=-math.pi / 2)

    def test_hull_in_the_way_seen_not_shot(self):
        bot, me, him, snap = rider_scene(**self.FAR_SIDE)
        terrain = OpenTerrain()
        for t in (0.0, 0.5):
            bot.per.update(t, me, snap, terrain.sees, [], game="h4")
        self.assertEqual(bot.per.target_parts[1], (False, False))
        self.assertIn(1, bot.per.visible_enemies())

    def fight(self, n=4, **kw):
        bot, me, him, snap = rider_scene(**kw)
        terrain = OpenTerrain()
        out = []
        for k in range(n):
            now = 10.0 + k / 30
            ready_fight(bot, me, him, now, terrain)
            bot.per.update(now, me, snap, terrain.sees, [], game="h4")
            bot.per.last_seen[1] = now
            act = Action(yaw=me.yaw, pitch=me.pitch)
            bot.shot_part, bot.h4_lock, bot.fx = None, None, None
            bot.fight(now, 1 / 30, me, snap, 1, act, lambda *a, **kw2: None)
            bot.fire_gate(now, me, act, snap)
            bot.h4_pressed = bool(act.fire)
            out.append((act, bot.shot_part, bot.h4_lock))
        return out, bot

    def test_fires_at_an_exposed_riders_head(self):
        out, bot = self.fight()
        self.assertEqual([o[0].fire for o in out], [True, False, True, False])
        self.assertTrue(all(o[2] == (1, True) for o in out))

    def test_no_shot_through_the_hull(self):
        out, bot = self.fight(**self.FAR_SIDE)
        self.assertEqual(bot.per.target_parts[1], (False, False))
        self.assertFalse(any(o[0].fire for o in out))
        self.assertTrue(all(o[2] is None for o in out))

    def test_a_dry_rider_is_held_off(self):
        out, bot = self.fight(n=int(1.2 * 30))
        self.assertIn(1, bot.rider_dry)
        k = next(i for i, o in enumerate(out) if o[2] is None)
        self.assertGreaterEqual(k / 30, 0.75)
        self.assertFalse(any(o[0].fire for o in out[k + 1:]))


if __name__ == "__main__":
    unittest.main()
