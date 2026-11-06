"""Out of bounds: where nobody may be. The games' kill zones and soft kill zones (the "return to the battlefield" count)
as the maps define them (KNOWN, below), and the spots learned where they show:

  death  a player died with nobody who could have killed him: alive and on foot, health and shield full a second
         before, no fall (under FALL u down in the last 2 s), no enemy within NEAR u and none in sight within SIGHT u,
         and not one of several deaths at once (a round's reset). One such death is a candidate; it counts once a
         second one lands within R of it, or at once if no enemy was alive within ALONE u
  flag the player's bug report naming it ("out of bounds", "oob", "kill zone", "soft kill", "kill barrier"): at once,
         where he stood
Neither on a Forge layout whose own .mvar was read (its kill zones all known: Oob.learn False).

Kept per map or Forge layout in maps/<map>/oob.json: {"spots": [[x, y, z, source, t, note]], "candidates": [...]}.
Terrain.set_oob (brain/terrain.py) makes the counted spots a soft wall: a step into a cell within R (and DZ of its
height) costs a barrier's, a goal there moves out, the vehicles' ground leaves it out, a pilot's probe sees it within
AIR_DZ of its height.

KNOWN: maps/<map>/killzones.json (tools/killzones.py, from the kits' scenario and structure design data) and, on a
Forge layout, maps/<map>/variants/<v>/killzones.json (its .mvar boundaries), both loaded (volumes()):
  {"volumes": [{"kind", "shape", "center", "size", "rotation"?, "source", "label", "points"?, "triangles"?}]}
  kind      "hard": inside kills at once; "soft": inside starts the soft kill count; "safe" / "soft_safe" (Reach-era
            Safe / Soft Safe zones): OUTSIDE every volume of that kind kills / starts the count
  shape     "box": size = full lengths along forward, left (= up x forward), up; "points" [[x, y], ...] when it is a
            polygon prism (a Reach sector: inside the polygon, z within the box); "cylinder": size = [radius, radius,
            height] round center (mid height) along up; "sphere": size = [radius, radius, radius]; "plane": a soft kill
            surface (BSP soft ceiling), "triangles" [[v0, v1, v2], ...], center / size its bounding box, inside = within
            SLAB of a triangle
  center    the volume's middle, world units; rotation {"forward": [x, y, z], "up": [x, y, z]} unit axes (omitted:
            axis aligned, forward +x, up +z)
  source    "scenario" | "bsp" | "mvar"; label: the map's name for it
  condition (optional) why it is not always on (a game type's object, a script-toggled volume over the spawns):
            such volumes are kept in the file and left out here
Terrain.set_oob(spots, version, volumes): the hard and soft volumes' floors (and the floors outside every safe zone)
join the learned spots' soft wall (each step in costs BARRIER_COST, a goal there moves out, the vehicles' ground leaves
them out); oob_avoid gives a pilot's probe discs over them. watch() counts a death inside one (or within EDGE of it) at
once, "known: <label>".
"""
import json
import math
import os
import re
import time

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
R, DZ, AIR_DZ = 4.0, 3.0, 8.0      # u: a spot's soft wall round it, its floors' height band, a pilot's
NEAR, SIGHT, ALONE, FALL = 6.0, 80.0, 80.0, 3.0   # (ALONE as SIGHT: a sniper 60 u off through a gap the level
# data has as solid is no out of bounds until a second death there)
FULL = 0.9                         # health and shield a second before: nothing had hurt him
AT_ONCE = 3                        # this many deaths inside a second: a reset, not a zone
BLAST_S = 3.0                      # s: a candidate's twin dies at least this long after it (not in the same blast)
WORDS = re.compile(r"out of bounds|\boob\b|kill ?zone|soft ?kill|kill ?barrier|kill ?boundar", re.I)
SLAB = 0.5                         # u: a soft kill surface's triangles count this far each side
EDGE = 2.0                         # u: a death this near a known volume is its (the last read was before he got in)
DROP_READ = 10.0                   # u: how far over a kill zone a falling player can be read last (where_dropping)
BODY = (0.1, 0.6)                  # u over a floor: the heights a standing player's body is tested at
KILLS, SAFES = ("hard", "soft"), ("safe", "soft_safe")


def path_of(map_name):
    return os.path.join(ROOT, map_name, "oob.json")


def volumes(map_name, phase=None):
    """The known kill / soft kill / safe volumes of a map or Forge layout ("<map>/variants/<v>"): its base map's
    killzones.json and the layout's own. phase: the Invasion phase running (its gates' volumes still stand)."""
    out, base = [], map_name.replace("\\", "/").partition("/")[0]
    for m in dict.fromkeys((base, map_name)):
        try:
            out += json.load(open(os.path.join(ROOT, m, "killzones.json"), encoding="utf-8")).get("volumes", [])
        except (OSError, ValueError):
            pass
    # a map variant's game-type volumes (.mvar gametype_specific) are the game type's, not the map's. Invasion's phase
    # gates (inv_gates, spawn sequence = the phase they close) stand until their phase is taken: Boneyard's laser lines
    # kill, Spire's soft kill boxes keep attackers out of the spire; for good they put Spire's phase 2 territories,
    # core and delivery point out of bounds and no attacker ever stood on them (live 20261104-222857); never, the sim's
    # Boneyard attackers took the lasers' gaps and stood under phase 1's territories all round (6 of 6 rounds lost)
    # ponytail: any other game type's volume (inv_slayer) is left out, not avoided; one mask for both teams
    gate = lambda v: phase is not None and v.get("forge_label") == "inv_gates" and v.get("seq", 1) >= phase
    return [v for v in out if not v.get("condition") and v.get("placed_at_start", True)
            and (not v.get("gametype_specific") or gate(v))]


def _axes(v):
    r = v.get("rotation") or {}
    f, u = np.array(r.get("forward", (1, 0, 0)), float), np.array(r.get("up", (0, 0, 1)), float)
    return f, np.cross(u, f), u


def _seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def tri_dist(tri, P):
    """Distance of each point of P (n, 3) to the triangle tri [v0, v1, v2]."""
    a, b, c = (np.asarray(v, float) for v in tri)
    d = np.minimum(np.minimum(_seg_dist(P, a, b), _seg_dist(P, b, c)), _seg_dist(P, c, a))
    n = np.cross(b - a, c - a)
    area2 = float(n @ n)
    if area2 < 1e-12:
        return d
    w = P - a
    u = (np.cross(w, c - a) @ n) / area2          # barycentric: P's projection = a + u (b - a) + v (c - a)
    v = (np.cross(b - a, w) @ n) / area2
    inside = (u >= 0) & (v >= 0) & (u + v <= 1)
    return np.where(inside, np.abs(w @ n) / math.sqrt(area2), d)


def _in_polygon(pts, Q, pad):
    """Q (n, 2) inside the polygon pts [[x, y], ...] or within pad of its edges."""
    poly = np.asarray(pts, float)
    x, y = Q[:, 0], Q[:, 1]
    inside = np.zeros(len(Q), bool)
    near = np.full(len(Q), np.inf)
    for (x1, y1), (x2, y2) in zip(poly, np.roll(poly, -1, axis=0)):
        with np.errstate(divide="ignore", invalid="ignore"):
            cross_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        inside ^= ((y1 > y) != (y2 > y)) & (x < cross_x)
        if pad > 0:
            near = np.minimum(near, _seg_dist(np.c_[Q, np.zeros(len(Q))], np.array([x1, y1, 0.0]), np.array([x2, y2, 0.0])))
    return inside | (near <= pad)


def contains(v, P, pad=0.0):
    """Which of the points P ((n, 3), or one (x, y, z)) are inside the volume v grown by pad."""
    P = np.asarray(P, float).reshape(-1, 3)
    if v["shape"] == "plane":
        out = np.zeros(len(P), bool)
        for tri in v["triangles"]:
            lo, hi = np.min(tri, axis=0) - SLAB - pad, np.max(tri, axis=0) + SLAB + pad
            k = np.all((P >= lo) & (P <= hi), axis=1)
            if k.any():
                out[k] |= tri_dist(tri, P[k]) <= SLAB + pad
        return out
    s = np.asarray(v["size"], float)
    f, lf, u = _axes(v)
    d = P - np.asarray(v["center"], float)
    a, b, h = d @ f, d @ lf, d @ u
    if v["shape"] == "sphere":
        return np.sqrt(a * a + b * b + h * h) <= s[0] + pad
    zin = np.abs(h) <= s[2] / 2 + pad
    if v["shape"] == "cylinder":
        return zin & (np.hypot(a, b) <= s[0] + pad)
    if v.get("points"):
        return zin & _in_polygon(v["points"], P[:, :2], pad)
    return zin & (np.abs(a) <= s[0] / 2 + pad) & (np.abs(b) <= s[1] / 2 + pad)


def bounds(v, pad=0.0):
    """(lo, hi) world box round a volume (grown by pad)."""
    if v["shape"] == "plane":
        xs = np.asarray([p for t in v["triangles"] for p in t], float)
        return xs.min(axis=0) - SLAB - pad, xs.max(axis=0) + SLAB + pad
    s, c = np.asarray(v["size"], float), np.asarray(v["center"], float)
    if v["shape"] == "sphere":
        r = s[0]
    else:
        f, lf, u = _axes(v)
        half = [s[0], s[0], s[2] / 2] if v["shape"] == "cylinder" else s / 2
        r = abs(f) * half[0] + abs(lf) * half[1] + abs(u) * half[2]
    return c - r - pad, c + r + pad


def where(vols, p, pad=0.0):
    """The volume p (x, y, z) is in, the kill kinds first; or the safe kind he is outside every volume of; None."""
    for v in vols:
        if v["kind"] in KILLS and contains(v, p, pad)[0]:
            return v
    for kind in SAFES:
        vs = [v for v in vols if v["kind"] == kind]
        if vs and not any(contains(v, p, -pad)[0] for v in vs):
            return dict(vs[0], label=f"outside {vs[0]['label']}")
    return None


def where_dropping(vols, p, drop, pad=EDGE):
    """where() for a death at p, last read: a player falling (drop: u down in his last 2 s) is read up to DROP_READ u
    above where he died (Island's sea: 26 u falls last read 7 u over the kill box), so the column under p counts."""
    v = where(vols, p, pad)
    for k in np.arange(1.0, min(drop, DROP_READ) + 0.01, 1.0) if v is None and drop >= FALL else ():
        v = where(vols, (p[0], p[1], p[2] - k), pad)
        if v is not None:
            break
    return v


def floor_mask(vols, lz, x0, y0, cell):
    """(L, nh, nw) bool: the floors (lz: their heights, NaN none) a standing player's body would be out of bounds on:
    inside a hard / soft volume, or outside every volume of a safe kind."""
    mask = np.zeros(lz.shape, bool)
    _, nh, nw = lz.shape

    def test(v, lo, hi):
        i0, i1 = max(0, int((lo[0] - x0) / cell)), min(nw, int((hi[0] - x0) / cell) + 1)
        j0, j1 = max(0, int((lo[1] - y0) / cell)), min(nh, int((hi[1] - y0) / cell) + 1)
        if i0 >= i1 or j0 >= j1:
            return
        sub = lz[:, j0:j1, i0:i1]
        with np.errstate(invalid="ignore"):
            cand = np.isfinite(sub) & (sub > lo[2] - BODY[1]) & (sub < hi[2])
        if not cand.any():
            return
        ls, js, is_ = np.nonzero(cand)
        X, Y, Z = x0 + (is_ + i0 + 0.5) * cell, y0 + (js + j0 + 0.5) * cell, sub[cand]
        hit = np.zeros(len(Z), bool)
        for dz in BODY:
            hit |= contains(v, np.c_[X, Y, Z + dz])
        mask[ls[hit], js[hit] + j0, is_[hit] + i0] = True

    for v in vols:
        if v["kind"] not in KILLS:
            continue
        if v["shape"] == "plane":                   # triangle by triangle: a ceiling's box is the whole map
            for tri in v["triangles"]:
                lo, hi = np.min(tri, axis=0) - SLAB, np.max(tri, axis=0) + SLAB
                test(dict(v, triangles=[tri]), lo, hi)
        else:
            test(v, *bounds(v))
    for kind in SAFES:
        vs = [v for v in vols if v["kind"] == kind]
        if not vs:
            continue
        ls, js, is_ = np.nonzero(np.isfinite(lz))
        P = np.c_[x0 + (is_ + 0.5) * cell, y0 + (js + 0.5) * cell, lz[ls, js, is_] + BODY[1]]
        safe = np.zeros(len(P), bool)
        for v in vs:
            safe |= contains(v, P)
        mask[ls[~safe], js[~safe], is_[~safe]] = True
    return mask


def air_discs(vols):
    """A pilot's probe's avoid discs (x, y, z, r, height band) over the hard and soft volumes: each tiled by discs a
    tile's diagonal wide. ponytail: safe zones are left out (a pilot leaving a map's safe zone flies 100s of u out)."""
    out = []
    for v in vols:
        if v["kind"] not in KILLS:
            continue
        lo, hi = bounds(v)
        g = 6.0 if v["shape"] == "plane" else max(6.0, min(hi[0] - lo[0], hi[1] - lo[1]) / 4)
        cols = {}
        if v["shape"] == "plane":                   # the surface's height range per tile
            for tri in v["triangles"]:
                for p in tri:
                    k = (int((p[0] - lo[0]) // g), int((p[1] - lo[1]) // g))
                    z0, z1 = cols.get(k, (p[2], p[2]))
                    cols[k] = (min(z0, p[2]), max(z1, p[2]))
        else:
            for a in range(int(math.ceil((hi[0] - lo[0]) / g))):
                for b in range(int(math.ceil((hi[1] - lo[1]) / g))):
                    x, y = lo[0] + (a + 0.5) * g, lo[1] + (b + 0.5) * g
                    zs = np.linspace(lo[2], hi[2], 9)
                    inn = contains(v, np.c_[np.full(9, x), np.full(9, y), zs], pad=g * 0.5)
                    if inn.any():
                        cols[(a, b)] = (float(zs[inn].min()), float(zs[inn].max()))
        for (a, b), (z0, z1) in cols.items():
            out.append((lo[0] + (a + 0.5) * g, lo[1] + (b + 0.5) * g, (z0 + z1) / 2, g * 0.75, (z1 - z0) / 2 + 1.0))
    return out


def load(map_name):
    try:
        d = json.load(open(path_of(map_name), encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {"spots": d.get("spots", []), "candidates": d.get("candidates", []), "known": d.get("known", [])}


class Oob:
    """The map's out of bounds, watched live (the brain's loop and LiDAR's: watch every tick, flag per bug report)."""

    def __init__(s, map_name, clock=time.time):
        s.map, s.clock = map_name, clock
        d = load(map_name)
        s.spots, s.candidates, s.known = d["spots"], d["candidates"], d["known"]   # (known: deaths in known volumes)
        s.volumes = volumes(map_name)          # the map's own kill zones (killzones.json)
        s.hist, s.version = {}, 0              # (id -> [(t, pos, health, shield, riding)] last 2 s); bumped on change
        # A Forge layout whose own map variant file was read (brain/mvar.write filed its killzones.json): every kill
        # zone it has is known, its own and its base map's, so a death in none of them was a kill nobody was seen
        # making (a grenade or a rocket round cover), not out of bounds. Learned there, they walled the ways to the
        # objectives: Spire 20261105-004256 a spot 5 u from phase 2's territory; S3 / S4 three along the Spartans'
        # lane to phase 1's territory A (its way 61.7 -> 72.2 u), phase 1 lost both rounds of S5 (045139) after 8 of 8
        # taken; Boneyard spots on the stairs to phase 1's platform (249.0, 102.5) and the east ramp (262.2, 73.5).
        # Nor a player's flag: it is filed where he stands, and a report names out of bounds about something else too
        # (Spire 20261105-201917 at 342.8 s, from the spire's top: "... flies it into the fucking soft kill boundary
        # it should be fucking detecting ...", the Falcon): a soft wall 4 u round the core's stand. The spots learned
        # there before, deaths and flags, are dropped.
        # ponytail: base maps (scenario + BSP kill zones) still learn; drop it there too once one shows the same
        layout = "/" in map_name.replace("\\", "/")
        s.learn = not (layout and os.path.exists(os.path.join(ROOT, map_name, "killzones.json")))
        if not s.learn and (s.spots or s.candidates):
            s.spots, s.candidates = [], []
            s.version += 1                     # (saved so, at the brain's next save)

    def set_phase(s, T, phase):
        """The Invasion phase now (None: not Invasion): its standing gates' volumes join the known ones, on T too."""
        if phase != getattr(s, "_phase", None):
            s._phase, s.volumes = phase, volumes(s.map, phase)
            T.set_oob(s.spots, None, s.volumes)

    def _add(s, x, y, z, source, t, note=""):
        s.spots.append([round(x, 2), round(y, 2), round(z, 2), source, round(t, 1), note[:80]])
        s.version += 1

    def flag(s, text, pos, t):
        """the player's bug report: a spot where he stood when it names out of bounds (not on a layout whose kill zones
        are all known: learn False). True if it did."""
        if not pos or not s.learn or not WORDS.search(text or ""):
            return False
        s._add(pos[0], pos[1], pos[2], "flag", t, text)
        return True

    def watch(s, now, people, sees=None):
        """people: [(id, team, (x, y, z) or None, alive, health, shield, riding)] this tick. sees(a, b): a clear line of
        sight between two places (the terrain's), or None (then nobody in sight counts only past SIGHT). Returns the
        deaths it took for out of bounds this tick, [(x, y, z, counted)]."""
        out, died = [], []
        for pid, team, pos, alive, hp, sh, riding in people:
            h = s.hist.setdefault(pid, [])
            if alive and pos is not None:
                h.append((now, pos, hp, sh, riding))
                while h and now - h[0][0] > 2.0:
                    h.pop(0)
            elif not alive and h:
                died.append((pid, team, h[-1], list(h)))
                s.hist[pid] = []
        if len(died) >= AT_ONCE:
            return out
        living = [(team, h[-1][1]) for pid, team, *_ in people for h in [s.hist.get(pid)] if h]
        for pid, team, last, h in died:
            t, pos, hp, sh, riding = last
            before = [e for e in h if now - e[0] >= 0.8] or h[:1]
            # riding: counted only with the vehicle's health read full before too (the player: a bot pilot flew him
            # out of bounds; a wreck kills its crew without a scratch on them, an unread vehicle stays skipped)
            hurt = [e[4] for e in before if e[4] is not False]
            if any(r is True or r < FULL for r in hurt) or min(e[2] for e in before) < FULL \
                    or min(e[3] for e in before) < FULL:
                continue
            v = where_dropping(s.volumes, pos, max(e[1][2] for e in h) - pos[2]) if s.volumes else None
            if v is not None:                                # the map's own kill zone (a fall into a kill pit too)
                s.known.append([round(pos[0], 2), round(pos[1], 2), round(pos[2], 2), round(now, 1), v["label"][:60]])
                s.version += 1
                out.append((pos[0], pos[1], pos[2], True))
                continue
            if not s.learn:
                continue                                     # (every kill zone of this layout known: Oob.learn)
            if max(e[1][2] for e in h) - pos[2] >= FALL:
                continue                                     # a fall (LiDAR's deadly drops have it)
            foes = [q for tm, q in living if tm != team or tm < 0]
            near = [q for q in foes if math.dist(q, pos) < SIGHT]
            if any(math.dist(q, pos) < NEAR for q in near):
                continue
            if near and (sees is None or any(sees(q, pos) for q in near)):
                continue                                     # (no sight lines to test: anyone within SIGHT could)
            alone = not any(math.dist(q, pos) < ALONE for q in foes)
            # (a second death there later: two in the same blast are one event, a grenade or a rocket out of sight;
            # live Spire 20261105-004256, two Spartans at 232.1 s, 5 u from phase 2's territory)
            twin = next((c for c in s.candidates if math.dist(c[:2], pos[:2]) < R and abs(c[2] - pos[2]) < DZ
                         and now - c[3] > BLAST_S), None)
            counted = alone or twin is not None
            if counted:
                s._add(pos[0], pos[1], pos[2], "death", now, "alone" if alone else "twice")
                if twin is not None:
                    s.candidates.remove(twin)
            else:
                s.candidates.append([round(pos[0], 2), round(pos[1], 2), round(pos[2], 2), round(now, 1)])
            out.append((pos[0], pos[1], pos[2], counted))
        return out

    def save(s):
        p = path_of(s.map)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        json.dump({"spots": s.spots, "candidates": s.candidates, "known": s.known}, open(tmp, "w", encoding="utf-8"),
                  indent=1)
        os.replace(tmp, p)
        return p


KIND_NAME = {"hard": "kill zone", "soft": "soft kill zone", "safe": "safe zone edge", "soft_safe": "soft safe zone edge"}


def outline(v, step=2.0):
    """Points along a known volume's edges for the LiDAR view: a box / prism / cylinder its bottom and top rims, a
    sphere its equator, a surface its triangles' middles (at most 400)."""
    if v["shape"] == "plane":
        tris = v["triangles"]
        return [list(np.mean(t, axis=0)) for t in tris[::max(1, len(tris) // 400)]]
    c, s = np.asarray(v["center"], float), np.asarray(v["size"], float)
    f, lf, u = _axes(v)
    if v.get("points"):
        ring = [np.array([x, y, 0.0]) for x, y in v["points"]]
        ring = [p + np.array([0, 0, c[2]]) for p in ring]
    elif v["shape"] in ("cylinder", "sphere"):
        n = max(8, min(64, int(2 * math.pi * s[0] / step)))
        ring = [c + s[0] * (math.cos(a) * f + math.sin(a) * lf) for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]
    else:
        ring = [c + (sa * s[0] / 2) * f + (sb * s[1] / 2) * lf for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    dz = [0.0] if v["shape"] == "sphere" else [-s[2] / 2, s[2] / 2]
    pts = []
    for a, b in zip(ring, ring[1:] + ring[:1]):
        n = max(1, min(40, int(np.linalg.norm(b - a) / step)))
        for k in range(n):
            q = a + (b - a) * k / n
            pts += [list(q + h * u) for h in dz]
    return pts


def features(map_name, data=None):
    """The counted spots and the map's known volumes (killzones.json) as the LiDAR view's zones (tools/lidar.py
    load_features): a labelled zone at a volume's middle, its rims as kill_edge dots."""
    d = data if data is not None else load(map_name)
    out = [dict(kind="zone", name=f"out of bounds ({sp[3]})", pos=sp[:3], station="out_of_bounds") for sp in d["spots"]]
    for v in volumes(map_name):
        out.append(dict(kind="zone", name=f"{KIND_NAME.get(v['kind'], v['kind'])}: {v['label']}", pos=list(v["center"]),
                        station="kill_zone"))
        out += [dict(kind="kill_edge", name="", pos=[round(float(x), 2) for x in p]) for p in outline(v)]
    return out
