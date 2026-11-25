"""(custom, Nov 24) The owner's picks from the campaign comparison (HREK ai\\generic.character and the vehicles' tags),
Reach, every tier at the wheel but Easy: the Revenant's gun range (7-15 u held, no shot inside 4 u or past 25 u) and its
lob past 20 u worked out from its shot's flight; the Scorpion's feet-or-chest aim, its turns (throttle never under 0.6,
the view leading the turn), men on foot within 10 u first and shelled from a stop, its wider tank ground; the Falcon
pilot's height keeping the man inside its side guns' pitch."""
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import terrain, vehicles                     # noqa: E402
from brain.bot import Belief                            # noqa: E402
from brain.core import PlayerState, Vec                 # noqa: E402
from brain.equipment import game_of                     # noqa: E402
from brain.profiles import make_profile                 # noqa: E402
from test_mongoose_transport import drive, scene        # noqa: E402
from test_tank_targets import pick                      # noqa: E402


def fight(kind, game="reach", tier=None):
    d, b, me, snap = scene(kind)
    if game != "reach":
        b.map["name"] = game + "_test"
        b.game = game_of(b.map["name"])
    if tier is not None:
        import random
        b.p = make_profile(tier, "rusher", random.Random(3))
    enemy = PlayerState(1, 1, "enemy", Vec(12, 0, 0), weapon="assault_rifle")
    snap.players.append(enemy)
    b.per.recognized.add(1)
    return b, me, snap, enemy


def at(b, enemy, x, y=0.0, now=100.0):
    enemy.pos = Vec(x, y, 0)
    b.per.beliefs[1] = Belief(enemy.pos, Vec(), now, True, "eyes")


def in_ghost(snap, enemy, x):
    enemy.vehicle = 20
    snap.vehicles.append(dict(handle=20, kind="ghost", pos=(x, 0, 0), occupied=True, team=1, riders=1,
                              fwd=(-1, 0, 0)))


class RevenantTests(unittest.TestCase):
    def test_holds_7_to_15_and_drives_in_from_farther(self):
        b, me, snap, enemy = fight("revenant")
        at(b, enemy, 12)
        self.assertEqual(drive(b, me, snap).forward, 0.0)
        at(b, enemy, 20, now=100.1)
        self.assertEqual(drive(b, me, snap, now=100.1).forward, 1.0)     # (was held at 10-30 u)

    def test_no_shot_inside_4_or_past_25(self):
        for x, fires in ((3.0, False), (5.0, True), (26.0, False)):
            b, me, snap, enemy = fight("revenant")
            in_ghost(snap, enemy, x)              # (a man in a vehicle: no boarder's run down)
            at(b, enemy, x)
            self.assertEqual(drive(b, me, snap).fire, fires, x)

    def test_other_games_keep_10_to_30(self):
        b, me, snap, enemy = fight("revenant", "h4")
        at(b, enemy, 20)
        self.assertEqual(drive(b, me, snap).forward, 0.0)

    def test_lob_measured_to_20_computed_past_it(self):
        cam, a15 = vehicles.driver_view("revenant", 15.0, -2.0, "reach")
        self.assertAlmostEqual(math.degrees(a15), 9.0, places=3)         # (the owner's measured lob)
        a20 = math.degrees(vehicles.driver_view("revenant", 20.25, -2.0, "reach")[1])
        a25 = math.degrees(vehicles.driver_view("revenant", 25.0, -2.0, "reach")[1])
        self.assertLess(abs(a20 - 9.0), 0.6)                             # (the two meet at 20 u)
        self.assertGreater(a25, 12.0)
        self.assertLess(a25, 14.5)
        # (a man higher up: a shorter way down for the shot, no more lob than on the level)
        self.assertLessEqual(vehicles.revenant_lob(25.0, 2.0), vehicles.revenant_lob(25.0, -2.0) + 1e-6)
        for kind, game, dz in (("revenant", "h4", -2.0), ("revenant", "reach", None), ("wraith", "reach", -2.0)):
            self.assertAlmostEqual(vehicles.driver_view(kind, 25.0, dz, game)[1],
                                   vehicles.driver_view(kind, 25.0)[1], msg=(kind, game, dz))


class ScorpionTests(unittest.TestCase):
    def aims(self, sees):
        b, me, snap, enemy = fight("scorpion")
        b._terrain = SimpleNamespace(vnav=lambda start, goal: goal, point_los=lambda a, p, mode=None: sees)
        seen = []
        step = b.aim.step
        b.aim.step = lambda *a, **k: (seen.append(k["splash_at_feet"]), step(*a, **k))[1]
        at(b, enemy, 20)
        drive(b, me, snap)
        return seen[-1]

    def test_feet_when_it_sees_them_else_the_chest(self):
        self.assertTrue(self.aims(True))         # (Legendary, fixed: its chest aim was every shot)
        self.assertFalse(self.aims(False))

    def test_a_man_on_foot_within_10_u_is_shelled_from_a_stop(self):
        b, me, snap, enemy = fight("scorpion")
        at(b, enemy, 4)
        act = drive(b, me, snap)
        self.assertEqual((act.forward, act.strafe), (0.0, 0.0))
        self.assertNotEqual(b.att[0], "splatter")
        self.assertIn("vehicle: a man on foot close in, holding still to shell him", b.notes)

    def test_the_wraith_and_easy_as_before(self):
        b, me, snap, enemy = fight("wraith")
        at(b, enemy, 4)
        drive(b, me, snap)
        self.assertEqual(b.att[0], "splatter")
        b, me, snap, enemy = fight("scorpion", tier="novice")
        at(b, enemy, 4)
        self.assertNotIn("vehicle: a man on foot close in, holding still to shell him", b.notes)

    def test_the_nearest_man_on_foot_first_whatever_his_score(self):
        enemies = [(1, 8.0, None, "rockets"), (2, 4.0, None, "pistol")]
        self.assertEqual(pick("scorpion", enemies), 2)
        self.assertEqual(pick("wraith", enemies), 1)          # (the Wraith keeps the score within the band)

    def travel(self, goal, kind="scorpion", game="reach", tier=None):
        b, me, snap, enemy = fight(kind, game, tier)
        snap.players.remove(enemy)
        b.drive_to = b.order.point = goal
        return drive(b, me, snap)

    def test_turns_at_0_6_throttle_and_the_view_leads(self):
        act = self.travel(Vec(-50, 50, 0))                     # (135 deg off its nose: was 0.35)
        self.assertEqual(act.forward, 0.6)
        act = self.travel(Vec(50, 50, 0))                      # (45 deg off: led to 1 rad, the forward arc)
        self.assertAlmostEqual(act.yaw, 1.0, places=3)
        for kw in (dict(game="h4"), dict(tier="novice"), dict(kind="wraith")):
            act = self.travel(Vec(-50, 50, 0), **kw)
            self.assertEqual(act.forward, 0.35, kw)

    def test_tank_ground_is_1_75_u_clear(self):
        self.assertEqual(terrain.Terrain.VEH_ROOM_TANK, 7)


class FalconTests(unittest.TestCase):
    def setUp(self):
        d, self.b, self.me, snap = scene("falcon")
        self.me.pos = Vec(0, 0, 10)               # (5 u over its floor: h)

    def elevation(self, goal, at):
        gun = self.me.pos.z - 5.0 + goal + vehicles.GUN_HEIGHT["falcon_side_gun"]
        return math.degrees(math.atan2(at.z + 0.35 - gun, math.hypot(at.x, at.y)))

    def test_up_when_he_is_over_the_guns(self):
        at = Vec(5, 0, 20)
        goal = self.b.falcon_gun_height(self.me, at, 5.0, 5.0)
        self.assertGreater(goal, 5.0)
        self.assertAlmostEqual(self.elevation(goal, at), 20.0, places=3)

    def test_down_when_he_is_too_steeply_under(self):
        at = Vec(5, 0, 0)
        goal = self.b.falcon_gun_height(self.me, at, 5.0, 5.0)
        self.assertLess(goal, 5.0)
        self.assertAlmostEqual(self.elevation(goal, at), -55.0, places=3)

    def test_left_alone_inside_the_pitch_or_right_under(self):
        self.assertEqual(self.b.falcon_gun_height(self.me, Vec(10, 0, 8), 5.0, 5.0), 5.0)
        self.assertEqual(self.b.falcon_gun_height(self.me, Vec(0.5, 0, 0), 5.0, 5.0), 5.0)


if __name__ == "__main__":
    unittest.main()
