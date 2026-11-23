"""(custom, Nov 23) tools/brain_sampler.py: the live brain's sampling profiler (the owner: "Yes, profile first")."""
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_sampler                                   # noqa: E402


def slow_part(until):
    x = 0
    while time.time() < until:
        x += 1
    return x


def fast_part(until):
    while time.time() < until:
        time.sleep(0.001)


def work(sampler, passes=6):
    for k in range(passes):
        sampler.tick = time.time()
        fast_part(time.time() + 0.03)
        if k % 2:
            slow_part(time.time() + 0.15)      # (a pass past SLOW_MS)


class Sampler(unittest.TestCase):
    def test_counts_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "brain_profile_test.txt")
            done = threading.Event()
            box = {}

            def target():
                box["id"] = threading.get_ident()
                started.wait()
                work(s)
                done.set()
            started = threading.Event()
            t = threading.Thread(target=target)
            t.start()
            while "id" not in box:
                time.sleep(0.001)
            s = brain_sampler.Sampler(path, thread_id=box["id"], sample_s=0.002, write_s=99.0)
            s.start()
            started.set()
            done.wait(10)
            t.join()
            s.stop()
            s.join(2)
            self.assertFalse(s.is_alive())
            self.assertGreater(s.n["all"], 50)
            self.assertGreater(s.n["slow"], 10)
            slow = {k[1]: c for k, c in s.total["slow"].items()}
            self.assertGreater(slow.get("slow_part", 0), 0.8 * s.n["slow"])       # (the slow passes are slow_part's)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("== slow passes: by total time", text)
            self.assertIn("slow_part", text)

    def test_never_raises_without_its_thread(self):
        with tempfile.TemporaryDirectory() as d:
            s = brain_sampler.Sampler(os.path.join(d, "p.txt"), thread_id=-1)
            s.sample()
            self.assertEqual(s.n["all"], 0)
            s.write()
            self.assertTrue(os.path.exists(os.path.join(d, "p.txt")))


if __name__ == "__main__":
    unittest.main()
