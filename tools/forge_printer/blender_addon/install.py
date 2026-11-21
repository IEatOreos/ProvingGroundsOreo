"""Install the Reach Forge Printer add-on into Blender: the one step.

    python\\python.exe tools\\forge_printer\\blender_addon\\install.py            install and enable
    python\\python.exe tools\\forge_printer\\blender_addon\\install.py --remove   disable and unlink
    ... [--blender PATH]                                                         another Blender

Close Blender first. This puts a link (a directory junction, no copy) named
reach_forge_printer in Blender's own add-ons folder, pointing at this folder, then starts
Blender once in the background to enable the add-on and save that in its preferences. Because
it is a link, Blender always runs the repository's current version. Removing it deletes only
the link, never this folder.

Phase 4 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import argparse
import glob
import os
import subprocess
import sys

MODULE = "reach_forge_printer"
HERE = os.path.dirname(os.path.realpath(__file__))
MARK = "FORGE_PRINTER:"


def find_blender(given=None):
    """The newest Blender under Program Files, or the one given (or in the BLENDER environment variable)."""
    for path in (given, os.environ.get("BLENDER")):
        if path:
            return path if os.path.isfile(path) else None
    roots = [os.environ.get("ProgramFiles", r"C:\Program Files")]
    found = []
    for root in roots:
        found += glob.glob(os.path.join(root, "Blender Foundation", "Blender*", "blender.exe"))

    def version(path):
        name = os.path.basename(os.path.dirname(path)).replace("Blender", "").strip()
        try:
            return tuple(int(n) for n in name.split("."))
        except ValueError:
            return ()
    return max(found, key=version) if found else None


def run_blender(blender, expr, factory=False):
    """Runs a line of Python in a background Blender; returns (exit code, lines our script printed)."""
    args = [blender, "--background"] + (["--factory-startup"] if factory else []) + [
        "--python-exit-code", "1", "--python-expr", expr]
    run = subprocess.run(args, capture_output=True, text=True, errors="replace", timeout=300)
    ours = [line[len(MARK):].strip() for line in run.stdout.splitlines() if line.startswith(MARK)]
    if run.returncode and not ours:
        ours = (run.stderr or run.stdout).strip().splitlines()[-5:]
    return run.returncode, ours


def blender_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq blender.exe", "/NH"], capture_output=True, text=True,
                             timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return "blender.exe" in out.lower()


def addons_folder(blender):
    code, out = run_blender(blender, "import bpy; print(%r + bpy.utils.user_resource('SCRIPTS', path='addons', "
                                     "create=True))" % MARK, factory=True)
    if code or not out:
        raise SystemExit("install: Blender did not say where its add-ons go: %s" % " / ".join(out))
    return out[-1]


def is_link_here(path):
    return os.path.isdir(path) and (os.path.isjunction(path) or os.path.islink(path)) and \
        os.path.normcase(os.path.realpath(path)) == os.path.normcase(HERE)


def install(blender):
    link = os.path.join(addons_folder(blender), MODULE)
    if os.path.lexists(link) and not is_link_here(link):
        raise SystemExit("install: %s is already there and is not a link to this folder; move it away first" % link)
    if not os.path.lexists(link):
        import _winapi
        _winapi.CreateJunction(HERE, link)
    print("install: linked %s -> %s" % (link, HERE))
    code, out = run_blender(blender, (
        "import addon_utils, bpy, sys\n"
        "mod = addon_utils.enable(%r, default_set=True, persistent=True)\n"
        "if mod is None: print(%r + 'not enabled'); sys.exit(1)\n"
        "bpy.ops.wm.save_userpref()\n"
        "from %s import ui\n"
        "print(%r + 'enabled ' + ', '.join(c.__name__ for c in ui.CLASSES))\n") % (MODULE, MARK, MODULE, MARK))
    for line in out:
        print("install: " + line)
    if code:
        print("install: Blender could not enable the add-on (see above)")
        return 1
    print("install: done. In Blender: the 3D view's sidebar (press N), tab \"Forge\"")
    return 0


def remove(blender):
    link = os.path.join(addons_folder(blender), MODULE)
    code, out = run_blender(blender, (
        "import addon_utils, bpy\n"
        "addon_utils.disable(%r, default_set=True)\n"
        "bpy.ops.wm.save_userpref()\n"
        "print(%r + 'disabled')\n") % (MODULE, MARK))
    for line in out:
        print("remove: " + line)
    if os.path.lexists(link):
        if not is_link_here(link):
            print("remove: %s is not a link to this folder; left alone" % link)
            return 1
        os.rmdir(link)                    # removes the junction only, never what it points at
        print("remove: unlinked %s" % link)
    return 0 if not code else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install the Reach Forge Printer add-on into Blender")
    parser.add_argument("--remove", action="store_true", help="disable the add-on and remove the link")
    parser.add_argument("--blender", help="blender.exe to use (default: the newest under Program Files)")
    args = parser.parse_args(argv)
    blender = find_blender(args.blender)
    if not blender:
        print("install: Blender was not found; give it with --blender PATH")
        return 1
    if blender_running():
        print("install: close Blender first, then run this again (it saves Blender's preferences)")
        return 1
    print("install: using %s" % blender)
    return remove(blender) if args.remove else install(blender)


if __name__ == "__main__":
    sys.exit(main())
