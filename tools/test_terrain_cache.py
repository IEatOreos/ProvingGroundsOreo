"""(custom, Nov 21) The terrain cache (brain/maps.py cache_key, _cache_save, _cache_load, prebuild_after_match): the bots
stood at their spawns 10-17 s into every match while the brain built the map's terrain (7.3 s on Asylum). Keyed on
everything the build reads; a key that is the same loads the same terrain and map settings back."""
import os
import pickle
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import maps          # noqa: E402
from brain.core import Vec      # noqa: E402


def fake_map(name="t_map"):
    return dict(name=name, items=[dict(name="sword", pos=Vec(1, 2, 3))], zones=SimpleNamespace(zones=[SimpleNamespace(center=Vec(0, 0, 0))]),
                points={"mid": Vec(1, 1, 1)}, lanes=[Vec(2, 2, 2)], holds={0: [Vec(3, 3, 3)]}, teleporters=[],
                variant=dict(id="v1", first_seen="a", last_seen="b", objects=[]), window=None)


class Cache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "maps")
        os.makedirs(os.path.join(self.root, "t_map"))
        for fn, text in (("wall_kinds.json", "{}"), ("stations.json", "{}"), ("lidar.json", '{"walk": []}')):
            Path(self.root, "t_map", fn).write_text(text)
        self.patches = [mock.patch.object(maps, "ROOT", self.root),
                        mock.patch.object(maps, "CACHE_DIR", os.path.join(self.tmp, "cache"))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_key_follows_what_the_build_reads(self):
        m = fake_map()
        k = maps.cache_key(m)
        self.assertEqual(k, maps.cache_key(fake_map()))                       # the same inputs, the same key
        Path(self.root, "t_map", "stations.json").write_text('{"x": 1}')       # written each match, never read: same
        self.assertEqual(k, maps.cache_key(m))
        m["variant"]["last_seen"] = "c"                                         # the variant's seen times: same
        self.assertEqual(k, maps.cache_key(m))
        Path(self.root, "t_map", "lidar.json").write_text('{"walk": [[1, 2, 3, 1, 1]]}')   # people walked: new key
        k2 = maps.cache_key(m)
        self.assertNotEqual(k, k2)
        m["teleporters"] = [dict(pos=Vec(0, 0, 0))]                             # the game mode's teleporters: new key
        self.assertNotEqual(k2, maps.cache_key(m))
        Path(self.root, "t_map", "new_data.json").write_text("{}")              # an unknown file counts (safe side)
        self.assertNotEqual(maps.cache_key(m), k2)

    def test_round_trip_puts_the_map_settings_back(self):
        m = fake_map()
        key = maps.cache_key(m)
        m.update(live_blocks=[("box", 1)], shields=[], points={"mid": Vec(9, 9, 9)})
        m["items"][0]["reachable"] = True
        m["zones"].zones[0].center = Vec(5, 5, 5)
        maps._cache_save(m, key, SimpleNamespace(level="built"), wait=True)
        fresh = fake_map()
        T = maps._cache_load(fresh, key)
        self.assertEqual(T.level, "built")
        self.assertEqual(fresh["points"], {"mid": Vec(9, 9, 9)})
        self.assertEqual(fresh["live_blocks"], [("box", 1)])
        self.assertTrue(fresh["items"][0]["reachable"])
        self.assertEqual(fresh["zones"].zones[0].center, Vec(5, 5, 5))
        self.assertIsNone(maps._cache_load(fake_map(), "0" * 40))               # another key: nothing
        other = fake_map()
        other["items"].append(dict(name="x", pos=Vec(0, 0, 0)))
        self.assertIsNone(maps._cache_load(other, key))                          # a map that does not fit it: nothing

    def test_one_file_a_map_and_the_newest_kept(self):
        m = fake_map()
        maps._cache_save(m, "a" * 40, SimpleNamespace(), wait=True)
        maps._cache_save(m, "b" * 40, SimpleNamespace(), wait=True)
        files = os.listdir(maps.CACHE_DIR)
        self.assertEqual([f for f in files if f.endswith(".pkl.z")], [os.path.basename(maps._cache_file("t_map", "b" * 40))])
        with mock.patch.object(maps, "CACHE_KEEP", 2):
            for k in "cde":
                maps._cache_save(fake_map(f"t_{k}"), k * 40, SimpleNamespace(), wait=True)
            self.assertEqual(len([f for f in os.listdir(maps.CACHE_DIR) if f.endswith(".pkl.z")]), 2)

    def test_after_the_match_the_next_one_is_built_from_this_matchs_inputs(self):
        m = fake_map()
        maps._PRE[m["name"]] = maps._pickle_m(m)
        m["window"] = (0.0, 0.0, 10.0, 10.0)                                    # grown in the match
        with mock.patch("subprocess.Popen") as popen:
            self.assertIsNotNone(maps.prebuild_after_match(m))
        path = popen.call_args[0][0][-1]
        with open(path, "rb") as f:
            m0 = pickle.load(f)
        self.assertEqual(m0["window"], (0.0, 0.0, 10.0, 10.0))
        self.assertEqual(m0["points"], m["points"])
        self.assertIsNone(maps.prebuild_after_match(fake_map("never_built")))


if __name__ == "__main__":
    unittest.main()
