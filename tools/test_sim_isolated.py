"""(Nov 18) The simulated matches reach the site and the career totals when the tools run as MCC runs them:
`python -I`, which leaves the tools folder off sys.path. Before the fix both caught the failed `import bot_sim` and went
on without a simulated match (the owner: every bot had only the games it played with him). Each check runs a fresh
`python -I` driver from a temporary folder on a made-up install (test_bot_sim.World): nothing real is read or written."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_bot_sim import World  # noqa: E402

DRIVER = r'''
import importlib.util, json, os, sys
tools, what, arg = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
assert tools not in sys.path, "the tools folder is already importable: this would not test -I"
def load(name):
    spec = importlib.util.spec_from_file_location(name + "_under_test", os.path.join(tools, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
if what == "site":
    sr = load("service_record")
    data = sr.build(sr.Paths(**arg))
    print(json.dumps({"matches": len(data["matches"]),
                      "games": sum(p["g"].get("reach", {}).get("cats", {}).get("all", {}).get("games", 0) for p in data["players"])}))
else:
    career = load("bot_career")
    career.OUT = arg["out"]
    career.LOGS = arg["logs"]
    career.MCC_REPORT = arg["report"]
    career.main(["--quiet"])
    with open(os.path.join(arg["out"], "totals.txt"), encoding="utf-8") as f:
        print(json.dumps({"games": sum(int(l.split("\t")[1]) for l in f if l.strip())}))
'''


class Isolated(unittest.TestCase):
    def run_driver(self, tmp, what, arg):
        driver_dir = os.path.join(tmp, "driver")
        os.makedirs(driver_dir, exist_ok=True)
        driver = os.path.join(driver_dir, "driver.py")
        with open(driver, "w", encoding="utf-8") as f:
            f.write(DRIVER)
        out = subprocess.run([sys.executable, "-I", driver, HERE, what, json.dumps(arg)], capture_output=True,
                             text=True, timeout=600, cwd=driver_dir)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout.strip().splitlines()[-1])

    def test_site_and_totals_have_the_simulated_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = World(tmp, names=40)
            played = w.round(seed=3, pace=1.0)
            self.assertTrue(played, "the round played no match")
            p = w.paths
            site = self.run_driver(tmp, "site", {k: getattr(p, k) for k in (
                "store", "ledger", "out", "profiles", "pool", "bot_pool", "matchmaking", "logs", "maps", "snap",
                "mcc_report", "emblems", "looks", "look_names")})
            self.assertGreater(site["matches"], 0, "no simulated match on the site under python -I")
            self.assertGreater(site["games"], 0)
            # bot_career reads the simulation beside its own folder: <parent>/service_record/sim.db
            career = os.path.join(tmp, "career2", "career")
            os.makedirs(os.path.join(tmp, "career2", "service_record"))
            os.makedirs(career)
            shutil.copyfile(os.path.join(p.store, "sim.db"), os.path.join(tmp, "career2", "service_record", "sim.db"))
            totals = self.run_driver(tmp, "career", {"out": career, "logs": p.logs, "report": p.mcc_report})
            self.assertGreater(totals["games"], 0, "no simulated match in the career totals under python -I")


if __name__ == "__main__":
    unittest.main()
