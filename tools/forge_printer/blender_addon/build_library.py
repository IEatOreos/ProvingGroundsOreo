"""Build the Reach Forge pieces asset library and add it to Blender's Asset Browser.

    python\\python.exe tools\\forge_printer\\blender_addon\\build_library.py          build, then add it to Blender
    ... [--out FOLDER] [--blender PATH] [--no-register]

Builds "Reach Forge Pieces.blend" (every named piece as an asset with its real model and a rendered
thumbnail, one catalog a Forge category) in re_tools\\forge_printer\\asset_library, never in the
repository: it holds the game's models. The build runs in a background Blender with factory settings,
so it never touches your Blender's preferences. Then, if Blender is closed, a second background
Blender adds the folder as the asset library "Reach Forge Pieces" and saves the preferences; with
Blender open that step is skipped and the way to add it by hand is printed.

Phase 4 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLS)

from forge_printer.blender_addon import install  # noqa: E402

MARK = install.MARK


def default_out():
    from forge_printer import pieces
    return os.path.join(os.path.dirname(pieces.DEFAULT_KEEP), "asset_library")


def run(blender, expr, factory, timeout=1200):
    args = [blender, "--background"] + (["--factory-startup"] if factory else []) + [
        "--python-exit-code", "1", "--python-expr", expr]
    done = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=timeout)
    ours = [line[len(MARK):].strip() for line in done.stdout.splitlines() if line.startswith(MARK)]
    if done.returncode and not ours:
        ours = (done.stderr or done.stdout).strip().splitlines()[-8:]
    return done.returncode, ours


def build(blender, out):
    code, lines = run(blender, (
        "import sys\n"
        "sys.path.insert(0, %r)\n"
        "from forge_printer.blender_addon import library\n"
        "path, made, boxes = library.build(%r)\n"
        "print(%r + 'wrote %%s: %%d pieces, %%d of them boxes (no model exported)' %% (path, made, boxes))\n"
    ) % (TOOLS, out, MARK), factory=True)
    for line in lines:
        print("library: " + line)
    return code


def register(blender, out):
    code, lines = run(blender, (
        "import sys, bpy\n"
        "sys.path.insert(0, %r)\n"
        "from forge_printer.blender_addon import library\n"
        "entry = library.register_library(%r)\n"
        "bpy.ops.wm.save_userpref()\n"
        "print(%r + 'Asset Browser library %%r -> %%s' %% (entry.name, entry.path))\n"
    ) % (TOOLS, out, MARK), factory=False, timeout=300)
    for line in lines:
        print("library: " + line)
    return code


TERRAIN_MARGIN = 30.0     # world units of Forge World's level kept beyond the area Forge can place in


def terrain(folder, bounds, mcc=None, bsp2obj=None):
    """Forge World's own level (bsp2obj on haloreach\\maps\\forge_halo.map), turned Z up, cut to the area a
    variant can place objects in plus TERRAIN_MARGIN: <folder>\\forge_world.obj. Returns (path, triangles)."""
    import tempfile

    import numpy as np

    from forge_printer import h3_reference, pieces, surfaces
    sys.path.insert(0, os.path.join(os.path.dirname(TOOLS), "brain"))
    import paths
    mcc = mcc or paths.mcc()
    bsp2obj = bsp2obj or paths.map_tool("bsp2obj")
    if not mcc or not bsp2obj:
        raise SystemExit("library: MCC or bsp2obj.exe was not found (see brain/paths.py)")
    source = os.path.join(mcc, *pieces.MAP)
    os.makedirs(folder, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        raw = os.path.join(tmp, "raw.obj")
        done = subprocess.run([bsp2obj, source, raw], capture_output=True, text=True, timeout=1200)
        if done.returncode or not os.path.isfile(raw):
            raise SystemExit("library: bsp2obj failed: %s" % (done.stderr or done.stdout).strip()[-300:])
        verts, tris = surfaces.load_obj(raw)
    verts = np.array([h3_reference.world(*v) for v in verts.tolist()], dtype=float)   # its Y up to the game's Z up
    lo = np.array(bounds[0::2]) - TERRAIN_MARGIN
    hi = np.array(bounds[1::2]) + TERRAIN_MARGIN
    centres = verts[tris].mean(axis=1)
    keep = tris[np.all((centres >= lo) & (centres <= hi), axis=1)]
    used, index = np.unique(keep, return_inverse=True)
    path = os.path.join(folder, "forge_world.obj")
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write("# Forge World's level (forge_halo.map), Z up, Reach units, cut to the Forge area\n")
        f.writelines("v %.4f %.4f %.4f\n" % tuple(v) for v in verts[used])
        f.writelines("f %d %d %d\n" % tuple(t + 1) for t in index.reshape(-1, 3))
    return path, len(keep)


def starter(blender, folder, template):
    from forge_printer import mvar
    bounds = mvar.MvarFile.read(template).variant.bounds
    path, count = terrain(folder, bounds)
    print("library: wrote %s: %d triangles of Forge World's level" % (path, count))
    code, lines = run(blender, (
        "import sys\n"
        "sys.path.insert(0, %r)\n"
        "from forge_printer.blender_addon import library\n"
        "path, made = library.build_starter(%r, %r, %r)\n"
        "print(%r + 'wrote %%s: Forge World and %%d template objects, template set, offset 0 0 0' %% (path, made))\n"
    ) % (TOOLS, folder, path, template, MARK), factory=True)
    for line in lines:
        print("library: " + line)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the Reach Forge pieces asset library for Blender")
    parser.add_argument("--out", help="folder for the library (default: re_tools\\forge_printer\\asset_library)")
    parser.add_argument("--blender", help="blender.exe to use (default: the newest under Program Files)")
    parser.add_argument("--no-register", action="store_true", help="build only; do not add it to Blender")
    parser.add_argument("--starter", metavar="TEMPLATE",
                        help="build the starter scene on this Forge World variant (one your MCC saved) instead")
    args = parser.parse_args(argv)
    blender = install.find_blender(args.blender)
    if not blender:
        print("library: Blender was not found; give it with --blender PATH")
        return 1
    if args.starter:
        folder = os.path.abspath(args.out or os.path.join(os.path.dirname(default_out()), "starter"))
        print("library: building the starter scene in %s (a few minutes: Forge World's level is large)" % folder)
        if starter(blender, folder, os.path.abspath(args.starter)):
            print("library: the starter scene failed (see above)")
            return 1
        print("library: done. Open \"Reach Forge Starter.blend\" there and save it under a new name to start a map")
        return 0
    out = os.path.abspath(args.out or default_out())
    print("library: using %s, building in %s (a minute or two)" % (blender, out))
    if build(blender, out):
        print("library: the build failed (see above)")
        return 1
    if args.no_register:
        return 0
    if install.blender_running():
        print("library: Blender is open, so it was not added to the Asset Browser. Either close Blender and run")
        print("library: this again, or in Blender: Edit > Preferences > File Paths > Asset Libraries > +, choose")
        print("library: %s and name it \"Reach Forge Pieces\" (or use the Forge palette's \"Add piece library\" button)." % out)
        return 0
    if register(blender, out):
        print("library: adding it to Blender failed (see above)")
        return 1
    print("library: done. In Blender: open an Asset Browser, choose \"Reach Forge Pieces\" and drag pieces in")
    return 0


if __name__ == "__main__":
    sys.exit(main())
