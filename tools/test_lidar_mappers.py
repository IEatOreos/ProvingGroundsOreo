"""LiDAR Simulator: who maps, ground, air or both (custom, Nov 8, tools/lidar_sim.py crew / Control / Airspace.seed)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lidar_sim                               # noqa: E402


class CrewTests(unittest.TestCase):
    def test_crew(self):
        self.assertEqual(lidar_sim.crew("both", 16, 8), (16, 8))
        self.assertEqual(lidar_sim.crew("ground", 16, 8), (16, 0))
        self.assertEqual(lidar_sim.crew("air", 16, 8), (0, 16))

    def test_control(self):
        c = lidar_sim.Control(["h3_armory"])
        self.assertEqual(c.state()["mappers"], "both")
        self.assertEqual(c.command(dict(action="mappers", mappers="air")), (200, dict(ok=True)))
        self.assertEqual(c.state()["mappers"], "air")
        self.assertEqual(c.command(dict(action="mappers", mappers="water"))[0], 400)
        self.assertEqual(c.state()["mappers"], "air")
        c.started("h3_armory", None, None, "air")
        self.assertEqual(c.state()["run_mappers"], "air")
        c.command(dict(action="mappers", mappers="ground"))       # the running map keeps its own
        self.assertEqual((c.state()["mappers"], c.state()["run_mappers"]), ("ground", "air"))


@unittest.skipUnless(os.path.exists(os.path.join(lidar_sim.ROOT, "maps", "h3_armory", "heightmap.npz")), "map data not here")
class SeedTests(unittest.TestCase):
    def test_air_only_has_air_to_fly(self):
        from brain.maps import get_map, terrain

        class NoFloor:
            floor_keys = set()

        T = lidar_sim.J.prepare(terrain(get_map("h3_armory")))      # (as run_map: the heights the air needs)
        air = lidar_sim.Airspace(T, lidar_sim.ceiling_of("h3_armory", T)[0])
        air.update(NoFloor())                  # nothing walked: nothing to fly (why air only seeds)
        self.assertFalse(air.want.any())
        air.seed(T)
        self.assertGreater(int(air.want.sum()), 1000)
        c = T._center(*map(int, next(zip(*(T.lwalk & T.reach).nonzero()))))
        self.assertTrue(air.route((c.x, c.y, c.z + 2.5)))           # an aircraft over the floor has somewhere to go


if __name__ == "__main__":
    unittest.main()
