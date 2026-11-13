"""Tanks on their own ground and wedge marks for every vehicle (custom, Nov 13: "Bots dont advance the map with a
scorpion", Forge World 20261112-213825: two Scorpions 2.5 minutes each in their own base's way in, wedged, backing
off 1.2 s and in again). brain/terrain.py use_vground, vwedge; brain/bot.py drive's tank back-off."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

from brain import maps  # noqa: E402
from brain.core import Vec  # noqa: E402

_T = {}


def fresh():
    """A Blood Gulch terrain of our own (not the shared cache: the marks stay in it)."""
    if "T" not in _T:
        m = maps.get_map("bloodgulch")
        _T["T"] = maps._build(m, None)
    return _T["T"]


def open_spot(T, far=8.0):
    """A cell of the car ground with open ground 8 u east (drive_clear), its centre."""
    T.use_vground(False)
    T.vnav(Vec(0, 0, 0), Vec(50, 50, 0))
    ls, js, is_ = np.nonzero(T.vroomy)
    order = np.argsort(np.abs(js - js.mean()) + np.abs(is_ - is_.mean()))
    for k in order[:4000:7]:
        p = T._center(int(ls[k]), int(js[k]), int(is_[k]))
        if T.drive_clear(p, 0.0, far) >= far and T.drive_clear(p, 0.0, far, big=True) >= far:
            return p
    raise AssertionError("no open spot")


class GroundTests(unittest.TestCase):
    def test_tank_ground_is_smaller_and_inside_the_cars(self):
        T = fresh()
        T.use_vground(False)
        T.vnav(Vec(0, 0, 0), Vec(50, 50, 0))
        car = T.vroomy.copy()
        T.vnav(Vec(0, 0, 0), Vec(50, 50, 0), big=True)
        tank = T.vroomy.copy()
        self.assertLess(int(tank.sum()), int(car.sum()))
        self.assertFalse((tank & ~car).any())
        T.vnav(Vec(0, 0, 0), Vec(50, 50, 0))                 # back to the car's: its own, untouched
        self.assertTrue((T.vroomy == car).all())


class WedgeTests(unittest.TestCase):
    def test_a_wedge_is_a_wall_ahead_for_every_size_and_survives_a_rebuild(self):
        T = fresh()
        p = open_spot(T)
        cost_before = T.graph_v.data.sum()
        q = T.vwedge(p, 0.0)
        self.assertIsNotNone(q)
        self.assertAlmostEqual(q.x - p.x, T.VWEDGE_AHEAD)
        for big in (False, True):
            d = T.drive_clear(p, 0.0, 8.0, big=big)
            self.assertLess(d, T.VWEDGE_AHEAD)               # the guard's look meets it
            self.assertGreaterEqual(T.drive_clear(p, math.pi, 8.0, big=big), 2.0)   # the way back stays open
        T.use_vground(False)
        self.assertGreater(T.graph_v.data.sum(), cost_before)   # into it costs more
        self.assertFalse(T.vroomy[T._node(q)])
        T._vreset()                                          # (paint, rides: built again) the mark stays
        T.vnav(Vec(0, 0, 0), Vec(50, 50, 0), big=True)
        self.assertFalse(T.vroomy[T._node(q)])
        self.assertIsNone(T.vwedge(p, 0.0))                  # (marked once)


class BlockerTests(unittest.TestCase):
    """The owner's vehicle blockers (Edit spots, maps/<map>/vehicle_blocks.json): no ground vehicle of any size in."""

    @classmethod
    def setUpClass(cls):
        m = maps.get_map("bloodgulch")
        cls.T = T = maps._build(m, None)                     # (one of our own: the blocker stays in it)
        cls.p = open_spot(T, far=12.0)
        cls.c = Vec(cls.p.x + 7.0, cls.p.y, cls.p.z)          # a blocker 7 u east of an open spot, 2.5 u round
        T.vblocks = [(cls.c, 2.5)]
        T._vreset()

    def test_off_every_size_of_ground(self):
        for big in (False, True):
            self.T.vnav(self.p, Vec(self.p.x + 40, self.p.y, self.p.z), big=big)
            self.assertFalse(self.T.vroomy[self.T._node(self.c)])

    def test_a_wall_to_the_look_ahead_but_not_from_inside(self):
        d = self.T.drive_clear(self.p, 0.0, 12.0)
        self.assertLess(d, 7.0 - 2.5 + 0.5)                  # stops at its edge
        self.assertGreaterEqual(self.T.drive_clear(self.c, math.pi, 3.0), 3.0)   # parked in it: out is open

    def test_a_route_past_it_goes_round(self):
        T, a, b = self.T, self.p, Vec(self.c.x + 6.0, self.c.y, self.c.z)
        pos = a
        for _ in range(60):
            w = T.vnav(pos, b)
            if w is None or (w - pos).flat() < 0.2:
                break
            step = min(1.0, (w - pos).flat())
            pos = pos + (w - pos) * (step / (w - pos).flat())
            self.assertGreater((pos - self.c).flat(), 2.5 - 0.3)   # (a cell's slack at its edge)

    def test_malformed_blockers_are_left_out(self):
        import json
        import os
        import tempfile
        from unittest import mock
        d = tempfile.mkdtemp(prefix="vblock_")
        os.makedirs(os.path.join(d, "m"))
        with open(os.path.join(d, "m", maps.VEHICLE_BLOCKS), "w", encoding="utf-8") as f:
            json.dump(dict(blocks=[dict(pos=[1, 2, 3], r=4), dict(pos=[1, 2], r=4), dict(pos=[1, 2, 3], r=0),
                                   dict(pos=[1, 2, 3], r=99), "junk"]), f)
        with mock.patch.object(maps, "ROOT", d):
            self.assertEqual([(b[0].x, b[1]) for b in maps.owner_vblocks("m")], [(1.0, 4.0)])
            self.assertEqual(maps.owner_vblocks("none"), [])


class BackOffTests(unittest.TestCase):
    def test_tank_back_off_is_longer(self):
        from brain.bot import TANK_BACK_S
        self.assertGreater(TANK_BACK_S, 1.2)


if __name__ == "__main__":
    unittest.main()
