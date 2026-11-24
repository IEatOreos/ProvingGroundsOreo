"""(custom, Nov 23) LiveH3._weapons_held looks each player's unit up once (brain/live.py): a weapon riding a marker is
placed by the marker, one riding a player's body is not, as before the change (the brain's profile of an 8v8 Forge World
CTF: every attached weapon looked every player's unit up again, 12.7% of its time)."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_reach_stockpile_flags import DMR, OBJ, OBJ_SIZE, TEAM, reach   # noqa: E402
from brain.live import LiveReach                                          # noqa: E402


def handle(k):
    return (0x100 + k) << 16 | k


class AttachedWeapons(unittest.TestCase):
    def scene(self, parent_k):
        # rows: unit 0 (k 0) and its DMR (k 1), unit 1 (k 2) and its DMR (k 3), then the loose ones: the attached DMR
        # (k 4) and a marker (k 5)
        live, players = reach([(DMR, (0.5, 0.5, 0.2)), (DMR, (10.0, 20.0, 3.0))], TEAM)
        struct.pack_into("<I", live.g.buf, OBJ + 4 * OBJ_SIZE + LiveReach.PARENT_AT, handle(parent_k))
        weapons, held = live._weapons_held(players)
        return {h: pos for h, tag, parent, pos in weapons}, held, players

    def test_on_a_marker_placed_by_it(self):
        pos, held, _ = self.scene(5)
        self.assertEqual([round(v, 3) for v in pos[handle(4)]], [10.5, 20.5, 3.2])

    def test_on_a_players_body_left_as_it_is(self):
        pos, held, _ = self.scene(0)
        self.assertEqual([round(v, 3) for v in pos[handle(4)]], [0.5, 0.5, 0.2])

    def test_the_slots_still_held(self):
        _, held, players = self.scene(5)
        self.assertIs(held[handle(1)], players[0])
        self.assertIs(held[handle(3)], players[1])


if __name__ == "__main__":
    unittest.main()
