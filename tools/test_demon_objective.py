"""(custom, Nov 13) Demon plays the objective when near it (Bot.demon_objective). The owner: "make demon bots play the
objective when theyre near it". Live Condemned Crazy King 20261113-204320: within 8 u of the hill the two Demons chose it
3% and 13% of the time, every other tier 30-85%."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                            # noqa: E402
from brain import profiles                                 # noqa: E402
from brain.bot import Bot, Order                           # noqa: E402
from brain.core import PlayerState, Snapshot, Vec          # noqa: E402

HILL = Vec(0, 0, 0)


def scene(tier="demon", at=Vec(8, 0, 0), role="defender", mode="king", foe_at=Vec(14, 0, 0)):
    b = Bot(1, 0, profiles.make_profile(tier, "objector", random.Random(1)), dict(name="test"))
    b.order = Order(role, HILL)
    b.dry = lambda me: False
    b.per.beliefs = {5: SimpleNamespace(pos=foe_at)}
    me = PlayerState(1, 0, "b", at)
    snap = Snapshot(100, [me, PlayerState(5, 1, "e", foe_at)], mode=mode)
    scores = {("objective", HILL): 1.8, ("item", Vec(-0.4, 0, 0)): 3.15, ("hunt", Vec(5, 5, 0)): 3.2,
              ("fight", 5): 3.19, ("retreat", Vec(20, 0, 0)): 1.0}
    return b, me, snap, scores


def best(scores):
    return max(scores, key=scores.get)[0]


class DemonObjectiveTests(unittest.TestCase):
    def test_near_the_hill_the_hill_wins(self):
        b, me, snap, scores = scene()
        b.demon_objective(me, snap, scores, [5])
        self.assertEqual(best(scores), "objective")
        for k, v in scores.items():
            if k[0] in ("item", "hunt", "fight"):
                self.assertLessEqual(v, 1.8 - botmod.DEMON_OBJ_MARGIN + 1e-9, k)
        self.assertEqual(scores[("retreat", Vec(20, 0, 0))], 1.0)          # a retreat is left alone

    def test_on_the_hill_it_fights_but_does_not_leave(self):
        b, me, snap, scores = scene(at=Vec(2, 0, 0))
        b.demon_objective(me, snap, scores, [5])
        self.assertEqual(scores[("fight", 5)], 3.19)                        # fights from inside it
        self.assertLess(scores[("item", Vec(-0.4, 0, 0))], 1.8)
        self.assertLess(scores[("hunt", Vec(5, 5, 0))], 1.8)

    def test_a_man_at_arms_length_is_still_fought(self):
        b, me, snap, scores = scene(foe_at=Vec(9.5, 0, 0))
        b.demon_objective(me, snap, scores, [5])
        self.assertEqual(scores[("fight", 5)], 3.19)

    def test_far_from_it_unchanged(self):
        b, me, snap, scores = scene(at=Vec(botmod.DEMON_OBJ_NEAR + 1, 0, 0))
        before = dict(scores)
        b.demon_objective(me, snap, scores, [5])
        self.assertEqual(scores, before)

    def test_only_demon_and_only_objective_modes_and_roles(self):
        # (Nov 18, owner: "Give mythic the same ruleset as demons") Mythic plays it too (profiles.demon_rules)
        for tier, mode, role in (("top", "king", "defender"), ("blind", "king", "defender"), ("demon", "slayer", "mid"),
                                 ("demon", "race", "runner"), ("demon", "ctf", "hunter"), ("demon", "ctf", "escort")):
            b, me, snap, scores = scene(tier=tier, mode=mode, role=role)
            before = dict(scores)
            b.demon_objective(me, snap, scores, [5])
            self.assertEqual(scores, before, (tier, mode, role))
        for tier in ("demon", "mythic"):
            for mode in ("king", "ctf", "oddball", "territories", "headhunter"):
                b, me, snap, scores = scene(tier=tier, mode=mode)
                b.demon_objective(me, snap, scores, [5])
                self.assertEqual(best(scores), "objective", (tier, mode))

    def test_dry_or_carrying_unchanged(self):
        b, me, snap, scores = scene()
        b.dry = lambda me: True
        before = dict(scores)
        b.demon_objective(me, snap, scores, [5])
        self.assertEqual(scores, before)
        b, me, snap, scores = scene()
        me.has_flag = True
        before = dict(scores)
        b.demon_objective(me, snap, scores, [5])
        self.assertEqual(scores, before)

    def test_a_teammate_on_it_lets_go(self):
        for mode, mate_at, holds in (("king", Vec(2.5, 0, 0), True), ("king", Vec(4.0, 0, 0), False),
                                     ("king", Vec(1.0, 0, 4.0), False), ("ctf", Vec(1.0, 1.0, 0), True),
                                     ("ctf", Vec(5.0, 0, 0), False)):
            b, me, snap, scores = scene(mode=mode)
            snap.hill, snap.hill_r = HILL, 3.0
            snap.players.append(PlayerState(2, 0, "mate", mate_at))
            before = dict(scores)
            b.demon_objective(me, snap, scores, [5])
            self.assertEqual(scores == before, holds, (mode, mate_at))
        b, me, snap, scores = scene()                                    # a dead teammate, an enemy: no hold
        snap.hill, snap.hill_r = HILL, 3.0
        dead = PlayerState(2, 0, "mate", Vec(1, 0, 0))
        dead.alive = False
        snap.players += [dead, PlayerState(3, 1, "foe", Vec(1, 0, 0))]
        b.demon_objective(me, snap, scores, [5])
        self.assertEqual(best(scores), "objective")

    def test_called_in_decide(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i, j = src.index("s.demon_objective(me, snap, scores, seen)"), src.index("shot_back = s.shoot_back(")
        self.assertGreater(i, j)                                         # after the shot-back and close-fight lifts


if __name__ == "__main__":
    unittest.main(verbosity=2)
