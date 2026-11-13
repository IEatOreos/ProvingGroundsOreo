"""(custom, Nov 13) The pre-nade (Bot.prenade): Legendary, Blind and Demon throw a grenade at the doorway an unseen man
is about to come through, then hold the angle. The owner: "when I 1v1 them I can throw a grenade at their doorway
before seeing them due to knowing the radar ... make only legendary blind and demons use the pre nade mechanic"."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod, profiles, scaling                       # noqa: E402
from brain.bot import PRENADE_HOLD, PRENADE_PER_MAN, Belief, Bot         # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec, angles_to, eye  # noqa: E402

DOOR_X = -6.0      # the corridor's doorway: the bot at the origin sees only x >= DOOR_X


class Corridor:
    """A straight corridor along x; a wall hides everything short of DOOR_X from the bot's end."""

    def path_ahead(self, a, b, n=80, **kw):
        d = b - a
        steps = min(n, int(d.flat() / 0.25))
        u = d.norm()
        return [a + u * (0.25 * (i + 1)) for i in range(steps)]

    def los(self, a, b, mode=None):
        return min(a.x, b.x) >= DOOR_X - 1e-6

    def walkable(self, p):
        return True


def make(tier="top", prof=None):
    p = prof or profiles.make_profile(tier, "rusher", random.Random(1))
    b = Bot(0, 0, p, {"name": "reach_test"}, random.Random(2))
    b._terrain = Corridor()
    b.notes = []
    b.aim.step = lambda now, dt, me, tid, at, vel, head, **kw: angles_to(eye(me), at)   # (the view goes where told)
    return b


def run(b, start_x=-10.0, vx=2.25, seen=False, mate_at=None, seconds=4.0, t0=10.0):
    """Ticks of prenade with a man at start_x walking +x at vx (known 0.1 s ago), the bot at the origin facing away."""
    me = PlayerState(0, 0, "bot", Vec(), yaw=3.14)
    him = PlayerState(1, 1, "enemy", Vec(start_x, 0, 0))
    players = [me, him] + ([PlayerState(2, 0, "mate", mate_at)] if mate_at is not None else [])
    b.per.beliefs[1] = Belief(Vec(start_x, 0, 0), Vec(vx, 0, 0), t0 - 0.1, seen, "radar")
    if seen:
        b.per.recognized.add(1)
    log, t = [], t0
    while t < t0 + seconds:
        b.notes = []
        act = Action(yaw=me.yaw, pitch=me.pitch, forward=1.0)
        on = b.prenade(t, 1 / 30, me, Snapshot(t, players), act)
        me.yaw, me.pitch = act.yaw, act.pitch
        log.append((round(t - t0, 3), on, act.grenade, act.forward, list(b.notes)))
        t += 1 / 30
    return log


class PrenadeTests(unittest.TestCase):
    def test_legendary_blind_and_demon_throw_at_the_doorway_then_hold(self):
        for tier in ("top", "blind", "demon"):
            b = make(tier)
            log = run(b)
            presses = [r for r in log if r[2]]
            self.assertTrue(presses, tier)
            self.assertTrue(any("pre-nade: thrown at the doorway" in r[4] for r in log), tier)
            first = presses[0][0]
            self.assertLess(first, 0.3, tier)                                 # (due 1.8 s: at once, after the turn)
            self.assertGreaterEqual(presses[-1][0] - first, 0.25, tier)       # the button held
            after = [r for r in log if first + 0.4 < r[0] < first + PRENADE_HOLD - 0.1]
            self.assertTrue(after and all(r[1] and not r[2] and r[3] == 0.0 for r in after), tier)   # held, standing
            self.assertTrue(any("pre-nade: holding the doorway" in r[4] for r in after), tier)
            self.assertEqual(b.att[0], "prenade")
            self.assertAlmostEqual(b.att[2], DOOR_X, delta=0.3)                # its eyes on the doorway

    def test_not_the_other_tiers(self):
        profs = [profiles.make_profile(t, "rusher", random.Random(1)) for t in ("novice", "average", "strong", "tactician")]
        profs.append(scaling.profile(1.0, "rusher", random.Random(1)))
        for p in profs:
            self.assertFalse(any(r[2] for r in run(make(prof=p))), (p.tier, p.label, p.extra is not None))

    def test_timing(self):
        self.assertFalse(any(r[2] for r in run(make(), start_x=-20.0, seconds=0.5)))   # due in 6 s: not yet
        self.assertFalse(any(r[2] for r in run(make(), start_x=-7.0, seconds=0.5)))    # due in 0.4 s: too late

    def test_not_in_view_not_going_away_not_by_a_mate(self):
        self.assertFalse(any(r[2] for r in run(make(), seen=True)))           # in view: the gunfight's
        self.assertFalse(any(r[2] for r in run(make(), vx=-2.25)))            # walking off
        self.assertFalse(any(r[2] for r in run(make(), mate_at=Vec(DOOR_X, 0.5, 0))))   # a teammate by the doorway

    def test_once_per_man(self):
        b = make("demon")
        self.assertTrue(any(r[2] for r in run(b, t0=10.0)))
        b.grenade_ready_at = 0.0
        self.assertFalse(any(r[2] for r in run(b, t0=15.0, seconds=1.0)))     # the same man 5 s on
        self.assertTrue(any(r[2] for r in run(b, t0=10.0 + PRENADE_PER_MAN + 1.0, seconds=1.0)))

    def test_switch_off(self):
        botmod.PRENADE = False
        try:
            self.assertFalse(any(r[2] for r in run(make("demon"))))
        finally:
            botmod.PRENADE = True


if __name__ == "__main__":
    unittest.main(verbosity=2)
