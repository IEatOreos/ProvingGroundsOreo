"""(custom, Nov 27) Noble plays the owner's own spots in Slayer (Bot.noble_rotation, noble_rot_pick, owner_spots_load):
from its spawn, his best open spot near, held his own median visit there, then the next. The owner: "I want good bots to
get to power positions more and utilize them like a real high KD player would"; "Yes, Noble first"."""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_take_space import Base, man, mk, snap  # noqa: E402
from brain import bot, noble  # noqa: E402
from brain.core import Vec  # noqa: E402

# (spot, his value there, his median visit s)
OWNER = [(Vec(10, 0, 0), 4.0, 3.0), (Vec(20, 0, 0), 12.0, 4.0), (Vec(-10, 0, 0), 6.0, 2.5)]


class RotationTests(Base):
    def setUp(self):
        super().setUp()
        bot._OWNER_SPOTS["test_space"] = list(OWNER)

    def tearDown(self):
        bot._OWNER_SPOTS.pop("test_space", None)
        noble.OVERRIDE = None
        super().tearDown()

    def go(self, b, me, now, seen=(), mates=()):
        scores = {}
        b.take_space(now, me, snap(me, *mates), scores, list(seen))
        return scores

    def test_from_spawn_his_best_spot_near(self):
        b, me = mk("noble"), man(1, 0, Vec(0, 0, 0))
        sc = self.go(b, me, 1.0)                                  # (no kill needed)
        self.assertEqual(list(sc), [("hold", Vec(20, 0, 0))])     # (12 a minute 20 u off over 4 a minute 10 u off)
        self.assertTrue(b.space["owner"])
        self.assertEqual(b.space["visit"], 4.0)

    def test_his_visit_then_the_next_not_back_to_the_last(self):
        b, me = mk("noble"), man(1, 0, Vec(0, 0, 0))
        self.go(b, me, 1.0)
        me.pos = Vec(20, 0, 0)
        self.go(b, me, 2.0)                                       # (there)
        self.assertEqual(list(self.go(b, me, 5.0)), [("hold", Vec(20, 0, 0))])        # (3 s of his 4)
        self.assertEqual(list(self.go(b, me, 5.0, seen=[9])), [])                       # (a man in view: the fight)
        sc = self.go(b, me, 6.5)
        self.assertEqual(list(sc), [("hold", Vec(10, 0, 0))])     # (his visit done: the next, not the one just left)

    def test_a_teammates_spot_is_passed(self):
        b, me = mk("noble"), man(1, 0, Vec(0, 0, 0))
        mate = man(2, 0, Vec(20.5, 0, 0))
        sc = self.go(b, me, 1.0, mates=[mate])
        self.assertEqual(list(sc), [("hold", Vec(-10, 0, 0))])

    def test_noble_slayer_and_its_switch_only(self):
        b, me = mk("demon"), man(1, 0, Vec(0, 0, 0))
        self.assertEqual(self.go(b, me, 1.0), {})                 # (Demon: its own Take Space, after a kill)
        b = mk("noble")
        self.assertIsNone(b.noble_rotation(snap(man(1, 0, Vec()), mode="ctf")))
        noble.OVERRIDE = {"owner_spots": 0}
        self.assertIsNone(b.noble_rotation(snap(man(1, 0, Vec()))))


class SaferRotationTests(RotationTests):
    """(Nov 27, the owner's three: safe rotations, a kill extends the visit, spots that see the enemy)"""

    def there(self):
        b, me = mk("noble"), man(1, 0, Vec(0, 0, 0))
        self.go(b, me, 1.0)
        me.pos = Vec(20, 0, 0)
        self.go(b, me, 2.0)                                       # (on his best spot, its visit 4 s)
        return b, me

    def test_stays_with_a_man_near_the_way_on(self):
        b, me = self.there()
        foe = man(9, 1, Vec(15, 1, 0))                            # (by the way to the next spot, at 10 u)
        b.per.beliefs[9] = types.SimpleNamespace(pos=foe.pos, t=6.0)
        sc = self.go(b, me, 6.5, mates=[foe])
        self.assertEqual(list(sc), [("hold", Vec(20, 0, 0))])     # (visit over, but not safe: it stays)
        b.kill_seen = (6.4, Vec(25, 0, 0))                        # (a kill there: a visit more, then on at once)
        self.assertEqual(list(self.go(b, me, 6.6, mates=[foe])), [("hold", Vec(20, 0, 0))])
        self.assertEqual(list(self.go(b, me, 10.7, mates=[foe])), [("hold", Vec(10, 0, 0))])   # (the man still there)

    def test_a_kill_there_extends_the_visit(self):
        b, me = self.there()
        b.kill_seen = (5.0, Vec(25, 0, 0))
        self.go(b, me, 5.1)                                       # (a kill on the spot: 4 s more from 5.1)
        b.kill_seen = None
        self.assertEqual(list(self.go(b, me, 8.0)), [("hold", Vec(20, 0, 0))])   # (past the first 4 s, still on)
        self.assertEqual(list(self.go(b, me, 9.3)), [("hold", Vec(10, 0, 0))])

    def test_a_spot_that_sees_him_first(self):
        b, me = mk("noble"), man(1, 0, Vec(0, 0, 0))
        foe = man(9, 1, Vec(-15, 5, 0))
        b.per.beliefs[9] = types.SimpleNamespace(pos=foe.pos, t=0.9)
        b.T = lambda: types.SimpleNamespace(los=lambda a, c: a.x < 0)           # (only the west spot sees him)
        sc = self.go(b, me, 1.0, mates=[foe])
        self.assertEqual(list(sc), [("hold", Vec(-10, 0, 0))])    # (6 a minute x 2 over 12 a minute 20 u off)


class LoadTests(unittest.TestCase):
    def test_his_spots_their_value_and_a_layouts_floor(self):
        prof = dict(spots=[dict(pos=[1, 2, 0], kills=23, deaths=4, kills_per_min=8.5, median_visit_s=3.8),
                           dict(pos=[5, 5, 0], kills=2, deaths=0, kills_per_min=9.0, median_visit_s=3.0),
                           dict(pos=[9, 9, 0], kills=10, deaths=14, kills_per_min=4.0, median_visit_s=20.0)])
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "m"))
            with open(os.path.join(d, "m", "owner_profile.json"), "w") as f:
                json.dump(prof, f)
            import brain.maps as M
            old, M.ROOT = M.ROOT, d
            try:
                b = mk("noble")
                got = b.owner_spots_load("m")
                self.assertEqual(len(got), 2)                     # (under 3 kills: left out)
                q, v, visit = got[0]
                self.assertAlmostEqual(v, 8.5 * 3.0)              # (his K/D there 24/5, counted up to 3)
                self.assertEqual(got[1][2], 8.0)                  # (his visit clamped)
                b.T = lambda: types.SimpleNamespace(walkable=lambda q: q.x < 5, nav_z=lambda x, y, z: z)
                self.assertEqual(len(b.owner_spots_load("m/variants/v1")), 1)   # (a layout: where it has floor)
            finally:
                M.ROOT = old


if __name__ == "__main__":
    unittest.main()
