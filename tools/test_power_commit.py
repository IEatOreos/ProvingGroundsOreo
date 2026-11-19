"""(custom, Nov 18) A run at a power weapon is finished while it would win against the men who can fight it, and not
with its shield under half and an enemy near (Bot.power_commit). The owner: "commit to them unless an enemy is close",
then "if the bot thinks it can win the fight from any range it commits to the push" and the recharge first when hurt
with an enemy near. Forge World 20261118-180057: about 170 runs at the rockets ended after 1-4 s for a hunt, a retreat
or a fight and were begun again."""
import random
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot as botmod                                # noqa: E402
from brain.bot import Belief, Bot                              # noqa: E402
from brain.core import PlayerState, Snapshot, Vec              # noqa: E402
from brain.profiles import make_profile                        # noqa: E402
from test_h4_pickup_board import Flat                          # noqa: E402

ROCKETS = Vec(20.0, 0.0, 1.5)
RIFLE = Vec(-10.0, 0.0, 0.0)


class Lines(Flat):
    """Open lines only from the men standing at these x."""
    def __init__(s, open_x=()):
        s.open_x = set(open_x)

    def los(s, a, b, mode=None):
        return round(a.x) in s.open_x


def scene(goal=("item", ROCKETS), tier="demon", men=(), open_x=(), shield=1.0):
    m = {"name": "reach_test", "items": [
        {"kind": "weapon", "name": "rocket_launcher", "value": 0.95, "pos": ROCKETS},
        {"kind": "weapon", "name": "dmr", "value": 0.5, "pos": RIFLE}]}
    b = Bot(0, 0, make_profile(tier, "objector", random.Random(1)), m, random.Random(2))
    b.notes = []
    b.goal = goal
    t = Lines(open_x)
    b.T = lambda: t
    me = PlayerState(0, 0, "bot", Vec(), shield=shield)
    players = [me]
    for k, (pos, src) in men.items() if isinstance(men, dict) else ():
        players.append(PlayerState(k, 1, f"foe{k}", pos))
        b.per.beliefs[k] = Belief(pos, Vec(), 9.9, src == "eyes", src)
    snap = Snapshot(10.0, players, mode="slayer")
    return b, me, snap


def scores():
    return {("item", ROCKETS): 1.6, ("hunt", Vec(5, 5, 0)): 3.0, ("retreat", Vec(-3, 0, 0)): 2.3,
            ("fight", 4): 1.7}


def odds(value):
    """The fight odds fixed (brain/odds.py's model is tested on its own)."""
    return mock.patch.object(botmod.odds_model, "simulate", return_value=value)


def run(b, me, snap, sc, hit=False, now=10.0):
    with mock.patch.object(Bot, "odds_threats", lambda s, now_, me_, snap_, seen, only=None, all_aware=False:
                           [(only, (1.0, 1.0, 0.0))]):
        b.power_commit(now, me, snap, sc, hit)
    return sc


class PushTests(unittest.TestCase):
    def test_nobody_who_can_fight_it_the_run_beats_everything(self):
        b, me, snap = scene(men={4: (Vec(14, 6, 0), "radar")})          # 15 u off, behind a wall
        sc = run(b, me, snap, scores())
        self.assertEqual(max(sc, key=sc.get), ("item", ROCKETS))
        self.assertAlmostEqual(sc[("item", ROCKETS)], 3.0 + botmod.POWER_COMMIT_MARGIN)
        self.assertIn("power weapon run: committed", b.notes)

    def test_a_man_with_a_line_at_any_range_a_win_pushes_on_a_loss_lets_go(self):
        for far in (12.0, 30.0):
            b, me, snap = scene(men={4: (Vec(far, 0, 0), "eyes")}, open_x=(far,))
            with odds(1.4):
                sc = run(b, me, snap, scores())
            self.assertEqual(max(sc, key=sc.get), ("item", ROCKETS), far)
            self.assertIn("power weapon run: committed, wins against 1", b.notes)
            b, me, snap = scene(men={4: (Vec(far, 0, 0), "eyes")}, open_x=(far,))
            with odds(0.7):
                self.assertEqual(run(b, me, snap, scores()), scores(), far)

    def test_close_behind_a_wall_or_the_man_shooting_it_count_too(self):
        b, me, snap = scene(men={4: (Vec(5, 3, 0), "radar")})            # 5.8 u off, no line
        with odds(0.7):
            self.assertEqual(run(b, me, snap, scores()), scores())
        with odds(1.2):
            self.assertGreater(run(b, me, snap, scores())[("item", ROCKETS)], 3.0)
        b, me, snap = scene(men={4: (Vec(25, 0, 0), "hit")})             # 25 u off, behind a wall, shooting it
        b.per.attacker_id = 4
        with odds(0.7):
            self.assertEqual(run(b, me, snap, scores(), hit=True), scores())
        with odds(1.2):
            self.assertGreater(run(b, me, snap, scores(), hit=True)[("item", ROCKETS)], 3.0)

    def test_men_past_the_watch_range_an_old_dot_or_a_mate_do_not_count(self):
        b, me, snap = scene(men={4: (Vec(botmod.DEMON_WATCH_R + 5, 0, 0), "eyes")},
                            open_x=(botmod.DEMON_WATCH_R + 5,))
        with odds(0.1):
            self.assertGreater(run(b, me, snap, scores())[("item", ROCKETS)], 3.0)
        b, me, snap = scene(men={4: (Vec(5, 3, 0), "radar")})
        b.per.beliefs[4].t = 10.0 - botmod.POWER_COMMIT_FRESH - 0.1
        with odds(0.1):
            self.assertGreater(run(b, me, snap, scores())[("item", ROCKETS)], 3.0)


class RechargeTests(unittest.TestCase):
    def test_hurt_with_a_man_near_recharges_first(self):
        b, me, snap = scene(men={4: (Vec(15, 0, 0), "radar")}, shield=0.3)     # 15 u, behind a wall
        with odds(9.0):
            self.assertEqual(run(b, me, snap, scores()), scores())
        b, me, snap = scene(men={4: (Vec(botmod.POWER_RECHARGE_R + 3, 0, 0), "radar")}, shield=0.3)
        with odds(9.0):
            self.assertGreater(run(b, me, snap, scores())[("item", ROCKETS)], 3.0)   # nobody near: on its way
        b, me, snap = scene(men={4: (Vec(15, 0, 0), "radar")}, shield=0.6)
        with odds(9.0):
            self.assertGreater(run(b, me, snap, scores())[("item", ROCKETS)], 3.0)   # half and more: on
        b, me, snap = scene(men={4: (Vec(15, 0, 0), "radar")}, shield=0.0)
        snap.shieldless = True                                                   # SWAT: no shield to wait for
        with odds(9.0):
            self.assertGreater(run(b, me, snap, scores())[("item", ROCKETS)], 3.0)


class ScopeTests(unittest.TestCase):
    def test_only_a_power_weapon_still_scored_on_foot(self):
        b, me, snap = scene(goal=("item", RIFLE))
        sc = scores()
        sc[("item", RIFLE)] = 1.6
        run(b, me, snap, sc)
        self.assertEqual(sc[("item", RIFLE)], 1.6)                               # a DMR: no commitment
        b, me, snap = scene()
        sc = scores()
        del sc[("item", ROCKETS)]                                                # taken, or given up as unreachable
        run(b, me, snap, sc)
        self.assertNotIn(("item", ROCKETS), sc)
        for attr, val in (("vehicle", 7), ("has_flag", True)):
            b, me, snap = scene()
            setattr(me, attr, val)
            self.assertEqual(run(b, me, snap, scores()), scores(), attr)
        b, me, snap = scene()
        with mock.patch.object(botmod, "POWER_COMMIT", False):
            self.assertEqual(run(b, me, snap, scores()), scores())

    def test_other_tiers_keep_their_fights(self):
        b, me, snap = scene(tier="top")
        sc = scores()
        sc[("fight", 4)] = 3.8
        run(b, me, snap, sc)
        self.assertEqual(max(sc, key=sc.get), ("fight", 4))                     # no shooting on the way: it fights
        self.assertGreater(sc[("item", ROCKETS)], 3.0)                           # over the hunt and the retreat

    def test_a_run_too_long_is_let_go(self):
        b, me, snap = scene()
        run(b, me, snap, scores())
        self.assertEqual(run(b, me, snap, scores(), now=10.0 + botmod.POWER_COMMIT_MAX + 0.1), scores())
        b.goal = ("hunt", Vec(5, 5, 0))                                          # a new run starts a new clock
        run(b, me, snap, scores(), now=40.0)
        b.goal = ("item", ROCKETS)
        self.assertGreater(run(b, me, snap, scores(), now=41.0)[("item", ROCKETS)], 3.0)

    def test_wired_into_decide_before_the_flip_flop_rule(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index("    def decide(s, now, me, snap):")
        body = src[i:src.index("\n    def ", i + 10)]
        self.assertLess(body.index("s.power_commit(now, me, snap, scores, hit_recent)"),
                        body.index("scores[s.goal] += 0.2"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
