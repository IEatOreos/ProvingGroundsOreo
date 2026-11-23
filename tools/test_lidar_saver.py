"""(custom, Nov 22) The people's LiDAR save in a helper process (tools/lidar_saver.py Saver, merge_save): the same file as
the save in place, a broken helper falls back to the save in place, and the merge keeps what the old save kept.
Live Asylum: the merge of its 3 MB lidar.json took 420-445 ms a minute and froze every bot's thinking."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import lidar  # noqa: E402
import lidar_saver  # noqa: E402

OLD = {"cell": 0.25, "zstep": 0.1, "runs": 4, "bot_minutes": 10.0, "human_minutes": 2.5,
       "walk": [[1, 2, 3, 9], [1, 2, 3, lidar.KIND_HUMAN, 2]],            # (the first row in the old 4-number form)
       "deaths": [{"t": 1.0, "who": "human", "cause": "gun"}], "jumps": [0.5], "links": [], "weapons": [],
       "cover": [], "objectives": [{"kind": "hill", "pos": [1, 2, 3]}]}


def recorder(path):
    with open(path, "w") as f:
        json.dump(OLD, f)
    rec = lidar.Recorder("_selftest", count_run=False, path=path)
    rec.walk[(1, 2, 3, lidar.KIND_HUMAN)] = 3                          # (2 stored + 3 new)
    rec.walk[(5, 6, 7, lidar.KIND_BOT)] = 1
    rec.deaths.append({"t": 2.0, "who": "human", "cause": "fall", "stood": [0, 0, 0]})
    rec.jumps.append(1.25)
    return rec


class SaverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, name):
        return os.path.join(self.tmp.name, name)

    def test_merge_keeps_what_the_old_save_kept(self):
        out = recorder(self.path("a.json")).save(human_seconds=30.0)
        self.assertEqual(out["walk"], [[1, 2, 3, lidar.KIND_BOT, 9], [1, 2, 3, lidar.KIND_HUMAN, 5],
                                       [5, 6, 7, lidar.KIND_BOT, 1]])
        self.assertEqual((out["runs"], out["bot_minutes"], out["human_minutes"]), (4, 10.0, 3.0))
        self.assertEqual([d["cause"] for d in out["deaths"]], ["gun", "fall"])
        self.assertEqual(out["jumps"], [0.5, 1.25])
        self.assertEqual(out["objectives"], OLD["objectives"])            # (no objectives watched: the file's own)
        with open(self.path("a.json")) as f:
            self.assertEqual(json.load(f), out)

    def test_the_helper_writes_the_same_file(self):
        here, there = recorder(self.path("here.json")), recorder(self.path("there.json"))
        here.save(human_seconds=30.0)
        saver = lidar_saver.Saver()
        try:
            self.assertIs(there.save(human_seconds=30.0, saver=saver), True)
            self.assertEqual(saver.fallbacks, 0)
            there.walk[(9, 9, 9, lidar.KIND_BOT)] = 2                   # (a second save over the same helper)
            here.walk[(9, 9, 9, lidar.KIND_BOT)] = 2
            there.save(saver=saver)
            here.save()
        finally:
            saver.close()
        self.assertIsNone(saver.proc)
        with open(self.path("here.json")) as a, open(self.path("there.json")) as b:
            self.assertEqual(a.read(), b.read())

    def test_a_broken_helper_saves_in_place(self):
        rec = recorder(self.path("b.json"))
        saver = lidar_saver.Saver(cmd=[sys.executable, "-c", "import sys; sys.stdin.readline()"])   # (exits, no reply)
        try:
            self.assertIs(rec.save(human_seconds=30.0, saver=saver), True)
        finally:
            saver.close()
        self.assertEqual(saver.fallbacks, 1)
        with open(self.path("b.json")) as f:
            self.assertEqual(json.load(f)["walk"][-1], [5, 6, 7, lidar.KIND_BOT, 1])

    def test_nothing_new_twice(self):
        rec = recorder(self.path("c.json"))
        rec.save()
        out = rec.save()                                                  # (the same counts again: added once)
        self.assertEqual(out["walk"][1], [1, 2, 3, lidar.KIND_HUMAN, 5])
        self.assertEqual(len(out["deaths"]), 2)


if __name__ == "__main__":
    unittest.main()
