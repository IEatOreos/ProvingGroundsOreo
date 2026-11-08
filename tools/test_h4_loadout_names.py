"""Halo 4's loadout guns by the brain's names (custom, Nov 8): the live tags storm_forerunner_rifle,
storm_stasis_pistol, storm_forerunner_smg and storm_assault_carbine are the Light Rifle, Boltshot, Suppressor and
Storm Rifle, which bot.py's tables know as lightrifle, boltshot, suppressor and storm_rifle."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import bot                                     # noqa: E402
from brain.bot import AUTO, CHARGE, H4_SNAP, PRECISION, WEAPON_RANK, h4_demon_fire, h4_wants_head   # noqa: E402
from brain.live import brain_name                         # noqa: E402
from test_h4_demon import scene                           # noqa: E402

LIVE = {"storm_forerunner_rifle": "lightrifle", "storm_stasis_pistol": "boltshot",
        "storm_forerunner_smg": "suppressor", "storm_assault_carbine": "storm_rifle"}


class NameTests(unittest.TestCase):
    def test_live_tags(self):
        for tag, name in LIVE.items():
            self.assertEqual(brain_name(tag), name, tag)

    def test_what_each_name_is(self):
        self.assertIn("lightrifle", PRECISION)
        self.assertIn("boltshot", CHARGE)
        for w in ("suppressor", "storm_rifle"):
            self.assertIn(w, AUTO)
        for w in ("lightrifle", "suppressor", "storm_rifle"):
            self.assertIn(w, H4_SNAP)
        for w in ("lightrifle", "boltshot"):
            self.assertIn(w, WEAPON_RANK)
            self.assertIn(w, bot.WEAPON_RANGE)

    def test_the_old_names_were_none_of_it(self):
        for w in ("forerunner_rifle", "stasis_pistol", "forerunner_smg", "assault_carbine"):
            self.assertFalse(w in PRECISION or w in AUTO or w in CHARGE or w in WEAPON_RANK, w)


class DemonTests(unittest.TestCase):
    def test_halo4_demon_locks_the_light_rifle_on_the_head(self):
        b, me, him, _ = scene(weapon="lightrifle")
        self.assertTrue(h4_demon_fire(b.p, "h4", me, him))
        self.assertTrue(h4_wants_head(me, him))
        me.weapon = "forerunner_rifle"              # (as it read before)
        self.assertFalse(h4_demon_fire(b.p, "h4", me, him))

    def test_automatics_at_the_body(self):
        b, me, him, _ = scene(weapon="suppressor")
        self.assertTrue(h4_demon_fire(b.p, "h4", me, him))
        self.assertFalse(h4_wants_head(me, him))


if __name__ == "__main__":
    unittest.main()
