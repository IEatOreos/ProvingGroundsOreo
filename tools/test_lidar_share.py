"""(custom, Nov 24) Sharing LiDAR scans (tools/lidar_share.py, upstream 0.3.0's export / bundle / list): a scan holding
an e-mail address, a user folder, this PC's user name or a personal term (.private_terms, our installer's privacy
scan, tools/privacy.py) is refused, a clean one exports, and what was found is named without the private words.
The tests use made-up terms in a temporary folder; the real .private_terms is never read or printed."""
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lidar_share  # noqa: E402
import privacy  # noqa: E402

TERM = "zebraquillfox"                         # (made up: stands for a personal term)
ENV = {"USERNAME": "testpilot", "USERPROFILE": r"C:\Users\testpilot"}
SCAN = {"cell": 0.25, "zstep": 0.1, "runs": 1, "bot_minutes": 2.0, "human_minutes": 1.0,
        "walk": [[1, 2, 3, 1, 4]], "links": [{"a": [0, 0, 0], "b": [1, 1, 1], "kind": "jump", "who": "human"}]}


class ShareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.maps = os.path.join(self.root, "maps")
        os.makedirs(os.path.join(self.maps, "h3_construct"))
        with open(os.path.join(self.root, ".private_terms"), "w", encoding="utf-8") as f:
            f.write(TERM + "\n")
        self.patches = [mock.patch.dict(os.environ, ENV), mock.patch.object(lidar_share, "ROOT", self.root),
                        mock.patch.object(lidar_share, "MAPS", self.maps)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def write(self, scan):
        with open(os.path.join(self.maps, "h3_construct", "lidar.json"), "w", encoding="utf-8") as f:
            json.dump(scan, f)

    def refused(self, extra):
        self.write(dict(SCAN, note=extra))
        with self.assertRaises(SystemExit) as e:
            lidar_share.export("h3_construct", out=os.path.join(self.root, "out"))
        msg = str(e.exception)
        self.assertIn("not exported", msg)
        self.assertNotIn(TERM, msg.lower())
        self.assertNotIn("testpilot", msg.lower())
        self.assertFalse(os.path.exists(os.path.join(self.root, "out")))
        return msg

    def test_email_refused(self):
        self.assertIn("e-mail", self.refused("someone@example.com"))

    def test_user_folder_refused(self):
        self.assertIn("user folder", self.refused(r"D:\Users\other\maps"))

    def test_user_name_refused(self):
        self.assertIn("user name", self.refused("saved by TestPilot today"))

    def test_private_term_refused(self):
        self.assertIn("personal term", self.refused("a " + TERM.upper() + " b"))

    def test_user_name_whole_word_only(self):
        self.assertEqual(lidar_share.private("the testpilots' armor"), [])

    def test_clean_scan_exports(self):
        self.write(SCAN)
        path = lidar_share.export("h3_construct", out=os.path.join(self.root, "out"))
        with zipfile.ZipFile(path) as z:
            self.assertEqual(set(z.namelist()), {"manifest.json", "lidar.json"})
            man = json.loads(z.read("manifest.json"))
            self.assertEqual((man["map"], man["game"]), ("h3_construct", "Halo 3"))
            self.assertEqual(json.loads(z.read("lidar.json")), SCAN)

    def test_bundle_refuses_a_private_scan(self):
        self.write(dict(SCAN, note=TERM))
        with self.assertRaises(SystemExit) as e:
            lidar_share.bundle("halo-3", out=os.path.join(self.root, "out"))
        self.assertNotIn(TERM, str(e.exception).lower())

    def test_installer_and_share_use_one_check(self):
        terms = privacy.load_terms(self.root)
        self.assertIn(TERM, terms)
        self.assertIn(ENV["USERPROFILE"].lower(), terms)
        user, word = privacy.user_word()
        self.assertEqual(privacy.hits("x " + TERM + " y", terms, user, word), [TERM])
        self.assertEqual(privacy.hits("field testpilot", terms, user, word), ["testpilot"])
        self.assertEqual(privacy.hits("field testpilots", terms, user, word), [])


MINE = {"cell": 0.25, "zstep": 0.1, "runs": 2, "bot_minutes": 3.0, "human_minutes": 1.5,
        "walk": [[1, 2, 3, 1, 4], [7, 7, 7, 9]], "deaths": [{"t": 1}], "jumps": [0.5],
        "links": [{"kind": "jump", "take_off": [0, 0, 0], "land": [1, 1, 1], "found_by": "human", "human": 1}],
        "teleports": [{"a": 1}]}
THEIRS = {"cell": 0.25, "zstep": 0.1, "runs": 1, "bot_minutes": 1.0, "human_minutes": 0.5,
          "walk": [[1, 2, 3, 1, 2], [5, 5, 5, 0, 1]], "deaths": [{"t": 2}], "jumps": [0.7],
          "links": [MINE["links"][0],                                                   # (a duplicate: dropped)
                    {"kind": "jump", "take_off": [2, 2, 2], "land": [3, 3, 3], "found_by": "human", "human": 2},
                    {"kind": "jump", "take_off": [4, 4, 4], "land": [5, 5, 5], "found_by": "map"},     # (a ride)
                    {"kind": "jump", "take_off": [6, 6, 6], "land": [7, 7, 7], "found_by": "bot", "crouch": True,
                     "human": 0},                                                       # (a bot's crouch-jump)
                    {"kind": "jump", "take_off": [8, 8, 8], "land": [9, 9, 9], "found_by": "human", "crouch": True,
                     "human": 1}],                                                      # (a person's: kept)
          "teleports": [{"a": 1}, {"a": 2}]}


class ImportTests(unittest.TestCase):
    """(custom, Nov 24) note #63: a shared zip merged by hand, filtered like our save, never during a match."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.maps = os.path.join(self.root, "maps")
        self.dir = os.path.join(self.maps, "h3_construct")
        os.makedirs(self.dir)
        with open(os.path.join(self.dir, "lidar.json"), "w", encoding="utf-8") as f:
            json.dump(MINE, f)
        import match_lock
        self.lock = os.path.join(self.root, "user", "match.running")
        self.patches = [mock.patch.object(lidar_share, "ROOT", self.root),
                        mock.patch.object(lidar_share, "MAPS", self.maps),
                        mock.patch.object(match_lock, "PATH", self.lock)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def zip(self, scan, name="h3_construct"):
        path = os.path.join(self.root, f"share_{len(os.listdir(self.root))}.zip")
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("manifest.json", json.dumps({"map": name}))
            z.writestr("lidar.json", json.dumps(scan))
        return path

    def saved(self):
        with open(os.path.join(self.dir, "lidar.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_merge_counts_and_filter(self):
        out = lidar_share.merge(MINE, THEIRS)
        walk = {tuple(w[:4]): w[4] for w in out["walk"]}
        self.assertEqual(walk[(1, 2, 3, 1)], 6)                       # (4 + 2: counts added)
        self.assertEqual(walk[(7, 7, 7, 0)], 9)                       # (an old 4-number cell: a bot's)
        self.assertEqual(walk[(5, 5, 5, 0)], 1)
        self.assertEqual((out["runs"], out["bot_minutes"], out["human_minutes"]), (3, 4.0, 2.0))
        self.assertEqual((out["deaths"], out["jumps"]), ([{"t": 1}, {"t": 2}], [0.5, 0.7]))
        takeoffs = [l["take_off"] for l in out["links"]]
        self.assertEqual(takeoffs, [[0, 0, 0], [2, 2, 2], [8, 8, 8]])  # (duplicate, ride and bot crouch-jump out)
        self.assertEqual(out["teleports"], [{"a": 1}, {"a": 2}])

    def test_merge_refuses_another_grid(self):
        with self.assertRaises(SystemExit):
            lidar_share.merge(MINE, dict(THEIRS, cell=0.5))

    def test_import_keeps_backup_and_skips_a_second_time(self):
        path = self.zip(THEIRS)
        got = lidar_share.import_any(path)
        self.assertEqual(got, [("h3_construct", "merged", 1, 3)])
        self.assertIn("1 map added to your scans (2 new jumps and rides)", lidar_share.summary(got))
        backups = [f for f in os.listdir(self.dir) if f.startswith("lidar.json.before-import-")]
        self.assertEqual(len(backups), 1)
        with open(os.path.join(self.dir, backups[0]), encoding="utf-8") as f:
            self.assertEqual(json.load(f), MINE)
        first = self.saved()
        self.assertTrue(all(l.get("found_by") != "map" for l in first["links"]))
        again = lidar_share.import_any(self.zip(THEIRS))
        self.assertEqual(again[0][1], "already imported")
        self.assertEqual(self.saved(), first)                          # (nothing added twice)
        self.assertIn("already imported", lidar_share.summary(again))

    def test_import_a_map_this_version_lacks(self):
        got = lidar_share.import_any(self.zip(THEIRS, name="no_such_map"))
        self.assertEqual(got[0][1], "not in this version")
        got = lidar_share.import_any(self.zip(THEIRS, name="../h3_construct"))
        self.assertEqual(got[0][1], "not in this version")
        self.assertEqual(self.saved(), MINE)

    def test_bundle_import(self):
        path = os.path.join(self.root, "bundle.zip")
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("bundle.json", json.dumps({"maps": ["h3_construct", "h3_guardian"]}))
            z.writestr("h3_construct/lidar.json", json.dumps(THEIRS))
            z.writestr("h3_guardian/lidar.json", json.dumps(THEIRS))
        got = lidar_share.import_any(path)
        self.assertEqual([r for _, r, *_ in got], ["merged", "not in this version"])

    def test_refused_while_a_match_runs(self):
        import match_lock
        match_lock.hold("h3_construct", path=self.lock)               # (this process: alive)
        try:
            self.assertTrue(match_lock.running())
            with self.assertRaises(SystemExit) as e:
                lidar_share.import_any(self.zip(THEIRS))
            self.assertIn("match is running", str(e.exception))
            self.assertEqual(self.saved(), MINE)
            self.assertFalse(any(f.startswith("lidar.json.before") for f in os.listdir(self.dir)))
            import launcher
            r = launcher.lidar_import(b"PK")
            self.assertFalse(r["ok"])
            self.assertIn("match is running", r["message"])
        finally:
            match_lock.release(self.lock)
        self.assertFalse(os.path.exists(self.lock))
        self.assertIsNone(match_lock.running())
        self.assertEqual(lidar_share.import_any(self.zip(THEIRS))[0][1], "merged")

    def test_a_crashed_match_lock_does_not_block(self):
        import match_lock
        os.makedirs(os.path.dirname(self.lock), exist_ok=True)
        with open(self.lock, "w", encoding="utf-8") as f:
            json.dump({"pid": 2 ** 31 - 7, "map": "h3_construct"}, f)          # (no such process)
        self.assertIsNone(match_lock.running())
        self.assertEqual(lidar_share.import_any(self.zip(THEIRS))[0][1], "merged")

    def test_launcher_refuses_a_bad_zip(self):
        import launcher
        with mock.patch.object(launcher, "ROOT", self.root):
            r = launcher.lidar_import(b"not a zip")
        self.assertFalse(r["ok"])
        self.assertIn("Not a LiDAR scan zip", r["message"])
        self.assertFalse(launcher.lidar_import(None)["ok"])

    def test_no_download_code(self):
        text = open(os.path.join(ROOT, "tools", "lidar_share.py"), encoding="utf-8").read()
        for word in ("urllib", "http://", "https://", "def fetch", "BUNDLE_URLS", "urlopen"):
            self.assertNotIn(word, text)
        page = open(os.path.join(ROOT, "tools", "launcher.html"), encoding="utf-8").read()
        self.assertNotIn("/lidar/fetch", page)
        self.assertNotIn("scan-fetch", page)


if __name__ == "__main__":
    unittest.main()
