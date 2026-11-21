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

--test tilt and --test slope are the follow-ups, described where their pieces are listed below:
tilt asked how far a step leans the up vector and what a turn means under a tilt; slope lays
eight tilted ramps that meet their platforms flush if those answers are right.

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

# The third test (--test slope): the tilt test's reading put to work. Eight tilted ramps, each a
# Block 5x1 Flat lying up a slope between two level Block 2x2 Flat platforms, floating in two rows of
# four (12 apart towards -x, the rows 6 and 18 to the -y side). The ramp's top is written to run from
# the lower platform's top edge to the upper one's. If a grid step leans the up vector as read
# (atan(steps / 208)) and a turn starts where read, both ends meet their platforms flush and the
# ramp's sides line up with them. One degree out shows as 0.04 at each end; a wrong turn shows as a
# ramp lying askew.
#   (label, the way it climbs in degrees counter-clockwise from +x, its slope in degrees)
SLOPE_CHECKS = [
    ("S1", 0.0, 10.0), ("S2", 0.0, 20.0), ("S3", 0.0, 35.0), ("S4", 90.0, 20.0),       # square to the map
    ("S5", 30.0, 20.0), ("S6", 60.0, 20.0), ("S7", 240.0, 15.0), ("S8", 150.0, 25.0),  # leaning in x and y at once
]
SLOPE_RAMP, SLOPE_PLATFORM = "Block 5x1 Flat", "Block 2x2 Flat"


def slope_pieces(known):
    """The slope test's pieces: [(label, piece name, offset from the origin, raw turn, raw up or None)]."""
    ramp, flat = known[SLOPE_RAMP], known[SLOPE_PLATFORM]
    out = []
    for n, (label, heading, slope) in enumerate(SLOPE_CHECKS):
        centre = (-12.0 * (n % 4), -6.0 - 12.0 * (n // 4), 4.0)        # the middle of the ramp's top
        around, lean = math.radians(heading), math.radians(slope)
        climb = (math.cos(around), math.sin(around))
        raw_up = mvar.up_raw((-math.sin(lean) * climb[0], -math.sin(lean) * climb[1], math.cos(lean)))
        up = mvar.up_vector(raw_up)                                     # what the file can hold, a hair off the wish
        raw_turn = mvar.encode_angle(mvar.turn_for(up, (math.cos(lean) * climb[0], math.cos(lean) * climb[1], math.sin(lean))))
        x_axis, y_axis, z_axis = mvar.axes(up, mvar.decode_angle(raw_turn))
        middle = ((ramp["min"][0] + ramp["max"][0]) / 2.0, (ramp["min"][1] + ramp["max"][1]) / 2.0, ramp["max"][2])
        offset = tuple(centre[i] - middle[0] * x_axis[i] - middle[1] * y_axis[i] - middle[2] * z_axis[i] for i in range(3))
        out.append((label, SLOPE_RAMP, offset, raw_turn, raw_up))
        half = (ramp["max"][0] - ramp["min"][0]) / 2.0
        flat_turn = mvar.encode_angle(around)
        level = (math.cos(mvar.decode_angle(flat_turn)), math.sin(mvar.decode_angle(flat_turn)))
        for end, edge in ((-1.0, flat["max"][0]), (1.0, flat["min"][0])):   # the platform's near edge at the ramp's end
            at = tuple(centre[i] + end * half * x_axis[i] for i in range(3))
            out.append((label + (" low" if end < 0 else " high"), SLOPE_PLATFORM,
                        (at[0] - edge * level[0], at[1] - edge * level[1], at[2] - flat["max"][2]), flat_turn, None))
    return out


def add_to(variant, origin, test="turn"):
    """Adds a test's pieces to a Forge World variant. Returns [(label, slot, piece name, position)]."""
    if not pieces.is_forge_world(variant):
        raise ValueError("the test needs a variant on today's Forge World palette (map %d, %d quota rows)" % (
            pieces.FORGE_WORLD_MAP_ID, pieces.FORGE_WORLD_QUOTA_ROWS))
    table = pieces.load()
    known = {p["name"]: p for p in table["pieces"]}
    middle = (mvar.UP_GRID - 1) // 2
    if test == "slope":
        entries = slope_pieces(known)
    else:
        entries = [(label, name, offset, mvar.encode_angle(math.radians(turn)),
                    None if up is None else mvar.join_up(up[0], middle + up[1], middle + up[2]))
                   for label, name, offset, turn, up in TESTS[test]]
    placed = []
    for label, name, offset, raw_turn, raw_up in entries:
        piece = known[name]
        obj = mvar.ForgeObject(type_index=piece["row"], variant_index=piece["item"],
                               placement_flags=PLACEMENT_FLAGS)
        position = tuple(origin[i] + offset[i] for i in range(3))
        variant.set_world_position(obj, *position)
        obj.angle = raw_turn
        if raw_up is not None:
            obj.up = raw_up
        placed.append((label, variant.add_object(obj), name, position))
    variant.recount_quotas()
    variant.budget_spent += PRICE_GUESS * len(placed)
    return placed


def main(source, out, origin, title=None, test="turn"):
    title = title or {"turn": "FP Turn Test", "tilt": "FP Tilt Test", "slope": "FP Slope Test"}[test]
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
