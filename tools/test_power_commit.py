"""(custom, Nov 18) A run at a power weapon is finished unless an enemy is close (Bot.power_commit). The owner: "commit
to them unless an enemy is close". Forge World 20261118-180057: about 170 runs at the rockets ended after 1-4 s for a
hunt, a retreat or a fight and were begun again."""
import random
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                                # noqa: E402
from brain.bot import Belief, Bot                              # noqa: E402
from brain.core import PlayerState, Snapshot, Vec              # noqa: E402
from brain.profiles import make_profile                        # noqa: E402

ROCKETS = Vec(20.0, 0.0, 1.5)
RIFLE = Vec(-10.0, 0.0, 0.0)


def scene(goal=("item", ROCKETS)):
    m = {"name": "reach_test", "items": [
        {"kind": "weapon", "name": "rocket_launcher", "value": 0.95, "pos": ROCKETS},
        {"kind": "weapon", "name": "dmr", "value": 0.5, "pos": RIFLE}]}
    b = Bot(0, 0, make_profile("demon", "objector", random.Random(1)), m, random.Random(2))
    b.notes = []
    b.goal = goal
    me = PlayerState(0, 0, "bot", Vec())
    snap = Snapshot(10.0, [me], mode="slayer")
    return b, me, snap


def scores():
    return {("item", ROCKETS): 1.6, ("hunt", Vec(5, 5, 0)): 3.0, ("retreat", Vec(-3, 0, 0)): 2.3,
            ("fight", 4): 1.7}


class PowerCommitTests(unittest.TestCase):
    def test_the_run_beats_hunts_retreats_and_far_fights(self):
        b, me, snap = scene()
        sc = scores()
        b.per.beliefs[4] = Belief(Vec(14, 6, 0), Vec(), 9.9, True, "eyes")      # seen, 15 u off
        b.power_commit(10.0, me, snap, sc, False)
        self.assertEqual(max(sc, key=sc.get), ("item", ROCKETS))
        self.assertAlmostEqual(sc[("item", ROCKETS)], 3.0 + botmod.POWER_COMMIT_MARGIN)
        self.assertIn("power weapon run: committed", b.notes)

    def test_an_enemy_close_or_a_hit_leaves_the_usual_choice(self):
        for src in ("eyes", "radar", "team", "hit"):
            b, me, snap = scene()
            b.per.beliefs[4] = Belief(Vec(5, 3, 0), Vec(), 9.9, src == "eyes", src)    # 5.8 u off
            sc = scores()
            b.power_commit(10.0, me, snap, sc, False)
            self.assertEqual(sc, scores(), src)
        b, me, snap = scene()
        sc = scores()
        b.power_commit(10.0, me, snap, sc, True)                                 # shot at in the last 2 s
        self.assertEqual(sc, scores())
        b, me, snap = scene()
        b.per.beliefs[4] = Belief(Vec(5, 3, 0), Vec(), 10.0 - botmod.POWER_COMMIT_FRESH - 0.1, False, "radar")
        sc = scores()
        b.power_commit(10.0, me, snap, sc, False)                                # an old dot: not close now
        self.assertGreater(sc[("item", ROCKETS)], 3.0)

    def test_only_a_power_weapon_still_scored_on_foot(self):
        b, me, snap = scene(goal=("item", RIFLE))
        sc = scores()
        sc[("item", RIFLE)] = 1.6
        b.power_commit(10.0, me, snap, sc, False)
        self.assertEqual(sc[("item", RIFLE)], 1.6)                               # a DMR: no commitment
        b, me, snap = scene()
        sc = scores()
        del sc[("item", ROCKETS)]                                                # taken, or given up as unreachable
        b.power_commit(10.0, me, snap, sc, False)
        self.assertNotIn(("item", ROCKETS), sc)
        for attr, val in (("vehicle", 7), ("has_flag", True)):
            b, me, snap = scene()
            setattr(me, attr, val)
            sc = scores()
            b.power_commit(10.0, me, snap, sc, False)
            self.assertEqual(sc, scores(), attr)
        b, me, snap = scene()
        sc = scores()
        with mock.patch.object(botmod, "POWER_COMMIT", False):
            b.power_commit(10.0, me, snap, sc, False)
        self.assertEqual(sc, scores())

    def test_a_run_too_long_is_let_go(self):
        b, me, snap = scene()
        b.power_commit(10.0, me, snap, scores(), False)
        sc = scores()
        b.power_commit(10.0 + botmod.POWER_COMMIT_MAX + 0.1, me, snap, sc, False)
        self.assertEqual(sc, scores())
        b.goal = ("hunt", Vec(5, 5, 0))                                          # a new run starts a new clock
        b.power_commit(40.0, me, snap, scores(), False)
        b.goal = ("item", ROCKETS)
        sc = scores()
        b.power_commit(41.0, me, snap, sc, False)
        self.assertGreater(sc[("item", ROCKETS)], 3.0)

    def test_wired_into_decide_before_the_flip_flop_rule(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index("    def decide(s, now, me, snap):")
        body = src[i:src.index("\n    def ", i + 10)]
        self.assertLess(body.index("s.power_commit(now, me, snap, scores, hit_recent)"),
                        body.index("scores[s.goal] += 0.2"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
