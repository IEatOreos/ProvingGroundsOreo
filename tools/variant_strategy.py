"""A Forge map variant's own strategy files (the player, his Forge World layout: "It didnt seem like the bots were
using the building structures at all"). The bots' goals came from Forge World's own callouts and power positions, the
empty canvas's: its "mid" at 1, 3, 0 and the blue holds at -58, -205, 300 u from the layout; 84% of their goal points on
the level, 2% on the layout's pieces, and they spent 4-20% of their time on the pieces to the player's 25%
(logs/tmp/structure_use.py). Written into the variant's folder (brain/variants.py), which brain/maps.py load_map prefers:
  positions.json  power positions on the variant's own nav (tools/power_positions.py: spots on its pieces preferred)
  callouts.json   zones named after its structures (pieces within LINK of each other: the tower, the room, the bunker
                  ...) and three areas across it; its mid point; holds and lanes (its power positions, for both teams)
Made when a layout is first seen and again when it changes (variant.json "strategy_of": its objects' hash).

usage: python -I variant_strategy.py <map variant> [...]      (e.g. reach_forge_halo/variants/v2ba2727c)
"""
import collections
import hashlib
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from brain import forge, maps, variants  # noqa: E402
from brain.callouts import read_json  # noqa: E402
from brain.core import Vec  # noqa: E402
import power_positions  # noqa: E402

CELL = 12.0          # a zone per square this size holding structure, named after it
WORDS = (("tower", "Tower"), ("room", "Room"), ("bunker", "Bunker"), ("pyramid", "Pyramid"), ("bridge", "Bridge"),
         ("catwalk", "Catwalk"), ("ramp", "Ramps"), ("tunnel", "Tunnel"), ("dish", "Dish"), ("base", "Base"),
         ("rock", "Rocks"), ("wall", "Walls"), ("door", "Door"), ("plat", "Platform"), ("column", "Pillars"),
         ("crate", "Crates"), ("barrier", "Barricade"), ("sandbag", "Sandbags"))


def layout_hash(data):
    return hashlib.sha1(json.dumps(data.get("objects", [])).encode()).hexdigest()[:12]


def stale(name):
    """Does map variant `name` need its strategy files made (none yet, or its layout changed since)?"""
    data = variants.info(name)
    if data is None:
        return False
    have = all(os.path.exists(os.path.join(variants.ROOT, name, f)) for f in ("callouts.json", "positions.json"))
    return not have or data.get("strategy_of") != layout_hash(data)


def structures(pieces):
    """Building pieces (those with faces: brain/forge.py block; not game-type objects, mp_*) by CELL squares: [(the
    square's corner, its word)], the word the most telling of its pieces in WORDS order (a bunker over platforms).
    (Grouped by distance the player's layout chained into one structure: its pieces touch.)"""
    groups = collections.defaultdict(list)
    for n, p, a in pieces:
        if not n.startswith("mp_") and len(forge.block(n, p, a) or ()) > 5:
            groups[(math.floor(p[0] / CELL) * CELL, math.floor(p[1] / CELL) * CELL)].append(n)
    return [(c, next((w for key, w in WORDS if any(key in n for n in names)), "Cover")) for c, names in sorted(groups.items())]


def compass(c, centre):
    a = math.degrees(math.atan2(c[1] - centre[1], c[0] - centre[0]))
    return ("East", "North-east", "North", "North-west", "West", "South-west", "South", "South-east")[round(a / 45.0) % 8]


def build(name):
    """Make the strategy files of map variant `name` (its nav built fresh, the caches untouched). Returns the seconds."""
    t0 = time.time()
    data = variants.info(name)
    m = maps.load_map(name)
    T = maps._build(m, m.get("window"))
    pos = power_positions.positions(m, T, top=8, spacing=9.0, cand_max=800, samples=60)
    own = [p for n, p in variants.own([(n, p) for n, p, _ in variants.pieces_of(data)],
                                      variants.base_placed(m["objects"]))]
    centre = (sum(p[0] for p in own) / len(own), sum(p[1] for p in own) / len(own),
              sorted(p[2] for p in own)[len(own) // 2])
    zones, used = {}, collections.Counter()
    for (x0, y0), word in structures(variants.pieces_of(data)):
        x1, y1 = x0 + CELL, y0 + CELL
        label = word if used[word] == 0 else f"{compass(((x0 + x1) / 2, (y0 + y1) / 2), centre)} {word.lower()}"
        n = 2
        while label in zones:
            label, n = f"{label.rsplit(' ', 1)[0] if label[-1].isdigit() else label} {n}", n + 1
        used[word] += 1
        zones[label] = dict(poly=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]], side="mid", priority=30,
                            full=f"the {word.lower()}", aka=[word.lower()], area=False)
    wx0, wy0, wx1, wy1 = T.window
    long_x = wx1 - wx0 >= wy1 - wy0
    names = ("West side", "Mid", "East side") if long_x else ("South side", "Mid", "North side")
    for k, label in enumerate(names):
        if long_x:
            a, b = wx0 + (wx1 - wx0) * k / 3, wx0 + (wx1 - wx0) * (k + 1) / 3
            poly = [[a, wy0], [b, wy0], [b, wy1], [a, wy1]]
        else:
            a, b = wy0 + (wy1 - wy0) * k / 3, wy0 + (wy1 - wy0) * (k + 1) / 3
            poly = [[wx0, a], [wx1, a], [wx1, b], [wx0, b]]
        zones[label] = dict(poly=poly, side="mid", priority=0, full=label.lower(), aka=[], area=True)
    l, j, i = T._node(Vec(*centre))
    mid = T._center(*T._reachable_node(l, j, i, centre[2]))
    holds = [p["pos"] for p in pos[:4]] or [[mid.x, mid.y, mid.z]]
    base = read_json(os.path.join(maps.ROOT, m["base"], "callouts.json"))
    callouts = dict(map=name, generated=True, base_radius=base.get("base_radius", 5.0), roof_z=base.get("roof_z", 0.0),
                    points={"mid": [round(mid.x, 2), round(mid.y, 2), round(mid.z, 2)],
                            "mid_hill": pos[0]["pos"] if pos else [round(mid.x, 2), round(mid.y, 2), round(mid.z, 2)]},
                    holds={"red": holds, "blue": holds}, lanes=[p["pos"] for p in pos] or holds, sneak={}, zones=zones)
    d = os.path.join(variants.ROOT, name)
    json.dump(callouts, open(os.path.join(d, "callouts.json"), "w"), indent=1)
    # (custom, Nov 8) the owner's marked spots (tools/power_positions.py --add) stay through a layout's new scoring
    old = os.path.join(d, "positions.json")
    pos = power_positions.merge_owner(pos, read_json(old) if os.path.exists(old) else [])
    json.dump(pos, open(old, "w"), indent=1)
    data["strategy_of"] = layout_hash(data)
    variants.save(name, data)
    return time.time() - t0


if __name__ == "__main__":
    for n in sys.argv[1:]:
        print(f"{n}: strategy files in {build(n):.1f} s", flush=True)
