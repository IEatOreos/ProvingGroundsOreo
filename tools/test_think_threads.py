"""(custom, Nov 23) How many threads the bots think on (tools/live_bots.py think_threads) and which Python runs the brain
(tools/play.py brain_python). The owner: "Yes, start the port"."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import live_bots                       # noqa: E402


class ThinkThreads(unittest.TestCase):
    def test_auto_half_the_pc_two_to_six(self):
        self.assertEqual(live_bots.think_threads(cpus=16, gil=False, env=""), 6)
        self.assertEqual(live_bots.think_threads(cpus=8, gil=False, env=""), 4)
        self.assertEqual(live_bots.think_threads(cpus=4, gil=False, env=""), 2)
        self.assertEqual(live_bots.think_threads(cpus=2, gil=False, env=""), 1)          # (never past the PC's less one)

    def test_with_the_lock_off_unless_asked(self):
        self.assertEqual(live_bots.think_threads(cpus=16, gil=True, env=""), 0)
        self.assertEqual(live_bots.think_threads(cpus=16, gil=True, env="4"), 4)

    def test_asked_for(self):
        self.assertEqual(live_bots.think_threads(cpus=16, gil=False, env="0"), 0)
        self.assertEqual(live_bots.think_threads(cpus=16, gil=False, env="3"), 3)
        self.assertEqual(live_bots.think_threads(cpus=16, gil=False, env="40"), 15)
        self.assertEqual(live_bots.think_threads(cpus=16, gil=False, env="x"), 6)


class BrainPython(unittest.TestCase):
    def test_the_free_threaded_one_where_it_is(self):
        import play
        with tempfile.TemporaryDirectory() as d:
            exe = os.path.join(d, "python.exe")
            open(exe, "w").close()
            with mock.patch.object(play, "FT_PYTHONS", (exe,)), mock.patch.dict(os.environ, {"PPG_THINK_THREADS": ""}):
                self.assertEqual(play.brain_python(), os.path.abspath(exe))
            with mock.patch.object(play, "FT_PYTHONS", (exe,)), mock.patch.dict(os.environ, {"PPG_THINK_THREADS": "0"}):
                self.assertEqual(play.brain_python(), sys.executable)
        with mock.patch.object(play, "FT_PYTHONS", (os.path.join(str(ROOT), "nowhere", "python.exe"),)), \
                mock.patch.dict(os.environ, {"PPG_THINK_THREADS": "", "PPG_BRAIN_PYTHON": ""}):
            self.assertEqual(play.brain_python(), sys.executable)


if __name__ == "__main__":
    unittest.main()
