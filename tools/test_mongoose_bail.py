"""(custom, Nov 25) Off a Mongoose when hit or with an enemy on radar (Bot.mongoose_bail, MONGOOSE_RADAR_R): the owner,
"They drive until an enemy is on radar, or as soon as they get shot and dismount". Driver and passenger, every tier and
game; not with the objective, not in a race. (custom, Nov 27, the owner: "they just drive to the open, get hit
dismount and die anyways") a driver drives away from him first and gets off behind cover, with him close (CLOSE_R),
stalled, or after FLEE_MAX s; a passenger rides on while it runs (Bot.goose_flee, brain/goose_rules)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.bot import MONGOOSE_RADAR_R, MONGOOSE_RETRY, Belief    # noqa: E402
from brain import goose_rules as G                                # noqa: E402
from brain.core import PlayerState, Vec                            # noqa: E402
from test_mongoose_transport import drive, scene                   # noqa: E402

NOTE = "mongoose: {}, off and on foot"


def got_off(bot, why):
    """Off with that reason (Nov 27: its end of the drive away in brackets)."""
    return any(n.startswith(f"mongoose: {why}") and n.endswith("off and on foot") for n in bot.notes)


def ride(kind="mongoose", seat="driver", mode="slayer"):
    d, b, me, snap = scene(kind, mode)
    b.seat, b.seat_for, b.seat_since = seat, 10, 99.0       # (on it since 99 s)
    enemy = PlayerState(1, 1, "enemy", Vec(30, 0, 0), weapon="dmr")
    snap.players.append(enemy)
    return b, me, snap, enemy


def spot(b, enemy, x, source="eyes", t=100.0):
    enemy.pos = Vec(x, 0, 0)
    b.per.beliefs[1] = Belief(enemy.pos, Vec(), t, source == "eyes", source)


class MongooseBailTests(unittest.TestCase):
    def test_off_when_shot(self):
        b, me, snap, enemy = ride()
        spot(b, enemy, G.CLOSE_R - 1.0)                     # (him close: off at once, no outrunning him)
        b.per.hurt_at = 100.0
        act = drive(b, me, snap)
        self.assertTrue(act.action)
        self.assertEqual((act.forward, act.fire), (0.0, False))
        self.assertIn(NOTE.format("shot (an enemy close)"), b.notes)
        self.assertGreaterEqual(b.vehicle_retry_at, 100.0 + MONGOOSE_RETRY)
        self.assertEqual(b.vjob, "dismount")

    def test_a_hit_before_it_got_on_does_not_count(self):
        b, me, snap, enemy = ride()
        b.per.hurt_at = 98.0
        drive(b, me, snap)
        self.assertNotIn(NOTE.format("shot"), b.notes)

    def test_off_with_an_enemy_on_radar_or_in_view_close(self):
        for source in ("eyes", "radar"):
            b, me, snap, enemy = ride()
            spot(b, enemy, G.CLOSE_R - 1.0, source)
            act = drive(b, me, snap)
            self.assertTrue(act.action, source)
            self.assertIn(NOTE.format("an enemy on radar (an enemy close)"), b.notes, source)

    def test_shot_from_afar_drives_away_then_off(self):
        # (custom, Nov 27) him 30 u off: away from him at full speed, in sight still; off after FLEE_MAX s
        b, me, snap, enemy = ride()
        me.vel = Vec(10, 0, 0)
        spot(b, enemy, -30.0)
        b.per.hurt_at = 100.0
        act = drive(b, me, snap)
        self.assertFalse(act.action)
        self.assertEqual(act.forward, 1.0)
        self.assertIn("mongoose: shot, driving away", b.notes)
        self.assertGreater(b.retreat_to.x, 10.0)            # (away: he is at -30)
        t = 100.0
        while not act.action and t < 100.0 + G.FLEE_MAX + 0.5:
            t += 0.1
            spot(b, enemy, -30.0, t=t)
            act = drive(b, me, snap, t)
        self.assertTrue(act.action)
        self.assertAlmostEqual(t, 100.0 + G.FLEE_MAX, delta=0.15)
        self.assertTrue(got_off(b, "shot (ran long enough)"))

    def test_radar_dot_in_range_drives_away_first(self):
        b, me, snap, enemy = ride()
        me.vel = Vec(10, 0, 0)
        spot(b, enemy, MONGOOSE_RADAR_R - 0.5, "radar")
        act = drive(b, me, snap)
        self.assertFalse(act.action)
        self.assertIn("mongoose: an enemy on radar, driving away", b.notes)

    def test_rides_on_past_radar_range_or_on_an_old_dot_or_a_teammate(self):
        b, me, snap, enemy = ride()
        spot(b, enemy, MONGOOSE_RADAR_R + 1.0)
        drive(b, me, snap)
        b2, me2, snap2, enemy2 = ride()
        spot(b2, enemy2, 4.0, "radar", t=98.0)               # (2 s old)
        drive(b2, me2, snap2)
        b3, me3, snap3, mate = ride()
        mate.team = 0
        spot(b3, mate, 4.0)
        drive(b3, me3, snap3)
        for bot in (b, b2, b3):
            self.assertFalse(any(n.startswith("mongoose: ") and n.endswith("off and on foot") for n in bot.notes))

    def test_the_passenger_too(self):
        b, me, snap, enemy = ride(seat="passenger")
        b.per.hurt_at = 100.0
        self.assertTrue(drive(b, me, snap).action)          # (stopped: off at once)
        self.assertIn(NOTE.format("shot (it slowed)"), b.notes)
        b, me, snap, enemy = ride(seat="passenger")         # (custom, Nov 27) running: it rides it out
        me.vel = Vec(10, 0, 0)
        b.per.hurt_at = 100.0
        self.assertFalse(drive(b, me, snap).action)
        self.assertIn("mongoose: shot, riding it out", b.notes)

    def test_rides_on_with_the_objective_or_in_a_race(self):
        b, me, snap, enemy = ride()
        me.has_flag = True
        b.per.hurt_at = 100.0
        drive(b, me, snap)
        b2, me2, snap2, enemy2 = ride(mode="race")
        b2.per.hurt_at = 100.0
        drive(b2, me2, snap2)
        for bot in (b, b2):
            self.assertNotIn(NOTE.format("shot"), bot.notes)

    def test_not_other_vehicles(self):
        b, me, snap, enemy = ride(kind="warthog")
        b.per.hurt_at = 100.0
        drive(b, me, snap)
        self.assertNotIn(NOTE.format("shot"), b.notes)


class MongooseBoardTests(unittest.TestCase):
    """(custom, Nov 25, the owner: "Also stop bots boarding a Mongoose while an enemy is on radar?" "Yes, add that")
    Bot.goose_off_limits, set each decide; veh_banned honours it for that tick; the walk to one is given up."""

    def on_foot(self, enemy_x, kind="mongoose", **kw):
        b, me, snap, enemy = ride(kind=kind, **kw)
        me.vehicle = -1
        snap.vehicles[0]["occupied"], snap.vehicles[0]["riders"] = False, 0
        spot(b, enemy, enemy_x)
        return b, me, snap

    def test_no_mongoose_with_an_enemy_on_radar(self):
        b, me, snap = self.on_foot(4.0)
        self.assertTrue(b.goose_off_limits(100.0, me, snap))
        self.assertTrue(b.veh_banned(snap.vehicles[0], 100.0))
        self.assertFalse(b.veh_banned(snap.vehicles[0], 100.5))          # (only the tick it was read)

    def test_free_when_he_is_far_or_it_is_another_kind_or_exempt(self):
        b, me, snap = self.on_foot(MONGOOSE_RADAR_R + 1.0)
        self.assertFalse(b.goose_off_limits(100.0, me, snap))
        b, me, snap = self.on_foot(4.0, kind="warthog")
        b.goose_off_limits(100.0, me, snap)
        self.assertFalse(b.veh_banned(snap.vehicles[0], 100.0))
        b, me, snap = self.on_foot(4.0, mode="race")
        self.assertFalse(b.goose_off_limits(100.0, me, snap))
        b, me, snap = self.on_foot(4.0)
        me.has_flag = True
        self.assertFalse(b.goose_off_limits(100.0, me, snap))

    def test_the_walk_to_one_is_given_up(self):
        b, me, snap = self.on_foot(9.0)
        me.pos = Vec(5, 0, 0)                     # (him 4 u off)
        b.goal, b.next_decide, b.vehicle_until = ("vehicle", 10), 999.0, 110.0
        b.plan(100.0, 1 / 30, snap, lambda a, c: True, lambda a, c: c, [])
        self.assertIn("mongoose: an enemy on radar, not getting on", b.notes)
        self.assertEqual((b.next_decide, b.vehicle_until), (100.0, 100.0))

    def test_a_wheelman_does_not_pick_one(self):
        from brain import profiles
        for x, picked in ((4.0, False), (MONGOOSE_RADAR_R + 1.0, True)):
            b, me, snap = self.on_foot(x)
            b.p = profiles.make_profile("average", "wheelman", __import__("random").Random(1))
            b.goose_off_limits(100.0, me, snap)
            self.assertEqual(b.wheel_pick(100.0, me, snap) is not None, picked, x)


if __name__ == "__main__":
    unittest.main()
