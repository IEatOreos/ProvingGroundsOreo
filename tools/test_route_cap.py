"""(custom, Nov 22) The route-search cap (brain/bot.py optional_search, brain/terrain.py OPT_FIELDS): inside a tactic
that can wait (a pre-nade's doorway, a break-off's rings, cover, a guess where he went) each bot's think builds at most
OPT_FIELDS fresh route fields; past that the tactic stops, gives its default and goes on next think from the cached
fields. The bot's own walk is never capped. Live, single thinks of 400-800 ms built 15-28 fresh fields each."""
import random
import sys
import types
import unittest
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as B  # noqa: E402
from brain.core import Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402
from brain.terrain import NAV_CELL, OPT_FIELDS, FieldBudget, Terrain, opt_state  # noqa: E402

N = 12


def grid():
    """A flat N x N nav grid, one floor at 0, every neighbour linked at its cell's length."""
    T = Terrain.__new__(Terrain)
    T.x0 = T.y0 = 0.0
    T.L, T.nh, T.nw = 1, N, N
    T.lz = np.zeros((1, N, N), np.float32)
    T.lwalk = np.ones((1, N, N), bool)
    rows, cols = [], []
    for j in range(N):
        for i in range(N):
            for dj, di in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                if 0 <= j + dj < N and 0 <= i + di < N:
                    rows.append(j * N + i)
                    cols.append((j + dj) * N + i + di)
    T.graph_to = csr_matrix((np.full(len(rows), NAV_CELL), (rows, cols)), shape=(N * N, N * N))
    T._fields, T._hfields, T._jfields = {}, {}, {}
    return T


def at(i, j):
    return Vec((i + 0.5) * NAV_CELL, (j + 0.5) * NAV_CELL, 0.0)


def bot(T):
    b = B.Bot(0, 0, make_profile("noble", "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    b.notes = []
    b._terrain = T
    return b


class Tactics:
    """Stand-ins for capped tactics: fields to goals two cells apart (one field each), and an `except Exception` round
    each as the real ones have."""

    @B.optional_search("waited")
    def far(s, goals):
        T = s.T()
        got = []
        for g in goals:
            try:
                got.append(float(T._field(g)[0, 0, 0]))
            except Exception:
                got.append(None)
        return got

    @B.optional_search(None)
    def outer(s, goals):
        return s.far(goals)


class CapTests(unittest.TestCase):
    def setUp(self):
        self.T = grid()
        self.goals = [at(2 * k, 2 * k) for k in range(5)]        # (each its own half-unit square: five fields)

    def capped(self):
        b = bot(self.T)
        b.far = types.MethodType(Tactics.far, b)
        b.outer = types.MethodType(Tactics.outer, b)
        return b

    def test_three_fresh_fields_then_its_default(self):
        b = self.capped()
        opt_state()["left"] = OPT_FIELDS
        self.assertEqual(b.far(self.goals), "waited")
        self.assertEqual(len(self.T._fields), OPT_FIELDS)        # (the three built are kept)
        self.assertEqual(b.capped, 1)
        self.assertEqual(opt_state()["depth"], 0)

    def test_next_think_goes_on_from_the_kept_fields(self):
        b = self.capped()
        opt_state()["left"] = OPT_FIELDS
        b.far(self.goals)
        opt_state()["left"] = OPT_FIELDS                             # (Bot.think's reset)
        got = b.far(self.goals)
        self.assertEqual(len(got), 5)
        self.assertTrue(all(v is not None for v in got))         # (not swallowed as a failed search)

    def test_the_walk_is_never_capped(self):
        opt_state()["left"] = 0
        for g in self.goals:
            self.T._field(g)                                     # (outside a capped tactic: nav, the director)
        self.assertEqual(len(self.T._fields), 5)

    def test_only_the_outermost_catches(self):
        b = self.capped()
        opt_state()["left"] = 1
        self.assertIsNone(b.outer(self.goals))                   # (the outer default, not "waited" handed up)
        self.assertEqual(opt_state()["depth"], 0)

    def test_think_resets_the_count(self):
        b = bot(self.T)
        opt_state()["left"] = 0
        snap = types.SimpleNamespace(player=lambda i: None)
        try:
            b.think(1.0, 0.03, snap, None, None, None)
        except Exception:
            pass                                                 # (only the reset at its start matters here)
        # (custom, Nov 23) its tier's count (brain/bot.py tier_budget: this Noble's TOP_OPT_FIELDS, everyone else's
        # OPT_FIELDS on time)
        self.assertEqual(opt_state()["left"], B.tier_budget(b.p, False)[0])
        self.assertEqual(B.tier_budget(make_profile("top", "rusher", random.Random(3)), False)[0], OPT_FIELDS)

    def test_cover_not_kept_as_none_when_cut(self):
        b = bot(self.T)
        calls = []

        def hidden(me, threats):
            calls.append(1)
            if len(calls) == 1:
                raise FieldBudget()
            return Vec(1, 1, 0)
        b.hidden_spot = hidden
        me = types.SimpleNamespace(pos=Vec(0, 0, 0))
        opt_state()["left"] = OPT_FIELDS
        self.assertIsNone(b.los_cover(me, [Vec(5, 5, 0)]))
        self.assertEqual(b.los_cover(me, [Vec(5, 5, 0)]), Vec(1, 1, 0))     # (searched again, not the cut's None)

    def test_a_cut_prenade_looks_again_next_think(self):
        b = bot(self.T)
        b.prenade_next = 99.0
        self.assertFalse(B.Bot.prenade_later(b, 5.0))
        self.assertEqual(b.prenade_next, 5.0)


if __name__ == "__main__":
    unittest.main()
