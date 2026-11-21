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
LEVEL_REACH = 2      # a level takes floor this many height steps above and below its own
OVERHANG = 0.10      # share of a block allowed past the floor's edge, in the second pass
TUCK_NEW = 0.35      # a block tucked under its neighbours must cover at least this share of new floor
TUCK_DROP = 0.01     # how much lower each tucked layer sits, world units
PLACEMENT_FLAGS = 204

# flat blocks, largest first: their tops are the floor
FLOOR_PIECES = ["Block 5x5 Flat", "Block 4x4 Flat", "Block 3x3 Flat", "Block 5x1 Flat", "Block 2x2 Flat",
                "Block 3x1 Flat", "Block 2x1 Flat", "Block 1x1 Flat"]

# ramps: the ones whose sloping face is a plain rectangle from their foot to their top
RAMP_PIECES = ["Ramp 2x2", "Ramp 1x2", "Ramp 1x2 Shallow", "Ramp 2x2 Steep"]
SLOPE_MIN_AREA = 1.5   # a sloping patch smaller than this is left for hand work, u2
LEAN_MATCH = 7.0       # a ramp may be this many degrees steeper or shallower than the slope it stands in for
SLOPE_FILL = 0.6       # the slope must be at least this share of the ramp's run and of its width

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
        level = {s: left[s].copy() for s in near}             # the level's floor before any block
        for name, x, y, w, d, turn, sunk in cover(floor, shapes):
            block = floor[y:y + d, x:x + w]
            heights = np.concatenate([layers[s][y:y + d, x:x + w][level[s][y:y + d, x:x + w]] for s in near])
            top = float(np.median(heights)) - sunk * TUCK_DROP
            overhang_cells += int(block.size - block.sum())
            for s in near:
                covered_cells += int(left[s][y:y + d, x:x + w].sum())
                left[s][y:y + d, x:x + w] = False
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


def fit_slopes(analysis, table=None):
    """Ramps for the walked slopes of an analysed reference: each flat sloping patch that is big
    enough takes the ramp whose own slope is nearest its tilt, turned to climb the same way and
    repeated along and across it. Returns (placements, report)."""
    table = table or pieces.load()
    a = analysis
    known = pieces.by_name(table)
    ramps = [known[name] for name in RAMP_PIECES]
    placements = []
    total = fitted = 0.0
    for number, patch in enumerate(a["patches"]):
        if patch["kind"] != "slope" or not patch.get("walked"):
            continue
        total += patch["area"]
        if patch["area"] < SLOPE_MIN_AREA:
            continue
        pts = a["verts"][a["tris"][a["owner"] == number]].reshape(-1, 3)
        climb = math.radians(patch["uphill"])
        along = np.array([math.cos(climb), math.sin(climb)])
        across = np.array([-along[1], along[0]])
        s, t = pts[:, :2] @ along, pts[:, :2] @ across
        length, width = float(s.max() - s.min()), float(t.max() - t.min())
        fits = [r for r in ramps if abs(r["slope"]["lean"] - patch["tilt"]) <= LEAN_MATCH
                and r["slope"]["run"] * SLOPE_FILL <= length and r["slope"]["width"] * SLOPE_FILL <= width]
        if not fits:
            continue
        ramp = min(fits, key=lambda r: (abs(r["slope"]["lean"] - patch["tilt"]) > 1.0,     # a near-exact slope first,
                                        -r["slope"]["run"] * r["slope"]["width"]))          # then the largest
        face = ramp["slope"]
        n_along = max(1, int(round(length / face["run"])))
        n_across = max(1, int(round(width / face["width"])))
        s_start = float(s.min() + s.max()) / 2.0 - n_along * face["run"] / 2.0
        t_start = float(t.min() + t.max()) / 2.0 - n_across * face["width"] / 2.0
        nx, ny, nz = patch["normal"]
        turn = (patch["uphill"] - face["uphill"]) % 360.0
        off_x, off_y = _turned(face["centre"][0], face["centre"][1], turn)
        for i in range(n_along):
            for j in range(n_across):
                mid = along * (s_start + (i + 0.5) * face["run"]) + across * (t_start + (j + 0.5) * face["width"])
                z = (patch["offset"] - nx * mid[0] - ny * mid[1]) / nz
                placements.append({"part": "slope", "piece": ramp["name"], "turn": round(turn, 2),
                                   "origin": [round(float(mid[0]) - off_x, 3), round(float(mid[1]) - off_y, 3),
                                              round(z - (face["low"] + face["high"]) / 2.0, 3)]})
        laid = n_along * n_across * face["run"] * face["width"] / math.cos(math.radians(face["lean"]))
        fitted += min(patch["area"], laid)
    return placements, {"slope_area": round(total, 1), "fitted_area": round(fitted, 1),
                        "coverage": round(fitted / total, 3) if total else 0.0, "pieces": len(placements)}


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
        ox, oy, oz = p["origin"]
        turn = math.radians(p["turn"])
        c, s = math.cos(turn), math.sin(turn)
        for z in (piece["min"][2], piece["max"][2]):
            for x, y in ((piece["min"][0], piece["min"][1]), (piece["max"][0], piece["min"][1]),
                         (piece["max"][0], piece["max"][1]), (piece["min"][0], piece["max"][1])):
                lines.append("v %.4f %.4f %.4f\n" % (ox + x * c - y * s + 0.0, oy + x * s + y * c + 0.0, oz + z + 0.0))
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
    slopes, slope_report = fit_slopes(analysis, table)
    walls, wall_report = fit_walls(analysis, table)
    placements = floors + slopes + walls
    counts = {}
    for p in placements:
        counts[p["piece"]] = counts.get(p["piece"], 0) + 1
    report = {"floors": floor_report, "slopes": slope_report, "walls": wall_report,
              "pieces": len(placements), "by_piece": {name: counts[name] for name in sorted(counts)}}
    ref = analysis["ref"]
    name = ref["source"]["map"]
    out = {"source": ref["source"], "mesh": name + "_fit.obj",
           "rules": {"grid": GRID, "height_step": HEIGHT_STEP, "overhang": OVERHANG, "floor_pieces": FLOOR_PIECES,
                     "ramp_pieces": RAMP_PIECES, "lean_match": LEAN_MATCH},
           "report": report, "placements": placements}
    boxes_obj(os.path.join(folder, out["mesh"]), placements, table)
    with open(os.path.join(folder, "fit.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    return out


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
    print("pieces   %d" % report["pieces"])
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
        slots = add_to(f.variant, fit["placements"], offset)
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
    return 0
