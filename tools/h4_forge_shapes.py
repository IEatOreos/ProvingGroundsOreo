"""Halo 4 Forge pieces' shapes read from MCC's own Halo 4 .map files, for the pieces the editing kit export lacks.
maps/_shapes/h4.json came from the kit's collision models (tools/object_shapes.py, not in every install); 23 of the
owner's Forge Ravine layout's 39 piece kinds had no shape there, so its round base, tower, walls and platforms were
open ground to the bots (brain/forge.py block: no shape, no block).

A cached Halo 4 collision model keeps no surfaces: every Forge piece's permutations have empty BSP blocks. What the
game moves bodies against is the piece's physics model (Havok): convex polyhedra, each the plane equations of its hull
shrunk by a convex radius (the 1x1 flat platform: half extents 0.4836 x 0.4836 x 0.0836 plus 0.0164, the kit's
0.5 x 0.5 x 0.1). A hull's planes, pushed out by its radius, clip one another into its faces; the part of a face
inside another hull of the same piece, or back to back against one, is inside the piece and left out. A piece is the
rigid bodies of each region's first (default) permutation, through their lists and MOPP trees. Phantom shapes (a man
cannon's launch volume, a lift's pull) and hulls of a material on a collision layer other than 0 (gravity volumes,
lights, shield doors' panes: bodies pass) are no walls and are left out. Each hull is also closed by the box round its
vertices, pushed out by its radius (a flat hull's planes leave it open).

The .map file (MCC Halo 4): header +0x2D8 the tag section's address, +0x2E0 the tag index header's, +0x4C4 the four
section offsets, +0x4D4 the four sections' (address, size). Tag data pointers are 32 bits: address * 4 + 0x4FFF0000.
A tag block is (count, pointer, 0xCDCDCDCD), a tag reference (group, -, -, datum). Found on the four Forge canvases
and checked against the kit's shapes (--check): object +0x64 its model (hlmt); model +0x10 collision model, +0x30
physics model; physics model +0x5C rigid bodies (0xE0 each: +0 node, +2 region, +4 permutation, +0xB8 shape type and
index), +0x68 materials (0x10: +0 name, +0xC phantom type, +0xE collision layer), +0xB0 polyhedra (0xA0: +4 material,
+0x1E phantom, +0x40 convex radius, +0x78 four-vectors used, +0x80 vertices, +0x90 planes used), +0xBC four-vectors
(0x30: x4, y4, z4), +0xC8 plane equations (0x10: normal, offset), +0xE0 lists (0x90: +0x38 children used), +0xEC list
shapes (0x20: shape type, index), +0xF8 MOPPs (0x80: +0x58 child). Polyhedra and lists take their four-vectors,
planes and children in order. Shape types: 4 polyhedron, 6 phantom, 14 list, 15 MOPP. String ids: namespace 0 ids
past its own count follow the other namespaces.

Only the Forge pieces (a path under objects\\levels\\forge\\, or a name starting fw_) and skies the shape files lack are
added; the kit's shapes stay. Entries made here carry "source": "physics_model". Bodies on a node other than the
piece's root are placed as if the node sat at the root (the jersey barriers', the large palette's and the vehicle
barrier's: their Forge Island twins' kit boxes agree within 0.02 u; --list names them).

usage: python -I tools/h4_forge_shapes.py [map ...]   adds the missing pieces to maps/_shapes/h4.json, h4_faces.json
       python -I tools/h4_forge_shapes.py --list      what it would add, and from which map
       python -I tools/h4_forge_shapes.py --check     this reading against the kit's shapes of the same pieces
(maps: the Halo 4 maps with a tag name list in maps/_shapes, default; MCC's folder from brain/paths.py)
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reach_tag_names  # noqa: E402  (MCC's folder; tag names by index)

SHAPES = os.path.join(HERE, "..", "maps", "_shapes")
POINTER_BASE = 0x4FFF0000
POLYHEDRON, PHANTOM, LIST, MOPP = 4, 6, 14, 15
OBJECT_GROUPS = ("bloc", "scen")         # what brain/forge.py reads live in Halo 4 (crates, scenery)
TOL = 2e-3                                # world units: one plane / one point for the hulls' surfaces
HOW = ("Halo 4 Forge pieces the kit export lacked (\"source\": \"physics_model\"): read from MCC's own Halo 4 .map "
       "files by tools/h4_forge_shapes.py, from each piece's physics model (Havok convex hulls pushed out by their "
       "convex radius; faces inside the piece left out). Same axes and units as the kit's.")


class CacheFile:
    """One MCC Halo 4 .map file's tag data, tag index, tag names and string ids."""

    def __init__(s, path):
        s.path = path
        with open(path, "rb") as f:
            h = f.read(0x800)
            if h[:4] != b"daeh":
                raise ValueError(f"{path}: not a cache file")
            offs = struct.unpack_from("<4i", h, 0x4C4)
            tag_addr, tag_size = struct.unpack_from("<2I", h, 0x4D4 + 16)
            s.vbase, index_at = struct.unpack_from("<QQ", h, 0x2D8)
            f.seek((tag_addr + offs[2]) & 0xFFFFFFFF)
            s.data = f.read(tag_size)
            debug = lambda p: (p + offs[0]) & 0xFFFFFFFF
            count, buf, size, idx = struct.unpack_from("<4I", h, 0x30)
            ns_count, ns_at = struct.unpack_from("<2I", h, 0x40)
            f.seek(debug(idx))
            offsets = struct.unpack(f"<{count}i", f.read(4 * count))
            f.seek(debug(buf))
            blob = f.read(size)
            f.seek(debug(ns_at))
            s.namespaces = struct.unpack(f"<{ns_count}i", f.read(4 * ns_count))
        s.strings = [blob[o:blob.find(b"\0", o)].decode("latin1") if o >= 0 else "" for o in offsets]
        ih = index_at - s.vbase
        gc, _, gv, tc, _, tv = struct.unpack_from("<iIQiIQ", s.data, ih)
        groups = [s.data[gv - s.vbase + 16 * i:gv - s.vbase + 16 * i + 4][::-1].decode("latin1") for i in range(gc)]
        s.tags = []
        for i in range(tc):
            g, _salt, addr = struct.unpack_from("<HHI", s.data, tv - s.vbase + 8 * i)
            s.tags.append((groups[g] if g < gc else None, addr))
        s.names = reach_tag_names.names_of(path)

    def off(s, ptr):
        o = ptr * 4 + POINTER_BASE - s.vbase
        if not 0 <= o < len(s.data):
            raise ValueError(f"pointer {ptr:#x} outside the tag data")
        return o

    def tag_off(s, i):
        return s.off(s.tags[i][1])

    def rows(s, at, stride):
        """A tag block's element offsets."""
        n, ptr = struct.unpack_from("<iI", s.data, at)
        if n <= 0:
            return []
        o = s.off(ptr)
        return [o + stride * k for k in range(n)]

    def ref(s, at, group):
        """The tag index a tag reference names, if it is of that group."""
        g, _, _, datum = struct.unpack_from("<4sIII", s.data, at)
        if g[::-1].decode("latin1") != group or datum == 0xFFFFFFFF or (datum & 0xFFFF) >= len(s.tags):
            return None
        i = datum & 0xFFFF
        return i if s.tags[i][0] == group else None

    def string(s, sid):
        i, ns = sid & 0x1FFFF, (sid >> 17) & 0xFF
        g = i - s.namespaces[0] + sum(s.namespaces) if ns == 0 and i >= s.namespaces[0] else sum(s.namespaces[:ns]) + i
        return s.strings[g] if 0 <= g < len(s.strings) else ""


def convex_parts(cf, phmo):
    """A physics model's solid hulls [(material, [(normal, offset)])] (points p inside: normal . p <= offset), and the
    nodes their bodies hang on."""
    d, o = cf.data, cf.tag_off(phmo)
    mats = [cf.string(struct.unpack_from("<I", d, r)[0]) for r in cf.rows(o + 0x68, 0x10)]
    # a material's phantom type (+0xC, -1: none) and collision layer (+0xE): layer 0 is what bodies stand on and bump
    # into; layer 9 is the gravity volumes', the lights' and the shield doors' (bodies pass), 4 a grab object's
    solid = [struct.unpack_from("<hB", d, r + 0xC) == (-1, 0) for r in cf.rows(o + 0x68, 0x10)]
    planes = [struct.unpack_from("<4f", d, r) for r in cf.rows(o + 0xC8, 0x10)]
    fourv = [struct.unpack_from("<12f", d, r) for r in cf.rows(o + 0xBC, 0x30)]
    polys, start, vstart = [], 0, 0
    for r in cf.rows(o + 0xB0, 0xA0):
        mat, = struct.unpack_from("<h", d, r + 4)
        phantom = struct.unpack_from("<b", d, r + 0x1E)[0]
        radius, = struct.unpack_from("<f", d, r + 0x40)
        nv, = struct.unpack_from("<i", d, r + 0x78)
        verts, = struct.unpack_from("<i", d, r + 0x80)
        n, = struct.unpack_from("<i", d, r + 0x90)
        pts = [(q[k], q[4 + k], q[8 + k]) for q in fourv[vstart:vstart + nv] for k in range(4)][:verts]
        polys.append((mat, phantom, radius, planes[start:start + n], pts))
        start, vstart = start + n, vstart + nv
    if start != len(planes) or vstart != len(fourv):
        raise ValueError("plane equations or vertices do not add up")
    lshapes = [struct.unpack_from("<hh", d, r) for r in cf.rows(o + 0xEC, 0x20)]
    lists, start = [], 0
    for r in cf.rows(o + 0xE0, 0x90):
        n, = struct.unpack_from("<i", d, r + 0x38)
        lists.append(lshapes[start:start + n])
        start += n
    if start != len(lshapes):
        raise ValueError("list shapes do not add up")
    mopps = [struct.unpack_from("<hh", d, r + 0x58) for r in cf.rows(o + 0xF8, 0x80)]
    found, nodes, unknown = [], set(), set()

    def walk(kind, i, depth=0):
        if depth > 8:
            return
        if kind == POLYHEDRON and 0 <= i < len(polys):
            found.append(i)
        elif kind == LIST and 0 <= i < len(lists):
            for k, j in lists[i]:
                walk(k, j, depth + 1)
        elif kind == MOPP and 0 <= i < len(mopps):
            walk(*mopps[i], depth=depth + 1)
        elif kind != PHANTOM:
            unknown.add(kind)

    for r in cf.rows(o + 0x5C, 0xE0):
        node, _region, perm = struct.unpack_from("<hhh", d, r)
        if perm != 0:
            continue                               # (another permutation: a destroyed or variant state)
        nodes.add(node)
        walk(*struct.unpack_from("<hh", d, r + 0xB8))
    if unknown:
        raise ValueError(f"shape types not read: {sorted(unknown)}")
    out = []
    for i in dict.fromkeys(found):
        mat, phantom, radius, pl, pts = polys[i]
        if phantom != -1 or not pts or not (0 <= mat < len(solid) and solid[mat]):
            continue
        hull = [((a, b, c), -e + radius) for a, b, c, e in pl]
        # the box round its vertices, pushed out by the radius, closes a hull whose planes leave it open (a flat one)
        # and trims a sharp corner the pushed-out planes overshoot; a side the hull already has is not added again
        for k in range(3):
            for sgn in (1.0, -1.0):
                n = tuple(sgn if j == k else 0.0 for j in range(3))
                e = max(sgn * p[k] for p in pts) + radius
                if not any(_dot(n, m) > 0.9999 and abs(e - f) < TOL for m, f in hull):
                    hull.append((n, e))
        out.append((mats[mat], hull))
    return out, nodes


# --- geometry: hulls to faces


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _clip(poly, n, e, keep_below=True):
    """Sutherland-Hodgman: the part of poly with n . p <= e (or >= e)."""
    out = []
    sgn = 1.0 if keep_below else -1.0
    for k, p in enumerate(poly):
        q = poly[k - 1]
        dp, dq = sgn * (_dot(n, p) - e), sgn * (_dot(n, q) - e)
        if dq <= 0.0:
            if dp <= 0.0:
                out.append(p)
            else:
                t = dq / (dq - dp)
                out.append(tuple(q[i] + t * (p[i] - q[i]) for i in range(3)))
        elif dp <= 0.0:
            t = dq / (dq - dp)
            out.append(tuple(q[i] + t * (p[i] - q[i]) for i in range(3)))
            out.append(p)
    return out


def _area(poly):
    s = (0.0, 0.0, 0.0)
    for k in range(1, len(poly) - 1):
        c = _cross(tuple(poly[k][i] - poly[0][i] for i in range(3)), tuple(poly[k + 1][i] - poly[0][i] for i in range(3)))
        s = (s[0] + c[0], s[1] + c[1], s[2] + c[2])
    return 0.5 * math.sqrt(_dot(s, s))


def hull_faces(planes, reach=1000.0):
    """A convex hull's faces [(plane index, polygon)], each polygon counter-clockwise seen from outside."""
    out = []
    for i, (n, e) in enumerate(planes):
        a = min(range(3), key=lambda k: abs(n[k]))
        axis = tuple(1.0 if k == a else 0.0 for k in range(3))
        u = _cross(n, axis)
        lu = math.sqrt(_dot(u, u))
        u = tuple(x / lu for x in u)
        v = _cross(n, u)                               # (u x v = n: the square below winds round n)
        c = tuple(x * e for x in n)
        poly = [tuple(c[k] + reach * (su * u[k] + sv * v[k]) for k in range(3))
                for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for j, (m, f) in enumerate(planes):
            if j != i and poly:
                poly = _clip(poly, m, f + 1e-7)
        if len(poly) >= 3 and _area(poly) > 1e-6:
            out.append((i, poly))
    return out


def _box(polys):
    pts = [p for poly in polys for p in poly]
    return tuple(min(p[k] for p in pts) for k in range(3)), tuple(max(p[k] for p in pts) for k in range(3))


def outside(poly, n, e, hull):
    """The pieces of poly (on its hull's plane n . p = e) not inside the convex hull [(normal, offset)]: a piece in
    the hull, or back to back against one of its faces, is inside the piece; a face flush with one of its faces is
    not."""
    # (a hull face back to back with poly is left out, so what lies against it counts as inside)
    facing = [(m, f) for m, f in hull if not (_dot(m, n) < -0.999 and abs(f + e) < TOL)]
    inner = poly
    for m, f in facing:
        inner = _clip(inner, m, f - TOL)
        if len(inner) < 3:
            return [poly]                          # (no part inside: kept whole, not cut into pieces)
    if _area(inner) <= 1e-6:
        return [poly]
    keep, rest = [], poly                          # (cut at the planes themselves: no slivers along the overlap)
    for m, f in facing:
        if not rest:
            break
        out = _clip(rest, m, f, keep_below=False)
        if len(out) >= 3 and _area(out) > 1e-6:
            keep.append(out)
        rest = _clip(rest, m, f)
    return keep


def faces(parts):
    """[(material, [x, y, z, ...])]: a piece's outer surface from its hulls, in its own axes, outward by winding."""
    hulls = []
    for mat, planes in parts:
        hf = hull_faces(planes)
        if hf:
            hulls.append((mat, planes, hf, _box([p for _, p in hf])))
    out = []
    for a, (mat, planes, hf, _) in enumerate(hulls):
        for i, poly in hf:
            n, e = planes[i]
            pieces = [poly]
            lo, hi = _box([poly])
            for b, (_, other, _, (olo, ohi)) in enumerate(hulls):
                if b == a or any(lo[k] > ohi[k] + TOL or hi[k] < olo[k] - TOL for k in range(3)):
                    continue
                pieces = [q for p in pieces for q in outside(p, n, e, other)]
                if not pieces:
                    break
            for p in pieces:
                pts = []
                for v in p:
                    r = tuple(round(x, 3) + 0.0 for x in v)
                    if not pts or r != pts[-1]:
                        pts.append(r)
                if len(pts) > 1 and pts[0] == pts[-1]:
                    pts.pop()
                if len(pts) >= 3 and _area(pts) > 1e-5:
                    out.append((mat, [x for v in pts for x in v]))
    return out


def shape(parts, tag, polys=None):
    """The shape file entry (h4.json) of a piece: its box from its faces."""
    polys = faces(parts) if polys is None else polys
    if not polys:
        return None
    axis = [[v for _, flat in polys for v in flat[k::3]] for k in range(3)]
    lo, hi = [min(a) for a in axis], [max(a) for a in axis]
    return {"min": [math.floor(v * 1000 + 1e-6) / 1000 for v in lo], "max": [math.ceil(v * 1000 - 1e-6) / 1000 for v in hi],
            "material": parts[0][0], "tag": tag, "bound_r": 0.0, "bound_off": [0.0, 0.0, 0.0],
            "source": "physics_model"}


# --- the maps' Forge pieces


def is_forge(path):
    base = path.rsplit("\\", 1)[-1]
    return "\\forge\\" in path or base.startswith("fw_") or base.endswith("_sky")


def pieces(cf):
    """{name: (path, physics model path or None, parts, nodes)} of the map's Forge crates and scenery."""
    out = {}
    for i, path in enumerate(cf.names):
        group, addr = cf.tags[i]
        if group not in OBJECT_GROUPS or not addr or not path or not is_forge(path):
            continue
        name = path.rsplit("\\", 1)[-1]
        model = cf.ref(cf.tag_off(i) + 0x64, "hlmt")
        phmo = cf.ref(cf.tag_off(model) + 0x30, "phmo") if model is not None else None
        if phmo is None:
            out[name] = (path, None, [], set())
            continue
        try:
            parts, nodes = convex_parts(cf, phmo)
        except ValueError as e:
            print(f"  {name}: {e}; not read")          # (one odd piece does not stop the rest)
            continue
        out[name] = (path, cf.names[phmo].replace("\\", "/") + ".physics_model", parts, nodes)
    return out


def map_names():
    """The Halo 4 maps with a tag name list in maps/_shapes (the ones the bots play)."""
    return sorted(fn[len("h4_tags_"):-5] for fn in os.listdir(SHAPES) if fn.startswith("h4_tags_") and fn.endswith(".json"))


def read_maps(names):
    """{name: (map, path, physics model path, parts, nodes)}, the first map naming a piece winning."""
    found = {}
    for m in names:
        p = os.path.join(reach_tag_names.MCC or "", "halo4", "maps", m + ".map")
        if not os.path.exists(p):
            print(f"  {m}: no .map file, skipped")
            continue
        cf = CacheFile(p)
        for name, (path, phmo, parts, nodes) in pieces(cf).items():
            found.setdefault(name, (m, path, phmo, parts, nodes))
    return found


def load():
    with open(os.path.join(SHAPES, "h4.json"), encoding="utf-8") as f:
        shapes = json.load(f)
    with open(os.path.join(SHAPES, "h4_faces.json"), encoding="utf-8") as f:
        fcs = json.load(f)
    return shapes, fcs


def kit_twin(name, shapes):
    """The kit's own shape of a piece, or of its Forge Island twin (fw_x on the Forge canvases is fi_x on Forge
    Island), with the name it is filed under."""
    for n in (name, "fi_" + name[3:] if name.startswith("fw_") else None):
        s = shapes["shapes"].get(n) if n else None
        if s and not s.get("source"):
            return n, s
    return None, None


def check(found, shapes, fcs):
    """The pieces this reading has that the kit has too (or has as their Forge Island twin): their boxes side by
    side, and their up-facing area (the kit's collision models keep faces inside a piece, these hulls do not).
    Returns the worst box difference."""
    worst = 0.0
    for name in sorted(found):
        kn, kit = kit_twin(name, shapes)
        m, _path, phmo, parts, _nodes = found[name]
        if not kit or not parts:
            continue
        polys = faces(parts)
        s = shape(parts, phmo, polys)
        diff = max(abs(a - b) for a, b in zip(kit["min"] + kit["max"], s["min"] + s["max"]))
        worst = max(worst, diff)
        up = lambda ps: sum(_area([tuple(f[k:k + 3]) for k in range(0, len(f), 3)]) for _, f in ps
                            if _normal_z(f) > 0.7)
        twin = "" if kn == name else f" (kit: {kn})"
        print(f"  {name:45s} box off by {diff:6.3f}  floor area kit {up(fcs['faces'].get(kn, [])):8.2f} "
              f"here {up(polys):8.2f}{twin}")
    return worst


def _normal_z(flat):
    pts = [tuple(flat[k:k + 3]) for k in range(0, len(flat), 3)]
    s = (0.0, 0.0, 0.0)
    for k in range(1, len(pts) - 1):
        c = _cross(tuple(pts[k][i] - pts[0][i] for i in range(3)), tuple(pts[k + 1][i] - pts[0][i] for i in range(3)))
        s = (s[0] + c[0], s[1] + c[1], s[2] + c[2])
    n = math.sqrt(_dot(s, s))
    return s[2] / n if n else 0.0


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    names = [a for a in argv if not a.startswith("--")] or map_names()
    shapes, fcs = load()
    found = read_maps(names)
    if "--check" in flags:
        print(f"worst box difference: {check(found, shapes, fcs):.3f}")
        return 0
    add, none = {}, []
    for name, (m, path, phmo, parts, nodes) in sorted(found.items()):
        if name in shapes["shapes"] and not shapes["shapes"][name].get("source"):
            continue                               # (the kit's own shape stays)
        polys = faces(parts) if parts else []
        if not polys:
            none.append(name)
            continue
        add[name] = (m, shape(parts, phmo, polys), polys, nodes)
    for name, (m, s, polys, nodes) in add.items():
        note = "" if nodes <= {0} else f"  (bodies on nodes {sorted(nodes)}: placed at the root)"
        print(f"  {name:45s} {m:20s} {len(polys):4d} faces  {s['min']} .. {s['max']}{note}")
    print(f"{len(add)} pieces with shapes, {len(none)} without solid shapes: {', '.join(none)}")
    if "--list" in flags:
        return 0
    for name, (m, s, polys, nodes) in add.items():
        shapes["shapes"][name] = s
        fcs["faces"][name] = [[mat, flat] for mat, flat in polys]
    nc = shapes.setdefault("no_collision", [])
    nc.extend(n for n in none if n not in nc and n not in shapes["shapes"])
    if HOW not in shapes["how"]:
        shapes["how"] = shapes["how"].rstrip() + "\n" + HOW
    if HOW not in fcs["how"]:
        fcs["how"] = fcs["how"].rstrip() + "\n" + HOW
    with open(os.path.join(SHAPES, "h4.json"), "w", encoding="utf-8") as f:
        json.dump(shapes, f, indent=1)
    with open(os.path.join(SHAPES, "h4_faces.json"), "w", encoding="utf-8") as f:
        json.dump(fcs, f, separators=(",", ":"))
    print("wrote maps/_shapes/h4.json and h4_faces.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
