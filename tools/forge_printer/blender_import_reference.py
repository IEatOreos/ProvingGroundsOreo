"""Loads a forge_printer reference folder into Blender (phase 2: no addon, no UI).

    blender --python tools\\forge_printer\\blender_import_reference.py -- <folder>
    blender --background --python tools\\forge_printer\\blender_import_reference.py -- <folder>

The folder is what `forge_printer reference <map>` wrote: <map>.obj and
reference.json, already in Reach units. The mesh comes in Z up, one Blender
unit per world unit, unchanged; every placement becomes a named empty in the
collections spawns, weapons, objectives and other. Prints what it loaded.
"""

import json
import os
import sys

import bpy

GROUPS = ("spawns", "weapons", "objectives", "other")
EMPTY = {"spawns": "SINGLE_ARROW", "weapons": "CUBE", "objectives": "CONE", "other": "SPHERE"}


def folder_arg():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        raise SystemExit("usage: blender --python blender_import_reference.py -- <reference folder>")
    return argv[0]


def collection(name, parent):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in parent.children:
        parent.children.link(c)
    return c


def label(group, item, n):
    what = item.get("name") or item.get("type") or item.get("kind") or group
    return "%s_%03d_%s" % (group[:-1] if group.endswith("s") else group, n, what)


def load(folder):
    with open(os.path.join(folder, "reference.json"), encoding="utf-8") as f:
        ref = json.load(f)
    mesh_path = os.path.join(folder, ref["mesh"])
    if not os.path.isfile(mesh_path):
        raise SystemExit("reference: %s is missing" % mesh_path)

    root = bpy.context.scene.collection
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=mesh_path, forward_axis="Y", up_axis="Z", global_scale=1.0)
    meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    level = collection("level", root)
    for o in meshes:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        level.objects.link(o)
        o.name = ref["source"]["map"]

    counts = {}
    for group in GROUPS:
        coll = collection(group, root)
        for n, item in enumerate(ref.get(group, [])):
            e = bpy.data.objects.new(label(group, item, n), None)
            e.empty_display_type = EMPTY[group]
            e.empty_display_size = 0.3
            e.location = item["pos"]
            e.rotation_euler = (0.0, 0.0, float(item.get("facing") or 0.0))
            for key, value in item.items():
                if key not in ("pos",) and isinstance(value, (int, float, str)):
                    e["ref_" + key] = value
            coll.objects.link(e)
        counts[group] = len(ref.get(group, []))

    lo, hi = [float("inf")] * 3, [float("-inf")] * 3
    tris = 0
    for o in meshes:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            for i in range(3):
                lo[i], hi[i] = min(lo[i], w[i]), max(hi[i], w[i])
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    want = ref["bounds"]
    worst = max(abs(a - b) for a, b in zip(lo + hi, want["min"] + want["max"]))

    print("reference: loaded %s" % folder)
    print("reference: objects %d (%d mesh, %d empties)" % (len(meshes) + sum(counts.values()), len(meshes),
                                                          sum(counts.values())))
    print("reference: empties " + ", ".join("%s %d" % (g, counts[g]) for g in GROUPS))
    print("reference: mesh triangles %d" % tris)
    print("reference: mesh box x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f" % (lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    print("reference: box vs reference.json bounds: max difference %.4f (%s)" % (worst, "ok" if worst <= 0.01 else "MISMATCH"))
    return 0 if worst <= 0.01 else 1


if __name__ == "__main__":
    code = load(folder_arg())
    if bpy.app.background:
        sys.exit(code)
