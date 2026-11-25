"""(custom, Nov 25, the owner: "The falcon gunner never hits a shot" ... "Do all of them just no extra error per round")
A Reach Falcon side gun: aimed from its own mount on the Falcon (vehicles.falcon_gun_origin), led at its round's 100 u/s
(Legendary and Demon locked on and led on this gun only: "Yes, this gun only"), never fired past 30 u, fired in the
campaign AI's bursts (Bot.falcon_gun_fire); its pilot holds 8-12 u (vehicles.FALCON_GUN_RANGE)."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import vehicles                              # noqa: E402
from brain.bot import Belief                            # noqa: E402
from brain.core import PlayerState, Vec                 # noqa: E402
from brain.profiles import make_profile                 # noqa: E402
from test_mongoose_transport import drive, scene        # noqa: E402

LEFT = "falcon_side_gun_left"


def gunner(turret=LEFT, at=Vec(0, 15, 0), vel=Vec(3, 0, 0), tier=None):
    """A bot on a Falcon's gun (facing +x at the origin), its pilot a teammate, a man at `at` moving at `vel`."""
    d, b, me, snap = scene("falcon")
    if tier is not None:
        b.p = make_profile(tier, "rusher", random.Random(3))
        from brain.bot import Aim
        b.aim = Aim(b.p, random.Random(3))
    b._terrain.height_over = lambda x, y, z: 0.0
    b.seat, b.seat_since = "gunner", 90.0
    me.turret, me.gunner_seat = turret, True
    snap.vehicles[0]["riders"] = 2
    snap.players.append(PlayerState(5, 0, "pilot", Vec(), vehicle=10))
    e = PlayerState(1, 1, "enemy", at, weapon="assault_rifle")
    e.vel = vel
    snap.players.append(e)
    b.per.recognized.add(1)
    b.per.beliefs[1] = Belief(at, vel, 100.0, True, "eyes")
    me.turret_origin = vehicles.falcon_gun_origin(snap.vehicles[0], turret)
    return b, me, snap


class OriginTests(unittest.TestCase):
    def test_on_its_own_side_at_the_guns_height(self):
        v = dict(pos=(10, 20, 5), fwd=(1, 0, 0))
        h = vehicles.GUN_HEIGHT["falcon_side_gun"]
        self.assertEqual(vehicles.falcon_gun_origin(v, LEFT), Vec(10 - 0.34, 20.5, 5 + h))
        self.assertEqual(vehicles.falcon_gun_origin(v, "falcon_side_gun_right"), Vec(10 - 0.34, 19.5, 5 + h))
        o = vehicles.falcon_gun_origin(dict(pos=(0, 0, 0), fwd=(0, 1, 0)), LEFT)    # (facing +y: left is -x)
        self.assertAlmostEqual(o.x, -0.5)
        self.assertAlmostEqual(o.y, -0.34)

    def test_the_live_mount_when_it_reads_right(self):
        v = dict(pos=(0, 0, 0), fwd=(1, 0, 0))
        o = vehicles.falcon_gun_origin(v, LEFT, (-0.3, 0.55, 0.05))
        self.assertEqual((round(o.x, 2), round(o.y, 2)), (-0.3, 0.55))
        for bad in ((120.0, 40.0, 3.0), (-0.3, -0.55, 0.0), (float("nan"), 0.5, 0.0)):   # (world place, other side)
            o = vehicles.falcon_gun_origin(v, LEFT, bad)
            self.assertEqual((round(o.x, 2), round(o.y, 2)), (-0.34, 0.5), bad)

    def test_none_without_a_facing_or_for_another_gun(self):
        self.assertIsNone(vehicles.falcon_gun_origin(dict(pos=(0, 0, 0), fwd=None), LEFT))
        self.assertIsNone(vehicles.falcon_gun_origin(dict(pos=(0, 0, 0), fwd=(1, 0, 0)), "warthog_chaingun"))


class LeadTests(unittest.TestCase):
    def test_every_tier_leads_its_100_u_s_round(self):
        b, me, snap = gunner(tier="average")
        seen = {}
        step = b.aim.step

        def spy(*a, **k):
            seen.update(k)
            return step(*a, **k)
        b.aim.step = spy
        drive(b, me, snap)
        self.assertEqual(seen.get("shot_speed"), vehicles.FALCON_GUN_SPEED)

    def test_legendary_and_demon_locked_on_and_led(self):
        for tier in ("top", "demon"):
            b, me, snap = gunner(tier=tier)
            drive(b, me, snap)
            o = me.turret_origin
            t =(Vec(0, 15, 0) - o).length() / vehicles.FALCON_GUN_SPEED + 0.05
            led = math.atan2(15 - o.y, 3 * t - o.x)
            self.assertAlmostEqual(b.aim.goal[0], led, places=2, msg=tier)
            self.assertLess(b.aim.goal[0], math.atan2(15 - o.y, -o.x) - 0.01, tier)     # (ahead of him: +x)

    def test_other_guns_keep_their_aim(self):
        b, me, snap = gunner(turret="falcon_side_grenade_left", tier="top")
        seen = {}
        step = b.aim.step

        def spy(*a, **k):
            seen.update(k)
            return step(*a, **k)
        b.aim.step = spy
        drive(b, me, snap)
        self.assertIsNone(seen.get("shot_speed"))


class TriggerTests(unittest.TestCase):
    def test_no_fire_past_30_u(self):
        for y, fires in ((15.0, True), (35.0, False)):
            b, me, snap = gunner(at=Vec(0, y, 0), vel=Vec(), tier="top")
            self.assertEqual(drive(b, me, snap).fire, fires, y)

    def test_campaign_bursts(self):
        b, me, snap = gunner(tier="top")
        on, now = [], 100.0
        while now < 106.0:
            on.append((now, b.falcon_gun_fire(now, me, 1, True)))
            now += 1 / 30
        first_off = next(t for t, f in on if not f) - 100.0
        self.assertTrue(1.5 <= first_off <= 2.05, first_off)
        back = next(t for t, f in on if f and t > 100.0 + first_off) - (100.0 + first_off)
        self.assertTrue(0.7 <= back <= 1.3, back)

    def test_let_go_long_enough_and_the_next_burst_is_fresh(self):
        b, me, snap = gunner(tier="top")
        for i in range(30):                      # (1 s)
            b.falcon_gun_fire(100.0 + i / 30, me, 1, True)
        for i in range(30):                      # (1 s off)
            b.falcon_gun_fire(101.0 + i / 30, me, 1, False)
        self.assertTrue(b.falcon_gun_fire(102.0, me, 1, True))
        self.assertGreaterEqual(b.fburst[1] - 102.0, 1.5)      # (a whole new burst, not the 1 s one's rest)


class PilotTests(unittest.TestCase):
    def strafe(self, y, game=None):
        d, b, me, snap = scene("falcon")
        if game:
            b.game = game
        b._terrain.height_over = lambda x, y_, z: 5.0
        b._terrain.air_heights = (5.0,)
        b.air_terrain = lambda: b._terrain
        me.pos = Vec(0, 0, 10)
        snap.vehicles[0].update(pos=(0, 0, 10), riders=2, turrets=[LEFT, "falcon_side_gun_right"], manned=[LEFT])
        g = PlayerState(5, 0, "gunner", Vec(0, 0, 10), vehicle=10)
        g.gunner_seat, g.turret = True, LEFT
        snap.players.append(g)
        e = PlayerState(1, 1, "enemy", Vec(0, y, 10), weapon="assault_rifle")
        snap.players.append(e)
        b.per.recognized.add(1)
        b.per.beliefs[1] = Belief(e.pos, Vec(), 100.0, True, "eyes")
        return drive(b, me, snap).strafe

    def test_holds_8_to_12_u(self):
        self.assertEqual(self.strafe(6.0), -0.6)
        self.assertEqual(self.strafe(10.0), 0.0)
        self.assertEqual(self.strafe(15.0), 0.6)

    def test_other_games_keep_8_to_18(self):
        self.assertEqual(self.strafe(15.0, "h3"), 0.0)


if __name__ == "__main__":
    unittest.main()
