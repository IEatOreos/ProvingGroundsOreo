"""(custom, Nov 17) Reach Stockpile's flags are found by the map's tag names (LiveReach.OBJECTIVE_NAMES), not learned off a
stand. The owner's Pinnacle Stockpile on Forge World (20261117-205817, "Bots cant play stockpile on pinnacle", "Bots all
stuck here"): its flag stands sit on weapon spawns (a rocket launcher 0.15 u from one, a plasma pistol 0.12 u from two),
so the flag's tag counted as a gun's (LiveH3._placed) and was never learned; at 49.6 s a gun a bot dropped dying on a
stand was learned instead, and the bots stood on dropped guns as loose flags. The scene here is that layout's own stands
and spawns, in a stand-in for the game's object table read by the real LiveReach.objective_items."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain.core import Vec                 # noqa: E402
from brain.live import NONE, LiveReach     # noqa: E402

# Pinnacle's flag stands (stp_flag, all neutral) and the weapon spawns beside some of them (its .mvar)
STANDS = [(132.987, 198.939, 23.508), (140.563, 179.105, 26.558), (152.684, 186.405, 26.595), (129.819, 178.279, 27.25),
          (154.728, 200.571, 29.113), (119.498, 186.797, 30.721), (139.595, 186.267, 29.289),
          (139.586, 186.267, 29.303), (152.813, 186.513, 26.595), (131.343, 182.239, 28.307),
          (133.388, 198.225, 23.552), (147.166, 193.865, 29.12), (137.826, 177.874, 26.216)]
SPAWNS = [("rockets", (132.849, 198.939, 23.564)), ("plasma_pistol", (152.822, 186.405, 26.651)),
          ("magnum", (129.833, 178.64, 27.277))]

# the map's tag names by index (brain/forge.py _tag_names), as Forge World lists them around the flag's: the flag's
# own entries, then its sounds and shaders (LiveReach._own_name looks up to 4 entries back)
NAMES = [""] * 5000
NAMES[4489] = "objects\\weapons\\rifle\\dmr\\dmr"
NAMES[4819] = "objects\\weapons\\pistol\\plasma_pistol\\plasma_pistol"
NAMES[4984] = "objects\\weapons\\support_high\\rocket_launcher\\rocket_launcher"
NAMES[4676] = "objects\\weapons\\multiplayer\\flag\\flag"
NAMES[4677] = "fx\\material_effects\\weapons\\flag"
NAMES[4678] = "sound\\weapons\\flag\\flag_drop"
NAMES[4679] = "objects\\weapons\\multiplayer\\flag\\flag"
NAMES[4680] = "objects\\weapons\\multiplayer\\flag\\shaders\\flag_cloth_blue_nwo"
FLAG, DMR, PISTOL, ROCKETS = 0xE2A1 << 16 | 4679, 0xE10F << 16 | 4489, 0xE12D << 16 | 4819, 0xE133 << 16 | 4984

ENTS, OBJ, OBJ_SIZE = 0x1000, 0x10000, 0x400


class Memory:
    def __init__(s, size=0x40000):
        s.buf = bytearray(size)

    def read(s, addr, n):
        return bytes(s.buf[addr:addr + n])


def reach(objects, units=()):
    """A LiveReach over a stand-in object table: objects [(tag, pos)] lying loose; units [(index, team, pos, [tags in
    slots 0..3])], each slot's weapon an object parented to the unit. Returns (live, players)."""
    r = object.__new__(LiveReach)
    r.g = Memory()
    rows = []                                       # (type, tag, parent, pos, slots)

    def add(typ, tag, parent, pos):
        rows.append([typ, tag, parent, pos, None])
        k = len(rows) - 1
        return (0x100 + k) << 16 | k

    players = []
    for index, team, pos, slots in units:
        h = add(0, 0, NONE, pos)
        rows[h & 0xFFFF][4] = [add(2, tag, h, (0.0, 0.0, 0.0)) if tag else NONE for tag in slots]
        players.append(dict(index=index, team=team, unit=h, pos=pos))
    for tag, pos in objects:
        add(2, tag, NONE, pos)
    for k, (typ, tag, parent, pos, slots) in enumerate(rows):
        e, o = ENTS + k * 0x18, OBJ + k * OBJ_SIZE
        struct.pack_into("<H", r.g.buf, e, 0x100 + k)
        r.g.buf[e + LiveReach.TYPE_AT] = typ
        struct.pack_into("<Q", r.g.buf, e + 0x10, o)
        struct.pack_into("<I", r.g.buf, o, tag)
        struct.pack_into("<I", r.g.buf, o + LiveReach.PARENT_AT, parent)
        struct.pack_into("<3f", r.g.buf, o + LiveReach.POS_AT, *pos)
        if slots:
            struct.pack_into("<4I", r.g.buf, o + LiveReach.SLOTS_AT, *(slots + [NONE] * (4 - len(slots))))
    r._array = lambda off: (ENTS, len(rows), 0x18)
    r._placements = list(SPAWNS)
    r._tag_name_list = NAMES                        # (brain/forge.py _tag_names: the map's names, cached)
    return r, players


STAND_K = {k: Vec(*p) for k, p in enumerate(STANDS)}
# a bot on each team with its rifles, as at the start: a DMR and an assault rifle held (a gun on a stand is held by
# somebody too, so it is never learned by stand while anyone holds one: LiveH3 flags_by_stand)
TEAM = [(1, 1, (134.2, 194.4, 27.5), [DMR, 0]), (2, 0, (151.2, 173.4, 30.6), [DMR, 0])]


class StockpileFlagsByName(unittest.TestCase):
    def items(self, objects, units=TEAM, live=None):
        live, players = live or reach(objects, units)
        return live, players, live.objective_items(players, STAND_K, "stockpile")

    def test_flag_on_a_stand_beside_a_weapon_spawn_is_found(self):
        """The flag 0.15 u from the rocket launcher's spawn, as on Pinnacle: found, lying loose."""
        _, _, got = self.items([(FLAG, STANDS[0]), (ROCKETS, SPAWNS[0][1])])
        self.assertEqual(len(got), 1)
        self.assertIsNone(got[0]["carrier"])
        self.assertAlmostEqual(got[0]["pos"][0], STANDS[0][0], places=3)
        self.assertAlmostEqual(got[0]["pos"][1], STANDS[0][1], places=3)

    def test_four_flags_all_found(self):
        """Four Flags, Random Placement: one beside the rockets, two beside the plasma pistol, one alone."""
        flags = [STANDS[0], STANDS[2], STANDS[8], STANDS[11]]
        _, _, got = self.items([(FLAG, p) for p in flags] + [(ROCKETS, SPAWNS[0][1]), (PISTOL, SPAWNS[1][1])])
        self.assertEqual(sorted(round(it["pos"][0], 2) for it in got), sorted(round(p[0], 2) for p in flags))

    def test_a_gun_dropped_on_a_stand_is_no_flag(self):
        """A bot died on a stand (49.5 s: on 154.7, 200.6) and its gun lay there: not a flag, then or later."""
        live, players = reach([(FLAG, STANDS[0]), (PISTOL, (154.9, 200.47, 29.1))])
        for _ in range(3):
            got = live.objective_items(players, STAND_K, "stockpile")
            self.assertEqual([round(it["pos"][0], 2) for it in got], [round(STANDS[0][0], 2)])

    def test_carried_flag_is_its_carriers(self):
        """Bot 1 took the flag at 3.7 s (in its third slot): it is the carrier, so it runs it home."""
        _, _, got = self.items([], units=[(1, 1, (132.9, 198.7, 24.3), [DMR, 0, FLAG]), TEAM[1]])
        self.assertEqual([it["carrier"] for it in got], [1])

    def test_ctf_flags_still_learn_by_stand(self):
        """Only Stockpile's set is named: CTF's flags (_flag_tags) are still learned off their stands here."""
        live, players = reach([(FLAG, STANDS[0])])
        live._weapons_held(players)
        self.assertIn(FLAG, live._obj_tags["stockpile"])
        self.assertNotIn("_flag_tags", live.__dict__)

    def test_the_old_way_missed_them(self):
        """Learned off a stand (no names), as before: the flag beside a weapon spawn is a gun's tag and never learned,
        and the first gun dropped dying on a stand becomes the "flag" (the bug, kept as the reason for the names)."""
        live, players = reach([(FLAG, STANDS[0]), (ROCKETS, SPAWNS[0][1])])
        live.OBJECTIVE_NAMES = {}
        self.assertEqual(live.objective_items(players, STAND_K, "stockpile"), [])
        dropped, players = reach([(FLAG, STANDS[0]), (ROCKETS, SPAWNS[0][1]), (PISTOL, (154.9, 200.47, 29.1))])
        dropped.OBJECTIVE_NAMES = {}
        got = dropped.objective_items(players, STAND_K, "stockpile")
        self.assertEqual([round(it["pos"][0], 1) for it in got], [154.9])


if __name__ == "__main__":
    unittest.main()
