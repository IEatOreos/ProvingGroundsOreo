"""A sight line through a placed piece's sloped top, and shoot-through learned in a placed piece.

The owner, Pinnacle (Forge World): bots "still shoot through the side of the forge bowl in the middle of the map". The
centre dish's rim is a sloped floor (no wall bins), and Terrain._ray's floor test compares each sample with its own
cell's level only, so a nearly level line slid in under the rising slope and through the solid rim (148 of 283 lines
across the dish). Terrain._slides_under now shuts them. And every one of Pinnacle's 40 learned shoot-through cells was
inside a Forge piece: none are learned (Terrain.learn_shot_through) or used (brain/maps.py, Terrain.piece_solid) there.

Run: python tools/test_piece_slide_los.py
"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import Vec
from brain.terrain import Terrain

# a ridge across y at x = 10: its slopes rise 0.8 over 2 u (ramps, no wall bins), its bottom on the floor
RIDGE = [("metal", [-2, -4, 0, 0, -4, 0.8, 0, 4, 0.8, -2, 4, 0]),
         ("metal", [0, -4, 0.8, 2, -4, 0, 2, 4, 0, 0, 4, 0.8]),
         ("metal", [-2, -4, 0, -2, 4, 0, 2, 4, 0, 2, -4, 0])]
# a waist-high wall piece across y at x = 10, 0.5 thick, heights 0.3-0.9 (a railing's height: the case learning is for)
WALL = [("metal", [-0.25, -4, 0.3, -0.25, 4, 0.3, -0.25, 4, 0.9, -0.25, -4, 0.9]),
        ("metal", [0.25, -4, 0.3, 0.25, -4, 0.9, 0.25, 4, 0.9, 0.25, 4, 0.3]),
        ("metal", [-0.25, -4, 0.9, -0.25, 4, 0.9, 0.25, 4, 0.9, 0.25, -4, 0.9]),
        ("metal", [-0.25, -4, 0.3, 0.25, -4, 0.3, 0.25, 4, 0.3, -0.25, 4, 0.3])]
IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def flat():
    """A 20 x 8 u level (0.25 u cells), floor z 0."""
    T = Terrain.__new__(Terrain)
    T.x0 = T.y0 = 0.0
    T.cell, T.h, T.w = 0.25, 32, 80
    T.window = (0.0, 0.0, 20.0, 8.0)
    T.wall_z0, T.wall_bin = -1.0, 0.125
    T.walls = np.zeros((32, 80, 1), np.uint64)
    T.floors = np.zeros((1, 32, 80), np.float32)
    T.top = np.zeros((32, 80), np.float32)
    T.low = np.zeros((32, 80), np.float32)
    T.slope = T.piece = None
    T.blocked = set()
    return T


def with_piece(faces):
    T = flat()
    T.add_faces([((10.0, 4.0, 0.0), IDENT, faces)])
    return T


class SlideUnderPieceTests(unittest.TestCase):
    def test_a_line_through_the_ridge_is_shut(self):
        T = with_piece(RIDGE)
        a, b = Vec(4.0, 4.1, 0.0), Vec(16.0, 4.1, 0.0)     # eye 0.62 to chest 0.4 / head 0.62: under the 0.8 ridge
        self.assertFalse(T.los(a, b))
        self.assertFalse(T.shot_los(a, b))
        saved = Terrain._slides_under                      # (the bug: without the slide test it read open)
        try:
            Terrain._slides_under = lambda *x, **k: None
            self.assertTrue(T.los(a, b))
        finally:
            Terrain._slides_under = saved

    def test_a_line_over_the_ridge_stays_open(self):
        T = with_piece(RIDGE)
        self.assertTrue(T.los(Vec(4.0, 4.1, 1.0), Vec(16.0, 4.1, 1.0)))
        self.assertTrue(T.los(Vec(9.0, 4.1, 0.4), Vec(16.0, 4.1, 0.0)))   # from up the slope, down the far side

    def test_no_piece_no_change(self):
        T = flat()
        self.assertTrue(T.los(Vec(4.0, 4.1, 0.0), Vec(16.0, 4.1, 0.0)))


class LearnInPieceTests(unittest.TestCase):
    def learn3(self, T):
        T.shot_los = lambda a, b: False               # (the round's line reads blocked: the case learning is for)
        a, b = Vec(4.0, 4.1, 0.0), Vec(16.0, 4.1, 0.0)
        return [c for _ in range(3) for c in T.learn_shot_through(a, b)]

    def test_a_piece_wall_is_never_learned_shoot_through(self):
        T = with_piece(WALL)
        self.assertEqual(self.learn3(T), [])
        self.assertTrue(T.piece_solid(10.0, 4.0, 0.5, 1.0))
        self.assertFalse(T.piece_solid(5.0, 4.0, 0.5, 1.0))
        self.assertFalse(T.piece_solid(10.0, 4.0, 2.0, 2.5))

    def test_the_same_wall_in_the_level_is_learned_as_before(self):
        T = flat()
        for bit in range(int((0.3 + 1.0) / 0.125), int((0.9 + 1.0) / 0.125) + 1):
            T.walls[:, 40, 0] |= np.uint64(1) << np.uint64(bit)
        learned = self.learn3(T)
        self.assertTrue(learned)
        self.assertFalse(any(T.piece_solid(c[0] / 4, c[1] / 4, c[2], c[3]) for c in learned))


if __name__ == "__main__":
    unittest.main()
