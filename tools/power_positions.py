"""Power positions per map (docs/bot-brain/01 section 7, "how the bot recognizes a power position on
any map"): every reachable spot scored by height over its surroundings, how much of the map's floor it
sees (floor people walked counting for more: traffic), cover beside it (a wall to duck behind), an escape (a spot within 3 units that most of what it
sees cannot see) and power items near it. The best spread-out spots go to maps/<map>/positions.json;
the director's Slayer roles hold and rotate between them (brain/director.py slayer_slots).

usage: python -I power_positions.py [maps...] [--top 8] [--spacing 9]   (default: every map)
"""
import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)

from brain.core import Vec  # noqa: E402
from brain.maps import get_map, terrain  # noqa: E402

SAMPLES = 90          # floor points each candidate tries to see
SIGHT = 45.0          # beyond this a spot does not count as seen (pistol / BR range)
MAX_CAND = 2500


def floor_nodes(T):
    l, j, i = np.nonzero(T.lwalk & T.reach)
    return l, j, i


PIECE = 0.25          # a spot on a Forge layout's own pieces (Terrain.piece): its towers, rooms and platforms are what
                      # it was built around


def traffic(m, pts):
    """Map brain MAP-06 ("sightlines onto high-traffic nodes"): a weight per floor point (x, y, z) by where people
    walked, from the LiDAR recorder's floor cells of kind 1 (tools/lidar.py KIND_HUMAN; maps/<map>/lidar.json, a
    built-in map's variant the base's too): 1 + the square root of the samples in its 1 u cell within 1 u of its
    height (a man standing still a minute is not traffic). None where no person walked the map (39 of 123 maps have
    some)."""
    from brain.maps import data_names
    cells = {}
    for nm in data_names(m):
        f = os.path.join(ROOT, "maps", nm, "lidar.json")
        for w in (json.load(open(f)).get("walk", []) if os.path.exists(f) else ()):
            if len(w) == 5 and w[3] == 1:
                k = (round(w[0] * 0.25), round(w[1] * 0.25), round(w[2] * 0.1))
                cells[k] = cells.get(k, 0) + w[4]
    if not cells:
        return None
    return [1.0 + math.sqrt(sum(cells.get((round(x), round(y), round(z) + dz), 0) for dz in (-1, 0, 1)))
            for x, y, z in pts]


def score_map(name, top=8, spacing=9.0, rng=None):
    m = get_map(name)
    return positions(m, terrain(m), top, spacing, rng)


def positions(m, T, top=8, spacing=9.0, rng=None, cand_max=MAX_CAND, samples=SAMPLES):
    """The power positions of map m on its terrain T (a map variant's own: tools/variant_strategy.py)."""
    rng = rng or random.Random(1)
    l, j, i = floor_nodes(T)
    if len(l) == 0:
        return []
    k = max(1, len(l) // 40000)
    nodes = list(zip(l[::k].tolist(), j[::k].tolist(), i[::k].tolist()))
    pts = np.array([[T._center(a, b, c).x, T._center(a, b, c).y, T.lz[a, b, c]] for a, b, c in nodes])
    step = max(1, len(pts) // cand_max)
    cand = pts[::step]
    piece = np.array([bool(T.piece[n]) for n in nodes[::step]]) if getattr(T, "piece", None) is not None \
        else np.zeros(len(cand), bool)
    w = traffic(m, pts.tolist())                  # floor people walk counts for more of what a spot sees
    sample = pts[rng.choices(range(len(pts)), weights=w, k=samples) if w else
                 rng.sample(range(len(pts)), min(samples, len(pts)))]
    vis = np.zeros(len(cand))
    for k, c in enumerate(cand):
        a = Vec(*c)
        n = 0
        for q in sample:
            if math.hypot(q[0] - c[0], q[1] - c[1]) < SIGHT and T.los(a, Vec(*q)):
                n += 1
        vis[k] = n
    # height over the floor around it (15 units)
    height = np.zeros(len(cand))
    for k, c in enumerate(cand):
        near = pts[(np.abs(pts[:, 0] - c[0]) < 15) & (np.abs(pts[:, 1] - c[1]) < 15)]
        height[k] = c[2] - np.median(near[:, 2]) if len(near) else 0.0
    items = [it["pos"] for it in m["items"] if it.get("value", 0) >= 0.7]
    item = np.array([1.0 if any(math.hypot(p.x - c[0], p.y - c[1]) < 15 for p in items) else 0.0 for c in cand])
    norm = lambda v: (v - v.min()) / (v.max() - v.min() + 1e-9)
    score = 0.5 * norm(vis) + 0.3 * norm(np.clip(height, -2, 8)) + 0.2 * item + PIECE * piece
    order = np.argsort(-score)
    chosen = []
    for k in order[:400]:
        c = cand[k]
        if any(math.hypot(c[0] - o[0], c[1] - o[1]) < spacing for o, *_ in chosen):
            continue
        # escape / duck spot: a floor point within 3 units that sees less than half of what this sees
        a = Vec(*c)
        seen = [q for q in sample if math.hypot(q[0] - c[0], q[1] - c[1]) < SIGHT and T.los(a, Vec(*q))]
        duck = False
        for q in pts[(np.abs(pts[:, 0] - c[0]) < 3) & (np.abs(pts[:, 1] - c[1]) < 3) & (np.abs(pts[:, 2] - c[2]) < 1.5)][::3]:
            b = Vec(*q)
            if sum(T.los(b, Vec(*s)) for s in seen) < 0.5 * len(seen):
                duck = True
                break
        chosen.append((c, float(score[k]) + (0.1 if duck else 0.0), int(vis[k]), round(float(height[k]), 1), duck))
        if len(chosen) >= top:
            break
    chosen.sort(key=lambda x: -x[1])
    return [dict(pos=[round(float(v), 2) for v in c], score=round(s, 3), sees=v, height=h, duck=d)
            for c, s, v, h, d in chosen]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("maps", nargs="*")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--spacing", type=float, default=9.0)
    o = ap.parse_args()
    names = o.maps or sorted(d for d in os.listdir(os.path.join(ROOT, "maps"))
                             if os.path.exists(os.path.join(ROOT, "maps", d, "heightmap.npz")))
    for name in names:
        t0 = time.time()
        try:
            out = score_map(name, o.top, o.spacing)
        except Exception as e:                       # a map the nav cannot load: skip, say so
            print(f"{name}: failed ({type(e).__name__}: {e})", flush=True)
            continue
        json.dump(out, open(os.path.join(ROOT, "maps", name, "positions.json"), "w"), indent=1)
        print(f"{name}: {len(out)} positions in {time.time() - t0:.0f} s; best {out[0] if out else None}", flush=True)


if __name__ == "__main__":
    main()
