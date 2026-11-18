"""tools/death_autopsy.py on a made-up trace: a Demon (bot 3) and the owner (0), with a bot teammate of his (5);
three deaths, three causes, measured from the world rows the same way for a bot and a person (custom, Nov 18)."""
import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import death_autopsy as da  # noqa: E402


def row(i, team, pos, yaw, hp, bot, sights=-1, alive=True):
    r = [i, team, alive, pos[0], pos[1], pos[2], hp[0], hp[1], bot, False, yaw, 0.0, 0.0, [], sights]
    return r + ([None, None] if not bot else [])


def face(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])


def scene(t):
    """Everyone's world rows at t."""
    if t < 10.0:            # 1: 0 and 5 both on the Demon from 9 s; it fights 0
        d, o, f = (0, 0, 0), (6, 0, 0), (6, 2, 0)
        dh = [1.0, 1.0] if t < 9.0 else [max(0.0, 1.0 - (t - 9.0)), 1.0]
        return [row(3, 1, d, 0.0, dh, True, sights=0 if t >= 8.0 else -1),
                row(0, 0, o, face(o, d), [1.0, 1.0], False), row(5, 0, f, face(f, d), [1.0, 1.0], True)]
    if t < 22.0:            # 2: the owner, hit at 15 (to 0.4), back to 0.6, taken on at 21 by the Demon he sees
        d, o, f = (0, 0, 0), (8, 0, 0), (60, 60, 0)
        oh = [1.0, 1.0] if t < 15.0 else ([0.4, 1.0] if t < 17.0 else ([0.6, 1.0] if t < 21.0 else [0.0, 0.3]))
        return [row(3, 1, d, face(d, o), [1.0, 1.0], True, sights=0), row(0, 0, o, face(o, d), oh, False, sights=3),
                row(5, 0, f, 0.0, [1.0, 1.0], True)]
    d, o, f = (0, 0, 0), (-6, 0, 0), (90, 0, 0)    # 3: the Demon looking away, the owner behind it
    dh = [1.0, 1.0] if t < 29.0 else [0.0, 0.5]
    return [row(3, 1, d, 0.0, dh, True), row(0, 0, o, face(o, d), [1.0, 1.0], False, sights=3),
            row(5, 0, f, math.pi, [1.0, 1.0], True)]


TEAM = {3: 1, 0: 0, 5: 0}


def kill(t, v, k, hits, kb, c=6):
    return {"t": t, "kill": {"v": v, "k": k, "new": True, "o": k, "c": c, "m": 0, "hits": hits, "vt": TEAM[v],
                             "kt": TEAM[k], "vb": int(v != 0), "kb": kb, "vp": [0, 0, 0], "kp": [6, 0, 0],
                             "gt": int(t * 60), "st": 1}}


class AutopsyTests(unittest.TestCase):
    def read(self, rows):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        for r in rows:
            f.write(json.dumps(r) + "\n")
        f.close()
        try:
            return da.read_trace(f.name, los=lambda a, b: True)
        finally:
            os.remove(f.name)

    def test_three_deaths_a_bot_and_a_person(self):
        rows = [{"t": 0.0, "kill_record": 2}]
        for i, tier in ((3, "demon"), (5, "average")):
            rows.append({"t": 0.1, "meta": {"map": "reach_test", "game": "reach",
                                            "bot": {"id": i, "name": f"B{i}", "team": 1 if i == 3 else 0, "tier": tier}}})
        deaths_at = {10.0: kill(10.05, 3, 0, [[0, 6, 0, 1.0, 0.5, 6], [5, 6, 0, 0.0, 0.5, 30]], 0),
                     22.0: kill(22.05, 0, 3, [[3, 6, 0, 0.7, 0.6, 6]], 1),
                     30.0: kill(30.05, 3, 0, [[0, 6, 0, 1.0, 1.0, 3]], 0)}
        t = 1.0
        while t <= 30.0 + 1e-9:
            rows.append({"t": round(t, 2), "mode": "slayer", "world": scene(t)})
            rows.append({"t": round(t, 2), "id": 3, "pos": [0, 0, 0], "goal": "fight" if t < 23 else "objective",
                         "veh": -1, "hp": [1.0, 1.0]})
            if round(t, 2) in deaths_at:
                rows.append(deaths_at[round(t, 2)])
            t += 0.25
        deaths, players = self.read(rows)
        self.assertEqual([(d["group"], da.cause(d)) for d in deaths],
                         [("demon", "outnumbered"), (da.YOU, "started hurt"), ("demon", "never saw him")],
                         [(d["shield"], d["shooters"], d["seen"]) for d in deaths])
        self.assertAlmostEqual(deaths[1]["shield"], 0.6)
        self.assertIn("took the fight", da.tags(deaths[0]))
        self.assertIn("caught", da.tags(deaths[2]))
        self.assertEqual(deaths[2]["goal"], "objective")               # (a bot's own goal, from its rows)
        self.assertEqual((players[0].kills, players[3].kills), (2, 1))
        self.assertTrue(any(x[2] for x in players[3].twos))           # the 2-on-1 that killed it
        out = []
        da.compare(deaths, [players], out=out.append)
        self.assertIn("you", out[1])
        self.assertTrue(any(line.strip().startswith("died in it") for line in out), out)
        out = []
        da.report(deaths, [players], da.YOU, 1, out=out.append)
        self.assertTrue(out[0].startswith("you: 1 deaths"), out[0])

    def test_untouched_shield_read_counts_full(self):
        rows = [{"t": 0.0, "kill_record": 2},
                {"t": 0.1, "meta": {"map": "m", "game": "reach", "bot": {"id": 3, "name": "D", "team": 1,
                                                                         "tier": "demon"}}}]
        t = 1.0
        while t <= 20.0 + 1e-9:                                         # (a 0 read all along, then the fatal hit)
            hp = [0.0, 1.0] if t < 19.0 else [0.0, 0.2]
            rows.append({"t": round(t, 2), "mode": "slayer",
                         "world": [row(3, 1, (0, 0, 0), 0.0, hp, True), row(0, 0, (6, 0, 0), math.pi, [1, 1], False)]})
            t += 0.25
        rows.append(kill(20.05, 3, 0, [[0, 6, 0, 0.8, 0.0, 6]], 0))
        deaths, _ = self.read(rows)
        self.assertEqual(deaths[0]["shield"], 1.0)
        self.assertEqual(da.cause(deaths[0]), "lost a 1v1")


if __name__ == "__main__":
    unittest.main()
