"""Reach Forge Printer, phase 3: the Forge World building pieces and their sizes.

    python\\python.exe tools\\forge_printer pieces [--measure] [--keep FOLDER]

Without --measure it prints the table in forge_world_pieces.json (beside this file).
With --measure it exports each piece's model from MCC's forge_halo.map with model2obj (run as its
own program), measures its box and rewrites the table. The exported models are made from the
game: they go to FOLDER (default E:\\Proving Grounds\\re_tools\\forge_printer\\pieces) and are
never committed; the table holds only names and sizes.

A piece's box is in its own axes, world units: where it reaches from the point Forge places it
by. Which of those axes is the piece's "forward" in a variant file is settled by the calibration
map, not here.

Phase 3 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import json
import os
import subprocess
import sys

TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forge_world_pieces.json")
DEFAULT_KEEP = r"E:\Proving Grounds\re_tools\forge_printer\pieces"
MAP = ("haloreach", "maps", "forge_halo.map")
TAG_FOLDER = "objects\\levels\\forge\\"

# (Forge menu name, model, how the name is known). Each category is in the map file's own order,
# which is the Forge menu's order wherever it could be checked (see the plan's phase 3 notes).
#   "noted"  the owner placed it in the calibration map and wrote the name down (2026-11-21)
#   "menu"   not in the owner's notes; the name is the Forge menu's as best remembered
#   "model"  not in the owner's notes and the menu name is not known: named after its model
NOTED, MENU, MODEL = "noted", "menu", "model"

# Where a variant file keeps each category: the row of Forge World's quota table (the object's "type"),
# for today's MCC palette (145 rows, map checksum 0x8B33E8AC). A piece's "item" is its place in its
# category, counting from 0. Read off ten Forge World variants on the owner's PC, 2026-11-21: rows 70 to
# 76 are the only ones with many items, and the highest item each uses is one less than the number of
# models the map file has for that category (25, 20, 10, 15, 11, 14, 7). The owner's own variant uses
# row 74 item 8 for Wall Coliseum.
FORGE_WORLD_MAP_ID = 3006
FORGE_WORLD_QUOTA_ROWS = 145
ROWS = {"Building Blocks": 70, "Bridges and Platforms": 71, "Buildings": 72, "Decorative": 73,
        "Doors, Windows and Walls": 74, "Inclines": 75, "Nature": 76}

CATEGORIES = [
    ("Building Blocks", [
        ("Block 1x1", "ff_plat_1x1", NOTED), ("Block 1x1 Flat", "ff_plat_1x1_flat", NOTED),
        ("Block 1x1 Short", "ff_plat_1x1_short", NOTED), ("Block 1x1 Tall", "ff_plat_1x1_tall", NOTED),
        ("Block 1x1 Tall and Thin", "ff_plat_1x1_tall_thin", NOTED), ("Block 1x2", "ff_plat_1x2", NOTED),
        ("Block 1x4", "ff_plat_1x4", NOTED), ("Block 2x1 Flat", "ff_plat_2x1_flat", NOTED),
        ("Block 2x2", "ff_plat_2x2", NOTED), ("Block 2x2 Flat", "ff_plat_2x2_flat", NOTED),
        ("Block 2x2 Short", "ff_plat_2x2_short", NOTED), ("Block 2x2 Tall", "ff_plat_2x2_tall", NOTED),
        ("Block 2x3", "ff_plat_2x3", NOTED), ("Block 2x4", "ff_plat_2x4", NOTED),
        ("Block 3x1 Flat", "ff_plat_3x1_flat", NOTED), ("Block 3x3", "ff_plat_3x3", NOTED),
        ("Block 3x3 Flat", "ff_plat_3x3_flat", NOTED), ("Block 3x3 Short", "ff_plat_3x3_short", NOTED),
        ("Block 3x3 Tall", "ff_plat_3x3_tall", NOTED), ("Block 3x4", "ff_plat_3x4", NOTED),
        ("Block 4x4", "ff_plat_4x4", NOTED), ("Block 4x4 Flat", "ff_plat_4x4_flat", NOTED),
        ("Block 4x4 Short", "ff_plat_4x4_short", MENU), ("Block 4x4 Tall", "ff_plat_4x4_tall", NOTED),
        # the owner's notes say "Block 5x1 Short"; the model is the flat one, 0.22 tall like the other Flat blocks
        ("Block 5x1 Flat", "ff_plat_5x1_flat", NOTED), ("Block 5x5 Flat", "ff_plat_5x5_flat", NOTED)]),
    ("Bridges and Platforms", [
        ("Bridge Small", "ff_bridge_2x1", NOTED), ("Bridge Medium", "ff_bridge_2x2", NOTED),
        ("Bridge Large", "ff_bridge_2x3", NOTED), ("Bridge XLarge", "ff_bridge_2x5", NOTED),
        ("Bridge Diagonal", "ff_bridge_diag", NOTED), ("Bridge Diag Small", "ff_bridge_diag_short", NOTED),
        ("Dish", "ff_dish", NOTED), ("Dish Open", "ff_dish_door", NOTED),
        ("Corner 45 Degrees", "ff_plat_2x2_45", NOTED), ("Corner 2x2", "ff_plat_2x2_corner", NOTED),
        ("Corner 4x4", "ff_plat_4x4_corner", NOTED), ("Landing Pad", "ff_plat_4x6", NOTED),
        ("Platform Ramped", "ff_ramp_plat", NOTED), ("Platform Large", "ff_plat_tower_4x4", NOTED),
        ("Platform XLarge", "ff_cylinder_small", NOTED), ("Platform XXL", "ff_cylinder_big", NOTED),
        ("Platform Y", "ff_plat_y_cross", NOTED), ("Platform Y Large", "ff_plat_y_cross_large", NOTED),
        ("Sniper Nest", "ff_ramp_enclosed", NOTED), ("Staircase", "ff_stair_case", NOTED),
        ("Walkway Large", "ff_walkway_small", NOTED)]),
    ("Buildings", [
        ("Bunker Small", "ff_bunker_low", NOTED), ("Bunker Small Covered", "ff_bunker_covered", NOTED),
        ("Bunker Box", "ff_bunker_full", NOTED), ("Bunker Round", "ff_base_round", NOTED),
        ("Bunker Ramped", "ff_bunker_stair", NOTED), ("Pyramid", "ff_pyramid", NOTED),
        ("Tower 2 Story", "ff_tower", NOTED), ("Tower 3 Story", "ff_tower_3_story", NOTED),
        ("Tower Tall", "ff_tower_tall", NOTED), ("Room Double", "ff_room_double", NOTED),
        ("Room Triple", "ff_room_triple", NOTED)]),
    # Sixteen items, as the variants show. The map file lists ff_dish_antenna apart from the rest; it is
    # put second here because the menu has two antennas first. The items from the sixth to the tenth
    # (column, covers, crenellations) are in the map file's order, which nothing has confirmed.
    ("Decorative", [
        ("ff_antenna", "ff_antenna", MODEL), ("ff_dish_antenna", "ff_dish_antenna", MODEL),
        ("ff_brace", "ff_brace", MODEL),
        ("ff_large_brace", "ff_large_brace", MODEL), ("ff_arch_brace", "ff_arch_brace", MODEL),
        ("Column", "ff_column", NOTED), ("ff_crenel_full", "ff_crenel_full", MODEL),
        ("ff_crenel_notch", "ff_crenel_notch", MODEL), ("Cover", "ff_cover_2", NOTED),
        ("ff_ramp_wall_2x1", "ff_ramp_wall_2x1", MODEL), ("Railing Small", "ff_railing_1", NOTED),
        ("Railing Medium", "ff_railing_2", NOTED), ("Railing Long", "ff_railing_3", NOTED),
        ("ff_teleport_frame", "ff_teleport_frame", MODEL), ("Strut", "ff_base_strut", NOTED),
        ("ff_walkway_small_cover", "ff_walkway_small_cover", MODEL)]),
    ("Doors, Windows and Walls", [
        # the first six were named by the owner from a picture of the models, 2026-11-21: Door is the tall
        # arch (2 x 2), Door Double the low one (2 x 1)
        ("Door", "ff_door_2", NOTED), ("Door Double", "ff_wall_2x1_door", NOTED),
        ("Window", "ff_wall_2x1_window", NOTED), ("Window Double", "ff_wall_2x2_window", NOTED),
        ("Wall", "ff_wall_2x2", NOTED), ("Wall Double", "ff_wall_2x4", NOTED),
        ("Wall Corner", "ff_wall_2x1_corner", NOTED), ("Wall Curved", "ff_wall_curve_short", NOTED),
        ("Wall Coliseum", "ff_arena_wall", NOTED), ("Window Coliseum", "ff_arena_window", MENU),
        ("Tunnel Short", "ff_tunnel_2x1", NOTED), ("Tunnel Long", "ff_tunnel_3x3", NOTED)]),
    ("Inclines", [
        ("Bank 1x1", "ff_bank_1x1", NOTED), ("Bank 1x2", "ff_bank_1x2", NOTED),
        ("Bank 2x1", "ff_bank_2x1", NOTED), ("Bank 2x2", "ff_bank_2x2", NOTED),
        ("Ramp 1x2", "ff_ramp_1x2", NOTED), ("Ramp 1x2 Shallow", "ff_ramp_1x2_shallow", NOTED),
        ("Ramp 2x2", "ff_ramp_2x2", NOTED), ("Ramp 2x2 Steep", "ff_ramp_2x2_steep", NOTED),
        ("Ramp Circular Small", "ff_ramp_circle_small", NOTED), ("Ramp Circular Large", "ff_ramp_circle_large", NOTED),
        ("Ramp Bridge Small", "ff_ramp_3", NOTED), ("Ramp Bridge Medium", "ff_ramp_4", NOTED),
        ("Ramp Bridge Large", "ff_ramp_5", NOTED), ("Ramp XL", "ff_ramp_4x2", NOTED),
        ("Ramp Stunt", "ff_race_stunt_ramp", NOTED)]),
    ("Nature", [
        ("Rock Small", "ff_rock_small", NOTED), ("Rock Flat", "ff_rock_flat", NOTED),
        ("Rock Medium 1", "ff_rock_med_a", NOTED), ("Rock Medium 2", "ff_rock_med_b", NOTED),
        ("Rock Spire 1", "ff_rock_spire_a", NOTED), ("Rock Spire 2", "ff_rock_spire_b", NOTED),
        ("Rock Seastack", "ff_rock_sea_stack", NOTED), ("Rock Arch", "ff_rock_arch", NOTED)]),
]


class PieceError(Exception):
    """A clear one-line reason the pieces could not be measured or read."""


def catalogue():
    """Every piece as a dict (category, row, item, name, model, name_from), in menu order."""
    return [{"category": category, "row": ROWS[category], "item": item, "name": name, "model": model,
             "name_from": source}
            for category, items in CATEGORIES for item, (name, model, source) in enumerate(items)]


def obj_box(path):
    """(min, max, vertex count) of an OBJ's vertices."""
    lo, hi, count = [float("inf")] * 3, [float("-inf")] * 3, 0
    with open(path, encoding="ascii", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                xyz = [float(c) for c in line.split()[1:4]]
                for i in range(3):
                    lo[i], hi[i] = min(lo[i], xyz[i]), max(hi[i], xyz[i])
                count += 1
    if not count:
        raise PieceError("%s holds no vertices" % os.path.basename(path))
    return lo, hi, count


def obj_slope(path):
    """The sloping face of a ramp model: the largest group of triangles that lean the same way.
    A dict: lean (degrees from level), uphill (the compass direction it climbs in the model's own
    axes, degrees counter-clockwise from +x), run and width (its size on the ground, along and
    across the climb), low and high (its heights), centre (the middle of it on the ground, x y).
    None for a model with no such face."""
    import math

    import numpy as np

    from . import surfaces
    verts, tris = surfaces.load_obj(path)
    normals, areas, _ = surfaces.geometry(verts, tris)
    lean = surfaces.lean(normals)
    sloped = (lean > 8.0) & (lean < 60.0)
    if not sloped.any():
        return None
    uphill = np.degrees(np.arctan2(-normals[:, 1], -normals[:, 0])) % 360.0
    groups = {}
    for t in np.nonzero(sloped)[0]:
        key = (int(round(lean[t] / 3.0)), int(round(uphill[t] / 15.0)) % 24)
        groups[key] = groups.get(key, 0.0) + float(areas[t])
    best = max(sorted(groups), key=lambda k: groups[k])
    chosen = np.array([t for t in np.nonzero(sloped)[0]
                       if (int(round(lean[t] / 3.0)), int(round(uphill[t] / 15.0)) % 24) == best])
    mean = (normals[chosen] * areas[chosen][:, None]).sum(axis=0)
    mean /= np.linalg.norm(mean)
    climb = math.atan2(-mean[1], -mean[0])
    along = np.array([math.cos(climb), math.sin(climb)])
    across = np.array([-along[1], along[0]])
    pts = verts[tris[chosen]].reshape(-1, 3)
    s, a = pts[:, :2] @ along, pts[:, :2] @ across
    mid = along * (s.min() + s.max()) / 2.0 + across * (a.min() + a.max()) / 2.0
    return {"lean": round(math.degrees(math.acos(float(mean[2]))), 1),
            "uphill": round(math.degrees(climb) % 360.0, 1) % 360.0,
            "run": tidy(float(s.max() - s.min())), "width": tidy(float(a.max() - a.min())),
            "low": tidy(float(pts[:, 2].min())), "high": tidy(float(pts[:, 2].max())),
            "centre": [tidy(float(mid[0])), tidy(float(mid[1]))]}


def tidy(value):
    """A measured length to the millimetre-ish, with the exporter's 0.00005 slop taken off round sizes."""
    return round(value, 3) + 0.0


def measure(keep=DEFAULT_KEEP, mcc_dir=None, model2obj=None, models=None):
    """Exports every piece's model into `keep` and returns the table (a dict ready to write)."""
    if mcc_dir is None or model2obj is None:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if root not in sys.path:
            sys.path.insert(0, root)
        from brain import paths
        mcc_dir = mcc_dir or paths.mcc()
        model2obj = model2obj or paths.map_tool("model2obj")
    if not mcc_dir or not os.path.isdir(mcc_dir):
        raise PieceError("MCC was not found (choose its folder in the launcher, or set HB_MCC)")
    if not model2obj:
        raise PieceError("model2obj.exe was not found (tools/map_tools, or set HB_MAP_TOOLS)")
    source = os.path.join(mcc_dir, *MAP)
    if not os.path.isfile(source):
        raise PieceError("%s is not in this MCC copy" % os.path.join(*MAP))
    os.makedirs(keep, exist_ok=True)
    pieces = []
    for piece in catalogue():
        if models is not None and piece["model"] not in models:
            continue
        model = piece["model"]
        out = os.path.join(keep, model + ".obj")
        if os.path.exists(out):
            os.remove(out)
        # "\name\name" picks this model only: "ff_tower\ff_tower" is not part of "ff_tower_tall\ff_tower_tall"
        run = subprocess.run([model2obj, source, "\\%s\\%s" % (model, model), out],
                             capture_output=True, text=True, timeout=300)
        if run.returncode != 0 or not os.path.isfile(out):
            last = (run.stderr or run.stdout or "").strip().splitlines()
            raise PieceError("model2obj failed on %s (exit %d): %s" % (model, run.returncode, last[-1] if last else "no output"))
        first = (run.stdout.strip().splitlines() or [""])[0]
        if not first.startswith(TAG_FOLDER + model + "\\" + model + ":"):
            raise PieceError("model2obj exported %r for %s" % (first.split(":")[0], model))
        lo, hi, _ = obj_box(out)
        piece = dict(piece)
        piece["min"] = [tidy(c) for c in lo]
        piece["max"] = [tidy(c) for c in hi]
        piece["size"] = [tidy(hi[i] - lo[i]) for i in range(3)]
        if piece["category"] == "Inclines":
            slope = obj_slope(out)
            if slope:
                piece["slope"] = slope
        pieces.append(piece)
    return {"map": "forge_halo",
            "units": "Halo: Reach world units",
            "axes": "each piece's own model axes; min and max are measured from the point Forge places it by",
            "palette": "row and item are a variant file's type and item on Forge World's 145-row palette",
            "pieces": pieces}


def save(table, path=None):
    with open(path or TABLE, "w", encoding="utf-8", newline="\n") as f:
        f.write('{\n "map": %s,\n "units": %s,\n "axes": %s,\n "palette": %s,\n "pieces": [\n' % (
            json.dumps(table["map"]), json.dumps(table["units"]), json.dumps(table["axes"]),
            json.dumps(table["palette"])))
        rows = [json.dumps(p) for p in table["pieces"]]        # one piece per line: readable diffs
        f.write(",\n".join("  " + row for row in rows))
        f.write("\n ]\n}\n")


def load(path=None):
    path = path or TABLE
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        raise PieceError("no piece table yet (%s): run `forge_printer pieces --measure`" % os.path.basename(path))


def by_name(table=None):
    """{Forge menu name: piece} for the pieces whose menu name is known."""
    table = table or load()
    return {p["name"]: p for p in table["pieces"] if p["name_from"] != MODEL}


def at(row, item, table=None):
    """The piece a Forge World variant means by (type row, item), or None."""
    table = table or load()
    for p in table["pieces"]:
        if p["row"] == row and p["item"] == item:
            return p
    return None


def is_forge_world(variant):
    """Whether a variant uses the palette this table describes."""
    return variant.map_id == FORGE_WORLD_MAP_ID and len(variant.quotas) == FORGE_WORLD_QUOTA_ROWS


def show(table):
    category = None
    for p in table["pieces"]:
        if p["category"] != category:
            category = p["category"]
            print("%s (row %d)" % (category, p["row"]))
        mark = {NOTED: " ", MENU: "~", MODEL: "?"}[p["name_from"]]
        print(" %s %2d %-24s %-22s %6.2f x %6.2f x %6.2f   x %6.2f..%-6.2f y %6.2f..%-6.2f z %6.2f..%-6.2f" % (
            mark, p["item"], p["name"], p["model"], p["size"][0], p["size"][1], p["size"][2],
            p["min"][0], p["max"][0], p["min"][1], p["max"][1], p["min"][2], p["max"][2]))
    names = [p["name_from"] for p in table["pieces"]]
    print("%d pieces: %d from the owner's notes, %d named from the menu (~), %d known only by model (?)" % (
        len(names), names.count(NOTED), names.count(MENU), names.count(MODEL)))


def main(do_measure=False, keep=None):
    try:
        if do_measure:
            table = measure(keep or DEFAULT_KEEP)
            save(table)
            print("measured %d pieces; models kept in %s; table written to %s" % (
                len(table["pieces"]), keep or DEFAULT_KEEP, TABLE))
        show(load())
    except PieceError as error:
        print("pieces: %s" % error)
        return 1
    return 0
