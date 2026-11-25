"""(custom, Nov 24) Infection's survivors spread in groups of 3 at most, people counted (brain/director.py mode_slots,
brain/modes.py survivor_spots), at the map's haven markers, then its hot spots, then its rooms; the last 2-3 hold a room
with a single way in (last_stand_hold). The owner, live Anchor 9 with 18 players: "all the bots are standing in one
hold", "if its like 4 or more survivors find a new spot. Or even use the hot spots", "if there is only 2-3 survivors
left they try to find and area with only 1 entrance"."""
import sys
import types
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import modes  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec, dist  # noqa: E402
from brain.director import Director  # noqa: E402

HAVENS = [Vec(0, 17, 0), Vec(-8, 2, 0), Vec(6, 3, 0), Vec(0, -5, 0), Vec(9, 16, 0)]
HOLDS = [dict(pos=Vec(30, 30, 0), entrances=2, doors=[]), dict(pos=Vec(-30, 30, 0), entrances=1, doors=[]),
         dict(pos=Vec(-40, -40, 0), entrances=1, doors=[])]


def director(n_bots, people_at=()):
    d = Director.__new__(Director)
    d.team = 0
    d.map = {"points": {"mid": Vec()}, "name": "test_infection", "positions": [Vec(20, 0, 0), Vec(-20, 0, 0)]}
    d.bots = {i: None for i in range(1, n_bots + 1)}
    d.terrain = lambda: None
    d.spread = lambda point, k, ring=4.0: point          # (each slot's own spot: the point itself here)
    players = [PlayerState(i, 0, f"b{i}", Vec(0, 16, 0), weapon="shotgun") for i in d.bots]
    players += [PlayerState(100 + k, 0, f"p{k}", q, weapon="shotgun") for k, q in enumerate(people_at)]
    players += [PlayerState(200, 1, "z", Vec(50, 50, 0), weapon="sword")]
    snap = Snapshot(10.0, players, mode="infection")
    snap.obj_zones = [(z, 1.5, -1) for z in HAVENS]
    return d, snap


class SurvivorTests(unittest.TestCase):
    def setUp(self):
        self._holds = modes.holds
        modes.holds = lambda T, name, wait=False: HOLDS

    def tearDown(self):
        modes.holds = self._holds

    def test_no_spot_gets_more_than_three(self):
        d, snap = director(15)
        slots = d.mode_slots(10.0, snap, 15)
        self.assertEqual(len(slots), 15)
        per = Counter((round(q.x), round(q.y)) for _, q, _ in slots)
        self.assertLessEqual(max(per.values()), 3)
        self.assertGreaterEqual(len(per), 5)
        spots = [Vec(x, y, 0) for x, y in per]
        self.assertTrue(all(dist(a, b) >= 6.0 for a in spots for b in spots if a != b))   # (each group its own area)

    def test_haven_markers_first_then_hot_spots(self):
        d, snap = director(6)
        spots = {(round(q.x), round(q.y)) for _, q, _ in d.mode_slots(10.0, snap, 6)}
        self.assertTrue(spots <= {(round(z.x), round(z.y)) for z in HAVENS})
        d, snap = director(15)
        spots = {(round(q.x), round(q.y)) for _, q, _ in d.mode_slots(10.0, snap, 15)}
        self.assertIn((20, 0), spots)                       # (five markers' 15 places: one more group to a hot spot)

    def test_people_count_toward_a_spot(self):
        d, snap = director(5, people_at=[Vec(0, 17, 0), Vec(0.5, 17, 0)])    # (two people at the first marker)
        per = Counter((round(q.x), round(q.y)) for _, q, _ in d.mode_slots(10.0, snap, 5))
        self.assertEqual(per[(0, 17)], 1)                   # (3 there with them)

    def test_the_last_ones_take_a_single_way_in(self):
        d, snap = director(2)
        spots = {(round(q.x), round(q.y)) for _, q, _ in d.mode_slots(10.0, snap, 2)}
        self.assertEqual(spots, {(-30, 30)})                # (one way in, the nearer of the two such rooms)

    def test_last_stand_hold(self):
        self.assertEqual(modes.last_stand_hold(HOLDS, Vec(-35, -35, 0))["pos"], Vec(-40, -40, 0))
        two = [dict(pos=Vec(1, 1, 0), entrances=3), dict(pos=Vec(9, 9, 0), entrances=2)]
        self.assertEqual(modes.last_stand_hold(two, Vec())["pos"], Vec(9, 9, 0))   # (none with one: the fewest)
        self.assertIsNone(modes.last_stand_hold([], Vec()))


if __name__ == "__main__":
    unittest.main()
