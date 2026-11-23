"""(custom, Nov 18) Reach Assault with one bomb (Neutral Bomb, One Bomb): its carrier drops it to fight by the CTF rule
(Bot.flag_fight_*, Bot.single_bomb), and in every Assault a planter within PLANT_HOLD_R of its goal does nothing but
plant (Bot.plant_hold, Bot.plant_stay). The owner: "Make it to where the bomb planter doesnt leave the bomb site if
theyre planting or within 4 units of planting to avoid a fight. That should be the only priority"."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot as botmod                                     # noqa: E402
from brain import profiles                                          # noqa: E402
from brain.bot import Belief, Bot, Order                            # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec           # noqa: E402

GOAL = Vec(0.0, 0.0, 0.0)         # the enemy goal we plant on
AT = Vec(12.0, 0.0, 0.0)
NOW = 100.0


def scene(variant="neutral", at=AT, game_map="reach_45_aftship", lost=(0.6, 0.6), hp=(0.0, 0.8),
          man_at=Vec(15.0, 0.0, 0.0)):
    """Team 0's bomb carrier, hurt by man 2 (team 1). variant: neutral (one bomb, team 8, both goals), one (One Bomb:
    the bomb team 0's, only team 1's goal), multi (two bombs, two goals)."""
    b = Bot(1, 0, profiles.make_profile("top", "rusher", random.Random(1)), dict(name=game_map))
    me = PlayerState(1, 0, "carrier", at)
    me.has_flag, me.weapon, me.weapons = True, "unknown", ["dmr", "assault_rifle"]
    me.shield, me.health, me.vehicle = hp[0], hp[1], -1
    man = PlayerState(2, 1, "man", man_at)
    snap = Snapshot(NOW, [me, man], mode="assault")
    bomb = dict(pos=at, carrier=1, kind="bomb", team=8 if variant == "neutral" else 0, armed=None)
    if variant == "one":
        snap.obj_goals, snap.obj_items = {1: [GOAL]}, [bomb]
    else:
        snap.obj_goals, snap.obj_items = {0: [Vec(40, 0, 0)], 1: [GOAL]}, [bomb]
    if variant == "multi":
        snap.obj_items.append(dict(pos=Vec(40, 0, 0), carrier=None, kind="bomb", team=1, armed=None))
    b.order = Order("runner", GOAL)
    b.per.beliefs[2] = Belief(man_at, Vec(0, 0, 0), NOW, True, "eyes")
    b.per.recognized.add(2)
    b.per.losses = [(NOW - 0.6 + 0.3 * k, x) for k, x in enumerate(lost)]
    return b, me, man, snap


def drop(me, snap, at):
    me.has_flag, me.weapon = False, "dmr"
    snap.obj_items[0] = dict(snap.obj_items[0], pos=at, carrier=None)


class BombFight(unittest.TestCase):
    def test_neutral_and_one_bomb_drop_to_fight(self):
        for variant in ("neutral", "one"):
            b, me, man, snap = scene(variant)
            self.assertTrue(Bot.single_bomb(snap), variant)
            scores = {("objective", GOAL): 3.0}
            b.flag_fight_scores(NOW, me, snap, scores)
            self.assertEqual(scores.get(("fight", 2)), botmod.FLAG_FIGHT_SCORE, variant)
            act = Action(action=True)
            b.flag_fight_press(NOW, me, act, b.flag_fight_phase(NOW, me, snap))
            self.assertTrue(act.cycle, variant)

    def test_two_bombs_and_other_games_unchanged(self):
        b, me, man, snap = scene("multi")
        self.assertFalse(Bot.single_bomb(snap))
        self.assertFalse(b.flag_fight_check(NOW, me, snap))
        b, me, man, snap = scene(game_map="h3_guardian")
        self.assertFalse(b.flag_fight_check(NOW, me, snap))

    def test_back_for_the_bomb_not_an_armed_one(self):
        b, me, man, snap = scene()
        self.assertTrue(b.flag_fight_check(NOW, me, snap))
        drop(me, snap, Vec(12.4, 0, 0))
        b.flag_fight_phase(NOW + 0.3, me, snap)
        man.alive = False
        scores = {}
        b.flag_fight_scores(NOW + 1.0, me, snap, scores)
        self.assertEqual(scores, {("objective", Vec(12.4, 0, 0)): botmod.FLAG_BACK_SCORE})
        snap.obj_items[0]["armed"] = 1          # (armed on a goal: not ours to take again)
        self.assertIsNone(b.flag_dropped_at(me, snap, Vec(12, 0, 0)))


class PlantHold(unittest.TestCase):
    def test_within_four_units_only_the_plant(self):
        """3.5 u from the goal, shot and a man close: every other score goes, a drop to fight is never made."""
        b, me, man, snap = scene(at=Vec(3.5, 0, 0), man_at=Vec(5.0, 0, 0))
        scores = {("fight", 2): 3.4, ("retreat", Vec(9, 9, 0)): 3.3, ("objective", GOAL): 3.0}
        b.flag_fight_scores(NOW, me, snap, scores)
        self.assertIsNone(getattr(b, "flag_fight", None))
        self.assertTrue(b.plant_hold(NOW, me, snap, scores))
        self.assertEqual(scores, {("objective", GOAL): botmod.PLANT_HOLD_SCORE})

    def test_not_on_the_floor_under_a_roof_goal(self):
        """(Nov 23) The goal on a roof 3.4 u up, the carrier on the floor right under it (Powerhouse): not planting, it
        is still on its way up; on the roof by it, planting."""
        b, me, man, snap = scene(at=Vec(1.8, 0.6, -3.4))
        self.assertIsNone(b.plant_point(me, snap))
        b, me, man, snap = scene(at=Vec(1.8, 0.6, 0.0))
        self.assertEqual(b.plant_point(me, snap), GOAL)

    def test_every_assault_every_game(self):
        for kw in (dict(variant="multi"), dict(game_map="h3_guardian")):
            b, me, man, snap = scene(at=Vec(2.0, 0, 0), **kw)
            self.assertEqual(b.plant_point(me, snap), GOAL, kw)

    def test_not_past_four_units_nor_without_the_bomb(self):
        b, me, man, snap = scene(at=Vec(4.5, 0, 0))
        scores = {("fight", 2): 3.4}
        self.assertFalse(b.plant_hold(NOW, me, snap, scores))
        self.assertEqual(scores, {("fight", 2): 3.4})
        b, me, man, snap = scene(at=Vec(2.0, 0, 0))
        me.has_flag = False
        self.assertIsNone(b.plant_point(me, snap))
        b, me, man, snap = scene(at=Vec(2.0, 0, 0))
        snap.mode = "ctf"
        self.assertIsNone(b.plant_point(me, snap))

    def test_a_drop_under_way_is_called_off(self):
        """Tapping to drop 5 u out, then within 4 u: the drop stops and it plants."""
        b, me, man, snap = scene(at=Vec(5.0, 0, 0), man_at=Vec(7.0, 0, 0))
        self.assertTrue(b.flag_fight_check(NOW, me, snap))
        me.pos = Vec(3.8, 0, 0)
        b.plant_hold(NOW + 0.2, me, snap, {})
        self.assertIsNone(b.flag_fight)
        act = Action()
        b.flag_fight_press(NOW + 0.2, me, act, b.flag_fight_phase(NOW + 0.2, me, snap))
        self.assertFalse(act.cycle)

    def test_plant_stay_puts_the_walk_back(self):
        b, me, man, snap = scene(at=Vec(2.0, 0, 0))
        b.notes = []
        act = Action(yaw=0.5, forward=1.0)
        kept = (0.5 + math.atan2(0.0, 1.0), 1.0, False)
        act.yaw, act.forward, act.strafe = 1.2, -1.0, 0.0      # a frag's step back, the view turned to a man
        b.plant_stay(me, snap, act, kept)
        self.assertAlmostEqual(math.atan2(act.strafe, act.forward) + act.yaw, 0.5, places=6)
        self.assertAlmostEqual(math.hypot(act.forward, act.strafe), 1.0, places=6)
        before = (act.forward, act.strafe)
        b.plant_stay(me, snap, act, None)
        self.assertEqual((act.forward, act.strafe), before)


class PlantInPlan(unittest.TestCase):
    """Through Bot.plan on open ground: within 4 u a fight goal is decided again at once and comes out the plant."""

    def tick(self, grenade=None):
        from test_h4_pickup_board import Flat
        b, me, man, snap = scene(at=Vec(3.0, 0, 0), man_at=Vec(4.5, 0, 0))
        b.notes, b._terrain = [], Flat()
        b.T = lambda: b._terrain
        walked = []

        def walk(me_, point, act, nav):          # (the stand-in world cannot walk: steer straight at it, noted)
            walked.append(point)
            b.steer(me_, point, act, True)
        b.move_to = walk
        b.nade_danger = lambda now, me_, snap_: grenade
        b.goal, b.next_decide = ("fight", 2), NOW + 99.0
        snap.time = NOW
        act = b.plan(NOW, 1 / 30, snap, lambda a, c: True, lambda a, c, **k: c, [])
        return b, act, walked

    def test_fight_goal_becomes_the_plant(self):
        b, act, walked = self.tick()
        self.assertEqual(b.goal, ("objective", GOAL))
        self.assertEqual(walked[-1], GOAL)
        self.assertFalse(act.cycle)

    def test_a_grenade_does_not_step_it_off(self):
        """A frag between it and the goal: enemy_grenade's step away is put back to the walk onto the goal."""
        _, calm, _ = self.tick()
        b, act, _ = self.tick(grenade=(Vec(2.0, 0.0, 0.0), "frag"))
        self.assertIn("bomb: planting, staying on the goal", b.notes)
        self.assertAlmostEqual(act.forward, calm.forward, places=6)
        self.assertAlmostEqual(act.strafe, calm.strafe, places=6)


if __name__ == "__main__":
    unittest.main()
