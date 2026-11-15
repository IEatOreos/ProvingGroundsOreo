"""(custom, Nov 15) Warthog guns and riders, from the owner's Forge World bug reports ("Bots in warthog gunners dont shoot
other vehicles", "BOT AIMING STRAIGHT DOWN IN WARTHOG GUNNER SEAT"):
- a Warthog's gun (chaingun, gauss, rocket) fights vehicles before men on foot, unless a man on foot is close (not the
  rocket gun's), as the tank drivers do (Bot.vehicle_pick, HOG_*). The owner: "make warthogs prioritize shooting other
  vehicles before infantry. Unless infantry is close similar to the tank mechanic";
- the rocket Warthog shoots men on foot "if and only when no enemy vehicles are within a range" (RHOG_VEHICLE_R);
- a rider out of a parked vehicle nobody drives does not climb straight back in (PARKED_BAN; live 20261115-051122: a
  Demon in and out of the rocket Warthog at its spawn 10 times);
- every tier fights the man in view on its way to a vehicle (Bot.vehicle_way_target)."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot as botmod                                # noqa: E402
from brain import profiles                                     # noqa: E402
from brain.bot import Belief, Bot, Order                       # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec      # noqa: E402
from test_h4_pickup_board import Flat                          # noqa: E402

HOG = 1


class Blind(Flat):
    def sees(s, *a, **k):
        return False


def pick(kind, enemies, tier="strong", terrain=None, unseen=()):
    """enemies: [(id, x, his vehicle kind or None, weapon)] along +x of a Warthog's gun at the origin. unseen: enemy
    vehicles [(id, x, kind)] whose crew is not in sight."""
    b = Bot(0, 0, profiles.make_profile(tier, "rusher", random.Random(1)), {"name": "reach_test"}, random.Random(2))
    t = terrain or Flat()
    b.T = lambda: t
    me = PlayerState(0, 0, "bot", Vec(), vehicle=HOG)
    hog = dict(handle=HOG, kind=kind, pos=(0, 0, 0), occupied=True, team=0, riders=2, fwd=(1, 0, 0))
    players, vs = [me], [hog]
    for k, x, vk, gun in enemies:
        p = PlayerState(k, 1, f"e{k}", Vec(x, 0.0, 0.0), weapon=gun, vehicle=-1 if vk is None else 100 + k)
        players.append(p)
        if vk is not None:
            vs.append(dict(handle=100 + k, kind=vk, pos=(x, 0, 0), occupied=True, team=1, riders=1, fwd=(-1, 0, 0)))
        b.per.beliefs[k] = Belief(p.pos, Vec(), 0.0, True, "eyes")
    for k, x, vk in unseen:
        players.append(PlayerState(k, 1, f"e{k}", Vec(x, 0.0, 0.0), vehicle=100 + k))
        vs.append(dict(handle=100 + k, kind=vk, pos=(x, 0, 0), occupied=True, team=1, riders=1, fwd=(-1, 0, 0)))
    snap = Snapshot(0.0, players, vehicles=vs, mode="slayer")
    return b.vehicle_pick(me, hog, "gunner", [e[0] for e in enemies], snap)


class WarthogTargetTests(unittest.TestCase):
    def test_vehicle_before_a_man_on_foot(self):
        # (the old score: a chaingun's man on foot 0.3 / 1.5 over a Mongoose 0.3 / 3.6)
        for kind in ("warthog", "gauss"):
            self.assertEqual(pick(kind, [(1, 30.0, "mongoose", "pistol"), (2, 15.0, None, "dmr")]), 1, kind)

    def test_close_man_on_foot_first(self):
        for kind in ("warthog", "gauss"):
            enemies = [(1, 20.0, "banshee", "pistol"), (2, botmod.HOG_FOOT_R - 2, None, "dmr")]
            self.assertEqual(pick(kind, enemies), 2, kind)

    def test_banshees_and_tanks_ranked_among_the_vehicles(self):
        enemies = [(1, 30.0, "mongoose", "pistol"), (2, 35.0, "banshee", "pistol"), (3, 25.0, "ghost", "pistol")]
        self.assertEqual(pick("warthog", enemies), 2)             # the Banshee: its score within the vehicles
        self.assertEqual(pick("warthog", [(1, 30.0, "mongoose", "pistol"), (2, 15.0, None, "dmr"),
                                          (4, 40.0, "scorpion", "pistol")]), 4)

    def test_rocket_man_counts_with_the_vehicles(self):
        self.assertEqual(pick("warthog", [(1, 30.0, "mongoose", "pistol"), (2, 20.0, None, "rockets")]), 2)

    def test_beyond_the_vehicle_range_as_before(self):
        far = [(1, botmod.HOG_VEHICLE_R + 10, "mongoose", "pistol"), (2, 15.0, None, "dmr")]
        self.assertEqual(pick("warthog", far), 2)                 # (both of the rest: the plain score)

    def test_not_the_drivers_tank_rule(self):
        # a Scorpion's gunner and other guns keep the plain score
        self.assertEqual(pick("falcon", [(1, 30.0, "mongoose", "pistol"), (2, 15.0, None, "dmr")]), 2)


class RocketHogTests(unittest.TestCase):
    def test_men_on_foot_with_no_vehicle_about(self):
        self.assertEqual(pick("rwarthog", [(2, 20.0, None, "dmr")]), 2)

    def test_not_men_on_foot_with_a_vehicle_in_sight(self):
        # its crew not recognised yet, the vehicle in sight within range: the rocket gun waits for it
        self.assertIsNone(pick("rwarthog", [(2, 20.0, None, "dmr")], unseen=[(5, 40.0, "ghost")]))
        # crew in sight: the vehicle, the man close in or not
        self.assertEqual(pick("rwarthog", [(2, 8.0, None, "dmr"), (5, 40.0, "ghost", "pistol")]), 5)
        self.assertEqual(pick("rwarthog", [(2, 20.0, None, "rockets"), (5, 40.0, "mongoose", "pistol")]), 5)

    def test_a_vehicle_out_of_range_or_sight_lets_it_fight_men(self):
        self.assertEqual(pick("rwarthog", [(2, 20.0, None, "dmr")],
                              unseen=[(5, botmod.RHOG_VEHICLE_R + 5, "ghost")]), 2)
        self.assertEqual(pick("rwarthog", [(2, 20.0, None, "dmr")], terrain=Blind(), unseen=[(5, 40.0, "ghost")]), 2)

    def test_no_rocket_at_a_man_on_top_of_it(self):
        self.assertIsNone(pick("rwarthog", [(2, botmod.RHOG_FOOT_MIN - 2, None, "dmr")]))

    def test_other_games_rule_unchanged_elsewhere(self):
        from brain import vehicles
        self.assertEqual(vehicles.target_score("reach", "rwarthog", "rocket_hog", "gunner", None), 0.0)
        self.assertGreater(vehicles.target_score("reach", "rwarthog", "rocket_hog", "gunner", None, ground_ok=True), 0)


def parked_gunner(riders=2, now=100.0):
    """A bot on a rocket Warthog's gun, a bot passenger, nobody driving, still since 90 s: it gets out (Bot.drive)."""
    mapdata = dict(name="reach_dlc_medium", flags={}, points={}, items=[])
    b = Bot(0, 0, profiles.make_profile("demon", "rusher", random.Random(3)), mapdata, random.Random(5))
    b.seat, b.seat_for, b.seat_since, b.notes = "gunner", HOG, 90.0, []
    b.order = Order("ride", Vec(10, 18, 0), target=HOG)
    b._terrain = Flat()
    b.T = lambda b=b: b._terrain
    b.still_at, b.still_since = Vec(10, 18, 0), 90.0
    me = PlayerState(0, 0, "me", Vec(10, 18, 0), vehicle=HOG)
    me.gunner_seat, me.turret = True, "warthog_rocket"
    mate = PlayerState(1, 0, "mate", Vec(10, 18, 0), vehicle=HOG)
    hog = dict(handle=HOG, kind="rwarthog", pos=(10.0, 18.0, 0.0), occupied=True, team=0, riders=riders, fwd=(1, 0, 0),
               up=(0, 0, 1))
    act = Action()
    b.drive(now, 1 / 30, me, Snapshot(now, [me, mate], vehicles=[hog], mode="slayer"), act, lambda a, c: c)
    return b, hog, act


class ParkedLoopTests(unittest.TestCase):
    def test_out_and_not_straight_back_in(self):
        b, hog, act = parked_gunner()
        self.assertTrue(act.action)
        out = dict(hog, riders=1)                                   # (it left: the passenger alone)
        self.assertTrue(b.veh_banned(out, 101.0))
        self.assertTrue(b.veh_banned(out, 100.0 + botmod.PARKED_BAN - 1))
        self.assertFalse(b.veh_banned(out, 100.0 + botmod.PARKED_BAN + 1))   # (the ban runs out)

    def test_back_in_once_someone_joins_or_it_moves(self):
        b, hog, _ = parked_gunner()
        self.assertFalse(b.veh_banned(dict(hog, riders=2), 101.0))          # a driver got in
        self.assertFalse(b.veh_banned(dict(hog, riders=1, pos=(20.0, 18.0, 0.0)), 101.0))   # driven off

    def test_the_ride_order_skips_it(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index('if s.order.role in ("ride", "board", "drive") and not close_fight and not urgent:')
        self.assertIn("not s.veh_banned(v, now)", src[i:i + 600])


def walker(tier, dist_to_seat=12.0, seen=True, flag=False):
    b = Bot(0, 0, profiles.make_profile(tier, "rusher", random.Random(1)), {"name": "reach_test"}, random.Random(2))
    me = PlayerState(0, 0, "bot", Vec(), weapon="dmr")
    me.has_flag = flag
    foe = PlayerState(7, 1, "foe", Vec(20, 5, 0), weapon="dmr")
    b.per.beliefs[7] = Belief(foe.pos, Vec(), 0.0, seen, "eyes")
    if seen:
        b.per.recognized.add(7)
    snap = Snapshot(0.0, [me, foe], mode="slayer")
    return b.vehicle_way_target(1.0, me, snap, Vec(dist_to_seat, 0, 0))


class FightOnTheWayTests(unittest.TestCase):
    def test_every_tier_fights_the_man_in_view(self):
        for tier in ("novice", "average", "strong", "top", "demon"):
            self.assertEqual(walker(tier), 7, tier)

    def test_not_in_the_last_steps_nor_carrying_nor_unseen(self):
        self.assertIsNone(walker("demon", dist_to_seat=botmod.VEHICLE_FIGHT_LAST - 1))
        self.assertIsNone(walker("demon", flag=True))
        self.assertIsNone(walker("demon", seen=False))

    def test_the_vehicle_run_fights_then_walks(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index('        if kind == "vehicle":\n')
        j = src.index('        if kind == "board":', i)
        run = src[i:j]
        self.assertIn("foe = s.vehicle_way_target(now, me, snap, vp)", run)
        self.assertLess(run.index("s.fight(now, dt, me, snap, foe, act, nav)"), run.index("s.move_to(me, vp, walk, nav)"))
        self.assertLess(run.index("s.move_to(me, vp, walk, nav)"), run.index("act.action = int(now * 6) % 2 == 0"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
