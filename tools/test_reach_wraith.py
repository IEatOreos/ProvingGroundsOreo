"""(custom, Nov 24) Reach's Wraith driven as the campaign's (HREK ai\\generic.character): fights from a stop at 8-16 u,
drives in from farther, charges inside 8 u (10 s between charges), turtles when hurt, no mortar inside 4 u."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.bot import Belief
from brain.core import PlayerState, Vec
from brain.equipment import game_of
from test_mongoose_transport import scene, drive


def fight(kind='wraith', game='reach'):
    d, b, me, snap = scene(kind)
    if game != 'reach':
        b.map['name'] = game + '_test'
        b.game = game_of(b.map['name'])
    enemy = PlayerState(1, 1, 'enemy', Vec(12, 0, 0), weapon='assault_rifle')
    snap.players.append(enemy)
    b.per.recognized.add(1)
    return b, me, snap, enemy


def at(b, enemy, x, now=100.0):
    enemy.pos = Vec(x, 0, 0)
    b.per.beliefs[1] = Belief(enemy.pos, Vec(), now, True, 'eyes')


class ReachWraithTests(unittest.TestCase):
    def test_fights_from_a_stop_in_range_and_drives_in_from_farther(self):
        b, me, snap, enemy = fight()
        at(b, enemy, 12)
        act = drive(b, me, snap)
        self.assertEqual((act.forward, act.strafe), (0.0, 0.0))
        at(b, enemy, 30, now=100.1)
        act = drive(b, me, snap, now=100.1)
        self.assertEqual(act.forward, 1.0)
        self.assertEqual(act.strafe, 0.0)

    def test_charges_inside_8_and_waits_10_s_for_the_next(self):
        b, me, snap, enemy = fight()
        at(b, enemy, 7)
        act = drive(b, me, snap)
        self.assertEqual(b.att[0], 'charge')
        self.assertEqual(act.forward, 1.0)
        at(b, enemy, 11, now=101)                 # (past the abort distance: over)
        drive(b, me, snap, now=101)
        self.assertIsNone(b.wraith_charge)
        at(b, enemy, 7, now=105)                  # (inside 8 again, 4 s on: no new charge yet, it holds)
        act = drive(b, me, snap, now=105)
        self.assertNotEqual(b.att[0], 'charge')
        self.assertEqual(act.forward, 0.0)
        at(b, enemy, 7, now=111.5)                # (10 s after the last one ended: charges again)
        drive(b, me, snap, now=111.5)
        self.assertEqual(b.att[0], 'charge')

    def test_a_boarder_on_foot_is_still_run_down(self):
        b, me, snap, enemy = fight()
        at(b, enemy, 4)
        act = drive(b, me, snap)
        self.assertEqual(b.att[0], 'splatter')
        self.assertFalse(act.fire)

    def test_turtles_when_hurt_and_keeps_firing(self):
        b, me, snap, enemy = fight()
        v = snap.vehicles[0]
        v['left'] = 1.0
        at(b, enemy, 12)
        drive(b, me, snap)
        v['left'] = 0.75                          # (a quarter of its body in a second)
        at(b, enemy, 7, now=101)
        act = drive(b, me, snap, now=101)
        self.assertNotEqual(b.att[0], 'charge')   # (no charge while turtling)
        self.assertEqual((act.forward, act.strafe), (0.0, 0.0))
        self.assertIn('vehicle: Wraith hurt, turtling', b.notes)
        self.assertTrue(b.reach_wraith_turtle(105.5, v))      # (5 s from its start: still on)
        v['left'] = 0.7                           # (hit again at 105.5: on to 110.5)
        self.assertTrue(b.reach_wraith_turtle(105.6, v))
        self.assertTrue(b.reach_wraith_turtle(110.0, v))
        self.assertFalse(b.reach_wraith_turtle(110.6, v))     # (over; the next takes a fresh 20%)

    def test_no_mortar_inside_4_u(self):
        b, me, snap, enemy = fight()
        enemy.vehicle = 20                        # (a man in a vehicle: no boarder's run down)
        snap.vehicles.append(dict(handle=20, kind='ghost', pos=(3, 0, 0), occupied=True, team=1, riders=1,
                                  fwd=(-1, 0, 0)))
        b.wraith_charge_next = 200.0              # (no charge: just whether it fires)
        at(b, enemy, 3)
        act = drive(b, me, snap)
        self.assertFalse(act.fire)

    def test_other_games_and_the_scorpion_keep_their_artillery(self):
        for kind, game in (('wraith', 'h3'), ('scorpion', 'reach')):
            b, me, snap, enemy = fight(kind, game)
            at(b, enemy, 12)
            act = drive(b, me, snap)
            self.assertNotEqual(act.strafe, 0.0, (kind, game))   # (holds its range on the move, side on)


if __name__ == '__main__':
    unittest.main()
