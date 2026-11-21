"""(custom, Nov 20) Noble's learning (brain/noble.py): its tune file, shot learning, winning spots. The owner: "I want
Noble to be our testing bot. So anything self learning we can give it ... we can try here"; "DO 1,2 and 4". Every test
uses a folder of its own: user/ is never read or written."""
import json
import os
import random
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain import bot, noble, profiles  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._dir, self._save = noble.STORE_DIR, noble.SAVE
        noble.STORE_DIR, noble.SAVE, noble.OVERRIDE = self.tmp.name, True, None
        noble.reload()

    def tearDown(self):
        noble.book().new = 0              # (nothing left to write once the folder is gone)
        noble.STORE_DIR, noble.SAVE, noble.OVERRIDE = self._dir, self._save, None
        noble.reload()
        self.tmp.cleanup()


def man(i, team, pos, shield=1.0, health=1.0, yaw=0.0, mag=(10,)):
    return PlayerState(i, team, f"p{i}", pos, yaw=yaw, shield=shield, health=health, weapon="dmr", weapons=["dmr"],
                       mag=list(mag))


def snap(t, *players):
    return Snapshot(t, list(players))


class TuneTests(Folder):
    def test_defaults_keep_demon_rules(self):
        st = noble.tune("reach")
        self.assertEqual(st, noble.DEFAULTS)
        self.assertTrue(all(st[r] == 1 for r in noble.RULES))
        self.assertEqual(st["push"], 0.0)

    def test_file_then_override(self):
        self.assertTrue(noble.save_tune("reach", dict(noble.DEFAULTS, push=0.3, peek=0), games=8, margin=4.5))
        with open(os.path.join(self.tmp.name, noble.TUNE_FILE), encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["reach"]["games"], 8)
        self.assertEqual((noble.tune("reach")["push"], noble.tune("reach")["peek"]), (0.3, 0))
        self.assertEqual(noble.tune("h3")["push"], 0.0)                     # (another game: its own, none yet)
        noble.OVERRIDE = dict(push=0.1, bogus=5)
        self.assertEqual(noble.tune("reach")["push"], 0.1)
        self.assertNotIn("bogus", noble.tune("reach"))

    def test_no_write_when_off(self):
        noble.SAVE = False
        self.assertFalse(noble.save_tune("reach", noble.DEFAULTS))
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, noble.TUNE_FILE)))


class ShotTests(Folder):
    def setUp(self):
        super().setUp()
        self.me, self.foe = man(1, 0, Vec()), man(2, 1, Vec(10, 0, 0))
        self.shot = man(1, 0, Vec(), mag=(9,))                              # (the round left: one fewer)

    def test_hit_and_miss(self):
        w = noble.ShotWatch("reach")
        w.pressed(0.0, snap(0.0, self.me, self.foe), self.me, 2, 10.0, "dmr", True, 0.4)
        hurt = man(2, 1, Vec(10, 0, 0), shield=0.75)
        w.resolve(0.1, snap(0.1, self.shot, hurt), self.shot)
        self.assertEqual((w.hits, w.misses), (1, 0))
        two = man(1, 0, Vec(), mag=(8,))
        w.pressed(0.5, snap(0.5, self.shot, hurt), self.shot, 2, 10.0, "dmr", True, 0.4)
        w.resolve(0.7, snap(0.7, two, hurt), two)
        self.assertEqual((w.hits, w.misses), (1, 0))                        # (still in its window)
        w.resolve(0.9, snap(0.9, two, hurt), two)
        self.assertEqual((w.hits, w.misses), (1, 1))
        cells = noble.book().counts("reach", "dmr")
        self.assertEqual(cells["2|rest|head"], [1, 1])                      # (the first shot: "rest")
        self.assertEqual(cells["2|1.3|head"], [1, 0])                       # (0.5 s after a 0.4 s gap: x1.25)

    def test_a_kill_is_a_hit(self):
        w = noble.ShotWatch("reach")
        w.pressed(0.0, snap(0.0, self.me, self.foe), self.me, 2, 5.0, "dmr", False, 0.4)
        dead = man(2, 1, Vec(10, 0, 0))
        dead.alive = False
        w.resolve(0.05, snap(0.05, self.shot, dead), self.shot)
        self.assertEqual(w.hits, 1)
        self.assertEqual(noble.book().counts("reach", "dmr")["1|rest|chest"], [1, 1])

    def test_a_press_that_fired_nothing_is_not_a_shot(self):
        # (live Nov 20: presses as a grenade left the hand, and on an empty magazine: the magazine never went down)
        w = noble.ShotWatch("reach")
        w.pressed(0.0, snap(0.0, self.me, self.foe), self.me, 2, 10.0, "dmr", True, 0.4)
        w.resolve(0.5, snap(0.5, self.me, self.foe), self.me)
        self.assertEqual((w.hits, w.misses, w.dry_presses), (0, 0, 1))
        self.assertEqual(noble.book().counts("reach", "dmr"), {})
        blind = man(1, 0, Vec(), mag=(-1,))                                 # (a magazine not read: counted)
        w.pressed(1.0, snap(1.0, blind, self.foe), blind, 2, 10.0, "dmr", True, 0.4)
        w.resolve(1.5, snap(1.5, blind, self.foe), blind)
        self.assertEqual(w.misses, 1)

    def test_a_mates_round_not_counted(self):
        mate = man(3, 0, Vec(0, 2, 0), yaw=-0.2, mag=(8,))                  # (facing him)
        w = noble.ShotWatch("reach")
        w.pressed(0.0, snap(0.0, self.me, self.foe, mate), self.me, 2, 10.0, "dmr", True, 0.4)
        fired = man(3, 0, Vec(0, 2, 0), yaw=-0.2, mag=(7,))
        w.resolve(0.1, snap(0.1, self.shot, man(2, 1, Vec(10, 0, 0), shield=0.75), fired), self.shot)
        self.assertEqual((w.hits, w.misses, w.skipped), (0, 0, 1))
        away = man(3, 0, Vec(0, 2, 0), yaw=3.0, mag=(8,))                   # (firing the other way: ours)
        w.pressed(1.0, snap(1.0, self.me, self.foe, away), self.me, 2, 10.0, "dmr", True, 0.4)
        w.resolve(1.1, snap(1.1, self.shot, man(2, 1, Vec(10, 0, 0), shield=0.75),
                            man(3, 0, Vec(0, 2, 0), yaw=3.0, mag=(7,))), self.shot)
        self.assertEqual(w.hits, 1)

    def test_written_and_read_back(self):
        bk = noble.book()
        for k in range(noble.SAVE_EVERY_N):
            bk.add("reach", "dmr", 2, 1.0, "head", k % 2 == 0)
        with open(os.path.join(self.tmp.name, noble.SHOTS_FILE), encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["reach"]["dmr"]["2|1.0|head"], [20, 10])
        noble.reload()
        self.assertEqual(noble.book().rate("reach", "dmr", 2, pace=1.0)[1], 20)
        self.assertEqual(noble.accuracy("reach"), {"reach": {"dmr": {2: [20, 10]}}})


class PaceTests(Folder):
    def test_untried_starts_at_the_paced_gap(self):
        noble.OVERRIDE = dict(explore=0.0)
        self.assertAlmostEqual(noble.gap("reach", "dmr", 6.0, 0.4, random.Random(1)), 0.4)
        self.assertAlmostEqual(noble.gap("reach", "dmr", 20.0, 0.4, random.Random(1)), 0.4 * 1.2)   # (long_pace)

    def test_a_faster_pace_that_lands(self):
        noble.OVERRIDE = dict(explore=0.0)
        bk = noble.book()
        for _ in range(40):
            bk.add("reach", "dmr", 1, 0.8, "head", True)                    # 0.8: 40 of 40
            bk.add("reach", "dmr", 1, 1.0, "head", True)
        self.assertAlmostEqual(noble.gap("reach", "dmr", 6.0, 0.4, random.Random(1)), 0.4 * 0.8)
        for _ in range(80):
            bk.add("reach", "dmr", 1, 0.8, "head", False)                   # now a third: slower lands more a second
        self.assertGreater(noble.gap("reach", "dmr", 6.0, 0.4, random.Random(1)), 0.4 * 0.8)
        self.assertAlmostEqual(noble.gap("reach", "dmr", 20.0, 0.4, random.Random(1)), 0.4 * 1.2)  # (its own band)

    def test_off(self):
        noble.OVERRIDE = dict(shot_learn=0)
        self.assertAlmostEqual(noble.gap("reach", "dmr", 6.0, 0.4, random.Random(1)), 0.4)

    def test_explores(self):
        got = {round(noble.gap("reach", "dmr", 6.0, 0.4, random.Random(s)), 3) for s in range(200)}
        self.assertGreater(len(got), 2)


class PartTests(Folder):
    def test_head_until_learned_then_the_better(self):
        noble.OVERRIDE = dict(explore=0.0)
        rng = random.Random(1)
        self.assertTrue(noble.part("reach", "dmr", 10.0, True, True, True, True, rng))
        bk = noble.book()
        for k in range(20):
            bk.add("reach", "dmr", 2, 1.0, "head", k < 10)                  # head 50%
            bk.add("reach", "dmr", 2, 1.0, "chest", k < 18)                 # chest 90%
        self.assertFalse(noble.part("reach", "dmr", 10.0, True, True, True, True, rng))   # shield up: the chest
        self.assertTrue(noble.part("reach", "dmr", 10.0, False, True, True, True, rng))   # shield down: the head
        self.assertTrue(noble.part("reach", "dmr", 10.0, True, True, False, True, rng))   # no line to the chest
        self.assertTrue(noble.part("reach", "dmr", 2.0, True, True, True, True, rng))     # (another band: untried)


class Lore:
    def __init__(self, kills):
        self.kills = kills

    def trusted(self):
        return True


class SpotTests(Folder):
    def lore(self):
        # a cell at (4, 0) that won 8 of 9, one at (-4, 0) that lost 6 of 7, one far off that won everything
        k = [[20.0, 0.0, 0.0, 4.5, 0.5, 0.0]] * 8 + [[4.5, 0.5, 0.0, 20.0, 0.0, 0.0]]
        k += [[-3.5, 0.5, 0.0, 20.0, 1.0, 0.0]] * 6 + [[20.0, 1.0, 0.0, -3.5, 0.5, 0.0]]
        k += [[40.0, 0.0, 0.0, 60.0, 0.0, 0.0]] * 10
        return Lore(k)

    def test_the_winning_cell_in_reach(self):
        lb = self.lore()
        got = noble.spot_for(lb, Vec(), Vec(20, 0, 0), lambda a, b: True)
        self.assertIsNotNone(got)
        spot, rate, key = got
        self.assertLess((spot - Vec(4.5, 0.5, 0)).flat(), 0.01)
        self.assertAlmostEqual(rate, 9 / 11)
        self.assertIsNone(noble.spot_for(lb, Vec(), Vec(20, 0, 0), lambda a, b: False))   # (no line onto him)
        self.assertIsNone(noble.spot_for(lb, Vec(), Vec(20, 0, 0), lambda a, b: True, banned={key}))
        self.assertIsNone(noble.spot_for(lb, Vec(30, 30, 0), Vec(20, 0, 0), lambda a, b: True))  # (too far)

    def test_cached_until_new_kills(self):
        lb = self.lore()
        t1 = noble.spot_table(lb)
        self.assertIs(noble.spot_table(lb), t1)
        lb.kills = lb.kills + [[0.0, 0.0, 0.0, 1.0, 1.0, 0.0]]
        self.assertIsNot(noble.spot_table(lb), t1)

    def test_bot_holds_it(self):
        b = bot.Bot.__new__(bot.Bot)
        b.p, b.game, b.notes = make_profile("noble", "camper", random.Random(1)), "reach", []
        lb = self.lore()
        b.lore = lambda: lb
        b.T = lambda: types.SimpleNamespace(los=lambda a, c: True)
        me = man(1, 0, Vec())
        sn = types.SimpleNamespace(mode="slayer")
        scores = {("hunt", Vec(20, 0, 0)): 2.0, ("objective", Vec(0, 9, 0)): 1.0}
        b.noble_spot(0.0, me, sn, scores, set())
        spots = [k for k in scores if k[0] == "retreat"]
        self.assertEqual(len(spots), 1)
        self.assertAlmostEqual(scores[spots[0]], 2.05)
        held = {("hunt", Vec(20, 0, 0)): 2.0, ("fight", 7): 2.5}
        b.noble_spot(0.5, me, sn, held, {7})                                 # a man in view: the fight's rules
        self.assertFalse(any(k[0] == "retreat" for k in held))
        b.p = make_profile("demon", "camper", random.Random(1))
        plain = {("hunt", Vec(20, 0, 0)): 2.0}
        b.noble_spot(0.0, me, sn, plain, set())
        self.assertEqual(list(plain), [("hunt", Vec(20, 0, 0))])             # (Demon: untouched)

    def test_held_then_walks_on(self):
        b = bot.Bot.__new__(bot.Bot)
        b.p, b.game, b.notes = make_profile("noble", "camper", random.Random(1)), "reach", []
        lb = self.lore()
        b.lore = lambda: lb
        b.T = lambda: types.SimpleNamespace(los=lambda a, c: True)
        sn = types.SimpleNamespace(mode="slayer")
        at = man(1, 0, Vec(4.5, 0.5, 0))
        for t in (0.0, 1.0, 2.0, 3.0):
            sc = {("hunt", Vec(20, 0, 0)): 2.0}
            b.noble_spot(t, at, sn, sc, set())
            self.assertTrue(any(k[0] == "retreat" for k in sc), t)
        sc = {("hunt", Vec(20, 0, 0)): 2.0}
        b.noble_spot(3.5, at, sn, sc, set())                                 # held spot_hold_s: the hunt goes on
        self.assertFalse(any(k[0] == "retreat" for k in sc))


class BotHookTests(Folder):
    def test_press_watched(self):
        b = bot.Bot.__new__(bot.Bot)
        b.p, b.game, b.id = make_profile("noble", "camper", random.Random(1)), "reach", 1
        me, foe = man(1, 0, Vec()), man(2, 1, Vec(10, 0, 0))
        b.shot_part = (2, True)
        sn = snap(0.0, me, foe)
        b.noble_fired(0.0, sn, types.SimpleNamespace(fire=True), False)
        self.assertEqual(len(b.noble_watch.pending), 1)
        b.noble_fired(0.03, sn, types.SimpleNamespace(fire=True), True)     # (a held press: once)
        self.assertEqual(len(b.noble_watch.pending), 1)
        b.noble_learn(0.1, snap(0.1, man(1, 0, Vec(), mag=(9,)), man(2, 1, Vec(10, 0, 0), shield=0.75)))
        self.assertEqual(b.noble_watch.hits, 1)

    def test_eyes_at_head_height(self):
        # (live Nov 20: "Staticwolf shot the ground": its look points chest high or on a corner's floor, 7-12 deg down)
        b = bot.Bot.__new__(bot.Bot)
        b.T = lambda: types.SimpleNamespace(nav_z=lambda x, y, z: 2.0)
        self.assertAlmostEqual(b.noble_head_height(Vec(5, 0, 2.0)).z, 2.0 + bot.EYE)       # a corner's floor
        self.assertAlmostEqual(b.noble_head_height(Vec(5, 0, 2.35)).z, 2.0 + bot.EYE)      # chest high
        self.assertAlmostEqual(b.noble_head_height(Vec(5, 0, 3.5)).z, 3.5)                 # higher already: kept
        self.assertAlmostEqual(b.noble_head_height(Vec(5, 0, 9.0)).z, 9.0)                 # no floor near: as it is
        src = (ROOT / "brain" / "bot.py").read_text(encoding="utf-8")
        self.assertIn("if dl > 1.0 and not noble_eyes:", src)                              # (no eye wander for Noble)

    def test_part_hook_in_fight(self):
        src = (ROOT / "brain" / "bot.py").read_text(encoding="utf-8")
        self.assertIn("head = noble.part(", src)
        self.assertIn("return noble.gap(", src)
        self.assertIn("s.noble_spot(now, me, snap, scores, seen)", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
