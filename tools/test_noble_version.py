"""Project Noble's version numbers (custom, Nov 24; the owner's scheme for upstream 0.3.0's note #67) and the update
check's comparisons with them: tools/noble_version.py, tools/updater.py version_key / is_newer / current."""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import noble_version as nv  # noqa: E402
import updater  # noqa: E402


class Scheme(unittest.TestCase):
    def test_commits_wrap_at_1000(self):
        self.assertEqual(nv.from_counts(325, 0), "0.0.325")
        self.assertEqual(nv.from_counts(999, 0), "0.0.999")
        self.assertEqual(nv.from_counts(1000, 0), "0.1.0")
        self.assertEqual(nv.from_counts(2047, 3), "3.2.47")
        self.assertEqual(nv.from_counts(340, 1), "1.0.340")              # (the owner's example)
        with self.assertRaises(ValueError):
            nv.from_counts(-1, 0)

    def test_only_new_scheme_releases_count(self):
        old = ["v0.2.2-custom.11", "v0.2.2-custom.12", "v0.2.2-custom.13", "v0.2.2-custom.14",
               "noble-checkpoint-2026-11-23", "v0.2.2", "v0.3.0"]
        self.assertEqual(nv.releases_in(old), 0)
        self.assertEqual(nv.releases_in(old + ["v1.0.340"]), 1)
        self.assertEqual(nv.releases_in(old + ["v1.0.340", "v2.0.361", "v2.0.361-test"]), 2)

    def test_stamped_copy(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        self.assertIsNone(nv.stamped(d))
        with open(os.path.join(d, "NOBLE_VERSION"), "w", encoding="utf-8") as f:
            f.write("1.0.340\n")
        self.assertEqual(nv.stamped(d), "1.0.340")
        self.assertEqual(nv.current(d), "1.0.340")                       # (no Git there: the stamp)
        with open(os.path.join(d, "NOBLE_VERSION"), "w", encoding="utf-8") as f:
            f.write("junk")
        self.assertIsNone(nv.current(d))

    @unittest.skipUnless(shutil.which("git") and nv.commit_count(nv.ROOT) is not None, "not a Git checkout with origin")
    def test_this_checkout(self):
        n = nv.commit_count(nv.ROOT)
        self.assertEqual(nv.current(nv.ROOT), nv.from_counts(n, nv.release_count(nv.ROOT)))
        v, tag = nv.next_release(nv.ROOT)
        self.assertEqual(tag, "v" + v)
        self.assertEqual(v.split(".")[0], str(nv.release_count(nv.ROOT) + 1))


class UpdaterComparisons(unittest.TestCase):
    """The update check only ever offers a newer version: the scheme's numbers are newer than every older one."""

    def newer(self, cur, latest):
        return updater.is_newer(cur, "", latest, "")

    def test_dev_copy_is_not_offered_the_old_release(self):
        self.assertFalse(self.newer("0.0.325", "v0.2.2-custom.14"))
        self.assertFalse(self.newer("0.0.999", "v0.2.2-custom.14"))

    def test_old_install_is_offered_the_next_release(self):
        self.assertTrue(self.newer("0.2.2-custom.14", "v1.0.340"))
        self.assertTrue(self.newer("0.2.2-custom.11", "v1.0.340"))
        self.assertTrue(self.newer("0.2.2-s181", "v1.0.340"))            # (a copy with upstream's VERSION only)

    def test_between_new_scheme_versions(self):
        self.assertTrue(self.newer("0.0.325", "v1.0.340"))
        self.assertFalse(self.newer("1.0.340", "v1.0.340"))
        self.assertFalse(self.newer("1.0.355", "v1.0.340"))              # (a dev copy past the release it has the tag of)
        self.assertTrue(self.newer("1.0.340", "v2.0.361"))
        self.assertTrue(self.newer("1.0.999", "v2.1.2"))

    def test_old_comparisons_unchanged(self):
        self.assertTrue(self.newer("0.2.2-custom.13", "v0.2.2-custom.14"))
        self.assertFalse(self.newer("0.2.2-custom.14", "v0.2.2-custom.14"))
        updater.selftest()

    def test_upstream_plain_versions_stay_old(self):
        for v in ("0.1.0", "0.2.0", "0.2.1", "v0.3.0"):
            self.assertEqual(updater.version_key(v)[0], 0, v)
            self.assertFalse(self.newer("0.0.325", v), v)

    def test_notes_of_old_versions_are_not_news_to_a_new_scheme_copy(self):
        md = ("<details><summary><b>0.2.2 s181</b> (Nov 6)</summary>\n<!-- build: 20261107-1530 -->\nold\n</details>\n"
              "<details><summary><b>0.2.1</b></summary>\nolder\n</details>\n")
        self.assertEqual(updater.news(md, "0.0.325", ""), [])

    def test_updater_reads_only_our_releases(self):
        self.assertEqual(updater.API, "https://api.github.com/repos/IEatOreos/ProvingGroundsOreo/releases/latest")
        self.assertTrue(updater.RELEASES.startswith("https://github.com/IEatOreos/ProvingGroundsOreo/"))


class CurrentVersion(unittest.TestCase):
    """updater.current(): the scheme's version first, CUSTOM_VERSION for an older install."""

    def copy(self, **files):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        for name, text in files.items():
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text + "\n")
        p = mock.patch.object(updater, "ROOT", d)
        p.start()
        self.addCleanup(p.stop)
        updater._CURRENT.update(at=-1e9, v=None)
        self.addCleanup(updater._CURRENT.update, at=-1e9, v=None)
        return d

    def test_stamped_wins_over_custom_version(self):
        self.copy(NOBLE_VERSION="1.0.340", CUSTOM_VERSION="0.2.2-custom.14", VERSION="0.2.2-s181")
        self.assertEqual(updater.current(), "1.0.340")

    def test_older_install_still_reads_custom_version(self):
        self.copy(CUSTOM_VERSION="0.2.2-custom.14", VERSION="0.2.2-s181")
        self.assertEqual(updater.current(), "0.2.2-custom.14")

    def test_kept_a_minute(self):
        self.copy(NOBLE_VERSION="1.0.340")
        with mock.patch.object(nv, "current", wraps=nv.current) as asked:
            updater.current()
            updater.current()
        self.assertEqual(asked.call_count, 1)


class BuildStamp(unittest.TestCase):
    def test_build_stamps_the_payload(self):
        import build_installer
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        with mock.patch.object(build_installer, "PAYLOAD", d):
            build_installer.stamp_version("1.0.340")
        self.assertEqual(nv.stamped(d), "1.0.340")


if __name__ == "__main__":
    unittest.main()
