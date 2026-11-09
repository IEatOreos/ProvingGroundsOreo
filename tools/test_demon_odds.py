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


class KeepGunTests(unittest.TestCase):
    """No swap mid-fight to a gun slower to the kill counting the swap and its charge (Bot.keeps_gun): live Haven
    1v1, a loaded BR swapped for the Boltshot at 2.5 u, its charge never fired."""

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
