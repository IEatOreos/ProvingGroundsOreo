"""(custom, Nov 22) An armor lock the game ended is let go (Kit.act, LOCK_ENDED_S). The owner's "c2ir let me shoot him
twice before returning fire": live Ivory Tower 20261122-163607, a Demon's lock came on, the game ended it, and the hold
went on 1.4 s, no shot and no step, while he emptied its shield."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import equipment as E  # noqa: E402
from brain.bot import Belief, Bot  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


def scene():
    bot = Bot(0, 0, make_profile("demon", "rusher", random.Random(3)), {"name": "reach_test"}, random.Random(5))
    bot.game = bot.kit.game = "reach"
    me = PlayerState(0, 0, "bot", Vec(), equipment="armor_lock")
    foe = PlayerState(1, 1, "enemy", Vec(2.3, 0, 0), weapon="dmr")
    bot.per.beliefs[1] = Belief(foe.pos, Vec(), 10, True, "eyes")
    bot.per.recognized.add(1)
    bot.goal = ("fight", 1)
    bot.kit.kind = "armor_lock"
    bot.kit.energy = E.Energy("reach", "armor_lock")
    bot.kit.press = ("armor_lock", "self", None, 3.0, "armor lock: grenade at my feet")
    bot.kit.hold_until, bot.kit.press_t0, bot.kit.press_hp = 13.0, 10.0, (1.0, 1.0)
    return bot, me, Snapshot(10, [me, foe])


def tick(bot, me, snap, now):
    a = Action()
    snap.time = now
    note = bot.kit.act(bot, now, 1 / 30, me, snap, a)
    return a, note


class LockEndedTests(unittest.TestCase):
    def test_held_while_locked(self):
        bot, me, snap = scene()
        me.ability_on = True
        a, _ = tick(bot, me, snap, 10.3)
        self.assertTrue(a.ability)
        self.assertFalse(a.fire)

    def test_let_go_once_the_game_ends_it(self):
        bot, me, snap = scene()
        me.ability_on = True
        tick(bot, me, snap, 10.3)
        me.ability_on = False
        a, _ = tick(bot, me, snap, 10.3 + E.LOCK_ENDED_S / 2)        # (the reader's lag: still held)
        self.assertTrue(a.ability)
        a, note = tick(bot, me, snap, 10.3 + E.LOCK_ENDED_S + 0.05)
        self.assertFalse(a.ability or a.equipment)
        self.assertEqual(note, "armor_lock: the lock ended, fighting on")
        self.assertEqual(bot.kit.energy.level, 0.0)
        a, _ = tick(bot, me, snap, 10.7)                               # (no new press straight after)
        self.assertFalse(a.ability or a.equipment)

    def test_never_locked_is_the_old_rule(self):
        bot, me, snap = scene()
        me.shield = 0.75                                               # (hurt, never on: the earlier let-go)
        a, note = tick(bot, me, snap, 10.3)
        self.assertEqual(note, "armor_lock: did not lock, fighting on")


if __name__ == "__main__":
    unittest.main()
