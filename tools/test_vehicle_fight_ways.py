"""(custom, Nov 14) The owner's vehicle asks: "I dont want any warthog driver to circle in a fight, just stick to their
normal pathing" (Bot.drive: a gunned Warthog drives its way on, its gunner on the man; other gun carriers still circle),
and "I want the ghost to boost when they go to run over a person ... you have to hold it down" (Bot.ram_boost splat:
held from GHOST_SPLAT_BOOST_R the whole run)."""
import math
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.bot import BOOST_CONE, BOOST_R, GHOST_SPLAT_BOOST_R, Belief, Bot, Order   # noqa: E402
from brain.core import Action, PlayerState, Snapshot, Vec                            # noqa: E402
from brain.profiles import make_profile                                              # noqa: E402


def bot(tier="strong", game_map="reach_test"):
    b = Bot(0, 0, make_profile(tier, "rusher", random.Random(3)), {"name": game_map}, random.Random(5))
    b.order = Order("mid", Vec(80, 0, 0))
    b.notes = []
    return b


def vehicle(kind, riders=2, handle=20):
    return dict(handle=handle, kind=kind, pos=(0.0, 0.0, 0.0), fwd=(1.0, 0.0, 0.0), up=(0.0, 0.0, 1.0),
                occupied=True, team=0, riders=riders, gunner=riders >= 2, turrets=[], manned=[])


class CircleTests(unittest.TestCase):
    def drive(self, kind):
        b = bot()
        b.seat, b.seat_for, b.seat_since = "driver", 20, 0.0
        b.drive_to = Vec(80, 0, 0)
        b._terrain = SimpleNamespace(vnav=lambda s, g: g, los=lambda *a, **k: True, height_over=lambda *a: 0.0,
                                     clearance=lambda *a, **k: 9.0, drive_clear=lambda *a, **k: None)
        b.T = lambda: b._terrain
        me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0), vehicle=20)
        mate = PlayerState(2, 0, "gunner", Vec(0.0, 0.0, 0.5), vehicle=20)
        mate.gunner_seat = True
        him = PlayerState(1, 1, "him", Vec(10.0, 6.0, 0.0), vehicle=-1, weapon="assault_rifle", weapons=["assault_rifle"])
        snap = Snapshot(10.0, [me, mate, him], vehicles=[vehicle(kind)], mode="slayer")
        b.per.beliefs[1] = Belief(him.pos, Vec(), 10.0, True, "eyes")
        b.per.recognized.add(1)
        b.per.last_seen[1] = b.per.clear_at[1] = 10.0
        act = Action()
        b.drive(10.0, 1 / 30, me, snap, act, lambda a, c: c)
        return b, act

    def test_a_gunned_warthog_keeps_its_way(self):
        for kind in ("warthog", "rwarthog", "gauss"):
            b, act = self.drive(kind)
            self.assertNotEqual((b.att or [None])[0], "circle", kind)
            self.assertEqual(b.att[0], "path", kind)
            self.assertAlmostEqual(act.yaw, 0.0, places=3, msg=kind)    # (on toward where it goes, +x)

    def test_other_gun_carriers_still_circle(self):
        b, act = self.drive("spectre")
        self.assertEqual(b.att[0], "circle")


class GhostBoostTests(unittest.TestCase):
    def boost(self, at, splat=True, tier="strong", game="reach_test", held=False, kind="ghost"):
        b = bot(tier, game)
        b.notes = []
        if held:
            b.splat_boost_t = 9.97
        me = PlayerState(0, 0, "me", Vec(0.0, 0.0, 0.0), vehicle=20)
        him = SimpleNamespace(pos=Vec(*at), vel=Vec())
        act = Action()
        b.ram_boost(10.0, me, vehicle(kind, riders=1), him, act, splat=splat)
        return b, act

    def test_held_from_farther_on_a_run(self):
        d = (BOOST_R + GHOST_SPLAT_BOOST_R) / 2                       # (past the old tap's reach)
        b, act = self.boost((d, 0.0, 0.0))
        self.assertTrue(act.fire2)
        self.assertTrue(act.vertical > 0.5)                           # (Reach: Bot.boost's output)
        self.assertIn("vehicle: boost into him (held)", b.notes)
        self.assertFalse(self.boost((GHOST_SPLAT_BOOST_R + 2, 0.0, 0.0))[1].fire2)
        self.assertFalse(self.boost((d, 0.0, 0.0), splat=False)[1].fire2)     # (not a run over him: the old tap)

    def test_the_cone_and_its_hold(self):
        a = BOOST_CONE * 1.5
        at = (10 * math.cos(a), 10 * math.sin(a), 0.0)
        self.assertFalse(self.boost(at)[1].fire2)                     # (not lined up yet)
        self.assertTrue(self.boost(at, held=True)[1].fire2)           # (held: kept through the swerve)

    def test_not_easy_and_not_a_warthog(self):
        self.assertFalse(self.boost((10.0, 0.0, 0.0), tier="novice")[1].fire2)
        self.assertFalse(self.boost((10.0, 0.0, 0.0), kind="warthog")[1].fire2)

    def test_halo4_sends_its_second_trigger(self):
        act = self.boost((10.0, 0.0, 0.0), game="h4_test")[1]
        self.assertTrue(act.fire2)


class BoostCaptureTests(unittest.TestCase):
    """tools/boost_capture.py's summary: the bit on in the fast holds comes first."""

    def test_the_held_bit_that_ran_fast(self):
        import struct
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import boost_capture
        rows, x = [], 0.0
        for i in range(600):
            t = i / 60
            held = int(t) % 6 >= 3                         # 3 s off, 3 s held
            x += (9.0 if held else 5.0) / 60
            act = bytearray(boost_capture.ACT_N)
            struct.pack_into("<Q", act, 0x08, (1 << 7) | ((1 << 19) if held else 0) | ((1 << 3) if i % 2 else 0))
            struct.pack_into("<f", act, 0x1C, 1.0)
            rows.append(dict(t=t, act=act.hex(), pos=[x, 0.0, 0.0], veh="vehicle 1"))
        c = boost_capture.candidates(boost_capture.with_speed(rows))
        self.assertEqual(c[0][0], "+0x08 bit 19")
        self.assertGreater(c[0][2], 8.0)
        self.assertLess(c[0][3], 6.0)
        self.assertNotIn("+0x08 bit 7", [n for n, *_ in c])          # (always on: not a held button)


if __name__ == "__main__":
    unittest.main()
