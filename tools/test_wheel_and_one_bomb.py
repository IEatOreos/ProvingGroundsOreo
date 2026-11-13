"""(custom, Nov 12) Two of the owner's reports.

A driver for a person on a driverless gun: his Blood Crash CTF (20261112-164125, 189-209 s) he sat on a Warthog's gun and
two bots were called into its one passenger seat, nobody to its wheel ("Why are they not driving me"). vehicles.wheel_open
and director.wheel_calls.

One Bomb's sides swap each round: his Breakpoint Assault (20261112-193700) round 2 the bomb's stand still read team 1's,
team 0 attacked, and its carriers stood 95 s at the map's mid with no goal. modes.Watch.bomb_attackers."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import modes, vehicles                                  # noqa: E402
from brain.bot import Bot, Order                                   # noqa: E402
from brain.core import PlayerState, Snapshot, Vec                  # noqa: E402
from brain.director import Director                                # noqa: E402
from brain.profiles import make_profile                            # noqa: E402

H = 3812819156
HOG = Vec(-17.1, 5.8, -0.4)


def hog(riders=1):
    return dict(handle=H, kind="storm_warthog", pos=(HOG.x, HOG.y, HOG.z), occupied=True, riders=riders, team=0,
                gunner=True, turrets=[], manned=["unknown"], dead=False, left=1.0)


def person(gun=True):
    p = PlayerState(0, 0, "owner", HOG, vehicle=H, is_bot=False)
    p.gunner_seat = gun
    return p


def bot(pid, tier, at):
    b = Bot(pid, 0, make_profile(tier, "flanker", random.Random(pid)), {"name": "h4_ca_blood_crash", "items": []},
            random.Random(pid))
    b.order = Order("runner", Vec(21, 1, -1.6))
    return b, PlayerState(pid, 0, f"bot{pid}", at, is_bot=True)


def director(bots):
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.roles = {}
    d.bots = {b.id: b for b in bots}
    d.event = lambda *a, **k: None
    return d


class WheelTests(unittest.TestCase):
    def setUp(self):
        self.heroic, self.hp = bot(1, "strong", HOG + Vec(6, 0, 0))
        self.demon, self.dp = bot(2, "demon", HOG + Vec(2, 0, 0))
        self.easy, self.ep = bot(3, "novice", HOG + Vec(1, 0, 0))

    def call(self, owner, v):
        snap = Snapshot(200.0, [owner, self.hp, self.dp, self.ep], mode="ctf", vehicles=[v])
        bots = [self.heroic, self.demon, self.easy]
        d = director(bots)
        d.wheel_calls(200.0, snap, bots, {b.id: snap.player(b.id) for b in bots})
        return d, snap

    def test_the_owner_on_the_gun_gets_a_driver(self):
        d, snap = self.call(person(gun=True), hog())
        self.assertTrue(vehicles.wheel_open(hog(), snap))
        self.assertEqual((self.heroic.order.role, self.heroic.order.target), ("drive", H))
        self.assertEqual(d.roles.get(1), "drive")

    def test_no_demon_at_a_warthog_wheel_and_no_easy(self):
        d, _ = self.call(person(gun=True), hog())
        self.assertNotEqual(self.demon.order.role, "drive")
        self.assertNotEqual(self.easy.order.role, "drive")

    def test_a_person_who_may_be_driving_is_left_alone(self):
        _, snap = self.call(person(gun=False), hog())                 # not on the gun: he may be at the wheel
        self.assertFalse(vehicles.wheel_open(hog(), snap))
        self.assertNotEqual(self.heroic.order.role, "drive")

    def test_a_bot_at_the_wheel_means_it_is_not_open(self):
        _, snap = self.call(person(gun=True), hog(riders=2))          # someone else aboard, not on a gun
        self.assertFalse(vehicles.wheel_open(hog(riders=2), snap))

    def test_too_far_is_not_called(self):
        self.hp.pos = HOG + Vec(40, 0, 0)
        self.call(person(gun=True), hog())
        self.assertNotEqual(self.heroic.order.role, "drive")


# Breakpoint's places (maps/reach_dlc_invasion/features.json): stands and goals by the map's teams
WEST_STAND, EAST_GOAL, WEST_GOAL = Vec(-44.313, -8.369, 0.917), Vec(19.526, -16.079, -5.3), Vec(-42.401, -8.835, 0.547)
LAY = {"bomb": [(Vec(-11.263, 0.198, -3.7), 1.0, 8), (WEST_STAND, 1.0, 1), (Vec(20.474, -14.516, -5.3), 1.0, 0)],
       "bomb_goal": [(EAST_GOAL, 2.0, 0), (WEST_GOAL, 2.0, 1)]}


class FakeLive:
    def __init__(self):
        self.bomb = dict(pos=(WEST_STAND.x, WEST_STAND.y, WEST_STAND.z), carrier=None, stand=1)

    def objective_items(self, raw, stands, mode):
        return [dict(self.bomb)]


def side(team, at, n=4, first=0):
    return [PlayerState(first + k, team, f"p{first + k}", at + Vec(k, 0, 0)) for k in range(n)]


class OneBombTests(unittest.TestCase):
    def setUp(self):
        self.w = modes.Watch("assault", {})
        self.w.lay = LAY
        self.live = FakeLive()

    def run_round(self, west_team, t0, secs=16):
        east_team = 1 - west_team
        snap = None
        for k in range(secs):
            players = side(west_team, Vec(-40, -8, 0.5), first=0) + side(east_team, Vec(15, -15, -5), first=4)
            snap = Snapshot(t0 + k, players, mode="assault")
            self.w.update(self.live, snap, t0 + k, raw=[{}])
        return snap

    def test_round_one_team_one_attacks_east(self):
        snap = self.run_round(west_team=1, t0=0.0)
        self.assertEqual(snap.obj_goals, {0: [EAST_GOAL]})
        self.assertEqual(snap.obj_items[0]["team"], 1)
        self.assertEqual(modes.carry_goal("assault", snap, 1, Vec()), EAST_GOAL)

    def test_round_two_the_sides_swap(self):
        self.run_round(west_team=1, t0=0.0)
        snap = self.run_round(west_team=0, t0=200.0)
        self.assertEqual(snap.obj_goals, {1: [EAST_GOAL]})
        self.assertEqual(snap.obj_items[0]["team"], 0)                 # ours to take from the stand
        self.assertEqual(modes.carry_goal("assault", snap, 0, Vec(-10.9, -12.7, -4.2)), EAST_GOAL)
        self.assertIsNone(modes.carry_goal("assault", snap, 1, Vec()))  # the defenders carry nothing

    def tick(self, t, players):
        snap = Snapshot(t, players, mode="assault")
        self.w.update(self.live, snap, t, raw=[{}])
        return snap

    def test_the_carrier_names_the_attackers_away_from_the_stand(self):
        self.run_round(west_team=1, t0=0.0)
        self.live.bomb = dict(pos=(-10.9, -12.7, -4.2), carrier=0, stand=1)    # p0 is team 0's in round two
        players = side(0, Vec(-12, -12, -4), first=0) + side(1, Vec(-38, -8, 0.5), first=4)   # defenders behind him
        snap = self.tick(16.0, players)
        self.assertEqual(snap.obj_goals, {1: [EAST_GOAL]})
        self.live.bomb = dict(pos=(-5.0, -15.0, -4.0), carrier=None, stand=1)  # he dies, it lies loose: still theirs
        snap = self.tick(17.0, players)
        self.assertEqual(snap.obj_goals, {1: [EAST_GOAL]})

    def test_armed_on_the_goal_is_the_defenders_to_disarm(self):
        self.run_round(west_team=0, t0=0.0)                            # team 0 attacks first this time
        self.live.bomb = dict(pos=(EAST_GOAL.x, EAST_GOAL.y, EAST_GOAL.z), carrier=None, stand=1)
        snap = self.tick(16.0, side(0, Vec(15, -15, -5)) + side(1, Vec(18, -12, -5), first=4))
        self.assertEqual(snap.obj_items[0]["armed"], 1)


class CarrierPickupTests(unittest.TestCase):
    """A person pulls up by our carrier bot: he gets in, Easy too (live Breakpoint 20261112-193700, 306-321 s)."""

    def scene(self, tier="novice", gun=False, d=3.0, riders=1):
        hog_v = dict(handle=H, kind="warthog", pos=(d, 0, 0), occupied=True, riders=riders, team=0, gunner=gun,
                     turrets=["warthog_chaingun"], manned=[], dead=False)
        me = PlayerState(0, 0, "owner", Vec(d, 0, 0), vehicle=H, is_bot=False)
        me.gunner_seat = gun
        b, cp = bot(8, tier, Vec())
        cp.has_flag = True
        snap = Snapshot(300.0, [me, cp], mode="assault", vehicles=[hog_v])
        dd = director([b])
        return dd, b, cp, snap

    def test_an_easy_carrier_gets_into_the_owners_warthog(self):
        dd, b, cp, snap = self.scene()
        self.assertTrue(dd.person_pickup(300.0, snap, cp, b))
        self.assertEqual((b.order.role, b.order.target), ("board", H))

    def test_not_from_far_off_nor_a_full_one_nor_with_him_on_the_gun(self):
        for kw in (dict(d=15.0), dict(riders=3), dict(gun=True)):
            dd, b, cp, snap = self.scene(**kw)
            self.assertFalse(dd.person_pickup(300.0, snap, cp, b), kw)
            self.assertNotEqual(b.order.role, "board", kw)


class VehicleBanTests(unittest.TestCase):
    def test_a_ban_ends_once_the_vehicle_has_moved(self):
        b, _ = bot(11, "top", Vec())
        v = dict(handle=7, kind="falcon", pos=(-36.1, -117.9, 5.3))
        b.veh_ban = {7: (606.0, Vec(-36.1, -117.9, 5.3))}
        self.assertTrue(b.veh_banned(v, 590.0))                       # still parked where it was given up on
        flown = dict(v, pos=(-59.6, -130.8, 2.6))
        self.assertFalse(b.veh_banned(flown, 590.0))                  # the owner flew it off and set it down
        self.assertFalse(b.veh_banned(v, 607.0))                      # and the ban runs out as before


if __name__ == "__main__":
    unittest.main()
