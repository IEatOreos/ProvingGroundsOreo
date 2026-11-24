"""(custom, Nov 23) A CTF carrier waiting for his own flag to come home waits on his own half (brain/director.py
home_posts, carry_point). The owner's 8v8 CTF on a new Forge World layout (20261123-182210): "My driver drove me back to
their base when I was carrying flag", "Why do the rrun it backwards?": its holds were the blank canvas's, ours 300 u off
the layout (the ferry's target (64.8, 207.4)) and theirs at (-58, -205), (-53, -202), (-62, -200), behind our base; the
layout's own strategy gives both teams one list of holds."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import FlagState, PlayerState, Snapshot, Vec   # noqa: E402
from brain.director import Director                             # noqa: E402

STAND = {0: Vec(-50.1, -188.0, 2.9), 1: Vec(-50.1, -92.2, 2.9)}     # (team 0's base south, team 1's north)
CANVAS = {0: [Vec(61, 210, 45), Vec(55, 208, 45), Vec(65, 207, 45)], 1: [Vec(-58, -205, 3), Vec(-53, -202, 2),
                                                                        Vec(-62, -200, 3)]}
SHARED = [Vec(-29, -194, 5), Vec(-60, -135, 5), Vec(-32, -127, 5), Vec(-48, -199, 4)]


def director(side, holds):
    d = Director.__new__(Director)
    d.team = d.side = side
    d.home_rule = True
    d.map = dict(flags=dict(STAND), returns=dict(STAND), holds=holds, points={"mid": Vec(-50, -140, 3)})
    d.posture = SimpleNamespace(state="even")
    d.is_one_flag = lambda snap: False
    return d


def snap(side, own_state="carried"):
    s = Snapshot(100, [PlayerState(1, side, "carrier", Vec(-50, -180 if side == 1 else -100, 3))], mode="ctf")
    s.players[0].has_flag = True
    own_at = Vec(-50, -150, 3)
    s.flags = {side: FlagState(side, STAND[side], own_at, own_state, 9),
               1 - side: FlagState(1 - side, STAND[1 - side], s.players[0].pos, "carried", 1)}
    return s


class HomePosts(unittest.TestCase):
    def test_their_canvas_holds_are_no_post(self):
        d = director(1, CANVAS)
        self.assertEqual(d.home_posts(snap(1)), [])
        self.assertEqual(d.carry_point(snap(1)), STAND[1])         # (the stand: not behind the enemy's base)

    def test_ours_300_u_off_are_no_post(self):
        d = director(0, CANVAS)
        self.assertEqual(d.carry_point(snap(0)), STAND[0])         # (the ferry's target, was (64.8, 207.4))

    def test_shared_holds_on_our_half_only(self):
        self.assertEqual(director(0, {0: SHARED, 1: SHARED}).home_posts(snap(0)), [Vec(-48, -199, 4)])
        self.assertEqual(director(1, {0: SHARED, 1: SHARED}).home_posts(snap(1)), [Vec(-32, -127, 5)])

    def test_our_flag_home_the_stand_as_before(self):
        d = director(0, {0: SHARED, 1: SHARED})
        self.assertEqual(d.carry_point(snap(0, own_state="home")), STAND[0])


if __name__ == "__main__":
    unittest.main()
