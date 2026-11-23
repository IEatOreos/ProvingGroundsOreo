"""(custom, Nov 23) A tank left empty once its role is filled gets a driver (brain/director.py crew_orders). The owner's
Forge World report "Bots dont get called to the wraith?", "They get called to the wraith just not at the beginning of
the match": the team's Revenant (anti-vehicle too) taken at 9 s left the Wraith's only role filled, and both Wraiths
stood empty until 65 and 91 s (20261123-155411)."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import profiles                                 # noqa: E402
from brain.bot import Bot, Order                           # noqa: E402
from brain.core import PlayerState, Snapshot, Vec          # noqa: E402
from brain.director import Director                        # noqa: E402


def bot(i, tier, mapdata):
    b = Bot(i, 0, profiles.make_profile(tier, "rusher", random.Random(i)), mapdata)
    b.order = Order("mid", Vec(80, 0, 0))
    b.set_order = lambda order, b=b, **kw: setattr(b, "order", order)
    return b


def scene(vehicles_, tiers=("strong",), dists=None):
    """Team 0's bots on foot at (dists[k], 0, 0); vehicles_ [(handle, kind, x, occupied)]."""
    mapdata = dict(name="reach_forge_halo", flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)})
    bots = [bot(i, t, mapdata) for i, t in enumerate(tiers)]
    dists = dists or [3.0 + 2.0 * i for i in range(len(tiers))]
    players = {b.id: PlayerState(b.id, 0, f"b{b.id}", Vec(dists[k], 0, 0)) for k, b in enumerate(bots)}
    vs = [dict(handle=h, kind=k, pos=(x, 0, 0), occupied=occ, team=0, riders=1 if occ else 0, fwd=(1, 0, 0))
          for h, k, x, occ in vehicles_]
    snap = Snapshot(100, list(players.values()), vehicles=vs, mode="slayer")
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map, d.bots, d.roles = mapdata, {b.id: b for b in bots}, {b.id: "mid" for b in bots}
    d.event = lambda *args: None
    d.enemy_vehicles = lambda *args: []
    return d, bots, players, snap


class TankCrew(unittest.TestCase):
    def test_the_wraith_driven_though_the_revenant_fills_its_role(self):
        d, bots, players, snap = scene([(10, "revenant", -5, True), (11, "wraith", 15, False)])
        d.crew_orders(100, snap, players, bots)
        self.assertEqual((bots[0].order.role, bots[0].order.target), ("drive", 11))

    def test_both_when_both_are_empty(self):
        d, bots, players, snap = scene([(10, "revenant", 0, False), (11, "wraith", 10, False)],
                                       tiers=("strong", "strong"), dists=[1.0, 9.0])
        d.crew_orders(100, snap, players, bots)
        self.assertEqual({b.order.target for b in bots if b.order.role == "drive"}, {10, 11})

    def test_a_second_revenant_left_as_before(self):
        d, bots, players, snap = scene([(10, "revenant", -5, True), (11, "revenant", 15, False)])
        d.crew_orders(100, snap, players, bots)
        self.assertNotEqual(bots[0].order.role, "drive")

    def test_not_beyond_the_crew_reach(self):
        d, bots, players, snap = scene([(10, "revenant", -5, True), (11, "wraith", Director.CREW_REACH + 10, False)],
                                       dists=[0.0])
        d.crew_orders(100, snap, players, bots)
        self.assertNotEqual(bots[0].order.role, "drive")

    def test_a_scorpion_too(self):
        d, bots, players, snap = scene([(10, "revenant", -5, True), (11, "scorpion", 15, False)])
        d.crew_orders(100, snap, players, bots)
        self.assertEqual((bots[0].order.role, bots[0].order.target), ("drive", 11))


if __name__ == "__main__":
    unittest.main()
