"""(custom, Nov 24) Upstream 0.3.0's brain notes as ported into Project Noble (logs/upstream_0.3.0_answers.md): each
class is one note, its build stamp in the docstring."""
import random
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain import bot as botmod                                 # noqa: E402
from brain.bot import Bot                                       # noqa: E402
from brain.core import Action, PlayerState, Vec                 # noqa: E402
from brain.profiles import make_profile                        # noqa: E402


def make_bot(tier="strong", mapname="reach_t", style="rusher", bid=0, team=0):
    return Bot(bid, team, make_profile(tier, style, random.Random(1)), {"name": mapname, "items": []},
               random.Random(2))


class TakeTapTests(unittest.TestCase):
    """#6 (build 20261112-2117): Halo 2 takes the ball on a press of Use, so Bot.take taps it there."""

    def take(self, mapname, now):
        b = make_bot(mapname=mapname)
        b.now = now
        me = PlayerState(id=0, team=0, name="b", pos=Vec(0, 0, 0))
        act = Action()
        b.take(me, act, Vec(1, 0, 0))
        return act.action

    def test_halo_2_taps(self):
        beat = botmod.TAKE_TAP_S
        self.assertTrue(self.take("h2_t", 0.0))
        self.assertFalse(self.take("h2_t", beat * 0.75))
        self.assertTrue(self.take("h2_t", beat * 1.1))

    def test_every_other_game_holds(self):
        for m in ("reach_t", "h3_t", "h4_t", "h2a_t", "ce_map"):
            for now in (0.0, botmod.TAKE_TAP_S * 0.75):
                self.assertTrue(self.take(m, now), (m, now))

    def test_no_static_calls_left(self):
        src = Path(botmod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("Bot.take(", src)


class _NoField:
    hjumps = hroutes = None

    def field_from(self, *a):
        raise RuntimeError("no level data in this test")


class HeadwayTests(unittest.TestCase):
    """#41 (build 20261118-2355): a bot's weapon patience restarts each life (no headway call for over a second)."""

    def walk(self, times, tier="strong"):
        b = make_bot(tier=tier)
        b._terrain = _NoField()
        me = PlayerState(id=0, team=0, name="b", pos=Vec(0, 0, 0))
        goal = ("item", Vec(20, 0, 0))
        for t in times:
            b.headway(t, me, goal)
        return b, b._goal_key(goal)

    def test_six_seconds_with_no_headway_still_bans(self):
        b, key = self.walk([i * 0.1 for i in range(80)])
        self.assertIn(key, getattr(b, "goal_ban", {}))

    def test_a_gap_starts_the_clock_again(self):
        # 5 s walking, dead 5 s (no call), then 3 s more: 8 s of calls, never 6 s since the respawn
        times = [i * 0.1 for i in range(50)] + [10.0 + i * 0.1 for i in range(30)]
        b, key = self.walk(times)
        self.assertNotIn(key, getattr(b, "goal_ban", {}))

    def test_easy_keeps_its_shorter_patience(self):
        times = [i * 0.1 for i in range(int(botmod.EASY_HEADWAY_S * 10) + 6)]
        b, key = self.walk(times, tier="novice")
        self.assertIn(key, getattr(b, "goal_ban", {}))


class _Wall:
    """A wall right along yaw 1.0 (the way the bot walks), room everywhere else."""

    def clearance(self, pos, yaw, r):
        return 0.3 if abs(yaw - 1.0) < 0.2 else 3.0


class ObjectiveReachTests(unittest.TestCase):
    """#11, the walking part (build 20261114-0323): an objective or gun within OBJ_REACH with a clear line is walked
    at straight, not stepped round the wall behind it."""

    def step(self, goal):
        b = make_bot()
        b._terrain = _Wall()
        b.goal = goal
        me = PlayerState(id=0, team=0, name="b", pos=Vec(0, 0, 0))
        act = Action(forward=1.0, yaw=1.0)
        b.redirect(0.0, me, act)
        return act

    def test_flag_in_reach_straight_at_it(self):
        for kind in ("objective", "item"):
            act = self.step((kind, Vec(2.0, 0, 0)))
            self.assertAlmostEqual(act.forward, botmod.math.cos(-1.0), 3, kind)
            self.assertAlmostEqual(act.strafe, botmod.math.sin(-1.0), 3, kind)

    def test_farther_or_another_floor_steps_round_as_before(self):
        for goal in (("objective", Vec(5.0, 0, 0)), ("objective", Vec(2.0, 0, 2.0)), ("hunt", Vec(2.0, 0, 0))):
            act = self.step(goal)
            self.assertAlmostEqual(act.forward, botmod.math.cos(0.52), 3, goal)
            self.assertAlmostEqual(act.strafe, botmod.math.sin(0.52), 3, goal)


class _Belief:
    def __init__(self, pos):
        self.pos, self.t = pos, 0.0


class _Eyes:
    """A Perception stand-in: the men in view and when they were seen."""

    def __init__(self, men, now=10.0):
        self.beliefs = {k: _Belief(p) for k, p in men.items()}
        self.last_seen = {k: now for k in men}

    def visible_enemies(self):
        return list(self.beliefs)


def tier_bot(tier):
    if tier == "scaling":
        from dataclasses import replace
        b = make_bot(tier="top")
        b.p = replace(b.p, extra={"scaling": 1})
        return b
    return make_bot(tier=tier)


class WalkFireTests(unittest.TestCase):
    """#2 (build 20261112-1507): bots shoot the man in front of them on their way, Easy to Legendary only."""

    def target(self, tier, man=Vec(6.0, 0.5, 0.0), **me_kw):
        b = tier_bot(tier)
        b.per = _Eyes({7: man})
        me = PlayerState(id=0, team=0, name="b", pos=Vec(0, 0, 0), weapon="dmr", weapons=["dmr"], ammo=[30], **me_kw)
        act = Action(forward=1.0, yaw=0.0)
        return b.walk_target(10.0, me, act)

    def test_easy_to_legendary_shoot_the_man_in_front(self):
        for tier in ("novice", "average", "strong", "top", "blind", "tactician", "scaling"):
            self.assertEqual(self.target(tier), 7, tier)

    def test_demon_noble_mythic_keep_only_our_rule(self):
        for tier in ("demon", "noble", "mythic"):
            self.assertIsNone(self.target(tier), tier)

    def test_behind_it_carrying_or_seated_no(self):
        self.assertIsNone(self.target("top", man=Vec(-6.0, 0.0, 0.0)))     # behind: past WALK_FIRE_CONE
        self.assertIsNone(self.target("top", has_flag=True))
        self.assertIsNone(self.target("top", vehicle=3))

    def test_walk_kept_while_firing(self):
        b = tier_bot("strong")
        b.per = _Eyes({7: Vec(6.0, 2.0, 0.0)})
        seen = {}
        def fight(now, dt, me, snap, tid, act, nav):
            seen["tid"] = tid
            act.yaw, act.forward, act.strafe, act.fire = 0.3, 0.0, 1.0, True
        b.fight = fight
        me = PlayerState(id=0, team=0, name="b", pos=Vec(0, 0, 0), weapon="dmr", weapons=["dmr"], ammo=[30])
        act = Action(forward=1.0, yaw=0.0)
        self.assertTrue(b.walk_fire(10.0, 0.03, me, None, act, None))
        self.assertEqual(seen["tid"], 7)
        # still walking along +x over the ground, now facing 0.3 rad off it
        gx = botmod.math.cos(act.yaw) * act.forward - botmod.math.sin(act.yaw) * act.strafe
        gy = botmod.math.sin(act.yaw) * act.forward + botmod.math.cos(act.yaw) * act.strafe
        self.assertAlmostEqual(gx, 1.0, 6)
        self.assertAlmostEqual(gy, 0.0, 6)
        self.assertTrue(act.fire)


class _Lore:
    def __init__(self):
        self.jumps = []

    def add_jump(self, key, made):
        self.jumps.append((key, made))


class JumpJudgeTests(unittest.TestCase):
    """#15 (build 20261114-1215): a landing judged by the nearest approach, results queued for the map's LiDAR link
    (HumanWatch.bot_jump) and our layout memory (lore.add_jump) both."""

    def jump(self, path, tier="top"):
        b = make_bot(tier=tier)
        lore = _Lore()
        b.lore = lambda: lore
        land = Vec(6.0, 4.0, 2.0)
        b.jump_try = ((3.0, 4.0), land, 3.0)
        me = PlayerState(id=0, team=0, name="b", pos=Vec(3.0, 4.0, 2.0))
        for t, pos in path:
            b.now = t
            me.pos = pos
            b.judge_jump(me)
        return b, lore

    def test_landed_and_ran_on_is_made(self):
        # down 0.2 u from the landing at 3.8 s, 3 u past it when judged at 4.6 s: made (it was "short" before)
        b, lore = self.jump([(3.4, Vec(5.0, 4.0, 3.0)), (3.8, Vec(6.2, 4.0, 2.0)), (4.6, Vec(9.0, 4.0, 2.0))])
        self.assertIsNone(b.jump_try)
        self.assertEqual(b.jump_results, [((3.0, 4.0), (6.0, 4.0, 2.0), True)])
        self.assertEqual(lore.jumps, [((3.0, 4.0), True)])
        self.assertFalse(getattr(b, "jump_fails", {}))

    def test_fell_under_it_is_short(self):
        b, lore = self.jump([(3.8, Vec(6.0, 4.0, -1.0)), (4.6, Vec(6.0, 4.0, -1.0))])
        self.assertEqual(b.jump_results, [((3.0, 4.0), (6.0, 4.0, 2.0), False)])
        self.assertEqual(lore.jumps, [((3.0, 4.0), False)])
        self.assertEqual(b.jump_fails[(3.0, 4.0)][0], 1)

    def test_lidar_link_counts_and_drops_after_three(self):
        import threading
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import lidar
        from brain.maps import usable_links

        class Rec:
            lock = threading.Lock()
            links = [dict(kind="jump", take_off=[3.0, 4.0, 2.0], land=[6.0, 4.0, 2.0], human=0, bot_ok=2, bot_fail=0),
                     dict(kind="jump", take_off=[3.0, 4.0, 2.0], land=[6.0, 4.0, 2.0], human=1, bot_ok=0, bot_fail=0)]
        w = lidar.HumanWatch("none", rec=Rec())
        self.assertIs(w.bot_jump((3.0, 4.0), (6.0, 4.0, 2.0), True), Rec.links[0])
        self.assertEqual(Rec.links[0]["bot_ok"], 3)
        Rec.links[0]["bot_ok"] = 0
        for _ in range(3):
            w.bot_jump((3.05, 4.0), (6.0, 4.5, 2.0), False)
        self.assertEqual(Rec.links[0]["bot_fail"], 3)
        self.assertEqual(Rec.links[1]["bot_fail"], 0, "a person's jump is never counted")
        self.assertNotIn(Rec.links[0], usable_links(Rec.links))
        self.assertIsNone(w.bot_jump((20.0, 4.0), (6.0, 4.0, 2.0), False), "no link at another take-off")


if __name__ == "__main__":
    unittest.main()
