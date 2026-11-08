"""Reach Demon direct fire: one tick of lead on its aim and its final DMR shot, and the dry-part switch (custom, Nov 7).
Legendary's protected head point and Halo 4 keep their own paths."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import Bot, DEMON_LEAD_S, PART_DRY_S, lead_ray   # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to, eye  # noqa: E402
from brain.profiles import make_profile                           # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_demon_fire import Cover                                 # noqa: E402


def scene(tier="demon", weapon="dmr", game="reach"):
    cover = Cover((True, True), (True, True), (True, True))
    rng = random.Random(1)
    bot = Bot(0, 0, make_profile(tier, "rusher", rng), {"name": game + "_test"}, rng)
    bot._terrain = cover
    bot.goal, bot.next_decide = ("fight", 1), 99.0
    bot.per.recognized.add(1)
    for name in ("no_wall_jump", "edge_guard", "obstacle_guard", "unstuck"):
        setattr(bot, name, lambda *args: None)
    me = PlayerState(0, 0, "bot", Vec(), vel=Vec(1.0, 0.0, 0.0), weapon=weapon, weapons=[weapon], mag=[15], ammo=[45])
    him = PlayerState(1, 1, "enemy", Vec(10, 0, 0), vel=Vec(0.0, 2.5, 0.0), head_pos=Vec(10, 0.08, 0.52))
    return bot, me, him, cover


def step(bot, me, him, cover, now):
    return bot.think(now, 1 / 30, Snapshot(now, [me, him]), cover.sees, lambda a, b, **kw: b, [])


class ReachDemonLeadTests(unittest.TestCase):
    def test_final_dmr_shot_is_led_one_tick(self):
        bot, me, him, cover = scene()
        act = step(bot, me, him, cover, 1.0)
        self.assertTrue(act.fire)
        self.assertEqual(bot.fx["part"], "head")
        o, p = eye(me) + me.vel * DEMON_LEAD_S, him.head_pos + him.vel * DEMON_LEAD_S
        want = angles_to(o, p)
        self.assertAlmostEqual(act.yaw, want[0])
        self.assertAlmostEqual(act.pitch, want[1])
        self.assertNotAlmostEqual(act.yaw, angles_to(eye(me), him.head_pos)[0], places=4)

    def test_lead_ignores_a_teleport_read(self):
        bot, me, him, cover = scene()
        him.vel = Vec(0.0, 400.0, 0.0)
        o, p = lead_ray(me, him, (eye(me), him.head_pos))
        self.assertEqual(p, him.head_pos)
        self.assertAlmostEqual(o.x, me.vel.x * DEMON_LEAD_S)

    def test_legendary_keeps_its_unled_protected_head(self):
        # the final shot step alone (think after a stubbed plan): Legendary's head point unled, Demon's led
        for tier, led in (("top", False), ("demon", True)):
            bot, me, him, cover = scene(tier)

            def plan(*args, bot=bot):
                bot.shot_part = (1, True)
                return Action(fire=True, yaw=0.0)
            bot.plan = plan
            act = bot.think(1.0, 1 / 30, Snapshot(1.0, [me, him]), cover.sees, None, [])
            ray = (eye(me), him.head_pos)
            want = angles_to(*(lead_ray(me, him, ray) if led else ray))
            self.assertAlmostEqual(act.yaw, want[0], msg=tier)
            self.assertAlmostEqual(act.pitch, want[1], msg=tier)


class ReachDemonDryPartTests(unittest.TestCase):
    def run_fight(self, seconds, hit_each_press=False):
        bot, me, him, cover = scene()
        me.vel = him.vel = Vec()
        parts, notes, presses = [], [], 0
        n = int(seconds * 30)
        for k in range(n):
            now = 1.0 + k / 30
            act = step(bot, me, him, cover, now)
            if act.fire:
                presses += 1
                if hit_each_press:
                    him.shield = max(0.05, him.shield - 0.2)
            parts.append((bot.fx or {}).get("part"))
            notes += bot.notes
        return parts, notes, presses

    def test_head_gone_dry_gives_way_to_the_chest(self):
        parts, notes, presses = self.run_fight(PART_DRY_S + 1.0)
        self.assertEqual(parts[0], "head")
        self.assertIn("part dry: the chest", notes)
        k = parts.index("chest")
        self.assertGreaterEqual(k / 30, PART_DRY_S - 0.05)
        self.assertGreaterEqual(presses, 3)

    def test_landing_rounds_keep_the_head(self):
        parts, notes, _ = self.run_fight(PART_DRY_S + 1.0, hit_each_press=True)
        self.assertNotIn("chest", parts)
        self.assertNotIn("part dry: the chest", notes)


if __name__ == "__main__":
    unittest.main()
