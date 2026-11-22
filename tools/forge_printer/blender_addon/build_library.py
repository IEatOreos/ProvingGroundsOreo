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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the Reach Forge pieces asset library for Blender")
    parser.add_argument("--out", help="folder for the library (default: re_tools\\forge_printer\\asset_library)")
    parser.add_argument("--blender", help="blender.exe to use (default: the newest under Program Files)")
    parser.add_argument("--no-register", action="store_true", help="build only; do not add it to Blender")
    args = parser.parse_args(argv)
    blender = install.find_blender(args.blender)
    if not blender:
        print("library: Blender was not found; give it with --blender PATH")
        return 1
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
