"""(custom, Nov 22) Modded maps for LiDAR and the bots. The owner: "find out a way to make modded maps mappable as well".

A map the bots and LiDAR know has level data, maps/<map>/heightmap.npz (tools/heightmap.py), and its scenario's
objects.json and callouts.json. MCC's own maps come with the map pack; a modded map (a Steam Workshop mod, or one built
with a mod kit, as the owner's FP_GUARDIAN port) has none, so LiDAR mapped it blind (tools/lidar.py level_data) and the
bots would not play it (tools/play.py: "bots do not know the map"). This finds every modded multiplayer map on this PC and
builds its level data from its own .map file:

  where    the mod folders MCC loads: those listed in LocalLow\\MCC\\Config\\ModManifest.txt (a mod kit's MCC folder) and
           every Steam library's workshop\\content\\976730; each mod's ModInfo.json "Engine" and its multiplayer\\*.json
           (ScenarioFile, Title) give the map. Its folder is named as the bots name the running map: "<game>_<scenario>"
           (reach_fp_guardian; tools/play.py). A mod's map on a stock map's scenario (The Great Forge's 20_sword_slayer)
           is that map: it already has level data and is left alone.
  level    bsp2obj.exe (the map tools, brain/paths.map_tool) exports its level geometry to source/bsp.obj, and
           tools/heightmap.py rasterises it as for every other map.
  objects  a modded map's scenario is not read (only its geometry is), so objects.json is a stand-in ("stand_in": true):
           STAND_INS spawn points spread over the level's floor and two flags (the farthest pair), which is all the
           brain needs to load a map (brain/maps.py load_map), and which set the height map's play area. Its floor
           comes from where people walked on it with LiDAR (maps/<map>/lidar.json, kinds 1 and 3) once there is any,
           else from its walkable faces (STAND_BIN cells holding STAND_AREA of floor, within its middle STAND_BAND). A
           Forge layout played on it is read live as on Forge World (brain/variants.py: no placed objects, so a canvas).
  callouts a generated callouts.json: three areas across the level, its middle, and holds at the flags.
  mod.json the mod and its map's in-game title (tools/lidar.py map_title shows it).

Nothing made by hand is overwritten: objects.json only while it is a stand-in, callouts.json only while generated.
The folder gets a .gitignore of "*": data made from a mod on this PC is never committed or shipped.
Run it again with --force after walking a new map with LiDAR, so the stand-ins come from where people walked.

usage: python -I tools/mod_maps.py              list the modded maps and whether each has level data
       python -I tools/mod_maps.py --build      build every modded map without level data, or whose .map is newer
       python -I tools/mod_maps.py <map> [--force]   build one (reach_fp_guardian), --force: again
       python -I tools/mod_maps.py --name-layouts [--dry]   name the filed Forge layouts with none (brain/mvar.py)
"""
import glob
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
from brain import paths  # noqa: E402

MAPS = os.path.join(ROOT, "maps")
MANIFEST = os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "MCC", "Config", "ModManifest.txt")
# ModInfo.json "Engine" -> the bots' game prefix; the games bsp2obj reads (Halo: CE and Halo 2 are not tried)
ENGINES = {"HaloReach": "reach", "Halo3": "h3", "Halo3ODST": "odst", "Halo4": "h4", "Halo2A": "h2a"}
GAME_DIRS = {"reach": "haloreach", "h3": "halo3", "odst": "halo3odst", "h4": "halo4", "h2a": "groundhog"}
STAND_INS = 16          # stand-in spawn points
STAND_BIN = 2.0         # floor cells (world units) ...
STAND_AREA = 2.0        # ... holding this much walkable face (not a leaf or a ledge's sliver)
STAND_BAND = (0.05, 0.95)   # the middle of the floor's heights and extent (not a sky box's floor, not the outskirts)
FLOOR_NZ = 0.7          # walkable, as tools/heightmap.py


def _json(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def mod_roots(manifest=MANIFEST, commons=None):
    """Folders holding mod folders: ModManifest.txt's lines, then each Steam library's MCC workshop content."""
    out = []
    try:
        with open(manifest, encoding="utf-8-sig") as f:
            out += [ln.strip() for ln in f if ln.strip()]
    except OSError:
        pass
    for common in paths.steam_commons() if commons is None else commons:
        out.append(os.path.join(os.path.dirname(common), "workshop", "content", paths.MCC_APPID))
    seen, keep = set(), []
    for r in out:
        k = os.path.normcase(os.path.abspath(r))
        if k not in seen and os.path.isdir(r):
            seen.add(k)
            keep.append(r)
    return keep


def _map_file(mod, stem):
    """The mod's <stem>.map (its maps folder, any case), or None."""
    for sub in os.listdir(mod):
        d = os.path.join(mod, sub)
        if sub.lower() == "maps" and os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.lower() == stem.lower() + ".map":
                    return os.path.join(d, fn)
    return None


def stock(game, stem, mcc=None):
    """Is <stem> one of MCC's own maps of this game (a mod replacing it keeps its level data)?"""
    mcc = paths.mcc() if mcc is None else mcc
    return bool(mcc) and os.path.exists(os.path.join(mcc, GAME_DIRS[game], "maps", stem + ".map"))


def mod_maps(roots=None, mcc=None):
    """Every modded multiplayer map: [dict(folder, game, stem, title, mod, mod_dir, map, stock, built)]."""
    out = []
    for root in mod_roots() if roots is None else roots:
        for mod in sorted(glob.glob(os.path.join(root, "*", ""))):
            mod = os.path.dirname(mod)
            info = _json(os.path.join(mod, "ModInfo.json"))
            if not isinstance(info, dict) or info.get("Engine") not in ENGINES:
                continue
            game = ENGINES[info["Engine"]]
            mod_title = (info.get("Title") or {}).get("Neutral") or os.path.basename(mod)
            for rel in (info.get("GameModContents") or {}).get("MultiplayerMaps") or []:
                mp = _json(os.path.join(mod, rel.replace("\\", os.sep)))
                if not isinstance(mp, dict) or not mp.get("ScenarioFile"):
                    continue
                stem = mp["ScenarioFile"].replace("/", "\\").rsplit("\\", 1)[-1]
                folder = f"{game}_{stem}"
                mf, hm = _map_file(mod, stem), os.path.join(MAPS, folder, "heightmap.npz")
                built = os.path.exists(hm)
                out.append(dict(folder=folder, game=game, stem=stem, title=(mp.get("Title") or {}).get("Neutral") or stem,
                                mod=mod_title, mod_dir=mod, map=mf, stock=stock(game, stem, mcc), built=built,
                                # (rebuilt by its maker since: the FP ports are)
                                stale=bool(built and mf and os.path.getmtime(mf) > os.path.getmtime(hm))))
    return out


def map_file(stem, game="reach"):
    """The .map file of a modded map by its scenario name (tools/reach_tag_names.py: a map MCC's folder lacks), or None."""
    return next((m["map"] for m in mod_maps() if m["game"] == game and m["stem"].lower() == stem.lower() and m["map"]),
                None)


def mod_title(folder):
    """A modded map's in-game title from its mod.json, or None."""
    d = _json(os.path.join(MAPS, folder, "mod.json"))
    return d.get("title") if isinstance(d, dict) else None


def walked(folder):
    """Where people stood on the map with LiDAR (lidar.json "walk", kinds 1 and 3): [(x, y, z)]."""
    d = _json(os.path.join(MAPS, folder, "lidar.json")) or {}
    c, zs = d.get("cell", 0.25), d.get("zstep", 0.1)
    return [(w[0] * c, w[1] * c, w[2] * zs) for w in d.get("walk", ())
            if len(w) > 4 and w[3] in (1, 3)]


def floor_points(v, f):
    """The level's floor as points (x, y, z): STAND_BIN cells holding STAND_AREA of walkable face, their faces'
    centre, within STAND_BAND of the floor's heights and extent."""
    import numpy as np
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    norm = np.linalg.norm(n, axis=1)
    up = (norm > 0) & (n[:, 2] >= FLOOR_NZ * norm)
    c, area = tri[up].mean(axis=1), norm[up] / 2
    if not len(c):
        return []
    lo, hi = np.quantile(c, STAND_BAND[0], axis=0), np.quantile(c, STAND_BAND[1], axis=0)
    keep = np.all((c >= lo) & (c <= hi), axis=1)
    c, area = c[keep], area[keep]
    cells = {}
    for p, a in zip(c, area):
        k = (math.floor(p[0] / STAND_BIN), math.floor(p[1] / STAND_BIN), math.floor(p[2] / 0.5))
        s = cells.setdefault(k, [0.0, 0.0, 0.0, 0.0])
        s[0] += a
        s[1] += p[0] * a
        s[2] += p[1] * a
        s[3] += p[2] * a
    return [(s[1] / s[0], s[2] / s[0], s[3] / s[0]) for s in cells.values() if s[0] >= STAND_AREA]


def spread(points, n=STAND_INS):
    """n of points spread over them (farthest-point sampling from the one nearest their middle)."""
    if not points:
        return []
    mx = sum(p[0] for p in points) / len(points)
    my = sum(p[1] for p in points) / len(points)
    pick = [min(points, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)]
    near = [math.dist(p, pick[0]) for p in points]
    while len(pick) < min(n, len(points)):
        i = max(range(len(points)), key=near.__getitem__)
        pick.append(points[i])
        near = [min(d, math.dist(p, points[i])) for d, p in zip(near, points)]
    return pick


def stand_ins(points):
    """objects.json for a modded map from its floor points: STAND_INS spawns (both teams, every game) and two CTF flags,
    the farthest pair of them."""
    sp = spread(points)
    if len(sp) < 2:
        raise ValueError("no floor found to stand on")
    a, b = max(((p, q) for i, p in enumerate(sp) for q in sp[i + 1:]), key=lambda pq: math.dist(pq[0][:2], pq[1][:2]))
    r = lambda p: [round(float(x), 3) for x in p]
    return dict(stand_in=True, netgame_flags=[dict(type="ctf - flag", id=t, team=t, pos=r(p), facing=0.0)
                                              for t, p in enumerate((a, b))],
                spawns=[dict(pos=r(p), team=k % 2, facing=0.0, games=["all games"]) for k, p in enumerate(sp)],
                equipment=[], vehicles=[], scenery=[], placed=[])


def callouts(folder, objs):
    """A generated callouts.json (as tools/variant_strategy.py makes a Forge layout's): three areas across the level,
    its middle, both teams' holds at their flags."""
    pts = [s["pos"] for s in objs["spawns"]]
    flags = [f["pos"] for f in objs["netgame_flags"]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0, x1, y1 = min(xs) - 8, min(ys) - 8, max(xs) + 8, max(ys) + 8
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    mid = min(pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
    long_x = x1 - x0 >= y1 - y0
    zones = {}
    for k, label in enumerate(("West side", "Mid", "East side") if long_x else ("South side", "Mid", "North side")):
        if long_x:
            a, b = x0 + (x1 - x0) * k / 3, x0 + (x1 - x0) * (k + 1) / 3
            poly = [[a, y0], [b, y0], [b, y1], [a, y1]]
        else:
            a, b = y0 + (y1 - y0) * k / 3, y0 + (y1 - y0) * (k + 1) / 3
            poly = [[x0, a], [x1, a], [x1, b], [x0, b]]
        zones[label] = dict(poly=[[round(c, 2) for c in q] for q in poly], side="mid", priority=0, full=label.lower(),
                            aka=[], area=True)
    hold = lambda f: sorted(pts, key=lambda p: math.dist(p, f))[:3]
    return dict(map=folder, generated=True, base_radius=5.0, roof_z=round(max(p[2] for p in pts), 2),
                points={"mid": mid, "mid_hill": mid}, holds={"red": hold(flags[0]), "blue": hold(flags[1])},
                lanes=pts, sneak={}, zones=zones)


def _write(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def build(m, force=False, log=print):
    """Level data for modded map m (mod_maps row): source/bsp.obj, stand-in objects.json, heightmap.npz, topdown.png,
    callouts.json, mod.json. Returns what it did ("built", or why not)."""
    if m["stock"]:
        return "a stock map's scenario: it has level data"
    if not m["map"]:
        return "the mod has no .map file for it"
    d = os.path.join(MAPS, m["folder"])
    if m["built"] and not m.get("stale") and not force:
        return "has level data (--force builds it again)"
    tool = paths.map_tool("bsp2obj")
    if not tool:
        return "bsp2obj.exe not found (tools/map_tools)"
    src = os.path.join(d, "source")
    os.makedirs(src, exist_ok=True)
    ign = os.path.join(d, ".gitignore")               # (made on this PC from a mod: never committed or shipped)
    if not os.path.exists(ign):
        with open(ign, "w", encoding="utf-8") as fh:
            fh.write("# made by tools/mod_maps.py from a mod's .map on this PC\n*\n")
    obj = os.path.join(src, "bsp.obj")
    log(f"{m['folder']}: exporting {os.path.basename(m['map'])} ...")
    r = subprocess.run([tool, m["map"], obj], capture_output=True, text=True)
    log("  " + (r.stdout.strip().splitlines() or ["(no output)"])[-1])
    if r.returncode != 0 or not os.path.exists(obj) or os.path.getsize(obj) < 100:
        return "bsp2obj exported no geometry"
    import heightmap
    v, f = heightmap.load_obj(obj)
    if not len(f):
        return "bsp2obj exported no geometry"
    op = os.path.join(d, "objects.json")
    old = _json(op)
    if old is None or old.get("stand_in"):
        people = walked(m["folder"])
        from_walk = len(people) >= STAND_INS * 4
        objs = stand_ins(people if from_walk else floor_points(v, f))
        objs["stand_in_from"] = "LiDAR walk" if from_walk else "floor faces"
        _write(op, objs)
    else:
        objs = old
    log(f"  objects: {'stand-ins from the ' + objs['stand_in_from'] if objs.get('stand_in') else 'kept (not a stand-in)'}")
    tmp = os.path.join(src, "_build")              # (written here, then each file swapped in whole: a match may be
    os.makedirs(tmp, exist_ok=True)                # reading the old ones)
    r = subprocess.run([sys.executable, "-I", os.path.join(HERE, "heightmap.py"), obj, op, tmp],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return "heightmap.py failed: " + (r.stderr.strip().splitlines() or ["?"])[-1]
    for fn in ("heightmap.npz", "topdown.png"):
        os.replace(os.path.join(tmp, fn), os.path.join(d, fn))
    log("  " + (r.stdout.strip().splitlines() or [""])[-1])
    cp = os.path.join(d, "callouts.json")
    oldc = _json(cp)
    if oldc is None or oldc.get("generated"):
        _write(cp, callouts(m["folder"], objs))
    _write(os.path.join(d, "mod.json"), dict(title=m["title"], mod=m["mod"], game=m["game"], scenario=m["stem"],
                                             map_file=m["map"]))
    return "built"


def main(argv):
    if "--name-layouts" in argv:                    # Forge layouts filed with no name: from the .mvar files (brain/mvar)
        from brain import mvar
        for layout, name, fn, share in mvar.name_layouts(write="--dry" not in argv):
            print(f"{layout}: {name!r} from {fn} ({share:.0%})" if name else f"{layout}: no clear name (best {share:.0%})")
        return 0
    rows = mod_maps()
    want = [a for a in argv if not a.startswith("--")]
    if not want and "--build" not in argv:
        for m in rows:
            state = ("stock map" if m["stock"] else "no .map" if not m["map"] else "OUT OF DATE" if m["stale"]
                     else "level data" if m["built"] else "NOT MAPPED")
            print(f"{m['folder']:32} {state:11} {m['title']}  ({m['mod']})")
        return 0
    todo = [m for m in rows if (m["folder"] in want if want else (not m["built"] or m["stale"]) and not m["stock"])]
    for w in set(want) - {m["folder"] for m in rows}:
        print(f"{w}: not a modded map on this PC")
    for m in todo:
        print(f"{m['folder']}: {build(m, force='--force' in argv)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
