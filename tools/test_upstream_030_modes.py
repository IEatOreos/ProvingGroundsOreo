"""(custom, Nov 24) Upstream 0.3.0's game-mode, Invasion, director and live-read notes as ported into Project Noble
(logs/upstream_0.3.0_answers.md): each class is one note, its build stamp in the docstring."""
import struct
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from brain import live as livemod                                   # noqa: E402
from brain.core import Vec                                          # noqa: E402
from brain.live import NONE, LiveReach                              # noqa: E402
import test_reach_stockpile_flags as stock                          # noqa: E402


class FreedMidRead(unittest.TestCase):
    """#39 (build 20261119-0039): an object freed while its table is read (its header read fails) is skipped, not the
    whole tick."""

    def live(self):
        live, _ = stock.reach([(stock.FLAG, stock.STANDS[0]), (stock.FLAG, stock.STANDS[2])])
        freed = stock.OBJ                                 # the first flag's header

        class Gone(stock.Memory):
            def read(s, addr, n):
                return None if addr == freed else super().read(addr, n)

        g = Gone()
        g.buf = live.g.buf
        live.g = g
        return live

    def test_loose_named_skips_it(self):
        got = self.live().loose_named("flag")
        self.assertEqual([round(p[0], 2) for p in got], [round(stock.STANDS[2][0], 2)])

    def test_objects_skips_it(self):
        live = self.live()
        live._names = {}
        live._was_held = lambda h: False
        live._learn = lambda tag, pos: None
        got = live.objects(types=(2,))
        self.assertEqual(len(got), 1)
        self.assertAlmostEqual(got[0][3][0], stock.STANDS[2][0], places=3)

    def test_halo_4_guard_is_there(self):
        import inspect
        self.assertIn("if head is None", inspect.getsource(livemod.LiveH4F.objects))


class WreckStays(unittest.TestCase):
    """#80 (build 20261120-1802): a vehicle read alive and then at 0 health or below stays a wreck for the match, in every
    game; the game's destroyed bit is still read; a new reader (a new match) remembers no wreck."""

    def reader(self, cls, healths, dead_bit=False):
        r = object.__new__(cls)
        seq = iter(healths)
        r.vehicle_left = lambda h: next(seq)
        r.object = lambda h: 0x100
        r.g = type("G", (), {"read": lambda s, a, n: bytes([4 if dead_bit else 0])})()
        return r

    def test_burning_warthog_stays_a_wreck(self):
        for cls in (livemod.LiveH2, LiveReach, livemod.Live):
            r = self.reader(cls, [1.0, -0.8, 0.25, 1.0])
            got = [r.vehicle_dead(7) for _ in range(4)]
            self.assertEqual(got, [False, True, True, True], cls.__name__)

    def test_zero_from_the_start_is_no_wreck(self):
        r = self.reader(LiveReach, [0.0, 0.0, 0.0])
        self.assertEqual([r.vehicle_dead(7) for _ in range(3)], [False, False, False])

    def test_destroyed_bit_still_read(self):
        r = self.reader(LiveReach, [1.0, 1.0], dead_bit=True)
        self.assertTrue(r.vehicle_dead(7))

    def test_a_new_match_remembers_no_wreck(self):
        r = self.reader(LiveReach, [1.0, 0.0])
        r.vehicle_dead(7)
        self.assertTrue(r.vehicle_dead(7))
        fresh = self.reader(LiveReach, [1.0])
        self.assertFalse(fresh.vehicle_dead(7))
        self.assertFalse(hasattr(LiveReach, "_veh_wrecked"))     # per reader, never on the class


class FirefightDeadCovenant(unittest.TestCase):
    """#12 (build 20261114-0323, GitHub #29): a Covenant unit with the game's destroyed bit set is dead, whatever its
    damage field reads; bots kept shooting dead Grunts."""

    def units(self, bit=True):
        r = object.__new__(LiveReach)
        r.g = stock.Memory()
        rows = [(0.4, 0), (0.4, 4), (0.0, 0)]            # (body damage, damage flags): alive, dead by the bit, alive
        for k, (dmg, flags) in enumerate(rows):
            e, o = stock.ENTS + k * 0x18, stock.OBJ + k * stock.OBJ_SIZE
            struct.pack_into("<H", r.g.buf, e, 0x100 + k)
            r.g.buf[e + 4] = 0                            # a biped
            struct.pack_into("<Q", r.g.buf, e + 0x10, o)
            struct.pack_into("<2f", r.g.buf, o + 0x124, 0.0, dmg)
            struct.pack_into("<I", r.g.buf, o + 0x14, NONE)
            struct.pack_into("<I", r.g.buf, o + 0x1D0, NONE)
            r.g.buf[o + LiveReach.UNIT_TEAM] = 3          # Covenant
            r.g.buf[o + LiveReach.DEAD_AT] = flags
        r._array = lambda off: (stock.ENTS, len(rows), 0x18)
        r._vitals = lambda h, sd, bd, player=False: (1.0 - sd, 1.0 - bd)
        old = livemod.AI_DEAD_BIT
        livemod.AI_DEAD_BIT = bit
        try:
            return [d["index"] for d in r.ai_units([])]
        finally:
            livemod.AI_DEAD_BIT = old

    def test_dead_by_the_bit_is_left_out(self):
        self.assertEqual(self.units(), [1000, 1002])

    def test_switch_off_reads_the_damage_alone(self):
        self.assertEqual(self.units(bit=False), [1000, 1001, 1002])


class CEFreeForAll(unittest.TestCase):
    """#14 (build 20261114-0323): in a CE free for all every player is his own side (team = his slot), even with the
    lobby's red and blue left on; a team game keeps the lobby's teams."""

    def players(self, teams):
        r = object.__new__(livemod.Live)
        r.g = stock.Memory(0x10000)
        r.g.base = 0
        base, size = 0x1000, 0x200
        struct.pack_into("<i", r.g.buf, 0x8000 + 0x34, 1 if teams else 0)
        r.VARIANT = 0x8000
        for i, team in enumerate((0, 1, 1, 0)):
            p = base + i * size
            struct.pack_into("<H", r.g.buf, p, 0x100 + i)
            struct.pack_into("<I", r.g.buf, p + 0x64, NONE)
            struct.pack_into("<i", r.g.buf, p + 0x4C, team)
        r._array = lambda at: (base, 4, size)
        r.object = lambda h: 0
        r.tracker = lambda p: []
        return [d["team"] for d in r.players()]

    def test_free_for_all_every_player_his_own_side(self):
        self.assertEqual(self.players(teams=False), [0, 1, 2, 3])

    def test_team_game_keeps_the_lobby_teams(self):
        self.assertEqual(self.players(teams=True), [0, 1, 1, 0])


class KingOddballCEH2(unittest.TestCase):
    """#17 (build 20261114-1215): King and Oddball in CE and Halo 2 play a real score: the hill is the circle inside its
    corners (inscribed; Halo 2 at least 1.5 u), CE's limit in seconds, and team seconds in the hill / with the ball where
    the reader has no team score (held_tally), for CE and Halo 2 only. The KING_CALLS callouts line is not taken."""

    def setUp(self):
        import live_bots
        self.lb = live_bots
        self.saved = dict(live_bots.HELD), live_bots.HELD["pts"]
        live_bots.HELD.update(t=None, pts={})

    def tearDown(self):
        self.lb.HELD.update(self.saved[0])

    def test_inscribed_square(self):
        r = livemod.inscribed((0.0, 0.0, 0.0), [(2, 0), (0, 2), (-2, 0), (0, -2)])
        self.assertAlmostEqual(r, 2 * 0.7071, places=3)

    def test_halo_2_hill_radius(self):
        h2 = object.__new__(livemod.LiveH2)
        corners = [dict(type="King Hill 0", pos=p) for p in ((2.2, 0, 0), (0, 2.2, 0), (-2.2, 0, 0), (0, -2.2, 0))]
        tiny = [dict(type="King Hill 1", pos=p) for p in ((10.5, 0, 0), (9.5, 0, 0), (10, 0.5, 0))]
        h2.set_map({"netgame_flags": corners + tiny})
        self.assertAlmostEqual(h2._h2_hills[0][1], 2.2 * 0.7071, places=3)
        self.assertEqual(h2._h2_hills[1][1], 1.5)

    def test_other_games_keep_their_hill(self):
        self.assertEqual(livemod.LiveH3.HILL_R, 3.0)
        self.assertEqual(LiveReach.HILL_R, 3.0)
        self.assertEqual(livemod.LiveH2.HILL_R, 1.5)

    def test_ce_limit_in_seconds(self):
        r = object.__new__(livemod.Live)
        r.g = stock.Memory(0x10000)
        r.g.base = 0
        r.VARIANT, r.GAME_TICKS, r.SLAYER = 0x100, 0x400, 0x500
        for engine, want in ((4, 120), (3, 120), (2, 2), (1, 2)):
            struct.pack_into("<ii", r.g.buf, 0x100 + 0x30, engine, 1)
            struct.pack_into("<i", r.g.buf, 0x100 + 0x58, 2)
            self.assertEqual(r.match_state([])["limit"], want, engine)

    def snap(self, mode, where, carrier=None):
        from brain.core import PlayerState, Snapshot, Vec
        ps = [PlayerState(id=i, team=t, name=str(i), pos=Vec(*p)) for i, (t, p) in enumerate(where)]
        s = Snapshot(0.0, ps, {}, mode=mode)
        if mode == "king":
            s.hill, s.hill_r = Vec(0, 0, 0), 2.0
        else:
            s.ball_carrier = carrier
        return s

    def test_held_tally_king(self):
        lb = self.lb
        alone = self.snap("king", [(0, (0.5, 0, 0)), (1, (8, 0, 0))])
        both = self.snap("king", [(0, (0.5, 0, 0)), (1, (0, 1, 0))])
        lb.held_tally(alone, 0.0)
        lb.held_tally(alone, 1.0)
        lb.held_tally(both, 2.0)                       # contested: nobody scores
        self.assertEqual(lb.held_tally(alone, 3.0), {0: 2, 1: 0})

    def test_held_tally_oddball(self):
        lb = self.lb
        s = self.snap("oddball", [(0, (0, 0, 0)), (1, (5, 0, 0))], carrier=1)
        for t in range(4):
            got = lb.held_tally(s, float(t))
        self.assertEqual(got, {0: 0, 1: 3})

    def test_only_ce_and_halo_2_tally(self):
        import inspect
        self.assertIn("TALLIED = type(live) in (Live, LiveH2)", inspect.getsource(self.lb.main))
        self.assertFalse(self.lb.TALLIED)              # (set per match in main; off until then)


class CEH2Captures(unittest.TestCase):
    """#11, its live_bots part (build 20261114-0323): in CE and Halo 2 (no score read) a flag carried and next seen
    home, last carried within CAP_R of the other team's stand, is a capture (CAPS); a flag returned is not."""

    def setUp(self):
        import live_bots
        self.lb = live_bots
        self.saved = dict(live_bots.CAPS), dict(live_bots.CARRIED)
        live_bots.CAPS.clear()
        live_bots.CAPS.update({0: 0, 1: 0})
        live_bots.CARRIED.clear()

    def tearDown(self):
        self.lb.CAPS.clear()
        self.lb.CAPS.update(self.saved[0])
        self.lb.CARRIED.clear()
        self.lb.CARRIED.update(self.saved[1])

    def run_flags(self, carried_to):
        from brain.core import FlagState, Snapshot, Vec

        class D:
            def __init__(s):
                s.heard = []

            def report(s, now, who, what, where):
                s.heard.append(what)

        homes = {0: Vec(0, 0, 0), 1: Vec(50, 0, 0)}
        dirs = {0: D(), 1: D()}
        before = {0: "home", 1: "home"}

        def tick(state1, pos1):
            flags = {0: FlagState(0, homes[0], homes[0]), 1: FlagState(1, homes[1], pos1, state=state1)}
            self.lb.flag_events(dirs, before, Snapshot(0.0, [], flags, mode="ctf"), 0.0)
            before.update({t: f.state for t, f in flags.items()})

        tick("carried", Vec(30, 0, 0))
        tick("carried", carried_to)
        tick("home", homes[1])
        return dict(self.lb.CAPS), dirs

    def test_carried_to_the_stand_is_a_capture(self):
        caps, dirs = self.run_flags(Vec(1, 1, 0))
        self.assertEqual(caps, {0: 1, 1: 0})
        self.assertIn("scored", dirs[0].heard)

    def test_returned_far_from_the_stand_is_none(self):
        caps, _ = self.run_flags(Vec(25, 0, 0))
        self.assertEqual(caps, {0: 0, 1: 0})

    def test_score_uses_caps_only_where_tallied(self):
        import inspect
        self.assertIn('dict(CAPS) if TALLIED and snap.mode == "ctf"', inspect.getsource(self.lb.snapshot))
        self.assertIn("snap.score_live = bool(MATCH", inspect.getsource(self.lb.snapshot))   # (ours, Nov 13, kept)


class PullFirst(unittest.TestCase):
    """#3b (build 20261112-1632): their flag on its stand, our runner or escort within PULL_FIRST_R of it is not called
    into a vehicle (the horn, an empty gun) until the pull; one extra condition only, our seat and Demon rules kept."""

    def scene(self, role0, d0, d1, flag_state="home", mode="ctf"):
        from brain.core import FlagState
        from test_resource_calls import scene
        d, snap, bots, players = scene("warthog", distances=(d0, d1), tiers=("strong", "average"))
        d.side = 0
        d.roles[0] = role0
        snap.mode = mode
        at = Vec(d0, 0, 0)
        snap.flags = {0: FlagState(0, Vec(-80, 0, 0), Vec(-80, 0, 0)),
                      1: FlagState(1, at, at if flag_state == "home" else Vec(d0 + 3, 0, 0), state=flag_state)}
        snap.vehicles[0].update(occupied=True, riders=1)
        return d, snap, bots, players

    def honk(self, *a, **k):
        d, snap, bots, players = self.scene(*a, **k)
        snap.honks = [10]
        d.honk_orders(100, snap, bots, players)
        return [b.order.role for b in bots]

    def gun_call(self, *a, **k):
        d, snap, bots, players = self.scene(*a, **k)
        for name in ("honk_orders", "crew_orders", "rider_calls", "ferry_orders", "vehicle_jobs", "wheel_calls"):
            setattr(d, name, lambda *a: None)
        d.vehicle_orders(100, snap, bots)
        return [b.order.role for b in bots]

    def test_horn_skips_the_runner_by_their_flag(self):
        self.assertEqual(self.honk("runner", 2, 12), ["mid", "ride"])

    def test_horn_calls_him_once_the_flag_is_off_its_stand(self):
        self.assertEqual(self.honk("runner", 2, 12, flag_state="dropped")[0], "ride")

    def test_horn_as_before_outside_ctf(self):
        self.assertEqual(self.honk("runner", 2, 12, mode="slayer")[0], "ride")

    def test_gun_call_skips_the_escort_by_their_flag(self):
        self.assertEqual(self.gun_call("escort", 5, 20), ["mid", "ride"])
        self.assertEqual(self.gun_call("escort", 5, 20, flag_state="dropped"), ["ride", "mid"])

    def test_switch_off(self):
        from brain import director
        old = director.PULL_FIRST
        director.PULL_FIRST = False
        try:
            self.assertEqual(self.honk("runner", 2, 12)[0], "ride")
        finally:
            director.PULL_FIRST = old


class HeadhunterOpenDrops(unittest.TestCase):
    """#34, the rest (build 20261118-1525): the game's read of the open drop points (LiveReach.open_drops) comes first
    in our Headhunter brain (headhunter.Skulls; our score inference the fallback), and a failed skull read keeps the
    last list 2 s, then credits nobody with a pickup."""

    def setUp(self):
        from brain import headhunter as HH
        from test_headhunter import ZONES, pl, snap
        self.HH, self.ZONES, self.pl, self.snap = HH, ZONES, pl, snap

    def test_bankers_go_to_the_open_drop_point(self):
        h = self.HH.Skulls()
        h.update(0.0, self.snap(0.0, [self.pl(1, 0, Vec(10, 5, 0))]), self.ZONES, [], open_zones={1})
        self.assertEqual(h.bank_zone(Vec(1, 0, 0), 0.0), self.ZONES[1][0])     # though the other is nearer
        h.update(0.5, self.snap(0.5, [self.pl(1, 0, Vec(10, 5, 0))]), self.ZONES, [], open_zones=None)
        self.assertEqual(h.bank_zone(Vec(1, 0, 0), 0.5), self.ZONES[0][0])     # no read: as before

    def test_a_closed_drop_point_banks_nothing_without_a_score(self):
        h = self.HH.Skulls()
        h.held = {1: 3}
        me = [self.pl(1, 0, Vec(0.5, 0, 0))]
        for t in (0.0, 1.0, 2.0, 3.5):
            h.update(t, self.snap(t, me, score={}), self.ZONES, [], open_zones={1})
        self.assertEqual(h.held[1], 3)
        for t in (4.0, 5.0, 6.0, 7.5):                  # (no read: taken as banked, our rule as before)
            h.update(t, self.snap(t, me, score={}), self.ZONES, [], open_zones=None)
        self.assertEqual(h.held[1], 0)

    def test_an_open_drop_point_is_never_judged_dead(self):
        h = self.HH.Skulls()
        h.held = {1: 3}
        me = [self.pl(1, 0, Vec(0.5, 0, 0))]
        for t in (0.0, 1.0, 2.0, 3.5):
            h.update(t, self.snap(t, me), self.ZONES, [], open_zones={0})
        self.assertEqual(h.dead, {})
        self.assertEqual(h.held[1], 3)
        h.update(4.0, self.snap(4.0, me, {0: 3, 1: 0}), self.ZONES, [], open_zones={0})   # the score shows the bank
        self.assertEqual(h.held[1], 0)

    def test_a_failed_read_credits_nobody(self):
        h = self.HH.Skulls()
        sk = Vec(20, 5, 0)
        h.update(0.0, self.snap(0.0, [self.pl(1, 0, Vec(20.2, 5, 0))]), self.ZONES, [sk])
        h.update(0.25, self.snap(0.25, [self.pl(1, 0, Vec(20.2, 5, 0))]), self.ZONES, None)
        h.update(0.5, self.snap(0.5, [self.pl(1, 0, Vec(20.2, 5, 0))]), self.ZONES, [])
        self.assertEqual(h.held, {})

    def watch(self, reads, drops=None):
        from brain import modes
        from test_headhunter import A, B
        w = modes.Watch("headhunter", {})
        w.lay = {"drop_point": [(A, 2.0, 8), (B, 2.0, 8)]}

        class Fake:
            def __init__(s):
                s.read = None

            def loose_named(s, name):
                if s.read is None:
                    raise OSError("freed")
                return [(q.x, q.y, q.z) for q in s.read]

        live = Fake()
        if drops is not None:
            live.open_drops = lambda: [(q.x, q.y, q.z) for q in drops]
        out = []
        for t, loose, where in reads:
            live.read = loose
            sn = self.snap(t, [self.pl(1, 0, where)])
            w.update(live, sn, t, raw=[{}])
            out.append((sn, list(w.skulls)))
        return w, out

    def test_the_watch_keeps_the_last_skulls_2_s(self):
        sk, by = Vec(20, 5, 0), Vec(20.2, 5, 0)
        w, out = self.watch([(0.0, [sk], Vec(10, 5, 0)), (0.5, None, by), (1.5, None, by), (2.6, None, by),
                             (3.0, None, by)])
        self.assertEqual([len(s) for _, s in out], [1, 1, 1, 0, 0])
        self.assertEqual(out[-1][0].skulls_held, {})       # the empty list past 2 s was not his pickup

    def test_the_watch_reads_the_open_drop_points(self):
        from test_headhunter import B
        w, out = self.watch([(0.0, [], Vec(10, 5, 0))], drops=[Vec(40.3, 0.2, 0), Vec(90, 90, 0)])
        self.assertEqual(w.hh.open, {1})                    # (the one off every drop point dropped)
        self.assertEqual(w.hh.bank_zone(Vec(0, 0, 0), 0.0), B)

    def test_halo_4_reads_no_drop_points(self):
        self.assertIsNone(livemod.LiveH4F.open_drops)
        self.assertTrue(callable(LiveReach.open_drops))


class StubT:
    """A terrain stand-in for invasion.Watch: barriers and link gates taken and ignored, every line clear."""
    hjumps = ()

    def set_barrier(self, *a, **k):
        pass

    def los(self, a, b):
        return True


def boneyard():
    import json
    from brain import invasion
    objs = json.load(open(Path(__file__).resolve().parents[1] / "maps" / "reach_70_boneyard" / "objects.json",
                          encoding="utf-8"))
    return invasion.layout(objs)


class InvasionElites(unittest.TestCase):
    """#75 (build 20261120-1620): the attackers are read from the team playing Elites (LiveReach.elite_team), with
    his score check (score_attacker, gated by elite_ok) and the sides reset at each round."""

    def elite(self, rows):
        r = object.__new__(LiveReach)
        r.g = stock.Memory()
        players = []
        for k, (team, side, alive) in enumerate(rows):
            o = stock.OBJ + k * stock.OBJ_SIZE
            r.g.buf[o + LiveReach.UNIT_TEAM] = side
            players.append(dict(team=team, unit=k, pos=(0.0, 0.0, 0.0) if alive else None))
        r.object = lambda h: stock.OBJ + h * stock.OBJ_SIZE
        return r.elite_team(players)

    def test_the_elites_team(self):
        self.assertEqual(self.elite([(0, 1, True), (1, 7, True), (1, 7, True), (0, 1, True)]), 1)

    def test_none_unless_one_team_is_all_elites(self):
        self.assertIsNone(self.elite([(1, 7, True)]))                          # one player read
        self.assertIsNone(self.elite([(0, 7, True), (1, 7, True)]))            # both
        self.assertIsNone(self.elite([(0, 1, True), (1, 1, True)]))            # neither
        self.assertIsNone(self.elite([(0, 7, True), (0, 1, True), (1, 1, True)]))   # a mixed team
        self.assertEqual(self.elite([(0, 1, True), (1, 7, True), (0, 7, False)]), 1)   # (the dead are not read)

    def watch(self):
        from brain import invasion
        return invasion.Watch(boneyard(), StubT())

    def test_score_attacker(self):
        w = self.watch()
        w.attackers, w.round_t = 1, 0.0
        w.score_attacker({0: 0, 1: 0}, 5.0)                 # settling
        self.assertIsNone(w.score_seen)
        w.score_attacker({0: 0, 1: 0}, 11.0)
        w.score_attacker({0: 1, 1: 0}, 12.0)                 # team 0 scored: it attacks
        self.assertEqual((w.attackers, w.sides_set, w.score_base), (0, True, (0, 0)))

    def test_score_attacker_holds_while_the_elites_read(self):
        w = self.watch()
        w.attackers, w.round_t, w.elite_ok = 1, 0.0, True
        w.score_attacker({0: 0, 1: 0}, 11.0)
        w.score_attacker({0: 1, 1: 0}, 12.0)
        self.assertEqual(w.attackers, 1)

    def test_score_attacker_ignores_a_rounds_jump_and_both_up(self):
        w = self.watch()
        w.attackers, w.round_t = 1, 0.0
        w.score_attacker({0: 0, 1: 0}, 11.0)
        w.score_attacker({0: 3, 1: 0}, 12.0)
        w.score_attacker({0: 1, 1: 1}, 13.0)
        self.assertEqual(w.attackers, 1)

    def run_watch(self, w, elites, scores=None, now=20.0, players=None):
        from brain.core import PlayerState, Snapshot

        class Fake:
            def elite_team(s, raw):
                if elites == "fail":
                    raise OSError("read")
                return elites

            def match_state(s):
                return dict(score=scores or {0: 0, 1: 0})

            def core(s, raw, stand, key="core"):
                return []

            def present(s, pts, names=None):
                return set(range(len(pts)))

        sn = Snapshot(now, players or [PlayerState(i, i % 2, str(i), Vec(0, 0, 0), alive=True) for i in range(4)], {})
        w.update(Fake(), sn, now, raw=[{}])
        return sn

    def test_the_elites_team_attacks(self):
        w = self.watch()
        inv_att = w.attackers
        sn = self.run_watch(w, 1 - inv_att)
        self.assertEqual((sn.inv_attackers, w.sides_set, w.elite_ok), (1 - inv_att, True, True))

    def test_no_elite_read_plays_as_before(self):
        w = self.watch()
        inv_att = w.attackers
        for el in (None, "fail"):
            sn = self.run_watch(w, el)
            self.assertEqual(sn.inv_attackers, inv_att)
            self.assertFalse(w.elite_ok)

    def test_a_new_round_resets_the_sides(self):
        from brain.core import PlayerState
        w = self.watch()
        w.sides_set, w.score_seen = True, {0: 0, 1: 0}
        dead = [PlayerState(i, i % 2, str(i), Vec(0, 0, 0), alive=False) for i in range(6)]
        self.run_watch(w, None, now=30.0, players=dead)
        far = Vec(999, 999, 0)                              # (spawns no label says anything of: the sides stay unread)
        self.run_watch(w, None, now=31.0, players=[PlayerState(i, i % 2, str(i), far, alive=True) for i in range(6)])
        self.assertEqual((w.sides_set, w.score_seen, w.round_t), (False, None, 31.0))


def custom_invasion(zone_seq=1):
    """A labelled custom Invasion layout like the reporter's Tempest (GitHub #26): three objectives, the core's stand,
    each team's p1 labels, and inv_res_zone spawns nearer the middle, both nearer team 0's p1 label (team 1 attacks:
    it starts farther out)."""
    f = lambda t, pos, team=8, **k: dict(type=t, pos=list(pos), team=team, **k)
    return dict(netgame_flags=[
        f("inv_objective", (0, 0, 0)), f("inv_objective", (10, 0, 0)), f("inv_objective", (60, 0, 0)),
        f("inv_obj_flag", (5, 5, 0)),
        f("inv_res_p1", (-30, 0, 0), 0), f("inv_res_p1", (120, 0, 0), 1),
        f("inv_res_zone", (30, -30, 0), 0, phase=zone_seq), f("inv_res_zone", (40, 30, 0), 1, phase=zone_seq),
        f("inv_res_zone", (40, 40, 0), 8, phase=3),
    ])


class InvasionCustomMaps(unittest.TestCase):
    """#35 (build 20261118-1714, GitHub #26): Invasion on custom maps: bots respawn in the map's own labelled zones for
    each phase on the side attacking that round (label_spawns / label_spawn, live_bots.label_zone), the sides and the
    phase read by every label where the p labels say nothing, and a layout's labels read from its .mvar file
    (mvar.find_invasion). label_pick is #46's."""

    def test_label_spawns(self):
        from brain import invasion
        res = invasion.label_spawns(custom_invasion(zone_seq=2)["netgame_flags"])
        self.assertEqual(sorted(res[0]), [1, 2, 3])
        self.assertEqual(res[0][1], [Vec(-30, 0, 0)])                       # p1 only for phase 1
        self.assertEqual(res[0][2][0], Vec(30, -30, 0))                     # sequence 2: phases 2 and 3
        self.assertIn(Vec(30, -30, 0), res[0][3])
        self.assertIn(Vec(40, 40, 0), res[0][3])                            # team 8: both teams
        self.assertIn(Vec(40, 40, 0), res[1][3])

    def test_label_spawn_nearest_the_goal_and_earlier_phases(self):
        from brain import invasion
        inv = invasion.layout(custom_invasion())
        self.assertEqual((inv["attackers"], inv["defenders"]), (1, 0))
        att = invasion.label_spawn(inv, 1, True, Vec(0, 0, 0))
        self.assertEqual(att, Vec(40, 30, 0))                                # (nearer the goal than its p1 label)
        self.assertEqual(invasion.label_spawn(inv, 1, False, Vec(0, 0, 0)), Vec(-30, 0, 0))
        self.assertIsNone(invasion.label_spawn(dict(inv, spawn_res={}), 1, True, None))

    def test_sides_read_by_every_label(self):
        from brain import invasion
        from brain.core import PlayerState, Snapshot
        inv = invasion.layout(custom_invasion())
        w = invasion.Watch(inv, StubT())
        # the teams swapped: team 0 spawns on the map attackers' inv_res_zone, team 1 on the defenders'; both lie
        # nearer the defenders' p1 label, so the p labels read both teams defending
        self.assertFalse(any(invasion.roles_from_spawns(inv, [(0, Vec(40, 30, 0)), (1, Vec(30, -30, 0))]).values()))
        ps = [PlayerState(i, 0, str(i), Vec(40, 30, 0)) for i in range(3)] + \
             [PlayerState(i, 1, str(i), Vec(30, -30, 0)) for i in range(3, 6)]
        sn = Snapshot(5.0, ps, {})
        w.update(type("L", (), {})(), sn, 5.0)
        self.assertEqual((w.attackers, w.sides_set), (0, True))

    def test_phase_by_every_label_skips_a_zone_serving_phase_1(self):
        from brain import invasion
        inv = invasion.layout(custom_invasion(zone_seq=1))
        sr = inv["spawn_res"]
        self.assertIsNone(invasion.phase_from_spawns(inv, [(1, Vec(40, 30, 0))], sr))   # serves 1, 2, 3: says nothing
        self.assertEqual(invasion.phase_from_spawns(inv, [(1, Vec(120, 1, 0))]), 1)      # (the p labels as before)

    def test_label_zone(self):
        import live_bots
        from brain import invasion
        from brain.core import PlayerState, Snapshot
        inv = invasion.layout(custom_invasion())
        w = type("W", (), dict(phase=1, attackers=1, sides_set=True, round_wait_until=-1.0))()
        sn = Snapshot(9.0, [PlayerState(3, 1, "b", Vec(0, 0, 0), alive=False)], {})
        memo = {}
        x, y, z, yaw = live_bots.label_zone(inv, sn, 3, w, memo)
        self.assertEqual((x, y), (40, 30))
        self.assertTrue(memo["label"])
        w.sides_set = False                                       # a round's change: the game's own zone
        self.assertIsNone(live_bots.label_zone(inv, sn, 3, w, memo))
        self.assertNotIn("label", memo)
        self.assertIsNone(live_bots.label_zone(dict(inv, spawn_res={}), sn, 3, w))

    def test_find_invasion(self):
        import inspect
        from brain import mvar
        self.assertEqual(list(inspect.signature(mvar.find).parameters), ["base", "pieces", "files"])   # ours, kept
        files = {"a.mvar": dict(ok=True, objects=[dict(label="inv_res_zone", name="x", pos=(0, 0, 0))]),
                 "b.mvar": dict(ok=True, objects=[dict(label=None, name="x", pos=(0, 0, 0))])}
        saved = mvar.map_id_of, mvar.header_map_id, mvar._cached, mvar.find
        try:
            mvar.map_id_of = lambda base: 1
            mvar.header_map_id = lambda path: 1
            mvar._cached = lambda path: files[path]
            mvar.find = lambda base, pieces, files=None: (None, 0.1)
            v, share = mvar.find_invasion("reach_t", [], files=list(files))
            self.assertIs(v, files["a.mvar"])                     # the only one with Invasion labels
            files["a.mvar"]["objects"][0]["label"] = None
            self.assertEqual(mvar.find_invasion("reach_t", [], files=list(files)), (None, 0.0))
        finally:
            mvar.map_id_of, mvar.header_map_id, mvar._cached, mvar.find = saved


class SmartInvasionSpawns(unittest.TestCase):
    """#46 (build 20261118-1714): bots respawn for a reason: a free vehicle of their side waiting at its spot sends one
    bot to spawn by it (only one its tier may drive: #46b, live_bots.drivable), else a weighted pick leaning to the
    territory short of its share of the team and away from the enemy's spawn and a seen enemy; on labelled maps the
    same (label_pick). Our errand guards in Bot.decide (may_drive, wheel_yield) are kept."""

    def spawns(self):
        from brain import invasion
        return invasion.honor_spawns("reach_70_boneyard")

    def test_lane_factor(self):
        from brain import invasion
        lanes = [Vec(0, 0, 0), Vec(100, 0, 0)]
        from brain.core import PlayerState
        ps = [PlayerState(i, 0, str(i), Vec(1, 0, 0)) for i in range(4)]
        counts = invasion.lane_counts(lanes, ps, 0)
        self.assertEqual(counts, [4, 0])
        self.assertEqual(invasion.lane_factor(Vec(99, 0, 0), lanes, counts), 1.0 + invasion.LANE_W)
        self.assertEqual(invasion.lane_factor(Vec(2, 0, 0), lanes, counts), invasion.LANE_MIN)
        self.assertEqual(invasion.lane_factor(Vec(2, 0, 0), lanes[:1], counts), 1.0)    # one lane: as before

    def test_a_seen_enemy_rules_a_spawn_out(self):
        from brain import invasion
        from brain.core import PlayerState
        me = PlayerState(1, 1, "me", Vec(0, 0, 0), alive=False)
        foe = PlayerState(2, 0, "foe", Vec(269.0, 78.0, -5.0))              # on Middle Approach's one point
        offers = invasion.spawn_offers(self.spawns(), 2, "att", me, [me, foe], StubT())
        names = {o["name"]: w for w, o in offers}
        self.assertNotIn("Middle Approach", names)
        self.assertIn("Bulkheads", names)

    def honor(self, tier, veh_at, inv_veh, kind="warthog"):
        import live_bots
        import random
        from brain.core import PlayerState, Snapshot
        from test_upstream_030_brain import make_bot
        b = make_bot(tier=tier, mapname="reach_70_boneyard", bid=1, team=1)
        me = PlayerState(1, 1, "me", Vec(0, 0, 0), alive=False)
        far = PlayerState(2, 0, "foe", Vec(900, 900, 0))     # (half the lobby alive: spawn_check picks)
        sn = Snapshot(50.0, [me, far], {}, mode="invasion",
                      vehicles=[dict(handle=77, kind=kind, pos=veh_at, occupied=False, team=1)])
        sn.inv_phase, sn.inv_attackers, sn.inv_zones = 2, 1, []
        w = type("W", (), dict(sides_set=True, round_wait_until=-1.0, placed=set()))()
        sent = []
        live_bots.spawn_check(lambda i, *a: sent.append(a), {1: b}, sn, 50.0, {}, self.spawns(), w,
                              random.Random(3), StubT(), inv_veh=inv_veh)
        return b, sent

    def test_a_waiting_vehicle_sends_one_bot_to_its_spawn(self):
        at = (270.0, 80.0, -5.0)                               # by Middle Approach
        inv_veh = [dict(kind="warthog", pos=Vec(*at), side="att", phase=2)]
        b, sent = self.honor("strong", at, inv_veh)
        self.assertEqual(b.errand[0], 77)
        self.assertAlmostEqual(sent[0][0], 269.508, places=2)
        b, sent = self.honor("strong", at, [dict(inv_veh[0], phase=3)])     # not spawned for this phase yet
        self.assertIsNone(b.errand)

    def test_46b_never_for_a_vehicle_its_tier_may_not_drive(self):
        at = (270.0, 80.0, -5.0)
        inv_veh = [dict(kind="warthog", pos=Vec(*at), side="att", phase=2)]
        for tier in ("demon", "noble", "mythic"):
            b, sent = self.honor(tier, at, inv_veh)
            self.assertIsNone(b.errand, tier)
            self.assertEqual(len(sent), 1, tier)                 # (still spawned, by the weighted pick)
        b, _ = self.honor("demon", at, [dict(inv_veh[0], kind="banshee")], kind="banshee")
        self.assertEqual(b.errand[0], 77)                         # (a Banshee it may fly)

    def test_label_pick(self):
        import random
        from brain import invasion
        inv = invasion.layout(custom_invasion())
        inv["vehicles"] = [dict(kind="ghost", pos=Vec(42, 30, 0), side="att", phase=1)]
        v = dict(handle=5, kind="ghost", pos=(42.0, 31.0, 0.0), occupied=False)
        o = invasion.label_pick(inv, 1, True, Vec(5, 0, 0), random.Random(1), vehicles=[v])
        self.assertEqual((o["pos"], o["ride"]), (Vec(40, 30, 0), 5))
        o = invasion.label_pick(inv, 1, True, Vec(5, 0, 0), random.Random(1), vehicles=[])
        self.assertIsNone(o["ride"])
        self.assertIn(o["pos"], inv["spawn_res"][1][1])

    def test_layout_reads_a_variants_vehicles(self):
        from brain import invasion
        objs = custom_invasion()
        objs["netgame_flags"].append(dict(type="inv_vehicle", pos=[50, 30, 0], team=1, phase=2, object="warthog"))
        inv = invasion.layout(objs)
        self.assertEqual(inv["vehicles"], [dict(kind="warthog", pos=Vec(50, 30, 0), side="att", phase=2)])

    def test_inv_vehicles_files_stay_local(self):
        gi = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("maps/*/inv_vehicles.json", gi.splitlines())


class InvasionSecondSquad(unittest.TestCase):
    """#45 (build 20261118-1714): with 4 or more attackers in phases 1-2, LANE_SPLIT of the team takes the other
    territory at the same time. The owner: behind a switch, off (0 = today's play) until checked in the sim; every tier
    (our assign_roles decides who fills the slots)."""

    def slots(self, n, split=None, phase_t=5.0):
        from brain import director as D
        from brain.core import Snapshot
        d = D.Director.__new__(D.Director)
        d.team, d.map = 1, {"points": {"mid": Vec(50, 0, 0)}}
        d.spread = lambda p, k, r: p
        d.overlooks = lambda p, n: []
        A, B = Vec(0, 0, 0), Vec(100, 0, 0)
        sn = Snapshot(10.0, [], {}, mode="invasion")
        sn.inv_zones, sn.inv_zone_r, sn.inv_phase, sn.inv_attackers, sn.inv_phase_t = [A, B], [2.5, 2.5], 1, 1, phase_t
        sn.inv_core, sn.inv_armed = None, False
        old = D.LANE_SPLIT
        if split is not None:
            D.LANE_SPLIT = split
        try:
            out = d.invasion_slots(10.0, sn, n)
        finally:
            D.LANE_SPLIT = old
        at = lambda z: sum(1 for r, q, _ in out if r == "defender" and q is z)
        return at(A), at(B), len(out)

    def test_off_by_default(self):
        from brain import director as D
        self.assertEqual(D.LANE_SPLIT, 0.0)
        self.assertEqual(self.slots(8), (8, 0, 8))               # today's play: all on one territory

    def test_his_split(self):
        self.assertEqual(self.slots(8, split=0.35), (5, 3, 8))   # round(0.35 * 8) = 3 in the other territory
        self.assertEqual(self.slots(3, split=0.35), (3, 0, 3))   # fewer than 4: no second squad

    def test_off_keeps_the_old_one_man_split_before_the_push(self):
        from brain import director as D
        old = D.PUSH_AFTER
        D.PUSH_AFTER = 60.0
        try:
            a, b, _ = self.slots(6, phase_t=5.0)
            self.assertEqual((a, b), (2, 1))                       # (two in, one to the other: as before)
            a, b, _ = self.slots(6, split=0.35, phase_t=5.0)
            self.assertEqual((a, b), (2, 2))                       # (his squad of 2 replaces the one man)
        finally:
            D.PUSH_AFTER = old


class LowPerformanceWarning(unittest.TestCase):
    """#47, its live_bots part (build 20261118-2107), by our own check (not his bot_capacity.py): the median pass over
    2 slots (66 ms) 3 checks in a row shows the "!" card, at most every 120 s; the bots think the same."""

    def setUp(self):
        import live_bots
        self.lb = live_bots
        self.saved = dict(live_bots.WARN)
        live_bots.WARN.update(run=0, at=-1e9)

    def tearDown(self):
        self.lb.WARN.update(self.saved)

    def feed(self, ms, now, shown):
        lb = self.lb
        buf = []
        out = False
        for _ in range(lb.SPEED_EVERY):
            buf.append(ms)
            out = lb.speed_note(buf, now, lambda t, line: shown.append((t, line))) or out
        self.assertEqual(buf, [])                         # (judged and cleared: its own list stays short)
        return out

    def test_three_slow_checks_in_a_row(self):
        shown = []
        self.assertFalse(self.feed(80.0, 10.0, shown))
        self.assertFalse(self.feed(80.0, 12.0, shown))
        self.assertTrue(self.feed(80.0, 14.0, shown))
        self.assertEqual(shown[0][0], "!BOT PERFORMANCE LOW")
        self.assertLessEqual(len("|".join(shown[0])), 127)     # (botctl.notice's room)
        self.assertFalse(self.feed(80.0, 16.0, shown))     # at most every 120 s
        self.assertTrue(self.feed(80.0, 140.0, shown))

    def test_a_fast_check_starts_over(self):
        shown = []
        self.feed(80.0, 10.0, shown)
        self.feed(80.0, 12.0, shown)
        self.feed(30.0, 14.0, shown)                       # (under 66 ms)
        self.assertFalse(self.feed(80.0, 16.0, shown))
        self.assertEqual(shown, [])
        self.assertAlmostEqual(self.lb.SLOT_MS * self.lb.HORRIBLE_SLOTS, 66.67, places=1)

    def test_a_failing_card_never_fails_the_pass(self):
        def boom(t, line):
            raise OSError("no overlay")
        buf = [99.0] * self.lb.SPEED_EVERY
        self.lb.WARN.update(run=5)
        self.assertFalse(self.lb.speed_note(buf, 500.0, boom))


if __name__ == "__main__":
    unittest.main()
