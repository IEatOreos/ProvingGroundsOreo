"""(custom, Nov 23) The real-rules Slayer sim's own rules (tools/real_sim.py): the armor abilities' buttons and meters as
the game takes them, armor lock's block, sprint's speed, frags on the level's floors, a suicide's point, the time
limit. The owner: "Follow the real games rules", "All of it"."""
import math
import sys
import types
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import real_sim as R  # noqa: E402
from brain import equipment as EQ  # noqa: E402
from brain.core import Action, Vec  # noqa: E402


def match(now=10.0):
    m = R.RealMatch.__new__(R.RealMatch)
    m.now, m.stats, m.score, m.limit, m.time_limit = now, __import__("collections").Counter(), {0: 0, 1: 0}, 50, 720.0
    m.frags, m.nade_h = [], 0
    return m


def man(kind):
    o = types.SimpleNamespace(id=1, team=0, alive=True, vehicle=-1, pos=Vec(), vel=Vec(), yaw=0.0, pitch=0.0)
    o.kind, o.energy = kind, EQ.Energy(R.GAME, kind)
    o.on, o.lock_since, o.camo_want, o.eq_was, o.reveal_until = False, None, False, False, 0.0
    o.frags, o.nade_ready, o.nade_was, o.throw_at = 2, 0.0, False, None
    o.air, o.v3, o.jump_was = False, [0.0, 0.0, 0.0], False
    return o


class AbilityTests(unittest.TestCase):
    def test_hold_kinds_need_the_held_bit(self):
        m, o = match(), man("jetpack")
        m.ability(o, Action(equipment=True))                    # (no act.ability: live, it never came on)
        self.assertFalse(o.on)
        m.ability(o, Action(equipment=True, ability=True))
        self.assertTrue(o.on)

    def test_armor_lock_after_its_warmup_then_blocks(self):
        m, o = match(), man("armor_lock")
        a = Action(equipment=True, ability=True)
        m.ability(o, a)
        self.assertFalse(o.on)                                  # (0.15 s warmup)
        for k in range(6):
            m.now += R.BS.DT
            m.ability(o, a)
        self.assertTrue(o.on)
        before = o.energy.level
        m.now += 1.0
        m.ability(o, a)
        self.assertLess(o.energy.level, before)                 # (its tag's drain)

    def test_camo_toggles_on_a_press(self):
        m, o = match(), man("active_camo")
        m.ability(o, Action(equipment=True))
        self.assertTrue(o.on)
        m.ability(o, Action())
        self.assertTrue(o.on)                                   # (a toggle: stays on)
        m.ability(o, Action(equipment=True))
        self.assertFalse(o.on)

    def test_sprint_starts_at_full_stick_and_runs_on(self):
        m, o = match(), man("sprint")
        m.ability(o, Action(equipment=True, forward=0.5))
        self.assertFalse(o.on)
        m.ability(o, Action(forward=1.0))
        m.ability(o, Action(equipment=True, forward=1.0))
        self.assertTrue(o.on)
        m.ability(o, Action(forward=1.0))
        self.assertTrue(o.on)                                   # (let go: it runs on, as live)
        m.ability(o, Action(equipment=True, forward=1.0))
        self.assertFalse(o.on)                                  # (a second press ends it)
        m.ability(o, Action(forward=1.0))
        m.ability(o, Action(equipment=True, forward=1.0))
        m.ability(o, Action(forward=0.2))
        self.assertFalse(o.on)                                  # (the stick off forward)

    def test_hologram_spends_the_meter(self):
        m, o = match(), man("hologram")
        m.ability(o, Action(equipment=True, ability=True))
        self.assertEqual(m.stats["holograms"], 1)
        self.assertFalse(o.on)                                  # (no lasting on: a bot never sees it, as live)
        self.assertLess(o.energy.level, 0.01)


class RuleTests(unittest.TestCase):
    def test_time_limit_and_score(self):
        m = match(now=719.0)
        self.assertFalse(m.over())
        m.now = 720.0
        self.assertTrue(m.over())
        m = match()
        m.score[1] = 50
        self.assertTrue(m.over())

    def test_floor_crossed(self):
        T = types.SimpleNamespace(x0=0.0, y0=0.0, nh=4, nw=4, L=2, nstep=1)
        T.lz = np.full((2, 4, 4), np.nan)
        T.lz[0], T.lz[1] = 0.0, 3.0                              # (a floor at 0, a ledge over it at 3)
        T.top = np.full((4, 4), 9999.0)
        self.assertEqual(R.floor_crossed(T, 0.5, 0.5, 3.5, 2.9), 3.0)
        self.assertEqual(R.floor_crossed(T, 0.5, 0.5, 2.0, -0.2), 0.0)
        self.assertIsNone(R.floor_crossed(T, 0.5, 0.5, 2.0, 1.0))

    def test_reach_numbers(self):
        self.assertAlmostEqual(R.PHYS.v0, 2.346, places=3)            # (jumpphys: fitted to live arcs)
        self.assertGreater(R.NADE_SPEED, 5.0)                          # (the bots' own throws, nade.model)
        self.assertEqual(R.ABILITIES, ("sprint", "jetpack", "armor_lock", "active_camo", "hologram"))
        self.assertGreater(R.SPRINT, R.BS.WALK)


if __name__ == "__main__":
    unittest.main()
