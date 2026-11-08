"""tools/h4_seat_capture.py against a stand-in Halo 4 memory: unit fields, the head marker, the vehicle frame, the
on-foot reader's verdict and the summary (no game needed)."""
import gzip
import json
import math
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import h4_seat_capture as cap                 # noqa: E402
from brain.live import LiveH4F                # noqa: E402

UNIT, VEH = 0x10010, 0x20020                  # handles
UA, VA = 0x100000, 0x200000                   # addresses
NODE_OFF = 0x145C


class FakeLive:
    PARENT_AT, ORIENT_AT, VEHICLE_TYPES = 0x24, 0x70, (1,)

    def __init__(s, seated, yaw=0.0):
        s.mem = {UA: bytearray(0x4000), VA: bytearray(0x200)}
        s.g = SimpleNamespace(dll="halo4.dll", read=s.read)
        u = s.mem[UA]
        vpos = (10.0, 20.0, 1.0)
        c, sn = math.cos(yaw), math.sin(yaw)
        if seated:
            # seated 0.4 u ahead and 0.3 u left of the vehicle's origin, place 0.5 up; head 0.25 over the place
            off = (0.4, 0.3)
            pos = (vpos[0] + c * off[0] - sn * off[1], vpos[1] + sn * off[0] + c * off[1], vpos[2] + 0.5)
        else:
            pos = (0.0, 0.0, 0.38)
        s.pos = pos
        struct.pack_into("<HH", u, 0x1BC, 120 * 52, NODE_OFF)
        struct.pack_into("<3f", u, 0x40, *pos)
        struct.pack_into("<3f", u, 0x64, pos[0], pos[1], pos[2] - 0.38)
        struct.pack_into("<3f", u, 0xD50, pos[0], pos[1], pos[2] + 0.22)
        struct.pack_into("<h", u, 0x2C, 0 if seated else -1)
        struct.pack_into("<I", u, 0x24, VEH if seated else 0xFFFFFFFF)
        # node 54: identity rotation, its origin so that the marker lands 0.25 over the place
        mk = cap.HEAD_MARKER
        struct.pack_into("<13f", u, NODE_OFF + 54 * 52, 1.0, 1, 0, 0, 0, 1, 0, 0, 0, 1,
                         pos[0] - mk[0], pos[1] - mk[1], pos[2] + 0.25 - mk[2])
        v = s.mem[VA]
        struct.pack_into("<3f", v, 0x40, *vpos)
        struct.pack_into("<3f", v, 0x70, c, sn, 0.0)
        struct.pack_into("<3f", v, 0x7C, 0.0, 0.0, 1.0)
        struct.pack_into("<I", v, 0x24, 0xFFFFFFFF)

    def read(s, a, n):
        for base, buf in s.mem.items():
            if base <= a < base + len(buf):
                return bytes(buf[a - base:a - base + n])
        return None

    def object(s, h):
        return {UNIT: UA, VEH: VA}.get(h)

    def objects(s, types=None):
        return [(VEH, 1, "storm_warthog", (10.0, 20.0, 1.0))]

    def players(s):
        return [dict(index=0, name="me", unit=UNIT, pos=s.pos, aim=(1, 0, 0), shield=1.0, health=1.0)]

    def map_name(s):
        return "test_map"

    def h4_spartan_pose(s, address, unit, position):
        return LiveH4F.h4_spartan_pose(s, address, unit, position)


class SeatCaptureTests(unittest.TestCase):
    def test_on_foot_row_matches_the_reader(self):
        live = FakeLive(seated=False)
        c = cap.Capture(tempfile.mkdtemp(), live=live)
        r = c.row(live, live.players()[0], bones=True)
        self.assertEqual(r["seat"], -1)
        self.assertIsNone(r["parent"])
        self.assertAlmostEqual(r["head"][2] - r["pos"][2], 0.25, places=4)
        self.assertTrue(r["reader_ok"])
        self.assertEqual(r["fails"], [])
        self.assertEqual(len(__import__("base64").b64decode(r["bones"])), 120 * 52)

    def test_seated_row_in_the_vehicle_frame(self):
        for yaw in (0.0, 1.2, -2.5):
            live = FakeLive(seated=True, yaw=yaw)
            c = cap.Capture(tempfile.mkdtemp(), live=live)
            for h, _, name, _ in live.objects():
                c.names[h] = name
            r = c.row(live, live.players()[0], bones=False)
            self.assertEqual(r["seat"], 0)
            self.assertEqual(r["ride"][0]["name"], "storm_warthog")
            self.assertEqual(r["frame_of"], "storm_warthog")
            f, l, u = r["pos_v"]
            self.assertAlmostEqual(f, 0.4, places=3)
            self.assertAlmostEqual(l, 0.3, places=3)
            self.assertAlmostEqual(u, 0.5, places=3)
            self.assertAlmostEqual(r["head_v"][2], 0.75, places=3)
            self.assertNotIn("bones", r)

    def test_summary_groups_by_seat(self):
        d = tempfile.mkdtemp()
        rows = []
        for seated in (False, True):
            live = FakeLive(seated=seated)
            c = cap.Capture(d, live=live)
            for h, _, name, _ in live.objects():
                c.names[h] = name
            rows.append(c.row(live, live.players()[0], bones=False))
        with gzip.open(os.path.join(d, "samples.jsonl.gz"), "wt", encoding="utf-8") as f:
            for k in range(3):
                f.write(json.dumps(dict(t=k, rows=rows)) + "\n")
        out = cap.summary(d)
        self.assertEqual(out["on foot"]["samples"], 3)
        self.assertEqual(out["storm_warthog seat 0"]["samples"], 3)
        self.assertAlmostEqual(out["storm_warthog seat 0"]["head_v"]["up"][0], 0.75, places=3)
        self.assertTrue(os.path.exists(os.path.join(d, "summary.json")))


if __name__ == "__main__":
    unittest.main()
