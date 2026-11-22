"""(custom, Nov 22) Take Space (Bot.take_space), the owner's mechanic from Rainbow Six Siege: "when you clear and area,
or kill an enemy you try to take space meaning you are taking control of the map"; "is another anchor here? move to
next, or do a call where they can move together"; "Do it for demon and Noble first"."""
import random
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain import bot  # noqa: E402
from brain.core import FlagState, PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

SPOTS = [Vec(10, 0, 0), Vec(20, 0, 0), Vec(30, 0, 0), Vec(-10, 0, 0)]


def man(i, team, pos, shield=1.0):
    return PlayerState(i, team, f"p{i}", pos, shield=shield)


def mk(tier="demon", i=1):
    b = bot.Bot.__new__(bot.Bot)
    b.p, b.game, b.notes, b.id = make_profile(tier, "camper", random.Random(1)), "reach", [], i
    b.map = {"name": "test_space", "positions": list(SPOTS)}
    b.order = bot.Order("hunter", None)
    b.per = types.SimpleNamespace(beliefs={})
    b.goal = ("roam", None)
    b.rng = random.Random(2)
    b.T = lambda: types.SimpleNamespace(nav_z=lambda x, y, z: z, ground_ok=lambda *a, **k: True)
    return b


def snap(*players, mode="slayer", **kw):
    sn = Snapshot(0.0, list(players), mode=mode)
    for k, v in kw.items():
        setattr(sn, k, v)
    return sn


class Base(unittest.TestCase):
    def setUp(self):
        bot.TEAM_SPACE.clear()

    def tearDown(self):
        bot.TEAM_SPACE.clear()


class PickTests(Base):
    def test_toward_where_they_were(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        q, why = b.space_pick(0.0, me, snap(me), {}, [])
        self.assertEqual(q, Vec(10, 0, 0))                     # (the nearest forward one: not 20 u off at once)
        self.assertIn("where they were", why)

    def test_a_power_weapon_lying_out(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        sn = snap(me, ground_weapons=[("rockets", Vec(-12, 0, 0))])
        q, why = b.space_pick(0.0, me, sn, {}, [])
        self.assertEqual(q, Vec(-10, 0, 0))
        self.assertIn("rockets", why)
        sn = snap(me, ground_weapons=[("dmr", Vec(-12, 0, 0))])     # (no power weapon: where they were)
        self.assertEqual(b.space_pick(0.0, me, sn, {}, [])[0], Vec(10, 0, 0))

    def test_the_objective(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        sn = snap(me, mode="ctf", flags={1: FlagState(1, Vec(-30, 0, 0), Vec(-30, 0, 0))})
        self.assertEqual(b.space_pick(0.0, me, sn, {}, [])[0], Vec(-10, 0, 0))
        sn = snap(me, mode="king", hill=Vec(25, 0, 0))
        self.assertEqual(b.space_pick(0.0, me, sn, {}, [])[0], Vec(10, 0, 0))

    def test_another_on_it_next_one(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        claims = {2: (0.0, Vec(10, 0, 0))}
        self.assertEqual(b.space_pick(0.0, me, snap(me), claims, [])[0], Vec(20, 0, 0))
        mate = man(3, 0, Vec(20.5, 0, 0))                        # (and a teammate standing on the next: the anchor)
        me.pos = Vec(6, 0, 0)
        self.assertEqual(b.space_pick(0.0, me, snap(me, mate), claims, [])[0], Vec(30, 0, 0))

    def test_none_free_moves_up_with_him(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        claims = {2: (0.0, Vec(10, 0, 0)), 4: (0.0, Vec(20, 0, 0)), 5: (0.0, Vec(30, 0, 0))}
        q, why = b.space_pick(0.0, me, snap(me), claims, [])
        self.assertIn("moving up with him", why)
        self.assertAlmostEqual(bot.dist(q, Vec(10, 0, 0)), bot.SPACE_PAIR_R, places=3)
        claims[6] = (0.0, Vec(10.5, 0, 0))                       # (two on each: nowhere)
        claims[7] = (0.0, Vec(20.5, 0, 0))
        claims[8] = (0.0, Vec(30.5, 0, 0))
        self.assertIsNone(b.space_pick(0.0, me, snap(me), claims, []))

    def test_nothing_forward(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(1, 0, 0), t=0.0)
        self.assertIsNone(b.space_pick(0.0, me, snap(me), {}, []))


class TakeTests(Base):
    def go(self, b, me, sn, now, seen=()):
        scores = {}
        b.take_space(now, me, sn, scores, list(seen))
        return scores

    def test_a_kill_takes_space_then_pushes_on(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        sn = snap(me)
        self.assertEqual(self.go(b, me, sn, 1.0), {})            # (nothing happened yet)
        b.kill_seen = (1.5, Vec(5, 0, 0))
        sc = self.go(b, me, sn, 2.0)
        self.assertEqual(sc, {("hold", Vec(10, 0, 0)): bot.SPACE_SCORE})
        self.assertIn(1, bot.TEAM_SPACE[("test_space", 0)])
        me.pos = Vec(10, 0, 0)
        self.go(b, me, sn, 3.0)                                  # (there)
        b.kill_seen = (4.0, Vec(15, 0, 0))
        self.go(b, me, sn, 4.1)
        b.kill_seen = (5.0, Vec(15, 0, 0))
        sc = self.go(b, me, sn, 5.1)                             # (two kills there: the next spot)
        self.assertEqual(list(sc), [("hold", Vec(20, 0, 0))])

    def test_quiet_there_pushes_on(self):
        b, me = mk(), man(1, 0, Vec(10, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        b.space = dict(steps=0, until=50.0, spot=Vec(10, 0, 0), at=1.0, kills=0, held=[], why="")
        sc = self.go(b, me, snap(me), 1.0 + bot.SPACE_QUIET + 0.1)
        self.assertEqual(list(sc), [("hold", Vec(20, 0, 0))])

    def test_hurt_or_in_a_fight_scores_nothing(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0), shield=0.4)
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        b.kill_seen = (1.5, Vec(5, 0, 0))
        self.assertEqual(self.go(b, me, snap(me), 2.0), {})      # (a recharge first)
        me.shield = 1.0
        b.kill_seen = (2.5, Vec(5, 0, 0))
        self.assertEqual(self.go(b, me, snap(me), 3.0, seen=[9]), {})   # (a man in view: the fight)
        self.assertIsNotNone(b.space)

    def test_demon_and_noble_only(self):
        for tier in ("top", "mythic", "strong"):
            b, me = mk(tier), man(1, 0, Vec(0, 0, 0))
            b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
            b.kill_seen = (1.5, Vec(5, 0, 0))
            self.assertEqual(self.go(b, me, snap(me), 2.0), {}, tier)
        b, me = mk("noble"), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        b.kill_seen = (1.5, Vec(5, 0, 0))
        self.assertEqual(len(self.go(b, me, snap(me), 2.0)), 1)

    def test_the_anchor_keeps_its_post(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        b.order = bot.Order("mid", Vec(-10, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(40, 0, 0), t=0.0)
        b.kill_seen = (1.5, Vec(5, 0, 0))
        self.assertEqual(self.go(b, me, snap(me), 2.0), {})

    def test_ends_after_its_steps(self):
        b, me = mk(), man(1, 0, Vec(0, 0, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(400, 0, 0), t=0.0)
        b.space = dict(steps=bot.SPACE_STEPS - 1, until=50.0, spot=Vec(10, 0, 0), at=1.0, kills=bot.SPACE_KILLS,
                       held=[], why="")
        self.assertEqual(self.go(b, me, snap(me), 2.0), {})
        self.assertIsNone(b.space)


class ShuffleOnSpot(Base):
    def test_shuffles_there(self):
        b, me = mk(), man(1, 0, Vec(10, 0, 0))
        b.space = dict(steps=0, until=50.0, spot=Vec(10, 0, 0), at=1.0, kills=0, held=[], why="")
        a = types.SimpleNamespace(forward=0.0, strafe=0.0, yaw=0.0, sprint=False, crouch=False)
        b.space_shuffle(2.0, me, a, "hold", Vec(10, 0, 0))
        self.assertTrue(abs(a.strafe) > 0.3 or a.crouch)
        a2 = types.SimpleNamespace(forward=0.0, strafe=0.0, yaw=0.0, sprint=False, crouch=False)
        b.space_shuffle(2.0, me, a2, "hold", Vec(-10, 0, 0))     # (another hold: as it was)
        self.assertEqual(a2.strafe, 0.0)


if __name__ == "__main__":
    unittest.main()
