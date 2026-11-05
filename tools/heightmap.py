"""Build a top-down height map of a Halo CE level from `tool.exe export-structure-mesh-obj`
output, and render it with the map's objects for laying out callout zones.

OBJ axes from the CE kit are (X, Y, Z) = (halo x, halo z, -halo y).

usage: python -I heightmap.py <bsp.obj> <objects.json> <out_dir> [cell=0.25] [zones.json]
writes heightmap.npz (top and lowest surface z per cell; floors = up to MAX_FLOORS walkable levels
per cell, normal z >= FLOOR_NZ, e.g. a doorway, the roof above it, a catwalk above that; NaN = none;
walls = per cell, a 128-bin bitmask (WALL_BIN high, from wall_z0) of the heights steep faces pass
through, so thin walls the top-down layers miss still block) and topdown.png
"""
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def load_obj(path):
    v, f = [], []
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            X, Y, Z = map(float, p[1:4])
            v.append((X, -Z, Y))
        elif p[0] == "f":
            f.append([int(x.split("/")[0]) - 1 for x in p[1:4]])
    return np.array(v), np.array(f)


FLOOR_NZ = 0.7   # walkable: slopes up to about 45 degrees (the base ramps are 32)
LAYER_GAP = 1.0  # a walkable surface this far above another is a separate floor level
MAX_FLOORS = 4   # floor levels kept per cell (Prisoner and Derelict stack three)
WALL_BIN = 0.25  # wall bitmask height bins from wall_z0
WALL_WORDS = 4   # 4 x 64 bins = 64 units of height
MARGIN = 40.0    # the grid covers the play area (spawns, flags, items, vehicles) plus this


def play_area(v, objs):
    """Grid bounds and the wall range start from where players can be, not the whole mesh (Death
    Island's ocean plane is 2700 units across; Boarding Action's mesh goes 70 units under the ships)."""
    pts = [o["pos"] for key in ("netgame_flags", "equipment", "vehicles", "spawns") for o in objs.get(key, [])]
    if not pts:
        return None, float(np.floor(v[:, 2].min())) - 1.0
    p = np.array(pts)
    x0, y0 = max(v[:, 0].min(), p[:, 0].min() - MARGIN), max(v[:, 1].min(), p[:, 1].min() - MARGIN)
    x1, y1 = min(v[:, 0].max(), p[:, 0].max() + MARGIN), min(v[:, 1].max(), p[:, 1].max() + MARGIN)
    return (x0, y0, x1, y1), float(np.floor(p[:, 2].min())) - 16.0


def rasterize_walls(v, f, cell, x0, y0, h, w, z0):
    """Sample every steep face densely in 3D (just inside its edges, so a face starting at 1.5
    does not leak into the bin below) and set the height bit of each sample's cell."""
    walls = np.zeros((h, w, WALL_WORDS), np.uint64)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    steep = np.abs(n[:, 2]) < FLOOR_NZ * np.linalg.norm(n, axis=1)
    for a, b, c in tri[steep]:
        k = int(max(np.linalg.norm(b - a), np.linalg.norm(c - a), np.linalg.norm(c - b)) / (cell * 0.4)) + 2
        u, t = np.meshgrid(np.linspace(0.01, 0.98, k), np.linspace(0.01, 0.98, k))
        keep = u + t <= 0.99
        pts = a + np.outer(u[keep], b - a) + np.outer(t[keep], c - a)
        j = ((pts[:, 1] - y0) / cell).astype(int)
        i = ((pts[:, 0] - x0) / cell).astype(int)
        bit = np.floor((pts[:, 2] - z0) / WALL_BIN).astype(int)
        ok = (j >= 0) & (j < h) & (i >= 0) & (i < w) & (bit >= 0) & (bit < 64 * WALL_WORDS)   # out of range: ignored
        np.bitwise_or.at(walls, (j[ok], i[ok], bit[ok] >> 6),
                         np.left_shift(np.uint64(1), (bit[ok] & 63).astype(np.uint64)))
    return walls


def rasterize(v, f, cell, bounds=None, floor_min=-np.inf):
    """floor_min: walkable surfaces lower than this are no floors (the pit under Halo 2's Lockout
    would take one of the MAX_FLOORS levels of every cell)."""
    x0, y0, x1, y1 = bounds if bounds else (v[:, 0].min(), v[:, 1].min(), v[:, 0].max(), v[:, 1].max())
    w = int(np.ceil((x1 - x0) / cell)) + 1
    h = int(np.ceil((y1 - y0) / cell)) + 1
    top = np.full((h, w), -np.inf)
    low = np.full((h, w), np.inf)
    floor_cells, floor_z = [], []
    for tri in v[f]:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue   # vertical wall seen from above
        i0, i1 = int(np.floor((min(ax, bx, cx) - x0) / cell)), int((max(ax, bx, cx) - x0) / cell) + 1
        j0, j1 = int(np.floor((min(ay, by, cy) - y0) / cell)), int((max(ay, by, cy) - y0) / cell) + 1
        if i1 < 0 or j1 < 0 or i0 >= w or j0 >= h:
            continue   # outside the play area
        i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1, w - 1), min(j1, h - 1)
        xs = x0 + (np.arange(i0, i1 + 1) + 0.5) * cell
        ys = y0 + (np.arange(j0, j1 + 1) + 0.5) * cell
        X, Y = np.meshgrid(xs, ys)
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        l3 = 1 - l1 - l2
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        z = l1 * az + l2 * bz + l3 * cz
        sub = top[j0:j1 + 1, i0:i1 + 1]
        hh, ww = sub.shape
        zz = np.where(inside, z, -np.inf)[:hh, :ww]
        np.maximum(sub, zz, out=sub)
        sub_lo = low[j0:j1 + 1, i0:i1 + 1]
        np.minimum(sub_lo, np.where(inside, z, np.inf)[:hh, :ww], out=sub_lo)
        n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        if n[2] >= FLOOR_NZ * np.linalg.norm(n) and max(az, bz, cz) >= floor_min:
            jj, ii = np.nonzero(inside[:hh, :ww])
            floor_cells.append((jj + j0) * w + (ii + i0))
            floor_z.append(z[:hh, :ww][jj, ii])
    for a in (top, low):
        a[np.isinf(a)] = np.nan
    floors = stack_floors(np.concatenate(floor_cells), np.concatenate(floor_z), h, w)
    return top, low, floors, x0, y0


def stack_floors(cells, zs, h, w):
    """Walkable floor levels per cell, lowest first: a surface starts a new level when it is at
    least LAYER_GAP above the previous level's top (a doorway, the roof over it, a catwalk above
    that). Returns (MAX_FLOORS, h, w), NaN where a cell has fewer levels."""
    out = np.full((MAX_FLOORS, h * w), np.nan)
    order = np.lexsort((zs, cells))
    cells, zs = cells[order], zs[order]
    start = np.r_[True, cells[1:] != cells[:-1]]
    level = np.zeros(len(zs), int)
    gap = np.r_[False, np.diff(zs) >= LAYER_GAP] & ~start
    # level index within each cell = number of gaps since the cell's first surface
    grp = np.cumsum(start) - 1
    cum = np.cumsum(gap)
    level = cum - cum[np.nonzero(start)[0]][grp]
    keep = level < MAX_FLOORS
    # a level's height = its highest surface (several close triangles: the walkable top)
    idx = level[keep] * (h * w) + cells[keep]
    flat = out.reshape(-1)
    np.fmax.at(flat, idx, zs[keep])
    return out.reshape(MAX_FLOORS, h, w)


def render(top, x0, y0, cell, objs, zones, out_png, scale=2):
    h, w = top.shape
    z = np.nan_to_num(top, nan=np.nanmax(top))
    gy, gx = np.gradient(z)
    shade = np.clip(0.85 + (gx - gy) * 0.8, 0.45, 1.15)
    # height bands: canyon floor greens, low hills yellow, ridges orange, cliffs grey
    stops = [(-1, (40, 90, 50)), (0.5, (70, 130, 70)), (2.0, (150, 170, 80)), (4.0, (200, 170, 80)),
             (6.0, (200, 120, 60)), (9.0, (150, 110, 100)), (14.0, (170, 170, 170)), (27.0, (235, 235, 235))]
    zs = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], dtype=float)
    rgb = np.stack([np.interp(z, zs, cols[:, c]) for c in range(3)], -1) * shade[..., None]
    band = np.floor(z / 1.0)   # contour line every 1 world unit of height
    edge = (np.diff(band, axis=0, prepend=band[:1]) != 0) | (np.diff(band, axis=1, prepend=band[:, :1]) != 0)
    rgb[edge] *= 0.55
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)[::-1]          # north (larger y) at the top
    edge = edge[::-1]
    img = Image.fromarray(rgb).resize((w * scale, h * scale), Image.NEAREST)
    d = ImageDraw.Draw(img, "RGBA")
    try:
        font = ImageFont.truetype("arial.ttf", 13)
        big = ImageFont.truetype("arialbd.ttf", 15)
    except OSError:
        font = big = ImageFont.load_default()
    P = lambda x, y: ((x - x0) / cell * scale, (h - (y - y0) / cell) * scale)
    for gxv in range(0, 140, 10):   # grid every 10 world units
        a, b = P(gxv, y0), P(gxv, y0 + h * cell)
        d.line([a, b], fill=(255, 255, 255, 40))
        d.text((a[0] + 2, img.height - 16), str(gxv), fill=(255, 255, 255, 200), font=font)
    for gyv in range(-200, -30, 10):
        a, b = P(x0, gyv), P(x0 + w * cell, gyv)
        d.line([a, b], fill=(255, 255, 255, 40))
        d.text((2, a[1] - 14), str(gyv), fill=(255, 255, 255, 200), font=font)
    for zname, zd in (zones or {}).items():
        poly = [P(x, y) for x, y in zd["poly"]]
        col = {"red": (230, 60, 60), "blue": (60, 110, 240)}.get(zd.get("side"), (240, 220, 80))
        d.polygon(poly, outline=col + (255,), fill=col + (38,))
        cxp = sum(p[0] for p in poly) / len(poly)
        cyp = sum(p[1] for p in poly) / len(poly)
        d.text((cxp - 4 * len(zname), cyp - 8), zname, fill=(255, 255, 255, 255), font=big,
               stroke_width=2, stroke_fill=(0, 0, 0, 255))
    mark = {"ctf - flag": ((255, 255, 255), "FLAG"), "teleport from": ((200, 80, 255), "TELE IN"),
            "teleport to": ((200, 80, 255), "TELE OUT")}
    for fl in objs["netgame_flags"]:
        if fl["type"] in mark:
            col, lab = mark[fl["type"]]
            x, y = P(*fl["pos"][:2])
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=col + (255,), outline=(0, 0, 0, 255))
            d.text((x + 8, y - 7), f"{lab} {fl['id']}", fill=col + (255,), font=font, stroke_width=1, stroke_fill=(0, 0, 0, 255))
    hills = {}
    for fl in objs["netgame_flags"]:   # KOTH hill markers outline the map's natural hills
        if fl["type"] == "hill - flag":
            hills.setdefault(fl["id"], []).append(fl["pos"])
    for hid, pts in hills.items():
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        zz = sum(p[2] for p in pts) / len(pts)
        px, py = P(x, y)
        d.text((px - 10, py - 7), f"H{hid} z{zz:.1f}", fill=(255, 255, 255, 230), font=font, stroke_width=2, stroke_fill=(60, 0, 60, 255))
    for e in objs["equipment"]:
        name = e["item"].split("\\")[-1]
        if "grenade" in name:
            continue
        x, y = P(*e["pos"][:2])
        d.rectangle([x - 4, y - 4, x + 4, y + 4], fill=(255, 200, 0, 255), outline=(0, 0, 0, 255))
        d.text((x + 6, y + 2), name, fill=(255, 230, 120, 255), font=font, stroke_width=1, stroke_fill=(0, 0, 0, 255))
    for s in objs["scenery"]:
        n = s["scenery"].split("\\")[-1]
        if "boulder" in n or "rock" in n or "tree" in n:
            x, y = P(*s["pos"][:2])
            d.polygon([(x, y - 5), (x + 5, y + 4), (x - 5, y + 4)], fill=(150, 150, 150, 255), outline=(0, 0, 0, 255))
    for sp in objs["spawns"]:
        x, y = P(*sp["pos"][:2])
        col = (255, 90, 90) if sp["team"] == 0 else (90, 140, 255)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=col + (200,))
    img.save(out_png)
    return img.size


def main():
    obj, objs_json, out = sys.argv[1:4]
    cell = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
    zones = json.load(open(sys.argv[5]))["zones"] if len(sys.argv) > 5 else None
    v, f = load_obj(obj)
    objs = json.load(open(objs_json))
    bounds, wall_z0 = play_area(v, objs)
    top, low, floors, x0, y0 = rasterize(v, f, cell, bounds, wall_z0)
    walls = rasterize_walls(v, f, cell, x0, y0, *top.shape, wall_z0)
    np.savez_compressed(f"{out}/heightmap.npz", top=top, low=low, floors=floors,
                        walls=walls, wall_z0=wall_z0, wall_bin=WALL_BIN, x0=x0, y0=y0, cell=cell)
    scale = max(2, int(1200 / max(top.shape)))       # small maps get a bigger image
    size = render(top, x0, y0, cell, objs, zones, f"{out}/topdown.png", scale)
    print("grid", top.shape, "origin", round(x0, 2), round(y0, 2), "z", round(float(np.nanmin(top)), 2),
          round(float(np.nanmax(top)), 2), "image", size)


if __name__ == "__main__":
    main()
