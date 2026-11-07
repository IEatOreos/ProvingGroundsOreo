"""LiDAR mode records vehicle drives and flights (tools/lidar.py RideWatch, as normal matches do) and the LiDAR view
draws them: stored ones from maps/<map>/rides.json (rides_view) and this run's as they come (Hub.live, /live rsince).
Run: python -I tools/test_lidar_drives.py
"""
import json
import os
import socket
import sys
import tempfile
import types
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import lidar  # noqa: E402


def rider(i, vehicle, alive=True):
    return types.SimpleNamespace(id=i, vehicle=vehicle, alive=alive)


class FlatT:
    """Terrain stand-in: the floor at z = 0."""
    def height_over(self, x, y, z):
        return z


def drive(rw, kind, xs, who, bots=(), z=0.0, handle=7, t0=0.0, y=0.0):
    for k, x in enumerate(xs):
        rw.update(t0 + k / 30, [dict(handle=handle, kind=kind, pos=(x, y, z))],
                  [rider(i, handle) for i in who], set(bots))


class RideWatchFeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "rides.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_person_and_bot_drives_feed_and_save(self):
        rw = lidar.RideWatch("_test", path=self.path)
        drive(rw, "warthog", [i * 0.3 for i in range(10)], who=[0])              # a person: 10 samples
        drive(rw, "warthog", [i * 0.3 for i in range(5)], who=[3], bots=[3], handle=8, y=5.0)   # a bot: 5, its own lane
        feed, n = rw.since(0)
        self.assertEqual(n, 15)
        self.assertEqual(sum(1 for f in feed if f[3] == rw.FEED_DRIVE), 10)
        self.assertEqual(sum(1 for f in feed if f[3] == rw.FEED_BOT_DRIVE), 5)
        self.assertEqual(rw.since(n), ([], n))                                   # nothing new
        self.assertTrue(rw.save())
        v = lidar.rides_view("_test", path=self.path)
        self.assertEqual(v["people"], 10)
        # a bot's single drive is not vehicle ground yet (brain/maps.py rides_layers: bots twice), so not drawn
        self.assertEqual(sum(1 for r in v["drive"] if r[3] == rw.FEED_BOT_DRIVE), 0)
        drive(rw, "warthog", [i * 0.3 for i in range(5)], who=[3], bots=[3], handle=9, t0=5.0, y=5.0)
        rw.save()
        v = lidar.rides_view("_test", path=self.path)
        self.assertEqual(sum(1 for r in v["drive"] if r[3] == rw.FEED_BOT_DRIVE), 5)

    def test_flights_feed_and_view_height(self):
        rw = lidar.RideWatch("_test", T=FlatT(), path=self.path)
        drive(rw, "banshee", [0.0] * 3, who=[0], z=0.5)                        # on the ground first
        drive(rw, "banshee", [i * 1.5 for i in range(1, 8)], who=[0], z=4.0, t0=1.0)
        feed, _ = rw.since(0)
        self.assertTrue(feed and all(f[3] == rw.FEED_AIR for f in feed))
        self.assertTrue(rw.save())
        air = lidar.rides_view("_test", path=self.path)["air"]
        self.assertTrue(air)
        self.assertTrue(all(abs(a[2] - 4.0) < 1e-6 for a in air), air)          # floor 0 + 4 u flown

    def test_feed_drops_oldest_but_counts_stay(self):
        rw = lidar.RideWatch("_test", path=self.path)
        rw.FEED_MAX = 4
        drive(rw, "warthog", [i * 0.3 for i in range(10)], who=[0])
        feed, n = rw.since(0)
        self.assertEqual((len(feed), n), (4, 10))
        self.assertEqual(rw.since(8), (feed[2:], 10))

    def test_no_rider_dead_rider_or_unknown_kind_records_nothing(self):
        rw = lidar.RideWatch("_test", path=self.path)
        rw.update(0, [dict(handle=1, kind="warthog", pos=(0, 0, 0))], [rider(0, -1)], set())
        rw.update(0, [dict(handle=1, kind="warthog", pos=(0, 0, 0))], [rider(0, 1, alive=False)], set())
        rw.update(0, [dict(handle=2, kind="not_a_vehicle", pos=(0, 0, 0))], [rider(0, 2)], set())
        self.assertEqual(rw.since(0), ([], 0))
        self.assertFalse(rw.save())

    def test_missing_or_bad_file_views_empty(self):
        self.assertEqual(lidar.rides_view("_test", path=self.path), dict(drive=[], air=[], people=0))
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertEqual(lidar.rides_view("_test", path=self.path), dict(drive=[], air=[], people=0))


class HubAndServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rec = lidar.Recorder("_selftest", count_run=False, path=os.path.join(self.tmp.name, "lidar.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_hub_sends_rides_only_with_a_watch(self):
        hub = lidar.Hub(self.rec, "live")
        self.assertNotIn("rides", hub.live(0))
        self.assertIn("rides", hub.stored_view())
        hub.rides = lidar.RideWatch("_selftest", path=os.path.join(self.tmp.name, "rides.json"))
        drive(hub.rides, "warthog", [i * 0.3 for i in range(6)], who=[0])
        d = hub.live(0, 0)
        self.assertEqual((len(d["rides"]), d["rseq"]), (6, 6))
        self.assertEqual(hub.live(0, 6)["rides"], [])
        json.dumps(d)

    def test_live_endpoint_takes_rsince(self):
        hub = lidar.Hub(self.rec, "live")
        hub.rides = lidar.RideWatch("_selftest", path=os.path.join(self.tmp.name, "rides.json"))
        drive(hub.rides, "warthog", [i * 0.3 for i in range(6)], who=[0])
        with socket.socket() as so:
            so.bind(("127.0.0.1", 0))
            port = so.getsockname()[1]
        srv = lidar.serve(hub, port)
        self.assertIsNotNone(srv)
        try:
            base = f"http://127.0.0.1:{port}"
            d = json.loads(urllib.request.urlopen(base + "/live?since=0&rsince=2", timeout=5).read())
            self.assertEqual((len(d["rides"]), d["rseq"]), (4, 6))
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(base + "/live?since=0&rsince=x", timeout=5)
            self.assertEqual(e.exception.code, 400)
            e.exception.close()
        finally:
            srv.shutdown()
            srv.server_close()


class PageTests(unittest.TestCase):
    def test_view_draws_and_polls_rides(self):
        page = (ROOT / "tools" / "lidar_view.html").read_text(encoding="utf-8")
        for needle in ('id="b-drive"', "rsince=", "setRides(d.rides)", "addRides(d.rides)", 'data-layer="drive"',
                       'v: "drive"', '"kinds", "drive"]'):
            self.assertIn(needle, page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
