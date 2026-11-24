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


if __name__ == "__main__":
    unittest.main()
