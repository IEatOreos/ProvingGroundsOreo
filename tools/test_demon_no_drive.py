"""Demons do not drive Warthogs or Mongooses (they ride the guns); Normal and Heroic are the team's drivers
(custom, Nov 7)."""
import random
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import profiles, vehicles                       # noqa: E402
from brain.bot import Bot, Order                           # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from brain.director import Director                        # noqa: E402


def bot(i, tier, mapdata, extra=None):
    prof = profiles.make_profile(tier, "rusher", random.Random(i))
    if extra is not None:
        prof = replace(prof, extra=extra)
    b = Bot(i, 0, prof, mapdata)
    b.order = Order("mid", Vec(80, 0, 0))
    b.set_order = lambda order, b=b, **kw: setattr(b, "order", order)
    return b


def crew_scene(tiers, kind="warthog", mode="slayer", dists=None):
    mapdata = dict(name="h4_test", flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)})
    bots = [bot(i, t, mapdata) for i, t in enumerate(tiers)]
    dists = dists or [3.0 + 2.0 * i for i in range(len(tiers))]
    players = {b.id: PlayerState(b.id, 0, f"b{b.id}", Vec(dists[k], 0, 0)) for k, b in enumerate(bots)}
    v = dict(handle=10, kind=kind, pos=(0, 0, 0), occupied=False, team=0, riders=0, fwd=(1, 0, 0))
    snap = Snapshot(100, list(players.values()), vehicles=[v], mode=mode)
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map, d.bots, d.roles = mapdata, {b.id: b for b in bots}, {b.id: "mid" for b in bots}
    d.event = lambda *args: None
    d.enemy_vehicles = lambda *args: []
    return d, bots, players, snap


class NoDriveRuleTests(unittest.TestCase):
    def test_which_vehicles(self):
        for name in ("warthog", "storm_warthog", "warthog_rocket", "warthog_gauss", "rwarthog", "thog", "mongoose",
                     "storm_mongoose", "gungoose"):
            self.assertTrue(vehicles.demon_no_drive(name), name)
        for name in ("ghost", "scorpion", "banshee", "wraith", "mantis", "falcon", "hornet", "elephant"):
            self.assertFalse(vehicles.demon_no_drive(name), name)

    def test_driver_priority(self):
        p = lambda t, extra=None: profiles.driver_priority(
            replace(profiles.make_profile(t, "rusher", random.Random(1)), extra=extra))
        self.assertEqual((p("average"), p("strong")), (0, 0))
        self.assertEqual((p("top"), p("top", extra={"x": 1})), (1, 1))
        self.assertEqual(p("novice"), 2)
        self.assertIsNone(p("demon"))

    def test_may_drive(self):
        mapdata = dict(name="h4_test")
        demon, heroic = bot(0, "demon", mapdata), bot(1, "strong", mapdata)
        slayer, race = SimpleNamespace(mode="slayer"), SimpleNamespace(mode="race")
        for kind in ("warthog", "mongoose", "warthog_gauss"):
            self.assertFalse(demon.may_drive(dict(kind=kind), slayer), kind)
            self.assertTrue(demon.may_drive(dict(kind=kind), race), kind)
            self.assertTrue(heroic.may_drive(dict(kind=kind), slayer), kind)
        for kind in ("ghost", "scorpion", "banshee"):
            self.assertTrue(demon.may_drive(dict(kind=kind), slayer), kind)


class DirectorDriverTests(unittest.TestCase):
    def test_heroic_drives_the_warthog_though_the_demon_is_nearer(self):
        d, bots, players, snap = crew_scene(["demon", "strong"], dists=[2.0, 12.0])
        d.crew_orders(100, snap, players, bots)
        self.assertNotEqual(bots[0].order.role, "drive")
        self.assertEqual(bots[1].order.role, "drive")
        self.assertEqual(bots[1].order.target, 10)

    def test_normal_and_heroic_before_legendary(self):
        d, bots, players, snap = crew_scene(["top", "average"], dists=[2.0, 20.0])
        d.crew_orders(100, snap, players, bots)
        self.assertEqual(bots[1].order.role, "drive")
        self.assertNotEqual(bots[0].order.role, "drive")

    def test_a_demon_alone_is_never_sent_to_a_warthog(self):
        d, bots, players, snap = crew_scene(["demon"])
        d.crew_orders(100, snap, players, bots)
        self.assertNotEqual(bots[0].order.role, "drive")

    def test_a_demon_still_drives_a_ghost(self):
        d, bots, players, snap = crew_scene(["demon"], kind="ghost")
        d.crew_orders(100, snap, players, bots)
        self.assertEqual(bots[0].order.role, "drive")

    def test_a_kept_warthog_job_is_dropped_for_a_demon(self):
        d, bots, players, snap = crew_scene(["demon"])
        d.crews = {10: (0, 99.0)}
        d.crew_orders(100, snap, players, bots)
        self.assertNotEqual(bots[0].order.role, "drive")


class SeatedDemonTests(unittest.TestCase):
    def seated(self, seat, kind="warthog", tier="demon"):
        mapdata = dict(name="h4_test", flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)})
        b = bot(0, tier, mapdata)
        b.seat, b.seat_for, b.seat_since = seat, 10, 99.0
        b.drive_to = b.order.point
        b._terrain = SimpleNamespace(vnav=lambda start, goal: goal)
        b.notes = []
        me = PlayerState(0, 0, "bot", Vec(), vehicle=10)
        v = dict(handle=10, kind=kind, pos=(0, 0, 0), occupied=True, team=0, riders=2, fwd=(1, 0, 0))
        snap = Snapshot(100, [me], vehicles=[v], mode="slayer")
        act = Action()
        b.drive(100, 1 / 30, me, snap, act, lambda a, c: c)
        return b, act

    def test_demon_at_a_warthog_wheel_gets_out(self):
        for kind in ("warthog", "mongoose"):
            b, act = self.seated("driver", kind)
            self.assertTrue(act.action, kind)
            self.assertGreater(b.exit_until, 100)
            self.assertIn("vehicle: Demon does not drive this, out", b.notes)

    def test_demon_on_the_gun_stays(self):
        b, act = self.seated("gunner")
        self.assertNotIn("vehicle: Demon does not drive this, out", b.notes)

    def test_heroic_at_the_wheel_drives(self):
        b, act = self.seated("driver", tier="strong")
        self.assertNotIn("vehicle: Demon does not drive this, out", b.notes)


if __name__ == "__main__":
    unittest.main()
