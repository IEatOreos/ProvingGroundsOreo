"""(custom, Nov 22) A power spawn this game type never fills (tools/live_bots.py item_check, ITEM_NOT_HERE). The owner:
"how did they have two empty weapon spots, They have ars and dmrs?" Asylum's .mvar places snipers the DMR game type
never spawns; the empty spawn's timer restarted every 90 s and sent a Demon onto it all match."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
import live_bots as lb  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402


class EmptySpawnTests(unittest.TestCase):
    def setUp(self):
        self.saved = lb.MAP, dict(lb.GROUND)
        lb.MAP = {"items": [dict(name="sniper", kind="weapon", value=0.9, pos=Vec(0, 0, 0), respawn=90.0)]}
        self.d = SimpleNamespace(item_up={0: 0.0}, bots={0: SimpleNamespace(id=0)})
        self.d.item_taken = lambda i, now, respawn: self.d.item_up.__setitem__(i, now + respawn)
        self.snap = Snapshot(0.0, [PlayerState(0, 0, "me", Vec(5, 0, 0))])
        self.empty = SimpleNamespace(objects=lambda types: [])

    def tearDown(self):
        lb.MAP = self.saved[0]
        lb.GROUND.clear()
        lb.GROUND.update(self.saved[1])

    def check(self, live, now):
        lb.item_check(live, {0: self.d}, {}, self.snap, now)

    def test_empty_after_its_time_is_not_in_this_game_type(self):
        self.check(self.empty, 10.0)                        # (seen empty: taken, its timer starts)
        self.assertEqual(self.d.item_up[0], 100.0)
        self.check(self.empty, 101.0)                       # (its time: not restarted, a run may still go)
        self.assertEqual(self.d.item_up[0], 100.0)
        self.check(self.empty, 100.0 + lb.ITEM_EMPTY_AFTER + 0.1)
        self.assertEqual(self.d.item_up[0], lb.ITEM_NOT_HERE)
        self.check(self.empty, 300.0)                       # (no new timer: no more runs)
        self.assertEqual(self.d.item_up[0], lb.ITEM_NOT_HERE)

    def test_a_gun_there_after_all(self):
        self.d.item_up[0] = lb.ITEM_NOT_HERE
        gun = SimpleNamespace(objects=lambda types: [(1, 2, "objects\\weapons\\rifle\\sniper", (0.2, 0.1, 0.0))])
        self.check(gun, 50.0)
        self.assertEqual(self.d.item_up[0], 0.0)

    def test_a_gun_back_on_time_is_timed_as_before(self):
        self.check(self.empty, 10.0)
        gun = SimpleNamespace(objects=lambda types: [(1, 2, "objects\\weapons\\rifle\\sniper", (0.2, 0.1, 0.0))])
        self.check(gun, 100.5)                              # (back on time: up again)
        self.assertEqual(self.d.item_up[0], 0.0)
        self.check(self.empty, 130.0)                       # (taken again later: a new timer, not "not here")
        self.assertEqual(self.d.item_up[0], 220.0)


if __name__ == "__main__":
    unittest.main()
