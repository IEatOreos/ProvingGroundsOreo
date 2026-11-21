"""Reach Forge Printer, phase 3 (first part): the play space cut out of a reference mesh and
sorted into floors, slopes, walls and ceilings.

    python\\python.exe tools\\forge_printer surfaces FOLDER [--side 4] [--below 3] [--above 8]

FOLDER is what `forge_printer reference <map>` wrote (<map>.obj and reference.json). Writes
beside them:

  <map>_play.obj   the mesh cut to the play space, one group per kind of surface
  surfaces.json    the cut box, each kind's area, and the flat patches a Forge piece could cover

How the play space is found: the walkable ground under the spawns is followed outward on foot
(short jumps, drops and gaps allowed) until nothing new is reached; everything outside a box
around that ground, grown a little to the sides and below and more above, is backdrop.

Both files are made from the game: they stay local and are never committed.
Phase 3 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import json
import math
import os

import numpy as np

KINDS = ("floor", "slope", "wall", "ceiling")
FLOOR, SLOPE, WALL, CEILING = range(4)

# a surface's kind, from how far its outward side leans away from straight up (degrees)
FLOOR_MAX_DEG = 10.0       # up to here: a floor
SLOPE_MAX_DEG = 55.0       # up to here: a slope a ramp could stand in for
CEILING_MIN_DEG = 125.0    # from here: a ceiling; in between: a wall

# following the ground on foot, to find the play space (generous: this only decides the cut)
WALK_MAX_DEG = 50.0        # ground steeper than this is not walked on
CELL = 0.5                 # the ground is sampled about this far apart, world units
LEVEL = 0.25               # ground heights in one cell closer than this are one level
GROUND_COVER = 0.4         # share of a cell that ground must cover to count (Guardian's branches cover far less)
JUMP_UP = 1.0              # a step or jump up
DROP = 4.0                 # a drop down
GAP = 2.0                  # a gap jumped across
WALKED_NEAR = 0.5          # a floor or slope this close to walked ground, up or down, is walked ground

# the cut: the box around the walked ground, grown by these
SIDE, BELOW, ABOVE = 4.0, 3.0, 8.0

# flat patches
PATCH_ANGLE_DEG = 6.0      # a patch's triangles lean within this of its first one
PATCH_OFFSET = 0.08        # ... and lie within this of its plane
PATCH_LISTED = 0.25        # patches smaller than this are counted but not listed (detail)
WELD = 3                   # decimals two corners must share to count as one point


class SurfaceError(Exception):
    """A clear one-line reason the surfaces could not be made."""


# ---- mesh in and out --------------------------------------------------------

def load_obj(path):
    """(vertices n x 3, triangles m x 3) of an OBJ; faces with more corners are fanned."""
    verts, tris = [], []
    with open(path, encoding="ascii", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                verts.append([float(c) for c in line.split()[1:4]])
            elif line.startswith("f "):
                idx = [int(c.split("/")[0]) for c in line.split()[1:]]
                idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
                for k in range(1, len(idx) - 1):
                    tris.append((idx[0], idx[k], idx[k + 1]))
    if not tris:
        raise SurfaceError("%s holds no triangles" % os.path.basename(path))
    return np.array(verts, dtype=float).reshape(-1, 3), np.array(tris, dtype=np.int64)


def save_obj(path, verts, tris, kinds):
    """Writes the triangles grouped by kind (g floor, g slope, ...), shared corners written once."""
    index = {}
    lines = []
    faces = {k: [] for k in range(len(KINDS))}
    for tri, kind in zip(tris, kinds):
        face = []
        for v in tri:
            key = tuple(round(float(c), 4) + 0.0 for c in verts[v])
            n = index.get(key)
            if n is None:
                n = index[key] = len(index) + 1
                lines.append("v %.4f %.4f %.4f\n" % key)
            face.append(n)
        if len(set(face)) == 3:
            faces[int(kind)].append("f %d %d %d\n" % tuple(face))
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.writelines(lines)
        for k, name in enumerate(KINDS):
            if faces[k]:
                f.write("g %s\n" % name)
                f.writelines(faces[k])
    return sum(len(v) for v in faces.values())


def geometry(verts, tris):
    """(unit normals, areas, centres) of the triangles."""
    a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    n = np.cross(b - a, c - a)
    length = np.linalg.norm(n, axis=1)
    unit = n / np.maximum(length, 1e-12)[:, None]
    return unit, length / 2.0, (a + b + c) / 3.0


def lean(normals):
    """Degrees each triangle's outward side leans away from straight up: 0 floor, 90 wall, 180 ceiling."""
    return np.degrees(np.arccos(np.clip(normals[:, 2], -1.0, 1.0)))


def classify(normals):
    """Each triangle's kind (an index into KINDS)."""
    deg = lean(normals)
    kinds = np.full(len(deg), WALL, dtype=np.int8)
    kinds[deg <= SLOPE_MAX_DEG] = SLOPE
    kinds[deg <= FLOOR_MAX_DEG] = FLOOR
    kinds[deg >= CEILING_MIN_DEG] = CEILING
    return kinds


# ---- the play space ---------------------------------------------------------

def _samples(a, b, c):
    """Points spread over a triangle, about CELL apart."""
    longest = max(np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c))
    k = max(1, int(math.ceil(longest / CELL)))
    out = []
    for i in range(k):
        for j in range(k - i):
            u, v = (i + 1.0 / 3.0) / k, (j + 1.0 / 3.0) / k
            out.append(a + (b - a) * u + (c - a) * v)
            if j < k - i - 1:
                u, v = (i + 2.0 / 3.0) / k, (j + 2.0 / 3.0) / k
                out.append(a + (b - a) * u + (c - a) * v)
    return out


def ground_levels(verts, tris, normals, areas):
    """The walkable ground as {(cell x, cell y): [height, ...]}, heights sorted, one per level.
    A level counts only where ground covers GROUND_COVER of its cell seen from above, so leaves,
    branches, rails and trim are not ground."""
    walk = np.nonzero(lean(normals) <= WALK_MAX_DEG)[0]
    found = {}
    for t in walk:
        a, b, c = verts[tris[t]]
        points = _samples(a, b, c)
        share = float(areas[t] * normals[t, 2]) / len(points)      # its area seen from above, split over its points
        for p in points:
            found.setdefault((int(math.floor(p[0] / CELL)), int(math.floor(p[1] / CELL))), []).append((float(p[2]), share))
    need = GROUND_COVER * CELL * CELL
    cells = {}
    for key, items in found.items():
        items.sort()
        levels = []
        for z, share in items:
            if levels and z - levels[-1][0] <= LEVEL:
                levels[-1][1] += share
            else:
                levels.append([z, share])
        solid = [z for z, cover in levels if cover >= need]
        if solid:
            cells[key] = solid
    return cells


def _under(cells, p, above=0.15, below=0.6):
    """The ground levels right under a point: [(cell, height)]."""
    ci, cj = int(math.floor(p[0] / CELL)), int(math.floor(p[1] / CELL))
    out = []
    for i in (ci - 1, ci, ci + 1):
        for j in (cj - 1, cj, cj + 1):
            for z in cells.get((i, j), ()):
                if p[2] - below <= z <= p[2] + above:
                    out.append(((i, j), z))
    return out


def grounded(cells, points):
    """How many of the points stand on walkable ground."""
    return sum(1 for p in points if _under(cells, p))


def walk(cells, starts):
    """Every ground level reachable on foot from the start points: a set of (cell, height)."""
    reach = int(math.ceil(GAP / CELL))
    seen = set()
    stack = []
    for p in starts:
        for node in _under(cells, p):
            if node not in seen:
                seen.add(node)
                stack.append(node)
    while stack:
        (ci, cj), z = stack.pop()
        for i in range(ci - reach, ci + reach + 1):
            for j in range(cj - reach, cj + reach + 1):
                for z2 in cells.get((i, j), ()):
                    if z - DROP <= z2 <= z + JUMP_UP:
                        node = ((i, j), z2)
                        if node not in seen:
                            seen.add(node)
                            stack.append(node)
    return seen


def play_box(reached, points, side=SIDE, below=BELOW, above=ABOVE):
    """(min, max) of the box around the walked ground and the placements, grown for the cut."""
    xs = [c[0] * CELL for c, _ in reached] + [(c[0] + 1) * CELL for c, _ in reached] + [p[0] for p in points]
    ys = [c[1] * CELL for c, _ in reached] + [(c[1] + 1) * CELL for c, _ in reached] + [p[1] for p in points]
    zs = [z for _, z in reached] + [p[2] for p in points]
    return ([min(xs) - side, min(ys) - side, min(zs) - below],
            [max(xs) + side, max(ys) + side, max(zs) + above])


def _clip(poly, axis, limit, keep_below):
    """A convex polygon cut by one side of the box (Sutherland-Hodgman)."""
    out = []
    for n, p in enumerate(poly):
        q = poly[(n + 1) % len(poly)]
        p_in = p[axis] <= limit if keep_below else p[axis] >= limit
        q_in = q[axis] <= limit if keep_below else q[axis] >= limit
        if p_in:
            out.append(p)
        if p_in != q_in:
            t = (limit - p[axis]) / (q[axis] - p[axis])
            cut = [p[k] + (q[k] - p[k]) * t for k in range(3)]
            cut[axis] = limit
            out.append(cut)
    return out


def cut_to_box(verts, tris, lo, hi):
    """The mesh inside the box: triangles wholly outside go, ones crossing a side are cut at it.
    (vertices, triangles): windings kept."""
    lo, hi = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)
    corners = verts[tris]                                   # m x 3 x 3
    t_lo, t_hi = corners.min(axis=1), corners.max(axis=1)
    apart = np.any((t_hi < lo) | (t_lo > hi), axis=1)
    whole = np.all((t_lo >= lo) & (t_hi <= hi), axis=1)
    out_v = [tuple(v) for v in verts]
    out_t = [tuple(t) for t in tris[whole]]
    for t in np.nonzero(~apart & ~whole)[0]:
        poly = [list(p) for p in corners[t]]
        for axis in range(3):
            poly = _clip(poly, axis, float(hi[axis]), True)
            if len(poly) < 3:
                break
            poly = _clip(poly, axis, float(lo[axis]), False)
            if len(poly) < 3:
                break
        if len(poly) < 3:
            continue
        base = len(out_v)
        out_v.extend(tuple(p) for p in poly)
        for k in range(1, len(poly) - 1):
            out_t.append((base, base + k, base + k + 1))
    v = np.array(out_v, dtype=float).reshape(-1, 3)
    t = np.array(out_t, dtype=np.int64).reshape(-1, 3)
    if len(t):
        _, areas, _ = geometry(v, t)
        t = t[areas > 1e-9]
    return v, t


# ---- flat patches -----------------------------------------------------------

def patches(verts, tris, normals, areas, centres, kinds):
    """Groups touching triangles of one kind that lie in one plane. Each patch is a dict; the
    second value gives every triangle's patch number."""
    welded = {}
    ids = np.empty(len(verts), dtype=np.int64)
    for n, v in enumerate(np.round(verts, WELD)):
        ids[n] = welded.setdefault((v[0] + 0.0, v[1] + 0.0, v[2] + 0.0), len(welded))
    w = ids[tris]
    edges = {}
    for t in range(len(tris)):
        a, b, c = int(w[t, 0]), int(w[t, 1]), int(w[t, 2])
        for e in ((a, b), (b, c), (c, a)):
            edges.setdefault((e[0], e[1]) if e[0] < e[1] else (e[1], e[0]), []).append(t)
    near = math.cos(math.radians(PATCH_ANGLE_DEG))
    owner = np.full(len(tris), -1, dtype=np.int64)
    out = []
    for seed in np.argsort(-areas, kind="stable"):          # biggest triangles first: steadier planes
        if owner[seed] != -1:
            continue
        number = len(out)
        normal, origin, kind = normals[seed], centres[seed], kinds[seed]
        owner[seed] = number
        members, stack = [seed], [seed]
        while stack:
            t = stack.pop()
            a, b, c = int(w[t, 0]), int(w[t, 1]), int(w[t, 2])
            for e in ((a, b), (b, c), (c, a)):
                for other in edges[(e[0], e[1]) if e[0] < e[1] else (e[1], e[0])]:
                    if (owner[other] == -1 and kinds[other] == kind
                            and float(normals[other] @ normal) >= near
                            and abs(float((centres[other] - origin) @ normal)) <= PATCH_OFFSET):
                        owner[other] = number
                        members.append(other)
                        stack.append(other)
        m = np.array(members)
        pts = verts[tris[m]].reshape(-1, 3)
        mean = (normals[m] * areas[m][:, None]).sum(axis=0)
        mean = mean / max(float(np.linalg.norm(mean)), 1e-12)
        tilt = math.degrees(math.acos(max(-1.0, min(1.0, float(mean[2])))))
        patch = {"kind": KINDS[int(kind)],
                 "area": round(float(areas[m].sum()), 3),
                 "triangles": len(members),
                 "normal": [round(float(c), 4) + 0.0 for c in mean],
                 "offset": round(float((centres[m] @ mean * areas[m]).sum() / max(float(areas[m].sum()), 1e-12)), 3),
                 "tilt": round(tilt, 1),
                 "min": [round(float(c), 3) for c in pts.min(axis=0)],
                 "max": [round(float(c), 3) for c in pts.max(axis=0)]}
        if kind == SLOPE:
            # the compass direction that goes uphill, degrees counter-clockwise from +x
            patch["uphill"] = round(math.degrees(math.atan2(-mean[1], -mean[0])) % 360.0, 1)
        out.append(patch)
    return out, owner


# ---- the command ------------------------------------------------------------

def analyse(folder, side=SIDE, below=BELOW, above=ABOVE):
    """The play space of a reference folder, worked out but not written anywhere: a dict with the
    cut mesh ("verts", "tris"), each triangle's "normals", "areas", "centres", "kinds" and whether
    it is "walked" ground, the flat "patches" and each triangle's patch ("owner"), and the rest
    build() reports."""
    try:
        with open(os.path.join(folder, "reference.json"), encoding="utf-8") as f:
            ref = json.load(f)
    except OSError:
        raise SurfaceError("no reference.json in %s (run `forge_printer reference <map>` first)" % folder)
    mesh = os.path.join(folder, ref["mesh"])
    if not os.path.isfile(mesh):
        raise SurfaceError("%s is missing" % mesh)
    verts, tris = load_obj(mesh)
    normals, areas, _ = geometry(verts, tris)
    spawns = [p["pos"] for p in ref.get("spawns", [])]
    points = [p["pos"] for group in ("spawns", "weapons", "objectives", "other") for p in ref.get(group, [])]
    if not spawns:
        raise SurfaceError("reference.json lists no spawns to find the play space from")
    cells = ground_levels(verts, tris, normals, areas)
    on_ground = grounded(cells, spawns)
    if on_ground * 2 < len(spawns):
        raise SurfaceError("only %d of %d spawns stand on ground in the mesh: the mesh and the placements "
                           "do not line up (axes or scale)" % (on_ground, len(spawns)))
    reached = walk(cells, spawns)
    lo, hi = play_box(reached, points, side, below, above)

    cut_v, cut_t = cut_to_box(verts, tris, lo, hi)
    if not len(cut_t):
        raise SurfaceError("nothing of the mesh is inside the play box")
    normals, areas2, centres = geometry(cut_v, cut_t)
    kinds = classify(normals)
    found, owner = patches(cut_v, cut_t, normals, areas2, centres, kinds)

    # which ground is the ground players walk on (a roof top or a branch is a floor too, but not that)
    ground = {}
    for cell, z in reached:
        ground.setdefault(cell, []).append(z)
    walked = np.zeros(len(cut_t), dtype=bool)
    for t in np.nonzero(kinds <= SLOPE)[0]:
        walked[t] = bool(_under(ground, centres[t], above=WALKED_NEAR, below=WALKED_NEAR))
    share = np.bincount(owner, weights=areas2 * walked, minlength=len(found))
    for number, patch in enumerate(found):
        if patch["kind"] in ("floor", "slope"):
            patch["walked"] = bool(share[number] * 2 >= patch["area"] and share[number] > 0)
    return {"ref": ref, "whole_triangles": int(len(tris)), "whole_area": float(areas.sum()),
            "verts": cut_v, "tris": cut_t, "normals": normals, "areas": areas2, "centres": centres,
            "kinds": kinds, "walked": walked, "patches": found, "owner": owner,
            "box": (lo, hi), "on_ground": on_ground, "spawns": len(spawns), "reached": reached}


def build(folder, side=SIDE, below=BELOW, above=ABOVE):
    """Writes <map>_play.obj and surfaces.json into the reference folder. Returns the surfaces dict."""
    a = analyse(folder, side, below, above)
    ref, cut_v, cut_t, kinds, walked, found = a["ref"], a["verts"], a["tris"], a["kinds"], a["walked"], a["patches"]
    areas2, reached, (lo, hi), on_ground = a["areas"], a["reached"], a["box"], a["on_ground"]

    name = ref["source"]["map"]
    play = name + "_play.obj"
    order = np.argsort(kinds, kind="stable")
    written = save_obj(os.path.join(folder, play), cut_v, cut_t[order], kinds[order])

    totals = {}
    for k, kind in enumerate(KINDS):
        mine = [p for p in found if p["kind"] == kind]
        listed = [p for p in mine if p["area"] >= PATCH_LISTED]
        totals[kind] = {"area": round(float(areas2[kinds == k].sum()), 2),
                        "walked_area": round(float(areas2[(kinds == k) & walked].sum()), 2),
                        "triangles": int((kinds == k).sum()),
                        "patches": len(mine),
                        "listed_patches": len(listed),
                        "listed_area": round(sum(p["area"] for p in listed), 2)}
    listed = sorted((p for p in found if p["area"] >= PATCH_LISTED),
                    key=lambda p: (-p["area"], p["kind"], p["min"], p["max"]))
    out = {"source": ref["source"],
           "mesh": play,
           "box": {"min": [round(c, 3) for c in lo], "max": [round(c, 3) for c in hi]},
           "cut": {"side": side, "below": below, "above": above},
           "rules": {"floor_max_deg": FLOOR_MAX_DEG, "slope_max_deg": SLOPE_MAX_DEG,
                     "ceiling_min_deg": CEILING_MIN_DEG, "patch_listed_area": PATCH_LISTED},
           "whole_mesh": {"triangles": a["whole_triangles"], "area": round(a["whole_area"], 2)},
           "play_mesh": {"triangles": written, "area": round(float(areas2.sum()), 2)},
           "spawns_on_ground": [on_ground, a["spawns"]],
           "walked_ground_cells": len({c for c, _ in reached}),
           "kinds": totals,
           "patches": listed}
    with open(os.path.join(folder, "surfaces.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    return out


def main(folder, side=SIDE, below=BELOW, above=ABOVE):
    try:
        s = build(folder, side, below, above)
    except SurfaceError as error:
        print("surfaces: %s" % error)
        return 1
    lo, hi = s["box"]["min"], s["box"]["max"]
    print("wrote %s and surfaces.json in %s" % (s["mesh"], folder))
    print("spawns on ground  %d of %d" % tuple(s["spawns_on_ground"]))
    print("play box          x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f  (size %.1f x %.1f x %.1f)" % (
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    print("kept              %d of %d triangles, area %.0f of %.0f" % (
        s["play_mesh"]["triangles"], s["whole_mesh"]["triangles"], s["play_mesh"]["area"], s["whole_mesh"]["area"]))
    print("kind      area  walked  triangles  patches  of %.2f u2 or more (their area)" % PATCH_LISTED)
    for kind in KINDS:
        k = s["kinds"][kind]
        print("%-8s %6.0f %7.0f %9d %8d %6d (%.0f)" % (kind, k["area"], k["walked_area"], k["triangles"], k["patches"],
                                                      k["listed_patches"], k["listed_area"]))
    print("largest patches:")
    for p in s["patches"][:8]:
        size = [p["max"][i] - p["min"][i] for i in range(3)]
        print("  %-7s %6.1f u2  tilt %5.1f  box %.1f x %.1f x %.1f at z %.2f..%.2f%s" % (
            p["kind"], p["area"], p["tilt"], size[0], size[1], size[2], p["min"][2], p["max"][2],
            "  walked" if p.get("walked") else ""))
    return 0
