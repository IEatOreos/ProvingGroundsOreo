"""(custom, Nov 24, the owner) Aircraft hold fire: bots on foot below Demon / Mythic / Noble hold fire on an enemy
Banshee's or Falcon's crew until that aircraft has killed enough of their team (docs/AIRCRAFT_HOLD_FIRE_DESIGN.md)."""
import random
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import profiles
from brain.profiles import make_profile


def prof(tier):
    return make_profile(tier, "rusher", random.Random(3))


class AirHoldKills(unittest.TestCase):
    def test_each_difficulty(self):
        want = {"demon": 0, "noble": 0, "mythic": 0, "top": 1, "strong": 2, "tactician": 2, "blind": 2,
                "average": 3, "novice": 5}
        got = {t: profiles.air_hold_kills(prof(t)) for t in want}
        self.assertEqual(got, want)

    def test_scaling_shoots_at_once(self):
        self.assertEqual(profiles.air_hold_kills(replace(prof("top"), extra={"head_aim": 0.5})), 0)
        self.assertEqual(profiles.air_hold_kills(replace(prof("novice"), extra={"head_aim": 0.1})), 0)


class P:
    """A player as the snapshot keeps him (the fields the counter and the hold read)."""

    def __init__(s, id, team, vehicle=-1, alive=True, gunner_seat=False):
        s.id, s.team, s.vehicle, s.alive, s.gunner_seat = id, team, vehicle, alive, gunner_seat


class Snap:
    def __init__(s, players, vehicles=()):
        s.players, s.vehicles = list(players), [dict(v) for v in vehicles]

    def player(s, i):
        return next((p for p in s.players if p.id == i), None)


BANSHEE = dict(handle=7, kind="banshee", dead=False)
FALCON = dict(handle=9, kind="falcon", dead=False)
HOG = dict(handle=11, kind="warthog", dead=False)


def row(v, k, vt, kt, new=True):
    return dict(v=v, k=k, new=new, o=k, c=None, m=None, hits=[], vt=vt, kt=kt, vb=0, kb=1,
                vp=[0.0, 0.0, 0.0], kp=[5.0, 5.0, 8.0], gt=100, st=1)


class Counter(unittest.TestCase):
    def setUp(self):
        import air_kills
        self.A = air_kills.AirKills()

    def test_pilot_kill_counts(self):
        snap = Snap([P(1, 0, vehicle=7), P(2, 1)], [BANSHEE])
        self.assertTrue(self.A.add(1, 1, snap))
        self.assertEqual(self.A.table(), {7: {1: 1}})

    def test_falcon_gunner_counts_to_falcon(self):
        snap = Snap([P(1, 0, vehicle=9, gunner_seat=True), P(2, 1)], [FALCON])
        self.A.add(1, 1, snap)
        self.A.add(1, 1, snap)
        self.assertEqual(self.A.table(), {9: {1: 2}})

    def test_ground_vehicle_and_foot_not_counted(self):
        snap = Snap([P(1, 0, vehicle=11), P(3, 0), P(2, 1)], [HOG])
        self.assertFalse(self.A.add(1, 1, snap))
        self.assertFalse(self.A.add(3, 1, snap))
        self.assertFalse(self.A.add(None, 1, snap))
        self.assertEqual(self.A.table(), {})

    def test_row_kill_counts_person_victim(self):
        snap = Snap([P(1, 0, vehicle=7), P(2, 1)], [BANSHEE])
        self.assertTrue(self.A.row(row(2, 1, 1, 0), snap, True))       # (vb 0: a person died)
        self.assertEqual(self.A.table(), {7: {1: 1}})

    def test_row_betrayal_and_death_not_counted(self):
        snap = Snap([P(1, 0, vehicle=7), P(2, 0), P(3, 1)], [BANSHEE])
        self.assertFalse(self.A.row(row(2, 1, 0, 0), snap, True))      # his own team: a betrayal
        self.assertFalse(self.A.row(row(3, None, 1, None), snap, True))  # nobody credited: a death
        self.assertEqual(self.A.table(), {})

    def test_trade_uses_before(self):
        snap = Snap([P(1, 0, vehicle=-1, alive=False), P(2, 1)], [BANSHEE])
        before = {1: P(1, 0, vehicle=7)}
        self.assertTrue(self.A.add(1, 1, snap, before))
        self.assertEqual(self.A.table(), {7: {1: 1}})

    def test_prune_on_dead_or_gone(self):
        snap = Snap([P(1, 0, vehicle=7), P(4, 0, vehicle=9), P(2, 1)], [BANSHEE, FALCON])
        self.A.add(1, 1, snap)
        self.A.add(4, 1, snap)
        self.A.prune(Snap(snap.players, [dict(BANSHEE, dead=True), FALCON]))
        self.assertEqual(self.A.table(), {9: {1: 1}})
        self.A.prune(Snap(snap.players, []))
        self.assertEqual(self.A.table(), {})
        new = Snap([P(1, 0, vehicle=8), P(2, 1)], [dict(BANSHEE, handle=8)])
        self.A.add(1, 1, new)
        self.assertEqual(self.A.table(), {8: {1: 1}})

    def test_table_is_a_copy(self):
        snap = Snap([P(1, 0, vehicle=7), P(2, 1)], [BANSHEE])
        self.A.add(1, 1, snap)
        t = self.A.table()
        t[7][1] = 99
        self.assertEqual(self.A.table(), {7: {1: 1}})


class Hold(unittest.TestCase):
    """Bot.air_held and where it leaves the aircraft's crew out: pick_target, the fight scores."""

    def setUp(self):
        from brain.core import PlayerState, Snapshot, Vec
        self.Vec, self.Snapshot = Vec, Snapshot
        self.me = PlayerState(0, 0, "bot", Vec())
        self.pilot = PlayerState(1, 1, "pilot", Vec(10, 0, 5), vehicle=7)
        self.gunner = PlayerState(3, 1, "gunner", Vec(12, 0, 5), vehicle=9, gunner_seat=True)
        self.man = PlayerState(2, 1, "man", Vec(6, 0, 0))

    def bot(self, tier, now=50.0, prof_=None):
        from brain.bot import Belief, Bot
        b = Bot(0, 0, prof_ or prof(tier), {"name": "reach_test"}, random.Random(5))
        for p in (self.pilot, self.gunner, self.man):
            b.per.beliefs[p.id] = Belief(p.pos, self.Vec(), now, True, "eyes")
        return b

    def snap(self, table, now=50.0):
        s = self.Snapshot(now, [self.me, self.pilot, self.gunner, self.man],
                          vehicles=[dict(BANSHEE, pos=(10, 0, 5)), dict(FALCON, pos=(12, 0, 5))])
        s.air_kills = table
        return s

    def test_no_table_no_hold(self):
        b = self.bot("top")
        self.assertFalse(b.air_held(50.0, self.me, self.snap(None), 1))

    def test_legendary_waits_for_one_kill(self):
        b = self.bot("top")
        self.assertTrue(b.air_held(50.0, self.me, self.snap({}), 1))
        self.assertTrue(b.air_held(50.0, self.me, self.snap({7: {1: 3}}), 1))    # (kills on the other team only)
        self.assertFalse(b.air_held(50.0, self.me, self.snap({7: {0: 1}}), 1))

    def test_normal_waits_for_three(self):
        b = self.bot("average")
        self.assertTrue(b.air_held(50.0, self.me, self.snap({7: {0: 2}}), 1))
        self.assertFalse(b.air_held(50.0, self.me, self.snap({7: {0: 3}}), 1))

    def test_falcon_gunner_held_by_his_falcon(self):
        b = self.bot("strong")
        self.assertTrue(b.air_held(50.0, self.me, self.snap({7: {0: 5}, 9: {0: 1}}), 3))
        self.assertFalse(b.air_held(50.0, self.me, self.snap({9: {0: 2}}), 3))

    def test_man_on_foot_never_held(self):
        self.assertFalse(self.bot("novice").air_held(50.0, self.me, self.snap({}), 2))

    def test_demon_noble_mythic_never_held(self):
        for t in ("demon", "noble", "mythic"):
            self.assertFalse(self.bot(t).air_held(50.0, self.me, self.snap({}), 1), t)

    def test_scaling_never_held(self):
        b = self.bot("top", prof_=replace(prof("top"), extra={"head_aim": 0.5}))
        self.assertFalse(b.air_held(50.0, self.me, self.snap({}), 1))

    def test_in_vehicle_never_held(self):
        from brain.core import PlayerState
        me = PlayerState(0, 0, "bot", self.Vec(), vehicle=11)
        self.assertFalse(self.bot("novice").air_held(50.0, me, self.snap({}), 1))

    def test_self_defence(self):
        b = self.bot("average")
        b.per.attacker_id, b.per.attacker_t = 3, 49.0         # the Falcon's gunner hit us 1 s ago
        self.assertFalse(b.air_held(50.0, self.me, self.snap({}), 3))
        self.assertTrue(b.air_held(50.0, self.me, self.snap({}), 1))   # (the Banshee's pilot: another aircraft)
        b.per.attacker_t = 46.5                                 # 3.5 s ago: held again
        self.assertTrue(b.air_held(50.0, self.me, self.snap({}), 3))

    def test_pick_target_skips_held(self):
        b = self.bot("top")
        snap = self.snap({})
        self.assertEqual(b.pick_target(50.0, self.me, snap, [1, 2]), 2)
        self.assertIsNone(b.pick_target(50.0, self.me, snap, [1]))
        self.assertEqual(b.pick_target(50.0, self.me, self.snap({7: {0: 1}}), [1]), 1)

    def test_decide_with_only_held_crew_in_view(self):
        b = self.bot("top")
        b.per.recognized = {1}
        for k in (2, 3):
            del b.per.beliefs[k]
        goal = b.decide(50.0, self.me, self.snap({}))
        self.assertNotEqual(goal, ("fight", 1))
        self.assertNotIn(("fight", 1), b.last_scores)
        self.assertEqual(b.decide(50.0, self.me, self.snap({7: {0: 1}})), ("fight", 1))

    def test_scores_drop_held_fight(self):
        b = self.bot("top")
        scores = {("fight", 1): 2.0, ("fight", 2): 1.0, ("hunt", self.Vec(1, 1, 0)): 0.5}
        b.air_hold_scores(50.0, self.me, self.snap({}), scores)
        self.assertEqual(set(scores), {("fight", 2), ("hunt", self.Vec(1, 1, 0))})


class Live(unittest.TestCase):
    """tools/live_bots.py: the fallback count from bots' deaths, and the table handed to the bots."""

    def setUp(self):
        import air_kills
        import live_bots
        from brain.bot import Belief, Bot
        from brain.core import PlayerState, Snapshot, Vec
        self.lb, self.A = live_bots, air_kills.AirKills()
        self.bot = Bot(5, 1, prof("average"), {"name": "reach_test"}, random.Random(5))
        self.bot.goal = ("fight", 1)                     # (fighting the pilot when it died: the killer it credits)
        self.bot.per.beliefs[1] = Belief(Vec(10, 0, 5), Vec(), 1.0, True, "eyes")
        pilot = PlayerState(1, 0, "pilot", Vec(10, 0, 5), vehicle=7)
        self.before = {5: PlayerState(5, 1, "bot", Vec()), 1: pilot}
        self.snap = Snapshot(2.0, [PlayerState(5, 1, "bot", Vec(), alive=False), pilot],
                             vehicles=[dict(BANSHEE, pos=(10, 0, 5))])

    def test_events_fallback_counts_when_no_record(self):
        self.lb.events({5: self.bot}, {}, self.before, self.snap, 2.0, air=self.A, record=False)
        self.assertEqual(self.A.table(), {7: {1: 1}})

    def test_events_no_double_count_with_record(self):
        self.lb.events({5: self.bot}, {}, self.before, self.snap, 2.0, air=self.A, record=True)
        self.assertEqual(self.A.table(), {})

    def test_air_table_off_without_teams(self):
        self.A.add(1, 1, self.snap)
        self.assertIsNone(self.lb.air_table(self.A, self.snap, False))
        self.assertEqual(self.lb.air_table(self.A, self.snap, True), {7: {1: 1}})
        self.snap.vehicles = []
        self.assertEqual(self.lb.air_table(self.A, self.snap, True), {})     # (destroyed: gone from the list)


if __name__ == "__main__":
    unittest.main()
