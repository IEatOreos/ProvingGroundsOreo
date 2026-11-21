"""Reach Forge Printer, phase 3: a test map that shows, in the game, how a variant file stores
turns and tilts.

    python\\python.exe tools\\forge_printer turntest FILE OUT --origin X Y Z [--title TEXT]

FILE is a Forge World variant MCC saved (it is not changed); OUT is the copy with the test
pieces added. X Y Z is a point on a flat floor with about 22 units of floor towards -x and 7
towards -y. Standing pieces show what cannot be read from files:

  row A, three Ramp 1x2 on the floor, 5 apart towards -x:   A1 turn 0, A2 turn +90, A3 turn +45
  row B, five small antennas floating 5.5 to the -y side:   B1-B3 "up" on faces 0, 1 and 5,
                                                            B4 and B5 face 2 pushed along u, along v
  three tall pillars 3.5 to the +y side of row A, so +y is "towards the pillars"

A ramp climbs towards its model's +x; an antenna's thin tip is its model's +z, the direction
the file calls "up". What the owner sees for each tells which way the stored numbers run.

Phase 3 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import math
import os

from . import mvar, pieces

PRICE_GUESS = 10          # budget added per piece; the real prices are not known yet
TILT_STEPS = 90           # grid steps off a face's middle for the two leaning antennas (about 23 degrees)
PLACEMENT_FLAGS = 204     # what nearly every building piece in MCC's own Forge World maps carries

# (label, piece, offset from the origin, turn in degrees, up as (face, u steps off middle, v steps off middle) or None)
STATIONS = [
    ("A1", "Ramp 1x2", (0.0, 0.0, 0.0), 0.0, None),
    ("A2", "Ramp 1x2", (-5.0, 0.0, 0.0), 90.0, None),
    ("A3", "Ramp 1x2", (-10.0, 0.0, 0.0), 45.0, None),
    ("B1", "ff_antenna", (0.0, -5.5, 2.5), 0.0, (0, 0, 0)),
    ("B2", "ff_antenna", (-5.0, -5.5, 2.5), 0.0, (1, 0, 0)),
    ("B3", "ff_antenna", (-10.0, -5.5, 4.5), 0.0, (5, 0, 0)),
    ("B4", "ff_antenna", (-15.0, -5.5, 2.5), 0.0, (2, TILT_STEPS, 0)),
    ("B5", "ff_antenna", (-20.0, -5.5, 2.5), 0.0, (2, 0, TILT_STEPS)),
    ("pillar", "Block 1x1 Tall", (0.0, 3.5, 1.0), 0.0, None),
    ("pillar", "Block 1x1 Tall", (-5.0, 3.5, 1.0), 0.0, None),
    ("pillar", "Block 1x1 Tall", (-10.0, 3.5, 1.0), 0.0, None),
]

# The second test (--test tilt), for what the first left open: how far a step off a face's middle
# leans the up vector, which way u and v run on a side face, and what a turn means once up is tilted.
#   row C, antennas floating on the -y side: C1 face 2 pushed to its +u edge (every reading says 45 degrees),
#     C2 face 2 half way there, C3 face 0 half way along u, C4 face 0 half way along v
#   row D, Ramp 1x2 floating over the first test's ramp spots: D1 up = face 0 turn 0, D2 up = face 0
#     turn +90, D3 up = face 1 turn 0
HALF = 104
EDGE = 208
TILT_STATIONS = [
    ("C1", "ff_antenna", (0.0, -5.5, 2.5), 0.0, (2, EDGE, 0)),
    ("C2", "ff_antenna", (-5.0, -5.5, 2.5), 0.0, (2, HALF, 0)),
    ("C3", "ff_antenna", (-10.0, -5.5, 2.5), 0.0, (0, HALF, 0)),
    ("C4", "ff_antenna", (-15.0, -5.5, 2.5), 0.0, (0, 0, HALF)),
    ("D1", "Ramp 1x2", (0.0, 0.0, 2.5), 0.0, (0, 0, 0)),
    ("D2", "Ramp 1x2", (-5.0, 0.0, 2.5), 90.0, (0, 0, 0)),
    ("D3", "Ramp 1x2", (-10.0, 0.0, 2.5), 0.0, (1, 0, 0)),
    ("pillar", "Block 1x1 Tall", (0.0, 3.5, 1.0), 0.0, None),
    ("pillar", "Block 1x1 Tall", (-5.0, 3.5, 1.0), 0.0, None),
    ("pillar", "Block 1x1 Tall", (-10.0, 3.5, 1.0), 0.0, None),
]
TESTS = {"turn": STATIONS, "tilt": TILT_STATIONS}


def add_to(variant, origin, test="turn"):
    """Adds a test's pieces to a Forge World variant. Returns [(label, slot, piece name, position)]."""
    if not pieces.is_forge_world(variant):
        raise ValueError("the test needs a variant on today's Forge World palette (map %d, %d quota rows)" % (
            pieces.FORGE_WORLD_MAP_ID, pieces.FORGE_WORLD_QUOTA_ROWS))
    table = pieces.load()
    known = {p["name"]: p for p in table["pieces"]}
    middle = (mvar.UP_GRID - 1) // 2
    placed = []
    for label, name, offset, turn, up in TESTS[test]:
        piece = known[name]
        obj = mvar.ForgeObject(type_index=piece["row"], variant_index=piece["item"],
                               placement_flags=PLACEMENT_FLAGS)
        position = tuple(origin[i] + offset[i] for i in range(3))
        variant.set_world_position(obj, *position)
        obj.angle = mvar.encode_angle(math.radians(turn))
        if up is not None:
            obj.up = mvar.join_up(up[0], middle + up[1], middle + up[2])
        placed.append((label, variant.add_object(obj), name, position))
    variant.recount_quotas()
    variant.budget_spent += PRICE_GUESS * len(placed)
    return placed


def main(source, out, origin, title=None, test="turn"):
    title = title or {"turn": "FP Turn Test", "tilt": "FP Tilt Test"}[test]
    if os.path.exists(out):
        print("turntest: refusing to overwrite %s" % out)
        return 1
    try:
        f = mvar.MvarFile.read(source)
        placed = add_to(f.variant, origin, test)
    except (OSError, ValueError, pieces.PieceError) as error:
        print("turntest: %s" % error)
        return 1
    problems = f.variant.problems()
    if problems:
        print("turntest: the result would not be sound: %s" % "; ".join(problems))
        return 1
    f.set_text(title)
    f.write(out)
    for label, slot, name, position in placed:
        print("%-6s slot %3d  %-16s at (%.2f, %.2f, %.2f)" % ((label, slot, name) + position))
    print("wrote %s  (%d pieces added, budget now %d, title %r)" % (out, len(placed), f.variant.budget_spent, title))
    return 0
