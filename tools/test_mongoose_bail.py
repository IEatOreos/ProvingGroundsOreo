"""(custom, Nov 25) Off a Mongoose when hit or with an enemy on radar (Bot.mongoose_bail, MONGOOSE_RADAR_R): the owner,
"They drive until an enemy is on radar, or as soon as they get shot and dismount". Driver and passenger, every tier and
game; not with the objective, not in a race."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain.bot import MONGOOSE_RADAR_R, MONGOOSE_RETRY, Belief    # noqa: E402
from brain.core import PlayerState, Vec                            # noqa: E402
from test_mongoose_transport import drive, scene                   # noqa: E402

NOTE = "mongoose: {}, off and on foot"


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
        b.per.hurt_at = 100.0
        act = drive(b, me, snap)
        self.assertTrue(act.action)
        self.assertEqual((act.forward, act.fire), (0.0, False))
        self.assertIn(NOTE.format("shot"), b.notes)
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
            spot(b, enemy, MONGOOSE_RADAR_R - 0.5, source)
            act = drive(b, me, snap)
            self.assertTrue(act.action, source)
            self.assertIn(NOTE.format("an enemy on radar"), b.notes, source)

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
        self.assertTrue(drive(b, me, snap).action)
        self.assertIn(NOTE.format("shot"), b.notes)

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


if __name__ == "__main__":
    unittest.main()
