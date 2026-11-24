"""(custom, Nov 23) Each tier's thinking budget (brain/bot.py tier_budget, pass_late, optional_search) and the speed
benchmark's check (tools/bench_brain.py compare). The owner: "Yes both"."""
import random
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from brain import bot as botmod                   # noqa: E402
from brain import profiles                        # noqa: E402
from brain.terrain import OPT_FIELDS              # noqa: E402

prof = lambda tier: profiles.make_profile(tier, "rusher", random.Random(1))


class TierBudget(unittest.TestCase):
    def test_on_time(self):
        self.assertEqual(botmod.tier_budget(prof("demon"), False), (botmod.TOP_OPT_FIELDS, False))
        self.assertEqual(botmod.tier_budget(prof("noble"), False), (botmod.TOP_OPT_FIELDS, False))
        self.assertEqual(botmod.tier_budget(prof("mythic"), False), (OPT_FIELDS, False))
        for t in ("top", "strong", "average", "novice", "blind", "tactician"):
            self.assertEqual(botmod.tier_budget(prof(t), False), (OPT_FIELDS, False), t)

    def test_late(self):
        self.assertEqual(botmod.tier_budget(prof("demon"), True), (botmod.TOP_OPT_FIELDS, False))
        self.assertEqual(botmod.tier_budget(prof("noble"), True), (botmod.TOP_OPT_FIELDS, False))
        self.assertEqual(botmod.tier_budget(prof("mythic"), True), (1, False))
        for t in ("top", "strong", "average", "blind", "tactician"):
            self.assertEqual(botmod.tier_budget(prof(t), True), (0, True), t)

    def test_pass_clock(self):
        try:
            botmod.PASS_CLOCK[0] = None
            self.assertFalse(botmod.pass_late())                       # (not timed: sims, tests)
            botmod.PASS_CLOCK[0] = time.perf_counter()
            self.assertFalse(botmod.pass_late())
            self.assertTrue(botmod.pass_late(botmod.PASS_CLOCK[0] + (botmod.PASS_LATE_MS + 1) / 1000.0))
        finally:
            botmod.PASS_CLOCK[0] = None

    def test_a_skipped_tactic_gives_its_default(self):
        class Ter:
            pass
        ter = Ter()

        class B:
            notes = []
            skip_optional = True
            ran = 0
            _t = ter

            def T(s):
                return s._t

            def note(s, text):
                s.notes.append(text)

            @botmod.optional_search(lambda s: "default")
            def tactic(s):
                s.ran += 1
                return "planned"
        b = B()
        self.assertEqual(b.tactic(), "default")
        self.assertEqual(b.ran, 0)
        b.skip_optional = False
        self.assertEqual(b.tactic(), "planned")


class BenchCheck(unittest.TestCase):
    def test_slower_than_the_baseline(self):
        import bench_brain
        base = {"renegade": dict(pass_ms=20.0, pass_p90_ms=40.0)}
        self.assertEqual(bench_brain.compare({"renegade": dict(pass_ms=22.0, pass_p90_ms=45.0)}, base), [])
        self.assertEqual(bench_brain.compare({"renegade": dict(pass_ms=26.0, pass_p90_ms=45.0)}, base),
                         [("renegade", "pass_ms", 26.0, 20.0)])
        self.assertEqual(bench_brain.compare({"utopie": dict(pass_ms=99.0)}, base), [])     # (no baseline for it)


if __name__ == "__main__":
    unittest.main()
