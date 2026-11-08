"""Power vehicles (custom, Nov 8; Redoubt's Wraith). A bot the director sends to a vehicle goes even with nothing else
scored (every game). Halo 4: the driver goes by rank only among bots about as near as the nearest (POWER_TIER_BAND), and a
teammate who comes near an empty power vehicle takes the job from one far off (POWER_HANDOVER)."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import profiles                                 # noqa: E402
from brain.bot import Bot, Order                           # noqa: E402
from brain.core import PlayerState, Snapshot, Vec          # noqa: E402
from brain.director import Director                        # noqa: E402
from test_h4_pickup_board import Flat                      # noqa: E402


def wraith(pos=(0.0, 0.0, 0.0), handle=10):
    return dict(handle=handle, kind="storm_wraith", pos=pos, occupied=False, team=-1, riders=0, fwd=(1, 0, 0),
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
            goal = b.decide(10.0, me, Snapshot(10.0, [me], vehicles=[wraith((30.0, 0.0, 0.0))], mode="slayer"))
            self.assertEqual(goal, ("vehicle", 10), game_map)
            self.assertEqual(list(b.last_scores), [("roam", None)])     # (nothing else was scored)


def crew_scene(tiers, dists, game_map="h4_test"):
    mapdata = dict(name=game_map, flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)})
    bots = []
    for i, t in enumerate(tiers):
        b = Bot(i, 0, profiles.make_profile(t, "rusher", random.Random(i)), mapdata)
        b.order = Order("mid", Vec(80, 0, 0))
        b.set_order = lambda order, b=b, **kw: setattr(b, "order", order)
        bots.append(b)
    players = {b.id: PlayerState(b.id, 0, f"b{b.id}", Vec(dists[k], 0, 0)) for k, b in enumerate(bots)}
    snap = Snapshot(100, list(players.values()), vehicles=[wraith()], mode="slayer")
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map, d.bots, d.roles = mapdata, {b.id: b for b in bots}, {b.id: "mid" for b in bots}
    d.event = lambda *args: None
    d.enemy_vehicles = lambda *args: []
    return d, bots, players, snap


class PickTests(unittest.TestCase):
    def driver(self, tiers, dists, game_map="h4_test"):
        d, bots, players, snap = crew_scene(tiers, dists, game_map)
        d.crew_orders(100, snap, players, bots)
        return [b.id for b in bots if b.order.role == "drive"]

    def test_halo4_a_much_nearer_heroic_drives(self):
        self.assertEqual(self.driver(["top", "strong"], [44.7, 27.3]), [1])     # (Redoubt, 312 s)

    def test_halo4_rank_still_wins_among_the_near(self):
        self.assertEqual(self.driver(["strong", "top"], [34.0, 34.8]), [1])     # (Redoubt, the start)
        self.assertEqual(self.driver(["average", "demon"], [10.0, 19.0]), [1])

    def test_reach_unchanged(self):
        self.assertEqual(self.driver(["top", "strong"], [44.7, 27.3], "reach_test"), [0])


class HandoverTests(unittest.TestCase):
    def scene(self, near_d, game_map="h4_test"):
        d, bots, players, snap = crew_scene(["top", "strong"], [40.0, 60.0], game_map)
        d.crew_orders(100, snap, players, bots)
        self.assertEqual(bots[0].order.role, "drive")             # the Legendary has the job
        for b in bots:
            b.order = Order("mid", Vec(80, 0, 0))                 # (the next role pass resets every order first)
        players[1].pos = Vec(near_d, 0, 0)                        # the Heroic respawns by it
        d.crew_orders(102, snap, players, bots)
        return [b.id for b in bots if b.order.role == "drive"]

    def test_a_teammate_by_it_takes_the_job(self):
        self.assertEqual(self.scene(5.0), [1])

    def test_not_for_one_hardly_nearer(self):
        self.assertEqual(self.scene(28.0), [0])

    def test_reach_unchanged(self):
        self.assertEqual(self.scene(5.0, "reach_test"), [0])


if __name__ == "__main__":
    unittest.main()
