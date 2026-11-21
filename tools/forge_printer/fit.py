"""Reach Forge Printer, phase 3: Forge pieces fitted to a reference map's floors.

    python\\python.exe tools\\forge_printer fit FOLDER
    python\\python.exe tools\\forge_printer print FOLDER TEMPLATE OUT --offset DX DY DZ [--title TEXT]

`fit` reads a reference folder (what `reference` wrote), finds the walked floors as `surfaces`
does, and covers them with flat Forge blocks, largest first. It writes beside the reference:

  fit.json         every piece: its name, where its middle is, its top height, its turn
  <map>_fit.obj    the pieces as plain boxes, to look at beside the reference mesh

`print` writes those pieces into a copy of TEMPLATE, a Forge World variant MCC saved, moved by
the offset (the reference keeps its own map's coordinates). TEMPLATE is never changed and OUT
never overwritten.

How floors are covered. The walked floor is sampled on a quarter-unit grid, each cell keeping
the heights of the floors over it. Heights are taken busiest first; all floor within two tenths
of a unit of one is a level, and on a level each block goes to the first place, row by row,
where it lies wholly on uncovered floor; a second pass lets a tenth of a block hang over an
edge; a third fills the strips left between blocks by tucking a block a hundredth of a unit
under its neighbours. Blocks stay square to the map's axes for now, so round rooms and diagonal
walkways are only part covered, and slopes are not touched at all.

Both files are made from the game: they stay local and are never committed.
Phase 3 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import json
import math
import os

import numpy as np

from . import mvar, pieces, surfaces

GRID = 0.25          # the floor is sampled this far apart, world units
HEIGHT_STEP = 0.1    # floor heights are told apart to this
LEVEL_REACH = 1      # a level takes floor this many height steps above and below its own: a kerb is
                     # levelled, a ledge of a quarter unit or more (waist high to a Spartan) stays a ledge
LEVEL_NEAR = 0.105   # ... and only floor within this of the level's height is the level's, world units
LEVEL_BIN = 0.05     # a level's blocks all sit at the height most of its floor shares, told apart to this
OVERHANG = 0.10      # share of a block allowed past the floor's edge, in the second pass
TUCK_NEW = 0.35      # a block tucked under its neighbours must cover at least this share of new floor
TUCK_DROP = 0.01     # how much lower each tucked layer sits, world units
PLACEMENT_FLAGS = 204

# flat blocks, largest first: their tops are the floor
FLOOR_PIECES = ["Block 5x5 Flat", "Block 4x4 Flat", "Block 3x3 Flat", "Block 5x1 Flat", "Block 2x2 Flat",
                "Block 3x1 Flat", "Block 2x1 Flat", "Block 1x1 Flat"]

# ramps: the ones whose sloping face is a plain rectangle from their foot to their top, all 2 long.
# A slope is climbed with whichever of a family's pieces keeps the run of ramps nearest it, so any
# angle up to the family's steepest piece can be followed without a step between pieces.
GENTLE_RAMPS = ["Block 2x1 Flat", "Ramp 1x2 Shallow", "Ramp 1x2"]   # 1 wide: rise 0, 0.5, 1 over the 2-unit run
STEEP_RAMPS = ["Ramp 2x2", "Ramp 2x2 Steep"]                        # 2 wide: rise 1, 2
WIDE_RAMP = "Ramp 2x2"                                              # stands for two Ramp 1x2 side by side
RAMP_PIECES = ["Ramp 1x2 Shallow", "Ramp 1x2", "Ramp 2x2", "Ramp 2x2 Steep"]
RAMP_RUN = 2.0
GENTLE_MAX_TILT = 27.5  # slopes up to here use the 1-wide family (its steepest piece climbs at 26.6 degrees)
SLOPE_MAX_TILT = 48.0   # steeper than the steepest ramp (45 degrees) by more than this is not a ramp's job
END_PROBE = 0.4        # a slope's floors are looked for this far past each of its ends
FLOOR_REACH = 0.6      # ... and a floor block counts if it comes within this of that point
END_SNAP = 0.35        # ... and its top is within this of the slope's own height there
DIVE = 1.0             # a slope whose foot is this far under the floor over it is not a ramp
RUN_LIP_OK = 0.06      # choosing a run's pieces: a run this much too deep is fine (0.03 of lip at each end),
RUN_LIP_COST = 10.0    # past that a floor standing proud of its ramp is the worst outcome;
RUN_EARLY_COST = 0.3   # a ramp that comes up out of the lower floor a little early is mild,
RUN_SHAPE_COST = 0.1   # and straying from the slope's own line or angle on the way matters least
LANDING = 1.0          # a landing block reaches this far along the floor from where a ramp meets it
LANDING_MATCH = 0.03   # a floor block within this of the floor's height already does a landing's job
LANDING_REACH = 0.15   # the reference has floor there if its own floor is within this of that height
LANDING_DROP = 0.005   # a landing sits this far under the floor's height: never level with a block or a tucked one
ONTO_MAX = 0.6         # a floor block's edge or corner hanging this far out over a slope's top is still its edge
TILT_MAX = 44.0        # tilted ramps: an up vector can lean 45 degrees from +Z and no further
TILTED_PIECES = {5.0: "Block 5x1 Flat", 3.0: "Block 3x1 Flat", 2.0: "Block 2x1 Flat"}   # length up the slope: 1-wide block
TILTED_PAST_COST = 1.5 # a unit of block running on past the slope's foot counts as this many extra pieces
SLOPE_MIN_AREA = 1.5   # a sloping patch smaller than this is left for hand work, u2
SLOPE_FILL = 0.6       # the slope must be at least this share of a ramp's run and of its lane's width

# walls: Wall (2 long, 2 tall) and Wall Double (4 long, 2 tall), stood along the wall
WALL_UPRIGHT = 2.0     # a wall leans at most this many degrees
WALL_MIN_AREA = 2.0
WALL_MIN_LENGTH = 1.5
WALL_MIN_HEIGHT = 1.5
WALL_FILL = 0.5        # its triangles fill at least this share of its length x height (and at most 1 / this)
WALL_FOOT = 1.0        # walked ground within this of its foot, up or down
WALL_MAX_ROWS = 2      # a wall is built no higher than this many pieces (4 units): above that nobody touches it


class FitError(Exception):
    """A clear one-line reason the fit could not be made."""


# ---- the floor as a grid ----------------------------------------------------

def floor_layers(verts, tris, chosen):
    """The chosen triangles sampled on the grid. Returns (origin x, origin y, {height step:
    2-D array of the floor's height at each cell, NaN where there is none})."""
    if not len(chosen):
        return 0.0, 0.0, {}
    pts = verts[tris[chosen]]                                  # n x 3 x 3
    x0 = math.floor(pts[:, :, 0].min() / GRID) * GRID
    y0 = math.floor(pts[:, :, 1].min() / GRID) * GRID
    nx = int(math.ceil((pts[:, :, 0].max() - x0) / GRID)) + 1
    ny = int(math.ceil((pts[:, :, 1].max() - y0) / GRID)) + 1
    layers = {}
    for a, b, c in pts:
        ix0 = int(math.floor((min(a[0], b[0], c[0]) - x0) / GRID))
        ix1 = int(math.floor((max(a[0], b[0], c[0]) - x0) / GRID))
        iy0 = int(math.floor((min(a[1], b[1], c[1]) - y0) / GRID))
        iy1 = int(math.floor((max(a[1], b[1], c[1]) - y0) / GRID))
        cx = x0 + (np.arange(ix0, ix1 + 1) + 0.5) * GRID
        cy = y0 + (np.arange(iy0, iy1 + 1) + 0.5) * GRID
        gx, gy = np.meshgrid(cx, cy)
        det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(det) < 1e-12:
            continue
        wa = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / det
        wb = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / det
        wc = 1.0 - wa - wb
        inside = (wa >= -1e-9) & (wb >= -1e-9) & (wc >= -1e-9)
        if not inside.any():
            continue
        z = wa * a[2] + wb * b[2] + wc * c[2]
        for j, i in zip(*np.nonzero(inside)):
            step = int(round(float(z[j, i]) / HEIGHT_STEP))
            layer = layers.get(step)
            if layer is None:
                layer = layers[step] = np.full((ny, nx), np.nan, dtype=np.float32)
            layer[iy0 + j, ix0 + i] = z[j, i]
    return x0, y0, layers


# ---- covering one level -----------------------------------------------------

def _window_sums(grid, w, d):
    """How many true cells each w-by-d window holds (the window's low corner at each cell)."""
    s = np.zeros((grid.shape[0] + 1, grid.shape[1] + 1), dtype=np.int32)
    s[1:, 1:] = np.cumsum(np.cumsum(grid.astype(np.int32), axis=0), axis=1)
    if grid.shape[0] < d or grid.shape[1] < w:
        return np.zeros((0, 0), dtype=np.int32)
    return s[d:, w:] - s[:-d, w:] - s[d:, :-w] + s[:-d, :-w]


def cover(floor, shapes):
    """Covers a level's floor grid with blocks. `shapes` is [(name, cells wide, cells deep, turn)],
    largest first. Returns [(name, low cell x, low cell y, cells wide, cells deep, turn, sunk)]:
    `sunk` is 0 for a block that touches no other, and 1, 2, ... for one laid partly under
    blocks already there (each a hair lower than the ones it meets, so no two tops fight)."""
    covered = np.zeros_like(floor, dtype=bool)
    depth = np.zeros(floor.shape, dtype=np.int16)
    placed = []
    # 1 and 2: side by side, wholly on the floor, then with a little allowed past its edge
    for allowance in (0.0, OVERHANG):
        for name, w, d, turn in shapes:
            need = int(math.ceil(w * d * (1.0 - allowance) - 1e-9))
            free = floor & ~covered
            sums = _window_sums(free, w, d)
            if not sums.size:
                continue
            for y, x in zip(*np.nonzero(sums >= need)):
                if covered[y:y + d, x:x + w].any():
                    continue
                if int(free[y:y + d, x:x + w].sum()) < need:
                    continue
                covered[y:y + d, x:x + w] = True
                free[y:y + d, x:x + w] = False
                placed.append((name, int(x), int(y), w, d, turn, 0))
    # 3: the strips left between blocks, too narrow for a block of their own: a block wholly on the
    # floor that tucks under its neighbours, as long as enough of it is new floor
    for name, w, d, turn in shapes:
        on_floor = _window_sums(floor, w, d)
        if not on_floor.size:
            continue
        need_new = int(math.ceil(w * d * TUCK_NEW))
        for y, x in zip(*np.nonzero(on_floor == w * d)):
            window = covered[y:y + d, x:x + w]
            if int(window.size - window.sum()) < need_new:
                continue
            sunk = int(depth[y:y + d, x:x + w][window].max()) + 1 if window.any() else 0
            covered[y:y + d, x:x + w] = True
            depth[y:y + d, x:x + w] = np.maximum(depth[y:y + d, x:x + w], sunk)
            placed.append((name, int(x), int(y), w, d, turn, sunk))
    return placed


def shapes_for(table, names=FLOOR_PIECES):
    """[(name, cells wide, cells deep, turn in degrees)] for each block both ways round, largest first."""
    known = pieces.by_name(table)
    out = []
    for name in names:
        size = known[name]["size"]
        w, d = int(round(size[0] / GRID)), int(round(size[1] / GRID))
        out.append((name, w, d, 0.0))
        if w != d:
            out.append((name, d, w, 90.0))
    out.sort(key=lambda s: -(s[1] * s[2]))            # stable: the list's own order breaks ties
    return out


# ---- the whole fit ----------------------------------------------------------

def fit_floors(analysis, table=None):
    """Blocks for every walked floor of an analysed reference. Returns (placements, report)."""
    table = table or pieces.load()
    a = analysis
    chosen = np.nonzero((a["kinds"] == surfaces.FLOOR) & a["walked"])[0]
    x0, y0, layers = floor_layers(a["verts"], a["tris"], chosen)
    floor_cells = sum(int(np.isfinite(layer).sum()) for layer in layers.values())
    shapes = shapes_for(table)
    known = pieces.by_name(table)
    left = {step: np.isfinite(layer) for step, layer in layers.items()}
    placements = []
    covered_cells = 0
    overhang_cells = 0
    for step in sorted(layers, key=lambda s: (-int(np.isfinite(layers[s]).sum()), s)):
        near = [s for s in range(step - LEVEL_REACH, step + LEVEL_REACH + 1) if s in left]
        floor = np.zeros_like(left[step])
        for s in near:
            floor |= left[s]
        if not floor.any():
            continue
        # one height for the whole level, the one most of its floor is at: blocks side by side sit flush
        heights = np.concatenate([layers[s][left[s]] for s in near])
        bins = np.round(heights / LEVEL_BIN).astype(np.int64)
        values, counts = np.unique(bins, return_counts=True)
        level_top = float(heights[bins == values[int(np.argmax(counts))]].mean())
        # only floor really within reach of that height: two neighbouring height steps can be nearly
        # two steps apart, and such floor is another level's (it stays for that level's turn)
        mine = {s: left[s] & (np.abs(np.nan_to_num(layers[s], nan=1e9) - level_top) <= LEVEL_NEAR) for s in near}
        floor = np.zeros_like(left[step])
        for s in near:
            floor |= mine[s]
        if not floor.any():
            continue
        for name, x, y, w, d, turn, sunk in cover(floor, shapes):
            block = floor[y:y + d, x:x + w]
            top = level_top - sunk * TUCK_DROP
            overhang_cells += int(block.size - block.sum())
            for s in near:
                covered_cells += int((left[s][y:y + d, x:x + w] & mine[s][y:y + d, x:x + w]).sum())
                left[s][y:y + d, x:x + w] &= ~mine[s][y:y + d, x:x + w]
            placement = {"part": "floor", "piece": name,
                         "centre": [round(x0 + (x + w / 2.0) * GRID, 3), round(y0 + (y + d / 2.0) * GRID, 3)],
                         "top": round(top, 3),
                         "turn": turn,
                         "size": [round(w * GRID, 3), round(d * GRID, 3)],
                         "tucked": sunk}
            placement["origin"] = [round(c, 3) for c in origin_of(placement, known[name])]
            placements.append(placement)
    counts = {}
    for p in placements:
        counts[p["piece"]] = counts.get(p["piece"], 0) + 1
    cell = GRID * GRID
    report = {"floor_area": round(floor_cells * cell, 1),
              "covered_area": round(covered_cells * cell, 1),
              "coverage": round(covered_cells / floor_cells, 3) if floor_cells else 0.0,
              "overhang_area": round(overhang_cells * cell, 1),
              "pieces": len(placements),
              "tucked": sum(1 for p in placements if p["tucked"]),
              "by_piece": {name: counts[name] for name in FLOOR_PIECES if name in counts},
              "levels": len(layers)}
    return placements, report


def _turned(x, y, degrees):
    r = math.radians(degrees)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)


def _best_run(rises, length, rise):
    """The pieces for a slope `length` long between floors `rise` apart: (the rise of each piece,
    top one first; how far to lift the whole run).

    The run starts at the upper floor's edge and is laid downhill, each piece RAMP_RUN long. What
    matters is where it stands at the lower floor's edge, `length` down from the top:
      - above the floor there: no harm, the ramp just comes up out of the floor a little sooner
        (as long as its foot, further on, gets down to the floor);
      - below it: the floor stands proud of the ramp. Half of that is moved to the top by lifting
        the run; up to RUN_LIP_OK in all is let pass, more is all but ruled out.
    Every mix of one piece more than the slope needs, and of one more again, is tried."""
    best = None
    first = max(1, int(math.ceil(length / RAMP_RUN - 0.05)))
    for count in (first, first + 1):
        if count > 7:
            break
        runs = [()]
        for _ in range(count):
            runs = [run + (r,) for run in runs for r in rises]
        for run in runs:
            whole = int(length // RAMP_RUN)
            at_edge = sum(run[:whole])
            if whole < count:
                at_edge += run[whole] * (length - whole * RAMP_RUN) / RAMP_RUN
            over = at_edge - rise                          # how far under the lower floor's edge it would be
            worst, drop = 0.0, 0.0
            for i in range(min(whole, count)):
                drop += run[i]
                worst = max(worst, abs(drop - (i + 1) * RAMP_RUN * rise / length))
            if over > RUN_LIP_OK:
                cost = RUN_LIP_COST * over
            elif over > 0.0:
                cost = over
            else:
                cost = RUN_EARLY_COST * -over + RUN_LIP_COST * max(0.0, rise - sum(run))   # a foot left above the floor
                if whole < count:                          # the piece that goes on into the lower floor keeps the slope's angle
                    cost += RUN_SHAPE_COST * abs(run[whole] - RAMP_RUN * rise / length)
            key = (round(cost + RUN_SHAPE_COST * worst, 6), count, run)
            if best is None or key < best[0]:
                best = (key, list(run), max(0.0, over) / 2.0)
    if best is None:                                       # a very long slope: follow it piece by piece from the top
        run, drop = [], 0.0
        for i in range(first):
            want = min(rise, (i + 1) * RAMP_RUN * rise / length)
            step = max([r for r in rises if drop + r <= want + 0.02] or [min(rises)])
            run.append(step)
            drop += step
        return run, 0.0
    return best[1], best[2]


def _floor_tops_at(floors, x, y, reach):
    """The tops of the fitted floor blocks that cover a point or come within `reach` of it."""
    out = []
    for p in floors:
        cx, cy = p["centre"]
        if abs(x - cx) <= p["size"][0] / 2.0 + reach and abs(y - cy) <= p["size"][1] / 2.0 + reach:
            out.append(p["top"])
    return out


def _onto_slope(floors, height, along, across, s_top, t_mid, lanes):
    """How far the upper floor's blocks stand out over a slope's top edge, within its lanes.

    Floor blocks are square to the map and may hang a little past the floor's edge, so where a
    slope meets its floor at an angle their corners reach out over the slope (and a block can
    hang over a square-on slope too). A ramp starting at the reference's edge would have those
    corners standing proud of it. Returns the reach of the furthest one, 0.0 if none; a block
    more than ONTO_MAX out over the slope is not an edge hanging past and is left out."""
    reach = 0.0
    half = lanes / 2.0 - 0.05
    for p in floors:
        if abs(p["top"] - height) > LANDING_MATCH:
            continue
        cx, cy = p["centre"]
        hx, hy = p["size"][0] / 2.0, p["size"][1] / 2.0
        if abs(cx * along[0] + cy * along[1] - s_top) > hx + hy + ONTO_MAX:
            continue
        gx, gy = np.meshgrid(np.linspace(cx - hx, cx + hx, int(hx * 2 / 0.05) + 1),
                             np.linspace(cy - hy, cy + hy, int(hy * 2 / 0.05) + 1))
        s = gx * along[0] + gy * along[1]
        t = gx * across[0] + gy * across[1]
        over = (np.abs(t - t_mid) <= half) & (s < s_top - 1e-6)
        if not over.any():
            continue
        deepest = s_top - float(s[over].min())
        if deepest <= ONTO_MAX:
            reach = max(reach, deepest)
    return reach


def _tilted_lengths(surface):
    """The lengths of flat blocks to lay down a tilted face `surface` long, longest first: the fewest
    pieces that reach its foot without running far past it."""
    sizes = sorted(TILTED_PIECES, reverse=True)
    best = None
    stack = [()]
    while stack:
        combo = stack.pop()
        total = sum(combo)
        if total >= surface - 0.02:
            key = (len(combo) + TILTED_PAST_COST * max(0.0, total - surface), combo)
            if best is None or key < best:
                best = key
            continue
        if len(combo) < 8:
            stack.extend(combo + (size,) for size in sizes if not combo or size <= combo[-1])
    return list(best[1])


def fit_slopes(analysis, table=None, floors=(), tilted=False):
    """Ramps for the walked slopes of an analysed reference, each run of ramps tied to the floors
    it joins. `floors` are the floor placements already fitted (fit_floors); without them a
    slope's own ends are used.

    A flat sloping patch that is big enough runs from a low floor to a high one. Ramp pieces are
    all 2 long and rise 0 (a flat block), 0.5, 1 or 2, so:
      - the run starts at the upper floor's edge, at its height, and is laid downhill, each piece
        starting where the one above it stopped, so pieces join end to end;
      - it is as many pieces as cover the slope's length, or one more; what is left over of the
        last piece goes on under the lower floor;
      - the mix of pieces is chosen for where the run stands at the lower floor's edge (see
        _best_run): level with the floor if the pieces allow it, otherwise a little above it,
        so the ramp comes up out of the floor instead of the floor standing proud of the ramp.
    A slope 2 or more wide is laid in pairs of lanes (Ramp 2x2 for a rise of 1, Ramp 2x2 Steep for
    2, two 1-wide pieces side by side for the rest); the steep piece needs a pair. A slope that
    dives under a floor instead of meeting it (a root, a brace) gets nothing.

    With fitted floors, the run's top is where the upper floor's blocks really end: the reference's
    edge, or the furthest block corner hanging out over the slope (see _onto_slope), so no block
    stands proud of the ramp's top.

    With fitted floors, a run also gets landings (part "landing"): the floor blocks are laid on a
    grid and can stop short of where the ramp's face meets the floor, which leaves the ramp's
    sunk foot showing in a gap, or its top with nothing past it. Where the reference has floor at
    such a join and no block at the floor's height covers it, a flat block turned with the ramp is
    put there, LANDING long, a hair under the floor's height.
    Returns (placements, report)."""
    table = table or pieces.load()
    a = analysis
    known = pieces.by_name(table)
    flat0, flat1, flat2 = known["Block 1x1 Flat"], known["Block 2x1 Flat"], known["Block 2x2 Flat"]
    shallow, ramp1, ramp2, steep = (known[n] for n in ("Ramp 1x2 Shallow", "Ramp 1x2", "Ramp 2x2", "Ramp 2x2 Steep"))

    grid_x, grid_y, layers = 0.0, 0.0, {}
    if len(floors):                                              # the reference's own floor, for the landings
        walked_floor = np.nonzero((a["kinds"] == surfaces.FLOOR) & a["walked"])[0]
        grid_x, grid_y, layers = floor_layers(a["verts"], a["tris"], walked_floor)

    def reference_floor(point, height):
        """Does the reference have walked floor at this spot, at about this height?"""
        ix, iy = int(math.floor((point[0] - grid_x) / GRID)), int(math.floor((point[1] - grid_y) / GRID))
        for layer in layers.values():
            if 0 <= iy < layer.shape[0] and 0 <= ix < layer.shape[1]:
                if abs(layer[iy, ix] - height) <= LANDING_REACH:     # NaN where there is no floor: never near
                    return True
        return False

    placements = []
    total = fitted = 0.0
    landings = 0
    for number, patch in enumerate(a["patches"]):
        if patch["kind"] != "slope" or not patch.get("walked"):
            continue
        total += patch["area"]
        if patch["area"] < SLOPE_MIN_AREA or patch["tilt"] > SLOPE_MAX_TILT:
            continue
        pts = a["verts"][a["tris"][a["owner"] == number]].reshape(-1, 3)
        climb = math.radians(patch["uphill"])
        along = np.array([math.cos(climb), math.sin(climb)])
        across = np.array([-along[1], along[0]])
        s, t = pts[:, :2] @ along, pts[:, :2] @ across
        s_low, s_high = float(s.min()), float(s.max())
        length, width = s_high - s_low, float(t.max() - t.min())
        if length < RAMP_RUN * SLOPE_FILL or width < SLOPE_FILL:
            continue
        t_mid = float(t.min() + t.max()) / 2.0
        nx, ny, nz = patch["normal"]

        def on_slope(s_at):
            p = along * s_at + across * t_mid
            return (patch["offset"] - nx * p[0] - ny * p[1]) / nz

        # the floors at its two ends: a fitted block just past each end, at about the slope's own height there
        ends = []
        dives = False
        for s_end, outward in ((s_low, -1.0), (s_high, 1.0)):
            own = on_slope(s_end)
            p = along * (s_end + outward * END_PROBE) + across * t_mid
            tops = _floor_tops_at(floors, float(p[0]), float(p[1]), FLOOR_REACH)
            near = [top for top in tops if abs(top - own) <= END_SNAP]
            if outward < 0 and not near and any(top > own + DIVE for top in tops):
                dives = True
            ends.append(min(near, key=lambda top: abs(top - own)) if near else own)
        low, high = ends
        if dives or high - low < 0.1:
            continue
        angle = math.degrees(math.atan2(high - low, length))
        if angle > SLOPE_MAX_TILT:
            continue
        lanes = max(1, int(round(width)))
        rises = [0.0, 0.5, 1.0]
        # the run starts where the upper floor's blocks really end: at the reference's edge, or at the
        # furthest block corner hanging out over the slope
        onto = _onto_slope(floors, high, along, across, s_high, t_mid, lanes) if len(floors) else 0.0
        as_tilt = tilted and math.degrees(math.atan2(high - low, length - onto)) <= TILT_MAX
        if angle > GENTLE_MAX_TILT and not as_tilt:              # only the 2-wide steep ramp climbs faster than 1 in 2
            lanes = max(2, 2 * int(round(width / 2.0)))
            rises.append(2.0)
            onto = _onto_slope(floors, high, along, across, s_high, t_mid, lanes) if len(floors) else 0.0
        s_top = s_high - onto
        if as_tilt:
            chosen, lift = [], 0.0
        else:
            chosen, lift = _best_run(rises, length - onto, high - low)
        count = len(chosen)
        top = high + lift

        t_start = t_mid - lanes / 2.0
        spots = []                                               # (middle across, lanes covered)
        j = 0
        while j < lanes:
            if j + 1 < lanes:
                spots.append((t_start + j + 1.0, 2))
                j += 2
            else:
                spots.append((t_start + j + 0.5, 1))
                j += 1
        steps = []
        at = top
        for i, step in enumerate(chosen):
            steps.append((step, at, s_top - (i + 0.5) * RAMP_RUN))    # rise, height of its high end, its middle
            at -= step
        for step, upper, s_mid in reversed(steps):               # listed from the bottom up
            for t_at, covered in spots:
                if step == 0.0:
                    laid = [(flat2, t_at)] if covered == 2 else [(flat1, t_at)]
                elif step == 0.5:
                    laid = [(shallow, t_at - 0.5), (shallow, t_at + 0.5)] if covered == 2 else [(shallow, t_at)]
                elif step == 1.0:
                    laid = [(ramp2, t_at)] if covered == 2 else [(ramp1, t_at)]
                else:
                    laid = [(steep, t_at)]
                for piece, t_spot in laid:
                    mid = along * s_mid + across * t_spot
                    if "slope" in piece:
                        face = piece["slope"]
                        turn = (patch["uphill"] - face["uphill"]) % 360.0
                        off_x, off_y = _turned(face["centre"][0], face["centre"][1], turn)
                        origin = (float(mid[0]) - off_x, float(mid[1]) - off_y, upper - face["high"])
                    else:                                        # a level step: a flat block, its top at the height
                        turn = patch["uphill"] % 360.0
                        origin = origin_of({"centre": [float(mid[0]), float(mid[1])], "top": upper, "turn": turn}, piece)
                    placements.append({"part": "slope", "piece": piece["name"], "turn": round(turn, 2),
                                       "origin": [round(c, 3) for c in origin]})
        if as_tilt:
            # one flat face from the upper floor's edge to the lower floor's, at the slope's own angle: flat
            # blocks tilted to it, laid from the top edge down, the last one running on under the lower floor
            run, rise = length - onto, high - low
            lean = math.atan2(rise, run)
            climb = (float(along[0]), float(along[1]))
            up = mvar.up_vector(mvar.up_raw((-math.sin(lean) * climb[0], -math.sin(lean) * climb[1], math.cos(lean))))
            turn = mvar.decode_angle(mvar.encode_angle(
                mvar.turn_for(up, (math.cos(lean) * climb[0], math.cos(lean) * climb[1], math.sin(lean)))))
            x_axis, y_axis, z_axis = mvar.axes(up, turn)         # up the slope, level across it, out of its face
            edge = along * s_top + across * t_mid                # the middle of the run's top edge
            for t_at, covered in spots:
                down = 0.0
                for size in _tilted_lengths(math.hypot(run, rise)):
                    if covered == 2 and size == 2.0:
                        laid = [(flat2, t_at)]
                    else:
                        piece = known[TILTED_PIECES[size]]
                        laid = [(piece, t_at - 0.5), (piece, t_at + 0.5)] if covered == 2 else [(piece, t_at)]
                    for piece, t_spot in laid:
                        middle = ((piece["min"][0] + piece["max"][0]) / 2.0, (piece["min"][1] + piece["max"][1]) / 2.0,
                                  piece["max"][2])
                        centre = [float(edge[0]), float(edge[1]), high]
                        origin = [centre[i] + (t_spot - t_mid) * y_axis[i] - (down + size / 2.0) * x_axis[i]
                                  - middle[0] * x_axis[i] - middle[1] * y_axis[i] - middle[2] * z_axis[i] for i in range(3)]
                        placements.append({"part": "slope", "piece": piece["name"], "turn": round(math.degrees(turn), 3),
                                           "up": [round(c, 6) for c in up], "origin": [round(c, 3) for c in origin]})
                    down += size
            covered_area = length * min(width, float(lanes)) / math.cos(math.radians(angle))
        else:
            covered_area = min(length, count * RAMP_RUN) * min(width, float(lanes)) / math.cos(math.radians(angle))
        fitted += min(patch["area"], covered_area)

        if not len(floors):
            continue
        # landings: where the run meets each floor, a block under the join if the floor blocks stop short of it
        foot = s_low if as_tilt else None                        # where the run's face comes down to the lower floor
        for step, upper, s_mid in steps:
            if step > 0.0 and upper >= low >= upper - step:
                foot = s_mid + RAMP_RUN / 2.0 - (upper - low) / step * RAMP_RUN
                break
        for s_from, height in ((None if foot is None else foot - LANDING, low), (s_top, high)):
            if s_from is None:
                continue
            for t_at, covered in spots:
                marks = [(s_from + 0.05 + (LANDING - 0.1) * i / 4.0, t_at + (covered / 2.0 - 0.1) * j / 2.0)
                         for i in range(5) for j in range(-2, 3)]
                points = [along * s_at + across * t_spot for s_at, t_spot in marks]
                bare = [p for p in points
                        if not any(abs(top_ - height) <= LANDING_MATCH
                                   for top_ in _floor_tops_at(floors, float(p[0]), float(p[1]), 0.0))]
                if not bare or sum(1 for p in points if reference_floor(p, height)) * 2 < len(points):
                    continue                                     # the floor is there already, or was never there
                piece = flat1 if covered == 2 else flat0
                turn = (patch["uphill"] + (90.0 if covered == 2 else 0.0)) % 360.0
                mid = along * (s_from + LANDING / 2.0) + across * t_at
                top_ = height - LANDING_DROP
                origin = origin_of({"centre": [float(mid[0]), float(mid[1])], "top": top_, "turn": turn}, piece)
                placements.append({"part": "landing", "piece": piece["name"], "turn": round(turn, 2),
                                   "top": round(top_, 3), "origin": [round(c, 3) for c in origin]})
                landings += 1
    return placements, {"slope_area": round(total, 1), "fitted_area": round(fitted, 1),
                        "coverage": round(fitted / total, 3) if total else 0.0, "pieces": len(placements),
                        "landings": landings}


def fit_walls(analysis, table=None):
    """Wall pieces for the upright, roughly rectangular walls that stand beside walked ground.
    Returns (placements, report)."""
    table = table or pieces.load()
    a = analysis
    known = pieces.by_name(table)
    double, single = known["Wall Double"], known["Wall"]
    ground = {}
    for cell, z in a["reached"]:
        ground.setdefault(cell, []).append(z)
    placements, seen = [], set()
    length_fitted = 0.0
    for number, patch in enumerate(a["patches"]):
        if patch["kind"] != "wall" or abs(patch["tilt"] - 90.0) > WALL_UPRIGHT or patch["area"] < WALL_MIN_AREA:
            continue
        pts = a["verts"][a["tris"][a["owner"] == number]].reshape(-1, 3)
        face = np.array(patch["normal"][:2], dtype=float)
        face /= np.linalg.norm(face)                           # the way the wall faces, on the ground
        run = np.array([-face[1], face[0]])                    # along the wall
        s = pts[:, :2] @ run
        length, low = float(s.max() - s.min()), float(pts[:, 2].min())
        height = float(pts[:, 2].max()) - low
        if length < WALL_MIN_LENGTH or height < WALL_MIN_HEIGHT:
            continue
        if not WALL_FILL <= patch["area"] / (length * height) <= 1.0 / WALL_FILL:
            continue
        front = float((pts[:, :2] @ face).mean())
        # does anyone walk at its foot? look half a unit in front of it and behind it, along its length
        foot = False
        for k in range(int(length / surfaces.CELL) + 1):
            along = float(s.min()) + min(length, (k + 0.5) * surfaces.CELL)
            for side in (0.5, -0.5):
                p = run * along + face * (front + side)
                if surfaces._under(ground, (p[0], p[1], low + 0.3), above=WALL_FOOT, below=WALL_FOOT):
                    foot = True
        if not foot:
            continue
        rows = min(WALL_MAX_ROWS, int((height + 0.5) // single["size"][2]))
        doubles = int(length // double["size"][0])
        rest = length - doubles * double["size"][0]
        if rest >= double["size"][0] - 0.5:
            doubles, rest = doubles + 1, 0.0
        singles = 1 if rest >= WALL_MIN_LENGTH else 0
        if rows < 1 or doubles + singles == 0:
            continue
        laid = doubles * double["size"][0] + singles * single["size"][0]
        turn = math.degrees(math.atan2(run[1], run[0])) % 360.0
        at = float(s.min() + s.max()) / 2.0 - laid / 2.0
        row_pieces = [double] * doubles + [single] * singles
        for row in range(rows):
            along = at
            for piece in row_pieces:
                mid = run * (along + piece["size"][0] / 2.0) + face * (front - piece["size"][1] / 2.0)
                along += piece["size"][0]
                z = low + row * piece["size"][2] - piece["min"][2]
                key = (round(float(mid[0]) * 2), round(float(mid[1]) * 2), round(z * 2), int(round(turn % 180.0 / 5.0)) % 36)
                if key in seen:                                # the other face of the same thin wall
                    continue
                seen.add(key)
                placements.append({"part": "wall", "piece": piece["name"], "turn": round(turn, 2),
                                   "origin": [round(float(mid[0]), 3), round(float(mid[1]), 3), round(z, 3)]})
        length_fitted += laid
    return placements, {"pieces": len(placements), "length": round(length_fitted, 1)}


def origin_of(placement, piece):
    """Where Forge's placing point goes so the piece's box sits on the placement: (x, y, z)."""
    turn = math.radians(placement["turn"])
    mx = (piece["min"][0] + piece["max"][0]) / 2.0
    my = (piece["min"][1] + piece["max"][1]) / 2.0
    cx, cy = placement["centre"]
    return (cx - (mx * math.cos(turn) - my * math.sin(turn)),
            cy - (mx * math.sin(turn) + my * math.cos(turn)),
            placement["top"] - piece["max"][2])


def boxes_obj(path, placements, table):
    """The placed pieces as boxes (their measured sizes), one group per kind of piece."""
    known = pieces.by_name(table)
    lines, faces, n = [], {}, 0
    for p in placements:
        piece = known[p["piece"]]
        ax = mvar.axes(p.get("up", (0.0, 0.0, 1.0)), math.radians(p["turn"]))
        for z in (piece["min"][2], piece["max"][2]):
            for x, y in ((piece["min"][0], piece["min"][1]), (piece["max"][0], piece["min"][1]),
                         (piece["max"][0], piece["max"][1]), (piece["min"][0], piece["max"][1])):
                lines.append("v %.4f %.4f %.4f\n" % tuple(
                    p["origin"][i] + x * ax[0][i] + y * ax[1][i] + z * ax[2][i] + 0.0 for i in range(3)))
        b = n + 1
        quads = [(b + 4, b + 5, b + 6, b + 7), (b + 3, b + 2, b + 1, b), (b, b + 1, b + 5, b + 4),
                 (b + 1, b + 2, b + 6, b + 5), (b + 2, b + 3, b + 7, b + 6), (b + 3, b, b + 4, b + 7)]
        faces.setdefault(p["piece"], []).extend("f %d %d %d %d\n" % q for q in quads)
        n += 8
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.writelines(lines)
        for name in sorted(faces):
            f.write("g %s\n" % name.replace(" ", "_"))
            f.writelines(faces[name])


def build(folder):
    """Fits the reference in `folder` and writes fit.json and <map>_fit.obj there. Returns the fit dict."""
    try:
        analysis = surfaces.analyse(folder)
        table = pieces.load()
    except (surfaces.SurfaceError, pieces.PieceError) as error:
        raise FitError(str(error))
    floors, floor_report = fit_floors(analysis, table)
    slopes, slope_report = fit_slopes(analysis, table, floors, tilted=True)
    walls, wall_report = fit_walls(analysis, table)
    placements = floors + slopes + walls
    counts = {}
    for p in placements:
        counts[p["piece"]] = counts.get(p["piece"], 0) + 1
    total, unpriced = pieces.cost([p["piece"] for p in placements])
    report = {"floors": floor_report, "slopes": slope_report, "walls": wall_report,
              "pieces": len(placements), "by_piece": {name: counts[name] for name in sorted(counts)},
              "budget": total, "unpriced": unpriced}
    ref = analysis["ref"]
    name = ref["source"]["map"]
    out = {"source": ref["source"], "mesh": name + "_fit.obj",
           "rules": {"grid": GRID, "height_step": HEIGHT_STEP, "overhang": OVERHANG, "floor_pieces": FLOOR_PIECES,
                     "gentle_ramps": GENTLE_RAMPS, "steep_ramps": STEEP_RAMPS,
                     "tilted_ramps": sorted(TILTED_PIECES.values()), "tilt_max": TILT_MAX},
           "report": report, "placements": placements}
    boxes_obj(os.path.join(folder, out["mesh"]), placements, table)
    with open(os.path.join(folder, "fit.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    return out


def within_limits(placements, free_slots, budget_left):
    """The placements a variant has room and money for, and what had to be left out.
    Floors are kept before ramps and ramps before walls, the larger floor blocks first; a piece
    with no known price is counted as free and named in the report. Returns (kept, report):
    kept is in the placements' own order, report is {"kept", "left_out", "by_part", "ran_out_of",
    "cost", "unpriced"}."""
    rank = {"floor": 0, "slope": 1, "landing": 1, "wall": 2}

    def worth(item):
        index, p = item
        size = p.get("size", [0.0, 0.0])
        return (rank.get(p.get("part"), 3), -size[0] * size[1], index)

    kept, cost, ran_out, unpriced = set(), 0, None, set()
    for index, p in sorted(enumerate(placements), key=worth):
        value = pieces.price(p["piece"])
        if value is None:
            unpriced.add(p["piece"])
            value = 0
        if len(kept) >= free_slots:
            ran_out = ran_out or "object slots"
        elif cost + value > budget_left:
            ran_out = ran_out or "budget"
        else:
            kept.add(index)
            cost += value
    left = [p for i, p in enumerate(placements) if i not in kept]
    by_part = {}
    for p in left:
        by_part[p.get("part", "piece")] = by_part.get(p.get("part", "piece"), 0) + 1
    return ([p for i, p in enumerate(placements) if i in kept],
            {"kept": len(kept), "left_out": len(left), "by_part": by_part, "ran_out_of": ran_out,
             "cost": cost, "unpriced": sorted(unpriced)})


def add_to(variant, placements, offset, table=None):
    """Adds the placements to a Forge World variant, moved by offset. Returns the slots used."""
    if not pieces.is_forge_world(variant):
        raise FitError("printing needs a variant on today's Forge World palette (map %d, %d quota rows)" % (
            pieces.FORGE_WORLD_MAP_ID, pieces.FORGE_WORLD_QUOTA_ROWS))
    known = pieces.by_name(table or pieces.load())
    free = sum(1 for o in variant.objects if o is None)
    if len(placements) > free:
        raise FitError("%d pieces to place, the variant has %d free slots" % (len(placements), free))
    slots = []
    for p in placements:
        piece = known[p["piece"]]
        obj = mvar.ForgeObject(type_index=piece["row"], variant_index=piece["item"], placement_flags=PLACEMENT_FLAGS)
        x, y, z = p["origin"]
        try:
            variant.set_world_position(obj, x + offset[0], y + offset[1], z + offset[2])
        except ValueError:
            raise FitError("a piece at (%.1f, %.1f, %.1f) is outside Forge World: change the offset" % (
                x + offset[0], y + offset[1], z + offset[2]))
        obj.angle = mvar.encode_angle(math.radians(p["turn"]))
        if "up" in p:                                            # a tilted piece: where its own +z points
            obj.up = mvar.up_raw(p["up"])
        slots.append(variant.add_object(obj))
    variant.recount_quotas()
    return slots


def main(folder):
    try:
        out = build(folder)
    except FitError as error:
        print("fit: %s" % error)
        return 1
    report = out["report"]
    r = report["floors"]
    print("wrote fit.json and %s in %s" % (out["mesh"], folder))
    print("floors   %.1f u2 walked on %d height steps; %.1f u2 covered (%.0f%%) by %d blocks, %d tucked, "
          "%.1f u2 hanging past an edge" % (r["floor_area"], r["levels"], r["covered_area"], 100 * r["coverage"],
                                           r["pieces"], r["tucked"], r["overhang_area"]))
    r = report["slopes"]
    print("slopes   %.1f u2 walked; %.1f u2 fitted (%.0f%%) by %d ramps" % (
        r["slope_area"], r["fitted_area"], 100 * r["coverage"], r["pieces"]))
    r = report["walls"]
    print("walls    %d pieces along %.1f units of wall" % (r["pieces"], r["length"]))
    print("pieces   %d, budget %d%s" % (report["pieces"], report["budget"],
                                        " plus the unpriced: " + ", ".join(report["unpriced"]) if report["unpriced"] else ""))
    for name, count in report["by_piece"].items():
        print("  %-18s %d" % (name, count))
    return 0


def print_main(folder, template, out, offset, title=None):
    if os.path.exists(out):
        print("print: refusing to overwrite %s" % out)
        return 1
    try:
        with open(os.path.join(folder, "fit.json"), encoding="utf-8") as f:
            fit = json.load(f)
    except OSError:
        print("print: no fit.json in %s (run `forge_printer fit` first)" % folder)
        return 1
    try:
        f = mvar.MvarFile.read(template)
        v = f.variant
        free = sum(1 for o in v.objects if o is None)
        kept, limits = within_limits(fit["placements"], free, v.budget_max - v.budget_spent)
        if not kept:
            raise FitError("the template has no room for any piece (%d free slots, %d of budget left)" % (
                free, v.budget_max - v.budget_spent))
        slots = add_to(v, kept, offset)
        v.budget_spent += limits["cost"]
    except (OSError, mvar.FormatError, FitError, pieces.PieceError) as error:
        print("print: %s" % error)
        return 1
    problems = f.variant.problems()
    if problems:
        print("print: the result would not be sound: %s" % "; ".join(problems[:3]))
        return 1
    f.set_text(title or ("FP " + fit["source"]["map"])[:31])
    f.write(out)
    print("wrote %s: %d pieces added in slots %d..%d, %d of %d slots used, title %r" % (
        out, len(slots), slots[0], slots[-1], len(f.variant.placed_objects()), mvar.OBJECT_SLOTS,
        f.variant.header.title))
    print("budget %d of %d spent (%d for these pieces%s)" % (
        v.budget_spent, v.budget_max, limits["cost"],
        "; no price known for " + ", ".join(limits["unpriced"]) if limits["unpriced"] else ""))
    if limits["left_out"]:
        print("LEFT OUT %d pieces, out of %s: %s" % (
            limits["left_out"], limits["ran_out_of"],
            ", ".join("%d %s" % (n, part) for part, n in sorted(limits["by_part"].items()))))
    return 0
