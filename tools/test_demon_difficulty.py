"""Demon is a distinct tier retaining the prior tuned profile; native menu keys stay compatible."""
import hashlib
import json
import os
import random
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from brain.profiles import PERSONALITIES, make_profile  # noqa: E402
from brain.tracefmt import meta_line  # noqa: E402
import botctl  # noqa: E402


class DemonProfileTests(unittest.TestCase):
    def test_demon_is_distinct_and_retains_pre_split_numeric_profiles(self):
        numbers=[]
        for style in sorted(PERSONALITIES):
            for seed in range(5):
                demon=make_profile('demon',style,random.Random(seed))
                numbers.append({k:v for k,v in vars(demon).items() if isinstance(v,(float,int))})
        digest=hashlib.sha256(json.dumps(numbers,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        # Golden numeric profiles from the pre-split brain, 7 styles x 5 seeds.
        self.assertEqual(digest,'721b76b80d487e920f091e3db8008e5c86de8cc23f1178b336d754723c9337da')
        for style in PERSONALITIES:
            for seed in range(5):
                top = make_profile("top", style, random.Random(seed))
                demon = make_profile("demon", style, random.Random(seed))
                self.assertEqual(demon.tier, "demon")
                self.assertIsNone(demon.extra)
                self.assertEqual(demon.label, "demon")
                self.assertIsNone(top.label)
                self.assertNotEqual(demon.reaction,top.reaction)
                self.assertEqual(demon.reaction,0.0)
                self.assertEqual(demon.decide,0.01)

    def test_trace_names_demon(self):
        demon = make_profile("demon", "rusher", random.Random(1))
        self.assertIn('"tier": "demon"', meta_line(0.0, "m", "reach", 0, "B", 0, demon))
        top = make_profile("top", "rusher", random.Random(1))
        self.assertIn('"tier": "top"', meta_line(0.0, "m", "reach", 0, "B", 0, top))

    def test_bots_list_keeps_demon(self):
        with tempfile.TemporaryDirectory() as d:
            ini = os.path.join(d, "botcore.ini")
            with open(ini, "w", encoding="utf-8") as f:
                f.write("roster=1\nteams=2\nbot=0,demon,rusher,Imp\nbot=1,top,any,Legend\n")
            r = botctl.roster(ini)
        self.assertEqual([b["tier"] for b in r], ["demon", "top"])


class NativeTableTests(unittest.TestCase):
    """The native menu's tables (can't run the DLL here: read its source)."""

    @staticmethod
    def strings(src, name):
        m = re.search(name + r"\[[^\]]*\]\s*=\s*\{([^}]*)\}", src)
        return re.findall(r'"([^"]*)"', m.group(1))

    def test_tier_keys_match(self):
        panel = (ROOT / "native" / "bots_panel.cpp").read_text(encoding="utf-8")
        self.assertEqual(tuple(self.strings(panel, "TIER_KEY")), botctl.TIER_KEYS)
        self.assertEqual(self.strings(panel, "TIER_NAME")[5], "Demon")
        header = (ROOT / "native" / "bots_panel.h").read_text(encoding="utf-8")
        self.assertIn("#define HB_TIER_DEMON 5", header)
        self.assertIn("#define HB_TIERS 6", header)

    def test_difficulty_launches_demon(self):
        core = (ROOT / "native" / "botcore.cpp").read_text(encoding="utf-8")
        tiers = self.strings(core, "TIERS")
        self.assertEqual(len(tiers), 7)
        self.assertEqual(tiers[6], "demon")
        self.assertIn("difficulty % 7", core)


if __name__ == "__main__":
    unittest.main(verbosity=2)
