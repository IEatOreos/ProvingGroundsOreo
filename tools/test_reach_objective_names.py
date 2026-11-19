"""(custom, Nov 18) Reach's Assault bombs and Oddball ball are found by the map's tag names (LiveReach.OBJECTIVE_NAMES), as
Stockpile's flags are (tools/test_reach_stockpile_flags.py), not learned off a stand or a ball spawn: the first gun lying
on one made every gun of its kind "the bomb" or "the ball" on any map. The owner, Nov 18: the bots don't play Multi Bomb,
Stockpile or Oddball right "even though the map has been scanned" (Sword Base), "I dont want to have to fix every single
map". The places here are Sword Base's own (maps/reach_20_sword_slayer/objects.json), in the Stockpile test's stand-in
for the game's object table read by the real LiveReach."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_reach_stockpile_flags import NAMES, reach   # noqa: E402
from brain.core import Vec                            # noqa: E402

# Sword Base: the bombs' stands (as_bomb: team 1, team 0, neutral) and the ball's spawns (oddball_ball)
BOMB_AT = {0: (-134.5, 32.0, 24.6), 1: (-119.5, 48.8, 26.1), 2: (-128.9, 39.4, 21.9)}
BOMB_STANDS = {k: Vec(*p) for k, p in BOMB_AT.items()}
BALL_SPOTS = {0: Vec(-132.9, 32.1, 26.5), 1: Vec(-117.0, 32.5, 24.5), 2: Vec(-128.6, 39.4, 21.9)}

MY_NAMES = list(NAMES)
MY_NAMES[3120] = "objects\\weapons\\multiplayer\\assault_bomb\\assault_bomb"
MY_NAMES[3121] = "sound\\weapons\\assault_bomb\\arming"
MY_NAMES[3305] = "objects\\weapons\\multiplayer\\skull\\skull"
MY_NAMES[3306] = "objects\\weapons\\multiplayer\\skull\\shaders\\skull"
MY_NAMES[2210] = "objects\\weapons\\pistol\\magnum\\magnum"
BOMB, SKULL, MAGNUM, DMR = 0xE301 << 16 | 3120, 0xE302 << 16 | 3305, 0xE303 << 16 | 2210, 0xE10F << 16 | 4489

TEAMS = [(1, 1, (-130.0, 36.0, 24.0), [DMR, 0]), (2, 0, (-121.0, 45.0, 25.0), [DMR, 0])]


def live_of(objects, units=TEAMS):
    live, players = reach(objects, units)
    live._tag_name_list = MY_NAMES
    live._placements = []
    live._ball_spots = dict(BALL_SPOTS)
    return live, players


class BombsByName(unittest.TestCase):
    def test_multi_bomb_both_found(self):
        """Multi Bomb: each team's bomb on its own stand, both found, each its stand's."""
        live, players = live_of([(BOMB, BOMB_AT[0]), (BOMB, BOMB_AT[1])])
        got = live.objective_items(players, BOMB_STANDS, "assault")
        self.assertEqual(sorted(it["stand"] for it in got), [0, 1])
        self.assertTrue(all(it["carrier"] is None for it in got))

    def test_a_gun_dropped_on_a_stand_is_no_bomb(self):
        """A magnum dropped dying on the neutral stand, seen before the bombs: not a bomb, then or later."""
        live, players = live_of([(MAGNUM, BOMB_AT[2]), (BOMB, BOMB_AT[0]), (BOMB, BOMB_AT[1])])
        for _ in range(3):
            got = live.objective_items(players, BOMB_STANDS, "assault")
            self.assertEqual(len(got), 2)
            self.assertNotIn(2, [it["stand"] for it in got])

    def test_carried_bomb_is_its_carriers(self):
        """A bot took team 0's bomb (its third slot): the carrier, so it runs it to their goal."""
        live, players = live_of([(BOMB, BOMB_AT[1])], units=[(1, 1, (-133.0, 33.0, 24.6), [DMR, 0, BOMB]), TEAMS[1]])
        got = live.objective_items(players, BOMB_STANDS, "assault")
        self.assertEqual(sorted(it["carrier"] for it in got if it["carrier"] is not None), [1])

    def test_the_old_way_took_the_gun(self):
        """Learned off a stand (no names), as before: the dropped magnum became "the bomb" and the bombs were missed."""
        live, players = live_of([(MAGNUM, BOMB_AT[2]), (BOMB, BOMB_AT[0]), (BOMB, BOMB_AT[1])])
        live.OBJECTIVE_NAMES = {}
        got = live.objective_items(players, BOMB_STANDS, "assault")
        self.assertEqual([it["stand"] for it in got], [2])


class BallByName(unittest.TestCase):
    def test_ball_lying_loose_is_found(self):
        """The ball dropped mid-map (its carrier died), first seen there: found, nobody carrying."""
        live, players = live_of([(SKULL, (-124.0, 40.0, 22.0))])
        got = live.balls(players)
        self.assertEqual(len(got), 1)
        self.assertAlmostEqual(got[0]["pos"][0], -124.0, places=3)
        self.assertIsNone(got[0]["carrier"])

    def test_carried_ball_is_its_carriers(self):
        live, players = live_of([], units=[(1, 1, (-130.0, 36.0, 24.0), [DMR, 0, SKULL]), TEAMS[1]])
        self.assertEqual([b["carrier"] for b in live.balls(players)], [1])

    def test_a_gun_on_a_ball_spawn_is_no_ball(self):
        live, players = live_of([(MAGNUM, (-128.6, 39.4, 21.9)), (SKULL, (-117.0, 32.5, 24.5))])
        got = live.balls(players)
        self.assertEqual([round(b["pos"][0], 1) for b in got], [-117.0])

    def test_no_ball_spawns_listed_still_found(self):
        """A layout whose export lists no ball spawn (a Forge variant without its .mvar read): found by name anyway."""
        live, players = live_of([(SKULL, (-124.0, 40.0, 22.0))])
        live._ball_spots = {}
        self.assertEqual(len(live.balls(players)), 1)

    def test_the_old_way_missed_a_loose_ball(self):
        """Learned only off its spawn marker before: a ball first seen loose was never the ball (Slayer was played)."""
        live, players = live_of([(SKULL, (-124.0, 40.0, 22.0))])
        live.OBJECTIVE_NAMES = {}
        self.assertEqual(live.balls(players), [])


if __name__ == "__main__":
    unittest.main()
