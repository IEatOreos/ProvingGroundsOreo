"""(custom, Nov 26) One bot of a team runs for a power weapon spawn at a time (brain/bot.py TEAM_POWER_RUNS, Bot.power_claim,
Bot.power_taken, best_item): the owner's Boneyard report 20261126-200759, "My team on boneyard just likes to accumulate
around the stairs below our teams sniper", up to 5 of his bots on the sniper's run at once.

Run: python -m unittest discover -s tools -p test_power_claim.py
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                                    # noqa: E402
from brain.bot import Bot                                          # noqa: E402
from brain.core import PlayerState, Vec                            # noqa: E402
from brain.profiles import make_profile                            # noqa: E402

SNIPER = Vec(277.2, 112.6, -6.4)
NEEDLER = Vec(277.0, 119.0, -10.2)


def a_map():
    return {"name": "reach_test", "items": [dict(name="sniper", kind="weapon", value=0.9, pos=SNIPER),
                                            dict(name="needle_rifle", kind="weapon", value=0.3, pos=NEEDLER)]}


class PowerClaim(unittest.TestCase):
    def setUp(self):
        botmod.TEAM_POWER_RUNS.clear()
        self.m = a_map()

    def tearDown(self):
        botmod.TEAM_POWER_RUNS.clear()

    def bot(self, k, team=0):
        return Bot(k, team, make_profile("top", "rusher", random.Random(3)), self.m, random.Random(5))

    def runs(self, b, me, now=10.0):
        b.goal = ("item", SNIPER)
        b.power_claim(now, me, None)

    def best(self, b, me, now=10.0):
        it = b.best_item(now, me)
        return it[0] if it else None

    def test_alone_it_goes_for_the_sniper(self):
        me = PlayerState(2, 0, "b", Vec(285.0, 116.0, -10.4))
        self.assertEqual(self.best(self.bot(2), me), SNIPER)

    def test_a_nearer_teammate_on_the_run_has_it(self):
        mate = PlayerState(4, 0, "a", Vec(280.0, 112.0, -10.4))
        self.runs(self.bot(4), mate)
        me = PlayerState(2, 0, "b", Vec(290.0, 116.0, -10.4))
        self.assertNotEqual(self.best(self.bot(2), me), SNIPER)

    def test_a_farther_teammate_does_not_stop_it(self):
        mate = PlayerState(4, 0, "a", Vec(300.0, 130.0, -10.4))
        self.runs(self.bot(4), mate)
        me = PlayerState(2, 0, "b", Vec(281.0, 113.0, -10.4))
        self.assertEqual(self.best(self.bot(2), me), SNIPER)

    def test_an_enemy_on_the_run_does_not_stop_it(self):
        foe = PlayerState(4, 1, "a", Vec(279.0, 112.0, -10.4))
        self.runs(self.bot(4, team=1), foe)
        me = PlayerState(2, 0, "b", Vec(290.0, 116.0, -10.4))
        self.assertEqual(self.best(self.bot(2), me), SNIPER)

    def test_an_old_claim_runs_out(self):
        mate = PlayerState(4, 0, "a", Vec(280.0, 112.0, -10.4))
        self.runs(self.bot(4), mate, now=10.0)
        me = PlayerState(2, 0, "b", Vec(290.0, 116.0, -10.4))
        self.assertEqual(self.best(self.bot(2), me, now=10.0 + botmod.POWER_CLAIM_FRESH + 0.1), SNIPER)

    def test_another_goal_drops_the_claim(self):
        b, mate = self.bot(4), PlayerState(4, 0, "a", Vec(280.0, 112.0, -10.4))
        self.runs(b, mate)
        b.goal = ("roam", None)
        b.power_claim(10.5, mate, None)
        self.assertEqual(botmod.TEAM_POWER_RUNS[("reach_test", 0)], {})

    def test_a_plain_gun_is_never_claimed(self):
        b, mate = self.bot(4), PlayerState(4, 0, "a", Vec(277.0, 118.0, -10.4))
        b.goal = ("item", NEEDLER)
        b.power_claim(10.0, mate, None)
        self.assertEqual(botmod.TEAM_POWER_RUNS[("reach_test", 0)], {})


if __name__ == "__main__":
    unittest.main()
