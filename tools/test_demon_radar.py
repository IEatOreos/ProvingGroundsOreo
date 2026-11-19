"""(custom, Nov 18) Demon's radar attention by threat on the map (Bot.radar_threat, open_dots, demon_break_second's
radar second man). The owner: "only watch the dot on the radar ... if the bot cant see someone else, or is getting shot
or in a fight", and "if one is behind the wall and the other cant see him what happens then?"."""
import math
import random
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot as botmod                                # noqa: E402
from brain.bot import Belief, Bot                              # noqa: E402
from brain.core import PlayerState, Snapshot, Vec              # noqa: E402
from brain.profiles import make_profile                        # noqa: E402
from test_h4_pickup_board import Flat                          # noqa: E402


class Walls(Flat):
    """Open only to the men listed (by where they stand: x rounded)."""
    def __init__(s, open_x=()):
        s.open_x = set(open_x)

    def los(s, a, b, mode=None):
        return round(a.x) in s.open_x or round(b.x) in s.open_x


def scene(tier="demon", dots=(), open_x=(), corners=None):
    b = Bot(0, 0, make_profile(tier, "rusher", random.Random(2)), {"name": "reach_test"}, random.Random(4))
    b.notes = []
    t = Walls(open_x)
    b.T = lambda: t
    b.guess = lambda now, me, k, bel: bel.pos
    me = PlayerState(0, 0, "bot", Vec(), yaw=0.0)
    for k, (pos, src) in dots.items() if isinstance(dots, dict) else ():
        b.per.beliefs[k] = Belief(pos, Vec(), 9.9, False, src)
    corners = corners or {}
    b.dot_corner = lambda now, me_, k, g: (corners[k], None, None) if k in corners else (None, None, None)
    return b, me


def known(b):
    return list(b.per.beliefs.items())


class RankTests(unittest.TestCase):
    def test_open_line_first_over_a_nearer_one_behind_a_wall(self):
        b, me = scene(dots={1: (Vec(-4, 0, 0), "radar"), 2: (Vec(12, 0, 0), "radar")}, open_x=(12,),
                      corners={1: Vec(-2, 3, 0)})
        att, look = b.radar_threat(10.0, me, known(b))
        self.assertEqual(att[:2], ["radar", "#2 open"])
        self.assertAlmostEqual(look.x, 12.0)

    def test_behind_walls_the_one_soonest_round_his_corner_its_corner_watched(self):
        # #1 is nearer but 9 u from his corner; #2 farther, 2 u from his: #2 comes into view first
        b, me = scene(dots={1: (Vec(-5, 0, 0), "radar"), 2: (Vec(10, 0, 0), "team")},
                      corners={1: Vec(-5, 9, 0), 2: Vec(8, 0, 0)})
        att, look = b.radar_threat(10.0, me, known(b))
        self.assertEqual(att[1], "#2 corner")
        self.assertEqual((look.x, look.y), (8.0, 0.0))                  # the corner, not through the wall at him

    def test_a_long_way_round_is_left_eyes_on_the_way(self):
        b, me = scene(dots={1: (Vec(15, 0, 0), "radar")}, corners={1: Vec(2, 14, 0)})   # 18 u round: 7 s
        self.assertIsNone(b.radar_threat(10.0, me, known(b)))
        b, me = scene(dots={1: (Vec(15, 0, 0), "radar")})              # no corner, past DOT_NEAR_R
        self.assertIsNone(b.radar_threat(10.0, me, known(b), nav=lambda a, q: q))

    def test_a_way_that_turns_out_of_sight_right_by_us_is_watched_down_it(self):
        # (98.6 s of the owner's match: both men 6 u off, their ways round the doorway it stood in, no corner 2 u out)
        b, me = scene(dots={1: (Vec(-6.5, 0, 0), "radar"), 2: (Vec(6.1, 0, 0), "radar")})
        ways = {1: (None, 9.0, Vec(-1, 1, 0)), 2: (None, 7.25, Vec(1, 1, 0))}
        b.dot_corner = lambda now, me_, k, g: ways[k]
        att, look = b.radar_threat(10.0, me, known(b))
        self.assertEqual(att[1], "#2 way")                                # the shorter walk into view
        self.assertGreater(look.x, 0.0)

    def test_one_new_walk_a_tick(self):
        b, me = scene(dots={1: (Vec(-5, 0, 0), "radar"), 2: (Vec(10, 0, 0), "radar")})
        del b.dot_corner                                                   # the real one, on a made-up level
        calls = []

        def path_ahead(a, q, n=80, **kw):
            calls.append(q.x)
            return [Vec(q.x * i / 8.0, 0, 0) for i in range(1, 9)]
        b.T().path_ahead = path_ahead
        b.radar_threat(10.0, me, known(b))
        self.assertEqual(len(calls), 1)                                    # the other waits a tick
        b.radar_threat(10.034, me, known(b))
        self.assertEqual(len(calls), 2)
        b.radar_threat(10.068, me, known(b))
        self.assertEqual(len(calls), 2)                                    # both kept now

    def test_close_with_no_corner_the_way_he_would_come(self):
        b, me = scene(dots={1: (Vec(4, 0, 0), "radar")})
        att, look = b.radar_threat(10.0, me, known(b), nav=lambda a, q: q)
        self.assertEqual(att[1], "#1 way")

    def test_the_one_watched_held_until_another_is_clearly_sooner(self):
        b, me = scene(dots={1: (Vec(-5, 0, 0), "radar"), 2: (Vec(10, 0, 0), "radar")},
                      corners={1: Vec(-5, 2, 0), 2: Vec(10, 3, 0)})     # 0.8 s and 1.2 s
        self.assertEqual(b.radar_threat(10.0, me, known(b))[0][1], "#1 corner")
        corners = {1: Vec(-5, 2.5, 0), 2: Vec(10, 2.0, 0)}              # now 1.0 s and 0.8 s: under DOT_SWITCH
        b.dot_corner = lambda now, me_, k, g: (corners[k], None, None)
        self.assertEqual(b.radar_threat(10.1, me, known(b))[0][1], "#1 corner")
        corners[2] = Vec(10, 0.5, 0)                                     # 0.2 s: clearly sooner
        self.assertEqual(b.radar_threat(10.2, me, known(b))[0][1], "#2 corner")

    def test_only_the_two_nearest_fresh_dots_of_demon(self):
        b, me = scene(dots={1: (Vec(-5, 0, 0), "radar"), 2: (Vec(6, 0, 0), "radar"), 3: (Vec(7, 1, 0), "radar"),
                            4: (Vec(9, 0, 0), "radar")},
                      open_x=(9,), corners={1: Vec(-5, 1, 0), 2: Vec(6, 1, 0), 3: Vec(7, 2, 0)})
        self.assertEqual(botmod.DOT_RANKED, 3)
        self.assertNotEqual(b.radar_threat(10.0, me, known(b))[0][1], "#4 open")   # the fourth nearest not ranked
        b, me = scene(dots={1: (Vec(-5, 0, 0), "radar")}, open_x=(-5,))
        b.per.beliefs[1].t = 10.0 - botmod.DOT_FRESH - 0.1
        self.assertIsNone(b.radar_threat(10.0, me, known(b)))           # stale
        b, me = scene(dots={1: (Vec(-5, 0, 0), "heard")}, open_x=(-5,))
        self.assertIsNone(b.radar_threat(10.0, me, known(b)))           # a shot heard: not a dot
        for tier in ("top", "strong", "blind"):
            b, me = scene(tier=tier, dots={1: (Vec(-5, 0, 0), "radar")}, open_x=(-5,))
            self.assertIsNone(b.radar_threat(10.0, me, known(b)), tier)
        # (Nov 18, owner: "Give mythic the same ruleset as demons") Mythic watches the dot too (profiles.demon_rules)
        b, me = scene(tier="mythic", dots={1: (Vec(-5, 0, 0), "radar")}, open_x=(-5,))
        self.assertIsNotNone(b.radar_threat(10.0, me, known(b)))
        b, me = scene(dots={1: (Vec(-5, 0, 0), "radar")}, open_x=(-5,))
        with mock.patch.object(botmod, "DEMON_RADAR", False):
            self.assertIsNone(b.radar_threat(10.0, me, known(b)))
        me.has_flag = True
        self.assertIsNone(b.radar_threat(10.0, me, known(b)))


class LookTests(unittest.TestCase):
    def test_look_point_takes_the_radar_threat_but_not_over_a_man_seen_or_a_hit(self):
        b, me = scene(dots={1: (Vec(-5, 0, 0), "radar")}, open_x=(-5,))
        b.now = 10.0
        b.arrival = lambda now, me_: None           # (no launches on the test level)
        b.tele_watching = lambda now: None
        b.look_point(me, Vec(10, 0, 0), nav=lambda a, q: q)
        self.assertEqual(b.att[:2], ["radar", "#1 open"])
        b.per.beliefs[2] = Belief(Vec(6, 6, 0), Vec(), 10.0, True, "eyes")      # a man in view: him
        b.look_point(me, Vec(10, 0, 0), nav=lambda a, q: q)
        self.assertNotEqual(b.att[0], "radar")
        del b.per.beliefs[2]
        b.per.beliefs[3] = Belief(Vec(0, 8, 0), Vec(), 10.0, False, "hit")      # shot at: the hit
        b.look_point(me, Vec(10, 0, 0), nav=lambda a, q: q)
        self.assertEqual(b.att[:2], ["watch", "#3 hit"])

    def test_wired_free_of_the_walk_cone_and_the_slow_turn(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index("    def plan(s, now, dt, snap, los, nav, callouts, items=None):")
        body = src[i:src.index("    def ", i + 10)]
        self.assertIn('and not (s.att and s.att[0] == "radar")', body)          # full speed on its way
        self.assertIn('s.att[0] in ("watch", "post", "flank")', body)           # the cone: not for "radar"


class FightTests(unittest.TestCase):
    def fight(self, dot_at=Vec(-6, 4, 0), open_=True, age=0.2, team=1):
        b, me = scene(open_x=(round(dot_at.x),) if open_ else ())
        foe = PlayerState(5, 1, "foe", Vec(10, 0, 0), yaw=math.pi)           # in view, facing it
        dot = PlayerState(6, team, "dot", dot_at, yaw=0.0)
        snap = Snapshot(10.0, [me, foe, dot], mode="slayer")
        b.per.beliefs[5] = Belief(foe.pos, Vec(), 10.0, True, "eyes")
        b.per.beliefs[6] = Belief(dot_at, Vec(), 10.0 - age, False, "radar")
        b.goal = ("fight", 5)
        return b, me, snap

    def test_open_dots(self):
        b, me, snap = self.fight()
        self.assertEqual(list(b.open_dots(10.0, me, snap, [5])), [6])
        for kw in (dict(open_=False), dict(age=botmod.DOT_BREAK_FRESH + 0.1), dict(team=0)):
            b, me, snap = self.fight(**kw)
            self.assertEqual(b.open_dots(10.0, me, snap, [5]), {}, kw)

    def test_a_dot_with_a_line_on_it_is_the_second_man(self):
        b, me, snap = self.fight()
        spot = Vec(1.5, -2.0, 0)
        scores = {("fight", 5): 2.0}
        with mock.patch.object(Bot, "break_point", return_value=spot) as bp, \
                mock.patch.object(Bot, "finishing", return_value=False):
            b.demon_break_second(10.0, me, snap, scores, [5])
        self.assertEqual(scores.get(("retreat", spot)), botmod.DEMON_BREAK_SCORE)
        self.assertNotIn(("fight", 5), scores)
        others = bp.call_args[0][1]
        self.assertEqual([(q.x, q.y) for q in others], [(-6.0, 4.0)])          # out of the dot's line
        self.assertEqual(bp.call_args[0][2].x, 10.0)                             # the man it fights still sees it
        b, me, snap = self.fight(open_=False)                                    # behind a wall: the duel goes on
        scores = {("fight", 5): 2.0}
        with mock.patch.object(Bot, "break_point", return_value=spot), \
                mock.patch.object(Bot, "finishing", return_value=False):
            b.demon_break_second(10.0, me, snap, scores, [5])
        self.assertEqual(scores, {("fight", 5): 2.0})


if __name__ == "__main__":
    unittest.main(verbosity=2)
