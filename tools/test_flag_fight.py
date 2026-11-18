"""(custom, Nov 17) Reach CTF and Stockpile: a carrier that will die before it gets home drops the flag and fights the man,
then goes back for it (Bot.flag_fight_*). The owner: "it feels like they just let me kill them for free because they
ignore anything but running the flag". Four Reach CTF traces (Nov 13-17): 15 bot carriers killed, most walking on
while a man 2-6 u off emptied them in 0.1-3 s."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                                     # noqa: E402
from brain import profiles                                          # noqa: E402
from brain.bot import Belief, Bot, Order                            # noqa: E402
from brain.core import Action, FlagState, PlayerState, Snapshot, Vec  # noqa: E402

HOME = Vec(0.0, 0.0, 0.0)         # our capture point
AT = Vec(12.0, 0.0, 0.0)          # the carrier, 12 u out (4.8 s walk)
NOW = 100.0


def scene(mode="ctf", at=AT, game_map="reach_45_aftship", lost=(0.6, 0.6), hp=(0.0, 0.8), man_at=Vec(15.0, 0.0, 0.0),
          vehicle=-1):
    """A carrier on team 0 hurt by man 2 (team 1); lost: the losses in the last 1.5 s; hp: its (shield, health)."""
    b = Bot(1, 0, profiles.make_profile("top", "rusher", random.Random(1)), dict(name=game_map))
    me = PlayerState(1, 0, "carrier", at)
    me.has_flag, me.weapon, me.weapons = True, "flag", ["dmr", "assault_rifle", "flag"]
    me.shield, me.health, me.vehicle = hp[0], hp[1], vehicle
    man = PlayerState(2, 1, "man", man_at)
    snap = Snapshot(NOW, [me, man], mode=mode)
    if mode == "ctf":
        snap.flags = {0: FlagState(0, HOME, HOME), 1: FlagState(1, Vec(40, 0, 0), at, "carried", 1)}
        b.order = Order("runner", HOME)
    else:
        snap.obj_goals = {0: [HOME], 1: [Vec(40, 0, 0)]}
        snap.obj_items = [dict(pos=at, carrier=1, kind="stockpile_flag", team=8)]
    b.per.beliefs[2] = Belief(man_at, Vec(0, 0, 0), NOW, True, "eyes")
    b.per.recognized.add(2)
    b.per.losses = [(NOW - 0.6 + 0.3 * k, x) for k, x in enumerate(lost)]
    return b, me, man, snap


def drop(b, me, snap, flag_at=AT, mode="ctf"):
    """The flag leaves its hands at flag_at."""
    me.has_flag, me.weapon, me.weapons = False, "dmr", ["dmr", "assault_rifle"]
    if mode == "ctf":
        snap.flags[1] = FlagState(1, Vec(40, 0, 0), flag_at, "dropped")
    else:
        snap.obj_items = [dict(pos=flag_at, carrier=None, kind="stockpile_flag", team=8)]


class FlagFight(unittest.TestCase):
    def test_dying_far_from_home_drops_and_fights(self):
        """0.8 left, losing 0.8/s: empty in 1 s, home 4.8 s off: the switch is tapped and the man fought over the run."""
        b, me, man, snap = scene()
        scores = {("objective", HOME): 3.0}
        b.flag_fight_scores(NOW, me, snap, scores)
        self.assertEqual(scores[("fight", 2)], botmod.FLAG_FIGHT_SCORE)
        self.assertGreater(scores[("fight", 2)], scores[("objective", HOME)])
        act = Action(action=True)
        b.flag_fight_press(NOW, me, act, b.flag_fight_phase(NOW, me, snap))
        self.assertTrue(act.cycle)
        self.assertFalse(act.action)

    def test_runs_on_when_it_would_live(self):
        """Losing slowly (empty in 4 s), healthy, or not hurt at all: it runs on, as before."""
        for kw in (dict(lost=(0.3,)), dict(hp=(1.0, 1.0)), dict(lost=())):
            b, me, man, snap = scene(**kw)
            self.assertFalse(b.flag_fight_check(NOW, me, snap), kw)

    def test_runs_on_near_home(self):
        """3 u from home it carries on: the capture beats any fight."""
        b, me, man, snap = scene(at=Vec(3.0, 0.0, 0.0), man_at=Vec(5.0, 0.0, 0.0))
        self.assertFalse(b.flag_fight_check(NOW, me, snap))

    def test_runs_on_when_home_comes_first(self):
        """Home 3 s off (7.5 u): empty in 1.4 s, it dies first and drops; empty in 2 s (past FLAG_FIGHT_DIE_S), it runs
        on."""
        b, me, man, snap = scene(at=Vec(7.5, 0, 0), man_at=Vec(10, 0, 0), lost=(0.6, 0.6), hp=(0.0, 1.12))
        self.assertTrue(b.flag_fight_check(NOW, me, snap))
        b, me, man, snap = scene(at=Vec(7.5, 0, 0), man_at=Vec(10, 0, 0), lost=(0.6, 0.6), hp=(0.4, 1.2))
        self.assertFalse(b.flag_fight_check(NOW, me, snap))

    def test_no_man_near_no_drop(self):
        """The damage from a man 25 u off (a sniper across the map): nobody to fight here, it runs on."""
        b, me, man, snap = scene(man_at=Vec(37.0, 0.0, 0.0))
        self.assertFalse(b.flag_fight_check(NOW, me, snap))

    def test_not_in_a_vehicle_not_other_games_or_modes(self):
        for kw in (dict(vehicle=5), dict(game_map="h4_ca_warhouse"), dict(game_map="h3_guardian")):
            b, me, man, snap = scene(**kw)
            self.assertFalse(b.flag_fight_check(NOW, me, snap), kw)
        b, me, man, snap = scene()
        snap.mode = "oddball"
        self.assertFalse(b.flag_fight_check(NOW, me, snap))

    def test_fights_then_goes_back_for_it(self):
        """Dropped: it fights him and is not after the flag; he dies: back for the flag at FLAG_BACK_SCORE; taken
        again: over, and no new drop for FLAG_FIGHT_AGAIN s."""
        b, me, man, snap = scene()
        self.assertTrue(b.flag_fight_check(NOW, me, snap))
        drop(b, me, snap, Vec(12.5, 0.3, 0.0))
        self.assertEqual(b.flag_fight_phase(NOW + 0.4, me, snap), "fight")
        scores = {}
        b.flag_fight_scores(NOW + 0.5, me, snap, scores)
        self.assertEqual(scores, {("fight", 2): botmod.FLAG_FIGHT_SCORE})
        man.alive = False
        scores = {("fight", 3): 2.9}
        b.flag_fight_scores(NOW + 2.0, me, snap, scores)
        self.assertEqual(scores[("objective", Vec(12.5, 0.3, 0.0))], botmod.FLAG_BACK_SCORE)
        self.assertGreater(botmod.FLAG_BACK_SCORE, scores[("fight", 3)])
        me.has_flag = True
        self.assertIsNone(b.flag_fight_phase(NOW + 3.0, me, snap))
        self.assertIsNone(b.flag_fight)
        man.alive = True
        later = NOW + 3.0 + botmod.FLAG_FIGHT_AGAIN
        for t in (NOW + 3.6, later + 0.2):
            b.per.losses = [(t - 0.4, 0.6), (t - 0.1, 0.6)]
            b.per.beliefs[2] = Belief(Vec(15, 0, 0), Vec(0, 0, 0), t, True, "eyes")
            self.assertEqual(b.flag_fight_check(t, me, snap), t > later, t - NOW)

    def test_man_lost_or_long_fight_goes_back(self):
        """The man unknown for FLAG_FIGHT_LOST s, or the fight past FLAG_FIGHT_HOLD: back for the flag."""
        b, me, man, snap = scene()
        b.flag_fight_check(NOW, me, snap)
        drop(b, me, snap)
        b.flag_fight_phase(NOW + 0.3, me, snap)
        self.assertEqual(b.flag_fight_phase(NOW + 0.3 + botmod.FLAG_FIGHT_LOST + 0.1, me, snap), "back")
        b, me, man, snap = scene()
        b.flag_fight_check(NOW, me, snap)
        drop(b, me, snap)
        b.flag_fight_phase(NOW + 0.3, me, snap)
        b.per.beliefs[2] = Belief(man.pos, Vec(0, 0, 0), NOW + 9.0, True, "eyes")
        self.assertEqual(b.flag_fight_phase(NOW + 0.3 + botmod.FLAG_FIGHT_HOLD + 0.1, me, snap), "back")

    def test_flag_gone_ends_it(self):
        """Back for it, but the flag went home (returned) or someone took it: over."""
        b, me, man, snap = scene()
        b.flag_fight_check(NOW, me, snap)
        drop(b, me, snap)
        b.flag_fight_phase(NOW + 0.3, me, snap)
        man.alive = False
        self.assertEqual(b.flag_fight_phase(NOW + 1.0, me, snap), "back")
        snap.flags[1] = FlagState(1, Vec(40, 0, 0), Vec(40, 0, 0), "home")
        self.assertIsNone(b.flag_fight_phase(NOW + 1.5, me, snap))

    def test_failed_drop_carries_on(self):
        """Still carrying FLAG_FIGHT_DROP_S after the tap: the drop did not take, it carries on."""
        b, me, man, snap = scene()
        b.flag_fight_check(NOW, me, snap)
        self.assertEqual(b.flag_fight_phase(NOW + 1.0, me, snap), "drop")
        self.assertIsNone(b.flag_fight_phase(NOW + botmod.FLAG_FIGHT_DROP_S + 0.1, me, snap))
        scores = {}
        b.flag_fight_scores(NOW + 2.0, me, snap, scores)
        self.assertNotIn(("fight", 2), scores)

    def test_second_tap_only_with_the_flag_in_hand(self):
        """The retap at FLAG_FIGHT_RETAP goes only while the weapon read still shows the flag: the gun in hand means
        it dropped (the carrier read lags), and another switch would only swap rifles."""
        b, me, man, snap = scene()
        b.flag_fight_check(NOW, me, snap)
        t = NOW + botmod.FLAG_FIGHT_RETAP + 0.1
        act = Action()
        b.flag_fight_press(t, me, act, "drop")
        self.assertTrue(act.cycle)
        me.weapon = "dmr"
        act = Action()
        b.flag_fight_press(t, me, act, "drop")
        self.assertFalse(act.cycle)
        act = Action()
        b.flag_fight_press(NOW + 0.5, me, act, "drop")
        self.assertFalse(act.cycle)

    def test_stockpile_too(self):
        """Stockpile: home is our goal; back for the loose flag it dropped, not one already in our goal."""
        b, me, man, snap = scene(mode="stockpile")
        self.assertTrue(b.flag_fight_check(NOW, me, snap))
        drop(b, me, snap, Vec(12.4, 0, 0), mode="stockpile")
        snap.obj_items.append(dict(pos=Vec(0.5, 0, 0), carrier=None, kind="stockpile_flag", team=8))
        b.flag_fight_phase(NOW + 0.3, me, snap)
        man.alive = False
        scores = {}
        b.flag_fight_scores(NOW + 1.0, me, snap, scores)
        self.assertEqual(scores, {("objective", Vec(12.4, 0, 0)): botmod.FLAG_BACK_SCORE})


class FlagFightInPlan(unittest.TestCase):
    """Through Bot.plan on open ground (test_h4_pickup_board's stand-in world): the tap reaches the action sent, and the
    flag at its feet is not taken again while it fights, only after."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_h4_pickup_board import Flat
        self.b, self.me, self.man, self.snap = scene()
        self.b.notes, self.b._terrain = [], Flat()
        self.b.T = lambda: self.b._terrain

    def tick(self, now, goal):
        self.b.goal, self.b.next_decide = goal, now + 99.0
        self.snap.time = now
        return self.b.plan(now, 1 / 30, self.snap, lambda a, c: True, lambda a, c, **k: c, [])

    def test_tap_then_no_retake_until_the_fight_ends(self):
        b, me, snap = self.b, self.me, self.snap
        self.assertTrue(b.flag_fight_check(NOW, me, snap))
        act = self.tick(NOW + 0.05, ("fight", 2))
        self.assertTrue(act.cycle)
        drop(b, me, snap, Vec(me.pos.x, me.pos.y, me.pos.z))          # lying at its feet
        for t in (NOW + 0.5, NOW + 3.0):
            b.per.beliefs[2] = Belief(self.man.pos, Vec(0, 0, 0), t, True, "eyes")
            act = self.tick(t, ("fight", 2))
            self.assertEqual(b.flag_fight_phase(t, me, snap), "fight")
            self.assertFalse(act.action, f"took the flag mid-fight at {t - NOW:.1f} s")
        self.man.alive = False                  # (the take goes whatever the goal: the stand-in world cannot walk one)
        act = self.tick(NOW + 3.5, ("fight", 2))
        self.assertEqual(b.flag_fight_phase(NOW + 3.5, me, snap), "back")
        self.assertTrue(act.action, "the fight over, the flag at its feet is taken")


if __name__ == "__main__":
    unittest.main()
