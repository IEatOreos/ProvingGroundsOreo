"""(custom, Nov 24) After a drop to fight, the gun's first round when the game lets it go (brain/bot.py drop_ready_wait,
DROP_READY_S): the owner's own drops, Condemned Neutral Bomb 20261124-185819, first rounds 0.57, 0.71, 0.57 s after;
"Record it and apply it to the bots"."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot as botmod                                     # noqa: E402
from brain.core import Action, Vec                                  # noqa: E402
from test_bomb_plant import NOW, drop, scene                        # noqa: E402


def dropped(b, me, snap, t=NOW):
    """The bomb gone from its hands at t (flag_fight_phase notes the drop)."""
    assert b.flag_fight_check(NOW, me, snap)
    drop(me, snap, Vec(12.0, 0, 0))
    b.flag_fight_phase(t, me, snap)


class DropReady(unittest.TestCase):
    def test_no_press_before_the_gun_is_ready(self):
        b, me, man, snap = scene()
        dropped(b, me, snap)
        for k in (0.0, 0.1, 0.3, 0.5, 0.56):
            act = Action(fire=True)
            b.notes = []
            self.assertTrue(b.drop_ready_wait(NOW + k, me, act), k)
            self.assertFalse(act.fire, k)

    def test_the_press_at_the_ready_tick_then_until_the_round_shows(self):
        b, me, man, snap = scene()
        dropped(b, me, snap)
        t = NOW + botmod.DROP_READY_S
        act = Action(fire=True)
        b.notes = []
        self.assertFalse(b.drop_ready_wait(t, me, act))                  # (no longer waiting: the press goes)
        self.assertTrue(b.retry_after_grenade(t, me, True, act, 12.0))
        self.assertTrue(act.fire)
        act = Action(fire=True)                                          # (the next tick: released, a fresh press)
        b.retry_after_grenade(t + 0.034, me, True, act, 12.0)
        self.assertFalse(act.fire)
        me.mag = [me.mag[0] - 1] + me.mag[1:] if me.mag else me.mag      # (the round shows: the retry ends)
        self.assertIsNone(getattr(b, "drop_ready", None))

    def test_dead_or_carrying_again_no_wait(self):
        b, me, man, snap = scene()
        dropped(b, me, snap)
        me.alive = False
        self.assertFalse(b.drop_ready_wait(NOW + 0.1, me, Action(fire=True)))
        self.assertIsNone(b.drop_ready)

    def test_the_owners_measure(self):
        self.assertEqual(botmod.DROP_READY_S, 0.57)
        self.assertEqual(botmod.drop_ready_s("dmr"), 0.57)
        self.assertEqual(botmod.drop_ready_s("rockets"), 0.89)
        self.assertEqual(botmod.drop_ready_s("sniper"), 0.57)          # (not measured yet: the DMR's)

    def test_rockets_wait_longer(self):
        b, me, man, snap = scene()
        assert b.flag_fight_check(NOW, me, snap)
        drop(me, snap, Vec(12.0, 0, 0))
        me.weapon, me.weapons = "rockets", ["rockets", "dmr"]
        b.flag_fight_phase(NOW, me, snap)
        b.notes = []
        act = Action(fire=True)
        self.assertTrue(b.drop_ready_wait(NOW + 0.7, me, act))          # (a DMR would be firing by now)
        self.assertFalse(act.fire)
        self.assertFalse(b.drop_ready_wait(NOW + 0.89, me, Action(fire=True)))


if __name__ == "__main__":
    unittest.main()
