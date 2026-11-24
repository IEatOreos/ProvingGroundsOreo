"""(custom, Nov 24) Warthog drivers stay on their way: no dodging aimed rockets, rams only off the nose, boarders fled."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.bot import Belief
from brain.core import PlayerState, Vec
from brain import vehicles
from test_mongoose_transport import scene


def threat(b, snap, pos, weapon, yaw=0.0, vehicle=-1):
    enemy = PlayerState(1, 1, 'enemy', pos, weapon=weapon, yaw=yaw, vehicle=vehicle)
    snap.players.append(enemy)
    b.per.beliefs[1] = Belief(enemy.pos, Vec(), 100, True, 'eyes')
    b.per.recognized.add(1)
    return enemy


def evade_after_reaction(b, me, snap):
    v, sp = snap.vehicles[0], vehicles.spec(snap.vehicles[0]['kind'])
    b.evade(100.0, me, v, sp, snap)
    return b.evade(100.0 + b.p.reaction + 0.1, me, v, sp, snap)


class WarthogPathTests(unittest.TestCase):
    def test_rocket_aimed_at_a_warthog_is_no_dodge(self):
        for kind, dodges in (('warthog', False), ('gauss', False), ('mongoose', True)):
            d, b, me, snap = scene(kind)
            threat(b, snap, Vec(10, 0, 0), 'rockets', yaw=math.pi)    # (pointed straight at it)
            mv = evade_after_reaction(b, me, snap)
            self.assertEqual(mv is not None, dodges, kind)

    def test_a_warthog_still_flees_a_boarder(self):
        d, b, me, snap = scene('warthog')
        b.open_way = lambda me, yaw: yaw
        threat(b, snap, Vec(1.5, 0, 0), 'assault_rifle')
        mv = evade_after_reaction(b, me, snap)
        self.assertIsNotNone(mv)
        self.assertEqual(mv[0], 'away from a boarder')

    def test_a_warthog_rams_only_off_its_nose(self):
        d, b, me, snap = scene('warthog')
        v = snap.vehicles[0]
        ghost = dict(handle=20, kind='ghost', pos=(10, 0, 0), occupied=True, team=1, riders=1, fwd=(-1, 0, 0))
        snap.vehicles.append(ghost)
        st = vehicles.strategy('warthog')
        for pos, ok in ((Vec(10, 0, 0), True), (Vec(0, 10, 0), False), (Vec(-10, 0, 0), False)):
            enemy = PlayerState(1, 1, 'enemy', pos, vehicle=20)
            bel = Belief(pos, Vec(), 100, True, 'eyes')
            self.assertEqual(b.ram_ok(me, v, st, snap, enemy, bel), ok, pos)
            b.ram = (1, 100.0, 0.0)          # (a run already on him: still only off the nose)
            self.assertEqual(b.ram_ok(me, v, st, snap, enemy, bel), ok, pos)
            b.ram = None


if __name__ == '__main__':
    unittest.main()
