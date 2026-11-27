"""(custom, Nov 27) Mongooses only for the objective, and the bail drives away first (brain/goose_rules.py). The owner:
"Like only use them when escorting a bomb carrier, or flag carrier? Cause even now in 8v8 they just drive to the open,
get hit dismount and die anyways"; "Dont have bots use mongoose in slayer or koth"."""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import goose_rules as G  # noqa: E402
from brain.bot import Belief, Bot, Order  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.director import Director  # noqa: E402

GOOSE = dict(handle=50, kind="mongoose", pos=(0.0, 0.0, 0.0), occupied=False)
GOOSE2 = dict(handle=51, kind="mongoose", pos=(30.0, 0.0, 0.0), occupied=True, team=0)
HOG = dict(handle=60, kind="warthog", pos=(5.0, 0.0, 0.0), occupied=False)


def snap_of(mode, players, vehicles=(GOOSE,)):
    return Snapshot(10.0, list(players), mode=mode, vehicles=[dict(v) for v in vehicles])


class SelfPickTests(unittest.TestCase):
    def test_no_mongoose_in_slayer_or_king(self):
        me = PlayerState(1, 0, "b", Vec())
        for mode in ("slayer", "king", "oddball", "infection", "firefight", "invasion"):
            self.assertFalse(G.self_ok(snap_of(mode, [me]), me, "runner", GOOSE), mode)

    def test_runner_in_a_carrier_game_one_at_a_time(self):
        me = PlayerState(1, 0, "b", Vec())
        for mode in ("ctf", "assault", "stockpile"):
            self.assertTrue(G.self_ok(snap_of(mode, [me]), me, "runner", GOOSE), mode)
            self.assertFalse(G.self_ok(snap_of(mode, [me]), me, "free", GOOSE), mode)
        mate = PlayerState(2, 0, "c", Vec(30, 0, 0), vehicle=51)
        s = snap_of("ctf", [me, mate], (GOOSE, GOOSE2))
        self.assertFalse(G.self_ok(s, me, "runner", GOOSE))               # (one out already: SLOTS)
        mate.has_flag = True                                              # (... but it runs our carrier: no slot taken)
        self.assertTrue(G.self_ok(s, me, "runner", GOOSE))

    def test_race_and_the_objective_in_hand(self):
        me = PlayerState(1, 0, "b", Vec())
        self.assertTrue(G.self_ok(snap_of("race", [me]), me, "free", GOOSE))
        me.has_flag = True
        self.assertTrue(G.self_ok(snap_of("slayer", [me]), me, "free", GOOSE))

    def test_back_seat_calls(self):
        s = snap_of("ctf", [])
        self.assertTrue(G.rider_ok(s, "runner", 50))
        self.assertFalse(G.rider_ok(s, "mid", 50))
        self.assertFalse(G.rider_ok(snap_of("slayer", []), "runner", 50))

    def test_veh_banned_keeps_the_directors_orders(self):
        b = types.SimpleNamespace(goose_use=(10.0, False), order=Order("free"), goose_radar=None)
        self.assertTrue(Bot.veh_banned(b, GOOSE, 10.0))
        self.assertFalse(Bot.veh_banned(b, HOG, 10.0))                    # (other vehicles as before)
        b.order = Order("drive", Vec(), target=50)
        self.assertFalse(Bot.veh_banned(b, GOOSE, 10.0))                  # (the director's pick, checked when given)
        b.order, b.goose_use = Order("free"), (10.0, True)
        self.assertFalse(Bot.veh_banned(b, GOOSE, 10.0))


class GoalTests(unittest.TestCase):
    def director(self, mode, players, park=Vec(80, 0, 0)):
        d = types.SimpleNamespace(team=0, bots={}, carry_point=lambda snap: Vec(0, 0, 0),
                                  getaway_park=lambda snap, start: park)
        return d, snap_of(mode, players)

    def test_slayer_and_king_none(self):
        me = PlayerState(1, 0, "b", Vec(50, 0, 0))
        for mode in ("slayer", "king"):
            d, s = self.director(mode, [me])
            self.assertIsNone(Director.goose_goal(d, s, types.SimpleNamespace(id=1, order=Order("free")), me), mode)

    def test_fetch_our_carrier_then_the_getaway(self):
        me = PlayerState(1, 0, "b", Vec(10, 0, 0))
        carrier = PlayerState(2, 0, "c", Vec(60, 0, 0), has_flag=True)
        d, s = self.director("ctf", [me, carrier])
        fetch = set()
        b = types.SimpleNamespace(id=1, order=Order("free"))
        self.assertEqual(Director.goose_goal(d, s, b, me, fetch), carrier.pos)
        self.assertEqual(fetch, {1})
        carrier.pos = Vec(10, 0, 0)                                       # (by home: no fetch, the getaway spot)
        self.assertEqual(Director.goose_goal(d, s, b, me), Vec(80, 0, 0))
        d.bots = {9: types.SimpleNamespace(order=Order("free"), vjob="getaway")}
        self.assertIsNone(Director.goose_goal(d, s, b, me))               # (one getaway ride a team)


class Per:
    def __init__(s):
        s.beliefs, s.seen = {}, []

    def visible_enemies(s):
        return list(s.seen)


def rider(seat="driver"):
    b = types.SimpleNamespace(per=Per(), seat=seat, notes=[])
    b.note = b.notes.append
    return b


class FleeTests(unittest.TestCase):
    def setUp(s):
        s.me = PlayerState(1, 0, "b", Vec(), vehicle=50, vel=Vec(10, 0, 0))
        s.foe = PlayerState(2, 1, "e", Vec(-15, 0, 0))
        s.snap = snap_of("ctf", [s.me, s.foe])

    def seen(s, b, now, pos=None):
        b.per.beliefs[2] = Belief(pos or s.foe.pos, Vec(), now, True, "eyes")
        b.per.seen = [2]

    def test_driver_drives_away_then_off_out_of_sight(s):
        b = rider()
        s.seen(b, 10.0)
        s.assertTrue(Bot.goose_flee(b, 10.0, s.me, s.snap, "shot"))
        s.assertGreater(b.retreat_to.x, 15.0)                             # (straight away from him: he is at -15)
        b.per.seen = []                                                   # (behind cover)
        s.assertTrue(Bot.goose_flee(b, 10.8, s.me, s.snap, "shot"))
        s.assertFalse(Bot.goose_flee(b, 11.6, s.me, s.snap, "shot"))
        s.assertEqual(b.goose_flight["off"], "out of sight")

    def test_off_at_once_with_him_close(s):
        b = rider()
        s.seen(b, 10.0, Vec(-3, 0, 0))
        s.assertFalse(Bot.goose_flee(b, 10.0, s.me, s.snap, "an enemy on radar"))

    def test_runs_no_longer_than_flee_max(s):
        b = rider()
        t = 10.0
        while t < 10.0 + G.FLEE_MAX - 0.05:
            s.seen(b, t)
            s.assertTrue(Bot.goose_flee(b, t, s.me, s.snap, "shot"))
            t += 0.1
        s.seen(b, 10.0 + G.FLEE_MAX)
        s.assertFalse(Bot.goose_flee(b, 10.0 + G.FLEE_MAX, s.me, s.snap, "shot"))

    def test_stalled_driver_gets_off(s):
        b = rider()
        s.seen(b, 10.0)
        s.assertTrue(Bot.goose_flee(b, 10.0, s.me, s.snap, "shot"))
        s.seen(b, 10.6)
        s.assertTrue(Bot.goose_flee(b, 10.6, s.me, s.snap, "shot"))
        s.me.vel = Vec(1, 0, 0)
        s.seen(b, 11.2)
        s.assertFalse(Bot.goose_flee(b, 11.2, s.me, s.snap, "shot"))

    def test_passenger_rides_it_out_off_as_it_slows(s):
        b = rider("passenger")
        s.seen(b, 10.0)
        s.assertTrue(Bot.goose_flee(b, 10.0, s.me, s.snap, "shot"))
        s.assertFalse(hasattr(b, "retreat_to"))                           # (a passenger steers nothing)
        s.me.vel = Vec(0.5, 0, 0)
        s.seen(b, 10.5)
        s.assertFalse(Bot.goose_flee(b, 10.5, s.me, s.snap, "shot"))

    def test_a_new_ride_starts_a_new_flight(s):
        b = rider()
        s.seen(b, 10.0)
        Bot.goose_flee(b, 10.0, s.me, s.snap, "shot")
        s.seen(b, 50.0)
        s.assertTrue(Bot.goose_flee(b, 50.0, s.me, s.snap, "shot"))       # (same Mongoose 40 s on: its own clock)


if __name__ == "__main__":
    unittest.main()
