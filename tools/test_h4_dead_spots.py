"""(custom, Nov 10) Halo 4: a loose gun's spot that two waits came to nothing at (the spawn rooms' racked Storm Rifles,
live Warhouse 20261110-184913) is skipped by every bot for the match: no walk to it, no Boltshot in hand for the swap."""
import random
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brain import bot  # noqa: E402
from brain.core import Vec  # noqa: E402
from brain.profiles import make_profile  # noqa: E402


def a_bot(name="h4_ca_warhouse"):
    b = bot.Bot.__new__(bot.Bot)
    b.p = make_profile("strong", "flanker", random.Random(0))
    b.game, b.map = "h4", {"name": name, "items": []}
    return b


class DeadSpotTests(unittest.TestCase):
    def setUp(self):
        bot.DEAD_SPOTS.clear()

    tearDown = setUp

    def upgrade(self, b):
        me = SimpleNamespace(pos=Vec(10.0, 16.5, 2.8), weapons=["battle_rifle", "boltshot"], ammo=[108, 30])
        snap = SimpleNamespace(ground_weapons=[("assault_rifle",Vec(10.8, 16.7, 2.99))], time=50.0)
        return b.upgrade_point(me, snap)

    def test_racked_rifle_is_an_upgrade_until_two_waits_fail(self):
        b = a_bot()
        self.assertIsNotNone(self.upgrade(b))         # (the Boltshot's Short 0.6: a Storm Rifle adds over the gain)
        spot = ("h4_ca_warhouse", (11, 17))
        bot.DEAD_SPOTS[spot] = 1
        b.skip_dead_spots()
        self.assertIsNotNone(self.upgrade(b))         # one wait: maybe someone took it first
        bot.DEAD_SPOTS[spot] = bot.DEAD_SPOT_FAILS
        other = a_bot()                               # another bot, either team: the count is shared
        other.skip_dead_spots()
        self.assertIsNone(self.upgrade(other))
        self.assertEqual(other.rearm_skip[(11, 17)], float("inf"))

    def test_other_maps_spots_do_not_count(self):
        bot.DEAD_SPOTS[("h4_wraparound", (11, 17))] = 5
        b = a_bot()
        b.skip_dead_spots()
        self.assertIsNotNone(self.upgrade(b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
