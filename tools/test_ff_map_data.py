"""(custom, Nov 24) Upstream 0.3.0's note #81 (build 20261120-2003): Installation 04 and Unearthed (Halo: Reach Firefight,
from the map packs) have their map data, so the LiDAR tools read them and the bots load them. The JSON is committed;
heightmap.npz and topdown.png are the map pack's (git-ignored), checked only when present."""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

MAPS = {"reach_cex_ff_halo": "Installation 04", "reach_ff_unearthed": "Unearthed"}
JSON = ("callouts.json", "features.json", "killzones.json", "objects.json", "phantoms.json", "positions.json",
        "wall_kinds.json")


class FirefightMapData(unittest.TestCase):
    def test_json_and_names(self):
        names = json.loads((ROOT / "tools" / "view_art" / "names.json").read_text(encoding="utf-8"))
        for name, title in MAPS.items():
            self.assertEqual(names[name], title)
            for fn in JSON:
                with open(ROOT / "maps" / name / fn, encoding="utf-8") as f:
                    json.load(f)
        for sky in ("h2a_ca_forge_skybox01", "h2a_ca_forge_skybox02", "h2a_ca_forge_skybox03"):
            self.assertIn(sky, names)

    def test_bots_load_them(self):
        for name in MAPS:
            if not (ROOT / "maps" / name / "heightmap.npz").exists():
                self.skipTest("the map pack is not here")
            from brain.maps import get_map
            m = get_map(name)
            self.assertTrue(m["spawns"])
            import lidar
            self.assertEqual(lidar.map_title(name), MAPS[name])


if __name__ == "__main__":
    unittest.main()
