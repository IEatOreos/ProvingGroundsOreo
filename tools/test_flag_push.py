"""(custom, Nov 27) CTF's "their defense is down" push (brain/director.py Director.flag_push), and both it and Assault's
(bomb_push) at 8v8: 3 of 4 of the other team dead, 5 of 8 with eight. The owner: "Do the same logic for Ctf as well. And
Add it to 8v8 logic as well", "Sorry, Make 5 of 8 trigger it for 8v8"."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain.core import FlagState, PlayerState, Snapshot, Vec  # noqa: E402
from brain.director import Director  # noqa: E402

OUR, THEIR = Vec(0, 0, 0), Vec(100, 0, 0)        # the stands: ours (team 0) and theirs (team 1)


def director(team=0, name="reach_45_launch_station"):
    d = Director.__new__(Director)
    d.team = d.side = team
    d.map = dict(name=name)
    return d


def ctf(per=4, dead=0, their_flag="home", our_flag="home", carrier=None, one_flag=None):
    players = [PlayerState(i, 0, f"a{i}", Vec(10, i, 0)) for i in range(per)]
    players += [PlayerState(per + i, 1, f"d{i}", Vec(95, i, 0)) for i in range(per)]
    for p in players[per:per + dead]:
        p.alive = False
    s = Snapshot(100, players, mode="ctf")
    flags = {0: FlagState(0, OUR, OUR, our_flag, carrier if our_flag == "carried" else -1),
             1: FlagState(1, THEIR, Vec(90, 0, 0) if their_flag == "dropped" else THEIR, their_flag)}
    s.flags = {one_flag: flags[one_flag]} if one_flag is not None else flags
    if carrier is not None:
        players[carrier].has_flag = True
    return s


class FlagPush(unittest.TestCase):
    def test_three_of_four_dead_all_take_their_flag(self):
        self.assertEqual(director().flag_push(ctf(dead=3)), (THEIR, "flag: their defense is down"))
        self.assertEqual(director().flag_push(ctf(dead=3, their_flag="dropped")), (Vec(90, 0, 0), "flag: their defense is down"))
        self.assertIsNone(director().flag_push(ctf(dead=2)))                 # (half: not 75%)

    def test_eight_v_eight_five_of_eight(self):
        self.assertEqual(director().flag_push(ctf(per=8, dead=5)), (THEIR, "flag: their defense is down"))
        self.assertIsNone(director().flag_push(ctf(per=8, dead=4)))

    def test_ours_back_first(self):
        s = ctf(dead=3, our_flag="carried", carrier=7)          # (the one of theirs standing has our flag)
        s.players[7].pos = Vec(40, 0, 0)
        self.assertEqual(director().flag_push(s), (Vec(40, 0, 0), "flag: their team is down, ours back"))

    def test_one_flag(self):
        # (their flag the only one: we attack it; ours the only one: we defend, a push only after a carrier)
        self.assertEqual(director().flag_push(ctf(dead=3, one_flag=1)), (THEIR, "flag: their defense is down"))
        self.assertIsNone(director().flag_push(ctf(dead=3, one_flag=0)))

    def test_carried_by_us_or_not_ctf(self):
        self.assertIsNone(director().flag_push(ctf(dead=3, their_flag="carried")))   # (ours has it: his plan)
        s = ctf(dead=3)
        s.mode = "slayer"
        self.assertIsNone(director().flag_push(s))


class BombPushEightVEight(unittest.TestCase):
    def scene(self, dead):
        players = [PlayerState(i, 0, f"a{i}", Vec(10, i, 0)) for i in range(8)]
        players += [PlayerState(8 + i, 1, f"d{i}", Vec(95, i, 0)) for i in range(8)]
        for p in players[8:8 + dead]:
            p.alive = False
        s = Snapshot(100, players, mode="assault")
        s.time_left = 120.0
        s.obj_items = [dict(pos=Vec(50, 0, 0), carrier=None, team=8, armed=None)]
        s.obj_goals = {1: [THEIR]}
        return s

    def test_five_of_eight_defenders_dead(self):
        self.assertEqual(director().bomb_push(self.scene(5)), (Vec(50, 0, 0), "bomb: their defense is down"))
        self.assertIsNone(director().bomb_push(self.scene(4)))


if __name__ == "__main__":
    unittest.main()
