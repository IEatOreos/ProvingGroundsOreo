"""Reach Forge Printer, phase 2: a Halo 3 map as a tracing reference for Blender.

    python\\python.exe tools\\forge_printer reference h3_guardian [--out FOLDER]

Writes, in FOLDER (default E:\\Proving Grounds\\re_tools\\forge_printer\\reference\\<map>):

  <map>.obj        the map's level geometry (bsp2obj, run as its own program),
                   every vertex in Reach units
  reference.json   its spawns, weapons, objectives and other placements from
                   maps/<map>/objects.json and features.json, in Reach units,
                   facings in radians

Both are made from the game: they stay local and are never committed.
Phase 2 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import json
import math
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPS = os.path.join(ROOT, "maps")
DEFAULT_OUT = r"E:\Proving Grounds\re_tools\forge_printer\reference"

# Halo 3 world units -> Halo: Reach world units. Measured 2026-11-21 (see the
# Phase 2 handoff note in docs/REACH_FORGE_PRINTER_PLAN.md): both games are the
# same engine family and the same world unit. The player models, exported with
# model2obj, stand 0.761 u (Halo 3 mp_masterchief) and 0.742 u (Reach spartans)
# tall at the 99.9th percentile of vertex height, 2.5% apart. That gap is the
# two armour designs or a unit change; this one measurement cannot tell which.
# 1.0 (no change) until the owner decides.
H3_TO_REACH_SCALE = 1.0

SOURCE_GAME = "halo3"
PREFIX = "h3_"
GRID = 4                     # decimals written for every coordinate (bsp2obj's own precision)


class ReferenceError(Exception):
    """A clear one-line reason the reference could not be made."""


def _paths():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from brain import paths
    return paths


def map_file(name, mcc_dir):
    """The Halo 3 .map file for a maps/ folder name (h3_guardian -> halo3\\maps\\guardian.map)."""
    if not name.startswith(PREFIX):
        raise ReferenceError("only Halo 3 maps (maps/h3_*) are supported for now, not %r" % name)
    path = os.path.join(mcc_dir, "halo3", "maps", name[len(PREFIX):] + ".map")
    if not os.path.isfile(path):
        raise ReferenceError("%s is not in this MCC copy (%s)" % (os.path.basename(path), os.path.dirname(path)))
    return path


def r(value):
    return round(value * H3_TO_REACH_SCALE, GRID)


def pos(p):
    return [r(float(c)) for c in p[:3]]


def facing(deg):
    """objects.json keeps facings in degrees (brain/invasion.py reads math.radians(facing))."""
    return round(math.radians(float(deg or 0.0)), 6)


def placements(objects, features):
    """reference.json's placement lists from the two source files' dicts."""
    spawns = [{"pos": pos(s["pos"]), "facing": facing(s.get("facing")), "team": s.get("team"),
               "games": s.get("games", [])} for s in objects.get("spawns", [])]
    objectives = [{"type": f.get("type"), "pos": pos(f["pos"]), "facing": facing(f.get("facing")),
                   "team": f.get("team"), "id": f.get("id")} for f in objects.get("netgame_flags", [])]
    weapons, other = [], []
    for f in features.get("features", []):
        kind = f.get("kind")
        if kind == "objective":          # objects.json's netgame_flags carry these, with facing and id
            continue
        if kind == "weapon":
            weapons.append({"name": f.get("name"), "pos": pos(f["pos"]), "respawn": f.get("respawn"),
                            "team": f.get("team")})
        else:
            item = {"kind": kind, "name": f.get("name"), "pos": pos(f["pos"])}
            for key in ("respawn", "team", "role"):
                if key in f:
                    item[key] = f[key]
            other.append(item)
    for pair in features.get("teleporters", []):
        other.append({"kind": "teleporter_pair", "name": "teleporter", "pos": pos(pair[0]), "to": pos(pair[1])})
    return {"spawns": spawns, "weapons": weapons, "objectives": objectives, "other": other}


def scale_obj(src, dst):
    """Copies an OBJ with every vertex scaled into Reach units. (triangles, (min, max) bounds)."""
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    tris = 0
    with open(src, encoding="ascii", errors="replace") as fin, open(dst, "w", encoding="ascii", newline="\n") as fout:
        for line in fin:
            if line.startswith("v "):
                xyz = [r(float(c)) for c in line.split()[1:4]]
                for i, c in enumerate(xyz):
                    lo[i], hi[i] = min(lo[i], c), max(hi[i], c)
                fout.write("v %.4f %.4f %.4f\n" % tuple(xyz))
            else:
                if line.startswith("f "):
                    tris += len(line.split()) - 3
                fout.write(line if line.endswith("\n") else line + "\n")
    if not tris:
        raise ReferenceError("bsp2obj wrote no triangles")
    return tris, (lo, hi)


def outside(items, bounds, margin=2.0):
    """The placements not inside the bounding box grown by margin: [(list name, item)]."""
    lo, hi = bounds
    out = []
    for group in ("spawns", "weapons", "objectives", "other"):
        for item in items[group]:
            p = item["pos"]
            if any(p[i] < lo[i] - margin or p[i] > hi[i] + margin for i in range(3)):
                out.append((group, item))
    return out


def build(name, out_dir=None, mcc_dir=None, bsp2obj=None, maps_dir=MAPS):
    """Writes <out>/<name>.obj and <out>/reference.json. Returns the reference dict plus a 'report' dict."""
    src_dir = os.path.join(maps_dir, name)
    if not os.path.isdir(src_dir):
        raise ReferenceError("no map folder maps/%s" % name)
    try:
        with open(os.path.join(src_dir, "objects.json"), encoding="utf-8") as f:
            objects = json.load(f)
        with open(os.path.join(src_dir, "features.json"), encoding="utf-8") as f:
            features = json.load(f)
    except OSError as error:
        raise ReferenceError("maps/%s is missing %s" % (name, os.path.basename(error.filename or "a file")))
    if bsp2obj is None or mcc_dir is None:
        paths = _paths()
        mcc_dir = mcc_dir or paths.mcc()
        bsp2obj = bsp2obj or paths.map_tool("bsp2obj")
    if not mcc_dir or not os.path.isdir(mcc_dir):
        raise ReferenceError("MCC was not found (choose its folder in the launcher, or set HB_MCC)")
    if not bsp2obj:
        raise ReferenceError("bsp2obj.exe was not found (tools/map_tools, or set HB_MAP_TOOLS)")
    source = map_file(name, mcc_dir)
    out_dir = out_dir or os.path.join(DEFAULT_OUT, name)
    os.makedirs(out_dir, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=out_dir) as tmp:
        raw = os.path.join(tmp, "raw.obj")
        run = subprocess.run([bsp2obj, source, raw], capture_output=True, text=True, timeout=600)
        if run.returncode != 0 or not os.path.isfile(raw):
            last = (run.stderr or run.stdout or "").strip().splitlines()
            raise ReferenceError("bsp2obj failed (exit %d): %s" % (run.returncode, last[-1] if last else "no output"))
        listed = None
        for line in run.stdout.splitlines():
            if " triangles (" in line and line.split()[1] == "bsps,":
                listed = int(line.split()[2])
        mesh = name + ".obj"
        tris, bounds = scale_obj(raw, os.path.join(out_dir, mesh))

    ref = {"source": {"game": SOURCE_GAME, "map": name, "scale_from_source": H3_TO_REACH_SCALE},
           "mesh": mesh,
           "bounds": {"min": bounds[0], "max": bounds[1]}}
    ref.update(placements(objects, features))
    with open(os.path.join(out_dir, "reference.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(ref, f, indent=1)
        f.write("\n")
    report = {"out": out_dir, "triangles": tris, "bsp2obj_triangles": listed,
              "outside": outside(ref, bounds),
              "source_counts": {"spawns": len(objects.get("spawns", [])),
                                "netgame_flags": len(objects.get("netgame_flags", [])),
                                "features": len(features.get("features", []))}}
    return ref, report


def main(name, out_dir=None):
    try:
        ref, rep = build(name, out_dir)
    except ReferenceError as error:
        print("reference: %s" % error)
        return 1
    lo, hi = ref["bounds"]["min"], ref["bounds"]["max"]
    print("wrote %s" % rep["out"])
    print("mesh        %s  %d triangles (bsp2obj reported %s)" % (ref["mesh"], rep["triangles"], rep["bsp2obj_triangles"]))
    print("bounds      x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f  (size %.2f x %.2f x %.2f)" % (
        lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))
    print("placements  %d spawns, %d weapons, %d objectives, %d other" % tuple(
        len(ref[k]) for k in ("spawns", "weapons", "objectives", "other")))
    print("scale       %.4f (Halo 3 -> Reach units)" % H3_TO_REACH_SCALE)
    if rep["outside"]:
        print("outside the mesh box (+2 u): %d" % len(rep["outside"]))
        for group, item in rep["outside"]:
            print("  %s %s %s" % (group, item.get("name") or item.get("type") or "", item["pos"]))
    else:
        print("outside the mesh box (+2 u): none")
    return 0
