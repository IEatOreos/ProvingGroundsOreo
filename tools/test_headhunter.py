"""(custom, Nov 12) Reach Headhunter: skull counts and the live drop point (brain/headhunter.py), and the director's
use of them (hh_bankers, mode_slots). The owner: "see if there is code for headhunter in halo reach, and if not try and
start making the bots play that mode", then "Yes, build it" (skull counting and banking)."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import headhunter as HH, modes                         # noqa: E402
from brain.bot import Bot, Order                                  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec                 # noqa: E402
from brain.director import Director                               # noqa: E402
from brain.profiles import make_profile                           # noqa: E402

A, B = Vec(0, 0, 0), Vec(40, 0, 0)          # two drop points
ZONES = [(A, 2.0), (B, 2.0)]


def pl(pid, team, at, alive=True):
    return PlayerState(pid, team, f"p{pid}", at, alive=alive)


def snap(t, players, score=None, mode="headhunter"):
    return Snapshot(t, players, mode=mode, score=dict(score if score is not None else {0: 0, 1: 0}))


class CountTests(unittest.TestCase):
    def setUp(self):
        self.h = HH.Skulls()

    def test_a_skull_gone_under_a_man_is_his(self):
        sk = Vec(20, 5, 0)
        self.h.update(0.0, snap(0.0, [pl(1, 0, Vec(10, 5, 0)), pl(2, 1, Vec(30, 5, 0))]), ZONES, [sk])
        self.h.update(0.25, snap(0.25, [pl(1, 0, Vec(20.4, 5, 0)), pl(2, 1, Vec(30, 5, 0))]), ZONES, [])
        self.assertEqual(self.h.held, {1: 1})

    def test_a_skull_gone_with_nobody_by_is_nobodys(self):
        self.h.update(0.0, snap(0.0, [pl(1, 0, Vec(10, 5, 0))]), ZONES, [Vec(20, 5, 0)])
        self.h.update(0.25, snap(0.25, [pl(1, 0, Vec(10, 5, 0))]), ZONES, [])
        self.assertEqual(self.h.held, {})

    def test_a_rolling_skull_is_the_same_skull(self):
        self.h.update(0.0, snap(0.0, [pl(1, 0, Vec(20.5, 5, 0))]), ZONES, [Vec(20, 5, 0)])
        self.h.update(0.25, snap(0.25, [pl(1, 0, Vec(20.5, 5, 0))]), ZONES, [Vec(20.4, 5, 0)])
        self.assertEqual(self.h.held, {})

    def test_death_drops_them_all(self):
        self.h.held = {1: 4}
        self.h.update(0.0, snap(0.0, [pl(1, 0, Vec(), alive=False)]), ZONES, [])
        self.assertNotIn(1, self.h.held)

    def test_a_team_score_rise_in_a_drop_point_banks_and_marks_it_live(self):
        self.h.held = {1: 3}
        self.h.update(0.0, snap(0.0, [pl(1, 0, Vec(40.5, 0, 0))]), ZONES, [])
        self.h.update(0.5, snap(0.5, [pl(1, 0, Vec(40.5, 0, 0))], {0: 3, 1: 0}), ZONES, [])
        self.assertEqual(self.h.held[1], 0)
        self.assertEqual(self.h.live[0], 1)
        self.assertEqual(self.h.bank_zone(Vec(1, 0, 0), 1.0), B)       # the live one, though A is nearer

    def test_skulls_and_no_score_in_one_mark_it_dead(self):
        self.h.held = {1: 2}
        for k in range(16):                                           # 4 s in A, the score still
            self.h.update(k * 0.25, snap(k * 0.25, [pl(1, 0, Vec(0.5, 0, 0))]), ZONES, [])
        self.assertEqual(self.h.held[1], 2)
        self.assertGreater(self.h.dead.get(0, 0.0), 4.0)
        self.assertEqual(self.h.bank_zone(Vec(1, 0, 0), 5.0), B)
        self.assertEqual(self.h.bank_zone(Vec(1, 0, 0), 5.0 + HH.DEAD_FOR), A)   # tried again later

    def test_a_score_that_never_moves_is_no_signal(self):
        self.h.held = {1: 2}
        self.h.dead = {1: 99.0}                                       # B already found dead
        for k in range(16):                                           # then 4 s in A, the score still
            self.h.update(k * 0.25, snap(k * 0.25, [pl(1, 0, Vec(0.5, 0, 0))]), ZONES, [])
        self.assertEqual(self.h.held[1], 0)                           # taken as banked
        self.assertEqual(self.h.dead, {})

    def test_all_found_dead_means_the_nearest(self):
        self.h.zones = ZONES
        self.h.dead = {0: 99.0, 1: 99.0}
        self.assertEqual(self.h.bank_zone(Vec(35, 0, 0), 10.0), B)

    def test_free_for_all_with_no_score_read_banks_after_the_wait(self):
        self.h.held = {5: 2}                                          # team 5: no score of his is read
        for k in range(14):
            self.h.update(k * 0.25, snap(k * 0.25, [pl(5, 5, Vec(0.5, 0, 0))]), ZONES, [])
        self.assertEqual(self.h.held[5], 0)
        self.assertEqual(self.h.dead, {})


class ShouldBankTests(unittest.TestCase):
    def test_the_rules(self):
        self.assertFalse(HH.should_bank(0, 1.0))
        self.assertTrue(HH.should_bank(5, 200.0))
        self.assertTrue(HH.should_bank(3, 40.0))
        self.assertFalse(HH.should_bank(3, 60.0))
        self.assertTrue(HH.should_bank(1, 10.0))
        self.assertFalse(HH.should_bank(2, 30.0))
        self.assertTrue(HH.should_bank(2, 100.0, need=2))             # a winning bank


class FakeLive:
    def __init__(self):
        self.loose = []

    def loose_named(self, name):
        return [(q.x, q.y, q.z) for q in self.loose]


class WatchTests(unittest.TestCase):
    def test_the_watch_fills_the_counts(self):
        w = modes.Watch("headhunter", {})
        w.lay = {"drop_point": [(A, 2.0, 8), (B, 2.0, 8)]}
        live = FakeLive()
        live.loose = [Vec(20, 5, 0)]
        s0 = snap(0.0, [pl(1, 0, Vec(10, 5, 0))])
        w.update(live, s0, 0.0, raw=[{}])
        live.loose = []
        s1 = snap(0.5, [pl(1, 0, Vec(20.2, 5, 0))])
        w.update(live, s1, 0.5, raw=[{}])
        self.assertEqual(s1.skulls_held, {1: 1})
        self.assertIs(s1.hh, w.hh)
        self.assertEqual(len(s1.obj_zones), 2)


def bot(pid, tier="strong"):
    b = Bot(pid, 0, make_profile(tier, "flanker", random.Random(pid)), {"name": "reach_30_settlement", "items": []},
            random.Random(pid))
    b.order = Order("mid", Vec())
    return b


def director(bots):
    d = Director.__new__(Director)
    d.team = d.side = 0
    d.roles = {}
    d.bots = {b.id: b for b in bots}
    d.map = dict(points={"mid": Vec(20, 0, 0)})
    d.event = lambda *a, **k: None
    d.overlooks = lambda q, n: [q + Vec(3, 0, 0)] * n
    d.slayer_slots = lambda now, snap, n: [("hunter", Vec(), "aggression")] * n
    return d


class DirectorTests(unittest.TestCase):
    def scene(self, held, me_at=Vec(10, 0, 0)):
        bots = [bot(1), bot(2)]
        h = HH.Skulls()
        h.zones, h.held = ZONES, dict(held)
        sn = snap(10.0, [pl(1, 0, me_at), pl(2, 0, Vec(30, 0, 0)), pl(9, 1, Vec(25, 5, 0))])
        sn.hh, sn.skulls_held = h, dict(held)
        sn.obj_zones = [(A, 2.0, -1), (B, 2.0, -1)]
        return director(bots), bots, sn

    def test_a_bot_carrying_three_by_a_drop_point_banks(self):
        d, bots, sn = self.scene({1: 3})
        got = d.hh_bankers(10.0, sn, bots)
        self.assertEqual([(b.id, z) for b, z in got], [(1, A)])

    def test_one_skull_far_from_a_drop_point_is_kept(self):
        d, bots, sn = self.scene({1: 1}, me_at=Vec(20, 0, 0))         # 20 u from both
        self.assertEqual(d.hh_bankers(10.0, sn, bots), [])

    def test_not_in_other_modes(self):
        d, bots, sn = self.scene({1: 5})
        sn.mode = "slayer"
        self.assertEqual(d.hh_bankers(10.0, sn, bots), [])

    def test_an_enemy_seen_with_skulls_is_hunted_first(self):
        d, bots, sn = self.scene({9: 4})
        bots[0].per.beliefs[9] = SimpleNamespace(pos=Vec(25, 5, 0), t=9.0)
        slots = d.mode_slots(10.0, sn, 4)
        self.assertEqual(slots[0][:2], ("hunter", Vec(25, 5, 0)))
        self.assertEqual(slots[1][:2], ("hunter", Vec(25, 5, 0)))

    def test_an_enemy_unseen_is_not(self):
        d, bots, sn = self.scene({9: 4})
        slots = d.mode_slots(10.0, sn, 4)
        self.assertNotEqual(slots[0][:2], ("hunter", Vec(25, 5, 0)))


class MoveTimeTests(unittest.TestCase):
    """(Nov 12, second pass) live Launch Station 20261112-223426, drop points moving every 30 s: the bankers ran to the
    last scoring drop point 75 s after it had moved (LIVE_KEEP was 90 s)."""

    def live_at(self, h, t):
        h.zones, h.live = ZONES, (1, t)

    def test_the_live_drop_point_is_kept_its_movement_time(self):
        h = HH.Skulls(30)
        self.live_at(h, 0.0)
        self.assertEqual(h.bank_zone(Vec(1, 0, 0), 25.0), B)
        self.assertEqual(h.bank_zone(Vec(1, 0, 0), 35.0), A)          # moved on by now: the nearest

    def test_never_moves_keeps_it(self):
        h = HH.Skulls(0)
        self.live_at(h, 0.0)
        self.assertEqual(h.bank_zone(Vec(1, 0, 0), 900.0), B)

    def test_not_read_is_thirty_seconds(self):
        h = HH.Skulls()
        self.assertEqual(h.live_keep, 30.0)
        self.assertEqual(h.dead_for, 30.0)

    def test_a_dead_drop_point_is_skipped_no_longer_than_a_move(self):
        h = HH.Skulls(15)
        h.held = {1: 2}
        for k in range(16):
            h.update(k * 0.25, snap(k * 0.25, [pl(1, 0, Vec(0.5, 0, 0))]), ZONES, [])
        self.assertAlmostEqual(h.dead[0], 3.0 + 15.0, delta=0.3)

    def test_the_variant_option(self):
        from brain import mvar
        opt = lambda v: {"options": [{"name": "Drop point movement time", "value": v, "number": 7}]}
        self.assertEqual(mvar.drop_point_move(opt("30 seconds")), 30)
        self.assertEqual(mvar.drop_point_move(opt("1 minute")), 60)
        self.assertEqual(mvar.drop_point_move(opt("never")), 0)
        self.assertEqual(mvar.drop_point_move(opt("odd")), 7)
        self.assertIsNone(mvar.drop_point_move({"options": [{"name": "Drop Points", "value": "2 points"}]}))
        self.assertIsNone(mvar.drop_point_move(None))

    def test_the_watch_passes_it_on(self):
        w = modes.Watch("headhunter", {})
        w.lay = {"drop_point": [(A, 2.0, 8), (B, 2.0, 8)]}
        w.hh_move = 45
        w.update(FakeLive(), snap(0.0, [pl(1, 0, Vec(10, 5, 0))]), 0.0, raw=[{}])
        self.assertEqual(w.hh.live_keep, 45.0)


class MoreTeamScoreTests(unittest.TestCase):
    """(Nov 12, second pass) four-team Headhunter: teams 2 and 3 had no score read (live.LiveReach.more_team_scores)."""

    def read(self, values, teams_on=(0, 1, 2, 3), team_game=True, limit=50):
        import struct
        from brain.live import LiveReach
        fake = SimpleNamespace(REACH_TEAMS_MAX=LiveReach.REACH_TEAMS_MAX, variant=lambda: {"teams": team_game})
        b = b"".join(struct.pack("<ii", v, 0) for v in values)
        return LiveReach.more_team_scores(fake, b, [{"team": t} for t in teams_on], limit)

    def test_teams_two_and_three(self):
        self.assertEqual(self.read([49, 17, 22, 30, 0, 0, 0, 0]), {2: 22, 3: 30})

    def test_two_teams_add_nothing(self):
        self.assertEqual(self.read([5, 6, 99, 99, 0, 0, 0, 0], teams_on=(0, 1)), {})

    def test_free_for_all_adds_nothing(self):
        self.assertEqual(self.read([5, 6, 7, 8, 0, 0, 0, 0], team_game=False), {})

    def test_a_bad_read_is_left_out(self):
        self.assertEqual(self.read([5, 6, 7, -9999, 0, 0, 0, 0]), {2: 7})


class BankOverHuntTests(unittest.TestCase):
    """(Nov 12, second pass) a banker with skulls hunted instead (objective 0.7-1.7 against a hunt's 3.16): live Launch
    Station 20261112-223426, a bot with 13-16 skulls round the live drop point 20 s, died with them."""

    @classmethod
    def setUpClass(cls):
        from brain.maps import load_map
        cls.map = load_map("reach_cex_headlong")

    def decide(self, skulls, foe_seen=False, at_zone=True):
        from brain.bot import Belief
        b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), self.map, random.Random(5))
        me = PlayerState(0, 0, "bot", Vec(-27.3, 14.6, 7.6), weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        zone = me.pos + Vec(18, 0, 0)
        foe = PlayerState(1, 1, "foe", me.pos + Vec(0, -14, 0), weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        sn = Snapshot(100.0, [me, foe], mode="headhunter")
        sn.obj_zones = [(zone if at_zone else zone + Vec(9, 9, 0), 2.0, -1)]
        sn.skulls_held = {0: skulls} if skulls else {}
        b.order = Order("runner", zone)
        b.per.beliefs[1] = Belief(foe.pos, Vec(), 99.8, foe_seen, "eyes" if foe_seen else "radar")
        if foe_seen:
            b.per.recognized.add(1)
            b.per.last_seen[1] = 100.0
        return b.decide(100.0, me, sn)[0]

    def test_no_skulls_does_something_else(self):
        self.assertNotEqual(self.decide(0), "objective")              # (a gun on this map, or the hunt)

    def test_one_skull_to_the_drop_point_banks(self):
        self.assertEqual(self.decide(1), "objective")

    def test_a_runner_for_a_loose_skull_is_not_a_banker(self):
        self.assertNotEqual(self.decide(4, at_zone=False), "objective")

    def test_three_skulls_bank_past_a_man_in_view(self):
        self.assertEqual(self.decide(3, foe_seen=True), "objective")

    def test_not_in_other_modes(self):
        b = Bot(0, 0, make_profile("top", "rusher", random.Random(3)), self.map, random.Random(5))
        me = PlayerState(0, 0, "bot", Vec(-27.3, 14.6, 7.6), weapon="dmr", weapons=["dmr"], ammo=[45], mag=[15])
        sn = Snapshot(100.0, [me], mode="slayer")
        sn.obj_zones, sn.skulls_held = [(me.pos + Vec(18, 0, 0), 2.0, -1)], {0: 5}
        b.order = Order("runner", me.pos + Vec(18, 0, 0))
        b.decide(100.0, me, sn)                                       # (no headhunter boost: just no crash)


if __name__ == "__main__":
    unittest.main()
