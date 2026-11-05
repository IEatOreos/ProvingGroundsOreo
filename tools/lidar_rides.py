"""Gravity lifts and man cannons read from the kits' tags, and where each one carries a player: ride links for LiDAR
runs (a live LiDAR match and the simulator), and the push the simulator applies to a body inside one.

Where the numbers come from (OBSERVED in the kits' XML exports, tool.exe export-tag-to-xml; Reach Aftship's
aftship_lift_xl: logs/tmp/gaps/pm):
  - the map's placements (maps/<map>/source/*scenario*.xml, as tools/map_features.py reads them): every crate, scenery,
    machine or control whose name says lift / man cannon (map_features.interact_kind), its position and rotation (yaw,
    pitch, roll, degrees);
  - its object tag -> "model" -> "physics_model" and "render model" (references by name: found in the kit's tags);
  - physics_model "phantom types": the push of a phantom volume: "marker name" (its direction), "direction acc" /
    "direction max vel" (along it), "axis acc" / "axis max vel" (toward the marker's axis); "materials" give each shape
    its phantom type; the shapes ("polyhedra") give their box ("aabb center", "aabb half extents", object frame);
  - render_model "marker groups": the marker's translation and rotation (quaternion i, j, k, w) and "direction"
    (1, 0, 0 with "has node relative direction"): the push direction in the object frame.
INFERRED (no tag says it): gravity acts inside a phantom too; the push is applied while the body's speed along the
direction is under its max (the axis pull the same toward the marker's line); the object frame is yaw about z, pitch
about y (nose up), roll about x; a body is inside when the point 0.3 u above its feet is in a shape's box (rotated with
the object). Checked against bot rides recorded in real matches (H4 Adrift / ca_warhouse: 4 rides of its two lifts:
solved landings 0.5-0.8 u off flat, 0.3-1.0 u lower; test_lidar_rides.py, the --check option here). Players drift
out of a lift with air control: each lift is solved hands off and steering 8 ways, every different landing a ride
("steer": the heading the bot holds in the air).

Games: Reach (HREK), Halo 3 (H3EK, then H3ODSTEK: the ODST kit carries the Halo 3 multiplayer objects), ODST, Halo 4
(H4EK), H2A (H2AMPEK). CE has no lifts or cannons; Halo 2 (H2EK) and Forge pieces are not read (UNKNOWN: H2's tag
layout for phantoms; a Forge layout's lifts come from its .mvar, not the scenario).

Out: maps/<map>/phantoms.json {objects: [{name, kind, pos, rot, shapes: [{center, axes, half, dir, marker, acc, vmax,
axis_acc, axis_vmax}]}], skipped: [...]} (world frame), built by `python -I tools/lidar_rides.py [maps...] [--all]`;
ride_links(map, T, phys) turns each into a ride link (take-off: the floor where you step in; landing: where the push
and then gravity put you down), found_by "map", sim_ok 1 (the simulator's own physics landed it), never saved into
lidar.json (Recorder.save leaves found_by "map" out).

usage: python -I lidar_rides.py [maps...] [--all] [--check]
"""
import glob
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

KITS = {"h3": ("H3EK", "H3ODSTEK"), "odst": ("H3ODSTEK",), "reach": ("HREK",), "h2a": ("H2AMPEK",), "h4": ("H4EK",)}
OBJ_EXTS = (".crate", ".scenery", ".machine", ".control")
FEET = 0.3               # u: the point above the feet tested for being inside a phantom (INFERRED)
DT = 1.0 / 30            # s: the ride solver's step
RIDE_MAX_S = 12.0        # s: a ride longer than this never came down: not a ride
MIN_GAIN = 1.0           # u up (or 3 u across): a push that moves you less is no ride
SAME_LAND = 3.0          # u: landings of one lift this close (and within 1 u of height) are one ride
_INDEX, _XML = {}, {}


def kit_dirs(game):
    from brain import paths
    return [k for k in (paths.kit(n) for n in KITS.get(game, ())) if k]


def index(kit):
    """{(name, ext): [tag path relative to tags/]} of a kit, built once (cached in logs/)."""
    if kit in _INDEX:
        return _INDEX[kit]
    cache = os.path.join(ROOT, "logs", "kit_index_" + os.path.basename(kit.rstrip("\\/")) + ".json")
    if os.path.exists(cache):
        idx = {tuple(k.split("|")): v for k, v in json.load(open(cache)).items()}
    else:
        idx, top = {}, os.path.join(kit, "tags")
        for root, _, files in os.walk(top):
            for f in files:
                stem, ext = os.path.splitext(f)
                if ext in OBJ_EXTS + (".model", ".physics_model", ".render_model"):
                    idx.setdefault((stem.lower(), ext), []).append(os.path.relpath(os.path.join(root, f), top))
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump({"|".join(k): v for k, v in idx.items()}, open(cache, "w"))
    _INDEX[kit] = idx
    return idx


def find(kit, name, ext, near=None):
    """A tag by name and extension, the one in (or nearest to) the folder `near` when several."""
    hits = index(kit).get((name.lower(), ext), [])
    if not hits:
        return None
    if near:
        d = os.path.dirname(near).lower()
        hits = sorted(hits, key=lambda h: (os.path.dirname(h).lower() != d, len(os.path.commonprefix([h.lower(), d])) * -1))
    return hits[0]


def export(kit, rel):
    """The tag as the kit's XML (ElementTree root), cached in logs/tag_xml."""
    key = (kit, rel)
    if key in _XML:
        return _XML[key]
    out = os.path.join(ROOT, "logs", "tag_xml", os.path.basename(kit.rstrip("\\/")), rel + ".xml")
    if not os.path.exists(out) or os.path.getsize(out) == 0:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        import killzones
        if not killzones.tool(kit, os.path.join(kit, "tags", rel), os.path.abspath(out)):
            _XML[key] = None
            return None
    try:                                             # (values like "<unavailable>" are not escaped in these exports)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", open(out, encoding="utf-8", errors="replace").read())
        text = re.sub(r'="([^"]*[<>][^"]*)"', lambda m: '="' + m.group(1).replace("<", "&lt;").replace(">", "&gt;") + '"', text)
        _XML[key] = ET.fromstring(text)
    except ET.ParseError:
        _XML[key] = None
    return _XML[key]


def fval(e, name):
    """A field's value among e's own children (not nested elements)."""
    f = next((x for x in e if x.tag == "field" and x.get("name") == name), None)
    return None if f is None else f.get("value")


def ref(e, name):
    """A tag reference's name: Reach exports the bare name, Halo 3 style kits (H2A, H4) "path\name,group"."""
    v = fval(e, name) if e is not None else None
    v = (v or "").split(",")[0].rsplit("\\", 1)[-1].strip()
    return v or None


def ffloat(e, name, default=0.0):
    v = fval(e, name)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def fvec(e, name):
    v = fval(e, name)
    return [float(a) for a in v.split(",")] if v else None


def bidx(v):
    """A block index field's value: Reach "3. name", Halo 3 style ",3" (-1: none). None if none."""
    m = re.match(r"\s*,?\s*(-?\d+)", v or "")
    return int(m.group(1)) if m and int(m.group(1)) >= 0 else None


def block(root, name):
    """The elements of a top-level block: Reach's <element>s right after its <field type="block">, or Halo 3 style
    XML's <block name=...> (H2A, H4)."""
    if root is None:
        return []
    b = next((x for x in root if x.tag == "block" and x.get("name") == name), None)
    if b is not None:
        return [x for x in b if x.tag == "element"]
    out, on = [], False
    for x in root:
        if x.tag == "field":
            if on:
                break
            on = x.get("name") == name and x.get("type") == "block"
        elif x.tag == "element" and on:
            out.append(x)
    return out


def qrot(q, v):
    """Rotate v by quaternion q (i, j, k, w)."""
    x, y, z, w = q
    u = np.array([x, y, z])
    v = np.asarray(v, float)
    return 2 * u.dot(v) * u + (w * w - u.dot(u)) * v + 2 * w * np.cross(u, v)


def euler(rot):
    """The object's rotation matrix from its placement (yaw, pitch, roll degrees: INFERRED order z, y up, x)."""
    y, p, r = (math.radians(a) for a in (list(rot) + [0, 0, 0])[:3])
    Rz = np.array([[math.cos(y), -math.sin(y), 0], [math.sin(y), math.cos(y), 0], [0, 0, 1]])
    Ry = np.array([[math.cos(p), 0, -math.sin(p)], [0, 1, 0], [math.sin(p), 0, math.cos(p)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(r), -math.sin(r)], [0, math.sin(r), math.cos(r)]])
    return Rz @ Ry @ Rx


def phantom_shapes(kits, name):
    """[{center, half, dir, marker, acc, vmax, axis_acc, axis_vmax}] in the object frame, or (None, why)."""
    for kit in kits:
        obj = next((find(kit, name, e) for e in OBJ_EXTS if find(kit, name, e)), None)
        if obj is None:
            continue
        root = export(kit, obj)
        model = ref(root, "model")
        mrel = find(kit, model, ".model", obj) if model else None
        mroot = export(kit, mrel) if mrel else None
        if mroot is None:
            return None, f"{name}: no model ({kit})"
        pm, rm = ref(mroot, "physics_model"), ref(mroot, "render model")
        prel = find(kit, pm, ".physics_model", mrel) if pm else None
        rrel = find(kit, rm, ".render_model", mrel) if rm else None
        proot = export(kit, prel) if prel else None
        rroot = export(kit, rrel) if rrel else None
        if proot is None:
            return None, f"{name}: no physics model (its push is elsewhere: BSP or collision)"
        types = block(proot, "phantom types")
        if not types:
            return None, f"{name}: physics model has no phantom types"
        mats = [(e.get("name"), bidx(fval(e, "phantom type"))) for e in block(proot, "materials")]
        markers = {}
        for g in block(rroot, "marker groups") if rroot is not None else []:
            m = next((x for x in g.iter("element") if x is not g), None)   # (its first marker)
            if m is not None:
                markers[fval(g, "name")] = (fvec(m, "translation") or [0, 0, 0], fvec(m, "rotation") or [0, 0, 0, 1],
                                            fvec(m, "direction") or [1, 0, 0])
        out = []
        for shape_block in ("polyhedra", "boxes", "pills", "spheres"):
            for e in block(proot, shape_block):
                mat = next((f.get("value") for f in e.iter("field") if f.get("name") == "material"), "") or ""
                mi = bidx(mat) if mat.lstrip().startswith(",") else                     next((k for k, (n, _) in enumerate(mats) if n == mat), None)   # (Reach: the material's name)
                ti = mats[mi][1] if mi is not None and mi < len(mats) else None
                if ti is None or ti >= len(types):
                    continue
                t = types[ti]
                if shape_block == "polyhedra":
                    c = next((f.get("value") for f in e.iter("field") if f.get("name") == "aabb center"), None)
                    h = next((f.get("value") for f in e.iter("field") if f.get("name") == "aabb half extents"), None)
                else:
                    c = next((f.get("value") for f in e.iter("field") if f.get("name") in ("translation", "center")), None)
                    h = next((f.get("value") for f in e.iter("field") if f.get("name") == "half extents"), None)
                    if h is None:                    # pill / sphere: its radius each way (and the pill's length)
                        rad = next((f.get("value") for f in e.iter("field") if f.get("name") == "radius"), None)
                        h = ",".join([rad] * 3) if rad else None
                if not c or not h:
                    continue
                mk = markers.get(fval(t, "marker name"))
                if mk is None:
                    continue
                d = qrot(mk[1], mk[2])
                out.append(dict(center=[float(a) for a in c.split(",")], half=[abs(float(a)) for a in h.split(",")],
                                dir=[float(a) for a in d / (np.linalg.norm(d) or 1)], marker=mk[0],
                                acc=ffloat(t, "direction acc"), vmax=ffloat(t, "direction max vel"),
                                axis_acc=ffloat(t, "axis acc"), axis_vmax=ffloat(t, "axis max vel"),
                                shape=shape_block, type=fval(t, "marker name")))
        if out:
            return out, None
        return None, f"{name}: phantom types but no shape with a marker"
    return None, f"{name}: no object tag in {', '.join(os.path.basename(k) for k in kits) or 'no kit'}"


def placements(map_name):
    """[(kind, name, pos, rot)] of every lift / man cannon placed in the map's scenario XML."""
    import map_features as F
    import reach_export as R
    d = os.path.join(ROOT, "maps", map_name, "source")
    xmls = [x for x in glob.glob(os.path.join(d, "*.xml"))
            if "scenario" in os.path.basename(x) and not (os.path.exists(x[:-4] + ".slim.xml") and not x.endswith(".slim.xml"))
            and not os.path.basename(x).endswith(".xml.xml")]
    out = []
    for x in xmls:
        for group, name, pos, e in F.from_xml(x):
            k = F.interact_kind(name)
            if k in ("lift", "launcher"):
                rot = R.fld(e, "rotation")
                out.append((k, name, list(pos), [float(a) for a in rot.split(",")] if rot else [0.0, 0.0, 0.0]))
    return out


def build(map_name):
    """maps/<map>/phantoms.json from the kits. Returns the dict."""
    import jumpphys as J
    game = J.game_of(map_name)
    kits = kit_dirs(game)
    objs, skipped, cache = [], [], {}
    for kind, name, pos, rot in placements(map_name):
        if name not in cache:
            cache[name] = phantom_shapes(kits, name) if kits else (None, f"{name}: no kit for {game}")
        shapes, why = cache[name]
        if shapes is None:
            skipped.append(why)
            continue
        R = euler(rot)
        P = np.array(pos)
        world = []
        for s in shapes:
            world.append(dict(s, center=[round(float(v), 4) for v in P + R @ np.array(s["center"])],
                              axes=[[round(float(v), 5) for v in R[:, k]] for k in range(3)],
                              dir=[round(float(v), 5) for v in R @ np.array(s["dir"])],
                              marker=[round(float(v), 4) for v in P + R @ np.array(s["marker"])]))
        objs.append(dict(kind=kind, name=name, pos=pos, rot=rot, shapes=world))
    out = dict(game=game, objects=objs, skipped=sorted(set(skipped)))
    path = os.path.join(ROOT, "maps", map_name, "phantoms.json")
    tmp = path + ".tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, path)
    return out


def load(map_name):
    p = os.path.join(ROOT, "maps", map_name.replace("\\", "/").partition("/")[0], "phantoms.json")
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return {}


def inside(shape, p):
    """Is p (a body's test point) in the shape's box (object-rotated)?"""
    c, r = shape["center"], shape.get("_r") or math.sqrt(sum(h * h for h in shape["half"]))
    if abs(p[0] - c[0]) > r or abs(p[1] - c[1]) > r or abs(p[2] - c[2]) > r:
        return False                                 # (far from it: the cheap test, every body every tick)
    d = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
    return all(abs(d[0] * a[0] + d[1] * a[1] + d[2] * a[2]) <= h for a, h in zip(shape["axes"], shape["half"]))


def push(shapes, p, v, dt):
    """The phantoms' push on a body with feet at p and velocity v (changed in place) over dt. True if any acts."""
    q = (p[0], p[1], p[2] + FEET)
    on = False
    for s in shapes:
        if not inside(s, q):
            continue
        on = True
        d = np.asarray(s["dir"])
        vd = v[0] * d[0] + v[1] * d[1] + v[2] * d[2]
        if vd < s["vmax"]:
            k = min(s["acc"] * dt, s["vmax"] - vd)
            for n in range(3):
                v[n] += d[n] * k
        if s["axis_acc"] > 0:                        # toward the marker's line
            r = np.asarray(q) - s["marker"]
            off = r - r.dot(d) * d
            n_ = float(np.linalg.norm(off))
            if n_ > 0.05:
                u = -off / n_
                vu = v[0] * u[0] + v[1] * u[1] + v[2] * u[2]
                if vu < s["axis_vmax"]:
                    k = min(s["axis_acc"] * dt, s["axis_vmax"] - vu, n_ / dt)
                    for n in range(3):
                        v[n] += u[n] * k
    return on


def all_shapes(data):
    out = [s for o in data.get("objects", []) for s in o["shapes"]]
    for s in out:
        s["_r"] = math.sqrt(sum(h * h for h in s["half"]))
    return out


def solve(T, ph, shapes, start, steer=None):
    """A body stepping in at start (on the floor), steering toward heading steer (unit [x, y]) with the game's air
    control while the push is off it (as players drift out of a lift onto a deck), or hands off (None): (landing
    [x, y, z], path, seconds, top z) or None."""
    import jumpphys as J
    J.prepare(T)
    p, v = [start[0], start[1], start[2] + 0.02], [0.0, 0.0, 0.0]
    path, t, top, pushed = [list(p)], 0.0, p[2], False
    while t < RIDE_MAX_S:
        if push(shapes, p, v, DT):
            pushed = True
        elif not pushed:
            return None                              # it never pushed: the step-in point is outside its volume
        elif steer is not None:                      # air control (lidar_sim Body.step's rule)
            dvx, dvy = steer[0] * ph.run - v[0], steer[1] * ph.run - v[1]
            dv = math.hypot(dvx, dvy)
            if dv > 1e-9:
                k = min(1.0, J.AIR_ACCEL * DT / dv)
                v[0] += dvx * k
                v[1] += dvy * k
        out, _ = J.air_step(T, ph, p, v, DT)
        t += DT
        top = max(top, p[2])
        if int(t / DT) % 3 == 0:
            path.append([round(float(c), 2) for c in p])
        if out == "void":
            return None
        if out == "land" and t > 0.2 and not any(inside(s, (p[0], p[1], p[2] + FEET)) for s in shapes):
            return [round(float(c), 2) for c in p], path + [[round(float(c), 2) for c in p]], round(t, 2), round(float(top), 2)
    return None


def step_in(T, obj):
    """Where a player steps into a lift or cannon: its lowest phantom box's middle, on the floor under it (the floor
    nearest below its bottom, up to 1.5 u under)."""
    from brain.core import Vec
    s = min(obj["shapes"], key=lambda s: s["center"][2] - abs(float(np.dot(s["half"], np.abs(np.array(s["axes"])[:, 2])))))
    bottom = s["center"][2] - abs(float(np.dot(s["half"], np.abs(np.array(s["axes"])[:, 2]))))
    x, y = s["center"][0], s["center"][1]
    if not T.inside(x, y):
        return None
    j, i = T._cell(Vec(x, y, bottom))
    f = T.lz[:, j, i]
    cand = [float(z) for z in f if np.isfinite(z) and bottom - 1.5 <= z <= bottom + 1.0]
    if not cand:
        return None
    return [x, y, max(cand)]


def ride_links(map_name, T, ph):
    """Every lift / man cannon of the map as a ride link (phantoms.json, solved with this game's physics)."""
    data = load(map_name)
    shapes = all_shapes(data)
    out = []
    for o in data.get("objects", []):
        a = step_in(T, o)
        if a is None:
            continue
        mine = []                                    # hands off, then steering 8 ways: each different landing a link
        for steer in [None] + [(math.cos(k * math.pi / 4), math.sin(k * math.pi / 4)) for k in range(8)]:
            r = solve(T, ph, shapes, a, steer)
            if r is None:
                continue
            land, path, air_s, top = r
            if land[2] - a[2] < MIN_GAIN and math.dist(land[:2], a[:2]) < 3 * MIN_GAIN:
                continue
            if any(math.dist(land[:2], q["land"][:2]) < SAME_LAND and abs(land[2] - q["land"][2]) < 1.0 for q in mine):
                continue
            mine.append(dict(kind="jump", ride=1, name=o["name"], take_off=[round(c, 2) for c in a], land=land,
                             runup=None, apex=top, air_s=air_s, path=path[::max(1, len(path) // 16)] + [land],
                             ways="one-way", found_by="map", human=0, bot_ok=0, bot_fail=0, sim_ok=1, t=0,
                             steer=[round(c, 3) for c in steer] if steer else None))
        out += mine
    return out


def check(map_name, T, ph):
    """The solved rides against the ride links bots and people made in real matches (lidar.json): [(recorded take-off,
    recorded landing, solved landing, flat miss, height miss)]."""
    from brain.maps import anchor_launches
    import lidar
    real = [k for k in anchor_launches(lidar.load(os.path.join(ROOT, "maps", map_name, "lidar.json")).get("links", []),
                                       lidar.load_features(map_name).get("features", [])) if k.get("ride")]
    shapes = all_shapes(load(map_name))
    out = []
    for k in real:
        r = solve(T, ph, shapes, k["take_off"])
        if r:
            out.append((k["take_off"], k["land"], r[0], round(math.dist(r[0][:2], k["land"][:2]), 2),
                        round(r[0][2] - k["land"][2], 2)))
        else:
            out.append((k["take_off"], k["land"], None, None, None))
    return out


def main():
    import jumpphys as J
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--all" in sys.argv:
        args = sorted(n for n in os.listdir(os.path.join(ROOT, "maps")) if J.game_of(n) in KITS
                      and os.path.isdir(os.path.join(ROOT, "maps", n, "source")))
    for m in args:
        d = build(m)
        n = sum(len(o["shapes"]) for o in d["objects"])
        line = f"{m}: {len(d['objects'])} lifts / cannons, {n} phantom shapes" + \
            (f"; skipped {len(d['skipped'])}: {'; '.join(d['skipped'][:4])}" if d["skipped"] else "")
        if "--check" in sys.argv or "--links" in sys.argv:
            from brain.maps import get_map, terrain
            T = J.prepare(terrain(get_map(m)))
            ph = J.Phys(J.game_of(m))
            links = ride_links(m, T, ph)
            line += f"; {len(links)} rides: " + ", ".join(f"{l['name']} {l['take_off']} -> {l['land']} ({l['air_s']} s)"
                                                         for l in links[:6])
            if "--check" in sys.argv:
                line += f"; against recorded rides: {check(m, T, ph)}"
        print(line, flush=True)


if __name__ == "__main__":
    main()
