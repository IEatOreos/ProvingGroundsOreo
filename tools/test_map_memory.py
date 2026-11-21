"""(custom, Nov 19) Map memory, Legendary and up (brain/lore.py, profiles.map_memory). The owner: "Danger map, Spawns,
Movement facts ... only give it to legendary and up". What a layout taught over matches: the spots men shot from when
people died where a bot walks (looked at first), the lanes the most people died in (gone round when about as short),
where people respawn (watched after a kill), and the jumps bots keep falling short of (another way when there is one)."""
import math
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot as botmod                                # noqa: E402
from brain import lore                                          # noqa: E402
from brain import profiles                                      # noqa: E402
from brain.bot import Belief, Bot                              # noqa: E402
from brain.core import PlayerState, Snapshot, Vec              # noqa: E402
from brain.profiles import make_profile                        # noqa: E402
from test_h4_pickup_board import Flat                          # noqa: E402

NAME = "reach_test_lore"


class Sight(Flat):
    """Lines blocked to the points listed (by x, y rounded); a walking way everywhere unless told."""
    def __init__(s, blocked=(), walk=True):
        s.blocked, s.walk = {(round(p[0]), round(p[1])) for p in blocked}, walk

    def los(s, a, b, *k, **kw):
        return (round(b.x), round(b.y)) not in s.blocked and (round(a.x), round(a.y)) not in s.blocked

    def reaches(s, a, b, jump=False, human=False):
        return s.walk


def book(kill_matches=3):
    b = lore.Lore(None)
    for k in range(kill_matches):
        b.match(f"m{k}")
        b.kill_match(f"m{k}")
    lore._BOOKS[NAME] = b
    return b


def make(tier="demon", T=None, pos=Vec()):
    m = {"name": NAME, "items": []}
    b = Bot(0, 0, make_profile(tier, "objector", random.Random(1)), m, random.Random(2))
    b.notes = []
    t = T or Sight()
    b.T = lambda: t
    me = PlayerState(0, 0, "bot", pos)
    return b, me


class LoreTests(unittest.TestCase):
    def test_shooting_spots_where_people_died_here_only_once_trusted(self):
        b = book(kill_matches=2)
        for k in range(4):
            b.add_kill((1.0 + 0.1 * k, 0.0, 0.0), (20.0, 5.0, 2.0))     # died here, shot from (20, 5)
        b.add_kill((1.0, 0.0, 0.0), (-30.0, 0.0, 0.0))                  # once from elsewhere: not a spot
        b.add_kill((40.0, 0.0, 0.0), (60.0, 0.0, 0.0))                  # died far off: not here
        self.assertEqual(b.shooters(Vec()), [], "two matches with kills: not trusted yet")
        b.kill_match("m2")
        spots = b.shooters(Vec())
        self.assertEqual(len(spots), 1)
        self.assertLess((spots[0][0] - Vec(20.0, 5.0, 2.0)).length(), 0.01)
        self.assertEqual(spots[0][1], 4)

    def test_lanes_the_cells_most_people_died_in(self):
        b = book()
        for k in range(10):
            b.add_kill((5.0, 5.0, 0.0), (0.0, 0.0, 0.0))
        for k in range(3):
            b.add_kill((50.0, 5.0, 0.0), (0.0, 0.0, 0.0))
        ln = b.lanes()
        self.assertEqual(len(ln), 1)
        self.assertEqual(ln[0][:2], (5.0, 5.0))
        self.assertEqual(ln[0][3], lore.LANE_R)

    def test_spawn_spots_by_mode_and_not_ones_own_team(self):
        b = book()
        for k in range(3):
            b.add_spawn("slayer", (10.0, 0.0, 0.0), 0)
            b.add_spawn("slayer", (-10.0, 0.0, 0.0), 1)
            b.add_spawn("ctf", (0.0, 30.0, 0.0), 1)
        self.assertEqual(len(b.spawn_spots("slayer")), 2)
        self.assertEqual([round(p.x) for p, n in b.spawn_spots("slayer", 0)], [-10])
        self.assertEqual([round(p.y) for p, n in b.spawn_spots("ctf")], [30])
        self.assertEqual(len(b.spawn_spots("oddball")), 3, "a mode with none: every mode's")

    def test_jumps_left_only_when_mostly_short(self):
        b = book()
        for made in (False, False, False, True):
            b.add_jump((3.04, 4.0), made)
        self.assertTrue(b.jump_bad((3.0, 4.0)))
        b.add_jump((3.0, 4.0), True)
        self.assertFalse(b.jump_bad((3.0, 4.0)), "made twice to three shorts: kept")

    def test_saved_and_read_back(self):
        with tempfile.TemporaryDirectory() as d:
            b = lore.Lore(d)
            b.match("x")
            b.kill_match("x")
            b.add_kill((1, 2, 3), (4, 5, 6))
            b.add_spawn("slayer", (7, 8, 9), 1)
            b.add_jump((1.0, 2.0), False)
            b.save()
            c = lore.Lore(d)
            self.assertEqual((c.matches, c.kill_matches, c.kills), (["x"], ["x"], [[1, 2, 3, 4, 5, 6]]))
            self.assertEqual(c.spawns, {"slayer": [[7.0, 8.0, 9.0, 1]]})
            self.assertEqual(c.jumps, {"1.0,2.0": [0, 1]})
            self.assertFalse(c.match("x"), "a match is filed once")


class TierTests(unittest.TestCase):
    def test_legendary_and_up_only(self):
        rng = random.Random(1)
        for tier, has in (("demon", True), ("top", True), ("mythic", True), ("strong", False), ("average", False)):
            self.assertEqual(profiles.map_memory(make_profile(tier, "objector", rng)), has, tier)
        scaled = make_profile("top", "objector", rng)
        scaled.extra = {"aim_err": 1.0}
        self.assertFalse(profiles.map_memory(scaled), "Scaling's top tier")

    def test_heroic_reads_none(self):
        book()
        b, me = make("strong")
        self.assertIsNone(b.lore())
        self.assertEqual(b.danger_lanes(me), ())

    def test_switch_off(self):
        book()
        b, me = make("demon")
        old, botmod.MAP_MEMORY = botmod.MAP_MEMORY, False
        try:
            self.assertIsNone(b.lore())
        finally:
            botmod.MAP_MEMORY = old


class DangerLookTests(unittest.TestCase):
    def setUp(self):
        self.b = book()
        for k in range(4):
            self.b.add_kill((0.0, 0.0, 0.0), (20.0, 0.0, 0.0))     # ahead (+x)
            self.b.add_kill((0.0, 0.0, 0.0), (0.0, -20.0, 0.0))    # to the right, 90 degrees off
        for k in range(3):
            self.b.add_kill((0.0, 0.0, 0.0), (-20.0, 0.0, 0.0))    # behind

    def test_walking_the_spot_ahead_then_left_a_while(self):
        b, me = make()
        q = b.danger_look(10.0, me, Vec(5.0, 0.0, 0.0))
        self.assertIsNotNone(q)
        self.assertEqual((round(q.x), round(q.y)), (20, 0))
        self.assertEqual(b.danger_look(10.5, me, Vec(5.0, 0.0, 0.0)), q, "held DANGER_LOOK_S")
        self.assertIsNone(b.danger_look(11.0, me, Vec(5.0, 0.0, 0.0)), "the others are out of the walk's cone")
        self.assertIsNotNone(b.danger_look(10.0 + botmod.DANGER_RECHECK + 1, me, Vec(5.0, 0.0, 0.0)), "again later")

    def test_standing_every_spot_by_kills(self):
        b, me = make()
        first = b.danger_look(10.0, me)
        self.assertIn((round(first.x), round(first.y)), ((20, 0), (0, -20)))
        second = b.danger_look(11.0, me)
        self.assertNotEqual((round(first.x), round(first.y)), (round(second.x), round(second.y)))

    def test_a_spot_out_of_sight_is_not_looked_at(self):
        b, me = make(T=Sight(blocked=[(20, 0)]))
        self.assertIsNone(b.danger_look(10.0, me, Vec(5.0, 0.0, 0.0)))

    def test_look_point_uses_it_when_nobody_is_known(self):
        b, me = make()
        me.vel = Vec(2.0, 0.0, 0.0)
        b.wp = Vec(5.0, 0.0, 0.0)
        b.now = 10.0
        b.arrival = lambda *a: None
        b.tele_watching = lambda *a: None
        q = b.look_point(me, Vec(30.0, 0.0, 0.0))
        self.assertEqual(b.att[:2], ["watch", "danger"])
        self.assertEqual((round(q.x), round(q.y)), (20, 0))


class SpawnLookTests(unittest.TestCase):
    def setUp(self):
        self.b = book()
        for k in range(5):
            self.b.add_spawn("slayer", (25.0, 0.0, 0.0), 1)
            self.b.add_spawn("slayer", (-25.0, 0.0, 0.0), 0)       # its own team's

    def kill(self, b, me):
        foe = PlayerState(4, 1, "foe", Vec(8.0, 0.0, 0.0))
        b.goal = ("fight", 4)
        b.game_team = 0
        b.kill_check(9.9, Snapshot(9.9, [me, foe], mode="slayer"))
        foe.alive = False
        b.kill_check(10.0, Snapshot(10.0, [me, foe], mode="slayer"))

    def test_after_a_kill_the_enemy_spawn_in_sight(self):
        b, me = make()
        self.assertIsNone(b.spawn_look(10.0, me), "no kill: no spawn watch")
        self.kill(b, me)
        q = b.spawn_look(10.1, me)
        self.assertEqual((round(q.x), round(q.y)), (25, 0))
        self.assertIsNone(b.spawn_look(10.0 + botmod.SPAWN_WATCH_S + 0.5, me), "over after SPAWN_WATCH_S")

    def test_not_out_of_the_walks_cone(self):
        b, me = make()
        self.kill(b, me)
        self.assertIsNone(b.spawn_look(10.1, me, Vec(0.0, 5.0, 0.0)))

    def test_spawns_flipped_this_match_lead_the_history(self):
        # (owner: "some maps and modes spawns flip if they take it over") the enemy came back at -25 lately, where
        # the history has our own side; we came back at +25, the history's enemy spot
        b, me = make()
        for t in (40.0, 55.0):
            self.b.add_spawn("slayer", (0.0, -25.0, 0.0), 1, now=t)
            self.b.add_spawn("slayer", (25.0, 0.5, 0.0), 0, now=t)
        spots = self.b.spawn_spots("slayer", 0, now=60.0)
        self.assertEqual([(round(v.x), round(v.y)) for v, n in spots], [(0, -25)], "theirs lately; ours left")
        old = self.b.spawn_spots("slayer", 0, now=60.0 + lore.RECENT_S + 20.0)
        self.assertEqual([(round(v.x), round(v.y)) for v, n in old], [(25, 0)], "past RECENT_S: the history again")
        self.assertEqual([(round(v.x), round(v.y)) for v, n in self.b.spawn_spots("slayer", 0)], [(25, 0)])
        self.b.match("next")                                       # a new match: nothing recent
        self.assertEqual(self.b.recent, [])

    def test_a_spot_a_teammate_stands_on_is_not_watched(self):
        b, me = make()
        mate = PlayerState(2, 0, "mate", Vec(23.0, 2.0, 0.0))
        foe = PlayerState(4, 1, "foe", Vec(8.0, 0.0, 0.0))
        b.goal, b.game_team = ("fight", 4), 0
        b.kill_check(9.9, Snapshot(9.9, [me, mate, foe], mode="slayer"))
        foe.alive = False
        b.kill_check(10.0, Snapshot(10.0, [me, mate, foe], mode="slayer"))
        self.assertIsNone(b.spawn_look(10.1, me))


class RadarSpotTests(unittest.TestCase):
    def test_a_dot_by_a_known_shooting_spot_that_spot_is_watched(self):
        b0 = book()
        for k in range(4):
            b0.add_kill((0.0, 0.0, 0.0), (14.0, 4.0, 0.0))
        b, me = make(T=Sight(blocked=[(14, 2)]))                     # the dot itself out of sight
        b.guess = lambda now, me_, k, bb: bb.pos
        b.dot_corner = lambda *a: (Vec(10.0, 0.0, 0.0), 12.0, None)
        known = [(4, Belief(Vec(14.0, 2.0, 0.0), Vec(), 9.9, False, "radar"))]
        att, look = b.radar_threat(10.0, me, known)
        self.assertEqual(att[1], "#4 spot")
        self.assertEqual((round(look.x), round(look.y)), (14, 4))


class JumpTests(unittest.TestCase):
    class J:
        sx, sy, x, y, z = 3.0, 4.0, 6.0, 4.0, 2.0

    def test_a_jump_bots_keep_missing_another_way_when_there_is_one(self):
        b0 = book()
        for _ in range(3):
            b0.add_jump((3.0, 4.0), False)
        b, me = make()
        self.assertTrue(b.jump_learned_bad(me, self.J(), Vec(10, 0, 0)))
        self.assertTrue(b.jump_blocked(self.J()), "banned as two shorts of its own")
        b2, me2 = make(T=Sight(walk=False))
        self.assertFalse(b2.jump_learned_bad(me2, self.J(), Vec(10, 0, 0)), "no walking way: still tried")
        b3, me3 = make("strong")
        self.assertFalse(b3.jump_learned_bad(me3, self.J(), Vec(10, 0, 0)), "Heroic: as before")

    def test_outcomes_are_filed(self):
        b0 = book()
        b, me = make()
        b.now = 5.0
        b.jump_try = ((3.0, 4.0), Vec(6.0, 4.0, 2.0), 3.0)
        me.pos = Vec(6.2, 4.0, 2.0)
        b.judge_jump(me)
        b.jump_try = ((3.0, 4.0), Vec(6.0, 4.0, 2.0), 3.0)
        me.pos = Vec(4.0, 4.0, -3.0)
        b.judge_jump(me)
        self.assertEqual(b0.jumps, {"3.0,4.0": [1, 1]})


@unittest.skipUnless((Path(__file__).resolve().parents[1] / "maps" / "reach_70_boneyard" / "heightmap.npz").exists(),
                     "SKIP: no Boneyard heightmap (map pack not installed)")
class AvoidNavTests(unittest.TestCase):
    """Terrain.nav avoid on a real layout: round a disk when about as short, the plain way when not."""
    @classmethod
    def setUpClass(cls):
        from brain.maps import get_map, terrain
        cls.T = terrain(get_map("reach_70_boneyard"))

    def walk(self, a, b, **kw):
        pts, p = [a], a
        for _ in range(400):
            q = self.T.nav(p, b, **kw)
            if q is None or (q - p).length() < 1e-3:
                break
            p = Vec(q.x, q.y, q.z)
            pts.append(p)
            if (p - b).flat() < 0.5:
                break
        return pts

    @staticmethod
    def length(pts):
        return sum((q - p).flat() for p, q in zip(pts, pts[1:]))

    @staticmethod
    def near(pts, c, r):
        for p, q in zip(pts, pts[1:]):
            for k in range(11):
                x, y = p.x + (q.x - p.x) * k / 10, p.y + (q.y - p.y) * k / 10
                if math.hypot(x - c[0], y - c[1]) < r and abs(p.z - c[2]) < 1.5:
                    return True
        return False

    def test_round_a_lane_when_about_as_short(self):
        a, b = Vec(268.4, 136.6, -10.2), Vec(295.7, 88.3, -5.0)
        b = self.T._center(*self.T._node(b))
        a = self.T._center(*self.T._node(a))
        plain = self.walk(a, b)
        self.assertLess((plain[-1] - b).flat(), 1.0, "the plain way gets there")
        tried = 0
        for p in plain[2:-2]:
            disk = ((round(p.x, 1), round(p.y, 1), round(p.z, 1), 2.0),)
            way = self.walk(a, b, avoid=disk)
            if self.length(way) - self.length(plain) < 0.5:
                continue
            tried += 1
            self.assertLess((way[-1] - b).flat(), 1.0)
            self.assertFalse(self.near(way[1:], disk[0], 1.0), "goes round it")
            self.assertLessEqual(self.length(way), self.length(plain) * self.T.AVOID_LONGER + self.T.AVOID_EXTRA + 4.0)
            break
        self.assertTrue(tried, "some lane on the way had a way round")

    def test_a_goal_in_the_lane_the_plain_way(self):
        a, b = Vec(268.4, 136.6, -10.2), Vec(295.7, 88.3, -5.0)
        b = self.T._center(*self.T._node(b))
        disk = ((round(b.x, 1), round(b.y, 1), round(b.z, 1), 3.0),)
        self.assertEqual(self.T.nav(a, b, avoid=disk), self.T.nav(a, b))


if __name__ == "__main__":
    unittest.main()
