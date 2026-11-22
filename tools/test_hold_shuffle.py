"""(custom, Nov 22) Bot.hold_shuffle / peek_shuffle: a pre-nade's doorway hold and a peek waited out are side steps and
crouch walks on the spot, not a bot standing still. The owner: "holding a door wait they can strafe a little, and same
as 3 ... Anything other than standing completely still in the open". Recharging in cover is left as it was."""
import random
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain import bot  # noqa: E402
from brain.core import PlayerState, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


def mk(tier="demon", los=lambda a, b: False):
    b = bot.Bot.__new__(bot.Bot)
    b.p, b.game, b.notes, b.id = make_profile(tier, "camper", random.Random(1)), "reach", [], 1
    b.rng = random.Random(4)
    b.T = lambda: types.SimpleNamespace(los=los)
    return b


def act():
    return types.SimpleNamespace(forward=0.0, strafe=0.0, yaw=0.0, pitch=0.0, sprint=True, crouch=False, jump=False)


def me_at(x=0.0, y=0.0):
    return PlayerState(1, 0, "b", Vec(x, y, 0.0))


class ShuffleTests(unittest.TestCase):
    def test_never_stands_still(self):
        b, me = mk(), me_at()
        moved = 0
        for i in range(90):
            a = act()
            b.hold_shuffle(i / 30.0, me, a)
            self.assertFalse(a.sprint)
            moved += abs(a.strafe) > 0.3 or a.crouch
            me.pos = me.pos + Vec(0.0, a.strafe * 1.2 / 30.0, 0.0)      # (yaw 0: a strafe moves along y)
        self.assertEqual(moved, 90)
        self.assertLess(abs(me.pos.y), bot.SHUFFLE_LEASH + 0.3)          # (kept on its spot)

    def test_back_toward_the_spot_past_the_leash(self):
        b, me = mk(), me_at()
        b.hold_shuffle(0.0, me, act())
        me.pos = Vec(0.0, bot.SHUFFLE_LEASH + 0.2, 0.0)
        a = act()
        b.hold_shuffle(0.03, me, a)
        self.assertLess(a.strafe, 0.0)
        me.pos = Vec(bot.SHUFFLE_LEASH + 0.2, 0.0, 0.0)
        a = act()
        b.hold_shuffle(0.06, me, a)
        self.assertLess(a.forward, 0.0)

    def test_hidden_side_only(self):
        him = Vec(0.0, 20.0, 0.62)
        b, me = mk(los=lambda a, c: c.y > 0.3), me_at()                  # (he sees only what steps his way, +y)
        for i in range(40):
            a = act()
            b.hold_shuffle(i / 30.0, me, a, hidden_from=him)
            self.assertLessEqual(a.strafe, 0.0)
        b2 = mk(los=lambda a, c: True)                                   # (both sides seen: a crouch on the spot)
        a = act()
        b2.hold_shuffle(0.0, me_at(), a, hidden_from=him)
        self.assertEqual(a.strafe, 0.0)
        self.assertTrue(a.crouch)


class PeekTests(unittest.TestCase):
    def setUp(self):
        self.b, self.me = mk(), me_at()
        self.b.per = types.SimpleNamespace(beliefs={7: types.SimpleNamespace(pos=Vec(20, 0, 0))})
        self.b.peek_wait = (7, 0.0)

    def test_its_own_peek_spot(self):
        self.b.peek_spots = [(0.0, Vec(0.0, 0.0, 0.0))]
        a = act()
        self.b.peek_shuffle(0.5, self.me, a, "retreat", Vec(0.0, 0.0, 0.0))
        self.assertTrue(abs(a.strafe) > 0.3 or a.crouch)

    def test_not_a_recharge_cover(self):
        self.b.peek_spots = [(0.0, Vec(5.0, 5.0, 0.0))]
        a = act()
        self.b.peek_shuffle(0.5, self.me, a, "retreat", Vec(0.0, 0.0, 0.0))   # (a retreat goal of another kind)
        self.assertEqual((a.strafe, a.crouch), (0.0, False))
        self.b.peek_shuffle(0.5, self.me, a, "hunt", Vec(0.0, 0.0, 0.0))
        self.assertEqual(a.strafe, 0.0)

    def test_waited_long_enough(self):
        self.b.peek_spots = [(0.0, Vec(0.0, 0.0, 0.0))]
        a = act()
        self.b.peek_shuffle(bot.PEEK_WAIT_S + 0.1, self.me, a, "retreat", Vec(0.0, 0.0, 0.0))
        self.assertEqual(a.strafe, 0.0)


class PrenadeHoldTests(unittest.TestCase):
    def test_doorway_hold_moves(self):
        b, me = mk("demon"), me_at()
        b.prenade_ok = lambda: True
        b.per = types.SimpleNamespace(visible_enemies=lambda: [])
        b.aim = types.SimpleNamespace(step=lambda *a: (0.0, 0.0))
        b.prenade_st = (Vec(10.0, 0.0, 0.0), 5.0, "hold", 7)
        moved = 0
        for i in range(30):
            a = act()
            self.assertTrue(b.prenade(1.0 + i / 30.0, 1 / 30.0, me, None, a))
            moved += abs(a.strafe) > 0.3 or a.crouch
            self.assertFalse(a.sprint)
        self.assertEqual(moved, 30)


if __name__ == "__main__":
    unittest.main()
