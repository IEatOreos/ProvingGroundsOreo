"""Map variants filed under their base map. A map variant built in Forge gets maps/<base>/variants/<id>/: its own navmesh
data (LiDAR's lidar.json, learned stuck spots and sight lines, paint, reviewed moves: brain/maps.py reads and writes
them by the map name "<base>/variants/<id>") and variant.json (its objects, its nav window, when it was seen, a name
once known). The base map's folder keeps what every variant shares: the level (heightmap.npz), the scenario's objects,
callouts.

A variant is known by the objects it places that the base map's own scenario does not (Forge pieces, spawns, objectives;
read live): the same layout again is the same variant, and a layout sharing most of its objects with a filed one is
that one edited in Forge (pieces added or moved): it keeps its folder and its data. Fewer than MIN_OWN objects of its
own: the base map itself.

Its nav covers its window, not the whole level: its objects' extent plus MARGIN, out to the TILE grid; grown (grown)
when a player comes within EDGE of an edge the level goes on past, and kept in variant.json, so the next match starts
at the size it reached.
"""
import hashlib
import json
import math
import os
import time

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
SUB = "variants"
MIN_OWN = 3          # objects of its own a layout needs to be a variant
SAME = 0.6           # share of the smaller layout's objects also in the other: the same variant, edited since
NEAR = 0.3           # an object this close to a base placement of its name (any name at a spawn) is the base map's
MARGIN = 24.0        # nav around the variant's objects and around a player who reaches an edge
TILE = 16.0          # windows snap out to this grid
EDGE = 8.0           # a player this close to an edge the level goes on past grows the window


def base_of(name):
    """The base map of a map name ("reach_forge_halo/variants/v1a2b3c4d" -> "reach_forge_halo")."""
    return name.split("/" + SUB + "/")[0]


def base_placed(objs):
    """The base map's own placements [(name, pos)] from its objects.json: placed objects, objective objects, and its
    spawns (name "*": whatever stands there)."""
    out = [(it["name"], tuple(it["pos"])) for it in objs.get("placed", [])]
    out += [(f["object"], tuple(f["pos"])) for f in objs.get("netgame_flags", []) if f.get("object")]
    return out + [("*", tuple(sp["pos"])) for sp in objs.get("spawns", [])]


def base_area(objs):
    """Where the base map's own layout is (its placed objects and weapons, objects.json): a variant's window takes it
    in, so a few pieces added to Settlement do not cut the nav down to them. A Forge canvas (Forge World) has none."""
    return [tuple(it["pos"]) for k in ("placed", "equipment") for it in objs.get(k, [])]


def own(objs, placed):
    """The objects [(name, pos)] the base map does not place itself, skybox scenery left out (Forge World's sky_halo,
    the ring in the sky at 0, 0, 0: not the layout, and it stretched the window 110 u)."""
    return [(n, p) for n, p in objs if not n.startswith("sky")
            and not any((m == n or m == "*") and math.dist(q, p) <= NEAR for m, q in placed)]


def _key(name, pos):
    return (name, round(pos[0] * 2) / 2, round(pos[1] * 2) / 2, round(pos[2] * 2) / 2)


def _snap(x0, y0, x1, y1):
    return (math.floor(x0 / TILE) * TILE, math.floor(y0 / TILE) * TILE, math.ceil(x1 / TILE) * TILE,
            math.ceil(y1 / TILE) * TILE)


def union(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])) if a and b else tuple(a or b)


def window_of(points):
    """The window around points [(x, y, ...)]: their extent plus MARGIN, out to the TILE grid."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return _snap(min(xs) - MARGIN, min(ys) - MARGIN, max(xs) + MARGIN, max(ys) + MARGIN)


def grown(window, pos, full):
    """The window grown to take in pos with MARGIN round it, when pos is within EDGE of one of its edges past which the
    level (full: its whole extent) goes on; else None."""
    x0, y0, x1, y1 = window
    x, y = (pos.x, pos.y) if hasattr(pos, "x") else (pos[0], pos[1])
    if not ((x < x0 + EDGE and x0 > full[0]) or (x > x1 - EDGE and x1 < full[2]) or
            (y < y0 + EDGE and y0 > full[1]) or (y > y1 - EDGE and y1 < full[3])):
        return None
    w = union(window, _snap(x - MARGIN, y - MARGIN, x + MARGIN, y + MARGIN))
    w = (max(w[0], math.floor(full[0] / TILE) * TILE), max(w[1], math.floor(full[1] / TILE) * TILE),
         min(w[2], math.ceil(full[2] / TILE) * TILE), min(w[3], math.ceil(full[3] / TILE) * TILE))
    return w if w != tuple(window) else None


def _read(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    json.dump(data, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, path)


def info(name):
    """A filed variant's variant.json (None for a base map)."""
    return _read(os.path.join(ROOT, name, "variant.json")) if "/" + SUB + "/" in name else None


def pieces_of(data):
    """A filed variant's pieces as [(name, pos, (forward, left, up))] (variant.json "pieces")."""
    return [(p[0], tuple(p[1:4]), (tuple(p[4:7]), tuple(p[7:10]), tuple(p[10:13]))) for p in data.get("pieces", [])]


def identify(base, pieces, placed=(), game=None, now=None, area=()):
    """The map name for a layout read live, pieces [(name, pos, (forward, left, up))] (placed: the base map's own,
    base_placed(); area: where its layout is, base_area()): base when it has fewer than MIN_OWN objects of its own,
    else "<base>/variants/<id>", the filed variant sharing SAME or more of its objects (the best) or a new one. Its
    variant.json gets the layout (all its pieces, to build its nav from, live or not: brain/maps.py), a window round it
    and the base map's area (the old window kept within) and when it was seen."""
    mine = own([(n, p) for n, p, _ in pieces], placed)
    if len(mine) < MIN_OWN:
        return base
    keys = {_key(n, p) for n, p in mine}
    d = os.path.join(ROOT, base, SUB)
    best = None
    for vid in sorted(os.listdir(d)) if os.path.isdir(d) else ():
        old = _read(os.path.join(d, vid, "variant.json"))
        if not old:
            continue
        theirs = {tuple(k) for k in old.get("objects", [])}
        share = len(keys & theirs) / max(1, min(len(keys), len(theirs)))
        if share >= SAME and (best is None or share > best[0]):
            best = (share, vid, old)
    now = now or time.strftime("%Y-%m-%d %H:%M")
    if best:
        _, vid, data = best
    else:
        vid = "v" + hashlib.sha1(json.dumps(sorted(keys)).encode()).hexdigest()[:8]
        data = dict(id=vid, base=base, game=game, name=None, first_seen=now)
    data.update(objects=[list(k) for k in sorted(keys)], count=len(keys), last_seen=now,
                window=list(union(data.get("window"), window_of([p for _, p in mine] + list(area)))),
                pieces=[[n] + [round(v, 4) for v in tuple(p) + tuple(c for ax in a for c in ax)] for n, p, a in pieces])
    _write(os.path.join(d, vid, "variant.json"), data)
    return f"{base}/{SUB}/{vid}"


def save(name, data):
    """Write a filed variant's variant.json."""
    _write(os.path.join(ROOT, name, "variant.json"), data)


def save_window(name, window):
    """Keep a variant's grown window for its next match."""
    data = info(name)
    if data is not None:
        data["window"] = list(window)
        save(name, data)
