"""Halo 4 Demon (custom, Nov 7): real-height sight, body-then-head part choice, the led view lock and the tapped
trigger. Reach, Halo 4 Legendary and Scaling keep their own paths."""
import math
import random
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import profiles                                          # noqa: E402
from brain.bot import (Belief, Bot, H4_CHEST_DROP, H4_LEAD_S, h4_chest, h4_demon_fire, h4_ray,   # noqa: E402
                       h4_wants_head)
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to  # noqa: E402


class OpenTerrain:
    """Every live ray open unless listed in blocked (point pairs, rounded)."""
    def __init__(s, blocked=()):
        s.blocked_rays, s.calls = set(blocked), []

    def point_los(s, a, b, mode=None):
        s.calls.append((a, b, mode))
        return (round(b.z, 3)) not in s.blocked_rays

    def target_parts(s, *a, **kw):
        return True, True        # the generic pair 0.38 u high: open over the cover

    def sees(s, a, b):
        return True

    def los(s, a, b, mode=None):
        return True


def scene(tier="demon", game_map="h4_test", weapon="dmr", shield=1.0, extra=None):
    prof = profiles.make_profile(tier, "rusher", random.Random(3))
    if extra is not None:
        prof = replace(prof, extra=extra)
    bot = Bot(0, 0, prof, {"name": game_map}, random.Random(5))
    me = PlayerState(0, 0, "bot", Vec(0, 0, 0.38), weapon=weapon, weapons=[weapon],
                     view_pos=Vec(0, 0, 0.6), head_pos=Vec(0, 0, 0.63))
    him = PlayerState(1, 1, "him", Vec(12, 0, 0.38), vel=Vec(0, 2.0, 0), shield=shield,
                      view_pos=Vec(12, 0, 0.6), head_pos=Vec(12.02, 0.0, 0.63))
    return bot, me, him, Snapshot(0, [me, him])


def ready_fight(bot, me, him, now, terrain, parts=(True, True)):
    bot.T = lambda: terrain
    bot._terrain = terrain
    bot.per.beliefs[1] = Belief(him.pos, him.vel, now, True, "eyes")
    bot.per.recognized.add(1)
    bot.per.last_seen[1] = now
    bot.per.clear_at[1] = now
    bot.per.target_parts = {1: parts}
    bot.notes = []
    bot.engaged_since = now - 1.0
    bot.strafing, bot.plant, bot.nade_open, bot.press_fight = True, False, False, False
    bot.grenade_ready_at = now + 99.0


class H4DemonGateTests(unittest.TestCase):
    def test_only_halo4_demon_on_foot_with_a_live_pair(self):
        bot, me, him, _ = scene()
        self.assertTrue(h4_demon_fire(bot.p, "h4", me, him))
        self.assertFalse(h4_demon_fire(bot.p, "reach", me, him))
        top, _, _, _ = scene("top")
        self.assertFalse(h4_demon_fire(top.p, "h4", me, him))
        scaling, _, _, _ = scene("top", extra={"loose_follow": 0.0, "loose_early": 0.0})
        self.assertFalse(h4_demon_fire(scaling.p, "h4", me, him))
        for change in (dict(weapon="rockets"), dict(vehicle=7), dict(view_pos=None)):
            _, me2, him2, _ = scene()
            for k, v in change.items():
                setattr(me2, k, v)
            self.assertFalse(h4_demon_fire(bot.p, "h4", me2, him2), change)
        _, me3, him3, _ = scene()
        him3.head_pos = None
        self.assertFalse(h4_demon_fire(bot.p, "h4", me3, him3))

    def test_body_while_shielded_head_to_finish(self):
        _, me, him, _ = scene()
        self.assertFalse(h4_wants_head(me, him))
        him.shield = 0.0
        self.assertTrue(h4_wants_head(me, him))
        me.weapon = "sniper"
        him.shield = 1.0
        self.assertTrue(h4_wants_head(me, him))
        self.assertAlmostEqual(h4_chest(him).z, him.head_pos.z - H4_CHEST_DROP)
        self.assertEqual((h4_chest(him).x, h4_chest(him).y), (him.pos.x, him.pos.y))

    def test_lead_moves_both_ends_and_ignores_teleports(self):
        _, me, him, _ = scene()
        me.vel = Vec(1.0, 0, 0)
        o, p = h4_ray(me, him, True, lead=True)
        self.assertAlmostEqual(o.x, me.view_pos.x + H4_LEAD_S)
        self.assertAlmostEqual(p.y, him.head_pos.y + 2.0 * H4_LEAD_S)
        him.vel = Vec(300.0, 0, 0)
        _, p = h4_ray(me, him, True, lead=True)
        self.assertEqual(p, him.head_pos)


class H4DemonSightTests(unittest.TestCase):
    def test_no_phantom_sight_over_cover(self):
        """The generic pair is open over the wall; the real chest and head lines are not: not seen."""
        bot, me, him, snap = scene()
        bot.game = "h4"
        terrain = OpenTerrain(blocked={round(h4_chest(him).z, 3), round(him.head_pos.z, 3)})
        for t in (0.0, 0.5):
            bot.per.update(t, me, snap, terrain.sees, [], game="h4")
        self.assertEqual(bot.per.target_parts[1], (False, False))
        self.assertNotIn(1, bot.per.visible_enemies())

    def test_real_chest_line_sees_him(self):
        bot, me, him, snap = scene()
        terrain = OpenTerrain(blocked={round(him.head_pos.z, 3)})
        for t in (0.0, 0.5):
            bot.per.update(t, me, snap, terrain.sees, [], game="h4")
        self.assertEqual(bot.per.target_parts[1], (True, False))
        self.assertIn(1, bot.per.visible_enemies())
        self.assertIn((me.view_pos, h4_chest(him), "see"), terrain.calls)

    def test_legendary_keeps_the_generic_chest(self):
        bot, me, him, snap = scene("top")
        terrain = OpenTerrain(blocked={round(h4_chest(him).z, 3)})
        bot.per.update(0.0, me, snap, terrain.sees, [], game="h4")
        self.assertEqual(bot.per.target_parts[1], (True, True))


class H4DemonFightTests(unittest.TestCase):
    def fight_ticks(self, n=6, shield=1.0, weapon="dmr", blocked=(), d=12.0):
        bot, me, him, snap = scene(weapon=weapon, shield=shield)
        him.pos = Vec(d, 0, 0.38)
        him.head_pos = Vec(d + 0.02, 0, 0.63)
        him.view_pos = Vec(d, 0, 0.6)
        terrain = OpenTerrain(blocked)
        out = []
        dt = 1 / 30
        for k in range(n):
            now = 10.0 + k * dt
            ready_fight(bot, me, him, now, terrain)
            act = Action(yaw=me.yaw, pitch=me.pitch)
            bot.shot_part, bot.h4_lock, bot.fx = None, None, None
            bot.fight(now, dt, me, snap, 1, act, lambda *a, **kw: None)
            bot.fire_gate(now, me, act, snap)
            bot.h4_pressed = bool(act.fire)
            out.append((act, bot.shot_part, bot.h4_lock, dict(bot.fx or {})))
        return out, bot, me, him, snap

    def test_tapped_every_other_tick_on_the_body(self):
        out, *_ = self.fight_ticks()
        fires = [a.fire for a, *_ in out]
        self.assertEqual(fires, [True, False, True, False, True, False])
        self.assertTrue(all(part == (1, False) for _, part, _, _ in out))
        self.assertTrue(all(lock == (1, False) for _, _, lock, _ in out))
        self.assertEqual(out[0][3].get("part"), "chest")

    def test_head_once_the_shield_is_down(self):
        out, *_ = self.fight_ticks(shield=0.0)
        self.assertTrue(all(part == (1, True) for _, part, _, _ in out))
        self.assertTrue(out[0][0].fire)

    def test_covered_body_takes_the_head(self):
        _, _, _, him, _ = self.fight_ticks(n=1)
        out, *_ = self.fight_ticks(blocked={round(h4_chest(him).z, 3)})
        self.assertTrue(all(part == (1, True) for _, part, _, _ in out))
        self.assertTrue(out[0][0].fire)

    def test_no_line_no_shot_no_lock(self):
        _, _, _, him, _ = self.fight_ticks(n=1)
        out, *_ = self.fight_ticks(blocked={round(h4_chest(him).z, 3), round(him.head_pos.z, 3)})
        self.assertFalse(any(a.fire for a, *_ in out))
        self.assertTrue(all(lock is None for _, _, lock, _ in out))

    def test_automatic_held_on_the_body(self):
        out, *_ = self.fight_ticks(weapon="storm_rifle", shield=0.0, d=8.0)
        self.assertTrue(all(a.fire for a, *_ in out))
        self.assertTrue(all(part == (1, False) for _, part, _, _ in out))

    def test_paced_past_the_tap_range(self):
        out, *_ = self.fight_ticks(n=8, d=40.0)
        self.assertEqual(sum(a.fire for a, *_ in out), 1)


class H4DemonLockTests(unittest.TestCase):
    def think_with(self, lock, act, game_map="h4_test", tier="demon"):
        bot, me, him, snap = scene(tier, game_map)
        me.vel = Vec(0.5, 0.5, 0)
        bot.plan = lambda *a: (setattr(bot, "h4_lock", lock), setattr(bot, "shot_part", lock), act)[2]
        return bot.think(0, 1 / 30, snap, None, None, []), me, him, bot

    def test_view_locked_led_past_the_turn_cap_walk_kept(self):
        act = Action(yaw=math.pi, pitch=0.0, forward=0.4, strafe=0.3)
        got, me, him, bot = self.think_with((1, False), act)
        want = angles_to(*h4_ray(me, him, False, lead=True))
        self.assertAlmostEqual(got.yaw, want[0])
        self.assertAlmostEqual(got.pitch, want[1])
        # the walk still heads where the plan sent it
        self.assertAlmostEqual(math.cos(got.yaw) * got.forward - math.sin(got.yaw) * got.strafe,
                               math.cos(math.pi) * 0.4 - math.sin(math.pi) * 0.3)
        self.assertFalse(bot.h4_pressed)

    def test_grenade_keeps_its_own_aim(self):
        act = Action(yaw=1.0, pitch=0.3, grenade=True)
        got, *_ = self.think_with((1, True), act)
        self.assertNotAlmostEqual(got.yaw, 0.0, places=2)

    def test_reach_demon_and_h4_legendary_have_no_lock(self):
        for game_map, tier in (("reach_test", "demon"), ("h4_test", "top")):
            act = Action(yaw=0.1, pitch=0.05)     # within the turn cap: left exactly as planned
            got, *_ = self.think_with((1, False), act, game_map, tier)
            self.assertEqual((got.yaw, got.pitch), (0.1, 0.05), (game_map, tier))


if __name__ == "__main__":
    unittest.main()
