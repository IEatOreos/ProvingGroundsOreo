"""(custom, Nov 23) Reach's one-bomb Assault team pushes (brain/director.py Director.bomb_push). The owner: "I want the bots
on attack to notice when there is 15 seconds or less on the game clock ... sudden death starts if youre holding the bomb
when the game clock hits zero ... teams to notice when 3-4 players are dead on defense and the team director does a push
order ... when the bomb is within 3-5u of the plant site, have everyone urgently push/fight to plant it"; "make it neutral
and one bomb", "yes do 75%"."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.core import PlayerState, Snapshot, Vec           # noqa: E402
from brain.director import Director                         # noqa: E402

GOAL = Vec(100, 0, 0)          # team 1's goal: team 0 attacks it


def director(team=0, name="reach_45_launch_station"):
    d = Director.__new__(Director)
    d.team = d.side = team
    d.map = dict(name=name)
    return d


def scene(bomb=Vec(50, 0, 0), carrier=None, left=120.0, dead=0, armed=None, neutral=True, goals=None):
    """Team 0 (ids 0-3) attacks, team 1 (ids 4-7) defends; `dead` of the defenders down."""
    players = [PlayerState(i, 0, f"a{i}", Vec(10, i, 0)) for i in range(4)]
    players += [PlayerState(4 + i, 1, f"d{i}", Vec(95, i, 0)) for i in range(4)]
    for p in players[4:4 + dead]:
        p.alive = False
    if carrier is not None:
        players[carrier].has_flag = True
        players[carrier].pos = bomb
    s = Snapshot(100, players)
    s.mode, s.time_left = "assault", left
    s.obj_items = [dict(pos=bomb, carrier=carrier, team=8 if neutral else 0, armed=armed)]
    s.obj_goals = {1: [GOAL]} if goals is None else goals
    return s


class BombPush(unittest.TestCase):
    def test_nothing_in_a_normal_moment(self):
        self.assertIsNone(director().bomb_push(scene()))
        self.assertIsNone(director().bomb_push(scene(carrier=0)))

    def test_at_the_plant_site(self):
        self.assertEqual(director().bomb_push(scene(bomb=Vec(96, 0, 0), carrier=0)), (GOAL, "bomb: at the plant site"))
        self.assertIsNone(director().bomb_push(scene(bomb=Vec(94, 0, 0), carrier=0)))      # 6 u: not yet

    def test_the_last_seconds_with_the_bomb(self):
        self.assertEqual(director().bomb_push(scene(carrier=0, left=15.0)), (GOAL, "bomb: the last seconds"))
        self.assertIsNone(director().bomb_push(scene(carrier=0, left=16.0)))

    def test_sudden_death(self):
        self.assertEqual(director().bomb_push(scene(carrier=0, left=0.0)), (GOAL, "bomb: sudden death"))

    def test_the_last_seconds_loose_bomb(self):
        self.assertEqual(director().bomb_push(scene(left=10.0)), (Vec(50, 0, 0), "bomb: the last seconds, take it"))
        self.assertEqual(director().bomb_push(scene(left=0.0)), (Vec(50, 0, 0), "bomb: the last seconds, take it"))

    def test_their_carrier_with_the_bomb(self):
        # (One Bomb: a defender picked it up, carrier 4) the last seconds are no push of ours
        self.assertIsNone(director().bomb_push(scene(carrier=4, left=10.0)))

    def test_three_of_four_defenders_dead(self):
        self.assertEqual(director().bomb_push(scene(carrier=0, dead=3)), (GOAL, "bomb: their defense is down"))
        self.assertEqual(director().bomb_push(scene(dead=3)), (Vec(50, 0, 0), "bomb: their defense is down"))
        self.assertIsNone(director().bomb_push(scene(dead=2)))          # half: not 75%

    def test_not_when_defending(self):
        # team 1 has no goal of team 0's to plant on
        self.assertIsNone(director(team=1).bomb_push(scene(carrier=4, left=5.0, dead=0)))
        self.assertIsNone(director(team=1).bomb_push(scene(left=5.0)))

    def test_not_once_armed(self):
        self.assertIsNone(director().bomb_push(scene(bomb=GOAL, armed=0.0, left=5.0, dead=3)))

    def test_reach_only(self):
        self.assertIsNone(director(name="guardian").bomb_push(scene(carrier=0, left=5.0)))

    def test_two_bomb_assault_left_alone(self):
        s = scene(carrier=0, left=5.0, neutral=False, goals={0: [Vec(0, 0, 0)], 1: [GOAL]})
        s.obj_items.append(dict(pos=Vec(20, 0, 0), carrier=None, team=1, armed=None))
        self.assertIsNone(director().bomb_push(s))

    def test_one_bomb(self):
        # One Bomb: the attackers' bomb (team 0), one goal (theirs)
        self.assertEqual(director().bomb_push(scene(carrier=0, left=5.0, neutral=False)), (GOAL, "bomb: the last seconds"))

    def test_sudden_death_is_overtime(self):
        self.assertTrue(Director.overtime(scene(left=0.0)))
        self.assertFalse(Director.overtime(scene(left=10.0)))
        self.assertFalse(Director.overtime(scene(left=None)))


class Blitz(unittest.TestCase):
    """blitz_tick: a bomb push goes at once (no rally), and never waits out the cool-down."""

    def team(self, d, snap):
        d.bots = {}
        for p in snap.players[:4]:
            if p.has_flag:
                continue
            b = SimpleNamespace(id=p.id, p=SimpleNamespace(teamwork=1.0), order=SimpleNamespace(role="slayer"),
                                blitz_until=0.0)
            d.bots[p.id] = b
        return d

    def start(self, snap, cool=0.0):
        d = self.team(director(), snap)
        d.blitz, d.blitz_cool, d.events = None, cool, []
        d.event = lambda now, kind, text: d.events.append(text)
        d.blitz_rally = lambda c, target: c
        d.blitz_prongs = lambda rally, target: []
        d.blitz_holds = lambda snap, team: {}
        stop = RuntimeError("past the start")

        def holds(*a):
            raise stop
        d.blitz_holds = holds
        try:
            d.blitz_tick(10.0, snap)
        except RuntimeError as e:
            if e is not stop:
                raise
        return d

    def test_goes_at_once(self):
        snap = scene(carrier=0, left=10.0)
        for p in snap.players[1:4]:
            p.pos = Vec(-60 + 30 * p.id, 40 * p.id, 0)      # strung out, far from the goal: a rally otherwise
        d = self.start(snap)
        self.assertEqual(d.blitz["why"], "bomb: the last seconds")
        self.assertEqual(d.blitz["go"], 10.0)

    def test_no_cool_down(self):
        d = self.start(scene(bomb=Vec(97, 0, 0), carrier=0, left=10.0), cool=25.0)
        self.assertIsNotNone(d.blitz)
        self.assertEqual(d.blitz["why"], "bomb: at the plant site")


if __name__ == "__main__":
    unittest.main()
