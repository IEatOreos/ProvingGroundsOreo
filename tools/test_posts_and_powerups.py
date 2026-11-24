"""(custom, Nov 23) Two of the owner's bug reports.

Sword Base, "Make bots use this lift on swordbase, it leads to floor 3. So make routes worth it" and "Swordbase is
usually height is most important": power positions no player can stand on are left out (brain/maps.py
keep_reachable_positions); its four on the roof (z 38) got 40% of the bots' orders while nobody stood over z 33.

Beaver Creek Anniversary, "These are overshields": a .mvar's powerups are power items (brain/mvar.py scenario_objects,
brain/maps.py power_items, POWER "powerup_red"), and the live reader's name for one is the brain's (tools/live_bots.py
item_name)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from brain import maps, mvar                       # noqa: E402
from brain.core import Vec                          # noqa: E402


class FakeT:
    """A nav over x 0..100 whose floor is reachable below z 30 only."""

    def inside(s, x, y):
        return 0 <= x <= 100

    def _node(s, p):
        return p.z < 30.0

    @property
    def reach(s):
        return {True: True, False: False}


class ReachablePositions(unittest.TestCase):
    def m(self):
        pts = [Vec(10, 0, 28), Vec(20, 0, 38), Vec(30, 0, 28), Vec(200, 0, 38)]
        return dict(positions=pts, position_info=[dict(pos=p, score=k / 10) for k, p in enumerate(pts)])

    def test_the_roof_posts_left_out(self):
        m = self.m()
        maps.keep_reachable_positions(m, FakeT())
        self.assertEqual(m["positions"], [Vec(10, 0, 28), Vec(30, 0, 28), Vec(200, 0, 38)])   # (200: outside the window)
        self.assertEqual([i["score"] for i in m["position_info"]], [0.0, 0.2, 0.3])

    def test_all_reachable_unchanged(self):
        m = dict(positions=[Vec(10, 0, 28)], position_info=[dict(pos=Vec(10, 0, 28), score=1.0)])
        before = dict(m)
        maps.keep_reachable_positions(m, FakeT())
        self.assertEqual(m, before)

    def test_no_way_back_left_out(self):
        """(Spire BTB) a post reached by a lift with no route down (Terrain.trap) is no post."""
        class TrapT(FakeT):
            trap = {True: False, False: False, "top": True}
            reach = {True: True, False: False, "top": True}

            def _node(s, p):
                return "top" if p.z > 35 else p.z < 30.0
        T = TrapT()
        m = dict(positions=[Vec(10, 0, 28), Vec(20, 0, 40)], position_info=[dict(score=1.0), dict(score=0.9)])
        maps.keep_reachable_positions(m, T)
        self.assertEqual(m["positions"], [Vec(10, 0, 28)])
        self.assertTrue(maps._in_trap(T, Vec(20, 0, 40)))
        self.assertFalse(maps._in_trap(FakeT(), Vec(20, 0, 40)))      # (no trap known: none)

    def test_kept_by_the_terrain_cache(self):
        self.assertIn("positions", maps.CACHE_M_STATE)
        self.assertIn("position_info", maps.CACHE_M_STATE)


def mvar_object(name, mp, pos, respawn=90):
    return dict(name=name, label=None, team=8, pos=pos, mp_type=mp, forward=[1.0, 0.0, 0.0], spawn_sequence=0,
                respawn_time=respawn)


class Overshield(unittest.TestCase):
    def test_a_variants_powerup_is_a_power_item(self):
        v = dict(objects=[mvar_object("powerup_red", "powerup", [1.4665, -7.0822, -0.8063]),
                          mvar_object("sniper", "weapon", [4.0, -8.7, 3.6], 180)])
        objs = mvar.scenario_objects(v)
        self.assertEqual([e["item"] for e in objs["powerups"]], ["powerup_red"])
        self.assertEqual([e["item"] for e in objs["equipment"]], ["sniper"])     # (the weapons' placements as before)
        items = {i["name"]: i for i in maps.power_items(objs)}
        self.assertEqual((items["overshield"]["kind"], items["overshield"]["respawn"]), ("powerup", 90))
        self.assertIn("sniper", items)

    def test_the_live_name_is_the_brains(self):
        import live_bots
        for tag, name in (("powerup_red", "overshield"), ("powerup_blue", "camo"), ("powerup_yellow", "custom_powerup")):
            self.assertEqual(live_bots.item_name(f"objects\\multi\\powerups\\{tag}\\{tag}"), name)
            self.assertEqual(maps.POWER[tag][:2], (name, "powerup"))

    def test_without_powerups_as_before(self):
        self.assertEqual([i["name"] for i in maps.power_items(dict(equipment=[dict(item="rockets", pos=[0, 0, 0],
                                                                                    spawn_time=0)]))], ["rockets"])


if __name__ == "__main__":
    unittest.main()
