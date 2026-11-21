"""Reach Forge Printer, phase 4: counting a scene against a variant's limits, and exporting it.

No bpy here: the test suite imports this module. The addon turns each Forge object into an
entry, {"label": object name, "placement": ..., "reason": ..., "warning": ...} (convert.py's
placement_from), and hands the list over in the order to write it.

Writing goes through the proven code only: `fit.within_limits` chooses what fits (slots,
budget, 255 pieces a palette row), `fit.add_to` adds it to a copy of the template, and
`MapVariant.problems()` has the last word. Nothing is written over an existing file.

Phase 4 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import os
import re

from forge_printer import fit, mvar, pieces

from . import convert

DEFAULT_OUT = r"E:\Proving Grounds\re_tools\forge_printer"
TITLE_MAX = 31          # what `print` keeps of a title
ROW_NAMES = {row: name for name, row in pieces.ROWS.items()}


class ExportError(Exception):
    """A clear one-line reason nothing was written."""


def row_name(row):
    return "%s (row %d)" % (ROW_NAMES[row], row) if row in ROW_NAMES else "row %d" % row


def load_template(path):
    """The template as an MvarFile, its quotas recounted. Raises ExportError."""
    if not path:
        raise ExportError("choose a template: a Forge World variant your MCC saved")
    try:
        f = mvar.MvarFile.read(path)
    except OSError as error:
        raise ExportError("the template cannot be read: %s" % error)
    except mvar.FormatError as error:
        raise ExportError("the template is not a map variant this tool reads: %s" % error)
    if not pieces.is_forge_world(f.variant):
        raise ExportError("the template must be a Forge World variant on today's palette (map %d, %d quota rows)" % (
            pieces.FORGE_WORLD_MAP_ID, pieces.FORGE_WORLD_QUOTA_ROWS))
    f.variant.recount_quotas()
    return f


def room(variant):
    """(free slots, budget left, {row: pieces it can still take}) of a variant, as `print` works them out."""
    free = sum(1 for o in variant.objects if o is None)
    return free, variant.budget_max - variant.budget_spent, {
        row: mvar.ROW_MAX - quota.placed for row, quota in enumerate(variant.quotas)}


def count(placements, variant=None, table=None):
    """The live counter's figures for these placements on top of the template (None: an empty one).

    {"slots_used", "slots_max", "slots_over", "rows": {row: pieces}, "rows_over": {row: pieces too
    many}, "budget_added", "budget_spent", "budget_max" (None without a template), "budget_over",
    "unpriced": pieces with no known price (not counted in the budget), "unpriced_names"}."""
    known = pieces.by_name(table)
    rows = {}
    if variant is not None:
        for row, quota in enumerate(variant.quotas):
            if quota.placed:
                rows[row] = quota.placed
    names = []
    for p in placements:
        row = known[p["piece"]]["row"]
        rows[row] = rows.get(row, 0) + 1
        names.append(p["piece"])
    added, unpriced_names = pieces.cost(names)
    used = len(placements) + (len(variant.placed_objects()) if variant is not None else 0)
    spent = added + (variant.budget_spent if variant is not None else 0)
    budget_max = variant.budget_max if variant is not None else None
    return {"slots_used": used, "slots_max": mvar.OBJECT_SLOTS, "slots_over": max(0, used - mvar.OBJECT_SLOTS),
            "rows": rows, "rows_over": {row: n - mvar.ROW_MAX for row, n in rows.items() if n > mvar.ROW_MAX},
            "budget_added": added, "budget_spent": spent, "budget_max": budget_max,
            "budget_over": max(0, spent - budget_max) if budget_max is not None else 0,
            "unpriced": sum(1 for name in names if pieces.price(name) is None), "unpriced_names": unpriced_names}


def _outside(variant, position):
    b = variant.bounds
    return any(not b[i * 2] <= position[i] <= b[i * 2 + 1] for i in range(3))


def plan(entries, variant, offset, table=None):
    """What an export would write. Nothing is written here.

    Returns {"kept": placements to write, in order; "kept_labels"; "refused": [(label, reason)],
    pieces that cannot be written at all; "left_out": [(label, why)], pieces that can be written
    but do not fit; "warnings": [(label, text)]; "report": within_limits' report; "counts": the
    counter's figures for every writable piece}."""
    refused, warnings, candidates = [], [], []
    for entry in entries:
        label, p = entry["label"], entry.get("placement")
        if p is None:
            refused.append((label, entry.get("reason") or "it cannot be written"))
            continue
        if entry.get("warning"):
            warnings.append((label, entry["warning"]))
        at = tuple(p["origin"][i] + offset[i] for i in range(3))
        if _outside(variant, at):
            refused.append((label, "it is outside Forge World's bounds, at (%.1f, %.1f, %.1f) in Forge World: "
                                   "move it, or change the offset" % at))
            continue
        candidates.append((label, p))
    free, budget_left, row_room = room(variant)
    kept, report = fit.within_limits([p for _, p in candidates], free, budget_left, row_room, table)
    kept_ids = set(id(p) for p in kept)
    left_out = [(label, "out of %s" % report["ran_out_of"]) for label, p in candidates if id(p) not in kept_ids]
    return {"kept": kept, "kept_labels": [label for label, p in candidates if id(p) in kept_ids],
            "refused": refused, "left_out": left_out, "warnings": warnings, "report": report,
            "counts": count([p for _, p in candidates], variant, table)}


def lines(result, limit=None):
    """The plan's problems in words, one line each; empty when everything will be written."""
    out = []
    if result["refused"]:
        out.append("%d piece(s) cannot be written:" % len(result["refused"]))
        out.extend("  %s: %s" % item for item in result["refused"][:limit])
        if limit is not None and len(result["refused"]) > limit:
            out.append("  ... and %d more" % (len(result["refused"]) - limit))
    if result["left_out"]:
        report, counts = result["report"], result["counts"]
        out.append("%d piece(s) do not fit and would be left out (%s), out of %s:" % (
            len(result["left_out"]), ", ".join("%d %s" % (n, part) for part, n in sorted(report["by_part"].items())),
            report["ran_out_of"]))
        for row, over in sorted(counts["rows_over"].items()):
            out.append("  %s would hold %d pieces; a row holds %d" % (row_name(row), counts["rows"][row], mvar.ROW_MAX))
        if counts["slots_over"]:
            out.append("  %d objects of %d slots" % (counts["slots_used"], counts["slots_max"]))
        if counts["budget_over"]:
            out.append("  budget %d of %d" % (counts["budget_spent"], counts["budget_max"]))
        out.extend("  %s: %s" % item for item in result["left_out"][:limit])
        if limit is not None and len(result["left_out"]) > limit:
            out.append("  ... and %d more" % (len(result["left_out"]) - limit))
    if result["warnings"]:
        out.append("%d warning(s):" % len(result["warnings"]))
        out.extend("  %s: %s" % item for item in result["warnings"][:limit])
    return out


def _up_parts(raw):
    raw = convert.STRAIGHT_UP if raw is None else raw     # "the world's up" and the +Z face's middle are one direction
    face, rest = divmod(raw, mvar.UP_FACE_SPAN)
    return (face,) + divmod(rest, mvar.UP_GRID)


def differences(expected, got, position=0.002, turn_steps=1, up_steps=1):
    """Slot by slot, how two variants' objects differ beyond the tolerances (the brief's: position
    within 0.002, raw turn within one step, raw up within one grid step of u and v). Returns
    [(slot, what)]; empty when they match."""
    out = []
    for slot, (a, b) in enumerate(zip(expected.objects, got.objects)):
        if a is None or b is None:
            if (a is None) != (b is None):
                out.append((slot, "only in the %s" % ("first" if b is None else "second")))
            continue
        why = []
        if (a.type_index, a.variant_index) != (b.type_index, b.variant_index):
            why.append("piece %s.%s against %s.%s" % (a.type_index, a.variant_index, b.type_index, b.variant_index))
        pa, pb = expected.world_position(a), got.world_position(b)
        gap = max(abs(pa[i] - pb[i]) for i in range(3))
        if gap > position:
            why.append("%.4f apart" % gap)
        steps = abs(a.angle - b.angle) % (1 << mvar.ANGLE_BITS)
        steps = min(steps, (1 << mvar.ANGLE_BITS) - steps)
        if steps > turn_steps:
            why.append("turn %d steps apart" % steps)
        ua, ub = _up_parts(a.up), _up_parts(b.up)
        if ua[0] != ub[0] or abs(ua[1] - ub[1]) > up_steps or abs(ua[2] - ub[2]) > up_steps:
            why.append("up face %d (%d, %d) against face %d (%d, %d)" % (ua + ub))
        if a.placement_flags != b.placement_flags:
            why.append("flags %d against %d" % (a.placement_flags, b.placement_flags))
        if why:
            out.append((slot, ", ".join(why)))
    return out


def free_path(folder, stem):
    """A path in folder for a new file named after stem that does not exist yet: FP_x.mvar, FP_x_2.mvar, ..."""
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "FP_Map"
    if not stem.startswith("FP_"):
        stem = "FP_" + stem
    path, n = os.path.join(folder, stem + ".mvar"), 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(folder, "%s_%d.mvar" % (stem, n))
    return path


def write(template_path, result, offset, out_path, title, table=None):
    """Writes the plan's kept pieces into a copy of the template at out_path (never over a file).
    Returns {"path", "slots", "objects", "budget_spent", "budget_max", "title"}. Raises ExportError."""
    if not result["kept"]:
        raise ExportError("nothing to write: no piece can be written")
    f = load_template(template_path)          # a fresh copy: planning never changes the template
    v = f.variant
    try:
        slots = fit.add_to(v, result["kept"], offset, table)
    except fit.FitError as error:
        raise ExportError(str(error))
    v.budget_spent += result["report"]["cost"]
    problems = v.problems()
    if problems:
        raise ExportError("the result would not be sound: %s" % "; ".join(problems[:3]))
    f.set_text((title or "FP Map")[:TITLE_MAX])
    data = f.to_bytes()
    folder = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(folder, exist_ok=True)
    try:
        with open(out_path, "xb") as handle:        # "x": fails rather than write over a file
            handle.write(data)
    except FileExistsError:
        raise ExportError("%s already exists; nothing was written" % out_path)
    back = mvar.MvarFile.read(out_path).variant
    return {"path": out_path, "slots": slots, "objects": len(back.placed_objects()), "budget_spent": back.budget_spent,
            "budget_max": back.budget_max, "title": f.variant.header.title, "problems": back.problems()}
