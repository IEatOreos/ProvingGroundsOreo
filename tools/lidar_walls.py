"""Three kinds of wall from the maps' own collision data: solid (blocks walking, sight and shots), window (glass: blocks
walking, lets sight through, stops shots unless it breaks) and fence (grates, chain-link, railings, mesh, bars: blocks
walking, lets sight and shots through: the owner, Nov 4: "fences still act as walls but can be shot through").

Where it comes from (OBSERVED in the kits' XML exports of each map's .scenario_structure_bsp, tool.exe
export-tag-to-xml):
  - "collision materials": each collision surface's material is a shader by name ("render method" Halo 3 / ODST / H4 /
    H2A, "shader" Reach and CE, "new shader" Halo 2) and, in CE, its tag group (sgla: shader_transparent_glass);
  - the collision BSP ("surfaces": material, flags, "breakable surface"; "edges"; "vertices") of the structure and of
    every instanced geometry definition, placed by "instanced geometry instances" (scale, forward, left, up, position,
    instance definition; CE has none);
  - a surface's kind by its shader's name (brain/terrain.py wall_kind: glass / window -> window unless it names a light,
    metal, frame, screen or opacity; fence / grate / chain(link) / mesh / rail(ing) / bars / grill / lattice / cage ->
    fence; else solid). Upright faces are walls (window, fence), flat ones decks (window_floor: a glass floor,
    fence_floor: a grate deck). A window surface breaks with the breakable flag (bit 3 / "breakable") or, outside CE,
    a breakable surface index.
INFERRED (no field says it; the owner's rule and the game's collision): a window stops shots unless it breaks (its
collision surface is there for projectiles too); a fence lets shots through (the owner). UNKNOWN: projectile
material responses per weapon (some rounds over-penetrate); render-only fences (no collision) were never walls.

Games: CE (HCEEK), Halo 2 (H2EK), Halo 3 (H3EK, the ODST kit for maps H3EK lacks), ODST, Reach (HREK), Halo 4 (H4EK),
H2A (H2AMPEK), plus each map's glass.json (the map pack's render glass, H2A / H4 / ODST) as windows and, for Halo 4 and
H2A (their kits' exports lack the instanced geometry's collision), the render fences of MCC's .map (the map tools' bsp2obj
--fence: render_fences). Forge pieces:
brain/terrain.py piece_wall_kinds (their faces' materials).

Out: maps/<map>/wall_kinds.json {cell: 0.25, source, shaders {name: kind}, counts, window [[x4, y4, lo, hi, breaks]],
fence [[x4, y4, lo, hi]], window_floor, fence_floor} (quarter-unit cells, the height range the faces cover, inside the
map's heightmap), read by brain/terrain.py (Terrain.set_wall_kinds: sight and shot lines) and tools/lidar.py (LiDAR
paints them as their own kinds, the view shows them).

usage: python -I lidar_walls.py <map> [<map> ...] [--keep-xml]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from brain.terrain import face_cells, is_flat, kinds_out, wall_kind as kind_of  # noqa: E402

KITS = {"h3": ("H3EK", "H3ODSTEK"), "odst": ("H3ODSTEK",), "reach": ("HREK",), "h4": ("H4EK",), "h2a": ("H2AMPEK",),
        "ce": ("HCEEK",), "h2": ("H2EK",)}
LINE = re.compile(r'^( *)<(block|field|element)\b(.*)$')
ATTR = re.compile(r'(\w+)="([^"]*)"')


def bidx(v):
    m = re.search(r"(-?\d+)\s*$", v or "")    # (",0"; Reach: "BAD: 0", the index all the same)
    return int(m.group(1)) if m else -1


def parse(xml):
    """Collision materials, the collision sets {(owner, n): (surfaces, edges, vertices)} (owner -1: the structure, k: the
    k-th instanced geometry definition) and the instances [(definition, scale, forward, left, up, position)], streamed
    line by line (a map's XML is 0.4-1.4 GB). Both export styles: <block name=...> (Halo 3, H4, H2A) and
    <field ... type="block"/> followed by its elements (Reach)."""
    block_at, path = {}, []                       # indent -> the block whose elements sit there; open elements
    mats, sets, inst = [], {}, []
    cur = {}
    count = {}
    for line in open(xml, encoding="utf-8", errors="replace"):
        m = LINE.match(line)
        if not m:
            continue
        ind, tag, rest = len(m.group(1)), m.group(2), m.group(3)
        a = dict(ATTR.findall(rest))
        if tag == "block":
            block_at[ind + 4] = a.get("name", "")
            continue
        if tag == "field" and a.get("type") == "block":
            block_at[ind] = a.get("name", "")
            continue
        while path and path[-1][0] >= ind:
            path.pop()
        if tag == "element":
            blk = block_at.get(ind, "")
            ename = a.get("name", "")
            path.append((ind, blk, int(a.get("index", -1)), ename))
            owner = next((p[2] for p in path if p[1] == "instanced geometries definitions"), -1)
            if ename.endswith("surfaces_block") and blk == "surfaces":
                if int(a.get("index", -1)) == 0:
                    count[owner] = count.get(owner, -1) + 1
                key = (owner, count.get(owner, 0))
                sets.setdefault(key, ([], [], []))[0].append(cur := {})
            elif ename.endswith("edges_block") and blk == "edges":
                key = (owner, count.get(owner, 0))
                sets.setdefault(key, ([], [], []))[1].append(cur := {})
            elif ename.endswith("vertices_block") and blk == "vertices":
                key = (owner, count.get(owner, 0))
                sets.setdefault(key, ([], [], []))[2].append(cur := {})
            elif blk == "collision materials":
                mats.append(cur := {})
            elif blk == "instanced geometry instances":
                inst.append(cur := {})
            else:
                cur = None
            continue
        if cur is None or not path or path[-1][0] >= ind:
            continue
        name, val = a.get("name"), a.get("value")
        if name is not None:
            cur.setdefault(name, val)
    return mats, sets, inst


CE_TAG = re.compile(r'<(block|element|field|tag_reference|block_index)\b([^>]*?)(/?)>([^<]*)(</\w+>)?')
COLL_BLOCKS = ("surfaces", "edges", "vertices")


def parse_tabs(xml):
    """The CE and Halo 2 kits' export (HCEEK / H2EK tool.exe: tabs, values as element text): the same (mats, sets,
    inst) as parse. The structure's set is the "collision bsp" block's; Halo 2's instanced geometry definitions carry
    their own surfaces / edges / vertices. A material's shader is "shader" (CE) or "new shader" (H2), its "type" the
    shader's tag group (CE sgla: shader_transparent_glass)."""
    stack, mats, sets, inst = [], [], {}, []      # stack: [block name, its open element index]
    cur, pend = None, None
    for line in open(xml, encoding="utf-8", errors="replace"):
        t = line.strip()
        if t == "</block>":
            stack.pop() if stack else None
            cur = None
            continue
        if pend is not None and t and not t.startswith("<"):
            if cur is not None:
                cur[pend] = t
            pend = None
            continue
        m = CE_TAG.match(t)
        if not m:
            continue
        tag, a = m.group(1), dict(ATTR.findall(m.group(2)))
        if tag == "block":
            stack.append([a.get("name", ""), -1])
            cur = None
            continue
        if not stack:
            continue
        top = stack[-1][0]
        names = [b[0] for b in stack]
        if tag == "element":
            stack[-1][1] = int(a.get("index", -1))
            cur = None
            if top == "collision materials" and len(stack) == 1:
                mats.append(cur := {})
            elif top == "instanced geometry instances" and len(stack) == 1:
                inst.append(cur := {})
            elif top in COLL_BLOCKS and len(stack) == 2 and names[0] in ("collision bsp", "instanced geometries definitions"):
                owner = -1 if names[0] == "collision bsp" else stack[0][1]
                sets.setdefault((owner, 0), ([], [], []))[COLL_BLOCKS.index(top)].append(cur := {})
            continue
        if cur is None:
            continue
        if tag == "tag_reference":
            if a.get("name") in ("shader", "new shader") and m.group(4):
                cur.update(shader=m.group(4), type=a.get("type", ""))
        elif tag == "block_index":
            cur[a.get("type", "")] = a.get("index", "-1")
        elif tag == "field":
            if m.group(5):
                cur[a.get("name")] = m.group(4)
            else:
                pend = a.get("name")
    return mats, sets, inst


def vec(v):
    return [float(x) for x in v.split(",")] if v else [0.0, 0.0, 0.0]


def rings(surfaces, edges, vertices):
    """Each surface's polygon by its edge ring (tools/object_shapes.py faces): [(surface dict, [(x, y, z)])]."""
    V = [vec(v.get("point")) for v in vertices]
    E = [(int(e["start vertex"]), int(e["end vertex"]), int(e["forward edge"]), int(e["reverse edge"]),
          int(e["left surface"])) for e in edges if "start vertex" in e]
    out = []
    for si, s in enumerate(surfaces):
        ring, seen, e = [], set(), int(s.get("first edge", -1))
        while 0 <= e < len(E) and e not in seen:
            seen.add(e)
            sv, ev, fe, re_, left = E[e]
            k = sv if left == si else ev
            if 0 <= k < len(V):
                ring.append(V[k])
            e = fe if left == si else re_
        if len(ring) >= 3:
            out.append((s, ring))
    return out


def classify(xml):
    """{shaders, window cells, fence cells, counts} of one structure BSP XML."""
    with open(xml, encoding="utf-8", errors="replace") as f:
        ce = "\t<" in f.read(400)
    mats, sets, inst = (parse_tabs if ce else parse)(xml)
    names = [m.get("render method") or m.get("shader") or "" for m in mats]
    kinds = ["window" if m.get("type") == "sgla" else kind_of(n) for m, n in zip(mats, names)]
    out = {k: {} for k in ("window", "fence", "window_floor", "fence_floor")}
    counts = dict(window=0, fence=0, solid=0)
    place = {-1: [(1.0, [1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, 0])]}
    for it in inst:
        d = bidx(it.get("instance definition"))
        place.setdefault(d, []).append((float(it.get("scale") or 1), vec(it.get("forward")), vec(it.get("left")),
                                        vec(it.get("up")), vec(it.get("position"))))
    for (owner, _), (S, E, V) in sets.items():
        for s, ring in rings(S, E, V):
            mi = int(s.get("material", -1) or -1)
            k = kinds[mi] if 0 <= mi < len(kinds) else None
            counts[k or "solid"] += 1
            if k is None:
                continue
            fl = (s.get("flags") or "")
            # (CE: every surface says breakable surface 0; the tab exports' flag bit 3 says it breaks)
            brk = (not ce and int(s.get("breakable surface", -1) or -1) >= 0) or "breakable" in fl or \
                (fl.strip().isdigit() and int(fl) & 8)
            for sc, f, l, u, p in place.get(owner, []):
                w = [[p[n] + sc * (q[0] * f[n] + q[1] * l[n] + q[2] * u[n]) for n in range(3)] for q in ring]
                face_cells(w, out[k + "_floor" if is_flat(w) else k], brk and k == "window")
    return dict(shaders={n.split(",")[0].rsplit("\\", 1)[-1]: k for n, k in zip(names, kinds) if k}, **kinds_out(out),
                counts=counts, instances=len(inst), sets=len(sets))


def bsp_tags(map_name):
    """The map's structure BSP tags in its kit: [(kit, tag path relative to tags)]."""
    import jumpphys as J
    from brain import paths
    game = J.game_of(map_name)
    stem = map_name.split("_", 1)[1] if "_" in map_name else map_name
    out = []
    for kn in KITS.get(game, ()):
        kit = paths.kit(kn)
        if not kit:
            continue
        walk = [(root, files) for top in ("levels", "scenarios") for root, _, files in os.walk(os.path.join(kit, "tags", top))]
        scen = None
        for root, files in walk:
            for f in files:
                if f.endswith(".scenario_structure_bsp") and (f[:-len(".scenario_structure_bsp")].lower() == stem.lower()
                                                               or os.path.basename(root).lower() == stem.lower()):
                    out.append((kit, os.path.relpath(os.path.join(root, f), os.path.join(kit, "tags"))))
                if f.lower() == stem.lower() + ".scenario":
                    scen = os.path.join(root, f)
        if not out and scen:                      # a map on another level's structure (Reach Firefight on the
            names = scenario_bsps(kit, scen)      # campaign's): the scenario's own "structure bsps"
            out = [(kit, os.path.relpath(os.path.join(root, f), os.path.join(kit, "tags"))) for root, files in walk
                   for f in files if f.endswith(".scenario_structure_bsp")
                   and f[:-len(".scenario_structure_bsp")].lower() in names]
        if out:
            break
    return out


RENDER_GAMES = {"h4": "halo4", "h2a": "groundhog"}   # games whose kit export has no instanced collision: their .map


def render_fences(map_name):
    """The shoot-through triangles of the map's render geometry (the map tools' bsp2obj --fence on MCC's .map, a fence /
    grate / railing material by name), for the games whose kits' BSP export lacks the instanced geometry's collision
    (Halo 4, H2A: OBSERVED, ca_port's export has 1590 collision surfaces and no instanced geometry definitions).
    [] when the game is another, the tool or the .map is missing."""
    import subprocess
    import tempfile
    import jumpphys as J
    from brain import paths
    game = J.game_of(map_name)
    exe = paths.map_tool("bsp2obj")
    if game not in RENDER_GAMES or not exe:
        return []
    mp = os.path.join(paths.mcc(), RENDER_GAMES[game], "maps", map_name[len(game) + 1:] + ".map")
    if not os.path.exists(mp):
        return []
    tmp = tempfile.mkdtemp(prefix="fence_")
    txt = os.path.join(tmp, "fence.txt")
    subprocess.run([exe, mp, os.path.join(tmp, "mesh.obj"), "--fence", txt], capture_output=True, text=True)
    out = []
    for line in open(txt) if os.path.exists(txt) else ():
        v = [float(x) for x in line.split()]
        if len(v) == 9:
            out.append([v[0:3], v[3:6], v[6:9]])
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    return out


def scenario_bsps(kit, scen):
    """The structure BSP names a .scenario uses ("structure bsps": Reach value="m10_000", Halo 3 a tag path)."""
    import killzones
    xml = os.path.join(ROOT, "logs", "tag_xml", os.path.basename(kit.rstrip("\\/")),
                       os.path.relpath(scen, os.path.join(kit, "tags")) + ".xml")
    os.makedirs(os.path.dirname(xml), exist_ok=True)
    tag = os.path.relpath(scen, os.path.join(kit, "tags")) if os.path.basename(kit.rstrip("\\/")).upper() == "HCEEK" else scen
    if not (os.path.exists(xml) and os.path.getsize(xml)) and not killzones.tool(kit, tag, os.path.abspath(xml)):
        return set()
    out = set()
    for line in open(xml, encoding="utf-8", errors="replace"):
        if 'name="structure bsp"' in line:
            m = re.search(r'value="([^"]+)"', line) or re.search(r'>([^<]+)<', line)
            if m and m.group(1).strip():
                out.add(m.group(1).strip().replace("/", "\\").rsplit("\\", 1)[-1].lower())
    return out


def build(map_name, keep=False):
    import killzones
    tags = bsp_tags(map_name)
    total = dict(shaders={}, window={}, fence={}, window_floor={}, fence_floor={}, counts=dict(window=0, fence=0, solid=0),
                 source=[])
    for kit, rel in tags:
        out = os.path.join(ROOT, "logs", "tag_xml", os.path.basename(kit.rstrip("\\/")), rel + ".xml")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        # (the CE kit's tool takes the tag path under tags, the others the full path; a failed export leaves an empty
        # file, which is no cache)
        tag = rel if os.path.basename(kit.rstrip("\\/")).upper() == "HCEEK" else os.path.join(kit, "tags", rel)
        if not (os.path.exists(out) and os.path.getsize(out)) and not killzones.tool(kit, tag, os.path.abspath(out)):
            if os.path.exists(out):
                os.remove(out)
            print(f"{map_name}: {kit} could not export {rel}", flush=True)
            continue
        r = classify(out)
        total["source"].append(os.path.basename(kit.rstrip("\\/")) + ":" + rel)
        total["shaders"].update(r["shaders"])
        for k in ("window", "fence", "window_floor", "fence_floor"):
            for c in r[k]:
                total[k][(c[0], c[1])] = c
        for k, v in r["counts"].items():
            total["counts"][k] += v
        if not keep:
            os.remove(out)
    try:                                          # the map pack's render glass (H2A / H4 / ODST): windows too
        for x, y, lo, hi in json.load(open(os.path.join(ROOT, "maps", map_name, "glass.json"))).get("cells", []):
            total["window"].setdefault((x, y), [x, y, lo, hi, 0])
        total["source"].append("glass.json")
    except (OSError, ValueError):
        pass
    fences = render_fences(map_name)              # H4 / H2A: the kits' exports lack the instanced geometry's collision
    if fences:
        cells = {"fence": {}, "fence_floor": {}}
        for tri in fences:
            face_cells(tri, cells["fence_floor" if is_flat(tri) else "fence"])
        for k, v in kinds_out(cells).items():
            for c in v:
                total[k].setdefault((c[0], c[1]), c)
        total["source"].append(f"bsp2obj --fence ({len(fences)} triangles)")
    try:                                          # (the level's own extent: a sky / vista BSP's faces are no walls)
        import numpy as np
        d = np.load(os.path.join(ROOT, "maps", map_name, "heightmap.npz"))
        x0, y0, c, (h, w) = float(d["x0"]), float(d["y0"]), float(d["cell"]), d["low"].shape
        box = (x0 * 4, y0 * 4, (x0 + w * c) * 4, (y0 + h * c) * 4)
    except (OSError, KeyError, ValueError):
        box = None
    res = dict(cell=0.25, source=total["source"], shaders=total["shaders"], counts=total["counts"],
               **{k: sorted(v for v in total[k].values() if box is None or box[0] <= v[0] <= box[2] and box[1] <= v[1] <= box[3])
                  for k in ("window", "fence", "window_floor", "fence_floor")})
    if res["source"]:
        out = os.path.join(ROOT, "maps", map_name, "wall_kinds.json")
        with open(out + ".tmp", "w") as f:                 # (atomic: a reader never sees half a file)
            json.dump(res, f)
        os.replace(out + ".tmp", out)
    return res


def load(map_name):
    try:
        return json.load(open(os.path.join(ROOT, "maps", map_name.replace("\\", "/").partition("/")[0], "wall_kinds.json")))
    except (OSError, ValueError):
        return {}


if __name__ == "__main__":
    for m in [a for a in sys.argv[1:] if not a.startswith("--")]:
        r = build(m, keep="--keep-xml" in sys.argv)
        print(f"{m}: {len(r['window'])} window cells, {len(r['fence'])} fence cells; surfaces {r['counts']}; "
              f"shaders {r['shaders']}; from {r['source']}", flush=True)
