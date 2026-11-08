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

    def test_demon_fights_the_man_in_view_over_a_gun(self):
        ok, sc = self.lift()
        self.assertTrue(ok)
        self.assertAlmostEqual(sc[("fight", 1)], 2.8)

    def test_only_within_range_and_only_demon_unshot(self):
        self.assertFalse(self.lift(foe_d=35.0)[0])
        self.assertFalse(self.lift(tier="top")[0])          # Legendary keeps answering only when shot

    def test_avoid_posture_and_regroup_kept(self):
        self.assertFalse(self.lift(avoid=True)[0])

    def test_the_gun_it_was_sent_for_close_by_still_wins(self):
        from brain.bot import FETCH_COMMIT_SCORE
        ok, sc = self.lift(scores={("item", GUN): FETCH_COMMIT_SCORE, ("fight", 1): 1.87})
        self.assertFalse(ok)
        self.assertEqual(sc[("fight", 1)], 1.87)

    def test_anti_vehicle_hunt_counts_objective_only_in_slayer(self):
        hunt = ("hunt", Vec(5, 5, 5))
        ok, sc = self.lift(scores={hunt: 2.3, ("fight", 1): 1.87}, mission=[hunt])
        self.assertTrue(ok)
        self.assertAlmostEqual(sc[("fight", 1)], 2.7)
        obj = ("objective", Vec(5, 5, 5))
        self.assertFalse(self.lift(scores={obj: 2.0, ("fight", 1): 1.87}, mode="ctf")[0])
        self.assertTrue(self.lift(scores={obj: 2.0, ("fight", 1): 1.87})[0])

    def test_a_radar_hunt_is_not_an_errand(self):
        self.assertFalse(self.lift(scores={("hunt", Vec(5, 5, 5)): 3.2, ("fight", 1): 1.87})[0])


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
