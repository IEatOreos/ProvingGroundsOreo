"""(custom, Nov 13) Land Grab vs Territories. The owner: "Land Grab is where all points are nuetral and each team fights to
take them ... Once capture by either team it locks as theirs ... Each round ends when all points are capture ... Normal
territories is where team defends their land and the other attacks. Can you make the distinction". His Powerhouse Land
Grab 20261113-222752: the game scored 4-1 (all five taken) at 224 s while the brain had found 2; round 2 kept round 1's
owners, and bots attacked and guarded zones already locked or neutral."""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain import mvar                                      # noqa: E402
from brain.core import PlayerState, Snapshot, Vec           # noqa: E402
from brain.director import Director                         # noqa: E402
from brain.modes import Watch                               # noqa: E402

MCC = os.environ.get("MCC_ROOT", r"F:\SteamLibrary\steamapps\common\Halo The Master Chief Collection")
GV = os.path.join(MCC, "haloreach", "game_variants")
ZONES = [Vec(0, 0, 0), Vec(20, 0, 0), Vec(40, 0, 0), Vec(60, 0, 0), Vec(80, 0, 0)]


def watch(rules=None):
    w = Watch.__new__(Watch)
    w.kind = w.mode = "territories"
    w.lay = {"territory": [(z, 3.0, 8) for z in ZONES]}
    w.capture, w.owner, w.held = 30.0, {}, {}
    w.terr_style, w.terr_lock, w.round_total = None, False, None
    w.set_territory_rules(rules)
    return w


def snap(score, players, limit=5):
    s = Snapshot(100, [PlayerState(i, t, f"p{i}", pos) for i, (t, pos) in enumerate(players)])
    s.score, s.score_limit, s.score_live = dict(score), limit, limit > 0   # (limit 0 here: a failed read, the defaults)
    return s


LAND_GRAB = dict(style="symmetric", lock=True, capture=30.0)


class VariantRules(unittest.TestCase):
    def test_options(self):
        opt = lambda **kw: dict(options=[dict(name=k.replace("_", " ").title(), value=v) for k, v in kw.items()])
        self.assertEqual(mvar.territory_rules(opt(style="Symmetric", capture_lock="Enabled", capture_time="30 seconds")),
                         LAND_GRAB)
        self.assertEqual(mvar.territory_rules(opt(style="Asymmetric", capture_lock="Disabled", capture_time="1 minute")),
                         dict(style="asymmetric", lock=False, capture=60.0))
        self.assertIsNone(mvar.territory_rules(opt(flag_count="4 flags")))
        self.assertIsNone(mvar.territory_rules(None))

    @unittest.skipUnless(os.path.isdir(GV), "no MCC here")
    def test_mccs_own_variants(self):
        read = lambda f: mvar.territory_rules(mvar.read_game_variant(os.path.join(GV, f)))
        self.assertEqual(read("territories-landgrab_054.bin"), LAND_GRAB)
        self.assertEqual(read("territories_054.bin"), dict(style="asymmetric", lock=False, capture=30.0))
        self.assertEqual(read("territories-3plot_054.bin"), dict(style="symmetric", lock=False, capture=5.0))


class Ownership(unittest.TestCase):
    def test_capture_time_from_the_variant(self):
        w = watch(dict(style="symmetric", lock=False, capture=5.0))
        s = snap({0: 0, 1: 0}, [(0, ZONES[0])])
        w.update(None, s, 10.0)
        w.update(None, s, 15.5)
        self.assertEqual(s.obj_zones[0][2], 0)                      # 5 s, not 30

    def test_land_grab_owner_from_the_score(self):
        w = watch(LAND_GRAB)
        s = snap({0: 0, 1: 0}, [(0, ZONES[1]), (1, ZONES[3])])
        w.update(None, s, 10.0)
        self.assertEqual([o for _, _, o in s.obj_zones], [-1] * 5)
        s = snap({0: 1, 1: 0}, [(0, ZONES[1]), (1, ZONES[3])])      # 3 s later team 0 scores: its zone is taken
        w.update(None, s, 13.0)
        self.assertEqual([o for _, _, o in s.obj_zones], [-1, 0, -1, -1, -1])
        self.assertTrue(s.terr_lock)
        # held 40 s alone, no score: the 30 s guess does not take it under the lock
        s = snap({0: 1, 1: 0}, [(0, ZONES[1]), (1, ZONES[3])])
        w.update(None, s, 60.0)
        self.assertEqual(s.obj_zones[3][2], -1)
        # locked: team 1 standing in team 0's zone does not take it
        s = snap({0: 1, 1: 1}, [(1, ZONES[1]), (1, ZONES[3])])
        w.update(None, s, 61.0)
        w.update(None, s, 100.0)
        self.assertEqual([o for _, _, o in s.obj_zones], [-1, 0, -1, 1, -1])

    def test_score_by_a_man_near_the_edge(self):
        w = watch(LAND_GRAB)
        s = snap({0: 1, 1: 0}, [(0, ZONES[2] + Vec(4.5, 0, 0)), (1, ZONES[4] + Vec(9, 0, 0))])
        w.update(None, s, 5.0)
        self.assertEqual(s.obj_zones[2][2], 0)                      # 1.5 u past the edge: his
        s = snap({0: 1, 1: 1}, [(0, ZONES[2]), (1, ZONES[4] + Vec(9, 0, 0))])
        w.update(None, s, 6.0)
        self.assertEqual(s.obj_zones[4][2], -1)                     # nobody of 1's by any free zone: not guessed

    def test_new_round_resets(self):
        w = watch(LAND_GRAB)
        for score, pos in (({0: 1, 1: 0}, ZONES[0]), ({0: 2, 1: 0}, ZONES[1])):
            s = snap(score, [(0, pos)])
            w.update(None, s, 10.0)
        self.assertEqual([o for _, _, o in s.obj_zones][:2], [0, 0])
        s = snap({0: 0, 1: 0}, [(0, ZONES[0])])                     # round 2: 0-0, all neutral again
        w.update(None, s, 240.0)
        self.assertEqual([o for _, _, o in s.obj_zones], [-1] * 5)

    def test_everyone_dead_is_a_new_round(self):
        w = watch(LAND_GRAB)
        s = snap({0: 1, 1: 0}, [(0, ZONES[0]), (1, ZONES[4] + Vec(9, 0, 0))])
        w.update(None, s, 10.0)
        self.assertEqual(s.obj_zones[0][2], 0)
        s = snap({0: 0, 1: 0}, [(0, ZONES[0]), (1, ZONES[1])], limit=0)   # the round's end, the read gone with it
        for p in s.players:
            p.alive = False
        w.update(None, s, 230.0)
        self.assertEqual([o for _, _, o in s.obj_zones], [-1] * 5)

    def test_score_read_lost_falls_back_to_the_guess(self):
        # Powerhouse's round 2: 0-0 and limit 0 all round; the 30 s guess (locked once taken) takes over
        w = watch(LAND_GRAB)
        s = snap({0: 0, 1: 0}, [(1, ZONES[2])], limit=0)
        w.update(None, s, 240.0)
        w.update(None, s, 271.0)
        self.assertEqual(s.obj_zones[2][2], 1)
        s = snap({0: 0, 1: 0}, [(0, ZONES[2])], limit=0)                    # locked: team 0 cannot take it back
        w.update(None, s, 272.0)
        w.update(None, s, 310.0)
        self.assertEqual(s.obj_zones[2][2], 1)

    def test_without_rules_as_before(self):
        w = watch(None)
        s = snap({0: 3, 1: 0}, [(0, ZONES[0])])
        w.update(None, s, 1.0)
        self.assertEqual(s.obj_zones[0][2], -1)                     # the score alone takes nothing
        w.update(None, s, 32.0)
        self.assertEqual(s.obj_zones[0][2], 0)                      # 30 s alone
        self.assertFalse(s.terr_lock)


class MatchRead(unittest.TestCase):
    """tools/live_bots.py match_sane: each part of the score read judged on its own."""

    def setUp(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import live_bots
        self.sane = live_bots.match_sane

    def test_good_read_kept_as_is(self):
        v = dict(score={0: 4, 1: 1}, limit=5, time_left=70.0)
        self.assertIs(self.sane(v), v)

    def test_bad_limit_or_clock_keeps_the_score(self):
        self.assertEqual(self.sane(dict(score={0: 2, 1: 1}, limit=-1, time_left=60.0)),
                         dict(score={0: 2, 1: 1}, limit=0, time_left=60.0))
        self.assertEqual(self.sane(dict(score={0: 2, 1: 1}, limit=5, time_left=-30.0)),
                         dict(score={0: 2, 1: 1}, limit=5, time_left=None))

    def test_garbage_score_dropped(self):
        self.assertIsNone(self.sane(dict(score={0: 99999, 1: 0}, limit=5, time_left=60.0)))
        self.assertIsNone(self.sane(dict(score={0: -900, 1: 0}, limit=-1, time_left=None)))
        self.assertIsNone(self.sane(None))


class Plan(unittest.TestCase):
    def director(self):
        d = Director.__new__(Director)
        d.team = d.side = 0
        d.map = dict(points={"mid": Vec(40, 30, 0)})
        d.posture = SimpleNamespace(state="even")
        d.spread = lambda p, k, r: p
        d.overlooks = lambda p, n: []
        d.slayer_slots = lambda now, snap, n: [("slayer", None, "aggression")]
        return d

    def scene(self, owners, lock=True):
        s = snap({0: 0, 1: 0}, [(0, Vec(0, -5, 0)), (1, Vec(80, -5, 0))])
        s.mode, s.terr_lock = "territories", lock
        s.obj_zones = [(z, 3.0, o) for z, o in zip(ZONES, owners)]
        return s

    def test_land_grab_goes_for_neutral_only(self):
        d = self.director()
        slots = d.mode_slots(0.0, self.scene([0, 1, -1, 1, -1]), 4)
        pts = {(p.x, p.y) for role, p, _ in slots if role == "defender"}
        self.assertTrue(pts <= {(40, 0), (80, 0)}, pts)            # neutral zones only: none at 0 (ours) or 20 / 60
        self.assertIn((40, 0), pts)

    def test_easy_runs_at_a_neutral_zone(self):
        d = self.director()
        self.assertEqual(d.straight_objective(self.scene([0, 1, -1, 1, 0])), ZONES[2])
        self.assertEqual(d.straight_objective(self.scene([0, 1, 0, 1, 0])), Vec(40, 30, 0))     # none left: mid
        self.assertEqual(d.straight_objective(self.scene([-1, 1, 0, 1, 0], lock=False)), ZONES[1])   # theirs, as before

    def test_all_taken_plays_slayer(self):
        d = self.director()
        self.assertEqual(d.mode_slots(0.0, self.scene([0, 1, 0, 1, 1]), 4), [("slayer", None, "aggression")])

    def test_territories_unchanged(self):
        d = self.director()
        slots = d.mode_slots(0.0, self.scene([0, 1, -1, 1, -1], lock=False), 4)
        pts = [(p.x, p.y) for role, p, _ in slots if role == "defender"]
        self.assertIn((0, 0), pts)                                   # ours held, as before
