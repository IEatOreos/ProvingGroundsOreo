"""(custom, Nov 23) Terrain.field_from: a walk's route field searched out only as far as the walker, the whole map's when
he lies past that or the trip is long (the owner's 8v8 Forge World matches: full fields 47% of the brain's slow passes;
on that layout 60 of 60 next steps the same, a fresh one 31.9 -> 12.7 ms)."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import Vec                     # noqa: E402
from brain.terrain import Terrain              # noqa: E402


class Stub:
    """A field per limit: finite out to `reach` u from the goal (as a limited search), the full one everywhere."""
    FIELD_NEAR_K, FIELD_NEAR_ADD, FIELD_NEAR_MAX = Terrain.FIELD_NEAR_K, Terrain.FIELD_NEAR_ADD, Terrain.FIELD_NEAR_MAX
    field_from = Terrain.field_from

    def __init__(s, path_k=1.0):
        s.calls, s.path_k = [], path_k

    def _node(s, p):
        return p

    def _field(s, goal, jump=False, human=False, safe=False, limit=None, no_tele=False, hazards=()):
        s.calls.append(limit)
        lim = math.inf if limit is None else limit
        return {Vec(x, 0, 0): (abs(x - goal.x) * s.path_k if abs(x - goal.x) * s.path_k < lim else math.inf)
                for x in range(-200, 201)}


class FieldFrom(unittest.TestCase):
    def test_a_near_walker_gets_the_short_search(self):
        T = Stub()
        f = T.field_from(Vec(10, 0, 0), Vec(0, 0, 0))
        self.assertEqual(T.calls, [40.0])                 # (2 x 10 + 20)
        self.assertEqual(f[Vec(10, 0, 0)], 10.0)

    def test_past_its_reach_the_whole_map(self):
        T = Stub(path_k=5.0)                              # (a way round: 5 times the straight line)
        f = T.field_from(Vec(10, 0, 0), Vec(0, 0, 0))
        self.assertEqual(T.calls, [40.0, None])
        self.assertEqual(f[Vec(10, 0, 0)], 50.0)

    def test_a_long_trip_straight_to_the_whole_map(self):
        T = Stub()
        T.field_from(Vec(60, 0, 0), Vec(0, 0, 0))
        self.assertEqual(T.calls, [None])                 # (2 x 60 + 20 = 140: over FIELD_NEAR_MAX)


if __name__ == "__main__":
    unittest.main()
