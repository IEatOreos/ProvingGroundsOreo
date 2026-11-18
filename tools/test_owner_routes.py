"""(custom, Nov 17) The owner's LiDAR driving routes: "sometimes my routes wouldn't be ideal for bots that's why I created
the lidar driving routes. So bots would try to always stick to those". tools/lidar.py RideWatch(owner=True) counts a
person's drive in LiDAR mode as an owner route (the drive row's sixth number); brain/maps.py rides_layers makes them
the roads (T.owner_drive) and, once a map has them, people's match drives drivable ground only; brain/terrain.py
_build_vnav: an edge on one costs OWNER_ROAD_COST."""
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import numpy as np  # noqa: E402

import lidar  # noqa: E402
from brain import maps  # noqa: E402
from brain.core import Vec  # noqa: E402
from brain.terrain import OWNER_ROAD_COST, ROAD_COST  # noqa: E402

_T = {}


def gulch():
    if "T" not in _T:
        _T["T"] = maps._build(maps.get_map("bloodgulch"), None)
    return _T["T"]


def rider(pid, veh):
    from types import SimpleNamespace
    return SimpleNamespace(id=pid, vehicle=veh, alive=True)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "rides.json")

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)["drive"]

    def drive(self, rw, who, bots, y=0.0, handle=1):
        for k in range(8):
            rw.update(k * 0.1, [dict(handle=handle, kind="warthog", pos=(k * 0.3, y, 0.0))], [rider(who, handle)], bots)

    def test_lidar_mode_drives_are_owner_routes(self):
        rw = lidar.RideWatch("_test", path=self.path, owner=True)
        self.drive(rw, 0, set())                       # the owner, LiDAR mode
        self.drive(rw, 3, {3}, y=5.0, handle=2)        # a LiDAR bot: still a bot's
        feed, _ = rw.since(0)
        self.assertEqual(sum(1 for f in feed if f[3] == rw.FEED_OWNER_DRIVE), 8)
        self.assertEqual(sum(1 for f in feed if f[3] == rw.FEED_BOT_DRIVE), 8)
        self.assertTrue(rw.save())
        rows = self.rows()
        self.assertTrue(all(len(r) == 6 for r in rows))
        self.assertEqual(sum(1 for r in rows if r[5] >= 1 and r[3] == 0), 8)
        v = lidar.rides_view("_test", path=self.path)
        self.assertEqual(sum(1 for r in v["drive"] if r[3] == rw.FEED_OWNER_DRIVE), 8)

    def test_high_over_the_floor_is_no_route(self):
        # (Nov 18, Breakpoint: 1,949 of his route cells 5-19 u up, his flying saved as drives) DRIVE_MAX_H
        class Flat:
            def height_over(self, x, y, z):
                return z
        rw = lidar.RideWatch("_test", T=Flat(), path=self.path, owner=True)
        for k in range(8):
            rw.update(k * 0.1, [dict(handle=1, kind="warthog", pos=(k * 0.3, 0.0, 11.0))], [rider(0, 1)], set())
        self.assertEqual(rw.since(0), ([], 0))
        self.assertFalse(rw.save())
        for k in range(8):                              # on the ground, and over a bump within DRIVE_MAX_H: kept
            z = 0.6 if k < 4 else rw.DRIVE_MAX_H - 0.2
            rw.update(1 + k * 0.1, [dict(handle=1, kind="warthog", pos=(k * 0.3, 0.0, z))], [rider(0, 1)], set())
        feed, _ = rw.since(0)
        self.assertEqual(sum(1 for f in feed if f[3] == rw.FEED_OWNER_DRIVE), 8)

    def test_a_match_drive_is_not_and_old_rows_keep(self):
        with open(self.path, "w") as f:
            json.dump(dict(drive=[[9.0, 9.0, 0.0, 2, 1]]), f)      # an older five-number row
        rw = lidar.RideWatch("_test", path=self.path)             # a match (live_bots)
        self.drive(rw, 0, set())
        rw.save()
        rows = {tuple(r[:3]): r[3:] for r in self.rows()}
        self.assertEqual(rows[(9.0, 9.0, 0.0)], [2, 1, 0])
        self.assertTrue(all(r[0] == 1 and r[2] == 0 for k, r in rows.items() if k != (9.0, 9.0, 0.0)))


class LayerTests(unittest.TestCase):
    def layers(self, rows):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "rides.json")
            with open(f, "w") as fh:
                json.dump(dict(drive=rows), fh)
            from types import SimpleNamespace
            T = SimpleNamespace()
            drive, *_ = maps.rides_layers([], T, files=[f])
            return drive, T

    def test_without_routes_people_drives_are_the_roads(self):
        drive, T = self.layers([[1.0, 0.0, 0.0, 1, 0], [2.0, 0.0, 0.0, 0, 3]])
        self.assertEqual(T.people_drive, [(1.0, 0.0, 0.0)])
        self.assertEqual(T.owner_drive, [])
        self.assertEqual(len(drive), 2)

    def test_with_routes_match_drives_are_ground_only(self):
        drive, T = self.layers([[1.0, 0.0, 0.0, 1, 0, 0], [5.0, 0.0, 0.0, 0, 0, 1]])
        self.assertEqual(T.owner_drive, [(5.0, 0.0, 0.0)])
        self.assertEqual(T.people_drive, [])
        self.assertEqual(sorted(drive), [(1.0, 0.0, 0.0), (5.0, 0.0, 0.0)])     # both still drivable ground


class StickTests(unittest.TestCase):
    """Blood Gulch: a route bent well off the straight line between two open spots is driven, not cut."""

    @classmethod
    def setUpClass(cls):
        T = cls.T = gulch()
        T.use_vground(False)
        T.__dict__.pop("owner_drive", None)
        T.__dict__.pop("people_drive", None)
        T._vreset()
        T.vnav(Vec(0, 0, 0), Vec(50, 50, 0))
        cls.case = None
        ls, js, is_ = np.nonzero(T.vroomy)
        pts = [T._center(int(ls[k]), int(js[k]), int(is_[k])) for k in range(0, len(ls), max(1, len(ls) // 400))]
        for a in pts:
            for b in pts:
                d = (b - a).flat()
                if not 35 < d < 50:
                    continue
                route = cls.bent(T, a, b, 0.45 * d)
                if route:
                    cls.case = (a, b, route)
                    return

    @staticmethod
    def bent(T, a, b, off):
        """Samples every 0.25 u along a -> c -> b (c off the middle by `off`), each on the car ground, or None."""
        dx, dy = b.x - a.x, b.y - a.y
        n = math.hypot(dx, dy)
        c = Vec((a.x + b.x) / 2 - dy / n * off, (a.y + b.y) / 2 + dx / n * off, a.z)
        out, z = [], a.z
        for p, q in ((a, c), (c, b)):
            L = math.hypot(q.x - p.x, q.y - p.y)
            for k in range(int(L / 0.25) + 1):
                t = k * 0.25 / L
                x, y = p.x + (q.x - p.x) * t, p.y + (q.y - p.y) * t
                nd = T._node_at(x, y, z, tol=1.5) if T.inside(x, y) else None
                if nd is None or not T.vroomy[nd]:
                    return None
                z = float(T.lz[nd])
                out.append((x, y, z))
        return out

    def run_to(self, a, b):
        T, pos, path = self.T, a, [a]
        for _ in range(400):
            w = T.vnav(pos, b)
            if w is None or (w - pos).flat() < 0.05:
                break
            pos = w
            path.append(pos)
            if (b - pos).flat() < 4.0:
                break
        return path

    @staticmethod
    def off_line(p, a, b):
        dx, dy = b.x - a.x, b.y - a.y
        return abs((p.x - a.x) * dy - (p.y - a.y) * dx) / math.hypot(dx, dy)

    def test_drives_the_route(self):
        if self.case is None:
            self.skipTest("no open pair on the map")
        a, b, route = self.case
        T = self.T
        try:
            T.owner_drive = []
            T._vreset()
            plain = max(self.off_line(p, a, b) for p in self.run_to(a, b))
            T.owner_drive = route
            T._vreset()
            path = self.run_to(a, b)
            on = max(self.off_line(p, a, b) for p in path)
            off = (b - a).flat() * 0.45
            self.assertLess(plain, off * 0.5)              # on its own: about straight
            self.assertGreater(on, off * 0.8)              # with the route: out round its bend
            self.assertLess((path[-1] - b).flat(), 4.5)    # and on to the goal
        finally:
            T.owner_drive = []
            T._vreset()

    def test_costs(self):
        self.assertLess(OWNER_ROAD_COST, ROAD_COST)
        self.assertLessEqual(OWNER_ROAD_COST, 0.15)


if __name__ == "__main__":
    unittest.main()
