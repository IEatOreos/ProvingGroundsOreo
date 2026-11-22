"""Reach Forge Printer, phase 4: the add-on's Blender side (operators, panels, scene settings).

Everything worth testing without Blender is in convert.py (object <-> placement) and export.py
(counting, what fits, writing). This file only moves numbers between Blender and those two.

A Forge piece is any object carrying the custom property "fp_piece" (its piece name). Its
origin is Forge's placing point and its own axes are the piece's; scale must stay 1. Other
custom properties: "fp_index" (its place in the export, fit.json's order first), "fp_part",
"fp_fill", "fp_size" (what `fit.within_limits` ranks by).
"""

import json
import os

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy.types import Operator, Panel
from bpy_extras.io_utils import ImportHelper
from mathutils import Matrix

from forge_printer import mvar, pieces

from . import convert, export

ROOT = "Forge pieces"
BACKDROP = "Reference backdrop"
REPORT_TEXT = "Forge export report"
CATEGORY_COLOURS = {"Building Blocks": (0.55, 0.58, 0.63, 1.0), "Bridges and Platforms": (0.42, 0.52, 0.72, 1.0),
                    "Buildings": (0.62, 0.52, 0.42, 1.0), "Decorative": (0.75, 0.65, 0.3, 1.0),
                    "Doors, Windows and Walls": (0.5, 0.64, 0.52, 1.0), "Inclines": (0.8, 0.52, 0.3, 1.0),
                    "Nature": (0.42, 0.58, 0.36, 1.0)}
PLAY_COLOURS = {"floor": (0.25, 0.65, 0.3, 1.0), "slope": (0.9, 0.7, 0.2, 1.0),
                "wall": (0.55, 0.6, 0.7, 1.0), "ceiling": (0.7, 0.3, 0.3, 1.0)}
# one show/hide switch per kind of reference surface: (kind, scene property, label, shown at first)
BACKDROP_KINDS = (("floor", "fp_show_floor", "Floors", True), ("slope", "fp_show_slope", "Slopes", True),
                  ("wall", "fp_show_wall", "Walls", True), ("ceiling", "fp_show_ceiling", "Ceilings", False))

_TABLE = pieces.load()
KNOWN = pieces.by_name(_TABLE)
PALETTE = {}                                  # category -> pieces with a known menu name, in menu order
for _p in _TABLE["pieces"]:
    if _p["name"] in KNOWN:
        PALETTE.setdefault(_p["category"], []).append(_p)
UNNAMED = len(_TABLE["pieces"]) - len(KNOWN)  # known only by their model's name: not offered yet
_TEMPLATES = {}                               # path -> (mtime, MvarFile), for the live counter
_DIALOG = []                                  # the lines the export dialog shows


# ---- pieces in the scene ----------------------------------------------------

def forge_objects(scene):
    """The scene's Forge pieces in export order: fit.json's order, then pieces added by hand."""
    objs = [o for o in scene.objects if o.get("fp_piece") is not None]
    objs.sort(key=lambda o: (int(o.get("fp_index", 1 << 30)), o.name))
    return objs


def _plain(value):
    return value.to_list() if hasattr(value, "to_list") else value


def entry_for(obj):
    """convert.placement_from for one object, as an export entry."""
    matrix = [list(row) for row in obj.matrix_world]
    local_box = None
    if obj.type == "MESH":
        corners = [tuple(c) for c in obj.bound_box]
        local_box = (tuple(min(c[i] for c in corners) for i in range(3)),
                     tuple(max(c[i] for c in corners) for i in range(3)))
    props = {key: _plain(obj.get("fp_" + key)) for key in convert.CARRIED}
    placement, reason, warning = convert.placement_from(matrix, obj["fp_piece"], KNOWN, props, local_box)
    return {"label": obj.name, "placement": placement, "reason": reason, "warning": warning}


def scene_entries(scene):
    return [(o, entry_for(o)) for o in forge_objects(scene)]


def template_of(scene):
    """(MvarFile or None, error text or None) for the scene's template, read once per change on disk."""
    path = bpy.path.abspath(scene.fp_template) if scene.fp_template else ""
    if not path:
        return None, "no template chosen"
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None, "the template file is not there"
    cached = _TEMPLATES.get(path)
    if cached and cached[0] == mtime:
        return cached[1], None
    try:
        f = export.load_template(path)
    except export.ExportError as error:
        return None, str(error)
    _TEMPLATES[path] = (mtime, f)
    return f, None


# ---- making objects ---------------------------------------------------------

def material(category):
    name = "FP " + category
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = CATEGORY_COLOURS.get(category, (0.6, 0.6, 0.6, 1.0))
    return mat


def _import_model(path, name):
    """The mesh of a real piece model (an OBJ in the piece's own axes), or None."""
    before = set(bpy.data.objects)
    try:
        bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z", global_scale=1.0,
                              use_split_objects=False, use_split_groups=False)
    except RuntimeError:
        return None
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    mesh = meshes[0].data if len(meshes) == 1 else None
    for o in new:
        bpy.data.objects.remove(o)
    if mesh is not None:
        mesh.name = name
        mesh.materials.clear()
    return mesh


def piece_mesh(piece, real_models=True):
    """One mesh per piece, shared by every object of that piece: the real model when it is in the
    local models folder (never committed), else the piece's box from the committed table."""
    if real_models:
        name = "FP model " + piece["name"]
        mesh = bpy.data.meshes.get(name)
        if mesh is None:
            path = os.path.join(pieces.DEFAULT_KEEP, piece["model"] + ".obj")
            if os.path.isfile(path):
                mesh = _import_model(path, name)
                if mesh is not None:
                    mesh.materials.append(material(piece["category"]))
        if mesh is not None:
            return mesh
    name = "FP box " + piece["name"]
    mesh = bpy.data.meshes.get(name)
    if mesh is None:
        verts, quads = convert.box_mesh(piece)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], quads)
        mesh.update()
        mesh.materials.append(material(piece["category"]))
    return mesh


def collection(name, parent):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in parent.children:
        parent.children.link(c)
    return c


def part_collection(scene, part):
    return collection("Forge " + part, collection(ROOT, scene.collection))


def make_piece(scene, piece, matrix, part, index, extra=None, real_models=True):
    obj = bpy.data.objects.new(piece["name"], piece_mesh(piece, real_models))
    obj["fp_piece"] = piece["name"]
    obj["fp_part"] = part
    obj["fp_index"] = index
    for key, value in (extra or {}).items():
        if value is not None:
            obj["fp_" + key] = int(value) if isinstance(value, bool) else value
    obj.matrix_world = Matrix(matrix)
    part_collection(scene, part).objects.link(obj)
    return obj


def load_backdrop(scene, folder):
    """The reference level behind the pieces (its play space, coloured, when `surfaces` has run on it),
    not selectable so a click never moves it. Returns how many objects came in."""
    ref_path = os.path.join(folder, "reference.json")
    if not os.path.isfile(ref_path):
        return 0
    coll = collection(BACKDROP, scene.collection)
    if coll.objects:
        return 0                                          # already loaded
    surfaces_path = os.path.join(folder, "surfaces.json")
    if os.path.isfile(surfaces_path):
        with open(surfaces_path, encoding="utf-8") as f:
            mesh_path, split = os.path.join(folder, json.load(f)["mesh"]), True
    else:
        with open(ref_path, encoding="utf-8") as f:
            mesh_path, split = os.path.join(folder, json.load(f)["mesh"]), False
    if not os.path.isfile(mesh_path):
        return 0
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=mesh_path, forward_axis="Y", up_axis="Z", global_scale=1.0,
                          use_split_groups=split)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        o.hide_select = True
        kind = next((k for k in PLAY_COLOURS if k in o.name.lower()), None) if split else None
        o["fp_backdrop"] = kind or "level"
        if kind:
            o.name = "backdrop " + kind
            mat = bpy.data.materials.get("FP play " + kind) or bpy.data.materials.new("FP play " + kind)
            mat.diffuse_color = PLAY_COLOURS[kind]
            o.data.materials.clear()
            o.data.materials.append(mat)
        o.select_set(False)
    if bpy.context.view_layer.objects.active in new:
        bpy.context.view_layer.objects.active = None    # the importer leaves it active: never the thing a key moves
    show_backdrop(scene)
    return len(new)


def show_backdrop(scene, context=None):
    """Draws the backdrop as the scene's "fp_backdrop" says. The pieces' tops lie in the reference's
    floors, so solid floors hide them: wire is the default, solid floors show where floor is bare.
    Each kind of surface (floors, slopes, walls, ceilings) also has its own show/hide switch."""
    coll = bpy.data.collections.get(BACKDROP)
    if coll is None:
        return
    mode = scene.fp_backdrop
    shown = {kind: getattr(scene, prop) for kind, prop, _, _ in BACKDROP_KINDS}
    for o in coll.objects:
        kind = o.get("fp_backdrop", "level")
        o.display_type = "SOLID" if mode == "SOLID" and kind in ("floor", "slope") else "WIRE"
        try:
            o.hide_set(mode == "HIDDEN" or not shown.get(kind, True))
        except RuntimeError:
            pass                                        # not in this view layer


def select_only(context, objs):
    for o in context.selected_objects:
        o.select_set(False)
    for o in objs:
        if o.visible_get():
            o.select_set(True)
    if objs:
        context.view_layer.objects.active = objs[0]


def _report_text(text_lines):
    text = bpy.data.texts.get(REPORT_TEXT) or bpy.data.texts.new(REPORT_TEXT)
    text.clear()
    text.write("\n".join(text_lines) + "\n")


# ---- operators --------------------------------------------------------------

class FORGE_PRINTER_OT_open_fit(Operator, ImportHelper):
    """Open a fit.json: one object per Forge piece, the reference level behind them"""
    bl_idname = "forge_printer.open_fit"
    bl_label = "Open fit.json"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    offset: FloatVectorProperty(name="Offset into Forge World", size=3, default=(0.0, 0.0, 0.0),
                                description="Added to every piece's position on export (Guardian: -39 -135 8)")
    backdrop: BoolProperty(name="Reference level as a backdrop", default=True)
    real_models: BoolProperty(name="Real piece models where found", default=True,
                              description="Use the piece models in re_tools when they are there; boxes otherwise")
    replace: BoolProperty(name="Replace the pieces already here", default=False)

    def invoke(self, context, event):
        self.offset = context.scene.fp_offset
        return ImportHelper.invoke(self, context, event)

    def execute(self, context):
        scene = context.scene
        existing = forge_objects(scene)
        if existing and not self.replace:
            self.report({"ERROR"}, "This scene already holds %d Forge pieces: tick Replace, or start a new file"
                        % len(existing))
            return {"CANCELLED"}
        try:
            with open(self.filepath, encoding="utf-8") as f:
                data = json.load(f)
            placements = data["placements"]
        except (OSError, ValueError, KeyError) as error:
            self.report({"ERROR"}, "Not a fit.json this add-on reads: %s" % error)
            return {"CANCELLED"}
        for o in existing:
            bpy.data.objects.remove(o)
        made, unknown = 0, 0
        for index, p in enumerate(placements):
            piece = KNOWN.get(p.get("piece"))
            if piece is None:
                unknown += 1
                continue
            make_piece(scene, piece, convert.matrix_for(p), p.get("part", "added"), index,
                       {key: p.get(key) for key in convert.CARRIED if key != "part"}, self.real_models)
            made += 1
        scene.fp_offset = self.offset
        scene.fp_fit_path = self.filepath
        scene.fp_next_index = len(placements)
        source = data.get("source", {}).get("map", "Map")
        scene.fp_title = ("FP %s edit" % source.replace("h3_", "").title())[:export.TITLE_MAX]
        backdrop = load_backdrop(scene, os.path.dirname(self.filepath)) if self.backdrop else 0
        self.report({"INFO"}, "Opened %d Forge pieces%s%s" % (
            made, ", %d with an unknown piece name left out" % unknown if unknown else "",
            ", backdrop %d objects" % backdrop if backdrop else ""))
        print("forge printer: opened %d pieces from %s (%d unknown), backdrop %d" % (made, self.filepath, unknown,
                                                                                     backdrop))
        return {"FINISHED"}


class FORGE_PRINTER_OT_add_piece(Operator):
    """Add this Forge piece at the 3D cursor"""
    bl_idname = "forge_printer.add_piece"
    bl_label = "Add Forge piece"
    bl_options = {"REGISTER", "UNDO"}

    piece: StringProperty(name="Piece")

    @classmethod
    def description(cls, context, properties):
        p = KNOWN.get(properties.piece)
        if p is None:
            return cls.__doc__
        price = pieces.price(p["name"])
        return "Add %s at the 3D cursor: %.2f x %.2f x %.2f, %s item %d, price %s" % (
            p["name"], p["size"][0], p["size"][1], p["size"][2], p["category"], p["item"],
            price if price is not None else "not known yet")

    def execute(self, context):
        piece = KNOWN.get(self.piece)
        if piece is None:
            self.report({"ERROR"}, "No Forge piece called %r" % self.piece)
            return {"CANCELLED"}
        scene = context.scene
        index = max([scene.fp_next_index] + [int(o.get("fp_index", 0)) + 1 for o in forge_objects(scene)])
        scene.fp_next_index = index + 1
        matrix = Matrix.Translation(scene.cursor.location)
        obj = make_piece(scene, piece, matrix, "added", index, real_models=scene.fp_real_models)
        select_only(context, [obj])
        return {"FINISHED"}


class FORGE_PRINTER_OT_add_library(Operator):
    """Add the Reach Forge pieces asset library (built by build_library.py) to Blender's Asset Browser and
    save that in the preferences"""
    bl_idname = "forge_printer.add_library"
    bl_label = "Add piece library to the Asset Browser"

    def execute(self, context):
        from . import library
        if not os.path.isfile(os.path.join(library.DEFAULT_DIR, library.BLEND_NAME)):
            self.report({"ERROR"}, "the library is not built yet: run build_library.py first")
            return {"CANCELLED"}
        entry = library.register_library()
        bpy.ops.wm.save_userpref()
        self.report({"INFO"}, "Asset Browser library \"%s\" added: open an Asset Browser and drag pieces in" % entry.name)
        return {"FINISHED"}


def _library_state():
    """("missing" | "unregistered" | "ready", library name)."""
    from . import library
    if not os.path.isfile(os.path.join(library.DEFAULT_DIR, library.BLEND_NAME)):
        return "missing", library.LIBRARY_NAME
    names = {lib.name for lib in bpy.context.preferences.filepaths.asset_libraries}
    return ("ready" if library.LIBRARY_NAME in names else "unregistered"), library.LIBRARY_NAME


class FORGE_PRINTER_OT_select_problems(Operator):
    """Select the pieces that cannot be written (scaled, leaning too far, reshaped)"""
    bl_idname = "forge_printer.select_problems"
    bl_label = "Select them"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bad = [o for o, e in scene_entries(context.scene) if e["placement"] is None]
        select_only(context, bad)
        self.report({"INFO"}, "%d piece(s) cannot be written" % len(bad))
        return {"FINISHED"}


class FORGE_PRINTER_OT_export(Operator):
    """Write the pieces into a copy of the template, as a new .mvar (never over a file)"""
    bl_idname = "forge_printer.export"
    bl_label = "Export .mvar"
    bl_options = {"REGISTER"}

    accept: BoolProperty(name="Export the rest", default=False, options={"HIDDEN", "SKIP_SAVE"},
                         description="Write what can be written although some pieces cannot")

    def _plan(self, context):
        scene = context.scene
        template = bpy.path.abspath(scene.fp_template) if scene.fp_template else ""
        f = export.load_template(template)
        pairs = scene_entries(scene)
        if not pairs:
            raise export.ExportError("there are no Forge pieces in this scene")
        result = export.plan([e for _, e in pairs], f.variant, tuple(scene.fp_offset), _TABLE)
        return template, pairs, result

    def invoke(self, context, event):
        try:
            _, pairs, result = self._plan(context)
        except export.ExportError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if not export.lines(result):
            self.accept = True
            return self.execute(context)
        _DIALOG[:] = export.lines(result, limit=10)
        names = set(label for label, _ in result["refused"] + result["left_out"])
        select_only(context, [o for o, e in pairs if e["label"] in names])
        self.accept = True
        return context.window_manager.invoke_props_dialog(self, width=720, title="Before exporting",
                                                          confirm_text="Export the rest")

    def draw(self, context):
        col = self.layout.column(align=True)
        for line in _DIALOG:
            col.label(text=line)
        col.separator()
        col.label(text="Those pieces are selected now. Nothing is written unless you press Export the rest;")
        col.label(text="the full list goes to the text \"%s\"." % REPORT_TEXT)

    def execute(self, context):
        scene = context.scene
        try:
            template, pairs, result = self._plan(context)
            problems = export.lines(result)
            if problems and not self.accept:
                _report_text(problems)
                raise export.ExportError("%d piece(s) cannot be written or do not fit: press Export in the Forge "
                                         "panel to see them (also in the text \"%s\")" % (
                                             len(result["refused"]) + len(result["left_out"]), REPORT_TEXT))
            folder = bpy.path.abspath(scene.fp_out_dir) if scene.fp_out_dir else export.DEFAULT_OUT
            out = export.free_path(folder, scene.fp_title or "FP Map")
            info = export.write(template, result, tuple(scene.fp_offset), out, scene.fp_title, _TABLE)
        except export.ExportError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        report = result["report"]
        summary = "Wrote %s: %d pieces added, %d of %d objects, budget %d of %d%s" % (
            info["path"], len(info["slots"]), info["objects"], mvar.OBJECT_SLOTS, info["budget_spent"],
            info["budget_max"], ", no price known for " + ", ".join(report["unpriced"]) if report["unpriced"] else "")
        _report_text([summary, 'Title "%s"' % info["title"]] + problems)
        print("forge printer: " + summary)
        for line in problems:
            print("forge printer: " + line)
        self.report({"WARNING"} if problems else {"INFO"}, summary + (
            "; %d left out, see the text \"%s\"" % (len(result["refused"]) + len(result["left_out"]), REPORT_TEXT)
            if problems else ""))
        return {"FINISHED"}


# ---- panels -----------------------------------------------------------------

def _summary(scene):
    pairs = scene_entries(scene)
    f, template_error = template_of(scene)
    good = [e["placement"] for _, e in pairs if e["placement"] is not None]
    counts = export.count(good, f.variant if f else None, _TABLE)
    return pairs, good, counts, template_error


class FORGE_PRINTER_PT_main(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Forge"
    bl_label = "Reach Forge Printer"

    def draw(self, context):
        layout, scene = self.layout, context.scene
        layout.operator("forge_printer.open_fit", icon="FILE_FOLDER")
        layout.prop(scene, "fp_template")
        layout.prop(scene, "fp_offset")
        backdrop = bpy.data.collections.get(BACKDROP)
        if backdrop:
            layout.row().prop(scene, "fp_backdrop", expand=True)
            kinds = {o.get("fp_backdrop") for o in backdrop.objects}
            row = layout.row(align=True)
            row.active = scene.fp_backdrop != "HIDDEN"
            for kind, prop, _, _ in BACKDROP_KINDS:
                if kind in kinds:
                    row.prop(scene, prop, toggle=True)
        try:
            pairs, good, counts, template_error = _summary(scene)
        except Exception as error:                     # a panel must never stop drawing
            layout.label(text="Counting failed: %s" % error, icon="ERROR")
            return
        box = layout.box()
        if not pairs:
            box.label(text="No Forge pieces yet: open a fit.json, or add")
            box.label(text="pieces from the Forge palette below.")
        row = box.row()
        row.alert = counts["slots_over"] > 0
        row.label(text="Objects  %d of %d" % (counts["slots_used"], counts["slots_max"]))
        for r, n in sorted(counts["rows"].items()):
            if r not in export.ROW_NAMES and n <= mvar.ROW_MAX:
                continue                               # the template's own spawns and the like: not a piece row
            row = box.row()
            row.alert = n > mvar.ROW_MAX
            row.label(text="%s  %d of %d%s" % (export.ROW_NAMES.get(r, "row %d" % r), n, mvar.ROW_MAX,
                                               "  (%d over)" % (n - mvar.ROW_MAX) if n > mvar.ROW_MAX else ""))
        row = box.row()
        row.alert = counts["budget_over"] > 0
        if counts["budget_max"] is None:
            row.label(text="Budget  %d (choose a template for its limit)" % counts["budget_spent"])
        else:
            row.label(text="Budget  %d of %d" % (counts["budget_spent"], counts["budget_max"]))
        if counts["unpriced"]:
            box.label(text="+ %d with no price known" % counts["unpriced"], icon="INFO")
        if template_error:
            box.label(text="Template: %s" % template_error, icon="INFO")
        bad = len(pairs) - len(good)
        if bad:
            box.label(text="%d piece(s) cannot be written" % bad, icon="ERROR")
            row = box.row()
            row.alert = True
            row.operator("forge_printer.select_problems", text="Select them (Export says why)")
        col = layout.column()
        col.prop(scene, "fp_out_dir")
        col.prop(scene, "fp_title")
        col.operator("forge_printer.export", icon="EXPORT")


class FORGE_PRINTER_PT_palette(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Forge"
    bl_label = "Forge palette"

    def draw(self, context):
        layout, scene = self.layout, context.scene
        state, name = _library_state()
        if state == "unregistered":
            layout.operator("forge_printer.add_library", icon="ASSET_MANAGER")
        elif state == "ready":
            box = layout.box()
            box.label(text="Drag pieces in from an Asset Browser:", icon="ASSET_MANAGER")
            box.label(text="library \"%s\"" % name)
        layout.prop(scene, "fp_category", text="")
        layout.prop(scene, "fp_real_models")
        col = layout.column(align=True)
        for p in PALETTE.get(scene.fp_category, []):
            row = col.row(align=True)
            row.operator("forge_printer.add_piece", text=p["name"]).piece = p["name"]
            row.label(text="%g x %g x %g" % tuple(round(s, 2) for s in p["size"]))
        if UNNAMED:
            layout.label(text="%d pieces with no known menu name are not offered yet" % UNNAMED)


CLASSES = (FORGE_PRINTER_OT_open_fit, FORGE_PRINTER_OT_add_piece, FORGE_PRINTER_OT_add_library,
           FORGE_PRINTER_OT_select_problems, FORGE_PRINTER_OT_export, FORGE_PRINTER_PT_main, FORGE_PRINTER_PT_palette)


@bpy.app.handlers.persistent
def _redraw_counts(scene, depsgraph=None):
    """Redraw the Forge sidebar whenever the scene changes, so the counts are live."""
    wm = bpy.context.window_manager
    for window in (wm.windows if wm else ()):
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                for region in area.regions:
                    if region.type == "UI":
                        region.tag_redraw()


_CATEGORY_ITEMS = [(c, c, "Forge's %s pieces" % c) for c in PALETTE]

SCENE_PROPS = {
    "fp_template": StringProperty(name="Template", subtype="FILE_PATH",
                                  description="A Forge World variant your MCC saved; it is copied, never changed"),
    "fp_offset": FloatVectorProperty(name="Offset", size=3, default=(0.0, 0.0, 0.0),
                                     description="Added to every piece's position on export: where this map sits "
                                                 "in Forge World (Guardian: -39 -135 8)"),
    "fp_out_dir": StringProperty(name="Folder", subtype="DIR_PATH", default=export.DEFAULT_OUT,
                                 description="Where exported variants go; a new file each time"),
    "fp_title": StringProperty(name="Title", default="FP Map", maxlen=export.TITLE_MAX,
                               description="The name the variant shows in the game"),
    "fp_real_models": BoolProperty(name="Real models where found", default=True,
                                   description="New pieces use the piece models in re_tools when they are there"),
    "fp_category": EnumProperty(name="Category", items=_CATEGORY_ITEMS),
    "fp_backdrop": EnumProperty(name="Backdrop", default="WIRE", update=lambda self, context: show_backdrop(self),
                                items=[("WIRE", "Wire", "The reference level as lines: the pieces show as the game will"),
                                       ("SOLID", "Solid floors", "The reference's floors and slopes solid: bare floor "
                                                                 "shows, but they hide the pieces level with them"),
                                       ("HIDDEN", "Hidden", "No reference level")]),
    **{prop: BoolProperty(name=label, default=default, update=lambda self, context: show_backdrop(self),
                          description="Show the reference level's %s" % label.lower())
       for _, prop, label, default in BACKDROP_KINDS},
    "fp_fit_path": StringProperty(name="Opened from", subtype="FILE_PATH"),
    "fp_next_index": IntProperty(name="Next piece index", default=0, min=0),
}


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    for name, prop in SCENE_PROPS.items():
        setattr(bpy.types.Scene, name, prop)
    if _redraw_counts not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_redraw_counts)


def unregister():
    if _redraw_counts in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_redraw_counts)
    for name in SCENE_PROPS:
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
