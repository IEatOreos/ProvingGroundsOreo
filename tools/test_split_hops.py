"""(custom, Nov 23) A person's hops recorded as one jump are cut at the floor they touched (brain/maps.py split_hops).
The owner's Powerhouse roof climb (floor 39.42 -> rock top 39.96 -> roof 40.65) was filed as one 1.8 s jump rising
1.2 u that no bot could make (62 tries, 20261123-021733)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain import maps          # noqa: E402


class Ground:
    """A stand-in terrain: floor heights by x (a step function), every cell walkable."""

    def __init__(self, steps):
        self.steps = steps                      # [(from_x, z)], ascending
        self.lwalk = _Grid(lambda key: True)
        self.lz = _Grid(lambda key: self.floor(key[1] / 100.0))

    def floor(self, x):
        return [z for x0, z in self.steps if x >= x0][-1]

    def inside(self, x, y):
        return True

    def _node(self, p):
        return 0, int(round(p.x * 100)), 0


class _Grid:
    def __init__(self, f):
        self.f = f

    def __getitem__(self, key):
        return self.f(key)


def link(path, **kw):
    return dict(dict(take_off=path[0], land=path[-1], path=path, apex=max(q[2] for q in path), air_s=1.8, human=1), **kw)


# floor 0.0, a rock top at 0.55 from x 2.0, the roof at 1.2 from x 3.4
ROOF = Ground([(-10.0, 0.0), (2.0, 0.55), (3.4, 1.2)])
CLIMB = [[0.0, 0, 0.0], [0.4, 0, 0.2], [0.8, 0, 0.45], [1.2, 0, 0.6], [1.6, 0, 0.65], [2.2, 0, 0.6], [2.6, 0, 0.56],
         [2.9, 0, 0.75], [3.2, 0, 1.0], [3.5, 0, 1.25], [3.8, 0, 1.2]]


class SplitHops(unittest.TestCase):
    def test_the_roof_climb_is_two_hops(self):
        parts = maps.split_hops([link(CLIMB)], ROOF)
        self.assertEqual(len(parts), 2)
        a, b = parts
        self.assertEqual(a["take_off"], [0.0, 0, 0.0])
        self.assertEqual(a["land"], b["take_off"])
        self.assertAlmostEqual(a["land"][2], 0.6, places=6)           # down on the rock top (0.55, within HOP_TOUCH)
        self.assertEqual(b["land"], [3.8, 0, 1.2])
        self.assertEqual(b["runup"], b["take_off"])                     # the second hop leaves from that floor
        self.assertAlmostEqual(a["air_s"] + b["air_s"], 1.8, places=6)
        self.assertTrue(a["split"] and b["split"] and a["human"] and b["human"])
        self.assertEqual(len(maps.usable_links(parts)), 2)

    def test_a_plain_jump_stays_one(self):
        flat = Ground([(-10.0, 0.0), (3.0, 0.6)])
        jump = [[0.0, 0, 0.0], [0.6, 0, 0.35], [1.2, 0, 0.6], [1.8, 0, 0.7], [2.4, 0, 0.68], [3.0, 0, 0.62], [3.3, 0, 0.6]]
        self.assertEqual(maps.split_hops([link(jump)], flat), [link(jump)])

    def test_not_at_its_ends_nor_a_crouch_route_or_ride(self):
        near_end = [[0.0, 0, 0.0], [0.2, 0, 0.05], [0.3, 0, 0.0], [1.0, 0, 0.5], [2.0, 0, 0.7], [3.0, 0, 0.7]]
        self.assertEqual(len(maps.split_hops([link(near_end)], Ground([(-10.0, 0.0)]))), 1)
        for kw in (dict(kind="crouch"), dict(kind="route"), dict(ride=1)):
            self.assertEqual(len(maps.split_hops([link(CLIMB, **kw)], ROOF)), 1, kw)

    def test_a_launch_stays_whole(self):
        """A man cannon's throw recorded from the step onto its pad: cut there, its 15 u flight is no person's jump, so
        the recording stays one (HOP_MAX_FLAT; The Cage's cannon kept its take-off on the pad)."""
        pad = Ground([(-10.0, 0.0), (1.0, 0.3), (15.0, 0.0)])
        throw = [[0.0, 0, 0.0], [0.6, 0, 0.2], [1.2, 0, 0.32], [3.0, 0, 2.0], [7.0, 0, 4.0], [11.0, 0, 3.0], [15.5, 0, 0.0]]
        self.assertEqual(len(maps.split_hops([link(throw)], pad)), 1)

    def test_three_hops_in_a_row(self):
        steps = Ground([(-10.0, 0.0), (2.0, 0.55), (4.0, 1.1), (6.0, 1.65)])
        path = [[0.0, 0, 0.0], [0.7, 0, 0.4], [1.4, 0, 0.65], [2.4, 0, 0.6],
                [3.0, 0, 0.9], [3.6, 0, 1.2], [4.4, 0, 1.15],
                [5.0, 0, 1.45], [5.6, 0, 1.75], [6.3, 0, 1.65]]
        parts = maps.split_hops([link(path)], steps)
        self.assertEqual(len(parts), 3)
        self.assertEqual([round(p["land"][2], 2) for p in parts], [0.6, 1.15, 1.65])


if __name__ == "__main__":
    unittest.main()
