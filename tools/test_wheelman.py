"""(custom, Nov 13) The Wheelman play style: always goes for a vehicle, a Warthog first, first in line for the team's
wheels and from farther, keeps its vehicle at a trip's end. The owner: "a personality that always wants to drive
warthogs ... call it wheelman", Demon and Easy kept as they are (no Demon at a Warthog's, Mongoose's or Ghost's wheel;
Easy never drives a person on a gun)."""
import random
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from brain import profiles                                  # noqa: E402
from brain.bot import WHEEL_SEEK_R, Bot, Order              # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from brain.director import Director                        # noqa: E402
import botctl                                              # noqa: E402

MAP = dict(name="h4_test", flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)})


def bot(i, tier, style="wheelman"):
    b = Bot(i, 0, profiles.make_profile(tier, style, random.Random(i)), MAP)
    b.order = Order("mid", Vec(80, 0, 0))
    b.set_order = lambda order, b=b, **kw: setattr(b, "order", order)
    return b


def veh(h, kind, x, occupied=False, riders=0):
    return dict(handle=h, kind=kind, pos=(x, 0, 0), occupied=occupied, team=0, riders=riders, fwd=(1, 0, 0))


class ProfileTests(unittest.TestCase):
    def test_style(self):
        self.assertTrue(profiles.wheelman(profiles.make_profile("average", "wheelman", random.Random(1))))
        self.assertFalse(profiles.wheelman(profiles.make_profile("average", "flanker", random.Random(1))))
        p = lambda t: profiles.driver_priority(profiles.make_profile(t, "wheelman", random.Random(1)))
        for t in ("novice", "average", "strong", "top", "blind", "tactician"):
            self.assertEqual(p(t), -1, t)
        self.assertIsNone(p("demon"))
        self.assertEqual(profiles.driver_priority(profiles.make_profile("average", "rusher", random.Random(1))), 0)

    def test_menus_and_not_dealt_to_any(self):
        self.assertEqual(botctl.STYLE_KEYS[-2:], ("wheelman", "any"))
        panel = (ROOT / "native" / "bots_panel.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn('"sniper",\n                                            "wheelman", "any" };', panel)
        self.assertIn('"Wheelman", "Any style" };', panel)
        header = (ROOT / "native" / "bots_panel.h").read_text(encoding="utf-8", errors="replace")
        self.assertIn("#define HB_STYLE_ANY 8", header)
        self.assertIn("#define HB_STYLES 9", header)
        play = (ROOT / "tools" / "play.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn('"rusher,flanker,camper,objector,spammer,grudger,sniper"', play)
        self.assertNotIn("wheelman", play)


class PickTests(unittest.TestCase):
    def pick(self, tier, vs, me_at=0.0, players=()):
        b = bot(0, tier)
        me = PlayerState(0, 0, "bot", Vec(me_at, 0, 0))
        snap = Snapshot(100, [me, *players], vehicles=vs, mode="slayer")
        v = b.wheel_pick(100, me, snap)
        return v and v["handle"]

    def test_warthog_first(self):
        self.assertEqual(self.pick("average", [veh(1, "ghost", 10), veh(2, "warthog", 30), veh(3, "mongoose", 5)]), 2)
        self.assertEqual(self.pick("average", [veh(1, "banshee", 10), veh(2, "scorpion", 30)]), 2)   # ground first
        self.assertEqual(self.pick("average", [veh(3, "mongoose", 5)]), 3)

    def test_range_and_taken(self):
        self.assertIsNone(self.pick("average", [veh(2, "warthog", WHEEL_SEEK_R + 5)]))
        self.assertEqual(self.pick("average", [veh(2, "warthog", WHEEL_SEEK_R - 5)]), 2)
        self.assertIsNone(self.pick("average", [veh(2, "warthog", 10, occupied=True, riders=1)]))

    def test_demon_wheelman_skips_warthog_mongoose_ghost(self):
        vs = [veh(1, "warthog", 5), veh(2, "mongoose", 6), veh(3, "ghost", 7), veh(4, "scorpion", 40)]
        self.assertEqual(self.pick("demon", vs), 4)
        self.assertIsNone(self.pick("demon", vs[:3]))

    def test_wheel_with_a_person_on_the_gun_not_easy(self):
        you = PlayerState(5, 0, "you", Vec(20, 0, 0), vehicle=2)
        you.is_bot, you.gunner_seat = False, True
        vs = [veh(2, "warthog", 20, occupied=True, riders=1)]
        self.assertEqual(self.pick("average", vs, players=[you]), 2)
        self.assertIsNone(self.pick("novice", vs, players=[you]))


class CrewTests(unittest.TestCase):
    def scene(self, specs, kind="warthog"):
        bots = [bot(i, t, st) for i, (t, st, _) in enumerate(specs)]
        players = {b.id: PlayerState(b.id, 0, f"b{b.id}", Vec(x, 0, 0)) for b, (_, _, x) in zip(bots, specs)}
        snap = Snapshot(100, list(players.values()), vehicles=[veh(10, kind, 0)], mode="slayer")
        d = Director.__new__(Director)
        d.team = d.side = 0
        d.map, d.bots, d.roles = MAP, {b.id: b for b in bots}, {b.id: "mid" for b in bots}
        d.event = lambda *args: None
        d.enemy_vehicles = lambda *args: []
        d.crew_orders(100, snap, players, bots)
        return bots

    def test_wheelman_before_a_nearer_normal(self):
        bots = self.scene([("average", "rusher", 3.0), ("top", "wheelman", 30.0)])
        self.assertEqual(bots[1].order.role, "drive")
        self.assertNotEqual(bots[0].order.role, "drive")

    def test_from_farther(self):
        self.assertEqual(self.scene([("average", "wheelman", 60.0)])[0].order.role, "drive")
        self.assertNotEqual(self.scene([("average", "rusher", 60.0)])[0].order.role, "drive")

    def test_demon_wheelman_not_sent_to_a_warthog(self):
        self.assertNotEqual(self.scene([("demon", "wheelman", 5.0)])[0].order.role, "drive")


def seated_scene(specs, mode="ctf", carrier_at=None):
    """Bots at the wheels of Warthogs: specs [(tier, style, x)]; carrier_at: our carrier bot on foot there."""
    bots, players, vs = [], {}, []
    for i, (t, st, x) in enumerate(specs):
        b = bot(i, t, st)
        b.seat = "driver"
        bots.append(b)
        players[i] = PlayerState(i, 0, f"b{i}", Vec(x, 0, 0), vehicle=20 + i)
        vs.append(dict(veh(20 + i, "warthog", x, occupied=True, riders=1)))
    if carrier_at is not None:
        cb = bot(9, "average", "rusher")
        cp = PlayerState(9, 0, "carrier", carrier_at)
        cp.has_flag = True
        bots.append(cb)
        players[9] = cp
    snap = Snapshot(100, list(players.values()), vehicles=vs, mode=mode)
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map, d.bots, d.roles = MAP, {b.id: b for b in bots}, {b.id: "mid" for b in bots}
    d.event = lambda *args: None
    d.carry_point = lambda snap: Vec(200, 0, 0)
    d.gunner_pickup = lambda *a, **k: None
    return d, bots, players, snap


class CarrierRideTests(unittest.TestCase):
    """(Nov 13, the owner: "always go pick up flag carriers or objective") a Wheelman first for our carrier, from
    farther, first for the getaway ride, and to the objective when nothing is carried."""

    def ferry(self, specs):
        d, bots, players, snap = seated_scene(specs, carrier_at=Vec(0, 0, 0))
        d.ferry_orders(100, snap, bots, players)
        return [b.order.role for b in bots[:len(specs)]]

    def test_carrier_pickup_wheelman_first_and_from_farther(self):
        self.assertEqual(self.ferry([("average", "rusher", 20.0), ("average", "wheelman", 60.0)]), ["mid", "ferry"])
        self.assertEqual(self.ferry([("average", "rusher", 20.0), ("average", "wheelman", 80.0)]), ["ferry", "mid"])
        self.assertEqual(self.ferry([("average", "wheelman", 60.0)]), ["ferry"])
        self.assertEqual(self.ferry([("average", "rusher", 60.0)]), ["mid"])

    def jobs(self, specs, mode="ctf", park=Vec(-80, 0, 0)):
        d, bots, players, snap = seated_scene(specs, mode=mode)
        d.getaway_park = lambda snap, at: park
        d.vehicle_jobs(100, snap, bots, players)
        return bots

    def test_getaway_ride_goes_to_the_wheelman(self):
        bots = self.jobs([("average", "rusher", 10.0), ("strong", "wheelman", 30.0)])
        self.assertEqual((bots[0].vjob, bots[1].vjob), (None, "getaway"))
        bots = self.jobs([("average", "rusher", 10.0), ("strong", "flanker", 30.0)])
        self.assertEqual((bots[0].vjob, bots[1].vjob), ("getaway", None))   # (as before: the first free driver)

    def test_objective_run(self):
        b = self.jobs([("average", "wheelman", 10.0)], park=None)[0]
        self.assertEqual(b.vjob, "objective")
        self.assertEqual(b.drive_to, MAP["flags"][1])                         # their flag (straight_objective)
        self.assertIsNone(self.jobs([("average", "rusher", 10.0)], park=None)[0].vjob)
        self.assertIsNone(self.jobs([("average", "wheelman", 10.0)], mode="slayer", park=None)[0].vjob)


class KeepTests(unittest.TestCase):
    def arrive(self, style):
        b = bot(0, "average", style)
        b.seat, b.seat_for, b.seat_since = "driver", 10, 99.0
        b.drive_to = Vec(2, 0, 0)                     # where it goes: 2 u off, arrived
        b._terrain = SimpleNamespace(vnav=lambda start, goal: goal)
        b.notes = []
        me = PlayerState(0, 0, "bot", Vec(), vehicle=10)
        snap = Snapshot(100, [me], vehicles=[veh(10, "warthog", 0, occupied=True, riders=1)], mode="slayer")
        act = Action()
        b.drive(100, 1 / 30, me, snap, act, lambda a, c: c)
        return b, act

    def test_wheelman_keeps_its_warthog_at_the_trip_end(self):
        b, act = self.arrive("wheelman")
        self.assertFalse(act.action)
        self.assertLessEqual(getattr(b, "exit_until", 0.0), 100)
        self.assertIsNotNone(b.drive_to)
        self.assertNotEqual(b.drive_to, Vec(2, 0, 0))   # on to the next place

    def test_others_get_out(self):
        b, act = self.arrive("rusher")
        self.assertTrue(act.action)
        self.assertGreater(b.exit_until, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
