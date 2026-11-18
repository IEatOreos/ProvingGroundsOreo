"""tools/death_autopsy.py on a made-up trace: one Demon, three deaths, three causes (custom, Nov 18)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_autopsy as da  # noqa: E402


def trace(rows):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for r in rows:
        f.write(json.dumps(r) + "\n")
    f.close()
    return f.name


def life(t0, t1, hp, beliefs=(), goal="fight"):
    """Bot 3's rows from t0 to t1, 10 a second: hp(t) -> [shield, health]; beliefs [(enemy, seen)]."""
    out, t = [], t0
    while t <= t1 + 1e-9:
        out.append({"t": round(t, 2), "id": 3, "pos": [0, 0, 0], "goal": goal, "veh": -1, "hp": hp(t),
                    "foes": [[0, 1.0, 1.0], [5, 0.0, 0.6]]})
        out.append({"t": round(t, 2), "id": 3, "think": [], "flags": {"seen": len(beliefs)},
                    "beliefs": [[k, 1, 1, 0, int(sn), "eyes", 0.0] for k, sn in beliefs]})
        t += 0.1
    return out


def kill(t, k, hits, c=6):
    return {"t": t, "kill": {"v": 3, "k": k, "new": True, "o": k, "c": c, "m": 0, "hits": hits, "vt": 1, "kt": 0,
                             "vb": 1, "kb": 0, "vp": [0, 0, 0], "kp": [6, 8, 0], "gt": int(t * 60), "st": 1}}


class AutopsyTests(unittest.TestCase):
    def test_three_deaths(self):
        rows = [{"t": 0.0, "kill_record": 2},
                {"t": 0.1, "meta": {"map": "reach_test", "game": "reach",
                                    "bot": {"id": 3, "name": "D", "team": 1, "tier": "demon"}}}]
        # 1: full going in, two men shooting it (0 and 5), both seen
        rows += life(1.0, 10.0, lambda t: [1.0, 1.0] if t < 9.0 else [max(0.0, 1.0 - (t - 9.0)), 1.0],
                     beliefs=[(0, True), (5, True)])
        rows.append(kill(10.05, 0, [[0, 6, 0, 1.0, 0.5, 6], [5, 6, 0, 0.0, 0.5, 30]]))
        # 2: hit at 15 (to 0.4), then 5 s later taken on at 0.6 by one man it saw: started hurt
        rows += life(11.0, 22.0, lambda t: [1.0, 1.0] if t < 15.0 else ([0.4, 1.0] if t < 17.0 else
                     ([0.6, 1.0] if t < 21.0 else [0.0, 0.3])), beliefs=[(0, True)])
        rows.append(kill(22.05, 0, [[0, 6, 0, 0.7, 0.6, 6]]))
        # 3: full, one man it never saw, on its way to the objective
        rows += life(23.0, 30.0, lambda t: [1.0, 1.0] if t < 29.0 else [0.0, 0.5], goal="objective")
        rows.append(kill(30.05, 0, [[0, 8, 0, 1.0, 1.0, 3]], c=8))
        p = trace(rows)
        try:
            deaths, bots = da.read_trace(p)
        finally:
            os.remove(p)
        self.assertEqual([da.cause(d) for d in deaths], ["outnumbered", "started hurt", "never saw him"],
                         [(d["shield"], d["shooters"], d["seen"]) for d in deaths])
        self.assertAlmostEqual(deaths[1]["shield"], 0.6)
        self.assertIn("caught on its way", da.tags(deaths[2]))
        self.assertIn("took the fight", da.tags(deaths[0]))
        self.assertEqual(bots[3].kills, 0)
        out = []
        da.report(deaths, [bots], "demon", 1, out=out.append)
        self.assertTrue(out[0].startswith("demon bots: 3 deaths"), out[0])

    def test_untouched_shield_read_counts_full(self):
        rows = [{"t": 0.0, "kill_record": 2},
                {"t": 0.1, "meta": {"map": "m", "game": "reach", "bot": {"id": 3, "name": "D", "team": 1,
                                                                         "tier": "demon"}}}]
        rows += life(1.0, 20.0, lambda t: [0.0, 1.0] if t < 19.0 else [0.0, 0.2], beliefs=[(0, True)])  # (0 read)
        rows.append(kill(20.05, 0, [[0, 6, 0, 0.8, 0.0, 6]]))
        p = trace(rows)
        try:
            deaths, _ = da.read_trace(p)
        finally:
            os.remove(p)
        self.assertEqual(deaths[0]["shield"], 1.0)
        self.assertEqual(da.cause(deaths[0]), "lost a 1v1")


if __name__ == "__main__":
    unittest.main()
