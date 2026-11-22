"""(custom, Nov 22) Noble's four new lessons (brain/noble_habits.py): pre-aim, each person's habits, dodges, team
focus. The owner: "Do pre aim first and then into number 4, then number 5, and number 6 until completion, noble only".
Every test uses a folder of its own: user/ is never read or written."""
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
from brain import bot, noble, noble_habits as H  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

LAY = "reach_forge_halo/variants/vtest"


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._dir, self._save = noble.STORE_DIR, noble.SAVE
        noble.STORE_DIR, noble.SAVE, noble.OVERRIDE = self.tmp.name, True, None
        noble.reload()

    def tearDown(self):
        for st in H._STORES.values():
            st.new = 0
        noble.STORE_DIR, noble.SAVE, noble.OVERRIDE = self._dir, self._save, None
        noble.reload()
        self.tmp.cleanup()


def man(i, team, pos, shield=1.0, health=1.0, is_bot=True, name=None):
    return PlayerState(i, team, name or f"p{i}", pos, shield=shield, health=health, weapon="dmr", is_bot=is_bot)


def yes(a, b):
    return True


def noble_bot(i=1, tier="noble"):
    b = bot.Bot.__new__(bot.Bot)
    b.p, b.game, b.notes, b.id = make_profile(tier, "camper", random.Random(1)), "reach", [], i
    b.map = {"name": LAY}
    b.rng = random.Random(3)
    return b


class PreaimTests(Folder):
    def test_needs_enough_sightings(self):
        me = Vec(1, 1, 0)
        for _ in range(2):
            H.add_sight(LAY, me, Vec(20, 1, 0))
        self.assertIsNone(H.preaim(LAY, me, me, yes))
        H.add_sight(LAY, me, Vec(20.4, 1, 0))
        q, n = H.preaim(LAY, me, me, yes)
        self.assertAlmostEqual(q.x, 20.13, places=1)
        self.assertAlmostEqual(q.z, H.HEAD)
        self.assertEqual(n, 3)

    def test_most_seen_angle_with_a_line(self):
        me = Vec(1, 1, 0)
        for _ in range(5):
            H.add_sight(LAY, me, Vec(20, 1, 0))
        for _ in range(4):
            H.add_sight(LAY, me, Vec(1, 20, 0))
        self.assertGreater(H.preaim(LAY, me, me, yes)[0].x, 15)
        blocked = lambda a, b: b.x < 10                          # (no line to the first: the next)
        self.assertGreater(H.preaim(LAY, me, me, blocked)[0].y, 15)

    def test_next_cells_count_half(self):
        for _ in range(6):
            H.add_sight(LAY, Vec(3, 1, 0), Vec(20, 1, 0))         # (the cell east of ours)
        q, n = H.preaim(LAY, Vec(1, 1, 0), Vec(1, 1, 0), yes)
        self.assertEqual(n, 3.0)

    def test_a_persons_own_angles_win_while_he_plays(self):
        me = Vec(1, 1, 0)
        for _ in range(6):
            H.add_sight(LAY, me, Vec(20, 1, 0))                   # (bots: east)
        for _ in range(4):
            H.add_sight(LAY, me, Vec(1, 20, 0), name="Owner")     # (him: north)
        self.assertGreater(H.preaim(LAY, me, me, yes)[0].x, 15)
        self.assertGreater(H.preaim(LAY, me, me, yes, people=("Owner",))[0].y, 15)

    def test_written_to_its_file(self):
        for _ in range(H.SAVE_EVERY_N):
            H.add_sight(LAY, Vec(), Vec(9, 0, 0))
        with open(os.path.join(self.tmp.name, H.SIGHTS_FILE), encoding="utf-8") as f:
            self.assertIn(LAY, json.load(f))

    def test_bot_records_a_new_sighting_only(self):
        b = noble_bot()
        me, foe = man(1, 0, Vec(1, 1, 0)), man(2, 1, Vec(20, 1, 0), is_bot=False, name="Owner")
        b.noble_sighted(10.0, me, foe)
        b.noble_eyes_at = {2: 9.0}                                # (in its eyes a second ago: not a new one)
        b.noble_sighted(10.0, me, foe)
        cells = H.store(H.SIGHTS_FILE).data[LAY]
        (e,) = cells[H.cell(me.pos)].values()
        self.assertEqual((e[0], e[4]), (1, {"Owner": 1}))
        d = noble_bot(tier="demon")
        d.noble_sighted(20.0, me, foe)
        self.assertEqual(e[0], 1)                                 # (Demon: nothing)

    def test_bot_looks_there(self):
        b = noble_bot()
        b.T = lambda: types.SimpleNamespace(los=yes)
        me = man(1, 0, Vec(1, 1, 0))
        for _ in range(4):
            H.add_sight(LAY, me.pos, Vec(20, 1, 0))
        q = b.noble_preaim(5.0, me)
        self.assertGreater(q.x, 15)


class EscapeTests(Folder):
    def test_his_own_then_everyones(self):
        a = Vec(1, 1, 0)
        for _ in range(2):
            H.add_escape(LAY, "Owner", a, Vec(10, 10, 0))
        self.assertIsNone(H.escape_to(LAY, "Owner", a))
        H.add_escape(LAY, "Owner", a, Vec(10.5, 10, 0))
        p, n, share = H.escape_to(LAY, "Owner", a)
        self.assertEqual((n, share), (3, 1.0))
        self.assertAlmostEqual(p.x, 10.17, places=1)
        self.assertIsNone(H.escape_to(LAY, "Friend", a))           # (3 of all people's: under ESCAPE_MIN_ALL)
        for _ in range(3):
            H.add_escape(LAY, "Other", a, Vec(10, 10, 0))
        self.assertEqual(H.escape_to(LAY, "Friend", a)[1], 6)

    def test_no_place_he_mostly_goes(self):
        a = Vec(1, 1, 0)
        for x in (10, 20, 30, 40):
            H.add_escape(LAY, "Owner", a, Vec(x, 0, 0))
        self.assertIsNone(H.escape_to(LAY, "Owner", a))

    def test_watch_a_hurt_person_leaving_sight(self):
        me = man(1, 0, Vec())
        hurt = man(2, 1, Vec(5, 0, 0), shield=0.2, is_bot=False, name="Owner")
        bot_ = man(3, 1, Vec(6, 0, 0), shield=0.2)
        w = H.EscapeWatch(LAY)
        w.tick(0.0, Snapshot(0.0, [me, hurt, bot_]), me, [2, 3])
        w.tick(0.1, Snapshot(0.1, [me, hurt, bot_]), me, [])
        self.assertEqual(len(w.pending), 1)                       # (a person only)
        hurt.pos = Vec(15, 3, 0)
        w.tick(2.7, Snapshot(2.7, [me, hurt, bot_]), me, [])
        e = H.store(H.ESCAPES_FILE).data[LAY]["Owner"][H.cell(Vec(5, 0, 0))]
        self.assertEqual(list(e.values())[0][0], 1)

    def test_its_own_death_is_no_escape(self):
        me, hurt = man(1, 0, Vec()), man(2, 1, Vec(5, 0, 0), shield=0.2, is_bot=False, name="Owner")
        w = H.EscapeWatch(LAY)
        w.tick(0.0, Snapshot(0.0, [me, hurt]), me, [2])
        me.alive = False
        w.tick(0.1, Snapshot(0.1, [me, hurt]), me, [2])
        self.assertEqual(w.pending, [])

    def test_bot_guesses_where_he_goes_hurt(self):
        b = noble_bot()
        b.noble_names = {2: "Owner"}
        b.per = types.SimpleNamespace(est_shield=lambda k, now, sl: 0.2)
        for _ in range(3):
            H.add_escape(LAY, "Owner", Vec(5, 0, 0), Vec(15, 3, 0))
        belief = types.SimpleNamespace(pos=Vec(5, 0, 0), seen=False, t=1.0)
        self.assertIsNone(b.noble_escape_guess(1.5, 2, belief))   # (not long gone)
        self.assertAlmostEqual(b.noble_escape_guess(3.0, 2, belief).x, 15.0)
        b.per = types.SimpleNamespace(est_shield=lambda k, now, sl: 0.9)
        self.assertIsNone(b.noble_escape_guess(3.0, 2, belief))   # (healthy)
        self.assertIsNone(b.noble_escape_guess(3.0, 7, belief))   # (a bot: no name)


class DodgeTests(Folder):
    def test_picks_the_cheapest(self):
        for _ in range(10):
            for st in H.DODGES:
                H.add_dodge("reach", st, 0.02 if st == "keep" else 0.3)
        rng = types.SimpleNamespace(random=lambda: 0.9, choice=random.choice)
        self.assertEqual(H.dodge_pick("reach", rng), "keep")
        self.assertEqual(H.dodge_pick("h3", rng), "flip")          # (nothing learned there: the first)

    def test_his_own_count_weighs_more(self):
        for _ in range(30):
            H.add_dodge("reach", "keep", 0.02)
        for st in H.DODGES[:-1]:
            if st != "keep":
                for _ in range(10):
                    H.add_dodge("reach", st, 0.3)
        for _ in range(10):
            H.add_dodge("reach", "stop", 0.3)
        for _ in range(8):
            H.add_dodge("reach", "keep", 1.0, name="Owner")      # (against him keeping on cost it dear)
        rng = types.SimpleNamespace(random=lambda: 0.9, choice=random.choice)
        self.assertEqual(H.dodge_pick("reach", rng), "keep")
        self.assertNotEqual(H.dodge_pick("reach", rng, "Owner"), "keep")

    def test_watch_costs_the_damage_or_its_death(self):
        me = man(1, 0, Vec())
        w = H.DodgeWatch("reach")
        w.juked(0.0, me, "jump")
        me.shield = 0.7
        w.tick(0.3, me)
        self.assertEqual(len(w.pending), 1)
        w.tick(0.7, me)
        self.assertAlmostEqual(H.dodge_cost("reach", "jump")[0], (0.3 + H.DODGE_PRIOR * H.DODGE_PRIOR_N) / 4)
        w.juked(1.0, me, "stop")
        me.alive = False
        w.tick(1.1, me)
        self.assertEqual(H.store(H.DODGES_FILE).data["reach"]["all"]["stop"], [1, 1.7])

    def test_the_damage_it_deals_counts_off(self):
        me, foe = man(1, 0, Vec()), man(2, 1, Vec(8, 0, 0))
        w = H.DodgeWatch("reach")
        w.juked(0.0, me, "keep", foe=foe)
        me.shield, foe.shield = 0.8, 0.3                           # (took 0.2, dealt 0.7)
        w.tick(0.7, me, Snapshot(0.7, [me, foe]))
        self.assertEqual(H.store(H.DODGES_FILE).data["reach"]["all"]["keep"], [1, -0.5])
        w.juked(1.0, me, "flip", foe=foe)
        foe.alive = False                                          # (his death: all he had left)
        w.tick(1.7, me, Snapshot(1.7, [me, foe]))
        self.assertEqual(H.store(H.DODGES_FILE).data["reach"]["all"]["flip"], [1, -1.3])

    def test_bot_dodge_noble_only(self):
        b = noble_bot()
        b.per = types.SimpleNamespace(attacker_id=None)
        b.strafe_dir, b.next_strafe_flip = 1, 0.0
        me, act = man(1, 0, Vec()), types.SimpleNamespace(jump=False)
        self.assertTrue(b.noble_dodge(1.0, me, act, None))
        self.assertEqual(len(b.noble_dodges.pending), 1)
        self.assertGreater(b.next_strafe_flip, 1.0)
        d = noble_bot(tier="demon")
        self.assertFalse(d.noble_dodge(1.0, me, act, None))


class FocusTests(Folder):
    def test_focus_and_solo_fights(self):
        me, mate, foe = man(1, 0, Vec()), man(3, 0, Vec(1, 0, 0)), man(2, 1, Vec(5, 0, 0))
        w = H.FocusWatch("reach")
        sn = Snapshot(0.0, [me, mate, foe])
        w.tick(0.0, sn, me, 2, True, False)
        w.tick(0.5, sn, me, 2, True, True)                        # (a teammate on him: focus)
        foe.alive = False
        w.tick(1.0, sn, me, 2, False, False)
        foe.alive = True
        w.tick(2.0, sn, me, 2, True, False)                       # (a new fight, alone)
        mate.alive = False                                        # (a teammate down meanwhile)
        w.tick(2.5, sn, me, 2, True, False)
        me.alive = False
        w.tick(3.0, sn, me, 2, True, False)
        d = H.store(H.FOCUS_FILE).data["reach"]
        self.assertEqual(d["focus"]["0"], [1, 1.0])
        self.assertEqual(d["solo"]["0"], [1, -1.0 - H.FOCUS_MATE_COST])

    def test_a_break_is_not_counted(self):
        me, foe = man(1, 0, Vec()), man(2, 1, Vec(5, 0, 0))
        w = H.FocusWatch("reach")
        sn = Snapshot(0.0, [me, foe])
        w.tick(0.0, sn, me, 2, True, False)
        w.tick(1.0, sn, me, None, False, False)
        w.tick(1.0 + H.FOCUS_DROP_S + 0.1, sn, me, None, False, False)
        self.assertIsNone(w.fight)
        self.assertNotIn("reach", H.store(H.FOCUS_FILE).data)

    def test_lean_needs_both_and_an_edge(self):
        for _ in range(H.FOCUS_MIN):
            H.add_fight("reach", "focus", 1, 0.6)
        self.assertEqual(H.focus_lean("reach", 1), 0)
        for _ in range(H.FOCUS_MIN):
            H.add_fight("reach", "solo", 1, 0.1)
        self.assertEqual(H.focus_lean("reach", 1), 1)
        for _ in range(3 * H.FOCUS_MIN):
            H.add_fight("reach", "solo", 1, 1.0)
        self.assertEqual(H.focus_lean("reach", 1), -1)

    def test_bot_scores_a_teammates_man(self):
        b = noble_bot()
        me, foe = man(1, 0, Vec()), man(2, 1, Vec(10, 0, 0))
        b.noble_mate_on = lambda now, me_, k: k == 2
        for kind, v in (("focus", 0.8), ("solo", 0.0)):
            for _ in range(H.FOCUS_MIN):
                H.add_fight("reach", kind, H.focus_band(10.0), v)
        scored = {2: 10.0}
        b.noble_focus_scores(0.0, me, Snapshot(0.0, [me, foe]), scored)
        self.assertAlmostEqual(scored[2], 10.0 * H.FOCUS_BONUS)
        self.assertEqual(noble_bot(tier="demon").noble_focus_lean(me, foe), 0)


class SimWritesNothing(unittest.TestCase):
    def test_banshee_sim_turns_saving_off(self):
        was, old = noble.SAVE, sys.modules.pop("banshee_sim", None)
        try:
            noble.SAVE = True
            sys.path.insert(0, str(ROOT / "tools"))
            import banshee_sim  # noqa: F401
            self.assertFalse(noble.SAVE)
        finally:
            noble.SAVE = was
            if old is not None:
                sys.modules["banshee_sim"] = old


if __name__ == "__main__":
    unittest.main()
