"""(custom, Nov 24) No learned shoot-through spot in a solid wall standing on its floor (Terrain.solid_run / solid_slot):
the owner's report 20261124-194946, Boneyard, "Bots are trying to shoot through boneyards walls" (7 learned cells at the
foot of the wall he stood behind, Camper25's 10 rounds at PacMan through it, none landed); "As long as it only blocks
small holes and not the larger holes in railing and stuff": railings and a gap in a wall keep theirs.

Run: python tools/test_learn_solid_wall.py
"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.core import Vec                                          # noqa: E402
from test_learn_shot_through import grid                            # noqa: E402


def on_floor(*runs):
    """test_learn_shot_through's 10 x 10 u map with its floor at z 0 and the wall across x = 5 u in runs [(lo, hi)]."""
    T = grid(*runs[0])
    for lo, hi in runs[1:]:
        for b in range(int((lo - T.wall_z0) / T.wall_bin), int((hi - T.wall_z0) / T.wall_bin) + 1):
            T.walls[:, 20, 0] |= np.uint64(1) << np.uint64(b)
    T.floors[0] = 0.0
    return T


def learn3(T):
    a, b = Vec(1.0, 5.0, 0.0), Vec(9.0, 5.0, 0.0)
    return [c for _ in range(3) for c in T.learn_shot_through(a, b)]


class SolidWallTests(unittest.TestCase):
    def test_a_wall_standing_on_its_floor_is_never_learned_shoot_through(self):
        self.assertEqual(learn3(on_floor((0.0, 2.5))), [])          # (Nov 9's rule alone learned it: no wall 0.6 under)

    def test_a_railing_on_its_floor_is_learned_as_before(self):
        learned = learn3(on_floor((0.0, 0.8)))
        self.assertTrue(learned)
        self.assertTrue(all(c[4] == 0 for c in learned))

    def test_a_gap_in_the_wall_over_the_line_keeps_its_holes(self):
        self.assertTrue(learn3(on_floor((0.0, 0.9), (1.5, 2.5))))  # (a sill, an opening, a lintel: not solid)

    def test_a_file_spot_in_a_solid_wall_is_a_small_hole(self):
        T = on_floor((0.0, 2.5))
        self.assertTrue(T.solid_slot(5.0, 5.0, 0.0, 0.5))
        self.assertTrue(T.solid_slot(5.0, 5.0, 0.5, 1.0))

    def test_a_file_spot_in_a_railing_or_a_gap_is_not(self):
        self.assertFalse(on_floor((0.0, 0.8)).solid_slot(5.0, 5.0, 0.5, 1.0))
        self.assertFalse(on_floor((0.0, 0.9), (1.5, 2.5)).solid_slot(5.0, 5.0, 0.5, 1.0))
        self.assertFalse(on_floor((0.0, 2.5)).solid_slot(3.0, 5.0, 0.5, 1.0))    # (no wall there at all)


if __name__ == "__main__":
    unittest.main()
