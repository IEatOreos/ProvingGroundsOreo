"""Reach Forge Printer, phase 4: between a placement (fit.json's form) and a Blender object.

No bpy here: the test suite imports this module. A Blender object is handed over as plain
numbers, its world matrix as four rows of four and its own box as (min corner, max corner), and
everything is worked out with `mvar`'s own orientation functions (`axes`, `turn_for`, `up_raw`,
`up_vector`), which were checked in the game.

A placement is a dict as fit.json holds them: `piece`, `origin` (where Forge's placing point
goes), `turn` (degrees about up) and, for a tilted piece only, `up` (a unit vector). The
object's origin is Forge's placing point, its own x, y and z axes are the piece's, so its world
matrix is the placement.

Phase 4 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import math

from forge_printer import mvar

STRAIGHT_UP = mvar.join_up(2)   # the middle of the +Z face: written as "the world's up", as `print` does
SCALE_TOLERANCE = 1e-3          # an object's scale must be 1 to this
SKEW_TOLERANCE = 1e-4           # its axes square to each other to this (cosine)
SHAPE_TOLERANCE = 0.01          # its box the piece's box to this, world units
AXIS_SNAP = 1e-6                # an up this close to a cube axis is that axis (float32 noise; well under a grid step)
TURN_DECIMALS = 4               # a turn read back from Blender is rounded to this many decimals of a degree
CARRIED = ("part", "fill", "size")   # placement fields kept on the object: within_limits ranks by them
UNSURE_FACES = {3: "-X", 4: "-Y", 5: "-Z"}   # up on these faces: the turn's starting direction is not seen in the game


def _column(m, c):
    return (float(m[0][c]), float(m[1][c]), float(m[2][c]))


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _length(v):
    return math.sqrt(_dot(v, v))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def matrix_for(placement):
    """The world matrix (four rows of four) of an object standing for a placement."""
    up = placement.get("up", (0.0, 0.0, 1.0))
    x, y, z = mvar.axes(up, math.radians(placement["turn"]))
    o = placement["origin"]
    return [[x[0], y[0], z[0], float(o[0])],
            [x[1], y[1], z[1], float(o[1])],
            [x[2], y[2], z[2], float(o[2])],
            [0.0, 0.0, 0.0, 1.0]]


def box_mesh(piece):
    """A piece's box in its own axes, as (vertices, quads) with outward faces: the object's mesh."""
    (x0, y0, z0), (x1, y1, z1) = piece["min"], piece["max"]
    verts = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return verts, quads


def decompose(m):
    """(origin, unit x, y, z axes, scale per axis, mirrored, skew) of a world matrix."""
    columns = [_column(m, c) for c in range(3)]
    scale = tuple(_length(c) for c in columns)
    axes = tuple(tuple(c[i] / s for i in range(3)) if s > 0 else (0.0, 0.0, 0.0) for c, s in zip(columns, scale))
    mirrored = _dot(_cross(columns[0], columns[1]), columns[2]) < 0
    skew = max(abs(_dot(axes[0], axes[1])), abs(_dot(axes[0], axes[2])), abs(_dot(axes[1], axes[2])))
    return _column(m, 3), axes, scale, mirrored, skew


def _snapped(v):
    """v moved onto a cube axis when it is within AXIS_SNAP of one, else None."""
    for i in range(3):
        if abs(v[i]) > 1.0 - AXIS_SNAP:
            out = [0.0, 0.0, 0.0]
            out[i] = 1.0 if v[i] > 0 else -1.0
            return tuple(out)
    return None


def _degrees_between(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(a, b)))))


def up_and_turn(z_axis, x_axis):
    """(raw up, turn in degrees) a variant holds for a piece whose own z and x point so.
    Raises ValueError where no up value holds the direction."""
    try:
        raw = mvar.up_raw(z_axis)
    except ValueError:
        exact = _snapped(z_axis)
        if exact is None:
            raise
        raw = mvar.up_raw(exact)
    up = (0.0, 0.0, 1.0) if raw == STRAIGHT_UP else mvar.up_vector(raw)
    # to a ten-thousandth of a degree (a turn step is 0.022): Blender's 32-bit matrix makes +90 come back
    # as 89.99999, one step under where `print` writes an exact +90 (a step boundary)
    return raw, round(math.degrees(mvar.turn_for(up, x_axis)), TURN_DECIMALS)


def placement_from(matrix, piece_name, known, props=None, local_box=None):
    """What a Blender object stands for: (placement, None, warning) or (None, reason, None).

    `matrix` is the object's world matrix, `known` the piece table by name (pieces.by_name()),
    `props` the placement fields the object carries (CARRIED and "index"), `local_box` its mesh's
    own (min corner, max corner). The reason, when there is one, says in a sentence why the piece
    cannot be written and how to put it right."""
    piece = known.get(piece_name)
    if piece is None:
        return None, "%r is not a Forge piece the printer knows" % piece_name, None
    origin, axes, scale, mirrored, skew = decompose(matrix)
    if mirrored:
        return None, "it is mirrored (a negative scale); Reach cannot mirror a piece", None
    if any(abs(s - 1.0) > SCALE_TOLERANCE for s in scale):
        return None, ("it is scaled %s; Reach cannot scale a piece (Alt+S sets the scale back to 1)" %
                      " x ".join("%.2f" % s for s in scale)), None
    if skew > SKEW_TOLERANCE:
        return None, "it is skewed (its parent is scaled unevenly); Reach places a piece square", None
    if local_box is not None:
        worst = max(max(abs(a - b) for a, b in zip(local_box[0], piece["min"])),
                    max(abs(a - b) for a, b in zip(local_box[1], piece["max"])))
        if worst > SHAPE_TOLERANCE:
            return None, ("its shape is not the piece's (edited in Edit Mode, or its scale applied); "
                          "Reach places a piece at its own size"), None
    try:
        raw, turn = up_and_turn(axes[2], axes[0])
    except ValueError:
        return None, ("it leans %.0f degrees from straight up and %.0f from +X; a variant holds an up direction "
                      "no more than 45 degrees from straight up or from +X (along either side)" % (
                          _degrees_between(axes[2], (0.0, 0.0, 1.0)), _degrees_between(axes[2], (1.0, 0.0, 0.0)))), None
    placement = {"part": "added"}
    for key in CARRIED:
        if props and props.get(key) is not None:
            placement[key] = props[key]
    placement.update({"piece": piece_name, "origin": [origin[0], origin[1], origin[2]], "turn": turn})
    if raw != STRAIGHT_UP:
        placement["up"] = list(mvar.up_vector(raw))
    face = raw // mvar.UP_FACE_SPAN
    warning = None
    if face in UNSURE_FACES:
        warning = ("its up points %s: written, but how a turn starts under that up has not been seen in the game"
                   % UNSURE_FACES[face])
    return placement, None, warning
