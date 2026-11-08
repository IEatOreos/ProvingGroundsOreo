"""(Custom) the owner's Forge World bug reports, Nov 7 (logs/bug_reports/reach_forge_halo_20261107-180755): Demons
shot by him while on their way to a gun or a seat did not shoot back, and one swapped its empty DMR for an assault
rifle that held fire at 13 u. Bot.decide on a real map (as test_legendary_power_fetch.DemonFetchCommitTests).

Run: python tools/test_shoot_back.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))          # (test_demon_fire's Cover)
from brain.core import PlayerState, Snapshot, Vec, angles_to, eye
from brain.profiles import make_profile

GUN = Vec(-27.3, 14.6, 7.6)


class ShootBackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from brain.maps import load_map
        cls.map = load_map("reach_cex_headlong")

    def bot(self, tier):
        from brain.bot import Bot
        return Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), self.map, random.Random(5))

    def scene(self, tier, gun_off=6.0, foe_d=14.0, aiming=True, hurt=True):
        """A bot gun_off from the gun it was sent for, a foe in view foe_d off, aiming at it or not, and its shield
        dropping half a second ago (perception's hurt_at: it was not in a fight)."""
        from brain.bot import Belief
        b = self.bot(tier)
        me = PlayerState(0, 0, "bot", Vec(GUN.x + gun_off, GUN.y, GUN.z), weapon="dmr",
                         weapons=["dmr", "assault_rifle"], ammo=[45, 160], mag=[15, 32])
        me.shield = 0.3
        foe = PlayerState(1, 1, "foe", Vec(me.pos.x, me.pos.y - foe_d, GUN.z), weapon="dmr", weapons=["dmr"],
                          ammo=[45], mag=[15])
        yaw, pitch = angles_to(eye(foe), me.pos + Vec(0, 0, 0.35))
        foe.yaw, foe.pitch = (yaw, pitch) if aiming else (yaw + 1.5, pitch)
        snap = Snapshot(100.0, [me, foe], mode="slayer")
        b.per.beliefs[1] = Belief(foe.pos, Vec(), 100.0, True, "eyes")
        b.per.recognized.add(1)
        b.per.last_seen[1] = 100.0
        if hurt:
            b.per.hurt_at = 99.5
        b.fetch = (GUN, "rockets", 130.0, None)
        return b, me, snap

    def decide(self, *a, **kw):
        b, me, snap = self.scene(*a, **kw)
        return b.decide(100.0, me, snap)[0], b

    def test_demon_shot_by_the_man_in_view_fights_him_over_the_gun(self):
        goal, b = self.decide("demon")
        self.assertEqual(goal, "fight")
        self.assertTrue(b.last_flags["hit"])

    def test_not_shot_the_demon_still_takes_the_gun(self):
        self.assertEqual(self.decide("demon", hurt=False)[0], "item")

    def test_a_man_in_view_looking_elsewhere_is_not_the_shooter(self):
        self.assertEqual(self.decide("demon", aiming=False)[0], "item")

    def test_legendary_answers_too_and_others_keep_their_rules(self):
        self.assertEqual(self.decide("top")[0], "fight")
        for tier in ("strong", "average", "novice"):
            with self.subTest(tier=tier):
                b, me, snap = self.scene(tier)
                self.assertFalse(b.shoot_back(me, snap, {("item", GUN): 2.0, ("fight", 1): 1.7}, [1], True, None))

    def test_scaling_top_is_not_fixed_high(self):
        from brain.bot import Bot
        from brain.scaling import profile as scaling_profile
        b = Bot(0, 0, scaling_profile(1.0, "rusher", random.Random(3)), self.map, random.Random(5))
        _, me, snap = self.scene("demon")
        self.assertFalse(b.shoot_back(me, snap, {("item", GUN): 2.0, ("fight", 1): 1.7}, [1], True, None))

    def test_a_regroup_or_a_seat_keeps_its_way(self):
        b, me, snap = self.scene("demon")
        self.assertFalse(b.shoot_back(me, snap, {("item", GUN): 2.0, ("fight", 1): 1.7}, [1], True, Vec()))
        me.vehicle = 7
        self.assertFalse(b.shoot_back(me, snap, {("item", GUN): 2.0, ("fight", 1): 1.7}, [1], True, None))

    def test_retreat_to_cover_still_wins(self):
        b, me, snap = self.scene("demon")
        scores = {("item", GUN): 2.0, ("fight", 1): 1.7, ("retreat", Vec(1, 1, 1)): 3.1}
        self.assertTrue(b.shoot_back(me, snap, scores, [1], True, None))
        self.assertAlmostEqual(scores[("fight", 1)], 2.4)
        self.assertEqual(max(scores, key=scores.get)[0], "retreat")

    def test_hit_flag_comes_from_perception_out_of_a_fight(self):
        goal, b = self.decide("average", gun_off=40.0)
        self.assertTrue(b.last_flags["hit"])


class DemonEngageOnSightTests(unittest.TestCase):
    """(Custom) the owner's Rasu reports, Nov 7 (logs/bug_reports/reach_forge_halo_20261107-191109): a Demon fights a
    man in view within DEMON_ENGAGE_R over its errands without waiting to be shot (Bot.shoot_back)."""

    @classmethod
    def setUpClass(cls):
        from brain.maps import load_map
        cls.map = load_map("reach_cex_headlong")

    def lift(self, tier="demon", foe_d=22.0, scores=None, avoid=False, mode="slayer", hurt=False, mission=()):
        t = ShootBackTests()
        t.map = self.map
        b, me, snap = t.scene(tier, gun_off=40.0, foe_d=foe_d, aiming=False, hurt=hurt)
        snap.mode = mode
        b.mission_keys = tuple(mission)
        sc = dict(scores or {("item", Vec(1, 2, 3)): 2.4, ("fight", 1): 1.87})
        ok = b.shoot_back(me, snap, sc, [1], hurt, None, avoid)
        return ok, sc

    def test_a_gun_or_a_hunt_stays_the_goal_it_fights_on_the_way(self):
        ok, sc = self.lift()
        self.assertFalse(ok)
        self.assertEqual(sc[("fight", 1)], 1.87)
        hunt = ("hunt", Vec(5, 5, 5))
        self.assertFalse(self.lift(scores={hunt: 2.3, ("fight", 1): 1.87}, mission=[hunt])[0])

    def test_demon_fights_the_man_in_view_over_a_seat(self):
        ok, sc = self.lift(scores={("vehicle", 77): 2.2, ("fight", 1): 1.87})
        self.assertTrue(ok)
        self.assertAlmostEqual(sc[("fight", 1)], 2.6)

    def test_only_within_range_and_only_demon_unshot(self):
        seat = {("vehicle", 77): 2.2, ("fight", 1): 1.87}
        self.assertFalse(self.lift(foe_d=35.0, scores=seat)[0])
        self.assertFalse(self.lift(tier="top", scores=seat)[0])          # Legendary keeps answering only when shot

    def test_avoid_posture_and_regroup_kept(self):
        self.assertFalse(self.lift(avoid=True, scores={("vehicle", 77): 2.2, ("fight", 1): 1.87})[0])

    def test_objective_only_in_slayer(self):
        obj = ("objective", Vec(5, 5, 5))
        self.assertFalse(self.lift(scores={obj: 2.0, ("fight", 1): 1.87}, mode="ctf")[0])
        self.assertTrue(self.lift(scores={obj: 2.0, ("fight", 1): 1.87})[0])

    def test_a_radar_hunt_is_not_an_errand(self):
        self.assertFalse(self.lift(scores={("hunt", Vec(5, 5, 5)): 3.2, ("fight", 1): 1.87})[0])


class FightOnTheWayTests(unittest.TestCase):
    """(Custom) Bot.on_way_target through think: a Demon walking to a gun with a man in view shoots him while it walks
    on to the gun (the patrol's way: fight's aim and trigger, the walk turned toward the goal)."""

    def scene(self, tier="demon", gun=Vec(0, -20, 0), foe=Vec(15, 0, 0), kind="item", mode="slayer"):
        import math as m
        from test_demon_fire import Cover

        class Flat(Cover):                       # (an open floor for the walk too)
            def ground_ok(self, *args, **kw):
                return True

            def los(self, *args, **kw):
                return True
        cover = Flat((True, True), (True, True), None)
        rng = random.Random(1)
        bot = __import__("brain.bot", fromlist=["Bot"]).Bot(0, 0, make_profile(tier, "rusher", rng), {"name": "reach_test"}, rng)
        bot._terrain = cover
        bot.goal, bot.next_decide = (kind, gun), 99.0
        bot.per.recognized.add(1)
        for name in ("no_wall_jump", "edge_guard", "obstacle_guard", "unstuck"):
            setattr(bot, name, lambda *args: None)
        bot.detour = lambda now, me, kind, p: p          # (no map zones or floor grid in this lane)
        bot.no_floor_at = lambda *args, **kw: False
        me = PlayerState(0, 0, "bot", Vec(), weapon="dmr", weapons=["dmr"], mag=[15], ammo=[45])
        target = PlayerState(1, 1, "enemy", foe)
        acts = [bot.think(1.0 + i / 30, 1 / 30, Snapshot(1.0 + i / 30, [me, target], mode=mode), cover.sees,
                          lambda a, b, **kw: b, []) for i in range(12)]
        heading = lambda a: a.yaw + m.atan2(a.strafe, a.forward)
        return bot, me, target, acts, heading

    def test_demon_shoots_the_man_while_it_walks_to_the_gun(self):
        import math as m
        from brain.core import wrap
        bot, me, target, acts, heading = self.scene()
        self.assertEqual(bot.goal[0], "item")
        self.assertTrue(any(a.fire for a in acts))
        last = acts[-1]
        self.assertLess(abs(wrap(last.yaw - angles_to(eye(me), target.pos)[0])), 0.3)     # the gun on him
        self.assertGreater(m.hypot(last.forward, last.strafe), 0.3)                            # still walking
        self.assertLess(abs(wrap(heading(last) - (-m.pi / 2))), 0.6)                           # toward the gun (-y)

    def test_far_man_and_legendary_walk_on_without_shooting(self):
        self.assertFalse(any(a.fire for a in self.scene(foe=Vec(40, 0, 0))[3]))
        self.assertFalse(any(a.fire for a in self.scene(tier="top")[3]))

    def test_objective_run_outside_slayer_shoots_on_the_way(self):
        import math as m
        from brain.core import wrap
        for mode in ("ctf", "invasion", "koth"):
            with self.subTest(mode=mode):
                bot, me, target, acts, heading = self.scene(kind="objective", mode=mode)
                self.assertTrue(any(a.fire for a in acts))
                self.assertLess(abs(wrap(heading(acts[-1]) - (-m.pi / 2))), 0.6)      # still running the objective
                self.assertEqual(bot.goal[0], "objective")

    def test_objective_last_steps_slayer_and_race_unchanged(self):
        self.assertFalse(any(a.fire for a in self.scene(kind="objective", mode="ctf", gun=Vec(0, -2.0, 0))[3]))
        self.assertFalse(any(a.fire for a in self.scene(kind="objective", mode="slayer")[3]))
        self.assertFalse(any(a.fire for a in self.scene(kind="objective", mode="race")[3]))
        self.assertFalse(any(a.fire for a in self.scene(kind="objective", mode="ctf", tier="top")[3]))

    def test_last_steps_onto_the_gun_are_the_pickup(self):
        bot, me, target, acts, _ = self.scene(gun=Vec(0, -1.0, 0))
        self.assertFalse(any(a.fire for a in acts))


class EmptyMagSwitchTests(unittest.TestCase):
    """Bot.choose_weapon: the DMR's magazine out mid-fight goes to the rifle only where the rifle fires."""

    @classmethod
    def setUpClass(cls):
        from brain.maps import load_map
        cls.map = load_map("reach_cex_headlong")

    def choose(self, d, tier="demon"):
        from brain.bot import Bot, Belief
        b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), self.map, random.Random(5))
        me = PlayerState(0, 0, "bot", GUN, weapon="dmr", weapons=["dmr", "assault_rifle"], ammo=[45, 160], mag=[0, 32])
        snap = Snapshot(100.0, [me], mode="slayer")
        b.notes = []                                  # (think starts each tick's notes)
        b.per.beliefs[1] = Belief(Vec(GUN.x + d, GUN.y, GUN.z), Vec(), 100.0, True, "eyes")
        return b.choose_weapon(100.0, me, "fight", 1, snap)

    def test_rifle_within_its_reach_still_beats_the_reload(self):
        self.assertEqual(self.choose(8.0), 1)

    def test_past_the_rifle_reach_it_reloads(self):
        from brain.bot import OUT_OF_REACH, reach
        self.assertLess(reach("assault_rifle", "reach") * OUT_OF_REACH, 13.0)
        self.assertNotEqual(self.choose(13.0), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
