"""(custom, Nov 25) A Reach Banshee's bomb goes on a man in a vehicle too, and a selected bomb still goes close in.
Live Spire 20261125-175509: two pilots, 91 s of flying, 18 runs, no bomb; the run's man rode a vehicle on 12 of them
and Bot.bomb_lined / air_snap_bomb counted men on foot only."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain.bot as B  # noqa: E402
from brain.bot import AIR_BOMB_NEAR  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to  # noqa: E402
from test_banshee_bomb_aim import Air, banshee  # noqa: E402
from test_demon_vehicles import bot  # noqa: E402


def setup(foe_at, foe_vehicle=-1):
    b = bot("demon", name="reach_test")
    b._terrain = Air()
    b.T = lambda: b._terrain
    b.seat, b.can_cycle, b.veh_kind = "driver", True, "banshee"
    me = PlayerState(0, 0, "bot", Vec(0.0, 0.0, 9.0), vel=Vec(-6.0, 0.0, 0.0), vehicle=77, weapon="banshee")
    foe = PlayerState(1, 1, "foe", foe_at, vehicle=foe_vehicle, weapon="assault_rifle", weapons=["assault_rifle"])
    vehicles = [banshee()] + ([dict(handle=foe_vehicle, kind="warthog", pos=(foe_at.x, foe_at.y, foe_at.z), occupied=True, team=1,
                                    riders=1, turrets=[], manned=[])] if foe_vehicle != -1 else [])
    snap = Snapshot(50.0, [me, foe], vehicles=vehicles, mode="slayer")
    b.air_snap = snap
    b.per.last_seen[1] = b.per.clear_at[1] = 50.0
    act = Action()
    act.yaw, act.pitch = angles_to(me.pos + Vec(0, 0, 0.62), foe.pos)
    return b, me, snap, act


class BombRiderTests(unittest.TestCase):
    def test_lined_on_a_man_in_a_vehicle(self):
        b, me, snap, act = setup(Vec(-8.0, 0.0, 0.0), foe_vehicle=88)
        self.assertTrue(b.bomb_lined(act))

    def test_lined_close_in(self):
        b, me, snap, act = setup(Vec(-1.0, 0.0, 9.0 - (AIR_BOMB_NEAR + 1.0)))
        self.assertTrue(b.bomb_lined(act))

    def test_not_lined_off_him(self):
        b, me, snap, act = setup(Vec(-8.0, 0.0, 0.0), foe_vehicle=88)
        act.yaw += math.radians(40.0)
        self.assertFalse(b.bomb_lined(act))

    def test_snap_bomb_on_a_man_in_a_vehicle(self):
        b, me, snap, act = setup(Vec(-8.0, 0.0, 0.0), foe_vehicle=88)
        b.air_snap_bomb(50.0, me, act, snap)
        self.assertIsNotNone(b.rod)
        self.assertTrue(act.cycle)


class BombHeldTests(unittest.TestCase):
    """(custom, Nov 25) Live Spire 20261125-183823: the bomb selected 14-18 u out, the run over 0.3 s later 4-6 u flat
    from him, "off him before the shot, the bomb kept" (406.0, 414.6, 476.3 s)."""

    def run_state(self, rod, height=12.0):
        b, me, snap, act = setup(Vec(-4.0, 0.0, 0.0))            # 4 u flat: inside PASS_OVER
        me.pos = Vec(0.0, 0.0, height)
        me.yaw = math.pi
        b.air_terrain = lambda: b._terrain
        b.air_run, b.rod, b.rod_next = ["in", 1, 49.0, math.pi], rod, 99.0
        from brain.bot import Belief
        bel = Belief(Vec(-4.0, 0.0, 0.0), Vec(), 50.0, True, "eyes")
        b.per.beliefs[1] = bel
        act.yaw, act.pitch = angles_to(me.pos, bel.pos)
        b.air_pass(50.0, me, 1, bel, bel.pos, act, banshee())
        return b, act

    def test_the_run_stays_on_him_while_the_bomb_comes_up(self):
        b, act = self.run_state(["to", 49.9])
        self.assertEqual(b.air_run[0], "in")
        self.assertEqual(b.bomb_aim[0], 50.0)
        self.assertLess(act.pitch, -0.5)                         # (the nose still down on him)

    def test_no_bomb_ready_and_the_run_is_over(self):
        b, act = self.run_state(None)                            # (rod_next 99: recharging)
        self.assertEqual(b.air_run[0], "out")

    def test_high_over_him_with_the_bomb_ready_it_dives_on(self):
        """Live Spire 20261125-193322 at 427.1 s: 6 u flat and 19 u over its man, a line, no bomb, the run over."""
        b, me, snap, act = setup(Vec(-5.0, 0.0, 0.0))
        me.pos, me.yaw = Vec(0.0, 0.0, 19.0), math.pi
        b.air_terrain = lambda: b._terrain
        b.air_run, b.rod, b.rod_next = ["in", 1, 49.0, math.pi], None, 0.0
        from brain.bot import Belief
        bel = Belief(Vec(-5.0, 0.0, 0.0), Vec(), 50.0, True, "eyes")
        b.per.beliefs[1] = bel
        act.yaw, act.pitch = angles_to(me.pos, bel.pos)
        b.air_pass(50.0, me, 1, bel, bel.pos, act, banshee())
        self.assertEqual(b.air_run[0], "in")
        self.assertLess(act.pitch, -1.0)                         # (the nose down on him)
        me.pos = Vec(0.0, 0.0, 7.0)                              # low over him: the old rule, the run over
        b.air_run = ["in", 1, 49.0, math.pi]
        b.air_pass(50.0, me, 1, bel, bel.pos, act, banshee())
        self.assertEqual(b.air_run[0], "out")

    def test_not_held_into_the_ground(self):
        b, act = self.run_state(["to", 49.9], height=3.0)
        self.assertEqual(b.air_run[0], "out")

    def test_selected_early_on_the_way_in(self):
        b, me, snap, act = setup(Vec(-12.0, 0.0, -7.0))          # 21.5 u off: past the bomb's 18 u
        me.vel = Vec(-9.0, 0.0, -12.0)                           # closing 15 u/s
        act.yaw, act.pitch = angles_to(me.pos + Vec(0, 0, 0.62), Vec(-12.0, 0.0, -7.0))
        b.air_snap_bomb(50.0, me, act, snap)
        self.assertIsNotNone(b.rod)
        b2, me2, snap2, act2 = setup(Vec(-12.0, 0.0, -7.0))
        me2.vel = Vec(0.0, 0.0, 0.0)                             # not closing: not yet
        act2.yaw, act2.pitch = act.yaw, act.pitch
        b2.air_snap_bomb(50.0, me2, act2, snap2)
        self.assertIsNone(getattr(b2, "rod", None))


class NoBoostNearTests(unittest.TestCase):
    """(custom, Nov 25) Live Spire 20261125-193322: the boost let off 0.03 s before the bomb's press on 9 of 15 bombs,
    none of those a kill."""

    def boost_at(self, flat):
        b, me, snap, act = setup(Vec(-flat, 0.0, 0.0))
        me.pos, me.yaw = Vec(0.0, 0.0, 9.0), math.pi
        b.air_terrain = lambda: b._terrain
        b.boost_open = lambda *a: True
        b.air_run, b.rod, b.rod_next = ["in", 1, 49.0, math.pi], None, 99.0
        from brain.bot import Belief
        bel = Belief(Vec(-flat, 0.0, 0.0), Vec(), 50.0, True, "eyes")
        b.per.beliefs[1] = bel
        act.yaw, act.pitch = angles_to(me.pos, bel.pos)
        b.air_pass(50.0, me, 1, bel, bel.pos, act, banshee())
        return act.fire2

    def test_boosted_in_from_far_only(self):
        self.assertTrue(self.boost_at(40.0))
        self.assertFalse(self.boost_at(20.0))


class BombKeptTests(unittest.TestCase):
    """(custom, Nov 25, the owner: "Make it to where the bomb is always selected?") One cycle press after boarding,
    then the trigger alone."""

    @staticmethod
    def nose_on(snap, me, foe_at):
        to = foe_at - (me.pos + Vec(0, 0, 0.62))
        n = to.length()
        snap.vehicles[0]["fwd"] = (to.x / n, to.y / n, to.z / n)

    @staticmethod
    def aim_on(b, me, act, snap, t0=50.0, secs=0.8):
        """The view kept on him from t0 for secs, 0.1 s a tick (Bot.bomb_release's AIR_REL_AIM_S hold, Nov 26)."""
        t = t0
        while t <= t0 + secs + 1e-9 and not act.fire:
            b.per.clear_at[1] = b.per.last_seen[1] = t
            b.air_snap_bomb(t, me, act, snap)
            t += 0.1

    def test_from_anywhere_in_the_bombs_reach(self):
        # (Nov 26: the craft's own nose on him too, Bot.bomb_release; the nose off him holds it, test below)
        b, me, snap, act = setup(Vec(-12.0, 0.0, 0.0))           # 15 u: in the bomb's reach
        b.seat_since, b.bomb_sel = 40.0, 45.0
        self.nose_on(snap, me, Vec(-12.0, 0.0, 0.0))
        self.aim_on(b, me, act, snap)
        self.assertTrue(act.fire)
        b, me, snap, act = setup(Vec(-18.0, 0.0, 0.0))           # 20 u: past it
        b.seat_since, b.bomb_sel = 40.0, 45.0
        self.nose_on(snap, me, Vec(-18.0, 0.0, 0.0))
        self.aim_on(b, me, act, snap)
        self.assertFalse(act.fire)

    def test_the_aim_held_on_him_half_a_second_first(self):
        """(Nov 26, live Boneyard 20:03 + 20:29) Bombs under 0.5 s on him killed 2 of 18, 0.5 s or more 7 of 11."""
        b, me, snap, act = setup(Vec(-12.0, 0.0, 0.0))
        b.seat_since, b.bomb_sel = 40.0, 45.0
        self.nose_on(snap, me, Vec(-12.0, 0.0, 0.0))
        self.aim_on(b, me, act, snap, secs=0.4)
        self.assertFalse(act.fire)
        self.assertIn("air: bomb held, the aim settling on him", b.notes)
        self.aim_on(b, me, act, snap, t0=50.5, secs=0.2)
        self.assertTrue(act.fire)

    def test_the_nose_off_him_holds_it(self):
        """(Nov 26) Bot.bomb_release: the view on his feet but the craft's nose ~0.7 rad off him to the side: no bomb
        yet. Round 1 sim (reconstructed nose): releases more than 0.6 rad off killed 3 of 52 and 2 of 60."""
        b, me, snap, act = setup(Vec(-12.0, 0.0, 0.0))
        b.seat_since, b.bomb_sel = 40.0, 45.0
        snap.vehicles[0]["fwd"] = (-0.77, 0.64, -0.6)            # (~40 deg off him left/right, nose down)
        b.air_snap_bomb(50.0, me, act, snap)
        self.assertFalse(act.fire)
        self.assertIn("air: bomb held, the nose not on him yet", b.notes)

    def test_the_body_above_the_view_still_bombs(self):
        """(Nov 26, live traces) A Reach Banshee's body sits 15-25 deg above the view: on him left/right, the bomb goes."""
        b, me, snap, act = setup(Vec(-12.0, 0.0, 0.0))           # (the view ~37 deg down on him)
        b.seat_since, b.bomb_sel = 40.0, 45.0
        snap.vehicles[0]["fwd"] = (-0.94, 0.0, -0.34)            # (the body ~20 deg down: 17 deg above the view)
        self.aim_on(b, me, act, snap)
        self.assertTrue(act.fire)

    def test_held_until_the_nose_is_within_5_deg(self):
        """(Nov 26, live Boneyard 20:03) The nose under 5 deg off him killed 5 of 6 bombs, 5-15 deg 0 of 5."""
        for deg, want in ((8.0, False), (3.0, True)):
            b, me, snap, act = setup(Vec(-12.0, 0.0, 0.0))
            b.seat_since, b.bomb_sel = 40.0, 45.0
            a = math.pi + math.radians(deg)
            snap.vehicles[0]["fwd"] = (0.94 * math.cos(a), 0.94 * math.sin(a), -0.34)
            self.aim_on(b, me, act, snap, secs=1.3)              # (past the old 1 s "near him" fallback too)
            self.assertEqual(act.fire, want, deg)

    def test_the_lead_is_his_walk_over_the_bombs_flight(self):
        """(Nov 26) Bot.bomb_lead: the owner's 12 bomb kills led the man a median 0.59 s of his walk (the bomb's flight)."""
        b, me, snap, act = setup(Vec(-12.0, 0.0, 0.0))
        o = me.pos + Vec(0, 0, 0.62)
        feet = Vec(-12.0, 0.0, 0.0)
        self.assertEqual(b.bomb_lead(o, feet, Vec()), feet)                       # standing: his feet
        p = b.bomb_lead(o, feet, Vec(0.0, 2.0, 0.0))                             # walking 2 u/s across
        t = math.dist((o.x, o.y, o.z), (feet.x, feet.y, feet.z)) / B.REACH_BOMB_SPEED + 0.05
        self.assertAlmostEqual(p.y, 2.0 * t, places=6)
        self.assertEqual((p.x, p.z), (feet.x, feet.z))
        p = b.bomb_lead(o, feet, Vec(0.0, 40.0, 0.0))                            # (a vehicle's speed: capped)
        self.assertAlmostEqual(p.y, B.AIR_BOMB_LEAD_CAP)
        b.game = "h3"
        self.assertEqual(b.bomb_lead(o, feet, Vec(0.0, 2.0, 0.0)), feet)         # (Reach's Banshee pilot only)

    def test_a_walking_man_is_bombed_where_he_will_be(self):
        b, me, snap, act = setup(Vec(-12.0, 0.0, 0.0))
        b.seat_since, b.bomb_sel = 40.0, 45.0
        foe = snap.player(1)
        foe.vel = Vec(0.0, 2.5, 0.0)
        led = b.bomb_lead(me.pos + Vec(0, 0, 0.62), foe.pos, foe.vel)
        act.yaw, act.pitch = angles_to(me.pos + Vec(0, 0, 0.62), led)
        self.nose_on(snap, me, led)
        self.aim_on(b, me, act, snap)
        self.assertTrue(act.fire)

    def test_a_climbing_nose_holds_it(self):
        b, me, snap, act = setup(Vec(-12.0, 0.0, 0.0))
        b.seat_since, b.bomb_sel = 40.0, 45.0
        snap.vehicles[0]["fwd"] = (-0.94, 0.0, 0.34)             # (the body 20 deg up)
        b.air_snap_bomb(50.0, me, act, snap)
        self.assertFalse(act.fire)
        self.assertIn("air: bomb held, the nose climbing", b.notes)

    def test_selected_once_then_the_shot_at_once(self):
        b, me, snap, act = setup(Vec(-6.0, 0.0, 0.0))
        self.nose_on(snap, me, Vec(-6.0, 0.0, 0.0))
        b.seat_since, b.bomb_sel = 40.0, None
        a = Action()
        b.fuel_rod(50.0, a)                                      # nothing to bomb yet: the bomb selected
        self.assertTrue(a.cycle)
        self.assertEqual(b.bomb_sel, 50.0)
        a = Action()
        b.fuel_rod(50.5, a)
        self.assertFalse(a.cycle)                                # (not pressed again)
        self.aim_on(b, me, act, snap, t0=51.0)                   # a man under the nose: its shot once the aim holds
        self.assertTrue(act.fire)
        self.assertFalse(act.cycle)
        self.assertEqual(b.rod[0], "shot")
        a = Action()
        b.fuel_rod(52.0, a)                                      # the shot over: still selected, no cycle back
        self.assertFalse(a.cycle)
        self.assertIsNone(b.rod)
        self.assertEqual(b.bomb_sel, 50.0)

    def test_the_recharge_is_waited_out(self):
        b, me, snap, act = setup(Vec(-8.0, 0.0, 0.0))
        b.seat_since, b.bomb_sel, b.rod_next = 40.0, 45.0, 52.0
        b.air_snap_bomb(50.0, me, act, snap)
        self.assertFalse(act.fire)


if __name__ == "__main__":
    unittest.main()
