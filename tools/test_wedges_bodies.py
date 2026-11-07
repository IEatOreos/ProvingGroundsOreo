"""(Custom) tools/wedges.py learn: a stop against another player or vehicle (a fight scrum) is no wedge spot; a stop with
only the driver's own gunner beside it is. A synthetic trace on Headlong's map data, far off its pads and roads.

Run: python tools/test_wedges_bodies.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wedges  # noqa: E402

MAP = "reach_cex_headlong"
H, OTHER = 111, 222                         # the driver's Warthog, another vehicle


def trace(spots):
    """Two drivers (ids 5, 6) stopping 4 s each, throttle down, at every spot: (x, y, extra) where extra is "body" (another
    vehicle 2 u off), "gunner" (player 7 riding the driver's Warthog) or None."""
    rows, t = [], 0.0
    for x, y, extra in spots:
        for k in (5, 6):
            for _ in range(9):
                players = [[k, 1, True, x, y, 3.0]]
                vehs = [[H, "warthog", x, y, 3.0]]
                if extra == "body":
                    vehs.append([OTHER, "warthog", x + 2.0, y, 3.0])
                if extra == "gunner":
                    players.append([7, 1, True, x - 0.9, y, 3.6])
                rows.append(json.dumps(dict(t=round(t, 2), world=players, vehicles=vehs)))
                rows.append(json.dumps(dict(t=round(t, 2), id=k, pos=[x, y, 3.0], seat="driver", veh=H,
                                            cmd=[1.0, 0.0, 0.0, 0, 0.0])))
                t += 0.5
            t += 30.0                             # (the next stop: 20 s apart or more)
    return "\n".join(rows) + "\n"


class WedgeBodyTests(unittest.TestCase):
    def learn(self, spots):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, f"trace_{MAP}_test.jsonl")
            with open(p, "w", encoding="utf-8") as f:
                f.write(trace(spots))
            found, _ = wedges.learn([p], MAP)
        return [(w[0], w[1]) for w in found]

    def test_scenery_stop_is_learned(self):
        self.assertEqual(self.learn([(500.0, 500.0, None)]), [(500.0, 500.0)])

    def test_stop_against_another_vehicle_is_left_out(self):
        self.assertEqual(self.learn([(500.0, 500.0, "body")]), [])

    def test_own_gunner_is_no_block(self):
        self.assertEqual(self.learn([(500.0, 500.0, "gunner")]), [(500.0, 500.0)])

    def test_mixed(self):
        self.assertEqual(sorted(self.learn([(500.0, 500.0, None), (520.0, 500.0, "body"), (540.0, 500.0, "gunner")])),
                         [(500.0, 500.0), (540.0, 500.0)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
