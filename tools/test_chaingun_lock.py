"""(custom, Nov 18) Demon and Mythic on a Warthog's chaingun aim dead on the man's chest every tick, led by the round's
flight and the read delay (Bot.chaingun_lock, Aim.lock). The owner: "I would like Mythic and Demon chain gunners to have
aimbot with the warthog gunner seat". Other tiers and the Gauss and Rocket Warthogs aim as before."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import bot as botmod                                        # noqa: E402
from brain.bot import Belief                                           # noqa: E402
from brain.core import Vec, angles_to                                  # noqa: E402
from brain.profiles import make_profile                                # noqa: E402
from test_warthog_spin import HIM, PIVOT, gunner, tick                 # noqa: E402

VEL = Vec(0.0, 4.0, 0.0)          # crossing at 4 u/s


def aimed(tier, turret="warthog_chaingun"):
    b, me, snap = gunner()
    b.p = make_profile(tier, "rusher", random.Random(3))
    b.aim.p = b.p
    me.turret = turret
    snap.player(1).vel = VEL
    b.per.beliefs[1] = Belief(HIM, VEL, 10.0, True, "eyes")
    b.per.recognized.add(1)
    b.per.last_seen[1] = b.per.clear_at[1] = 10.0
    me.yaw, me.pitch = 2.0, 0.3            # looking well away: no turn limit for a lock
    return b, me, snap, tick(b, me, snap, 10.0)


def want():
    chest = HIM + Vec(0, 0, botmod.aim_height(False, False))
    t = botmod.dist(PIVOT, chest) / botmod.PROJECTILE_SPEED["assault_rifle"]
    return angles_to(PIVOT, chest + VEL * (t + 0.05))


class Lock(unittest.TestCase):
    def test_demon_and_mythic_dead_on_at_once(self):
        wy, wp = want()
        for tier in ("demon", "mythic"):
            b, me, snap, act = aimed(tier)
            self.assertTrue(b.chaingun_lock(snap.vehicles[0], me), tier)
            self.assertAlmostEqual(act.yaw, wy, places=6, msg=tier)
            self.assertAlmostEqual(act.pitch, wp, places=6, msg=tier)
            self.assertTrue(act.fire, tier)

    def test_legendary_still_turns_onto_him(self):
        b, me, snap, act = aimed("top")
        self.assertFalse(b.chaingun_lock(snap.vehicles[0], me))
        self.assertGreater(abs(act.yaw - want()[0]), 0.05)    # from 2.0 rad off: a turn, not a lock
        self.assertFalse(act.fire)

    def test_not_the_gauss_or_rocket_warthog(self):
        for turret in ("warthog_gauss", "warthog_rocket"):
            b, me, snap, act = aimed("demon", turret)
            self.assertFalse(b.chaingun_lock(snap.vehicles[0], me), turret)


if __name__ == "__main__":
    unittest.main()
