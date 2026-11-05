"""Roofless top-down views of a map: the level mesh drawn from straight above with everything over a cut height left out,
one picture per floor level, so every floor shows (under roofs, bridges and the floor above). Floors are shaded by
height and light, walls are dark, the painted nav (tools/paint.py) goes on top.

Cuts: one unit apart from CUT_HEAD over the lowest walkable floor (heightmap.npz) to the top, and a last view with
everything; the paint page steps through them (levels_of() groups floors into levels, but floors joined by ramps never
split: Rat's Nest's -9.7 to -6.6 read as one).

Writes maps/<map>/roofless/level_<k>.png and maps/<map>/roofless.json: {x0, y0, x1, y1, px, levels: [{z, cut, png}]}
(pixel (i, j) = world (x0 + i / px, y1 - j / px)).

usage: python -I roofless.py <map> [--px 12]        python -I roofless.py --selftest
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
from heightmap import FLOOR_NZ, load_obj, play_area  # noqa: E402

LEVEL_GAP = 1.2       # floors this far apart in height are different levels
MIN_SHARE = 0.04      # a level holds at least this share of the walkable cells
CUT_ABOVE = 2.5       # a level's cut: at most this over it (and 0.3 under the next level)
CUT_HEAD = 1.6        # a cut this far over the floor it shows (a player stands about 0.7 tall: rooms and doors keep)
LIGHT = np.array([-0.45, 0.35, 0.82])


def levels_of(lz, walk):
    """[(level height, cut height)] from the walkable floor heights (heightmap layers)."""
    zs = np.sort(lz[walk & np.isfinite(lz)].ravel())
    if not len(zs):
        return []
    groups, start = [], 0
    for k in range(1, len(zs) + 1):
        if k == len(zs) or zs[k] - zs[k - 1] > LEVEL_GAP:
            groups.append(zs[start:k])
            start = k
    keep = [float(np.median(g)) for g in groups if len(g) >= MIN_SHARE * len(zs)]
    out = []
    for i, z in enumerate(keep):
        nxt = keep[i + 1] if i + 1 < len(keep) else None
        out.append((round(z, 2), round(min(z + CUT_ABOVE, nxt - 0.3), 2) if nxt is not None else None))
    return out


# heights coloured low to high (blue, teal, green, yellow, orange, red, pale): a unit of height shows as a colour step
RAMP = np.array([[35, 60, 135], [35, 120, 165], [55, 150, 85], [185, 185, 65], [220, 135, 50], [195, 60, 60],
                 [235, 215, 235]], float)
CONTOUR = 1.0         # a thin dark line every this many units of height
LEDGE = 0.6           # a height step this big between neighbouring pixels is a ledge: outlined white
LOCAL = 6.0           # a cut's view colours the floors this far under the cut with the whole ramp (contours every half)


def ramp(a):
    """RGB for a 0..1 height share (array)."""
    a = np.clip(a, 0.0, 1.0) * (len(RAMP) - 1)
    k = np.minimum(a.astype(int), len(RAMP) - 2)
    t = (a - k)[..., None]
    return RAMP[k] * (1 - t) + RAMP[k + 1] * t


def draw(v, f, box, cut, px, zlo, zhi, zs=None):
    """The mesh from above, faces over `cut` left out (a wall keeps its part under the cut, a floor or roof only if it
    lies wholly under it); downward faces (ceilings) never drawn. Painter's order by height. Floors coloured by height
    (RAMP) and lit, walls the same colour darker, a contour line every CONTOUR units and ledges (drops of LEDGE+)
    outlined, so heights and the edges people jump from read at a glance."""
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = box
    W, H = int((x1 - x0) * px) + 1, int((y1 - y0) * px) + 1
    tid = Image.new("I", (W, H), 0)                      # which face is on top at each pixel (index + 1)
    dt = ImageDraw.Draw(tid)
    P = v[f]                                                 # (n, 3, 3)
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    ln = np.linalg.norm(n, axis=1) + 1e-9
    nz = n[:, 2] / ln
    zmin, zmax = P[:, :, 2].min(1), P[:, :, 2].max(1)
    inside = (P[:, :, 0].max(1) >= x0) & (P[:, :, 0].min(1) <= x1) & (P[:, :, 1].max(1) >= y0) & (P[:, :, 1].min(1) <= y1)
    up, steep = nz >= FLOOR_NZ * 0.5, np.abs(nz) < FLOOR_NZ * 0.5
    keep = inside & ((up & (zmax <= cut + 0.05)) | (steep & (zmin <= cut))) if cut is not None else inside & (up | steep)
    idx = np.nonzero(keep)[0]
    top = np.minimum(zmax[idx], cut) if cut is not None else zmax[idx]
    idx = idx[np.argsort(top, kind="stable")]
    for t in idx:
        pts = [((q[0] - x0) * px, (y1 - q[1]) * px) for q in P[t]]
        dt.polygon(pts, fill=int(t) + 1, outline=int(t) + 1)
    ids = np.asarray(tid, dtype=np.int64) - 1
    empty = ids < 0
    k = np.where(empty, 0, ids)
    # each pixel's exact height on its face's plane (a ramp reads as a ramp, not a stair of flat triangles)
    X = x0 + (np.arange(W)[None, :] + 0.5) / px
    Y = y1 - (np.arange(H)[:, None] + 0.5) / px
    nn = n / ln[:, None]
    a0 = P[:, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        zp = a0[k, 2] - (nn[k, 0] * (X - a0[k, 0]) + nn[k, 1] * (Y - a0[k, 1])) / nn[k, 2]
    wall = ~empty & steep[k]
    zp = np.where(wall | ~np.isfinite(zp), np.minimum(zmax[k], cut) if cut is not None else zmax[k], zp)
    zp = np.clip(zp, zmin[k], zmax[k])
    h = np.where(empty, np.nan, zp)
    l = np.where(wall, -1.0, np.clip(nn[k] @ LIGHT, 0.15, 1.0))
    hz = np.where(empty, zlo, h)
    # colour by the share of walkable floor under that height (zs: the floors' heights sorted), so the heights most of
    # the map's floor lies at get most of the colours (Spire: the island's -63..-54 was one teal under a 50 u scale)
    if cut is None:
        lin = (hz - zlo) / max(1e-6, zhi - zlo)
        share = 0.65 * np.searchsorted(zs, hz) / len(zs) + 0.35 * lin if zs is not None and len(zs) else lin   # (+ some
        # straight height: the few units of a high storey still differ)
        dim, step_h = 1.0, CONTOUR
    else:
        # a cut: the LOCAL units under it get the whole ramp (Spire's top: -24.1, -23.4 and -22.9 were one red), what
        # lies deeper, seen through a gap, is dimmed
        share = (hz - (cut - LOCAL)) / LOCAL
        dim, step_h = np.where(share < 0, 0.45, 1.0), CONTOUR / 2
    rgb = ramp(share) * (np.where(wall, 0.42, 0.5 + 0.5 * np.clip(l, 0, 1)) * dim)[..., None]
    band = np.floor(hz / step_h)
    edge = np.zeros_like(empty)
    ledge = np.zeros_like(empty)
    for dy, dx in ((0, 1), (1, 0)):
        a = (slice(0, H - dy), slice(0, W - dx))
        b = (slice(dy, H), slice(dx, W))
        diff = hz[b] - hz[a]
        both = ~empty[a] & ~empty[b] & ~wall[a] & ~wall[b]
        step = both & (np.abs(diff) >= LEDGE)
        cont = both & (band[a] != band[b]) & ~step
        edge[a] |= cont
        hi_a = step & (diff < 0)                      # the higher side of the step gets the outline
        hi_b = step & (diff > 0)
        ledge[a] |= hi_a
        ledge[b] |= hi_b
    rgb[edge] *= 0.6
    rgb[ledge] = rgb[ledge] * 0.25 + np.array([245, 245, 245]) * 0.75
    rgb[empty] = (18, 20, 24)
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def build(name, px=12):
    d = os.path.join(ROOT, "maps", name)
    src = os.path.join(d, "source", "bsp.obj")
    if not os.path.exists(src):
        sys.exit(f"{name}: no level mesh ({src})")
    v, f = load_obj(src)
    objs = json.load(open(os.path.join(d, "objects.json")))
    box, _ = play_area(v, objs)
    hm = np.load(os.path.join(d, "heightmap.npz"))
    lz = hm["floors"]                                # (levels, rows, cols) walkable floor heights, NaN: none
    walk = np.isfinite(lz)
    # cuts one unit apart from just over the lowest floor to the top, then everything: floors joined by ramps never
    # split into levels (Rat's Nest's -9.7 to -6.6 read as one), so the page steps through cut heights instead
    zs = lz[walk]
    lo, hi = float(np.percentile(zs, 1)), float(np.percentile(zs, 99))
    lv = [(round(c - CUT_HEAD, 2), round(c, 2)) for c in np.arange(lo + CUT_HEAD, hi + CUT_HEAD + 1e-6, 1.0)]
    lv.append((round(hi, 2), None))
    zlo, zhi = lo - 1.0, hi + 3.0
    out = os.path.join(d, "roofless")
    os.makedirs(out, exist_ok=True)
    levels = []
    for k, (z, cut) in enumerate(lv):
        img = draw(v, f, box, cut, px, zlo, zhi, np.sort(zs))
        png = f"level_{k}.png"
        img.save(os.path.join(out, png))
        levels.append(dict(z=z, cut=cut, png=png))
    meta = dict(map=name, x0=round(box[0], 2), y0=round(box[1], 2), x1=round(box[2], 2), y1=round(box[3], 2),
                px=px, levels=levels)
    json.dump(meta, open(os.path.join(d, "roofless.json"), "w"), indent=1)
    print(f"{name}: {len(levels)} levels {[l['z'] for l in levels]} -> maps/{name}/roofless/")
    return meta


def selftest():
    """Two floors 3 u apart: two levels, the lower one's cut under the upper floor; a box room's roof hides its floor
    in the top level and not in the lower one."""
    lz = np.full((2, 4, 4), np.nan)
    lz[0], lz[1] = 0.0, 3.0
    lv = levels_of(lz, np.isfinite(lz))
    assert [z for z, _ in lv] == [0.0, 3.0] and lv[0][1] == 2.5 and lv[1][1] is None, lv
    # a floor square at z 0 under a roof square at z 2 (both up-facing), 10 x 10
    v = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0], [0, 0, 2], [10, 0, 2], [10, 10, 2], [0, 10, 2.0]])
    f = np.array([[0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7]])
    lo = np.asarray(draw(v, f, (0, 0, 10, 10), 1.5, 4, -1, 3))
    hi = np.asarray(draw(v, f, (0, 0, 10, 10), None, 4, -1, 3))
    roof = np.asarray(draw(v, f[2:], (0, 0, 10, 10), None, 4, -1, 3))
    floor = np.asarray(draw(v, f[:2], (0, 0, 10, 10), 1.5, 4, -1, 3))
    floor_top = np.asarray(draw(v, f[:2], (0, 0, 10, 10), None, 4, -1, 3))
    # (colours are a ramp now, not lighter for higher: the views must match the roof alone / the floor alone, each on
    # the same scale: a cut colours its own 6 units, the full view the whole map)
    assert (hi[20, 20] == roof[20, 20]).all() and (hi[20, 20] != floor_top[20, 20]).any(), "the roof did not hide the floor"
    assert (lo[20, 20] == floor[20, 20]).all(), "the cut under the roof did not show the floor"
    # a step 1 u up across the middle (x 5): its upper edge is outlined near-white, the floors either side are not
    v2 = np.array([[0, 0, 0], [5, 0, 0], [5, 10, 0], [0, 10, 0], [5, 0, 1], [10, 0, 1], [10, 10, 1], [5, 10, 1.0]])
    st = np.asarray(draw(v2, f, (0, 0, 10, 10), None, 4, -1, 3)).astype(int)
    col = st[20, 18:23]
    assert col.min(axis=1).max() > 180 and st[20, 8].min() < 180 and st[20, 32].min() < 180, col
    print("roofless OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        px = int(sys.argv[sys.argv.index("--px") + 1]) if "--px" in sys.argv else 12
        for name in [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]:
            build(name, px)
