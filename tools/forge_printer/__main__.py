"""Command line for the Reach map variant reader and writer.

    python\\python.exe tools\\forge_printer info  FILE [--objects]
    python\\python.exe tools\\forge_printer check FILE_OR_FOLDER ...
    python\\python.exe tools\\forge_printer move  FILE OUT --slot N [--dx 0] [--dy 0] [--dz 0] [--title TEXT] [--keep-hash]
    python\\python.exe tools\\forge_printer reference MAP [--out FOLDER]
    python\\python.exe tools\\forge_printer surfaces FOLDER [--side 4] [--below 3] [--above 8]
    python\\python.exe tools\\forge_printer pieces [--measure] [--keep FOLDER]

`check` reads each file, writes it back in memory and compares the bytes.
`move` never touches FILE: it writes a changed copy to OUT.
"""

import argparse
import math
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from forge_printer import h3_reference, mvar
else:
    from . import h3_reference, mvar


def _mvar_files(paths):
    for path in paths:
        if os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                if name.lower().endswith(".mvar"):
                    yield os.path.join(path, name)
        else:
            yield path


def cmd_info(args):
    f = mvar.MvarFile.read(args.file)
    v = f.variant
    h = v.header
    placed = v.placed_objects()
    print("title        %s" % h.title)
    print("description  %s" % h.description)
    print("map id       %d   variant version %d   container %s" % (v.map_id, v.version, "_cmp (packed)" if f.compressed else "mvar"))
    print("bounds       x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f   axis bits %s" % (v.bounds + (v.axis_bits(),)))
    print("budget       %d of %d" % (v.budget_spent, v.budget_max))
    print("objects      %d of %d slots, %d quota rows" % (len(placed), mvar.OBJECT_SLOTS, len(v.quotas)))
    print("labels       %s" % ", ".join(str(n) for n in v.labels.names()))
    print("360 hash     %s" % ("valid" if f.hash_is_valid() else "not the Xbox 360 hash (normal for files MCC saved)"))
    problems = v.problems()
    print("problems     %s" % ("; ".join(problems) if problems else "none"))
    if args.objects:
        names = v.labels.names()
        table = None
        if __package__ in (None, ""):
            from forge_printer import pieces
        else:
            from . import pieces
        if pieces.is_forge_world(v):
            try:
                table = pieces.load()
            except pieces.PieceError:
                table = None
        print("slot type.var      x         y         z    angle  up      mp  team label  piece")
        for slot, o in placed:
            x, y, z = v.world_position(o)
            up = "world" if o.up is None else "f%d" % mvar.split_up(o.up)[0]
            label = "" if o.label is None else names[o.label]
            piece = pieces.at(o.type_index, o.variant_index, table) if table else None
            print("%4d %3d.%-2d %9.3f %9.3f %9.3f %7.1f  %-6s %3d %4d  %-6s %s" % (
                slot, o.type_index, o.variant_index, x, y, z, math.degrees(mvar.decode_angle(o.angle)), up,
                o.mp_type, o.team - 1, label, piece["name"] if piece else ""))
    return 0


def cmd_check(args):
    bad = 0
    count = 0
    for path in _mvar_files(args.paths):
        count += 1
        with open(path, "rb") as handle:
            data = handle.read()
        try:
            f = mvar.MvarFile.from_bytes(data)
            same = f.to_bytes() == data
            problems = f.variant.problems()
        except mvar.FormatError as error:
            print("FAIL  %s: %s" % (os.path.basename(path), error))
            bad += 1
            continue
        if same and not problems:
            print("ok    %s  (%d objects, v%d)" % (os.path.basename(path), len(f.variant.placed_objects()), f.variant.version))
        else:
            bad += 1
            print("FAIL  %s: %s" % (os.path.basename(path), "bytes differ after a round trip" if not same else "; ".join(problems)))
    print("%d file(s), %d failed" % (count, bad))
    return 1 if bad else 0


def cmd_move(args):
    if os.path.exists(args.out):
        print("refusing to overwrite %s" % args.out)
        return 1
    f = mvar.MvarFile.read(args.file)
    v = f.variant
    obj = v.objects[args.slot] if 0 <= args.slot < len(v.objects) else None
    if obj is None:
        print("slot %d is empty; use `info --objects` to list the used slots" % args.slot)
        return 1
    x, y, z = v.world_position(obj)
    v.set_world_position(obj, x + args.dx, y + args.dy, z + args.dz)
    if args.title:
        f.set_text(args.title)
    f.write(args.out, rehash=False if args.keep_hash else None)
    print("slot %d: (%.3f, %.3f, %.3f) -> (%.3f, %.3f, %.3f)" % ((args.slot, x, y, z) + v.world_position(obj)))
    print("wrote %s" % args.out)
    return 0


def cmd_reference(args):
    return h3_reference.main(args.map, args.out)


def cmd_surfaces(args):
    if __package__ in (None, ""):
        from forge_printer import surfaces     # needs numpy: only loaded for this command
    else:
        from . import surfaces
    return surfaces.main(args.folder, args.side, args.below, args.above)


def cmd_pieces(args):
    if __package__ in (None, ""):
        from forge_printer import pieces
    else:
        from . import pieces
    return pieces.main(args.measure, args.keep)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="forge_printer", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("info", help="describe one variant")
    p.add_argument("file")
    p.add_argument("--objects", action="store_true", help="list every placed object")
    p.set_defaults(run=cmd_info)
    p = sub.add_parser("check", help="round-trip files and compare bytes")
    p.add_argument("paths", nargs="+")
    p.set_defaults(run=cmd_check)
    p = sub.add_parser("move", help="write a copy with one object moved")
    p.add_argument("file")
    p.add_argument("out")
    p.add_argument("--slot", type=int, required=True)
    p.add_argument("--dx", type=float, default=0.0)
    p.add_argument("--dy", type=float, default=0.0)
    p.add_argument("--dz", type=float, default=0.0)
    p.add_argument("--title", help="new name for the copy, so it is easy to tell apart in game")
    p.add_argument("--keep-hash", action="store_true", help="leave the source file's hash bytes as they are")
    p.set_defaults(run=cmd_move)
    p = sub.add_parser("reference", help="a Halo 3 map as a Blender tracing reference (mesh + placements)")
    p.add_argument("map", help="a maps/ folder name, e.g. h3_guardian")
    p.add_argument("--out", help="output folder (default: re_tools\\forge_printer\\reference\\<map>)")
    p.set_defaults(run=cmd_reference)
    p = sub.add_parser("surfaces", help="cut a reference to its play space and sort it into floors, slopes, walls, ceilings")
    p.add_argument("folder", help="a folder `reference` wrote")
    p.add_argument("--side", type=float, default=4.0, help="world units kept beyond the walked ground, sideways")
    p.add_argument("--below", type=float, default=3.0, help="... below it")
    p.add_argument("--above", type=float, default=8.0, help="... above it")
    p.set_defaults(run=cmd_surfaces)
    p = sub.add_parser("pieces", help="the Forge World building pieces and their sizes")
    p.add_argument("--measure", action="store_true", help="export each piece's model from MCC and rewrite the table")
    p.add_argument("--keep", help="where the exported models go (default: re_tools\\forge_printer\\pieces)")
    p.set_defaults(run=cmd_pieces)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
