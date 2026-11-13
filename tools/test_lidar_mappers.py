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


class AllOfAGameTests(unittest.TestCase):
    """(Nov 13: "simulate all the maps in a per game basis") Every map, or every map of one game, queued."""
    NAMES = ["bloodgulch", "h3_construct", "reach_70_boneyard", "reach_cex_headlong",
             "reach_forge_halo", "reach_forge_halo/variants/v1234abcd", "h4_ca_blood_crash"]

    def test_one_game(self):
        c = lidar_sim.Control(self.NAMES)
        self.assertEqual(c.command(dict(action="all", game="reach")), (200, dict(ok=True, queued=3)))
        self.assertEqual(c.queue, ["reach_70_boneyard", "reach_cex_headlong", "reach_forge_halo"])   # (no Forge layouts)

    def test_every_game_and_refusals(self):
        c = lidar_sim.Control(self.NAMES)
        self.assertEqual(c.command(dict(action="all"))[1]["queued"], 6)
        self.assertEqual(c.command(dict(action="all", game="halo5"))[0], 400)
        self.assertEqual(c.command(dict(action="all", game="odst"))[0], 404)      # (none here)
        self.assertEqual(len(c.queue), 6)                                         # (a refused one changed nothing)


class SimStateTests(unittest.TestCase):
    """A map opened in the simulator's window asks GET /sim: the panel's state, and the simulator (which closes 90 s
    after its window stops asking) sees the window is open. The LiDAR Viewer has no simulator: 404."""

    def test_sim_state_keeps_the_simulator_open(self):
        import json
        import tempfile
        import time
        import urllib.error
        import urllib.request
        from lidar import Hub, Recorder, serve
        tmp = tempfile.mkdtemp(prefix="simstate_")
        sw = lidar_sim.Switch()
        sw.control = lidar_sim.Control(["h3_armory"])
        sw.current = Hub(Recorder("h3_armory", count_run=False, path=os.path.join(tmp, "idle.json")), "sim")
        sw.last_seen = 0.0
        srv = serve(sw, 8873)
        self.assertIsNotNone(srv)
        try:
            d = json.loads(urllib.request.urlopen("http://127.0.0.1:8873/sim", timeout=5).read())
            self.assertIsNone(d["current"])
            self.assertEqual(d["mappers"], "both")
            self.assertGreater(sw.last_seen, time.time() - 5)
        finally:
            srv.shutdown()
            srv.server_close()
        view = Hub(Recorder("h3_armory", count_run=False, path=os.path.join(tmp, "idle2.json")), "stored")
        srv = serve(view, 8874)
        try:
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen("http://127.0.0.1:8874/sim", timeout=5)
            self.assertEqual(e.exception.code, 404)
        finally:
            srv.shutdown()
            srv.server_close()


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
