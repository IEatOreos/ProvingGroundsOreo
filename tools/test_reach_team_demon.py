"""Halo 4 Demon's fight odds and team play for Reach Demon and Mythic, an enemy's difficulty in them, and the peek as he
looks away (custom, Nov 18: Bot.team_demon, enemy_acc, weak, peek_timing; brain/odds.py REACH_GUNS, acc_of).

The owner: "Yea add all of that to reach demons and mythics" (the Halo 4 Demon's team play, the peek timing, knowing
the other bots' difficulty).

    python\\python.exe tools\\test_reach_team_demon.py
"""
import math
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from brain import odds  # noqa: E402
from brain import bot as botmod  # noqa: E402
from brain.bot import Belief, Bot, PEEK_WAIT_S, PEEK_WAIT_SCORE  # noqa: E402
from brain.core import Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402
from test_demon_odds import demon, man, see  # noqa: E402
import test_demon_break_second as tbs  # noqa: E402
import test_demon_no_new_fight as tnn  # noqa: E402


def dmr(b_me):
    b, me = b_me
    me.weapon, me.weapons, me.ammo, me.mag = "dmr", ["dmr"], [45], [15]
    return b, me


class Clean(unittest.TestCase):
    def tearDown(self):
        botmod.BOT_PROFILES.clear()
        botmod.TEAM_FACING.clear()


class GateTests(Clean):
    def test_who_has_the_team_play(self):
        for tier, game_map, want in (("demon", "reach_test", True), ("mythic", "reach_test", True),
                                     ("top", "reach_test", False), ("demon", "h4_test", True),
                                     ("mythic", "h4_test", False), ("strong", "reach_test", False)):
            with self.subTest(tier=tier, game=game_map):
                b = Bot(0, 0, make_profile(tier, "rusher", random.Random(1)), {"name": game_map}, random.Random(2))
                self.assertEqual(b.team_demon(), want)

    def test_halo_4_only_rules_stay_halo_4s(self):
        b = Bot(0, 0, make_profile("demon", "rusher", random.Random(1)), {"name": "reach_test"}, random.Random(2))
        self.assertFalse(b.h4_demon())                       # (the Boltshot swap, the melee range, the power grab)


class ReachOddsTests(Clean):
    def test_reach_guns(self):
        full = man(1, 10.0)
        self.assertAlmostEqual(odds.kill_time("needle_rifle", 10.0, full, game="reach"), 1.3)
        self.assertAlmostEqual(odds.kill_time("needle_rifle", 10.0, full), odds.GUN_DEFAULT[0])   # (Halo 4: not its gun)
        self.assertAlmostEqual(odds.kill_time("dmr", 10.0, full, game="reach"), 1.2)
        self.assertAlmostEqual(odds.kill_time("battle_rifle", 10.0, full), 1.35)                 # Halo 4 unchanged

    def test_an_enemys_difficulty_is_his_pace(self):
        bot_man, person = man(1, 10.0), man(2, 10.0, human=True)
        self.assertAlmostEqual(odds.acc_of(bot_man, make_profile("novice", "rusher", random.Random(1)), "reach"), 0.17)
        self.assertAlmostEqual(odds.acc_of(bot_man, make_profile("demon", "rusher", random.Random(1)), "reach"), 0.52)
        self.assertAlmostEqual(odds.acc_of(person, None, "reach"), odds.ACC[True])
        self.assertAlmostEqual(odds.acc_of(bot_man, make_profile("demon", "rusher", random.Random(1)), "h4"),
                               odds.ACC[False])                 # (Halo 4 as before)
        self.assertLess(odds.own_acc(make_profile("mythic", "rusher", random.Random(1))), odds.DEMON_ACC)

    def test_the_team_posts_who_it_is_and_a_novice_is_less_feared(self):
        b, me = dmr(demon("demon", "reach_test"))
        him = man(1, -12.0, weapon="dmr")
        snap = Snapshot(50.0, [me, him], mode="slayer")
        see(b, him)
        got = {}
        for tier in ("novice", "top"):
            mate = Bot(1, 1, make_profile(tier, "rusher", random.Random(1)), {"name": "reach_test"}, random.Random(2))
            mate.per.visible_enemies = lambda: []
            mate.share_sightings(50.0, him, snap)             # (bot 1 posts its profile: who it is)
            self.assertEqual(botmod.BOT_PROFILES[("reach_test", 1)].tier, tier)
            got[tier] = b.fight_odds(50.0, me, snap, [1])[0]
        self.assertGreater(got["novice"], 2.0 * got["top"])    # (the same man as an Easy bot: far better odds)

    def test_reach_demon_and_mythic_one_shot_do_not_peek_a_full_man(self):
        for tier in ("demon", "mythic"):
            with self.subTest(tier=tier):
                b, me = dmr(demon(tier, "reach_test", shield=0.0, health=0.3, wall=0.5))
                him = man(1, -10.0, human=True, facing_me=False, weapon="dmr")
                snap = Snapshot(50.0, [me, him], mode="slayer")
                see(b, him)
                scores = {("fight", 1): 1.9}
                b.demon_odds_rules(50.0, me, snap, scores, [1])
                self.assertNotIn(("fight", 1), scores)
                self.assertTrue(any(k[0] == "retreat" for k in scores))

    def test_reach_legendary_as_before(self):
        b, me = dmr(demon("top", "reach_test", shield=0.0, health=0.3, wall=0.5))
        him = man(1, -10.0, human=True, facing_me=False, weapon="dmr")
        snap = Snapshot(50.0, [me, him], mode="slayer")
        see(b, him)
        scores = {("fight", 1): 1.9}
        b.demon_odds_rules(50.0, me, snap, scores, [1])
        self.assertEqual(scores, {("fight", 1): 1.9})


class WeakManTests(Clean):
    def test_a_weak_second_man_is_no_reason_to_leave_the_fight(self):
        t = tbs.BreakSecondTests()
        b, me, a, c, snap = t.setup()
        botmod.BOT_PROFILES[("reach_test", c.id)] = make_profile("novice", "rusher", random.Random(1))
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)

    def test_a_dangerous_second_man_still_is(self):
        t = tbs.BreakSecondTests()
        b, me, a, c, snap = t.setup()
        botmod.BOT_PROFILES[("reach_test", c.id)] = make_profile("top", "rusher", random.Random(1))
        self.assertEqual(b.decide(50.0, me, snap)[0], "retreat")

    def test_hurt_it_takes_on_a_weak_man(self):
        t = tnn.NoNewFightTests()
        b, me, foe, snap = t.setup()
        botmod.BOT_PROFILES[("reach_test", foe.id)] = make_profile("novice", "rusher", random.Random(1))
        b.decide(50.0, me, snap)
        self.assertIn(("fight", 1), b.last_scores)
        self.assertIsNone(b.fresh_cover)


class PeekTests(Clean):
    def setup(self, tier="demon", game_map="reach_test", looking=True, novice=False):
        """A Reach Demon at the origin about to hunt man 1, out of its sight 10 u west; a teammate sees him (TEAM_FACING)
        facing it, or facing away."""
        b, me = dmr(demon(tier, game_map))
        him = man(1, -10.0, facing_me=looking, weapon="dmr")
        snap = Snapshot(50.0, [me, him], mode="slayer")
        b.per.beliefs[1] = Belief(him.pos, Vec(), 49.9, False, "team")
        botmod.TEAM_FACING[(game_map, 0)] = {1: (50.0, him.yaw, him.pos)}
        if novice:
            botmod.BOT_PROFILES[(game_map, 1)] = make_profile("novice", "rusher", random.Random(1))
        return b, me, snap

    def peek(self, b, me, snap, t=50.0):
        scores = {("hunt", Vec(-10.0, 0.0, 0.0)): 3.2, ("objective", Vec(5, 5, 0)): 1.0}
        b.peek_timing(t, me, snap, scores, [])
        return scores

    def test_he_is_looking_this_way_it_waits(self):
        b, me, snap = self.setup()
        scores = self.peek(b, me, snap)
        self.assertEqual(scores.get(("retreat", me.pos)), PEEK_WAIT_SCORE)
        self.assertNotIn(("hunt", Vec(-10.0, 0.0, 0.0)), scores)

    def test_he_looks_away_it_goes(self):
        b, me, snap = self.setup(looking=False)
        self.assertIn(("hunt", Vec(-10.0, 0.0, 0.0)), self.peek(b, me, snap))

    def test_it_waits_no_longer_than_peek_wait_s(self):
        b, me, snap = self.setup()
        self.peek(b, me, snap)
        t = 50.0 + PEEK_WAIT_S + 0.1
        botmod.TEAM_FACING[("reach_test", 0)][1] = (t, *botmod.TEAM_FACING[("reach_test", 0)][1][1:])
        self.assertIn(("hunt", Vec(-10.0, 0.0, 0.0)), self.peek(b, me, snap, t))

    def test_a_weak_man_is_not_waited_for(self):
        b, me, snap = self.setup(novice=True)
        self.assertIn(("hunt", Vec(-10.0, 0.0, 0.0)), self.peek(b, me, snap))

    def test_unknown_facing_no_wait(self):
        b, me, snap = self.setup()
        botmod.TEAM_FACING.clear()                             # (nobody on the team sees him: no wallhack)
        self.assertIn(("hunt", Vec(-10.0, 0.0, 0.0)), self.peek(b, me, snap))

    def test_mythic_waits_legendary_and_halo_4_do_not(self):
        b, me, snap = self.setup(tier="mythic")
        self.assertIn(("retreat", me.pos), self.peek(b, me, snap))
        for tier, game_map in (("top", "reach_test"), ("demon", "h4_test")):
            with self.subTest(tier=tier, game=game_map):
                b, me, snap = self.setup(tier=tier, game_map=game_map)
                self.assertIn(("hunt", Vec(-10.0, 0.0, 0.0)), self.peek(b, me, snap))


if __name__ == "__main__":
    unittest.main()
