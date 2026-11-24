"""(custom, Nov 24) Upstream 0.3.0's notes #58 + #83: the Modded and Map Studio tabs of the LiDAR Viewer / Simulator and
Paint the nav (tools/lidar.py modded, brain/paths.workshop_maps). Ours wins: our tools/mod_maps.py is the only builder
("Read its level" runs it, never his modded_export.py), its folder names the map, and our titles come first."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import lidar  # noqa: E402
import lidar_sim  # noqa: E402
from brain import paths  # noqa: E402

FILE = os.path.join("C:\\", "mods", "fp_guardian", "maps", "fp_guardian.map")
WORK = [dict(name="reach_fp_guardian_x", game="reach", title="Fp Guardian", mod="FP_GUARDIAN", item="fp_guardian",
             file=FILE, local=True, dir=os.path.dirname(os.path.dirname(FILE)), studio=False),
        dict(name="reach_20_sword_slayer", game="reach", title="20 Sword Slayer", mod="The Great Forge", item="1",
             file="C:\\w\\20_sword_slayer.map", local=False, dir="C:\\w", studio=False),
        dict(name="h3_studio_map", game="h3", title="Studio Map", mod="Mine", item="mine", file="C:\\s\\studio_map.map",
             local=True, dir="C:\\s", studio=True),
        dict(name="blood_ce", game="ce", title="Blood Ce", mod="CE mod", item="2", file="C:\\c\\blood_ce.map",
             local=False, dir="C:\\c", studio=False)]
OURS = {"reach_fp_guardian": dict(folder="reach_fp_guardian", game="reach", stem="fp_guardian", title="FP_GUARDIAN MP",
                                  mod="FP_GUARDIAN", mod_dir=os.path.dirname(os.path.dirname(FILE)), map=FILE, stock=False),
        "reach_fp_proof": dict(folder="reach_fp_proof", game="reach", stem="fp_proof", title="FP_PROOF", mod="FP_PROOF",
                               mod_dir="C:\\p", map="C:\\p\\maps\\fp_proof.map", stock=False)}


class ModdedListTests(unittest.TestCase):
    def setUp(self):
        self.p = [mock.patch.object(lidar, "_modded_found", lambda: (WORK, OURS)),
                  mock.patch.object(lidar, "map_titles", lambda: {"reach_20_sword_slayer": "Sword Base"}),
                  mock.patch.object(lidar, "_mod_title", lambda base: "FP_GUARDIAN" if base == "reach_fp_guardian" else None)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def test_names_titles_and_flags(self):
        listed = [dict(name="reach_fp_guardian", title="FP_GUARDIAN", game="reach"),
                  dict(name="reach_fp_guardian/variants/v12345678", title="FP_GUARDIAN: Slayer", game="reach"),
                  dict(name="reach_20_sword_slayer", title="Sword Base", game="reach")]
        out = {m["name"]: m for m in lidar.modded(listed)}
        g = listed[0]
        self.assertTrue(g["modded"] and g["ready"])                     # (our folder, by its .map file: not his name)
        self.assertEqual(g["title"], "FP_GUARDIAN")                     # (ours kept)
        self.assertTrue(listed[1]["modded"])                            # (its layout goes with it)
        self.assertNotIn("modded", listed[2])                           # (a mod on a stock scenario is that map)
        self.assertNotIn("reach_fp_guardian_x", out)
        self.assertNotIn("reach_20_sword_slayer", out)
        self.assertEqual(out["reach_fp_proof"]["title"], "FP_PROOF")    # (only our builder knows it: listed too)
        self.assertTrue(out["reach_fp_proof"]["readable"])
        self.assertTrue(out["h3_studio_map"]["studio"])
        self.assertFalse(out["h3_studio_map"]["readable"])              # (our builder has no row for it)
        self.assertIn("Halo 4", out["blood_ce"]["why"])                  # (CE: the map tools do not read it)
        self.assertFalse(out["blood_ce"]["ready"])

    def test_read_its_level_runs_our_builder(self):
        calls = []

        class Done:
            returncode, stdout, stderr = 0, "reach_fp_proof: exporting ...\nreach_fp_proof: built\n", ""
        threads = []
        real_thread = lidar.threading.Thread

        def thread(target, daemon):
            t = real_thread(target=target, daemon=daemon)
            threads.append(t)
            return t
        with mock.patch("subprocess.run", lambda cmd, **kw: calls.append(cmd) or Done()), \
                mock.patch.object(lidar.threading, "Thread", thread):
            self.assertFalse(lidar.prepare_modded("h3_studio_map"))     # (not one our builder reads)
            self.assertFalse(lidar.prepare_modded("no_such_map"))
            self.assertTrue(lidar.prepare_modded("reach_fp_proof"))
            for t in threads:
                t.join(5)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][2].endswith("mod_maps.py"))
        self.assertEqual(calls[0][3], "reach_fp_proof")
        self.assertNotIn("reach_fp_proof", lidar.PREPARING)              # (built: nothing left to show)

    def test_a_failed_read_is_shown(self):
        class Failed:
            returncode, stdout, stderr = 0, "reach_fp_proof: bsp2obj exported no geometry\n", ""
        with mock.patch("subprocess.run", lambda cmd, **kw: Failed()):
            lidar.PREPARING.pop("reach_fp_proof", None)
            self.assertTrue(lidar.prepare_modded("reach_fp_proof"))
            for _ in range(100):
                if lidar.PREPARING.get("reach_fp_proof", {}).get("state") != "running":
                    break
                import time
                time.sleep(0.02)
        self.assertEqual(lidar.PREPARING.pop("reach_fp_proof"), dict(state="failed", error="bsp2obj exported no geometry"))


class NoSecondBuilderTests(unittest.TestCase):
    def test_his_builder_is_not_here(self):
        self.assertFalse((ROOT / "tools" / "modded_export.py").exists())
        self.assertNotIn("modded_export", (ROOT / "tools" / "lidar.py").read_text(encoding="utf-8").replace(
            "never his modded_export.py", ""))

    def test_page_has_the_tabs(self):
        page = (ROOT / "tools" / "lidar_view.html").read_text(encoding="utf-8")
        for part in ('"mod-game"', '"Map Studio"', "Read its level", '"/prepare?name="', '"X-LiDAR": "prepare"',
                     'id="sim-mappers"', 'id="sim-all-game"'):
            self.assertIn(part, page)


class WorkshopListingTests(unittest.TestCase):
    def test_local_mod_and_map_studio(self):
        with tempfile.TemporaryDirectory() as tmp:
            mods = os.path.join(tmp, "mods")
            mod = os.path.join(mods, "my_map")
            os.makedirs(os.path.join(mod, "maps"))
            os.makedirs(os.path.join(mod, "ppg"))
            open(os.path.join(mod, "maps", "my_map.map"), "w").close()
            open(os.path.join(mod, "maps", "shared.map"), "w").close()
            with open(os.path.join(mod, "ModInfo.json"), "w", encoding="utf-8") as f:
                json.dump({"Engine": "Halo3", "Title": {"Neutral": "My Map"}}, f)
            man = os.path.join(tmp, "ModManifest.txt")
            with open(man, "w", encoding="utf-8") as f:
                f.write(mods + "\n")
            with mock.patch.object(paths, "steam_commons", lambda: []):
                got = paths.workshop_maps(man)
        self.assertEqual([(w["name"], w["game"], w["mod"], w["studio"]) for w in got], [("h3_my_map", "h3", "My Map", True)])


class SimPickTests(unittest.TestCase):
    def test_a_map_read_since_can_be_picked(self):
        c = lidar_sim.Control(["h3_construct"])
        with mock.patch.object(lidar, "map_list_names", lambda: ["h3_construct", "reach_fp_proof"]):
            self.assertEqual(c.command(dict(action="pick", name="reach_fp_proof"))[0], 200)
        self.assertEqual(c.queue, ["reach_fp_proof"])


if __name__ == "__main__":
    unittest.main()
