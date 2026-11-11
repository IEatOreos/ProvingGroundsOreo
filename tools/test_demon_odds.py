"""Halo 4 Demon's fight odds (brain/odds.py) and the rules on them (Bot.demon_odds_rules, chase_ok), and the team's
sightings (Bot.share_sightings).

Run: python tools/test_demon_odds.py
"""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import odds
from brain import bot as botmod
from brain.bot import Belief, Bot, ODDS_BREAK, ODDS_ENGAGE, ODDS_BREAK_SCORE
from brain.core import PlayerState, Snapshot, Vec
from brain.profiles import make_profile


class OpenWall:
    """Flat open floor, a wall along x = 2.5: what is east of it does not see west of it."""

    def __init__(s, wall_x=2.5):
        s.wall_x = wall_x

    def path_ahead(s, a, b, n=80, **kw):
        d = b - a
        u = d.norm()
        return [a + u * (0.25 * (i + 1)) for i in range(min(n, int(d.flat() / 0.25)))]

    def los(s, a, b):
        return s.wall_x is None or (a.x - s.wall_x) * (b.x - s.wall_x) > 0

    def walkable(s, p):
        return True


def man(pid, x, y=0.0, shield=1.0, health=1.0, weapon="battle_rifle", facing_me=True, human=False, team=1):
    p = PlayerState(pid, team, f"p{pid}", Vec(x, y, 0.0), weapon=weapon, weapons=[weapon], ammo=[108], mag=[36],
                    yaw=math.atan2(-y, -x) if facing_me else math.atan2(y, x), is_bot=not human)
    p.shield, p.health = shield, health
    return p


def demon(tier="demon", game_map="h4_test", shield=1.0, health=1.0, wall=2.5):
    botmod.TEAM_EYES.clear()
    botmod.TEAM_SIGHTINGS.clear()
    b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": game_map}, random.Random(5))
    b.notes = []
    b._terrain = OpenWall(wall)
    me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0), weapon="battle_rifle", weapons=["battle_rifle"], ammo=[108],
                     mag=[36])
    me.shield, me.health = shield, health
    return b, me


def see(b, *men, t=50.0):
    for e in men:
        b.per.beliefs[e.id] = Belief(e.pos, Vec(), t, True, "eyes")
        b.per.recognized.add(e.id)


class ModelTests(unittest.TestCase):
    def odds(self, me_vitals, men):
        b, me = demon(shield=me_vitals[0], health=me_vitals[1])
        snap = Snapshot(50.0, [me] + men, mode="slayer")
        see(b, *men)
        return b.fight_odds(50.0, me, snap, [e.id for e in men])[0]

    def test_full_against_a_full_person_aware_is_a_slight_edge(self):
        o = self.odds((1.0, 1.0), [man(1, 10.0, human=True)])
        self.assertGreater(o, 1.0)
        self.assertLess(o, 1.4)

    def test_full_against_a_man_not_looking_is_taken(self):
        self.assertGreaterEqual(self.odds((1.0, 1.0), [man(1, 10.0, human=True, facing_me=False)]), ODDS_ENGAGE)

    def test_one_shot_against_a_full_man_is_not(self):
        self.assertLess(self.odds((0.0, 0.3), [man(1, 10.0, human=True, facing_me=False)]), ODDS_ENGAGE)
        self.assertLess(self.odds((0.0, 0.3), [man(1, 10.0, human=True)]), ODDS_BREAK)

    def test_two_people_on_one_loses(self):
        self.assertLess(self.odds((1.0, 1.0), [man(1, 10.0, human=True), man(2, 9.0, 4.0, human=True)]), ODDS_BREAK)

    def test_two_bots_on_a_full_demon_is_taken(self):
        self.assertGreater(self.odds((1.0, 1.0), [man(1, 10.0), man(2, 9.0, 4.0)]), ODDS_ENGAGE)

    def test_a_cracked_man_is_finished(self):
        self.assertGreater(self.odds((1.0, 1.0), [man(1, 10.0, shield=0.0, health=0.4, human=True)]), ODDS_ENGAGE)

    def test_out_of_his_guns_reach(self):
        self.assertGreater(self.odds((0.5, 1.0), [man(1, 20.0, weapon="shotgun")]), 5.0)

    def test_remaining_weights_shield_and_body(self):
        p = man(1, 0.0, shield=0.0, health=1.0)
        self.assertAlmostEqual(odds.remaining(p), 45.0 / 115.0)


class ShieldTests(unittest.TestCase):
    """Judged by the shield (the owner, Nov 8): shields down is one headshot from a precision gun, whatever the body."""

    def odds(self, me_vitals, men):
        b, me = demon(shield=me_vitals[0], health=me_vitals[1])
        snap = Snapshot(50.0, [me] + men, mode="slayer")
        see(b, *men)
        return b.fight_odds(50.0, me, snap, [e.id for e in men])[0]

    def test_kill_times(self):
        full, bare = man(1, 0.0), man(2, 0.0, shield=0.0, health=1.0)
        self.assertAlmostEqual(odds.kill_time("battle_rifle", 10.0, full), 1.35)
        self.assertAlmostEqual(odds.kill_time("battle_rifle", 10.0, bare), odds.FINISH["battle_rifle"])
        self.assertAlmostEqual(odds.kill_time("assault_rifle", 8.0, bare), 1.8 * 45.0 / 115.0)
        self.assertAlmostEqual(odds.kill_time("sniper", 30.0, bare), odds.kill_time("sniper", 30.0, full))
        self.assertAlmostEqual(odds.kill_time("battle_rifle", 10.0, bare, shieldless=True), odds.FINISH["battle_rifle"])

    def test_shields_down_full_body_is_one_shot(self):
        self.assertTrue(odds.one_shot(man(1, 0.0, shield=0.0, health=1.0)))
        self.assertLess(self.odds((0.0, 1.0), [man(1, 10.0, human=True)]), ODDS_BREAK)
        self.assertLess(self.odds((0.0, 1.0), [man(1, 10.0, human=True, facing_me=False)]), ODDS_ENGAGE)

    def test_his_shield_down_is_a_kill_to_take(self):
        self.assertGreater(self.odds((1.0, 1.0), [man(1, 10.0, shield=0.0, health=1.0, human=True)]), 3.0)

    def test_an_automatic_still_needs_the_body(self):
        br = self.odds((0.0, 1.0), [man(1, 8.0, human=True)])
        ar = self.odds((0.0, 1.0), [man(1, 8.0, human=True, weapon="assault_rifle")])
        self.assertGreater(ar, br)

    def test_chase_by_the_shield(self):
        b, me = demon(shield=0.4, health=1.0)                  # full body, shield under CHASE_MIN: no chase
        him = man(1, -12.0, shield=0.0, health=1.0)
        b.per.beliefs[1] = Belief(him.pos, Vec(), 49.5, False, "eyes")
        self.assertFalse(b.chase_ok(50.0, me, Snapshot(50.0, [me, him], mode="slayer"), 1))
        b, me = demon(shield=0.8, health=0.3)                  # low body, shield up: it may
        b.per.beliefs[1] = Belief(him.pos, Vec(), 49.5, False, "eyes")
        self.assertTrue(b.chase_ok(50.0, me, Snapshot(50.0, [me, him], mode="slayer"), 1))


class RuleTests(unittest.TestCase):
    def test_losing_breaks_off_to_cover_it_can_reach(self):
        b, me = demon(shield=0.6, health=1.0, wall=0.2)        # two people on it; a wall's edge 0.2 u behind it
        men = [man(1, -10.0, human=True), man(2, -9.0, 4.0, human=True)]
        snap = Snapshot(50.0, [me] + men, mode="slayer")
        see(b, *men)
        b.demon_odds_rules(50.0, me, snap, {("fight", 1): 2.9}, [1, 2])   # (any ODDS_PERSIST hold starts here)
        scores = {("fight", 1): 2.9, ("hunt", Vec(-5.0, 0.0, 0.0)): 3.2}
        b.demon_odds_rules(50.3, me, snap, scores, [1, 2])
        retreats = [v for k, v in scores.items() if k[0] == "retreat"]
        self.assertEqual(retreats, [ODDS_BREAK_SCORE])
        self.assertFalse([k for k in scores if k[0] == "hunt"])
        self.assertTrue(any("break off" in n for n in b.notes))

    def test_losing_with_nowhere_to_go_fights_on(self):
        b, me = demon(shield=0.5, health=1.0, wall=None)       # open ground: no cover
        men = [man(1, -10.0, human=True), man(2, -9.0, 4.0, human=True)]
        snap = Snapshot(50.0, [me] + men, mode="slayer")
        see(b, *men)
        scores = {("fight", 1): 2.9}
        b.demon_odds_rules(50.0, me, snap, dict(scores), [1, 2])
        b.demon_odds_rules(50.3, me, snap, scores, [1, 2])
        self.assertEqual(scores, {("fight", 1): 2.9})

    def test_cover_it_cannot_reach_in_time_is_no_way_out(self):
        b, me = demon(shield=0.1, health=0.8, wall=4.0)        # well under 1 s to live, the cover 4 u off
        men = [man(1, -10.0, human=True), man(2, -9.0, 4.0, human=True)]
        snap = Snapshot(50.0, [me] + men, mode="slayer")
        see(b, *men)
        scores = {("fight", 1): 2.9}
        b.demon_odds_rules(50.0, me, snap, dict(scores), [1, 2])
        b.demon_odds_rules(50.3, me, snap, scores, [1, 2])
        self.assertFalse([k for k in scores if k[0] == "retreat"])

    def test_one_shot_does_not_peek_a_full_man(self):
        b, me = demon(shield=0.0, health=0.3, wall=0.5)
        him = man(1, -10.0, human=True, facing_me=False)
        snap = Snapshot(50.0, [me, him], mode="slayer")
        see(b, him)
        scores = {("fight", 1): 1.9}
        b.demon_odds_rules(50.0, me, snap, scores, [1])
        self.assertNotIn(("fight", 1), scores)
        self.assertTrue(any(k[0] == "retreat" for k in scores))

    def test_full_takes_a_man_not_looking(self):
        b, me = demon(wall=None)
        him = man(1, -10.0, human=True, facing_me=False)
        snap = Snapshot(50.0, [me, him], mode="slayer")
        see(b, him)
        scores = {("fight", 1): 1.9}
        b.demon_odds_rules(50.0, me, snap, scores, [1])
        self.assertEqual(scores, {("fight", 1): 1.9})

    def test_a_hunt_into_a_group_is_dropped(self):
        b, me = demon(wall=None)
        g1, g2 = man(1, -30.0, human=True), man(2, -31.0, 2.0, human=True)
        snap = Snapshot(50.0, [me, g1, g2], mode="slayer")
        for e in (g1, g2):
            b.per.beliefs[e.id] = Belief(e.pos, Vec(), 49.0, False, "team")
        scores = {("hunt", Vec(-29.0, 0.0, 0.0)): 1.5}
        b.demon_odds_rules(50.0, me, snap, scores, [])
        self.assertEqual(scores, {})

    def test_other_tiers_and_games_unchanged(self):
        for tier, game_map in (("top", "h4_test"), ("demon", "reach_test")):
            with self.subTest(tier=tier, game=game_map):
                b, me = demon(tier, game_map, shield=0.0, health=0.3, wall=-1.0)
                him = man(1, -10.0, human=True, facing_me=False)
                snap = Snapshot(50.0, [me, him], mode="slayer")
                see(b, him)
                scores = {("fight", 1): 1.9}
                b.demon_odds_rules(50.0, me, snap, scores, [1])
                self.assertEqual(scores, {("fight", 1): 1.9})


class TeamOddsTests(unittest.TestCase):
    """Teammates with the enemy in view share the kill (Bot.mate_kill_times, odds.with_help): the owner, "in a team
    enviroment they struggle"."""

    def setup(self, mate_t=50.0, mate_eyes=(1, 2), mate_vehicle=-1, mate_alive=True, shield=1.0):
        b, me = demon(shield=shield, wall=0.2)
        men = [man(1, -10.0, human=True), man(2, -9.0, 4.0, human=True)]
        mate = PlayerState(5, 0, "mate", Vec(0.0, 3.0, 0.0), weapon="battle_rifle", weapons=["battle_rifle"],
                           ammo=[108], mag=[36])
        mate.vehicle, mate.alive = mate_vehicle, mate_alive
        snap = Snapshot(50.0, [me, mate] + men, mode="slayer")
        see(b, *men)
        botmod.TEAM_EYES[("h4_test", 0)] = {5: (mate_t, frozenset(mate_eyes), odds.DEMON_ACC)}
        return b, me, snap

    def test_two_on_one_with_a_demon_mate_on_them_is_no_longer_lost(self):
        b, me, snap = self.setup()
        with_mate = b.fight_odds(50.0, me, snap, [1, 2])[0]
        botmod.TEAM_EYES.clear()
        alone = b.fight_odds(50.0, me, snap, [1, 2])[0]
        self.assertLess(alone, ODDS_BREAK)
        self.assertGreaterEqual(with_mate, ODDS_BREAK)
        self.assertGreater(with_mate, 1.5 * alone)

    def test_a_stale_dead_or_riding_mate_does_not_count(self):
        for kw in (dict(mate_t=49.5), dict(mate_vehicle=7), dict(mate_alive=False), dict(mate_eyes=())):
            with self.subTest(**kw):
                b, me, snap = self.setup(**kw)
                self.assertLess(b.fight_odds(50.0, me, snap, [1, 2])[0], ODDS_BREAK)

    def test_no_break_off_while_a_mate_fights_them_with_it(self):
        for mate, breaks in (((1, 2), False), ((), True)):
            with self.subTest(mate_eyes=mate):
                b, me, snap = self.setup(mate_eyes=mate)
                b.demon_odds_rules(50.0, me, snap, {("fight", 1): 2.9}, [1, 2])
                scores = {("fight", 1): 2.9}
                b.demon_odds_rules(50.3, me, snap, scores, [1, 2])
                self.assertEqual(bool([k for k in scores if k[0] == "retreat"]), breaks)

    def test_with_help_adds_paces(self):
        self.assertAlmostEqual(odds.with_help(2.0, [2.0]), 1.0)
        self.assertAlmostEqual(odds.with_help(math.inf, [1.5]), 1.5)
        self.assertEqual(odds.with_help(math.inf, []), math.inf)

    def test_every_bot_posts_its_eyes(self):
        b, me = demon("top")
        him = man(1, -10.0)
        b.per.beliefs[1] = Belief(him.pos, Vec(), 50.0, True, "eyes")
        b.per.visible_enemies = lambda: [1]
        b.share_sightings(50.0, me, Snapshot(50.0, [me, him], mode="slayer"))
        t, eyes, acc = botmod.TEAM_EYES[("h4_test", 0)][0]
        self.assertEqual((t, eyes, acc), (50.0, frozenset({1}), odds.ACC[False]))


class SpreadTests(unittest.TestCase):
    """No piling onto a teammate's kill (Bot.mate_has_him, threat, demon_commit): live Haven, another Demon was on the
    man in 63% of Demon kills (the owner's 36%)."""

    def setup(self, tier="demon", game_map="h4_test", mate_demon=True, mate_t=50.0, my_gun="assault_rifle"):
        b, me = demon(tier, game_map, wall=None)
        me.weapon = me.weapons[0] = my_gun       # (an AR at 10 u: the mate's BR is the quicker kill)
        e1, e2 = man(1, -10.0), man(2, 6.0, 8.0)
        e1.yaw = math.atan2(6.0, 0.0)                       # (he faces the mate, not us)
        mate = PlayerState(5, 0, "mate", Vec(-10.0, 6.0, 0.0), weapon="battle_rifle", weapons=["battle_rifle"],
                           ammo=[108], mag=[36])
        snap = Snapshot(50.0, [me, mate, e1, e2], mode="slayer")
        see(b, e1, e2)
        key = (game_map, 0)
        botmod.TEAM_TARGETS.clear()
        botmod.TEAM_TARGETS[key] = {5: (mate_t, 1)}
        botmod.TEAM_EYES[key] = {5: (mate_t, frozenset({1}), odds.DEMON_ACC if mate_demon else odds.ACC[False])}
        return b, me, snap

    def test_a_mates_winning_kill_scores_half_and_no_team_shot(self):
        b, me, snap = self.setup()
        b.team_focus = {1: 1}
        piled = b.threat(50.0, me, snap, 1)
        botmod.TEAM_TARGETS.clear()
        alone = b.threat(50.0, me, snap, 1)
        self.assertAlmostEqual(piled, alone * botmod.SPREAD_K - 60.0 * b.p.teamwork * botmod.SPREAD_K)

    def test_a_committed_demon_turns_to_the_man_nobody_has(self):
        b, me, snap = self.setup()
        b.goal, b.target_at = ("fight", 1), 40.0
        scored = {1: 100.0, 2: 60.0}
        self.assertEqual(b.demon_commit(50.0, me, snap, [1, 2], scored, 2, 1), 2)
        self.assertTrue(any(n.startswith("spread") for n in b.notes))

    def test_two_alike_on_one_man_only_one_leaves(self):
        b, me, snap = self.setup(my_gun="battle_rifle")          # (both BRs: a tie)
        self.assertFalse(b.mate_has_him(50.0, me, snap, snap.player(1)))   # (it is bot 0: the lower id keeps him)
        b9 = Bot(9, 0, make_profile("demon", "rusher", random.Random(3)), {"name": "h4_test"}, random.Random(5))
        b9.notes = []
        me9 = PlayerState(9, 0, "me9", Vec(0.0, 0.0, 0.0), weapon="battle_rifle", weapons=["battle_rifle"],
                          ammo=[108], mag=[36])
        snap9 = Snapshot(50.0, [me9] + [p for p in snap.players if p.id != 0], mode="slayer")
        self.assertTrue(b9.mate_has_him(50.0, me9, snap9, snap9.player(1)))   # (bot 9 leaves him to bot 5)

    def test_the_man_it_left_stays_left_a_moment(self):
        b, me, snap = self.setup()
        b.goal, b.target_at = ("fight", 1), 40.0
        b.demon_commit(50.0, me, snap, [1, 2], {1: 100.0, 2: 60.0}, 2, 1)
        botmod.TEAM_TARGETS.clear()                               # (the mate's post gone: the hold alone)
        held = b.threat(50.5, me, snap, 1)
        after = b.threat(50.0 + botmod.SPREAD_HOLD + 0.1, me, snap, 1)
        self.assertAlmostEqual(held, after * botmod.SPREAD_K)

    def test_a_losing_or_stale_mate_still_gets_help(self):
        for kw in (dict(mate_demon=False), dict(mate_t=49.0)):
            with self.subTest(**kw):
                b, me, snap = self.setup(**kw)
                self.assertFalse(b.mate_has_him(50.0, me, snap, snap.player(1)))

    def test_other_tiers_and_games_unchanged(self):
        for tier, game_map in (("top", "h4_test"), ("demon", "reach_test")):
            with self.subTest(tier=tier, game=game_map):
                b, me, snap = self.setup(tier, game_map)
                self.assertFalse(b.mate_has_him(50.0, me, snap, snap.player(1)))


class PressTests(unittest.TestCase):
    """Halo 4 Demon walks in with two or more in view when ahead and winning (Bot.press_on, DEMON_PRESS_LEAD); alone
    with one man, upstream's rule (even on the vitals) as before."""

    def press(self, tier="demon", game_map="h4_test", my_shield=1.0, his_shield=1.0, odds_now=1.5, two=False):
        b, me = demon(tier, game_map, shield=my_shield, wall=None)
        him = man(1, -8.0, shield=his_shield, human=True)
        men = [him] + ([man(2, -8.0, 5.0)] if two else [])
        see(b, *men)
        b.press_fight, b.last_odds = True, odds_now
        snap = Snapshot(50.0, [me] + men, mode="slayer")
        b.per.visible_enemies = lambda: [m.id for m in men]
        return b.press_on(me, b.per.beliefs[1], him, snap, 8.0, 0.0)

    def test_two_in_view_ahead_and_winning_it_walks_in(self):
        self.assertTrue(self.press(two=True))

    def test_two_in_view_behind_or_losing_it_holds(self):
        self.assertFalse(self.press(two=True, my_shield=0.7, his_shield=1.0))
        self.assertFalse(self.press(two=True, odds_now=1.0))

    def test_one_man_in_view_as_before(self):
        self.assertTrue(self.press(odds_now=0.3))       # (even on the vitals: upstream presses, odds or not)
        self.assertFalse(self.press(my_shield=0.5))

    def test_legendary_and_reach_demon_keep_the_hold(self):
        for tier, game_map in (("top", "h4_test"), ("demon", "reach_test")):
            with self.subTest(tier=tier, game=game_map):
                self.assertFalse(self.press(tier, game_map, two=True))


class SixTests(unittest.TestCase):
    """The owner's six (Nov 8): trade rule, re-peek with a full shield, one-shot callouts, instant trades, third party,
    regroup."""

    def setUp(self):
        for d in (botmod.TEAM_TARGETS, botmod.TEAM_CRACKED, botmod.TEAM_ATTACKERS):
            d.clear()

    # 1 trade rule
    def test_kills_first(self):
        self.assertEqual(odds.kills_first([(1.0, 0.5, 0.0)]), 0)                      # he drops us first
        self.assertEqual(odds.kills_first([(0.5, 1.0, 0.0)]), 1)
        self.assertEqual(odds.kills_first([(0.3, 1.0, 0.0), (1.0, 1.0, 0.0)]), 1)     # one, then down
        self.assertEqual(odds.kills_first([]), 0)

    def trade_case(self, mode):
        b, me = demon(shield=0.5, wall=0.2)
        men = [man(1, -6.0, shield=0.0, human=True), man(2, -12.0, 4.0, human=True)]
        snap = Snapshot(50.0, [me] + men, mode=mode)
        see(b, *men)
        self.assertLess(b.fight_odds(50.0, me, snap, [1, 2])[0], ODDS_BREAK)          # (losing on the odds)
        b.demon_odds_rules(50.0, me, snap, {("fight", 1): 2.9}, [1, 2])
        scores = {("fight", 1): 2.9}
        b.demon_odds_rules(50.3, me, snap, scores, [1, 2])
        return b, scores

    def test_slayer_losing_but_a_kill_first_stays(self):
        b, scores = self.trade_case("slayer")
        self.assertFalse([k for k in scores if k[0] == "retreat"])
        self.assertTrue(any("trade" in n for n in b.notes))

    def test_objective_modes_no_trade_rule(self):
        b, _ = self.trade_case("ctf")
        self.assertFalse(any("trade" in n for n in b.notes))      # (as before: its cover out of reach, it fights on)

    def test_a_man_on_it_close_is_fought_out_not_run_from(self):
        b, me = demon(shield=0.4, wall=0.2)
        men = [man(1, -5.0, human=True), man(2, -9.0, 4.0, human=True)]
        snap = Snapshot(50.0, [me] + men, mode="ctf")                 # (no trade rule: the range alone)
        see(b, *men)
        b.demon_odds_rules(50.0, me, snap, {("fight", 1): 2.9}, [1, 2])
        scores = {("fight", 1): 2.9}
        b.demon_odds_rules(50.3, me, snap, scores, [1, 2])
        self.assertFalse([k for k in scores if k[0] == "retreat"])
        self.assertTrue(any("fight it out" in n for n in b.notes))

    def test_no_kill_first_still_breaks_off(self):
        b, me = demon(shield=0.6, wall=0.2)
        men = [man(1, -10.0, human=True), man(2, -9.0, 4.0, human=True)]
        snap = Snapshot(50.0, [me] + men, mode="slayer")
        see(b, *men)
        b.demon_odds_rules(50.0, me, snap, {("fight", 1): 2.9}, [1, 2])
        scores = {("fight", 1): 2.9}
        b.demon_odds_rules(50.3, me, snap, scores, [1, 2])
        self.assertTrue([k for k in scores if k[0] == "retreat"])
        self.assertGreater(b.repeek_until, 50.3)                                      # (the re-peek hold armed)

    # 6 re-peek with a full shield
    def repeek(self, **kw):
        b, me = demon(shield=0.5, wall=None)
        him = man(1, -10.0, human=True, **kw)
        snap = Snapshot(50.0, [me, him], mode="slayer")
        see(b, him)
        b.repeek_until, b.goal = 55.0, ("retreat", Vec(1.0, 0.0, 0.0))
        scores = {("fight", 1): 2.9, ("hunt", Vec(-5.0, 0.0, 0.0)): 3.2}
        return b, me, snap, scores

    def test_half_shield_no_re_peek(self):
        b, me, snap, scores = self.repeek(facing_me=False)
        b.repeek_rule(50.0, me, snap, scores)
        self.assertEqual(set(k[0] for k in scores), {"retreat"})
        self.assertEqual(scores[b.goal], botmod.REPEEK_HOLD_SCORE)

    def test_fights_back_a_man_hurting_it_or_one_shot(self):
        b, me, snap, scores = self.repeek()
        b.per.attacker_id, b.per.attacker_t = 1, 49.8
        b.repeek_rule(50.0, me, snap, scores)
        self.assertIn(("fight", 1), scores)
        b, me, snap, scores = self.repeek(shield=0.0)
        b.repeek_rule(50.0, me, snap, scores)
        self.assertIn(("fight", 1), scores)

    def test_full_shield_or_hold_over_peeks_again(self):
        b, me, snap, scores = self.repeek()
        me.shield = 0.97
        b.repeek_rule(50.0, me, snap, scores)
        self.assertIn(("fight", 1), scores)
        b, me, snap, scores = self.repeek()
        b.repeek_rule(56.0, me, snap, scores)
        self.assertIn(("fight", 1), scores)

    # 3 one-shot callouts
    def test_a_called_one_shot_out_of_sight_is_hunted_when_healthy(self):
        for shield, hunted in ((1.0, True), (0.3, False)):
            with self.subTest(shield=shield):
                b, me = demon(shield=shield, wall=None)
                him = man(1, -10.0, shield=0.0, human=True)
                b.per.beliefs[1] = Belief(him.pos, Vec(), 49.8, False, "team")
                botmod.TEAM_CRACKED[("h4_test", 0)] = {1: (49.5, him.pos)}
                scores = {}
                b.team_play(50.0, me, Snapshot(50.0, [me, him], mode="slayer"), scores, [])
                self.assertEqual(scores.get(("hunt", him.pos)) == botmod.CALLOUT_SCORE, hunted)

    def test_one_shot_in_sight_first(self):
        b, me = demon(wall=None)
        cracked, full = man(1, -10.0, shield=0.0), man(2, -10.0, 1.0)
        snap = Snapshot(50.0, [me, cracked, full], mode="slayer")
        see(b, cracked, full)
        self.assertGreater(b.threat(50.0, me, snap, 1), 1.4 * b.threat(50.0, me, snap, 2))

    def test_every_bot_posts_cracked_men_and_its_attacker(self):
        b, me = demon("top", wall=None)
        him = man(1, -10.0, shield=0.0)
        b.per.beliefs[1] = Belief(him.pos, Vec(), 50.0, True, "eyes")
        b.per.visible_enemies = lambda: [1]
        b.per.attacker_id, b.per.attacker_t = 1, 49.9
        b.share_sightings(50.0, me, Snapshot(50.0, [me, him], mode="slayer"))
        self.assertIn(1, botmod.TEAM_CRACKED[("h4_test", 0)])
        self.assertEqual(botmod.TEAM_ATTACKERS[("h4_test", 0)][0][:2], (1, 49.9))

    # 4 instant trades
    def test_a_teammates_killer_is_pushed(self):
        b, me = demon(wall=None)
        mate = PlayerState(5, 0, "mate", Vec(-4.0, 2.0, 0.0), weapon="battle_rifle", weapons=["battle_rifle"])
        killer = man(1, -12.0, shield=0.1, human=True)
        see(b, killer)
        b.team_play(49.9, me, Snapshot(49.9, [me, mate, killer], mode="slayer"), {}, [1])   # (the mate alive)
        botmod.TEAM_ATTACKERS[("h4_test", 0)] = {5: (1, 49.8, mate.pos)}
        mate.alive = False
        scores = {}
        b.team_play(50.0, me, Snapshot(50.0, [me, mate, killer], mode="slayer"), scores, [1])
        self.assertEqual(scores.get(("fight", 1)), botmod.TRADE_SCORE)
        self.assertTrue(any(n.startswith("trade: #5") for n in b.notes))

    # 2 third party
    def test_a_teammates_even_fight_is_taken_from_an_angle(self):
        b, me = demon(wall=None)
        mate = PlayerState(5, 0, "mate", Vec(-14.0, 10.0, 0.0), weapon="battle_rifle", weapons=["battle_rifle"])
        him = man(1, -14.0, 0.0, human=True)
        b.per.beliefs[1] = Belief(him.pos, Vec(), 49.9, False, "team")
        botmod.TEAM_TARGETS[("h4_test", 0)] = {5: (50.0, 1)}
        botmod.TEAM_EYES[("h4_test", 0)] = {5: (50.0, frozenset({1}), odds.ACC[False])}   # (a bot losing to him)
        scores = {}
        b.team_play(50.0, me, Snapshot(50.0, [me, mate, him], mode="slayer"), scores, [])
        hunts = [k[1] for k in scores if k[0] == "hunt"]
        self.assertEqual(len(hunts), 1)
        p = hunts[0]
        self.assertGreater(abs(p.x - him.pos.x), 3.0)                 # (off the mate's line, which runs along y)
        self.assertEqual(scores[("hunt", p)], botmod.THIRD_SCORE)

    def test_a_teammate_winning_his_fight_gets_no_third_man(self):
        b, me = demon(wall=None)
        mate = PlayerState(5, 0, "mate", Vec(-14.0, 10.0, 0.0), weapon="battle_rifle", weapons=["battle_rifle"])
        him = man(1, -14.0, 0.0)                                      # (a bot: the Demon mate beats him)
        b.per.beliefs[1] = Belief(him.pos, Vec(), 49.9, False, "team")
        botmod.TEAM_TARGETS[("h4_test", 0)] = {5: (50.0, 1)}
        botmod.TEAM_EYES[("h4_test", 0)] = {5: (50.0, frozenset({1}), odds.DEMON_ACC)}
        scores = {}
        b.team_play(50.0, me, Snapshot(50.0, [me, mate, him], mode="slayer"), scores, [])
        self.assertEqual(scores, {})

    # 5 regroup
    def test_break_off_cover_nearest_a_teammate(self):
        import numpy as np
        b, me = demon(wall=None)
        T = b._terrain
        T.los = lambda a, c: False                                    # (both spots hide from him)
        T.cover_spots = np.array([[1.0, 0.0, 0.0, -1.0, 0.0], [2.5, 2.5, 0.0, -1.0, 0.0]])
        him = man(1, -10.0, human=True)
        mate = PlayerState(5, 0, "mate", Vec(4.0, 4.0, 0.0), weapon="battle_rifle", weapons=["battle_rifle"])
        snap = Snapshot(50.0, [me, mate, him], mode="slayer")
        self.assertEqual(b.regroup_cover(me, [him.pos], snap, 5.0), Vec(2.5, 2.5, 0.0))
        self.assertEqual(b.regroup_cover(me, [him.pos], snap, 0.6), Vec(1.0, 0.0, 0.0))   # (the far one out of time)
        alone = Snapshot(50.0, [me, him], mode="slayer")
        self.assertEqual(b.regroup_cover(me, [him.pos], alone, 5.0), Vec(1.0, 0.0, 0.0))


class PickupTests(unittest.TestCase):
    """Nov 9: the odds by the best loaded gun carried (a pickup's swap held the Boltshot: odds 0.01, break-offs 1.3 u
    from the owner's SAW), a power gun lying close first (Bot.power_grab), and an empty main gun refilled
    (Bot.main_dry, rearm_point)."""

    def setUp(self):
        botmod.TEAM_EYES.clear()

    def holding_boltshot(self, carbine_rounds):
        b, me = demon(wall=None)
        me.weapon, me.weapons, me.ammo, me.mag = "boltshot", ["covenant_carbine", "boltshot"], [carbine_rounds, 30], [0, 10]
        owner = man(1, -17.0, human=True)
        snap = Snapshot(50.0, [me, owner], mode="slayer")
        see(b, owner)
        return b.fight_odds(50.0, me, snap, [1])[0]

    def test_odds_by_the_loaded_rifle_it_carries(self):
        self.assertGreater(self.holding_boltshot(58), 0.5)        # (its Carbine, the swap counted: not unarmed)
        self.assertLess(self.holding_boltshot(0), 0.1)           # (the Carbine empty: the Boltshot is all it has)

    def grab(self, gun="lmg", d=8.0, tier="demon", game_map="h4_test", near_man=None, demon_mate_at=None):
        b, me = demon(tier, game_map, wall=None)
        q = Vec(-d, 0.0, 0.0)
        men = [man(1, near_man, 0.0)] if near_man is not None else []
        players = [me] + men
        if demon_mate_at is not None:
            mate = PlayerState(5, 0, "mate", demon_mate_at, weapon="battle_rifle", weapons=["battle_rifle"])
            players.append(mate)
            botmod.TEAM_EYES[(game_map, 0)] = {5: (50.0, frozenset(), odds.DEMON_ACC)}
        see(b, *men)
        snap = Snapshot(50.0, players, mode="slayer", ground_weapons=[(gun, q)])
        scores = {}
        b.power_grab(50.0, me, snap, scores, [m.id for m in men])
        return scores.get(("item", q))

    def test_a_power_gun_lying_close_comes_first(self):
        self.assertEqual(self.grab(), botmod.POWER_GRAB_SCORE)
        self.assertEqual(self.grab("rockets", 14.0), botmod.POWER_GRAB_SCORE)

    def test_not_a_rifle_not_far_not_with_a_man_on_it_not_for_a_nearer_demon(self):
        self.assertIsNone(self.grab("battle_rifle"))
        self.assertIsNone(self.grab(d=20.0))
        self.assertIsNone(self.grab(near_man=-4.0))
        self.assertIsNone(self.grab(demon_mate_at=Vec(-7.5, 0.5, 0.0)))

    def banned_grab(self, gun_at, reaches=True):
        b, me = demon(wall=None)
        b._terrain.reaches = lambda a, c, **kw: reaches
        b.goal_ban = {b._goal_key(("item", gun_at)): 70.0}                 # (headway gave up on it)
        scores = {}
        b.power_grab(50.0, me, Snapshot(50.0, [me], mode="slayer", ground_weapons=[("lmg", gun_at)]), scores, [])
        return scores.get(("item", gun_at)), b

    def test_a_ban_lifts_beside_the_gun_on_its_floor(self):
        got, b = self.banned_grab(Vec(-2.0, 0.0, 0.0))
        self.assertEqual(got, botmod.POWER_GRAB_SCORE)
        self.assertEqual(b.goal_ban, {})

    def test_a_ban_holds_from_the_walkway_over_it_and_an_unreachable_gun_is_passed(self):
        got, b = self.banned_grab(Vec(-2.0, 0.0, -3.6))
        self.assertIsNone(got)
        self.assertTrue(b.goal_ban)
        b, me = demon(wall=None)
        b._terrain.reaches = lambda a, c, **kw: False
        scores = {}
        b.power_grab(50.0, me, Snapshot(50.0, [me], mode="slayer", ground_weapons=[("lmg", Vec(-6.0, 0.0, 0.0))]),
                     scores, [])
        self.assertEqual(scores, {})

    def rearm(self, game_map="h4_test", br_rounds=0, tier="demon"):
        b, me = demon(tier, game_map, wall=None)
        me.weapon, me.weapons, me.ammo, me.mag = "boltshot", ["battle_rifle", "boltshot"], [br_rounds, 30], [0, 10]
        q = Vec(-25.0, 0.0, 0.0)
        return b.rearm_point(me, Snapshot(50.0, [me], mode="slayer", ground_weapons=[("battle_rifle", q)])), q

    def test_an_empty_main_gun_is_refilled_from_its_own_kind(self):
        for tier in ("demon", "novice"):
            with self.subTest(tier=tier):
                got, q = self.rearm(tier=tier)
                self.assertEqual(got, q)

    def test_a_loaded_main_gun_or_another_game_as_before(self):
        self.assertIsNone(self.rearm(br_rounds=40)[0])
        self.assertIsNone(self.rearm(game_map="reach_test")[0])

    def test_main_dry(self):
        b, me = demon()
        me.weapons, me.ammo = ["battle_rifle", "boltshot"], [0, 30]
        self.assertTrue(b.main_dry(me))
        me.ammo = [0, 0]
        self.assertTrue(b.main_dry(me))
        me.ammo = [-1, 30]
        self.assertFalse(b.main_dry(me))                          # (not known: not empty)
        me.weapons, me.ammo = ["boltshot", "magnum"], [0, 0]
        self.assertFalse(b.main_dry(me))                          # (sidearms only: dry(), not this)


class KeepGunTests(unittest.TestCase):
    """No swap mid-fight to a gun slower to the kill counting the swap and its charge (Bot.keeps_gun): live Haven
    1v1, a loaded BR swapped for the Boltshot at 2.5 u, its charge never fired. (The Boltshot's Short band as it was,
    0.8, so the range score still wants the swap: these test keeps_gun, not the band.)"""

    def setUp(self):
        self.band = botmod.BANDS["boltshot"]
        botmod.BANDS["boltshot"] = (0.8, 0.4, 0.05, 0.0)

    def tearDown(self):
        botmod.BANDS["boltshot"] = self.band

    def choose(self, tier="demon", game_map="h4_test", other="boltshot", d=2.0, his_shield=0.36, mag=30):
        b, me = demon(tier, game_map, wall=None)
        me.weapons, me.ammo, me.mag = ["battle_rifle", other], [108, 30], [mag, 10]
        him = man(1, -d, shield=his_shield, human=True)
        see(b, him)
        snap = Snapshot(50.0, [me, him], mode="slayer")
        return b.choose_weapon(50.0, me, "fight", 1, snap), b

    def test_demon_keeps_a_loaded_br_over_the_boltshot_up_close(self):
        for shield in (0.36, 1.0):
            with self.subTest(his_shield=shield):
                pick, b = self.choose(his_shield=shield)
                self.assertEqual(pick, -1)
                self.assertTrue(any(n.startswith("keep the battle_rifle") for n in b.notes))

    def test_a_shotgun_up_close_still_comes_out(self):
        pick, _ = self.choose(other="shotgun", d=2.0, his_shield=1.0)
        self.assertEqual(pick, 1)

    def test_an_empty_magazine_still_swaps(self):
        pick, _ = self.choose(mag=0)
        self.assertEqual(pick, 1)

    def test_other_tiers_and_games_swap_as_before(self):
        for tier, game_map in (("top", "h4_test"), ("demon", "reach_test")):
            with self.subTest(tier=tier, game=game_map):
                self.assertEqual(self.choose(tier, game_map)[0], 1)


class BoltshotBandTests(unittest.TestCase):
    """The Boltshot's Short band 0.6 (Nov 9): a loose shotgun or Scattershot is worth the trip from BR + Boltshot, and
    a loaded BR stays in hand at 2 u for every tier."""

    def test_shotgun_and_scattershot_are_picked_up_over_the_boltshot(self):
        b, _ = demon("average")
        have = botmod.loadout_value(["battle_rifle", "boltshot"], b.rank, "h4")
        for gun in ("shotgun", "scattershot"):
            with self.subTest(gun=gun):
                gain = botmod.loadout_value(["battle_rifle", gun], b.rank, "h4") - have
                self.assertGreater(gain, botmod.UPGRADE_GAIN_GAME.get("h4", botmod.UPGRADE_GAIN))

    def test_a_loaded_br_stays_in_hand_up_close(self):
        b, me = demon("top", wall=None)
        me.weapons, me.ammo, me.mag = ["battle_rifle", "boltshot"], [108, 30], [30, 10]
        him = man(1, -2.0, shield=0.36, human=True)
        see(b, him)
        self.assertEqual(b.choose_weapon(50.0, me, "fight", 1, Snapshot(50.0, [me, him], mode="slayer")), -1)


class RetreatJukeTests(unittest.TestCase):
    """The walk to cover keeps its speed (Bot.retreat_juke): live Haven, a walk to the side was cut to 0.2."""

    def walk(self, tier, game_map, forward, strafe, juke):
        b, _ = demon(tier, game_map)
        b.strafe_dir = juke
        act = botmod.Action(yaw=0.0, pitch=0.0)
        act.forward, act.strafe = forward, strafe
        b.retreat_juke(act)
        return act.forward, act.strafe

    def test_demon_walks_to_the_side_at_full_speed_either_juke(self):
        for juke in (1.0, -1.0):
            f, st = self.walk("demon", "h4_test", -0.36, -0.93, juke)
            self.assertAlmostEqual(math.hypot(f, st), 1.0)
            toward = (f * -0.36 + st * -0.93) / math.hypot(0.36, 0.93)
            self.assertGreater(toward, 0.9)

    def test_the_juke_still_swings_the_walk(self):
        a = self.walk("demon", "h4_test", 0.0, 1.0, 1.0)
        b = self.walk("demon", "h4_test", 0.0, 1.0, -1.0)
        self.assertGreater(abs(a[0] - b[0]), 0.5)

    def test_other_tiers_and_games_keep_the_mix(self):
        for tier, game_map in (("top", "h4_test"), ("demon", "reach_test")):
            with self.subTest(tier=tier, game=game_map):
                self.assertEqual(self.walk(tier, game_map, -0.36, -0.93, 1.0), (-0.36, -0.93 * 0.6 + 0.4))


class ChaseTests(unittest.TestCase):
    def setup(self, shield=1.0, health=1.0, friend=False, tier="demon", game_map="h4_test"):
        b, me = demon(tier, game_map, shield=shield, health=health)
        him = man(1, -12.0, shield=0.3, health=1.0)
        men = [me, him]
        b.per.beliefs[1] = Belief(him.pos, Vec(), 49.5, False, "eyes")
        if friend:
            f = man(2, -15.0, 3.0)
            men.append(f)
            b.per.beliefs[2] = Belief(f.pos, Vec(), 49.0, False, "team")
        return b, me, Snapshot(50.0, men, mode="slayer")

    def test_healthy_alone_chases(self):
        b, me, snap = self.setup()
        self.assertTrue(b.chase_ok(50.0, me, snap, 1))

    def test_hurt_or_into_his_friend_does_not(self):
        b, me, snap = self.setup(shield=0.1, health=0.7)
        self.assertFalse(b.chase_ok(50.0, me, snap, 1))
        b, me, snap = self.setup(friend=True)
        self.assertFalse(b.chase_ok(50.0, me, snap, 1))

    def test_others_unchanged(self):
        b, me, snap = self.setup(shield=0.1, health=0.7, tier="top")
        self.assertTrue(b.chase_ok(50.0, me, snap, 1))
        b, me, snap = self.setup(shield=0.1, health=0.7, game_map="reach_test")
        self.assertTrue(b.chase_ok(50.0, me, snap, 1))


class TeamSightingTests(unittest.TestCase):
    def setUp(self):
        botmod.TEAM_SIGHTINGS.clear()

    def test_a_demon_takes_its_teammates_sightings(self):
        spotter, sme = demon("strong")
        sme = PlayerState(5, 0, "mate", Vec(30.0, 0.0, 0.0))
        d, me = demon()
        him = man(1, 40.0)
        snap = Snapshot(50.0, [me, sme, him], mode="slayer")
        spotter.per.beliefs[1] = Belief(him.pos, Vec(1.0, 0.0, 0.0), 50.0, True, "eyes")
        spotter.per.recognized.add(1)
        spotter.share_sightings(50.0, sme, snap)
        d.share_sightings(50.1, me, snap)
        b = d.per.beliefs.get(1)
        self.assertIsNotNone(b)
        self.assertEqual((b.source, b.seen, b.pos), ("team", False, him.pos))

    def test_stale_or_other_tiers_do_not(self):
        spotter, _ = demon("strong")
        sme = PlayerState(5, 0, "mate", Vec(30.0, 0.0, 0.0))
        him = man(1, 40.0)
        spotter.per.beliefs[1] = Belief(him.pos, Vec(), 50.0, True, "eyes")
        spotter.per.recognized.add(1)
        legend, me = demon("top")
        snap = Snapshot(50.0, [me, sme, him], mode="slayer")
        spotter.share_sightings(50.0, sme, snap)
        legend.share_sightings(50.1, me, snap)
        self.assertNotIn(1, legend.per.beliefs)
        d, me = demon()
        d.share_sightings(51.0, me, snap)                 # 1 s later: stale
        self.assertNotIn(1, d.per.beliefs)


if __name__ == "__main__":
    unittest.main()
