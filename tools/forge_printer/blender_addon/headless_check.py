"""The add-on's checks inside a real Blender, run headless.

    blender --background --factory-startup --python-exit-code 1 --python tools\\forge_printer\\blender_addon\\headless_check.py
    ... -- --guardian FOLDER --template MVAR --offset DX DY DZ --out DIR      also the Guardian round trip

Without arguments it needs nothing from the game: it enables the add-on, prints the classes it
registered, and checks the slope-test orientations and the export refusals on objects Blender
itself made. With --guardian it opens that fit.json through the add-on, exports it unedited
into DIR (a new file) and compares the result with what `forge_printer print` writes for the
same fit, template and offset (written beside it). Every check prints one line starting
"check:"; the last line says how many failed, and the exit code is 1 if any did.

tools/test_forge_printer_addon_blender.py runs this when Blender is installed.
"""

import argparse
import io
import math
import os
import sys
from contextlib import redirect_stdout

import addon_utils
import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.realpath(__file__))
INSTALLED = "reach_forge_printer"
FAILED = []


def check(ok, text):
    print("check: %s  %s" % ("ok  " if ok else "FAIL", text))
    if not ok:
        FAILED.append(text)
    return ok


def enable():
    """Enables the add-on: as installed (install.py's link) when Blender finds it, else straight
    from this folder. Returns the add-on's ui module."""
    names = [m.__name__ for m in addon_utils.modules()]
    name = INSTALLED if INSTALLED in names else "blender_addon"
    if name != INSTALLED:
        sys.path.insert(0, os.path.dirname(HERE))
    mod = addon_utils.enable(name, default_set=False, persistent=True)
    check(mod is not None, "the add-on enables (as %r)" % name)
    ui = sys.modules[name + ".ui"]
    print("registered: " + ", ".join(c.__name__ for c in ui.CLASSES))
    check(all(getattr(bpy.types, c.__name__, None) is not None for c in ui.CLASSES), "every class is registered")
    return ui


def clear_pieces(ui):
    for o in ui.forge_objects(bpy.context.scene):
        bpy.data.objects.remove(o)


def add(ui, name, matrix=None):
    bpy.ops.forge_printer.add_piece(piece=name)
    obj = bpy.context.view_layer.objects.active
    if matrix is not None:
        obj.matrix_world = Matrix(matrix)
    return obj


def slope_cases(ui):
    from forge_printer import mvar, pieces, turn_test
    from forge_printer.blender_addon import convert, export
    known = pieces.by_name()
    written = {label: (turn, up) for label, name, _, turn, up in turn_test.slope_pieces(known)
               if name == turn_test.SLOPE_RAMP}
    for label, heading, slope in turn_test.SLOPE_CHECKS:
        around, lean = math.radians(heading), math.radians(slope)
        climb = (math.cos(around), math.sin(around))
        x = (math.cos(lean) * climb[0], math.cos(lean) * climb[1], math.sin(lean))
        z = (-math.sin(lean) * climb[0], -math.sin(lean) * climb[1], math.cos(lean))
        y = convert._cross(z, x)
        obj = add(ui, turn_test.SLOPE_RAMP, [[x[i], y[i], z[i], 3.0 * i] for i in range(3)] + [[0, 0, 0, 1]])
        bpy.context.view_layer.update()                     # Blender's own loc/rot/scale -> matrix, in 32 bits
        e = ui.entry_for(obj)
        p = e["placement"]
        if not check(p is not None, "%s exports (%s)" % (label, e["reason"])):
            continue
        raw_turn = mvar.encode_angle(math.radians(p["turn"]))
        raw_up = mvar.up_raw(p["up"])
        want_turn, want_up = written[label]
        steps = abs(raw_turn - want_turn) % 16384
        steps = min(steps, 16384 - steps)
        a, b = export._up_parts(raw_up), export._up_parts(want_up)
        check(steps <= 1 and a[0] == b[0] and abs(a[1] - b[1]) <= 1 and abs(a[2] - b[2]) <= 1,
              "%s heading %g slope %g: turn %d (slope test %d), up %s (slope test %s)" % (
                  label, heading, slope, raw_turn, want_turn, a, b))
    clear_pieces(ui)


def refusals(ui):
    from forge_printer.blender_addon import export
    from test_forge_printer_turn_test import forge_world
    scaled = add(ui, "Block 2x2 Flat")
    scaled.scale = (1.2, 1.2, 1.2)
    leaning = add(ui, "Block 5x1 Flat")
    leaning.rotation_euler = (math.radians(50.0), 0.0, 0.0)          # tips +z towards -y: 50 from +Z, 90 from +X
    outside = add(ui, "Block 2x2 Flat")
    outside.location = (400.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    pairs = ui.scene_entries(bpy.context.scene)
    result = export.plan([e for _, e in pairs], forge_world(), (-40.0, -140.0, 10.0))
    reasons = dict(result["refused"])
    check("scaled 1.20" in reasons.get(scaled.name, ""), "a piece scaled 1.2 is refused: %s" % reasons.get(scaled.name))
    check("leans 50" in reasons.get(leaning.name, ""), "a piece leaning 50 degrees is refused: %s" % reasons.get(leaning.name))
    check("outside Forge World" in reasons.get(outside.name, ""), "a piece outside the bounds is refused: %s" %
          reasons.get(outside.name))
    clear_pieces(ui)
    for n in range(256):
        add(ui, "Block 1x1 Flat").location = (-50.0 + (n % 16) * 1.1, -50.0 + (n // 16) * 1.1, 0.0)
    bpy.context.view_layer.update()
    pairs = ui.scene_entries(bpy.context.scene)
    result = export.plan([e for _, e in pairs], forge_world(), (-40.0, -140.0, 10.0))
    check(len(result["kept"]) == 255 and len(result["left_out"]) == 1 and result["counts"]["rows_over"] == {70: 1},
          "256 pieces in one row: %d kept, %d left out (%s)" % (len(result["kept"]), len(result["left_out"]),
                                                               result["left_out"][:1]))
    clear_pieces(ui)


def guardian(ui, folder, template, offset, out_dir):
    import json
    from forge_printer import fit, mvar
    from forge_printer.blender_addon import export
    fit_path = os.path.join(folder, "fit.json")
    with open(fit_path, encoding="utf-8") as f:
        placements = json.load(f)["placements"]
    scene = bpy.context.scene
    bpy.ops.forge_printer.open_fit(filepath=fit_path, offset=offset, backdrop=True, real_models=True, replace=True)
    objs = ui.forge_objects(scene)
    check(len(objs) == len(placements), "opened %d objects for %d placements" % (len(objs), len(placements)))
    parts = sorted(c.name for c in bpy.data.collections if c.name.startswith("Forge ") and c.objects)
    print("collections: " + ", ".join("%s %d" % (c, len(bpy.data.collections[c].objects)) for c in parts))
    backdrop = bpy.data.collections.get(ui.BACKDROP)
    check(backdrop is not None and len(backdrop.objects) > 0 and all(o.hide_select for o in backdrop.objects),
          "the reference backdrop is loaded and cannot be selected (%d objects)" % (len(backdrop.objects) if backdrop else 0))
    if backdrop is not None:
        def hidden(kind):
            return {o.hide_get() for o in backdrop.objects if o.get("fp_backdrop") == kind}
        start = (hidden("floor"), hidden("wall"), hidden("ceiling"))
        scene.fp_show_wall = False
        walls_off = (hidden("floor"), hidden("wall"))
        scene.fp_show_wall = True
        check(start == ({False}, {False}, {True}) and walls_off == ({False}, {True}) and hidden("wall") == {False},
              "backdrop switches: walls hide and come back, floors stay, ceilings start hidden %s %s"
              % (start, walls_off))
    models = sorted(set(o.data.name for o in objs))
    print("meshes: " + ", ".join(models))

    # the counter against within_limits for this scene
    pairs = ui.scene_entries(scene)
    good = [e["placement"] for _, e in pairs if e["placement"] is not None]
    check(len(good) == len(pairs), "every opened piece can be written (%d refused)" % (len(pairs) - len(good)))
    scene.fp_template = template
    f, error = ui.template_of(scene)
    counts = export.count(good, f.variant)
    free, budget, rows = export.room(f.variant)
    kept, report = fit.within_limits(good, free, budget, rows)
    print("counter: objects %d of %d, rows %s, budget %d of %d, %d unpriced" % (
        counts["slots_used"], counts["slots_max"], counts["rows"], counts["budget_spent"], counts["budget_max"],
        counts["unpriced"]))
    print("within_limits: kept %d, left out %d %s, out of %s, cost %d" % (
        report["kept"], report["left_out"], report["by_part"], report["ran_out_of"], report["cost"]))
    over = sum(counts["rows_over"].values()) + counts["slots_over"]
    check(over == report["left_out"], "the counter's pieces over the limits (%d) equal within_limits' left out (%d)" % (
        over, report["left_out"]))
    priced_kept = sum(1 for p in kept if p["piece"] not in report["unpriced"])
    check(counts["unpriced"] == sum(1 for p in good if p["piece"] in report["unpriced"]),
          "the counter's unpriced pieces (%d) are within_limits' unpriced kinds" % counts["unpriced"])
    check(report["cost"] == 10 * priced_kept or report["unpriced"], "within_limits' cost %d" % report["cost"])

    # export unedited, and print the same fit
    scene.fp_out_dir = out_dir
    scene.fp_title = "FP Guardian addon"
    before = set(os.listdir(out_dir))
    bpy.ops.forge_printer.export(accept=True)
    new = sorted(set(os.listdir(out_dir)) - before)
    if not check(len(new) == 1, "the export wrote one new file: %s" % new):
        return
    exported = os.path.join(out_dir, new[0])
    text = bpy.data.texts[ui.REPORT_TEXT].as_string()
    print("export report:\n  " + "\n  ".join(text.strip().splitlines()[:6]))
    check("44 piece(s) do not fit" in text or report["left_out"] == 0,
          "the export names the shortfall print has (%d left out)" % report["left_out"])
    printed = os.path.join(out_dir, "printed_" + new[0])
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = fit.print_main(folder, template, printed, offset)
    print("print: " + buf.getvalue().strip().replace("\n", "\n  print: "))
    if not check(code == 0, "forge_printer print wrote %s" % printed):
        return
    a, b = mvar.MvarFile.read(printed).variant, mvar.MvarFile.read(exported).variant
    diffs = export.differences(a, b)
    added = len(b.placed_objects()) - len(f.variant.placed_objects())
    check(not diffs, "the export's %d added objects equal print's %d: %d differ" % (
        added, len(a.placed_objects()) - len(f.variant.placed_objects()), len(diffs)))
    for slot, why in diffs[:20]:
        print("  slot %d: %s" % (slot, why))
    check(b.budget_spent == a.budget_spent and not b.problems(), "budget %d (print %d), problems %s" % (
        b.budget_spent, a.budget_spent, b.problems()))

    # a few pieces moved and turned by hand: only they change, by what was done to them
    moved = objs[:3]
    for o in moved:
        o.location.x += 1.0
        o.rotation_euler.z += math.radians(90.0)
    bpy.context.view_layer.update()
    before = set(os.listdir(out_dir))
    bpy.ops.forge_printer.export(accept=True)
    new = sorted(set(os.listdir(out_dir)) - before)
    if check(len(new) == 1, "a second export is a new file, the first left alone: %s" % new):
        c = mvar.MvarFile.read(os.path.join(out_dir, new[0])).variant
        diffs = export.differences(b, c)
        slots = [slot for slot, _ in diffs]
        first = len(f.variant.placed_objects())
        check(slots == [first, first + 1, first + 2], "after moving three pieces only their slots differ: %s" % diffs)
        ok = True
        for slot in slots:
            pb, pc = b.world_position(b.objects[slot]), c.world_position(c.objects[slot])
            turn = (c.objects[slot].angle - b.objects[slot].angle) % 16384
            ok = ok and abs(pc[0] - pb[0] - 1.0) < 0.002 and abs(pc[1] - pb[1]) < 0.002 and abs(turn - 4096) <= 1
        check(ok, "each moved 1 along +x and turned 90 degrees in the file")


def library_check(ui):
    """A two-piece asset library: assets with thumbnails and catalogs, and a piece taken from it is
    exported like one from the palette. Runs last: building starts an empty file. Nothing is saved to
    the preferences (factory settings)."""
    import tempfile
    from forge_printer.blender_addon import library
    with tempfile.TemporaryDirectory() as folder:
        path, made, _ = library.build(folder, only={"Wall Double", "Block 2x2 Flat"})
        check(made == 2 and os.path.isfile(path), "the library builds (%d assets)" % made)
        with open(os.path.join(folder, library.CATALOG_FILE), encoding="utf-8") as f:
            check(library.catalog_id("Building Blocks") in f.read(), "its catalogs are written")
        bpy.ops.wm.read_homefile(use_empty=True)
        with bpy.data.libraries.load(path, link=False, assets_only=True) as (src, dst):
            dst.objects = list(src.objects)
        objs = [o for o in dst.objects if o is not None]
        check(len(objs) == 2 and all(o.asset_data and o.preview and any(o.preview.image_pixels_float[:4000])
                                     for o in objs), "both are assets with a thumbnail")
        scene = bpy.context.scene
        for i, o in enumerate(objs):
            scene.collection.objects.link(o)
            o.location = (3.0 * i, 1.0, 2.0)
        bpy.context.view_layer.update()
        entries = ui.scene_entries(scene)
        check(len(entries) == 2 and all(e["placement"] is not None for _, e in entries),
              "pieces taken from the library are Forge pieces that export: %s" % [
                  (e["placement"] or {}).get("piece") for _, e in entries])
        entry = library.register_library(folder)
        check(entry.name == library.LIBRARY_NAME and os.path.normcase(entry.path) == os.path.normcase(folder),
              "it can be added to the Asset Browser's libraries")


def starter_check(ui):
    """The starter scene on a made-up terrain (one 400 x 400 square) and the test suite's Forge World
    variant: the ground and the template's objects come in locked and unexported, the template is chosen
    and the offset is 0 0 0. Runs last (it starts an empty file)."""
    import tempfile
    from forge_printer import mvar
    from forge_printer.blender_addon import library
    from test_forge_printer_turn_test import forge_world
    with tempfile.TemporaryDirectory() as folder:
        ground = os.path.join(folder, "ground.obj")
        with open(ground, "w") as f:
            f.write("v -200 -200 0\nv 200 -200 0\nv 200 200 0\nv -200 200 0\nf 1 2 3\nf 1 3 4\n")
        v = forge_world()
        template = os.path.join(folder, "template.mvar")
        mvar.MvarFile(variant=v, chdr=mvar.build_chdr(v.header)).write(template)
        path, made = library.build_starter(folder, ground, template)
        check(made == len(v.placed_objects()), "the template's %d objects are shown" % made)
        bpy.ops.wm.open_mainfile(filepath=path)
        scene = bpy.context.scene
        check(os.path.normcase(bpy.path.abspath(scene.fp_template)) == os.path.normcase(template) and
              tuple(scene.fp_offset) == (0.0, 0.0, 0.0), "the starter chooses the template, offset 0 0 0")
        check(ui.forge_objects(scene) == [] and all(o.hide_select for o in bpy.data.objects),
              "the ground and the template's objects are locked and not counted as pieces")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="headless_check")
    parser.add_argument("--guardian")
    parser.add_argument("--template")
    parser.add_argument("--offset", type=float, nargs=3, default=(-39.0, -135.0, 8.0))
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    print("blender %s" % bpy.app.version_string)
    ui = enable()
    slope_cases(ui)
    refusals(ui)
    if args.guardian:
        guardian(ui, args.guardian, args.template, tuple(args.offset), args.out)
    library_check(ui)
    starter_check(ui)
    print("checks: %d failed" % len(FAILED))
    if FAILED:
        sys.exit(1)


main()
