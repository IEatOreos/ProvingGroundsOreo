"""(custom, Nov 24; our own version of upstream 0.3.0's idea, note #40) The vehicle grounds rebuilt off the pass
(brain/terrain.py VNAV_LATER, Terrain._vreset, _vready, _vfresh, _vbuild_job): with rides, paint or out of bounds
changed mid-match, bots drive on the old ground while the new one is built on a thread of its own, and it goes in whole;
both sizes (car, tank) with their own grounds and the wedge marks, one rebuild at a time, at a pass boundary when the
bots think on threads."""
import os
import pickle
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import terrain as termod  # noqa: E402
from brain.core import Vec  # noqa: E402
from brain.terrain import Terrain  # noqa: E402

N = 120                     # cells a side (0.25 u: a 30 u square)
A, B = Vec(5.0, 5.0, 0.0), Vec(25.0, 25.0, 0.0)


def level(path):
    """Flat floor at 0, walled round its edge and by a 3 u pillar in the middle (no floor there, its top 3 u up)."""
    floors, top = np.full((1, N, N), 0.0), np.zeros((N, N))
    solid = np.zeros((N, N), bool)
    solid[:2, :] = solid[-2:, :] = solid[:, :2] = solid[:, -2:] = True
    solid[54:66, 54:66] = True
    floors[0][solid], top[solid] = np.nan, 3.0
    np.savez(path, top=top, low=np.zeros((N, N)), floors=floors, walls=np.zeros((N, N, 1), np.uint64), wall_z0=-4.0,
             wall_bin=0.25, x0=0.0, y0=0.0, cell=0.25)


class Later(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.npz = os.path.join(self.tmp.name, "heightmap.npz")
        level(self.npz)
        self.T = Terrain(self.npz, [])
        self.saved = termod.VNAV_LATER, termod.THREADS, termod._PASS["seq"]
        termod.VNAV_LATER = True
        self.gate = None
        self.orig = Terrain._build_vnav

    def tearDown(self):
        if self.gate is not None:
            self.gate.set()
        Terrain._build_vnav = self.orig
        job = termod._VJOBS.get(self.T)
        if job is not None:
            job["thread"].join(5)
        termod.VNAV_LATER, termod.THREADS, termod._PASS["seq"] = self.saved
        self.tmp.cleanup()

    def hold(self):
        """The background builds wait on a gate (the pass meanwhile: "while it is built")."""
        self.gate = gate = threading.Event()
        orig = self.orig

        def slow(s):
            gate.wait(5)
            return orig(s)
        Terrain._build_vnav = slow

    def finish(self):
        if self.gate is not None:
            self.gate.set()
        job = termod._VJOBS.get(self.T)
        self.assertIsNotNone(job)
        job["thread"].join(5)
        self.assertTrue(job["done"])

    def drive(self, big=False):
        self.T.vnav(A, B, big=big)
        return self.T.graph_v

    def test_off_the_next_drive_builds_it_in_the_pass_as_before(self):
        termod.VNAV_LATER = False
        g = self.drive()
        self.T._vreset()
        self.assertNotIn("graph_v", self.T.__dict__)
        self.assertIsNot(self.drive(), g)
        self.assertIsNone(termod._VJOBS.get(self.T))

    def test_the_old_ground_is_driven_on_until_the_new_one_goes_in_whole(self):
        g = self.drive()
        self.hold()
        self.T._vreset()
        self.assertIs(self.drive(), g)                       # (the job started: no build in the pass)
        self.assertIsNotNone(termod._VJOBS.get(self.T))
        self.assertIs(self.drive(), g)
        self.finish()
        new = self.drive()
        self.assertIsNot(new, g)
        self.assertEqual(new.nnz, g.nnz)
        self.assertIsNone(termod._VJOBS.get(self.T))
        self.assertFalse(self.T.__dict__.get("_vstale"))
        self.assertIs(self.drive(), new)                     # (once: no rebuild without a change)

    def test_both_sizes_one_rebuild_at_a_time(self):
        car, tank = self.drive(), self.drive(big=True)
        self.assertLess(tank.nnz, car.nnz)
        self.hold()
        self.T._vreset()
        self.assertEqual(self.T._vstale, {"car", "tank"})
        self.assertIs(self.drive(big=True), tank)            # the tank's rebuild starts
        self.assertEqual(termod._VJOBS[self.T]["size"], "tank")
        self.assertIs(self.drive(), car)                     # the car waits its turn: its old ground
        self.assertEqual(termod._VJOBS[self.T]["size"], "tank")
        self.finish()
        self.assertIs(self.drive(), car)                     # the tank's goes to its store; the car's starts
        self.assertIsNot(self.T._vstore["tank"]["graph_v"], tank)
        self.assertEqual(termod._VJOBS[self.T]["size"], "car")
        new_tank = self.drive(big=True)
        self.assertEqual(new_tank.nnz, tank.nnz)
        self.finish()
        new_car = self.drive()
        self.assertIsNot(new_car, car)
        self.assertEqual(new_car.nnz, car.nnz)
        self.assertIs(self.drive(big=True), new_tank)

    def test_a_wedge_marked_while_it_is_built_is_on_the_new_ground(self):
        self.drive()
        self.hold()
        self.T._vreset()
        self.drive()
        q = self.T.vwedge(Vec(15.0, 15.0, 0.0), 0.0)
        self.assertIsNotNone(q)
        self.assertFalse(self.T.vroomy[self.T._node(q)])     # (on the old ground at once)
        self.finish()
        self.drive()
        self.assertIsNot(self.T.graph_v, None)
        self.assertFalse(self.T.vroomy[self.T._node(q)])     # and on the new one

    def test_threaded_passes_take_it_at_the_next_pass(self):
        g = self.drive()
        termod.THREADS = True
        self.T._vreset()
        self.drive()
        self.finish()
        self.assertIs(self.drive(), g)                       # (done during this pass: every bot of it on the old)
        termod._PASS["seq"] += 1
        self.assertIsNot(self.drive(), g)

    def test_a_grown_terrain_swapped_in_meanwhile_drops_the_rebuild(self):
        g = self.drive()
        self.hold()
        self.T._vreset()
        self.drive()
        grown = Terrain(self.npz, [])                        # (maps.swap: the same object, a new terrain's insides)
        self.T.__dict__.clear()
        self.T.__dict__.update(grown.__dict__)
        self.finish()
        new = self.drive()
        self.assertIsNot(new, g)
        self.assertIsNone(termod._VJOBS.get(self.T))

    def test_a_terrain_with_a_rebuild_under_way_pickles(self):
        self.drive()
        self.hold()
        self.T._vreset()
        self.drive()
        back = pickle.loads(pickle.dumps(self.T))           # (maps' terrain cache: no thread in it)
        self.assertNotIn("thread", back.__dict__)
        self.assertIsNone(termod._VJOBS.get(back))


if __name__ == "__main__":
    unittest.main()
