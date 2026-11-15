"""(custom, Nov 13) Stockpile: a carrier drops the flag in its own goal (Bot.stockpile_drop). The owner: "theyll go pick up
a flag ... and then just hold it inside their capture point ... they wont drop it until they die". Live Launch Station
20261113-220813: carriers stood 0.1 u from their goal's centre holding the flag up to 32 s, until killed. 223850: a
weapon slot chosen every tick there did not drop it, so the keys are tapped (the weapon switch, then Use)."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                            # noqa: E402
from brain import profiles                                 # noqa: E402
from brain.bot import Bot                                  # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec  # noqa: E402

OURS, THEIRS = Vec(-147.6, -4.0, 6.1), Vec(-161.1, -3.9, 6.1)


def scene(at=OURS, mode="stockpile", flag=True, weapons=("dmr", "assault_rifle", "flag")):
    b = Bot(1, 0, profiles.make_profile("demon", "objector", random.Random(1)), dict(name="test"))
    me = PlayerState(1, 0, "b", at)
    me.has_flag = flag
    me.weapons = list(weapons)
    me.weapon = "flag" if flag else weapons[0]
    snap = Snapshot(100, [me], mode=mode)
    snap.obj_goals = {0: [OURS], 1: [THEIRS]}
    return b, me, snap, Action(weapon=-1)


def presses(b, me, snap, t0, t1, dt=1 / 30):
    """[(t, cycle, action)] each tick from t0 to t1."""
    out, t = [], t0
    while t < t1:
        act = Action(weapon=-1)
        act.action = act.cycle = False
        b.stockpile_drop(t, me, snap, act)
        out.append((t, act.cycle, act.action, act.weapon))
        t += dt
    return out


class StockpileDropTests(unittest.TestCase):
    def test_taps_switch_then_use_in_our_goal(self):
        for off in (Vec(0, 0, 0), Vec(0.5, 0.3, 0), Vec(0.1, 0, 1.0)):
            b, me, snap, _ = scene(at=OURS + off)
            ticks = presses(b, me, snap, 10.0, 10.0 + 2 * botmod.STP_DROP_CYCLE)
            cyc = [t for t, c, a, w in ticks if c]
            use = [t for t, c, a, w in ticks if a]
            self.assertTrue(cyc and use, off)
            self.assertFalse(any(c and a for t, c, a, w in ticks))                  # one key at a time
            self.assertTrue(all(w == -1 for t, c, a, w in ticks))                   # no slot choice (did nothing live)
            self.assertLess(cyc[0], use[0])                                         # the switch first
            self.assertAlmostEqual(cyc[0], 10.0 + botmod.STP_SETTLE, delta=1 / 30)  # once still STP_SETTLE s
            # a press is held, then let go: some ticks with neither key between the taps
            self.assertTrue(any(not c and not a for t, c, a, w in ticks))
            # both taps come again on the next cycle
            self.assertTrue(any(t >= 10.0 + botmod.STP_DROP_CYCLE for t in cyc))

    def test_stops_before_it_drops(self):
        # the owner: "stop in the capture zone then switch weapons so momentum doesnt carry the flag"
        b, me, snap, _ = scene()
        me.vel = Vec(4.0, 1.0, 0)                                                   # still running in
        act = Action(weapon=-1, forward=1.0, strafe=0.5)
        act.sprint = act.jump = True
        act.action = act.cycle = False
        self.assertTrue(b.stockpile_drop(10.0, me, snap, act))
        self.assertEqual((act.forward, act.strafe, act.sprint, act.jump), (0.0, 0.0, False, False))
        self.assertFalse(act.cycle or act.action)                                   # no tap while it moves
        ticks = presses(b, me, snap, 10.0, 12.0)
        self.assertFalse(any(c or a for t, c, a, w in ticks))                       # never, while it keeps moving
        me.vel = Vec(0.1, 0, 0)                                                     # stopped
        ticks = presses(b, me, snap, 12.0, 12.5)
        cyc = [t for t, c, a, w in ticks if c]
        self.assertTrue(cyc)
        self.assertGreaterEqual(cyc[0], 12.0 + botmod.STP_SETTLE - 1e-9)           # after the settle
        me.vel = Vec(2.0, 0, 0)                                                     # pushed: stops and settles again
        ticks = presses(b, me, snap, 12.5, 12.7)
        self.assertFalse(any(c or a for t, c, a, w in ticks))

    def test_cycle_restarts_on_each_arrival(self):
        b, me, snap, _ = scene()
        presses(b, me, snap, 10.0, 10.5)
        me.pos = OURS + Vec(5, 0, 0)                                                # walked off
        presses(b, me, snap, 10.5, 11.0)
        me.pos = OURS
        ticks = presses(b, me, snap, 20.0, 20.0 + botmod.STP_SETTLE + 0.1)
        cyc = [t for t, c, a, w in ticks if c]
        self.assertTrue(cyc)
        self.assertAlmostEqual(cyc[0], 20.0 + botmod.STP_SETTLE, delta=1 / 30)     # settles anew, then taps

    def test_keeps_it_elsewhere(self):
        cases = (dict(at=OURS + Vec(botmod.STP_DROP_R + 0.2, 0, 0)),       # not in the goal yet
                 dict(at=OURS + Vec(0, 0, botmod.STP_DROP_DZ + 0.5)),      # the floor above it
                 dict(at=THEIRS),                                          # their goal
                 dict(flag=False),                                         # not carrying
                 dict(mode="ctf"), dict(mode="assault"), dict(mode="oddball"))
        for kw in cases:
            b, me, snap, act = scene(**kw)
            act.action = act.cycle = False
            self.assertFalse(b.stockpile_drop(10.0, me, snap, act), kw)
            self.assertFalse(act.cycle or act.action, kw)

    def test_not_in_a_vehicle(self):
        b, me, snap, act = scene()
        me.vehicle = 7
        self.assertFalse(b.stockpile_drop(10.0, me, snap, act))

    def test_last_in_plan(self):
        src = (Path(__file__).resolve().parents[1] / "brain" / "bot.py").read_text(encoding="utf-8")
        i = src.index("        s.stockpile_drop(now, me, snap, act)\n        return act\n")
        self.assertGreater(i, src.index("act.weapon = s.choose_weapon(now, me, *weapon_goal, snap)"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
