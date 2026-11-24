"""(custom, Nov 23) tools/field_pool.py: route fields worked out in helper processes (the owner: "Do 1 and 4 through
completion"). Real helpers on a small grid: their fields are the brain's own, a weight change makes them take the graph
again, a stand-in comes from a goal just by it, and a helper gone leaves the searches to the brain."""
import math
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import field_pool                                     # noqa: E402
from brain.core import Vec                            # noqa: E402
from brain.terrain import FieldCache, keep_field      # noqa: E402

H, W = 12, 12


def grid():
    rows, cols, wts = [], [], []
    for j in range(H):
        for i in range(W):
            k = j * W + i
            for dj, di in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                if 0 <= j + dj < H and 0 <= i + di < W:
                    rows.append(k)
                    cols.append((j + dj) * W + i + di)
                    wts.append(1.0)
    g = csr_matrix((wts, (rows, cols)), shape=(H * W, H * W))
    return g


def terrain():
    g = grid()
    return SimpleNamespace(L=1, nh=H, nw=W, graph_to=g, _fields=FieldCache())


def wait_for(pool, cache, ckey, keep, t=10.0):
    end = time.time() + t
    while time.time() < end:
        f = pool.wait(cache, ckey, keep, timeout=0.5)
        if f is not None:
            return f
        pool.drain(keep)
        if ckey in cache:
            return cache[ckey]
    return None


class Helpers(unittest.TestCase):
    def setUp(self):
        self.T = terrain()
        self.pool = field_pool.Pool(workers=2, slots=6)
        self.assertTrue(self.pool.bind(self.T))

    def tearDown(self):
        self.pool.close()

    def test_their_field_is_the_brains(self):
        cache = self.T._fields
        self.pool.submit(cache, (0, 4, 4), "walk", 4 * W + 4, None, Vec(4, 4, 0))
        f = wait_for(self.pool, cache, (0, 4, 4), keep_field)
        self.assertIsNotNone(f)
        want = dijkstra(self.T.graph_to, directed=True, indices=4 * W + 4).reshape(1, H, W)
        np.testing.assert_allclose(f, want)
        limited = (("limit", 3.0), 0, 0, 0)
        self.pool.submit(cache, limited, "walk", 0, 3.0, Vec(0, 0, 0))
        f = wait_for(self.pool, cache, limited, keep_field)
        self.assertEqual(float(f[0, 0, 2]), 2.0)
        self.assertTrue(math.isinf(float(f[0, 6, 6])))           # (past its limit: not searched)

    def test_a_weight_change_is_taken(self):
        cache = self.T._fields
        self.T.graph_to.data[:] = 2.0                             # (every step dearer: a learned spot's kind)
        cache.clear()                                             # (as the nav does: FieldCache.gen)
        self.pool.submit(cache, (0, 0, 0), "walk", 0, None, Vec(0, 0, 0))
        f = wait_for(self.pool, cache, (0, 0, 0), keep_field)
        self.assertEqual(float(f[0, 0, 3]), 6.0)

    def test_a_stand_in_by_it(self):
        cache = self.T._fields
        keep_field(cache, (0, 4, 4), np.zeros((1, H, W)))
        self.pool.note(cache, (0, 4, 4), Vec(4, 4, 0))
        self.assertIsNotNone(self.pool.near(cache, (0, 4, 5), Vec(5, 4, 0)))        # 1 u off
        self.assertIsNone(self.pool.near(cache, (0, 4, 8), Vec(8, 4, 0)))           # 4 u off
        self.assertIsNone(self.pool.near(cache, ("limit", 10.0, 0, 4, 5), Vec(5, 4, 0)))   # another search
        f = self.pool.lookup(cache, (0, 4, 5), "walk", 4 * W + 5, None, Vec(5, 4, 0), keep_field)
        self.assertIs(f, cache[(0, 4, 4)])                        # (stood in, the exact one asked for)
        self.assertIn((id(cache), (0, 4, 5)), self.pool.inflight)

    def test_a_fixed_target_kept_and_redone_on_a_weight_change(self):
        """("And then 3 afterwards") a pinned field stays out of the cache's churn, and a graph changed is worked out
        again for it."""
        cache = self.T._fields
        self.pool.pin(cache, (0, 0, 0), "walk", 0, None, Vec(0, 0, 0))
        end = time.time() + 10
        while (id(cache), (0, 0, 0)) not in self.pool.pinned and time.time() < end:
            self.pool.drain(keep_field)
            time.sleep(0.01)
        f = self.pool.pinned[(id(cache), (0, 0, 0))]
        self.assertEqual(float(f[0, 0, 3]), 3.0)
        self.assertNotIn((0, 0, 0), cache)                       # (kept apart: no LRU drops it)
        self.T.graph_to.data[:] = 2.0
        cache.clear()
        self.pool.drain(keep_field)
        self.pool._dispatch()
        end = time.time() + 10
        while time.time() < end:
            self.pool.drain(keep_field)
            g = self.pool.pinned.get((id(cache), (0, 0, 0)))
            if g is not None and float(g[0, 0, 3]) == 6.0:
                break
            time.sleep(0.01)
        self.assertEqual(float(self.pool.pinned[(id(cache), (0, 0, 0))][0, 0, 3]), 6.0)

    def test_a_helper_gone_leaves_it_to_the_brain(self):
        for h in self.pool.helpers:
            h.proc.kill()
        time.sleep(0.5)
        cache = self.T._fields
        self.pool.drain(keep_field)
        self.assertIsNotNone(self.pool.broken)
        self.assertIsNone(self.pool.lookup(cache, (0, 1, 1), "walk", W + 1, None, Vec(1, 1, 0), keep_field))


class Cache(unittest.TestCase):
    def test_clear_counts(self):
        c = FieldCache()
        c[1] = 2
        c.clear()
        c.clear()
        self.assertEqual((c.gen, len(c)), (2, 0))


if __name__ == "__main__":
    unittest.main()
