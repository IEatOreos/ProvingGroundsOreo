"""(custom, Nov 23) tools/live_bots.py full_rate: who thinks every pass (THINK_HALF). The owner on 8v8: "The bots play
really bad in 8v8", "Bug reports also show cosmic playing slow"; "Yes, do it" (fighters every pass, the rest every
other)."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import live_bots                                  # noqa: E402
from brain.core import PlayerState, Vec           # noqa: E402

NOW = 100.0


def scene(goal="patrol", role="mid", beliefs=None, losses=(), notes=(), vehicle=-1, flag=False):
    b = SimpleNamespace(goal=(goal, None), order=SimpleNamespace(role=role), notes=list(notes),
                        per=SimpleNamespace(beliefs=beliefs or {}, losses=list(losses)))
    me = PlayerState(1, 0, "b", Vec(0, 0, 0))
    me.vehicle, me.has_flag = vehicle, flag
    return b, me


def belief(age, source="eyes"):
    return SimpleNamespace(t=NOW - age, source=source)


class BigMatchesOnly(unittest.TestCase):
    """"Can we keep these thinking updates separate from the two modes 8v8 and 4v4?": 8v8 only."""

    def test_8v8_on_4v4_off(self):
        players = lambda n: SimpleNamespace(players=[PlayerState(i, i % 2, "p", Vec(0, 0, 0)) for i in range(n)])
        self.assertTrue(live_bots.think_half_on(players(16)))
        self.assertTrue(live_bots.think_half_on(players(12)))
        self.assertFalse(live_bots.think_half_on(players(8)))
        self.assertFalse(live_bots.think_half_on(players(10)))


class FullRate(unittest.TestCase):
    def test_a_plain_walk_is_half(self):
        self.assertFalse(live_bots.full_rate(*scene(), NOW))

    def test_fighting_driving_carrying(self):
        self.assertTrue(live_bots.full_rate(*scene(goal="fight"), NOW))
        self.assertTrue(live_bots.full_rate(*scene(role="drive"), NOW))
        self.assertTrue(live_bots.full_rate(*scene(vehicle=7), NOW))
        self.assertTrue(live_bots.full_rate(*scene(flag=True), NOW))

    def test_an_enemy_known_lately(self):
        self.assertTrue(live_bots.full_rate(*scene(beliefs={5: belief(2.0)}), NOW))
        self.assertTrue(live_bots.full_rate(*scene(beliefs={5: belief(1.0, "radar")}), NOW))
        self.assertFalse(live_bots.full_rate(*scene(beliefs={5: belief(5.0)}), NOW))
        self.assertFalse(live_bots.full_rate(*scene(beliefs={5: belief(1.0, "callout")}), NOW))

    def test_hurt_lately(self):
        self.assertTrue(live_bots.full_rate(*scene(losses=[(NOW - 1.0, 0.3)]), NOW))
        self.assertFalse(live_bots.full_rate(*scene(losses=[(NOW - 5.0, 0.3)]), NOW))

    def test_at_an_edge_or_a_jump(self):
        self.assertTrue(live_bots.full_rate(*scene(notes=["edge stop"]), NOW))
        self.assertTrue(live_bots.full_rate(*scene(notes=["wall ahead: stepping around"]), NOW))
        b, me = scene()
        b.jump_until = NOW + 0.5
        self.assertTrue(live_bots.full_rate(b, me, NOW))


if __name__ == "__main__":
    unittest.main()
