"""Reach Forge Printer, phase 4: the Forge pieces as a Blender asset library.

Every piece with a known menu name becomes an asset: an object with the piece's real model (or its
box when the model is not exported), its origin at Forge's placing point, and the custom properties
the add-on counts and exports ("fp_piece", "fp_part" = "added"). Dragged from Blender's Asset Browser
into a scene it is a Forge piece like one added from the sidebar palette. Assets are sorted into one
catalog per Forge category and carry a rendered thumbnail.

The library holds the game's models, so it is written under re_tools (DEFAULT_DIR), never into the
repository. Built and registered by build_library.py; this module needs Blender.
"""

import math
import os
import tempfile
import uuid

import bpy
from mathutils import Vector

from forge_printer import pieces

from . import ui

DEFAULT_DIR = os.path.join(os.path.dirname(pieces.DEFAULT_KEEP), "asset_library")
BLEND_NAME = "Reach Forge Pieces.blend"
LIBRARY_NAME = "Reach Forge Pieces"
CATALOG_FILE = "blender_assets.cats.txt"
THUMB_SIZE = 256
# a fixed namespace so a category keeps its catalog id each time the library is rebuilt
CATALOG_NAMESPACE = uuid.UUID("6f1d2b0c-5a3e-4c1e-9a7d-0f6b8c2e4d11")


def catalog_id(category):
    return str(uuid.uuid5(CATALOG_NAMESPACE, category))


def write_catalogs(directory, categories):
    """Blender's catalog file: one catalog a Forge category, under "Reach Forge"."""
    lines = ["# This is an Asset Catalog Definition file for Blender.", "", "VERSION 1", ""]
    lines.append("%s:Reach Forge:Reach Forge" % catalog_id("Reach Forge"))
    for category in categories:
        lines.append("%s:Reach Forge/%s:Reach Forge-%s" % (catalog_id(category), category, category.replace(",", "")))
    with open(os.path.join(directory, CATALOG_FILE), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def _thumbnail(scene, camera, obj, path):
    """Renders one piece on its own, seen from above at an angle, into a square PNG."""
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    low = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    high = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    centre, size = (low + high) / 2.0, max((high - low).length, 0.5)
    direction = Vector((1.0, -1.3, 0.9)).normalized()
    camera.location = centre + direction * size * 1.6
    camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = size * 1.05
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _set_preview(obj, path):
    """Puts a rendered PNG in as the asset's thumbnail."""
    image = bpy.data.images.load(path)
    try:
        w, h = image.size
        preview = obj.preview_ensure()
        preview.image_size = (w, h)
        preview.image_pixels_float.foreach_set(list(image.pixels))
    finally:
        bpy.data.images.remove(image)


def build(directory=DEFAULT_DIR, only=None, thumbnails=True):
    """Writes the library .blend and its catalog file into `directory`. `only`: piece names to include
    (all named pieces when None). Returns (path of the .blend, number of assets, how many use boxes)."""
    os.makedirs(directory, exist_ok=True)
    bpy.ops.wm.read_homefile(use_empty=True)                   # an empty file; the preferences are left alone
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = THUMB_SIZE
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    camera = bpy.data.objects.new("thumbnail camera", bpy.data.cameras.new("thumbnail camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera

    categories = list(ui.PALETTE)
    write_catalogs(directory, categories)
    boxes = made = 0
    with tempfile.TemporaryDirectory() as tmp:
        for category in categories:
            for piece in ui.PALETTE[category]:
                if only is not None and piece["name"] not in only:
                    continue
                mesh = ui.piece_mesh(piece, real_models=True)
                boxes += mesh.name.startswith("FP box ")
                obj = bpy.data.objects.new(piece["name"], mesh)
                obj["fp_piece"] = piece["name"]
                obj["fp_part"] = "added"
                scene.collection.objects.link(obj)
                if thumbnails:
                    for other in scene.collection.objects:
                        if other.type == "MESH":
                            other.hide_render = other is not obj
                    png = os.path.join(tmp, "%03d.png" % made)
                    _thumbnail(scene, camera, obj, png)
                    _set_preview(obj, png)
                obj.asset_mark()
                obj.asset_data.catalog_id = catalog_id(category)
                size = "x".join("%g" % round(v, 2) for v in piece["size"])
                obj.asset_data.description = "%s: %s (palette row %d, item %d), %s units" % (
                    category, piece["name"], piece["row"], piece["item"], size)
                for tag in (category, "Reach Forge"):
                    obj.asset_data.tags.new(tag, skip_if_exists=True)
                made += 1
    for obj in scene.collection.objects:
        obj.hide_render = False
    bpy.data.objects.remove(camera)
    path = os.path.join(directory, BLEND_NAME)
    bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False, compress=True)
    return path, made, boxes


STARTER_DIR = os.path.join(os.path.dirname(pieces.DEFAULT_KEEP), "starter")
STARTER_NAME = "Reach Forge Starter.blend"
TERRAIN_NAME = "forge_world.obj"
TERRAIN = "Forge World"                     # the collection of Forge World's own level, not exported
TEMPLATE_OBJECTS = "Template objects"       # the template's objects, shown where they are, not exported
GROUND_COLOUR = (0.42, 0.43, 0.40, 1.0)


def _shown_up(raw):
    """The up vector to draw a template object with: the file's own when it is worked out, else the cube
    face's axis (a hair off at most on the faces whose u and v are not worked out)."""
    from forge_printer import mvar
    if raw is None:
        return (0.0, 0.0, 1.0)
    try:
        return mvar.up_vector(raw)
    except ValueError:
        face = mvar.split_up(raw)[0]
        axis = [0.0, 0.0, 0.0]
        axis[face % 3] = 1.0 if face < 3 else -1.0
        return tuple(axis)


def add_template_objects(scene, template_path):
    """The template's own objects as locked, unexported objects where they stand (pieces with their model,
    others as a marker). Returns how many."""
    from forge_printer import mvar

    from . import convert, export
    f = export.load_template(template_path)
    v = f.variant
    by_slot = {(p["row"], p["item"]): p for p in ui._TABLE["pieces"]}
    coll = ui.collection(TEMPLATE_OBJECTS, scene.collection)
    count = 0
    for slot, o in v.placed_objects():
        placement = {"origin": v.world_position(o), "turn": math.degrees(mvar.decode_angle(o.angle)),
                     "up": _shown_up(o.up)}
        piece = by_slot.get((o.type_index, o.variant_index))
        if piece is not None:
            obj = bpy.data.objects.new("template %d %s" % (slot, piece["name"]), ui.piece_mesh(piece, True))
        else:
            obj = bpy.data.objects.new("template %d (row %d item %d)" % (slot, o.type_index, o.variant_index), None)
            obj.empty_display_type = "SINGLE_ARROW"
            obj.empty_display_size = 0.8
        from mathutils import Matrix
        obj.matrix_world = Matrix(convert.matrix_for(placement))
        obj["fp_template_object"] = slot
        obj.hide_select = True
        coll.objects.link(obj)
        count += 1
    return count


def build_starter(directory, terrain_obj, template_path, title="FP New Map"):
    """A .blend to start a Forge World map from: Forge World's level as solid ground (locked), the
    template's objects where they stand (locked), the template chosen and the offset 0 0 0 (the scene is
    Forge World itself), the view on the template's objects. Returns (path, template objects)."""
    os.makedirs(directory, exist_ok=True)
    bpy.ops.wm.read_homefile(use_empty=True)
    ours = not hasattr(bpy.types.Scene, "fp_template")
    if ours:
        ui.register()                                          # the scene settings the add-on reads
    scene = bpy.context.scene
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=terrain_obj, forward_axis="Y", up_axis="Z", global_scale=1.0,
                          use_split_objects=False, use_split_groups=False)
    ground = bpy.data.materials.new("FP Forge World")
    ground.diffuse_color = GROUND_COLOUR
    coll = ui.collection(TERRAIN, scene.collection)
    for o in set(bpy.data.objects) - before:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        o.name = "Forge World level"
        o.data.materials.clear()
        o.data.materials.append(ground)
        o.hide_select = True
    made = add_template_objects(scene, template_path)
    scene.fp_template = template_path
    scene.fp_offset = (0.0, 0.0, 0.0)
    scene.fp_title = title
    scene.fp_out_dir = ui.export.DEFAULT_OUT
    marks = [o for o in bpy.data.objects if o.get("fp_template_object") is not None]
    focus = sum((o.matrix_world.translation for o in marks), Vector()) / len(marks) if marks else Vector()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.clip_start, space.clip_end = 0.05, 2000.0
                region = space.region_3d
                region.view_location = focus
                region.view_distance = 40.0
    path = os.path.join(directory, STARTER_NAME)
    bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False, compress=True)
    if ours:
        ui.unregister()
    return path, made


def register_library(directory=DEFAULT_DIR, name=LIBRARY_NAME):
    """Adds (or points again) the library in Blender's preferences, appending pieces so they can be moved,
    sharing one mesh a piece. The caller saves the preferences. Returns the library entry."""
    libraries = bpy.context.preferences.filepaths.asset_libraries
    entry = next((lib for lib in libraries if lib.name == name), None)
    if entry is None:
        entry = next((lib for lib in libraries if os.path.normcase(os.path.abspath(lib.path)) ==
                      os.path.normcase(os.path.abspath(directory))), None)
    if entry is None:
        bpy.ops.preferences.asset_library_add(directory=directory)
        entry = libraries[-1]
    entry.name = name
    entry.path = directory
    if hasattr(entry, "import_method"):                        # pieces are appended so they can be moved;
        for method in ("APPEND_REUSE", "APPEND"):               # Blender 4 reuses one mesh a piece; 5 says APPEND
            try:
                entry.import_method = method
                break
            except TypeError:
                continue
    return entry
