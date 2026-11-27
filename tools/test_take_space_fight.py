"""(custom, Nov 27) Demon, Mythic and Noble walk on to their Take Space spot while fighting a man in view, as on a power
weapon run (Bot.take_space, on_way_target): while the fight is one it wins; losing, or hurt, the usual choice; at the
spot, the spot's own fights. The owner: "Take Space / hot spot add this to the shoots while still walking to it"."""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_take_space import Base, man, mk, snap  # noqa: E402
from brain import bot  # noqa: E402
from brain.core import Vec  # noqa: E402


def started(odds):
    b, me = mk(), man(1, 0, Vec(0, 0, 0))
    b.per.beliefs[9] = types.SimpleNamespace(pos=Vec(12, 0, 0), t=2.9)
    b.kill_seen = (1.5, Vec(5, 0, 0))
    b.take_space(2.0, me, snap(me), {}, [])                    # (a kill: its spot picked)
    b.odds_threats = lambda *a, **k: [(9, (1.0, 1.0, 1.0))]
    b._odds = odds
    return b, me


class FightOnTheWayTests(Base):
    def setUp(self):
        super().setUp()
        self._sim = bot.odds_model.simulate

    def tearDown(self):
        bot.odds_model.simulate = self._sim
        super().tearDown()

    def go(self, b, me, now, seen, scores=None):
        bot.odds_model.simulate = lambda th: b._odds
        scores = dict(scores or {})
        b.take_space(now, me, snap(me), scores, list(seen))
        return scores

    def test_a_fight_it_wins_keeps_the_walk_to_the_spot(self):
        b, me = started(odds=2.0)
        spot = b.space["spot"]
        sc = self.go(b, me, 3.0, [9], {("fight", 9): 3.1})
        self.assertGreater(sc[("hold", spot)], sc[("fight", 9)])  # (on to it, shooting him on the way)

    def test_a_fight_it_loses_or_hurt_is_the_usual_choice(self):
        b, me = started(odds=0.5)
        sc = self.go(b, me, 3.0, [9], {("fight", 9): 3.1})
        self.assertNotIn(("hold", b.space["spot"]), sc)
        b, me = started(odds=2.0)
        me.shield = 0.4
        sc = self.go(b, me, 3.0, [9], {("fight", 9): 3.1})
        self.assertEqual(sc, {("fight", 9): 3.1})

    def test_at_the_spot_its_fights_win(self):
        b, me = started(odds=2.0)
        me.pos = b.space["spot"]
        sc = self.go(b, me, 3.0, [9], {("fight", 9): 3.1})
        self.assertNotIn(("hold", b.space["spot"]), sc)


class OnWayTests(Base):
    def scene(self, at=None, tier="demon"):
        b, me = mk(tier), man(1, 0, Vec(0, 0, 0))
        b.space = dict(steps=0, until=50.0, spot=Vec(10, 0, 0), at=at, kills=0, held=[], why="")
        b.per = types.SimpleNamespace(beliefs={9: types.SimpleNamespace(pos=Vec(12, 0, 0), t=1.0)},
                                      visible_enemies=lambda: [9])
        b.pick_target = lambda now, me_, sn, seen: seen[0]
        b.dry = lambda me_: False
        return b, me

    def test_fights_on_the_way_to_its_spot(self):
        b, me = self.scene()
        self.assertEqual(b.on_way_target(1.0, me, snap(me), "hold", Vec(10, 0, 0)), 9)

    def test_not_once_there_nor_another_hold_nor_below_demon_rules(self):
        b, me = self.scene(at=0.5)
        self.assertIsNone(b.on_way_target(1.0, me, snap(me), "hold", Vec(10, 0, 0)))
        b, me = self.scene()
        self.assertIsNone(b.on_way_target(1.0, me, snap(me), "hold", Vec(-5, 3, 0)))   # (a hold that is not the spot)
        b, me = self.scene(tier="top")
        self.assertIsNone(b.on_way_target(1.0, me, snap(me), "hold", Vec(10, 0, 0)))


if __name__ == "__main__":
    unittest.main()
