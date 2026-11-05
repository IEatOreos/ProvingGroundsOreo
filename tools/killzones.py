"""Kill zones and soft kill zones from the kits' map data -> maps/<map>/killzones.json (schema: brain/oob.py).

Where they are, per game (OBSERVED in the kits' XML exports and tool.exe's own tag help):
  CE      none: the CE MP scenarios have no trigger volumes (no such block in the kit's XML) and the CE BSP has no
          kill surfaces; a CE player dies by falling (bipeds.c: falling damage) and nothing else the map names
  H2      trigger volumes listed in "scenario kill triggers" (H2EK XML: block_index type="kill trigger volume")
  H3/ODST trigger volumes whose "kill trigger volume" field indexes the kill trigger block (",0"; ",-1" none), and the
          structure design tags' soft ceilings of type "soft kill" (BSP triangles)
  Reach, H2A, H4
          trigger volumes by NAME, as the kits' tag help says: "the name of the trigger volume specifies what kind of
          volume it is: 'kill' (plus '_soft' for soft kill volume), 'playerkill' (plus '_soft') for player only kill
          volume, 'safe_zone' (plus '_soft')" (HREK / H4EK / H2AMPEK tool.exe); the back index ("BAD: 0") where a tag
          kept it; placed boundary objects (kill_volume, soft_kill_volume, safe_volume, soft_safe_volume scenery /
          crates, with their multiplayer boundary); soft ceilings of type "soft kill" in the structure design tags
A trigger volume's position is its corner: the box spans position + forward * [0, extents.x] + left * [0, extents.y]
+ up * [0, extents.z], left = up x forward (H2 Lockout's kill_pit spans x -50..32, y -35..67 under a map round 0, 0).
A sector volume ("sector": a polygon of points; its extents x / y are stale) keeps its polygon ("points") and its box
round the points, from the lowest point minus its z sink to the highest plus extents.z. Reach writes the points in
world space, H2A / H4 relative to the volume's position (DERIVED from the spawns: taken as world, 232-1175 of the H2A /
H4 maps' spawns fell in their kill_soft sectors; relative, none; Reach's: none either way, its points sit beside its
position).
H3's safe_zone volumes are not listed in its safe zone block (empty in every H3 map): kept with a condition (left
out by brain/oob.py: what H3 does with them is UNKNOWN); the name rule makes them safe zones from Reach on.

usage: python -I tools/killzones.py [map ...] [--export]   (default: every map under maps/ with a source folder)
  --export   with the kits (tool.exe export-tag-to-xml only, no game files): maps whose source XML lacks the trigger
             volume block (H2A / H4 / ODST: slimmed) get their scenario and children again, cut to the blocks read
             here (source/kz_<tag>.kz.xml, kept; the full XML deleted); every H3 / ODST / Reach / H2A / H4 map gets its
             structure designs' soft kill ceilings (source/soft_kill.kz.json)
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
MAPS = os.path.join(ROOT, "maps")
TV, KILL, SAFE = "trigger volumes", "scenario kill triggers", "scenario safe zone triggers"
PLACED = ("scenery", "crates")
PALETTES = ("scenery palette", "crate palette")
BOUNDARY = {"kill_volume": "hard", "soft_kill_volume": "soft", "safe_volume": "safe", "soft_safe_volume": "soft_safe"}
WANT = {TV, KILL, SAFE, "child scenarios"} | set(PLACED) | set(PALETTES)
KITS = {"h2": "H2EK", "h3": "H3EK", "odst": "H3ODSTEK", "reach": "HREK", "h2a": "H2AMPEK", "h4": "H4EK"}
NAMED = ("reach", "h2a", "h4")              # the games whose tool names a trigger volume's kind by its name
SKIP_CHILD = ("airprobe", "audio", "decorator", "deco", "_fx", "lighting", "cinematic", "effects")


def game_of(m):
    g = m.split("_", 1)[0] if "_" in m else "ce"
    return g if g in KITS else "ce"


def slices(path, names=WANT):
    """{block name: its XML text} of the top-level blocks named, streamed (a scenario XML can be GBs). Three
    styles: H2EK (tab, <block name=..>), Halo 3 style (4 spaces, <block name=.. value=|count=..>), Reach (4 spaces,
    <field name=.. type="block"/> then its <element>s as siblings up to the next top-level field)."""
    out, cur, buf = {}, None, []
    with open(path, "rb") as f:
        for raw in f:
            line = raw.decode("utf-8", "replace")
            top = line.startswith(("\t<", "    <")) and not line.startswith(("\t\t", "     "))
            if cur is not None and top:
                if cur[1] == "block" and line.lstrip().startswith("</block>"):
                    out[cur[0]], cur = "".join(buf), None
                    continue
                if cur[1] == "reach" and line.lstrip().startswith("<field"):
                    out[cur[0]], cur = "".join(buf), None
            if cur is None and top:
                m = re.match(r'\s*<block name="([^"]*)"', line) or \
                    re.match(r'\s*<field name="([^"]*)" value="\d+" type="block"/>', line)
                if m and m.group(1) in names:
                    cur, buf = (m.group(1), "block" if line.lstrip().startswith("<block") else "reach"), []
                continue
            if cur is not None:
                buf.append(line)
    if cur is not None:
        out[cur[0]] = "".join(buf)
    return out


def elements(text):
    """The block's top-level elements (tool.exe's XML is not always valid: cleaned as reach_export.parse)."""
    text = text.replace("<unknown>", "unknown")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r'="([^"]*)"', lambda m: '="%s"' % re.sub(r"&(?![a-z]+;|#)", "&amp;", m.group(1))
                  .replace("<", "&lt;").replace(">", "&gt;"), text)
    return [e for e in ET.fromstring("<r>" + text + "</r>") if e.tag == "element"]


def fields(e):
    """{field name: value} of an element's fields at any depth (the first wins: a volume's own position comes before
    its sector points'); H2EK block_index fields by their type ("kill trigger volume", "trigger volume")."""
    d = {}
    for x in e.iter():
        if x is e or x.tag == "element":
            continue
        if x.tag == "block_index":
            d.setdefault(x.get("type"), x.get("index"))
        elif x.tag == "field":
            v = x.get("value")
            d.setdefault(x.get("name"), (x.text or "").strip() if v is None else v)
    return d


def index(v):
    """A block index as tool.exe writes it: "3", ",3", "BAD: 3", "NONE" -> int, -1 for none."""
    m = re.search(r"(-?\d+)\s*$", v or "")
    return int(m.group(1)) if m else -1


def vec(s):
    return [float(v) for v in (s or "0,0,0").split(",")]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def euler_axes(yaw, pitch, roll):
    """forward, up of a placed object's rotation (degrees: yaw about z, then pitch, roll)."""
    y, p, r = (math.radians(v) for v in (yaw, pitch, roll))
    fwd = [math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p)]
    left0 = [-math.sin(y), math.cos(y), 0.0]
    up0 = cross(fwd, left0)
    up = [u * math.cos(r) - lf * math.sin(r) for u, lf in zip(up0, left0)]
    return fwd, up


def rnd(v, n=3):
    return [round(x, n) for x in v]


def named_kind(name):
    """Reach / H2A / H4: a trigger volume's kind by its name (the kits' tag help), None if it is no kill volume."""
    n = name.lower().strip()
    if n.startswith(("kill", "playerkill")):
        return "soft" if "_soft" in n else "hard"
    if n.startswith("safe_zone"):
        return "soft_safe" if "_soft" in n else "safe"
    return None


def trigger_volumes(blocks, game):
    """The kill (and safe) trigger volumes of a scenario's blocks as schema volumes."""
    if TV not in blocks:
        return []
    ref = lambda e: index(fields(e).get("trigger volume") or fields(e).get("short block index"))  # noqa: E731
    kills = {ref(e) for e in elements(blocks.get(KILL, ""))}
    safes = {ref(e) for e in elements(blocks.get(SAFE, ""))}
    out = []
    for i, e in enumerate(elements(blocks[TV])):
        f = fields(e)
        name = f.get("name") or e.get("name") or ""
        if game in NAMED:        # by name only: the back index also sits on garbage / AI volumes there (Invasion)
            kind = named_kind(name)
        elif i in kills or index(f.get("kill trigger volume")) >= 0:
            kind = "soft" if "_soft" in name.lower() else "hard"
        else:
            kind = ("soft_safe" if "_soft" in name.lower() else "safe") if i in safes or \
                name.lower().startswith("safe_zone") else None
        if kind is None:
            continue
        cond = None
        if kind in ("safe", "soft_safe") and game not in NAMED and i not in safes:
            cond = "safe_zone volume not in the safe zone block (H2 / H3 engine): what it does is UNKNOWN"
        fwd, up = vec(f.get("forward") or "1,0,0"), vec(f.get("up") or "0,0,1")
        pos, ext = vec(f.get("position")), vec(f.get("extents"))
        v = dict(kind=kind, shape="box", source="scenario", label=name)
        pts = [vec(p.get("value")) for p in e.iter("field") if p.get("name") == "position"][1:]
        if game in ("h2a", "h4"):  # their sector points are relative to the volume's position (Reach's are world:
            pts = [[p[k] + pos[k] for k in range(3)] for p in pts]   # tested against the maps' spawns)
        if (f.get("type") or "").startswith("sector") and len(pts) >= 3:
            lo = [min(p[k] for p in pts) for k in range(3)]
            hi = [max(p[k] for p in pts) for k in range(2)] + [max(p[2] for p in pts) + ext[2]]
            lo[2] -= float(f.get("z sink") or 0)
            v.update(center=rnd([(a + b) / 2 for a, b in zip(lo, hi)]), size=rnd([b - a for a, b in zip(lo, hi)]),
                     points=[rnd(p[:2]) for p in pts])
        else:
            left = cross(up, fwd)
            v.update(center=rnd([pos[k] + (fwd[k] * ext[0] + left[k] * ext[1] + up[k] * ext[2]) / 2 for k in range(3)]),
                     size=rnd(ext))
            if rnd(fwd) != [1, 0, 0] or rnd(up) != [0, 0, 1]:
                v["rotation"] = dict(forward=rnd(fwd, 5), up=rnd(up, 5))
        if cond:
            v["condition"] = cond
        out.append(v)
    return out


def boundary_objects(blocks):
    """Placed kill / safe boundary objects (Reach, H2A, H4) as schema volumes."""
    out = []
    for kind, palette in zip(PLACED, PALETTES):
        pal = [(fields(e).get("name") or e.get("name") or "") for e in elements(blocks.get(palette, ""))]
        for e in elements(blocks.get(kind, "")):
            f = fields(e)
            t = (f.get("type") or "").strip()
            if re.match(r"^(,|BAD|NONE|-?\d)", t):             # Halo 3 style: the palette's index
                i = index(t)
                t = pal[i] if 0 <= i < len(pal) else ""
            name = t.split(",")[0].rsplit("\\", 1)[-1].strip()
            if name not in BOUNDARY or "position" not in f:
                continue
            shape = (f.get("boundary shape") or "unused").split(",")[-1].strip().lower()
            w, ln = float(f.get("boundary width or radius") or 0), float(f.get("boundary box length") or 0)
            top, bot = float(f.get("boundary positive height") or 0), float(f.get("boundary negative height") or 0)
            pos = vec(f.get("position"))
            fwd, up = euler_axes(*(vec(f.get("rotation") or "0,0,0") + [0, 0, 0])[:3])
            if shape == "sphere":
                center, size = pos, [w, w, w]
            elif shape in ("cylinder", "box"):
                center = [pos[k] + up[k] * (top - bot) / 2 for k in range(3)]
                size = [w, w, top + bot] if shape == "cylinder" else [w, ln, top + bot]
            else:
                continue                                  # no boundary set: nothing the game tests
            v = dict(kind=BOUNDARY[name], shape=shape, center=rnd(center), size=rnd(size), source="scenario",
                     label=name)
            if rnd(fwd) != [1, 0, 0] or rnd(up) != [0, 0, 1]:
                v["rotation"] = dict(forward=rnd(fwd, 5), up=rnd(up, 5))
            if "hide unless" in (f.get("spawn flags") or ""):     # there only when the game type asks for it
                v["condition"] = f"game type: {f.get('megalo label') or 'its label'}"   # (Invasion's inv_gates)
            out.append(v)
    return out


def mark_spawn_holders(folder, vols):
    """A kill / soft kill volume over the map's own spawn points cannot be on in a match: the level's script toggles
    it (ODST sc130's kill_lobby_entry: the mission script's kill_volume_enable / disable): condition set."""
    sys.path.insert(0, ROOT)
    from brain import oob as O
    try:
        sp = [s["pos"] for s in json.load(open(os.path.join(folder, "objects.json"), encoding="utf-8"))["spawns"]]
    except (OSError, ValueError, KeyError):
        return
    if not sp:
        return
    import numpy as np
    P = np.asarray(sp, float) + [0, 0, 0.3]
    for v in vols:
        if v["kind"] in O.KILLS and "condition" not in v and O.contains(v, P).any():
            v["condition"] = f"holds {int(O.contains(v, P).sum())} of the map's spawn points: toggled by the level's script"


def soft_kill_ceilings(path):
    """[(name, [[v0, v1, v2], ...])] of a structure design XML's soft ceilings of type "soft kill"."""
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for part in re.split(r'name="\d+\. structure_soft_ceiling_block">', text)[1:]:
        m = re.search(r'name="type" value="([^"]*)"', part)
        if not m or m.group(1) != "soft kill":
            continue
        name = (re.search(r'name="name" value="([^"]*)"', part) or [None, ""])[1]
        vs = [vec(x) for x in re.findall(r'name="vertex[012]" value="([^"]*)"', part)]
        out.append((name, [[rnd(v) for v in t] for t in zip(vs[0::3], vs[1::3], vs[2::3])]))
    return out


def scenario_files(folder):
    """The map's scenario XMLs in its source folder (not the BSP's); the re-exported *.kz.xml when there are any."""
    src = os.path.join(folder, "source")
    if not os.path.isdir(src):
        return []
    names = sorted(f for f in os.listdir(src) if f.endswith(".xml") and not f.startswith(("bsp", "ordnance_")))
    kz = [f for f in names if f.endswith(".kz.xml")]
    return [os.path.join(src, f) for f in (kz or names)]


def has_tv(path):
    with open(path, "rb") as f:
        return any(b'name="trigger volumes"' in line for line in f)


def extract(folder):
    """(volumes, scenario files read) of a map folder."""
    vols, files, game = [], scenario_files(folder), game_of(os.path.basename(folder))
    for p in files:
        b = slices(p)
        vols += trigger_volumes(b, game) + boundary_objects(b)
    sk = os.path.join(folder, "source", "soft_kill.kz.json")
    if os.path.exists(sk):
        for design, name, tris in json.load(open(sk, encoding="utf-8"))["ceilings"]:
            xs = [v for t in tris for v in t]
            lo, hi = [min(v[k] for v in xs) for k in range(3)], [max(v[k] for v in xs) for k in range(3)]
            vols.append(dict(kind="soft", shape="plane", center=rnd([(a + b) / 2 for a, b in zip(lo, hi)]),
                             size=rnd([b - a for a, b in zip(lo, hi)]), triangles=tris, source="bsp",
                             label=f"{design}: soft ceiling {name or '(unnamed)'} (soft kill)"))
    return vols, files


_LEVELS = {}


def kit_level(m):
    """(kit folder, the scenario's folder under tags, its stem) of a map folder name, or None."""
    sys.path.insert(0, ROOT)
    from brain import paths
    g = game_of(m)
    kit = paths.kit(KITS[g]) if g in KITS else None
    if not kit:
        return None
    if kit not in _LEVELS:
        _LEVELS[kit] = {}
        for root, _, fs in os.walk(os.path.join(kit, "tags", "levels")):
            for f in fs:
                if f.endswith(".scenario"):
                    _LEVELS[kit].setdefault(f[:-9].lower(), root)
    stem = m.split("_", 1)[1].lower()
    root = _LEVELS[kit].get(stem)
    return (kit, root, stem) if root else None


def tool(kit, tag_file, out):
    subprocess.run([os.path.join(kit, "tool.exe"), "export-tag-to-xml", tag_file, out], capture_output=True,
                   text=True, errors="replace", cwd=kit)
    return os.path.exists(out) and os.path.getsize(out) > 0


def kit_export(folder):
    """The scenario (and its children) again from the kit, cut to WANT into source/kz_<tag>.kz.xml."""
    lv = kit_level(os.path.basename(folder))
    if lv is None:
        print(os.path.basename(folder), ": no kit scenario")
        return []
    kit, root, stem = lv
    src, written = os.path.join(folder, "source"), []
    todo, seen = [os.path.join(root, stem + ".scenario")], set()
    while todo:
        t = todo.pop(0)
        if t.lower() in seen:
            continue
        seen.add(t.lower())
        base = os.path.basename(t)[:-9]
        full = os.path.join(src, "kz_" + base + ".xml")
        if not tool(kit, t, full):
            print(os.path.basename(folder), "export failed:", t)
            continue
        b = slices(full)
        out = full[:-4] + ".kz.xml"
        with open(out, "w", encoding="utf-8") as o:     # each block read here as its own top-level block
            o.write('<?xml version="1.0"?>\n<tag>\n')
            for name, text in b.items():
                if name == "child scenarios":
                    for e in elements(text):
                        c = next((x.get("value") for x in e.iter("field") if x.get("type") == "tag reference"), "")
                        c = (c or "").split(",")[0].strip()
                        # ponytail: lighting / audio / fx / decorator children skipped (a decorator child is GBs of
                        # XML); a kill volume placed in one of them would be missed
                        if c and not any(k in c.rsplit("\\", 1)[-1].lower() for k in SKIP_CHILD):
                            todo.append(os.path.join(kit, "tags", c + ".scenario"))
                    continue
                o.write('    <block name="%s">\n%s    </block>\n' % (name, text))
            o.write("</tag>\n")
        os.remove(full)
        written.append(out)
    return written


def design_export(folder):
    """The soft kill ceilings of the structure design tags beside the map's scenario -> source/soft_kill.kz.json."""
    lv = kit_level(os.path.basename(folder))
    if lv is None:
        return None
    kit, root, stem = lv
    ceilings, designs = [], sorted(f for f in os.listdir(root) if f.endswith(".structure_design"))
    with tempfile.TemporaryDirectory() as tmp:
        for d in designs:
            out = os.path.join(tmp, d + ".xml")
            if tool(kit, os.path.join(root, d), out):
                ceilings += [[d[:-17], n, tris] for n, tris in soft_kill_ceilings(out)]
    p = os.path.join(folder, "source", "soft_kill.kz.json")
    json.dump({"designs": [d[:-17] for d in designs], "ceilings": ceilings}, open(p, "w", encoding="utf-8"))
    return p


def write(folder, vols):
    p = os.path.join(folder, "killzones.json")
    with open(p, "w", encoding="utf-8") as f:     # one volume per line (a soft ceiling's triangles on its own)
        f.write('{"volumes": [\n' + ",\n".join(json.dumps(v) for v in vols) + "\n]}\n")
    return p


def main(argv):
    export = "--export" in argv
    names = [a for a in argv if not a.startswith("--")] or sorted(
        m for m in os.listdir(MAPS) if os.path.isdir(os.path.join(MAPS, m, "source")))
    for m in names:
        folder = os.path.join(MAPS, m)
        if export and game_of(m) != "ce":
            fs = scenario_files(folder)
            if game_of(m) != "h2" and not any(has_tv(p) or p.endswith(".kz.xml") for p in fs):
                kit_export(folder)
            if game_of(m) not in ("h2",):
                design_export(folder)
        vols, files = extract(folder)
        mark_spawn_holders(folder, vols)
        write(folder, vols)
        kinds = {}
        for v in vols:
            k = v["kind"] + ("/bsp" if v["source"] == "bsp" else "")
            kinds[k] = kinds.get(k, 0) + 1
        print(f"{m}: {len(vols)} {kinds} from {len(files)} xml" +
              ("" if any(has_tv(p) for p in files) else " (no trigger volume block)"), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
