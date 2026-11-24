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


class WedgedDudTests(unittest.TestCase):
    """#21 (build 20261114-1900): a wedged vehicle is left and nobody gets back in for vehicles.DUD_FOR s; (custom) a
    vehicle a Wheelman keeps is never marked."""

    def wedged(self, style="rusher", moved=True, now=100.0):
        from types import SimpleNamespace
        from brain.bot import Order
        from brain.core import Snapshot
        from brain import vehicles
        mapdata = dict(name="reach_test", flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={"mid": Vec(80, 0, 0)})
        b = Bot(0, 0, make_profile("strong", style, random.Random(3)), mapdata, random.Random(2))
        b.order = Order("mid", Vec(80, 0, 0))
        b.seat = "driver"
        b.drive_to = Vec(80, 0, 0)
        b._terrain = SimpleNamespace(vnav=lambda start, goal, **k: goal)
        b.notes = []
        me = PlayerState(0, 0, "driver", Vec(), vehicle=10)
        v = dict(handle=10, kind="warthog", pos=(0, 0, 0), occupied=True, team=0, riders=1, fwd=(1, 0, 0))
        snap = Snapshot(100, [me], vehicles=[v], mode="slayer")
        b.seat_at, b.seat_moved = (10, Vec(-5, 0, 0) if moved else Vec()), moved
        b.drive_pos, b.drive_since = Vec(), now - 10.0          # 10 s without moving 1.5 u: stuck
        b.reversed_n, b.wedge_spot = 2, Vec()                   # both back-offs done here
        b.wheel_wedged = botmod.WHEEL_WEDGED_MAX                # (a Wheelman's other ways done too)
        b.seat_since = now - 20.0
        b.drive(now, 1 / 30, me, snap, Action(), lambda a, c, **k: c)
        return b.duds().get(10), vehicles.DUD_FOR, b.notes

    def test_wedged_past_its_back_offs_is_a_dud_for_everyone(self):
        until, dud_for, notes = self.wedged()
        self.assertEqual(until, 100.0 + dud_for, notes)

    def test_a_seat_that_never_moved_is_no_dud(self):
        until, _, notes = self.wedged(moved=False)
        self.assertIsNone(until, notes)

    def test_a_wheelmans_vehicle_is_never_marked(self):
        until, _, notes = self.wedged(style="wheelman")
        self.assertIsNone(until, notes)


class GunnerStaysTests(unittest.TestCase):
    """#32a (build 20261114-2230): a gunner stays in while somebody is at the wheel (AT_WHEEL), parked or not; the
    rest of our rider exits as before."""

    def setUp(self):
        botmod.AT_WHEEL.clear()

    tearDown = setUp

    def ride(self, stamp=True, riders=2, now=100.0):
        from types import SimpleNamespace
        from brain.bot import Order
        from brain.core import Snapshot
        mapdata = dict(name="reach_test", flags={0: Vec(100, 0, 0), 1: Vec(200, 0, 0)}, points={})
        b = Bot(0, 0, make_profile("strong", "rusher", random.Random(3)), mapdata, random.Random(2))
        b.order = Order("free")
        b.seat, b.seat_for = "gunner", 10
        b._terrain = SimpleNamespace(height_over=lambda *a: 0.0)
        b.notes = []
        me = PlayerState(0, 0, "gun", Vec(), vehicle=10, gunner_seat=True)
        driver = PlayerState(5, 0, "wheel", Vec(), vehicle=10)
        v = dict(handle=10, kind="warthog", pos=(0, 0, 0), occupied=True, team=0, riders=riders, fwd=(1, 0, 0))
        snap = Snapshot(100, [me, driver], vehicles=[v], mode="slayer")
        b.still_at, b.still_since, b.seat_since = Vec(), now - 10.0, now - 10.0     # parked 10 s
        if stamp:
            botmod.AT_WHEEL[10] = (5, now - 0.2)
        act = Action()
        b.drive(now, 1 / 30, me, snap, act, lambda a, c, **k: c)
        return act.action, b

    def test_at_wheel(self):
        from brain.core import Snapshot
        me = PlayerState(0, 0, "gun", Vec(), vehicle=10)
        drv = PlayerState(5, 0, "wheel", Vec(), vehicle=10)
        snap = Snapshot(100, [me, drv])
        self.assertFalse(Bot.at_wheel(100.0, me, snap))
        botmod.AT_WHEEL[10] = (5, 99.5)
        self.assertTrue(Bot.at_wheel(100.0, me, snap))
        self.assertFalse(Bot.at_wheel(101.0, me, snap), "a stale stamp")
        drv.vehicle = -1
        self.assertFalse(Bot.at_wheel(100.0, me, snap), "the driver got out")

    def test_parked_with_a_driver_the_gunner_stays(self):
        out, b = self.ride(stamp=True)
        self.assertFalse(out, b.notes)

    def test_parked_with_nobody_at_the_wheel_out_as_before(self):
        out, b = self.ride(stamp=False)
        self.assertTrue(out, b.notes)
        self.assertIn(10, getattr(b, "parked_ban", {}), "our parked_ban as before")

    def test_alone_in_it_out_as_before(self):
        out, b = self.ride(stamp=True, riders=1)
        self.assertTrue(out, b.notes)

    def test_the_stamp_is_held_back_in_a_threaded_pass(self):
        from brain.threads import Pass
        ps = Pass(1)
        try:
            got = ps.run([(lambda: botmod.AT_WHEEL.__setitem__(10, (5, 1.0)), ()),
                          (lambda: 10 in botmod.AT_WHEEL, ())])
        finally:
            ps.close()
        self.assertEqual(got[1], False, "another bot's stamp only after the pass")
        self.assertEqual(botmod.AT_WHEEL.get(10), (5, 1.0))


if __name__ == "__main__":
    unittest.main()
