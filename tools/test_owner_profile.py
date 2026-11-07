"""tools/owner_profile.py on a hand-made match: a kill from a spot, the spectated-match filter, the spot cluster."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owner_profile as op  # noqa: E402


def row(i, team, x, y, z, alive=True, hp=(1.0, 1.0), bot=True, yaw=0.0, pitch=0.0, sights=-1):
    return [i, team, alive, x, y, z, hp[0], hp[1], bot, False, yaw, pitch, 0.0, [], sights]


def match():
    """The person (0) on a ledge 2 u up shoots bot 1 (8 u east, not aiming at anyone) for 1 s; bot 1 dies."""
    rows = []
    for k in range(12):
        t = k * 0.25
        alive = k < 8
        me = row(0, 0, 0.0, 0.0, 2.0, bot=False, yaw=0.0, pitch=math.atan2(0.35 - 2.62, 8.0), sights=1 if alive else -1)
        him = row(1, 1, 8.0, 0.0, 0.0, alive=alive, hp=(max(0.0, 1.0 - 0.3 * k), 1.0), yaw=math.pi / 2)
        rows.append((t, {0: me, 1: him}))
    return rows


class OwnerProfileTests(unittest.TestCase):
    def test_kill_from_a_ledge(self):
        kills, deaths, fights, track, minutes = op.analyse(match(), 0)
        self.assertEqual(len(kills), 1)
        k = kills[0]
        self.assertAlmostEqual(k["dist"], math.dist((0, 0, 2), (8, 0, 0)), places=2)
        self.assertAlmostEqual(k["dz"], 2.0)
        self.assertEqual(k["vic_aim"], "nobody")
        self.assertFalse(k["saw_first"])
        self.assertEqual(deaths, [])
        self.assertEqual([f["result"] for f in fights], ["won"])

    def test_profile_and_spot(self):
        a = op.analyse(match(), 0)
        info = dict(trace="t", gametype="g", player="p", kills=1, deaths=0, minutes=a[4])
        prof = op.profile([(info, a)])
        self.assertEqual(prof["kills"], dict(game=1, found=1))
        self.assertEqual(prof["engage"]["above_victim_pct"], 100.0)
        self.assertEqual(len(prof["spots"]), 1)
        self.assertEqual(prof["spots"][0]["pos"], [0.0, 0.0, 2.0])

    def test_cluster(self):
        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (20, 0, 0)]
        c = op.cluster(pts)
        self.assertEqual(sorted(len(m) for _, m in c), [1, 3])


class BackgroundTests(unittest.TestCase):
    """The run tools/play.py starts at each match: one at a time, and matches that are not his read once."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.saved = op.CACHE, op.LOCK
        op.CACHE, op.LOCK = self.tmp, os.path.join(self.tmp, "run.lock")

    def tearDown(self):
        import shutil
        op.CACHE, op.LOCK = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_one_run_at_a_time(self):
        self.assertTrue(op.lock())
        self.assertFalse(op.lock())                  # a second run while the first holds it
        op.unlock()
        self.assertTrue(op.lock())
        old = __import__("time").time() - op.LOCK_STALE - 5
        os.utime(op.LOCK, (old, old))                # a run that died long ago does not block forever
        self.assertTrue(op.lock())
        op.unlock()

    def test_a_skipped_match_is_kept_as_a_skip(self):
        tr = os.path.join(self.tmp, "trace_x_20260101-000000.jsonl")
        open(tr, "w").write("{}\n")
        op.keep_skip(tr, "0 people in the carnage report")
        c = op.cached(tr)
        self.assertEqual(c["skip"], "0 people in the carnage report")
        open(tr, "a").write("{}\n")                  # the file changed: read again
        self.assertIsNone(op.cached(tr))


if __name__ == "__main__":
    unittest.main()
