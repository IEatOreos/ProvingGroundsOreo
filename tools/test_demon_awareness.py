"""Real perception cone boundaries and configured recognition delays."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Perception
from brain.core import PlayerState, Snapshot, Vec
from brain.profiles import make_profile


class DemonAwarenessTests(unittest.TestCase):
    def perception(self, tier, angle, distance=10):
        p = Perception(make_profile(tier, 'rusher', random.Random(2)), random.Random(4))
        me = PlayerState(0, 0, 'bot', Vec())
        a = math.radians(angle)
        enemy = PlayerState(1, 1, 'enemy', Vec(distance*math.cos(a), distance*math.sin(a), 0))
        snap = Snapshot(10, [me, enemy])
        return p, me, enemy, snap

    def test_demon_full_cone_and_edges_have_zero_configured_delay(self):
        for angle in (-90.1, -89.9, -70.1, -60, 0, 60, 70.1, 89.9, 90.1):
            p, me, _, snap = self.perception('demon', angle)
            p.update(10, me, snap, lambda *a: True, [])
            if abs(angle) < 90:
                self.assertEqual(p.pending[1], 10)
                p.update(10, me, snap, lambda *a: True, [])
                self.assertIn(1, p.visible_enemies())
            else:
                self.assertNotIn(1, p.pending)

    def test_legendary_cone_stays_120_degrees(self):
        p, me, _, snap = self.perception('top', 65)
        p.update(10, me, snap, lambda *a: True, [])
        self.assertNotIn(1, p.pending)

    def test_demon_always_notices_eligible_radar_and_respects_restrictions(self):
        for restriction in (None, 'range', 'crouch', 'stationary', 'jammed', 'disabled'):
            for seed in range(20):
                p, me, enemy, snap = self.perception('demon', 180, 26 if restriction == 'range' else 10)
                p.rng = random.Random(seed)
                me.tracker = restriction != 'disabled'
                enemy.vel = Vec() if restriction == 'stationary' else Vec(1, 0, 0)
                enemy.crouching = restriction == 'crouch'
                p.jammed = restriction == 'jammed'
                p.update(10, me, snap, lambda *a: False, [])
                self.assertEqual(1 in p.beliefs, restriction is None)
                if restriction is None:
                    self.assertEqual(p.beliefs[1].source, 'radar')


if __name__ == '__main__':
    unittest.main()
