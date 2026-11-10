"""CTF cut-offs and the carrier's emblem (custom, Nov 10, the owner: "hunt the flag carrier, but without back tracking.
Like cutting them off" and "once you pick up the flag it shows an emblem above your head ... make it to where they always
know where the flag carrier is"). Live Adrift: the hunters went back through their base to reach him on the top lane.

The director's intercept is checked on a small grid (1 u cells, walking costs its steps): a hunter goes to the first
point on his way home it beats him to, never one behind him; one bot a way; one by him still chases."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.sparse import csr_matrix

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain import director as D                                     # noqa: E402
from brain.bot import MARKER_R, Order, Perception                  # noqa: E402
from brain.core import FlagState, PlayerState, Snapshot, Vec, dist  # noqa: E402
from brain.director import Director                                 # noqa: E402
from brain.profiles import make_profile                             # noqa: E402

W, H = 80, 30                       # the grid: x 0-79, y 0-29, one floor, open
RED, BLUE = Vec(5, 15, 0), Vec(75, 15, 0)
CARRIER = 7


class Grid:
    """The terrain calls the intercept makes, on an open W x H grid of 1 u cells (four-way steps of 1 u)."""
    L, nh, nw, CELL = 1, H, W, 1.0

    def __init__(s):
        s.lz, s.lwalk = np.zeros((1, H, W)), np.ones((1, H, W), dtype=bool)
        rows, cols = [], []
        for j in range(H):
            for i in range(W):
                for dj, di in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    if 0 <= j + dj < H and 0 <= i + di < W:
                        rows.append(j * W + i)
                        cols.append((j + dj) * W + i + di)
        s.graph = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(W * H, W * H))

    def _node(s, p):
        return 0, min(max(int(round(p.y)), 0), H - 1), min(max(int(round(p.x)), 0), W - 1)

    @staticmethod
    def _center(l, j, i):
        return Vec(float(i), float(j), 0.0)


def line(a, b):
    """A way from a to b, a point a unit, as carrier_routes gives it: (point, his cost there from a)."""
    n = int(round(dist(a, b)))
    return [(a + (b - a) * (k / n), dist(a, b) * k / n) for k in range(n + 1)]


def path(*pts):
    """Legs joined, his cost running on."""
    out = line(pts[0], pts[1])
    for a, b in zip(pts[1:], pts[2:]):
        out += [(q, c + out[-1][1]) for q, c in line(a, b)[1:]]
    return out


def bot(pid, tier="strong"):
    return SimpleNamespace(id=pid, p=make_profile(tier, "rusher", random.Random(pid)))


def director(bots, routes):
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.map = dict(flags={0: RED, 1: BLUE}, returns={}, holds={0: [RED], 1: [BLUE]}, points={"mid": Vec(40, 15, 0)},
                 lanes=[], sneak={0: [], 1: []})
    d.bots = {b.id: b for b in bots}
    d._T = Grid()
    d.carrier_routes = lambda c, goal: routes
    d._cuts = {}
    return d


def snapshot(carrier_at, mates):
    players = [PlayerState(CARRIER, 1, "carrier", carrier_at, has_flag=True)]
    players += [PlayerState(pid, 0, f"bot{pid}", pos) for pid, pos in mates.items()]
    flags = {0: FlagState(0, RED, carrier_at, "carried", carrier=CARRIER), 1: FlagState(1, BLUE, BLUE)}
    return Snapshot(100, players, flags=flags, mode="ctf")


class InterceptTests(unittest.TestCase):
    def run_cuts(self, carrier_at, mates, routes, k=2, cuts=None):
        d = director([bot(pid) for pid in mates], routes)
        d._cuts = cuts or {}
        snap = snapshot(carrier_at, mates)
        return d.intercepts(snap, snap.flags[0], k)

    def made(self, route, start, spot):
        """The point of his way that spot covers (within CUT_NEAR), ahead of him, that a bot walking from start (the
        grid's four-way steps) gets in range of CUT_MARGIN_S before him; None: none."""
        walk = abs(spot.x - start.x) + abs(spot.y - start.y)
        return next((q for q, c in route if c >= D.CUT_MIN_AHEAD and dist(q, spot) <= D.CUT_NEAR + 1e-6
                     and walk + D.CUT_MARGIN_S * D.CUT_RUN <= c), None)

    def test_a_bot_ahead_of_him_cuts_him_off_ahead_never_behind(self):
        him, me = Vec(20, 15, 0), Vec(45, 5, 0)
        route = line(him, BLUE)
        cuts = self.run_cuts(him, {1: me}, [route])
        self.assertEqual(len(cuts), 1)
        q, bid = cuts[0]
        self.assertEqual(bid, 1)
        covered = self.made(route, me, q)
        self.assertIsNotNone(covered)                 # in range of his way before him, ahead of him
        self.assertGreater(covered.x, him.x + D.CUT_MIN_AHEAD - 0.01)
        self.assertLess(abs(q.x - me.x) + abs(q.y - me.y), dist(me, BLUE))   # the soonest: not off to his stand

    def test_a_bot_behind_him_gets_no_cutoff_and_chases(self):
        him = Vec(30, 15, 0)
        self.assertEqual(self.run_cuts(him, {1: Vec(10, 15, 0)}, [line(him, BLUE)]), [])

    def test_his_top_lane_and_their_bottom_floor(self):
        # Adrift's case on the grid: he runs east along the top (y 25) and comes down at x 60 to the bottom (y 5) on
        # his way home; the bot is on the bottom, under where he is. Chasing him meant walking up and back after him;
        # the cut-off is by where he comes down, which it gets in range of first. Nowhere on the top is it in time
        him, bend, down, me = Vec(30, 25, 0), Vec(60, 25, 0), Vec(60, 5, 0), Vec(32, 5, 0)
        route = path(him, bend, down, Vec(75, 5, 0))
        cuts = self.run_cuts(him, {1: me}, [route])
        self.assertEqual(len(cuts), 1)
        q = cuts[0][0]
        covered = self.made(route, me, q)
        self.assertIsNotNone(covered)
        self.assertAlmostEqual(covered.x, 60.0)       # his way down, not the top lane over it
        self.assertGreater(q.x, me.x)                 # on toward his goal, never back

    def test_one_bot_a_way(self):
        him = Vec(20, 15, 0)
        north, south = path(him, Vec(40, 27, 0), BLUE), path(him, Vec(40, 3, 0), BLUE)
        cuts = self.run_cuts(him, {1: Vec(45, 27, 0), 2: Vec(45, 3, 0)}, [north, south])
        self.assertEqual(sorted(b for _, b in cuts), [1, 2])
        by = {b: q for q, b in cuts}
        self.assertGreater(by[1].y, 15)        # each on the way by it
        self.assertLess(by[2].y, 15)

    def test_more_of_us_than_ways_spread_apart(self):
        him = Vec(20, 15, 0)
        cuts = self.run_cuts(him, {1: Vec(45, 10, 0), 2: Vec(50, 20, 0)}, [line(him, BLUE)])
        self.assertEqual(len(cuts), 2)
        self.assertGreaterEqual(dist(cuts[0][0], cuts[1][0]), D.CUT_SPREAD)

    def test_one_right_by_him_keeps_chasing(self):
        him = Vec(20, 15, 0)
        cuts = self.run_cuts(him, {1: Vec(45, 10, 0), 2: Vec(50, 20, 0), 3: Vec(14, 15, 0)}, [line(him, BLUE)], k=2)
        self.assertEqual(len(cuts), 1)           # two hunters: one cuts off, the slot left for the one behind him
        self.assertNotIn(3, [b for _, b in cuts])

    def test_nearly_home_all_chase(self):
        him = Vec(BLUE.x - D.CUT_NEAR_GOAL + 1, 15, 0)
        self.assertEqual(self.run_cuts(him, {1: Vec(74, 10, 0)}, [line(him, BLUE)]), [])

    def test_keeps_its_point_while_it_still_beats_him_there(self):
        him = Vec(20, 15, 0)
        route = line(him, BLUE)
        first = self.run_cuts(him, {1: Vec(45, 5, 0)}, [route])[0][0]
        later = Vec(first.x + 6, 15, 0)        # a point farther on, still good: kept, not swapped for the first one
        again = self.run_cuts(him, {1: Vec(45, 5, 0)}, [route], cuts={1: later})
        self.assertEqual(again[0][0], later)

    def test_role_slots_give_cutoff_slots_for_that_bot_then_hunters(self):
        him = Vec(20, 15, 0)
        d = director([bot(1), bot(2), bot(3)], [line(him, BLUE)])
        d.posture = SimpleNamespace(lead=0, state="even")
        d.score_unit, d.plan, d.rng = 1, {"stance": "balanced"}, random.Random(1)
        d.split_until, d.split, d.home_rule, d.defend_until = 1e9, False, True, 0.0
        d.defend_posts = lambda home, n: [home] * n
        snap = snapshot(him, {1: Vec(45, 5, 0), 2: Vec(5, 15, 0), 3: Vec(6, 16, 0)})
        slots = d.role_slots(100, snap, 3)
        cut = [sl for sl in slots if sl[0] == "cutoff"]
        hunt = [sl for sl in slots if sl[0] == "hunter"]
        self.assertEqual(len(cut) + len(hunt), 2)
        self.assertEqual(cut[0][2], ("bot", 1))

    def test_switch_off_all_chase(self):
        him = Vec(20, 15, 0)
        d = director([bot(1)], [line(him, BLUE)])
        old = D.CUTOFF
        try:
            D.CUTOFF = False
            d.posture = SimpleNamespace(lead=0, state="even")
            d.score_unit, d.plan, d.rng = 1, {"stance": "balanced"}, random.Random(1)
            d.split_until, d.split, d.home_rule, d.defend_until = 1e9, False, True, 0.0
            slots = d.role_slots(100, snapshot(him, {1: Vec(45, 5, 0)}), 2)
        finally:
            D.CUTOFF = old
        self.assertFalse(any(sl[0] == "cutoff" for sl in slots))


class MarkerTests(unittest.TestCase):
    """The emblem over our flag's carrier: an exact belief behind walls, never a sighting."""

    def update(self, carrier_at, far=False, state="carried"):
        per = Perception(make_profile("strong", "rusher", random.Random(1)), random.Random(1))
        per.marker_far = far
        me = PlayerState(1, 0, "me", Vec(0, 0, 0), yaw=0.0, tracker=False)
        him = PlayerState(CARRIER, 1, "him", carrier_at, vel=Vec(2, 0, 0), has_flag=state == "carried")
        flags = {0: FlagState(0, RED, carrier_at, state, carrier=CARRIER if state == "carried" else -1),
                 1: FlagState(1, BLUE, BLUE)}
        snap = Snapshot(100, [me, him], flags=flags, mode="ctf")
        per.update(100.0, me, snap, lambda a, b: False, [])      # (a wall between: never in view)
        return per.beliefs.get(CARRIER)

    def test_behind_a_wall_within_range_he_is_known_exactly(self):
        b = self.update(Vec(0, 20, 0))
        self.assertIsNotNone(b)
        self.assertEqual(b.source, "marker")
        self.assertFalse(b.seen)                 # known, not seen: no shot, no reaction through the wall
        self.assertEqual(b.pos, Vec(0, 20, 0))

    def test_far_off_only_for_its_hunters(self):
        self.assertIsNone(self.update(Vec(0, MARKER_R + 20, 0)))
        self.assertEqual(self.update(Vec(0, MARKER_R + 20, 0), far=True).source, "marker")

    def test_no_emblem_when_our_flag_is_not_carried(self):
        self.assertIsNone(self.update(Vec(0, 20, 0), state="dropped"))


class OrderTests(unittest.TestCase):
    def test_cutoff_is_an_order(self):
        self.assertEqual(Order("cutoff", Vec(1, 2, 3)).role, "cutoff")


if __name__ == "__main__":
    unittest.main()
