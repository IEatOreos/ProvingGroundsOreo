"""Power vehicles (custom, Nov 8; Redoubt's Wraith; the owner: Legendary and Demon go for power vehicles, over power
weapons and gun seats). A bot the director sends to a vehicle goes even with nothing else scored (every game). Fixed
Legendary and Demon are sent first by rank; one on a weapon run or riding a gun or a passenger seat is called too (its run
dropped, it gets out). Halo 4: a teammate ranked as high who comes near an empty power vehicle takes the job from one far
off (POWER_HANDOVER)."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import profiles                                 # noqa: E402
from brain.bot import Bot, Order                           # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from brain.director import Director                        # noqa: E402
from test_h4_pickup_board import Flat                      # noqa: E402


def vehicle(kind="storm_wraith", pos=(0.0, 0.0, 0.0), handle=10, occupied=False, team=-1):
    return dict(handle=handle, kind=kind, pos=pos, occupied=occupied, team=team, riders=int(occupied), fwd=(1, 0, 0),
                up=(0, 0, 1))


class DecideTests(unittest.TestCase):
    def test_a_called_driver_goes_with_nothing_else_scored(self):
        for game_map in ("h4_test", "reach_test"):
            mapdata = dict(name=game_map, flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)},
                           holds={0: [Vec(90, 0, 0)], 1: [Vec(190, 0, 0)]}, items=[])
            b = Bot(0, 0, profiles.make_profile("top", "rusher", random.Random(3)), mapdata, random.Random(5))
            b.order, b.notes = Order("drive", Vec(30, 0, 0), target=10), []
            b._terrain = Flat()
            b.T = lambda b=b: b._terrain
            me = PlayerState(0, 0, "me", Vec(0, 0, 0), weapon="battle_rifle", weapons=["battle_rifle"])
            goal = b.decide(10.0, me, Snapshot(10.0, [me], vehicles=[vehicle(pos=(30.0, 0.0, 0.0))], mode="slayer"))
            self.assertEqual(goal, ("vehicle", 10), game_map)
            self.assertEqual(list(b.last_scores), [("roam", None)])     # (nothing else was scored)


def scene(tiers, dists, game_map="h4_test", vehicles=None):
    mapdata = dict(name=game_map, flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)}, items=[])
    bots = []
    for i, t in enumerate(tiers):
        b = Bot(i, 0, profiles.make_profile(t, "rusher", random.Random(i)), mapdata)
        b.order = Order("mid", Vec(80, 0, 0))
        b.set_order = lambda order, b=b, **kw: setattr(b, "order", order)
        b.urgent = lambda *a: False
        b.pressing = lambda *a: False
        bots.append(b)
    players = {b.id: PlayerState(b.id, 0, f"b{b.id}", Vec(dists[k], 0, 0)) for k, b in enumerate(bots)}
    snap = Snapshot(100, list(players.values()), vehicles=vehicles or [vehicle()], mode="slayer")
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map, d.bots, d.roles, d.item_up = mapdata, {b.id: b for b in bots}, {b.id: "mid" for b in bots}, {}
    d.event = lambda *args: None
    d.enemy_vehicles = lambda *args: []
    return d, bots, players, snap


def drivers(bots):
    return [b.id for b in bots if b.order.role == "drive"]


class PickTests(unittest.TestCase):
    def test_legendary_first_by_rank(self):
        for game_map in ("h4_test", "reach_test"):
            d, bots, players, snap = scene(["top", "strong"], [44.7, 27.3], game_map)     # (Redoubt, 312 s)
            d.crew_orders(100, snap, players, bots)
            self.assertEqual(drivers(bots), [0], game_map)
        d, bots, players, snap = scene(["average", "demon"], [10.0, 40.0])
        d.crew_orders(100, snap, players, bots)
        self.assertEqual(drivers(bots), [1])

    def test_a_weapon_run_gives_way_to_a_power_vehicle(self):
        for tier in ("top", "demon"):
            d, bots, players, snap = scene([tier, "strong"], [30.0, 20.0])
            bots[0].fetch = (Vec(50, 0, 0), "rockets", 200.0, None)
            d.crew_orders(100, snap, players, bots)
            self.assertEqual(drivers(bots), [0], tier)
            self.assertIsNone(bots[0].fetch, tier)

    def test_not_for_a_gun_warthog(self):
        d, bots, players, snap = scene(["top", "strong"], [30.0, 20.0], vehicles=[vehicle("warthog_gauss")])
        bots[0].fetch = (Vec(50, 0, 0), "rockets", 200.0, None)
        d.crew_orders(100, snap, players, bots)
        self.assertIsNotNone(bots[0].fetch)                        # (Normal and Heroic drive the gun Warthogs)

    def test_out_of_a_gun_seat(self):
        for tier, called in (("top", True), ("demon", True), ("strong", False)):
            ride = vehicle("storm_warthog", pos=(20.0, 0.0, 0.0), handle=20, occupied=True, team=0)
            d, bots, players, snap = scene([tier], [20.0], vehicles=[vehicle(), ride])
            players[0].vehicle, bots[0].seat = 20, "gunner"
            d.crew_orders(100, snap, players, [], [], [b for b in bots if profiles.fixed_high(b.p)])
            self.assertEqual(drivers(bots) == [0], called, tier)


class HandoverTests(unittest.TestCase):
    def handover(self, near_tier, near_d, game_map="h4_test"):
        d, bots, players, snap = scene(["top", near_tier], [40.0, 60.0], game_map)
        d.crew_orders(100, snap, players, bots)
        self.assertEqual(drivers(bots), [0])                       # the far Legendary has the job
        for b in bots:
            b.order = Order("mid", Vec(80, 0, 0))                  # (the next role pass resets every order first)
        players[1].pos = Vec(near_d, 0, 0)                         # a teammate respawns by it
        d.crew_orders(102, snap, players, bots)
        return drivers(bots)

    def test_a_legendary_by_it_takes_the_job(self):
        self.assertEqual(self.handover("top", 5.0), [1])
        self.assertEqual(self.handover("demon", 5.0), [1])

    def test_a_heroic_by_it_does_not(self):
        self.assertEqual(self.handover("strong", 5.0), [0])

    def test_not_for_one_hardly_nearer(self):
        self.assertEqual(self.handover("top", 28.0), [0])

    def test_reach_unchanged(self):
        self.assertEqual(self.handover("top", 5.0, "reach_test"), [0])


class RunTests(unittest.TestCase):
    def test_no_weapon_run_for_the_power_vehicle_driver(self):
        d, bots, players, snap = scene(["top", "strong"], [30.0, 20.0])
        d.crew_orders(100, snap, players, bots)
        self.assertEqual(drivers(bots), [0])
        for b in bots:
            b.fetch = None
        snap.ground_weapons = [("rockets", Vec(25.0, 0.0, 0.0))]
        d.map["items"] = [dict(name="rockets", kind="weapon", value=1.0, pos=Vec(25.0, 0.0, 0.0))]
        d.power_runs(100.5, snap)
        self.assertIsNone(bots[0].fetch)
        self.assertIsNotNone(bots[1].fetch)


class SeatedBotTests(unittest.TestCase):
    def test_a_called_gunner_gets_out(self):
        mapdata = dict(name="h4_test", flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)})
        b = Bot(0, 0, profiles.make_profile("top", "rusher", random.Random(3)), mapdata)
        b.seat, b.seat_for, b.seat_since, b.notes = "gunner", 20, 90.0, []
        b.order = Order("drive", Vec(0, 0, 0), target=10)
        b._terrain = SimpleNamespace(vnav=lambda s, g: g)
        me = PlayerState(0, 0, "me", Vec(20, 0, 0), vehicle=20)
        ride = vehicle("storm_warthog", pos=(20.0, 0.0, 0.0), handle=20, occupied=True, team=0)
        act = Action()
        b.drive(100.0, 1 / 30, me, Snapshot(100, [me], vehicles=[vehicle(), ride], mode="slayer"), act,
                lambda a, c: c)
        self.assertTrue(act.action)
        self.assertGreater(b.exit_until, 100.0)
        self.assertIn("vehicle: out for the power vehicle", b.notes)


if __name__ == "__main__":
    unittest.main()
