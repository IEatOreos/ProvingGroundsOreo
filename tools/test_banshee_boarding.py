"""(custom, Nov 25) A Banshee a teammate just flew is no dud; the pilot boards it from its open side; the director sends a
bot to an empty Banshee while our Falcon flies, but never one out of an aircraft.

Live Spire 20261125-193322: the owner set the Banshee down by a low wall (he was in it to 128.9 s); bot 8 walked to its
walled side, pressed Use 21 times from behind the wall, and at 145.7 s Bot.dud_check banned it for everyone for 120 s.
From 52 to 132 s our crewed Falcon filled "anti_air" and no bot of ours was sent to the empty Banshee."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot, Order, wrap  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.director import Director  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

C = (-179.79, -389.17, -60.05)          # the Banshee, live
FAILED = Vec(-177.36, -390.49, -60.23)  # bot 8 at 143.1 s, the wall between
SEAT = Vec(-177.64, -390.32, -60.05)    # where its walk ended (behind the wall)


class WallT:
    """A low wall along the Banshee's south-east side: blocked toward the middle from 230-340 degrees."""
    def clearance(s, p, yaw, far=3.0, **kw):
        a0, a1 = math.radians(230), math.radians(340)
        x1, y1 = C[0] + math.cos(a0), C[1] + math.sin(a0)
        x2, y2 = C[0] + math.cos(a1), C[1] + math.sin(a1)
        dx, dy = math.cos(yaw), math.sin(yaw)
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            return far
        t = ((x1 - p.x) * ey - (y1 - p.y) * ex) / den
        u = ((x1 - p.x) * dy - (y1 - p.y) * dx) / den
        return t if 0 <= t <= far and 0 <= u <= 1 else far


def pilot(kind="banshee"):
    b = Bot(8, 0, make_profile("demon", "spammer", random.Random(8)), dict(name="reach_35_island", flags={}, points={}))
    b.game, b.notes, b._terrain = "reach", [], WallT()
    v = dict(handle=3809214621, kind=kind, pos=C, occupied=False, team=-1, riders=0, fwd=(1.0, 0.0, 0.0), up=(0, 0, 0.98))
    return b, v


def crewed(b, v, t, **kw):
    me = PlayerState(8, 0, "Death", FAILED)
    b.air_crewed_note(t, Snapshot(t, [me], vehicles=[dict(v, occupied=True, team=0, riders=1, **kw)]))


def stand_by(b, v, me, t0, secs, dt=1 / 30):
    for k in range(int(secs / dt)):
        if not b.dud_check(t0 + k * dt, dt, me, v):
            return t0 + k * dt
    return None


class DudTests(unittest.TestCase):
    def test_a_banshee_just_flown_is_never_banned(self):
        b, v = pilot()
        me = PlayerState(8, 0, "Death", FAILED)
        crewed(b, v, 128.8)
        self.assertIsNone(stand_by(b, v, me, 135.6, 30.0))
        self.assertFalse(b.duds())
        self.assertTrue(any(n.startswith("air: the banshee was flown lately") for n in b.notes))
        away = b.air_board_away
        b.notes = []
        p = b.air_board_point(146.0, me, v, SEAT, "driver")
        a = math.atan2(p.y - C[1], p.x - C[0])
        self.assertGreaterEqual(abs(wrap(a - away[1])), math.radians(60))       # (another side)
        r = math.hypot(p.x - C[0], p.y - C[1])
        self.assertGreaterEqual(WallT().clearance(Vec(p.x, p.y, C[2]), math.atan2(C[1] - p.y, C[0] - p.x), r), r - 0.1)

    def test_the_dud_rule_stands_otherwise(self):
        for kind, t, pos in (("banshee", 60.0, C), ("warthog", 128.8, C), ("banshee", 128.8, (C[0] + 6, C[1], C[2]))):
            b, v = pilot(kind)
            crewed(b, v, t, pos=pos)
            out = stand_by(b, v, PlayerState(8, 0, "Death", FAILED), 135.6, 30.0)
            self.assertIsNotNone(out, (kind, t, pos))
            self.assertIn(v["handle"], b.duds(), (kind, t, pos))


class BoardPointTests(unittest.TestCase):
    def test_a_walled_seat_point_is_swapped(self):
        b, v = pilot()
        me = PlayerState(8, 0, "Death", Vec(-175.8, -388.52, -59.48))
        p = b.air_board_point(140.1, me, v, SEAT, "driver")
        self.assertNotEqual((p.x, p.y), (SEAT.x, SEAT.y))
        open_vp = Vec(C[0] + 1.3, C[1] + 0.3, C[2])
        self.assertIs(b.air_board_point(140.1, me, v, open_vp, "driver"), open_vp)
        self.assertIs(b.air_board_point(140.1, me, v, SEAT, "gunner"), SEAT)


def director(bot):
    d = Director.__new__(Director)
    d.team = d.side = 0
    bot.set_order = lambda order, **kw: setattr(bot, "order", order)
    bot.order = Order("hunter", Vec(-160, -370, -56))
    d.map, d.bots, d.roles = bot.map, {8: bot}, {8: "hunter"}
    d.event = lambda *a: None
    d.enemy_vehicles = lambda *a: []
    return d


class DirectorTests(unittest.TestCase):
    FALCON = dict(handle=77, kind="falcon", pos=(-150, -350, -40), occupied=True, team=0, riders=1)
    BANSHEE = dict(handle=3809214621, kind="banshee", pos=C, occupied=False, team=-1, riders=0, up=(0, 0, 0.98))

    def test_a_bot_on_foot_is_sent_while_our_falcon_flies(self):
        bot, _ = pilot()
        d = director(bot)
        me = PlayerState(8, 0, "Death", Vec(-170, -380, -58))
        d.crew_orders(60.0, Snapshot(60.0, [me], vehicles=[self.FALCON, self.BANSHEE]), {8: me}, [bot])
        self.assertEqual((bot.order.role, bot.order.target), ("drive", self.BANSHEE["handle"]))

    def test_never_one_out_of_an_aircraft(self):
        """(review) a Demon on our flying Falcon's gun was ordered out to the Banshee, mid-air."""
        bot, _ = pilot()
        d = director(bot)
        me = PlayerState(8, 0, "Death", Vec(-160, -365, -45), vehicle=77)
        bot.seat = "gunner"
        d.crew_orders(60.0, Snapshot(60.0, [me], vehicles=[self.FALCON, self.BANSHEE]), {8: me}, [bot])
        self.assertNotEqual((bot.order.role, getattr(bot.order, "target", None)), ("drive", self.BANSHEE["handle"]))


if __name__ == "__main__":
    unittest.main()
