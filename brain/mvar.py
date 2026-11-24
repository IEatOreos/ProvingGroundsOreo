"""Halo: Reach map variant files (.mvar) read directly: every placed Forge object with its position, rotation, Forge
label, team, spawn sequence, game-type flags, shape (respawn zones, hills, kill boundaries), so a Forge map's objectives
and boundaries come from the file the match runs on, not from memory (Reach keeps no object's label where it was found:
docs/HANDOFF.md, Nov 3 Invasion entry).

Format (verified against real files: the GitHub issue #2 player's Tempest Invasion, MCC's built-in and hopper map
variants): a BLF file of big-endian chunks _blf, chdr (content header, map id at chunk +0x3C), mvar (version 31, 0x7028
bytes), _eof. The mvar body after its 0x18-byte head (sha-1, length) is a bitstream, most significant bit first. Field
order and widths from DavidJCobb's reach-mvar-viewer-js (map_variant_mvar.js, forge-rotation.js; GPL-3.0, read only,
reference/reach-mvar-viewer-js, commit ccda45c): content header, encoding version (8), map id, Forge bounds (6 floats),
budget, Forge label strings (zlib), 651 object slots, then min / max / placed per palette folder. Two checks prove a
parse: every folder's "placed" count equals the objects read in it, and the bits end inside the chunk with zeros after.
One change from that code: its axis B decode multiplies the scale by itself (a constant); here it is the axis' own bits,
like axis A (pieces on their side then come out unit-length before the normalise).

Objects are named by (palette folder, item): maps/_shapes/reach_palettes.json (tools/forge_palette.py --all, from each
map's scenario "map variant palettes"). Multiplayer object type (5 bits): 1 weapon, 12..14 teleporters, 15 spawn point,
16 respawn zone, 17/18 objectives, 19 named location, 25 safe volume, 26 kill volume, ...

python -I brain/mvar.py <file.mvar | file.bin> [--json]   lists the objects (Reach, Halo 3) or the options
"""
import glob
import json
import math
import os
import struct
import sys
import zlib

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
PALETTES = os.path.join(ROOT, "_shapes", "reach_palettes.json")
OBJECTS = 0x28B             # object slots in every Reach map variant
MIN16 = 0.00833333333       # a 16-bit position's step (reach-mvar-viewer-js _sub4DC8E0)
MP_TYPES = ("ordinary", "weapon", "grenade", "projectile", "powerup", "equipment", "ammo_pack", "light_vehicle",
            "heavy_vehicle", "flying_vehicle", "turret", "device", "teleporter_2way", "teleporter_sender",
            "teleporter_receiver", "spawn_point", "respawn_zone", "secondary_objective", "primary_objective",
            "named_location", "danger_zone", "fireteam1_respawn_zone", "fireteam2_respawn_zone",
            "fireteam3_respawn_zone", "fireteam4_respawn_zone", "safe_volume", "kill_volume", "cinematic_camera")
SHAPES = (None, "sphere", "cylinder", "box")
PHYSICS = ("normal", "fixed", "?", "phased")
SYMMETRY = ("never", "symmetric", "asymmetric", "both")


class Bits:
    """A big-endian bitstream (most significant bit first) over bytes b, from byte start."""

    def __init__(s, b, start=0):
        s.b, s.p = b, start * 8

    def u(s, n):
        if n <= 0:
            return 0
        i, j = s.p >> 3, (s.p + n + 7) >> 3
        if j > len(s.b):
            raise ValueError("map variant ends early")
        v = int.from_bytes(s.b[i:j], "big") >> ((j - i) * 8 - (s.p & 7) - n)
        s.p += n
        return v & ((1 << n) - 1)

    def raw(s, n):
        return bytes(s.u(8) for _ in range(n))

    def f32(s):
        return struct.unpack(">f", s.u(32).to_bytes(4, "big"))[0]

    def cstr(s, n):
        out = bytearray()
        for _ in range(n):
            c = s.u(8)
            if not c:
                break
            out.append(c)
        return out.decode("latin-1")

    def wstr(s, n):
        out = []
        for _ in range(n):
            c = s.u(16)
            if not c:
                break
            out.append(chr(c))
        return "".join(out)


def chunks(data):
    """{signature: (offset, size, version)} of a BLF file's chunks (big-endian sizes; MCC writes them so)."""
    out, o = {}, 0
    while o + 12 <= len(data):
        sig = data[o:o + 4].decode("latin-1")
        size, ver = struct.unpack(">IH", data[o + 4:o + 10])
        out[sig] = (o, size, ver)
        if sig == "_eof" or size < 12:
            break
        o += size
    return out


def _pos_bits(bounds, bitcount=21, cap=0x800000):
    """Bits per position axis for a variant's Forge bounds (reach-mvar-viewer-js _sub4DC8E0; (upstream 0.3.0) Halo 4
    and H2A cap the step count at 0x400000)."""
    step = MIN16 / (1 << (bitcount - 16)) if bitcount > 16 else (1 << (16 - bitcount)) * MIN16
    if step < 0.0001:
        return [26, 26, 26]
    out = []
    for lo, hi in bounds:
        n = min(cap, int(math.ceil((hi - lo) / (step * 2))))
        hb = n.bit_length() - 1
        out.append(min(26, hb + (1 if n & ((1 << hb) - 1) else 0)) if n else 0)
    return out


def _norm(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _up(bits, n=20):
    """The 20-bit up vector (forge-rotation.js decode_axis): six faces of a cube, two axes on the face."""
    pattern, root = 0x2AAAA, 0x1A1             # LOOKUP_TABLE[n - 6] for n = 20
    scale = root - 1
    face, bits = divmod(bits, pattern)
    a, b = divmod(bits, root)
    a = a * 2 / scale - 1 + 1 / scale
    b = b * 2 / scale - 1 + 1 / scale
    v = {0: (1, a, b), 1: (a, 1, b), 2: (a, b, 1), 3: (-1, a, b), 4: (a, -1, b), 5: (a, b, -1)}.get(face, (0, 0, 1))
    return _norm(v)


def _forward(up, yaw):
    """The forward vector: a world axis crossed with up (haloreach.dll 0xDBF14), turned yaw radians about up."""
    if abs(up[1]) > abs(up[0]):
        b = _norm((0.0, up[2], -up[1]))
    else:
        b = _norm((up[2], 0.0, -up[0]))
    s, c = (0.0, -1.0) if abs(abs(yaw) - math.pi) < 1e-7 else (math.sin(yaw), math.cos(yaw))
    d = sum(x * y for x, y in zip(b, up)) * (1 - c)
    cr = _cross(b, up)
    return _norm(tuple(up[k] * d + b[k] * c - cr[k] * s for k in range(3)))


def _size(bits):
    v = bits.u(11)
    return 0.0 if v == 0 else 200.0 if v == 0x7FF else (v - 1) * 0.0977517142892 + 0.0488758571446


def _object(bits, bounds):
    if not bits.u(1):
        return None
    o = {"unk00": bits.u(2)}
    o["folder"] = None if bits.u(1) else bits.u(8)
    o["item"] = None if bits.u(1) else bits.u(5)
    bits.u(1)                                   # (a position-encoding bit; both values use the bounds' bit counts)
    nb = _pos_bits(bounds)
    o["pos"] = [round((0.5 + bits.u(n)) * ((hi - lo) / (1 << n)) + lo, 4) for n, (lo, hi) in zip(nb, bounds)]
    up = (0.0, 0.0, 1.0) if bits.u(1) else _up(bits.u(20))
    yaw = bits.u(14) * 0.0003834952 - 3.1415927 + 0.0001917476
    f = _forward(up, yaw)
    o.update(up=[round(c, 5) for c in up], forward=[round(c, 5) for c in f],
             left=[round(c, 5) for c in _norm(_cross(up, f))], yaw=round(math.degrees(yaw), 3))
    o["relative_to"] = bits.u(10) - 1            # (unk2C; -1 for every object of the files read)
    st = bits.u(2)
    shape = {"shape": SHAPES[st]} if st else None
    if st == 1:
        shape["radius"] = _size(bits)
    elif st == 2:
        shape["radius"], shape["top"], shape["bottom"] = _size(bits), _size(bits), _size(bits)
    elif st == 3:
        shape["width"], shape["length"], shape["top"], shape["bottom"] = (_size(bits), _size(bits), _size(bits),
                                                                         _size(bits))
    o["shape"] = shape
    seq = bits.u(8)
    o["spawn_sequence"] = seq - 256 if seq >= 128 else seq
    o["respawn_time"] = bits.u(8)
    t = bits.u(5)
    o["mp_type"] = MP_TYPES[t] if t < len(MP_TYPES) else t
    o["label_index"] = None if bits.u(1) else bits.u(8)
    flags = bits.u(8)
    o["physics"] = PHYSICS[flags >> 6]
    o["gametype_specific"] = bool(flags & 0x20)
    o["symmetry"] = SYMMETRY[(flags >> 2) & 3]
    o["placed_at_start"] = not flags & 2
    o["flags"] = flags
    o["team"] = bits.u(4) - 1                    # 0.. teams, 8 neutral, -1 none
    o["color"] = -1 if bits.u(1) else bits.u(3)  # -1: the team's colour
    if t == 1:
        o["spare_clips"] = bits.u(8)
    elif 12 <= t <= 14:
        o["channel"], o["teleport_flags"] = bits.u(5), bits.u(5)
    elif t == 19:
        o["location_name"] = bits.u(8) - 1
    return o


def parse(data):
    """A Reach map variant file's contents: dict(title, description, author, map_id, version, bounds, budget, labels,
    objects, folders, ok). objects: [{index, folder, item, pos, up, forward, left, yaw, shape, spawn_sequence,
    respawn_time, mp_type, label_index, label, team, physics, gametype_specific, symmetry, placed_at_start, ...}]."""
    ch = chunks(data)
    if "_cmp" in ch and "mvar" not in ch:      # a compressed chunk (some user files): a byte 0 (zlib), the size, the
        off, size, _ = ch["_cmp"]               # whole mvar chunk deflated
        data = data[:off] + zlib.decompress(data[off + 17:off + size])
        ch = chunks(data)
    if "mvar" not in ch:
        raise ValueError("not a map variant (no mvar chunk)")
    off, size, ver = ch["mvar"]
    if size != 0x7028:
        raise ValueError(f"not a Halo: Reach map variant (mvar chunk 0x{size:x}, version {ver})")
    b = Bits(data, off + 12 + 0x18)
    h = {"content_type": b.u(4) - 1, "file_length": b.u(32)}
    b.raw(32)                                   # (owner / share / server ids)
    h["activity"], h["game_mode"], h["engine"] = b.u(3) - 1, b.u(3), b.u(3)
    h["map_id"], h["engine_category"] = b.u(32), b.u(8)
    authors = []
    for _ in range(2):
        b.raw(16)                                # (time, xuid: not kept)
        authors.append(b.cstr(16))
        b.u(1)
    h["title"], h["description"] = b.wstr(128), b.wstr(128)
    if h["activity"] == 2:
        b.u(16)                                 # (hopper id)
    if h["game_mode"] == 1:
        b.u(8), b.u(2), b.u(2), b.u(8), b.u(32)
    elif h["game_mode"] == 2:
        b.u(2), b.u(32)
    version = b.u(8)
    b.u(32), b.u(32)
    n_folders = b.u(9)
    map_id = b.u(32)
    b.u(1), b.u(1)
    xs = [b.f32() for _ in range(6)]
    bounds = [(xs[0], xs[1]), (xs[2], xs[3]), (xs[4], xs[5])]
    budget = (b.u(32), b.u(32))
    n_labels = b.u(9)
    offs = [b.u(12) if b.u(1) else None for _ in range(n_labels)]
    labels = [None] * n_labels
    if n_labels:
        length, packed = b.u(13), b.u(1)
        buf = zlib.decompress(b.raw(b.u(13))[4:]) if packed else b.raw(length)
        labels = [None if o is None else buf[o:buf.index(b"\0", o)].decode("latin-1") for o in offs]
    if version >= 32:
        b.u(32), b.u(16), b.u(16), b.u(64)
    objects = []
    for k in range(OBJECTS):
        o = _object(b, bounds)
        if o is not None:
            o["index"] = k
            li = o["label_index"]
            o["label"] = labels[li] if li is not None and li < len(labels) else None
            objects.append(o)
    folders = [(b.u(8), b.u(8), b.u(8)) for _ in range(n_folders)]
    end = off + size
    counts = {}
    for o in objects:
        counts[o["folder"]] = counts.get(o["folder"], 0) + 1
    # (the counts are 8-bit: Breakneck's 258 pieces of one folder read 2)
    ok = (b.p <= end * 8 and all(placed == counts.get(i, 0) & 0xFF for i, (_, _, placed) in enumerate(folders))
          and not any(data[(b.p + 7) // 8:end]))
    return dict(title=h["title"], description=h["description"], authors=authors, map_id=map_id,
                header_map_id=h["map_id"], version=version, bounds=bounds, budget=budget, labels=labels,
                objects=objects, folders=folders, ok=ok)


_PAL = {}


def palette(map_id):
    """The map's palette folders [{palette, name, objects}] (maps/_shapes/reach_palettes.json), or None."""
    if not _PAL:
        _PAL.update(json.load(open(PALETTES, encoding="utf-8")) if os.path.exists(PALETTES) else {})
    return _PAL.get(str(map_id))


def read(path):
    """parse() of a file, with each object's name from its map's palette (None when the palette lacks it) and the
    base map's folder name (maps/<name>)."""
    v = parse(open(path, "rb").read())
    pal = palette(v["map_id"])
    v["map"] = pal["map"] if pal else None
    for o in v["objects"]:
        fi = o["folder"]
        f = pal["folders"][fi] if pal and fi is not None and fi < len(pal["folders"]) else None
        o["name"] = (f["objects"][o["item"] or 0] or None) if f and (o["item"] or 0) < len(f["objects"]) else None
        o["folder_name"] = f["name"] if f else None
    v["path"] = path
    return v


# --- where MCC keeps map variants, and which one a match runs on
USER_DIRS = {"reach": "HaloReach", "h3": "Halo3", "h4": "Halo4", "h2a": "Halo2A"}      # LocalLow\MCC\... folders
GAME_DIRS = {"reach": "haloreach", "h3": "halo3", "h4": "halo4", "h2a": "groundhog"}  # in MCC's install folder
SAME = 0.6            # share of the live Forge pieces a file must place (same name within NEAR) to be the match's
NEAR = 0.3


def library(game="reach", mcc=None, home=None, kind="map"):
    """Every map variant file MCC lists for a game: the player's own (LocalLow\\MCC\\LocalFiles\\<xuid>\\<Game>\\Map,
    saved in Forge or copied in), the ones it downloaded (Temporary\\UserContent\\<Game>\\Map) and the built-in ones
    (<MCC>\\<game>\\map_variants, hopper_map_variants). kind "game": game variants (.bin; ...\\GameType, game_variants,
    hopper_game_variants). (Linux / Proton: UNKNOWN, the Wine prefix is not looked in.)"""
    if mcc is None:
        from . import paths
        mcc = paths.mcc()
    low = os.path.join(home or os.path.expanduser("~"), "AppData", "LocalLow", "MCC")
    sub, ext = ("Map", "*.mvar") if kind == "map" else ("GameType", "*.bin")
    pats = [os.path.join(low, "LocalFiles", "*", USER_DIRS[game], sub, ext),
            os.path.join(low, "Temporary", "UserContent", USER_DIRS[game], sub, ext)]
    if mcc:
        pats += [os.path.join(mcc, GAME_DIRS[game], d + kind + "_variants", ext) for d in ("", "hopper_")]
    return [p for pat in pats for p in sorted(glob.glob(pat))]


def header_map_id(path):
    """The map id in a file's content header (chdr +0x3C), without decoding it; None when it has none."""
    with open(path, "rb") as f:
        head = f.read(0x300)
    ch = chunks(head)
    if "chdr" not in ch:
        return None
    return struct.unpack_from("<I", head, ch["chdr"][0] + 0x3C)[0]


def map_id_of(base):
    """A Reach map folder's map id (reach_palettes.json), or None."""
    palette(0)
    return next((int(k) for k, p in _PAL.items() if p["map"] == base), None)


_READ = {}


def _cached(path):
    key = (path, os.path.getmtime(path))
    if key not in _READ:
        _READ[key] = read(path)
    return _READ[key]


def find(base, pieces, files=None):
    """The map variant file a match on base runs (pieces: the live Forge pieces [(name, pos, axes)], brain/forge.py
    live_pieces): of the files on its map, the one placing the largest share of the live pieces that its palette has
    (the base map's own scenery is not in a variant), at least SAME; ties to the newest. -> (variant, share) or
    (None, best share)."""
    best, best_share = None, 0.0
    for share, mtime, v in candidates(base, pieces, files):
        key = (round(share, 3), mtime)
        if share >= SAME and (best is None or key > best[0]):
            best = (key, v)
        best_share = max(best_share, share)
    return (best[1], best[0][0]) if best else (None, best_share)


def candidates(base, pieces, files=None):
    """[(share, file time, variant)] of every readable map variant file on base (find): the share of the live pieces
    its palette has that it places."""
    mid = map_id_of(base)
    names = {n for f in (palette(mid) or {}).get("folders", []) for n in f["objects"]}
    live = [(n, p) for n, p, _ in pieces if n in names]
    out = []
    if mid is None or not live:
        return out
    for path in library() if files is None else files:
        try:
            if header_map_id(path) != mid:
                continue
            v = _cached(path)
        except (OSError, ValueError, zlib.error, struct.error):
            continue
        if not v["ok"]:
            continue
        by = {}
        for o in v["objects"]:
            by.setdefault(o["name"], []).append(o["pos"])
        share = sum(1 for n, p in live if any(math.dist(p, q) <= NEAR for q in by.get(n, ()))) / len(live)
        out.append((share, os.path.getmtime(path), v))
    return out


# (custom, Nov 22) Layouts filed before their .mvar file was on this PC (or read) have no name: LiDAR listed them as
# "Forge layout F1ED". name_layouts names them from the files now here, when one name is clearly theirs: the best file
# places NAME_SHARE of their pieces, NAME_MIN pieces at least, and no file with another name comes within NAME_TIE.
NAME_SHARE = 0.9
NAME_MIN = 30
NAME_TIE = 0.05


def layout_name(base, pieces, files=None):
    """(name the game shows, its file's variant, share) for a filed layout (pieces: variant.json's, variants.pieces_of),
    or (None, None, best share) when no file is clearly its own (NAME_SHARE, NAME_MIN, NAME_TIE)."""
    from . import variants
    found = sorted(candidates(base, pieces, files), key=lambda c: (c[0], c[1]), reverse=True)
    if not found or len(pieces) < NAME_MIN or found[0][0] < NAME_SHARE:
        return None, None, found[0][0] if found else 0.0
    share, _, v = found[0]
    name = variants.title(v["title"], v["path"])
    if not name or any(s >= share - NAME_TIE and variants.title(o["title"], o["path"]) != name
                       for s, _, o in found[1:]):
        return None, None, share
    return name, v, share


def name_layouts(write=True, files=None):
    """Name every filed Reach layout with no name yet (layout_name): variant.json "name" (the file's title, as
    mvar.write files it: brain/variants.title shows it) and "named_from" (the file). -> [(layout, name shown or None,
    file, share)]."""
    import glob as _glob
    from . import variants
    out = []
    for p in sorted(_glob.glob(os.path.join(variants.ROOT, "reach_*", variants.SUB, "*", "variant.json"))):
        layout = os.path.relpath(os.path.dirname(p), variants.ROOT).replace("\\", "/")
        info = variants.info(layout)
        if not info or info.get("name"):
            continue
        name, v, share = layout_name(variants.base_of(layout), variants.pieces_of(info), files)
        fn = os.path.basename(v["path"]) if v else None
        out.append((layout, name, fn, share))
        if name and write:
            info = variants.info(layout)            # (read again: a match may have written it meanwhile)
            if info is not None and not info.get("name"):
                info.update(name=v["title"], named_from=fn)
                variants.save(layout, info)
    return out


def find_invasion(base, pieces, files=None):
    """The map variant file of a match on base whose Invasion labels (inv_res_*, inv_objective ...) the match runs, for a
    layout that adds only labels and hills to a built-in map (GitHub #26, the reporter's Tempest: no Forge building
    pieces of its own, so it was never filed as a variant, its labels never read and its Invasion played as Slayer with
    the game's own respawns, both teams' bots in the same zones): of this map's files with Invasion labels, the one
    placing the most live pieces (our find), else the only one there is. -> (variant, share) or (None, 0.0).
    (upstream 0.3.0, build 20261118-1714; it calls our find with its files, find and candidates unchanged)"""
    mid = map_id_of(base)
    if mid is None:
        return None, 0.0
    with_inv = []
    for path in library() if files is None else files:
        try:
            if header_map_id(path) != mid:
                continue
            v = _cached(path)
        except (OSError, ValueError, zlib.error, struct.error):
            continue
        if v["ok"] and any((o.get("label") or "").startswith(("inv_res", "inv_objective")) for o in v["objects"]):
            with_inv.append(path)
    if not with_inv:
        return None, 0.0
    v, share = find(base, pieces, files=with_inv)
    if v is None and len(with_inv) == 1:
        return _cached(with_inv[0]), share
    return v, share


# --- the variant's objects in the scenario schema (tools/reach_export.py writes the same from a map's own scenario),
# for brain/maps.py load_map, brain/invasion.py layout, tools/lidar.py objective_points
SPAWN_POINTS = ("respawn_point", "respawn_point_invisible")
BOUNDARY = {"kill_volume": "hard", "soft_kill_volume": "soft", "safe_volume": "safe", "soft_safe_volume": "soft_safe"}
VEHICLE_TYPES = ("light_vehicle", "heavy_vehicle", "flying_vehicle", "turret")


def _boundary(sh):
    """A Forge shape as the scenario export's "boundary" (w = radius or width, l = box length, up / down heights)."""
    if not sh:
        return None
    if sh["shape"] == "box":
        return dict(shape="box", w=sh["width"], l=sh["length"], up=sh["top"], down=sh["bottom"])
    return dict(shape=sh["shape"], w=sh["radius"], l=0.0, up=sh.get("top", sh["radius"]),
                down=sh.get("bottom", sh["radius"]))


def scenario_objects(v):
    """objects.json-style lists from a read() variant: netgame_flags (every labelled object; "seq" its spawn sequence,
    which Invasion uses as the phase; "phase" on inv_* labels), spawns, equipment (weapons), vehicles. Spawn points with
    a game type's own label (inf_spawn, inv_slayer, race_spawn ...) list that label as their game, so load_map's slayer
    and CTF lists leave them out."""
    from .live import brain_name
    out = dict(netgame_flags=[], spawns=[], equipment=[], vehicles=[], powerups=[])
    r = lambda xs: [round(x, 3) for x in xs]
    for o in v["objects"]:
        name, label, t = o["name"] or "", o["label"] if o["label"] not in (None, "none") else None, o["team"]
        # facing: the world heading of the object's forward (the file's yaw turns about up from an axis that flips
        # between world x and y with up's tilt: 18 of Spire's 183 objects read 90 deg off, its core's shield door
        # walled across the core's stand; the heading matches the live pieces' axes, 48 of 52 to the degree)
        pos, mp = r(o["pos"]), o["mp_type"]
        yaw = round(math.degrees(math.atan2(o["forward"][1], o["forward"][0])), 3)
        common = dict(team=t, pos=pos, facing=yaw)
        if mp == "spawn_point" or name in SPAWN_POINTS or name == "initial_spawn_point":
            teams = [t] if t in (0, 1) and label != "ffa_only" else [0, 1]
            games = ["slayer", "ctf"] if label in (None, "team_only", "ffa_only") else [label]
            for k in teams:
                sp = dict(pos=pos, team=k, facing=yaw, games=games)
                if name == "initial_spawn_point":
                    sp["initial"] = True
                if label:
                    sp["label"], sp["seq"] = label, o["spawn_sequence"]
                out["spawns"].append(sp)
            continue
        if mp == "weapon":
            out["equipment"].append(dict(item=brain_name(name), tag=name, path=name, yaw=yaw, team=t, pos=pos,
                                         games=["all games"], spawn_time=o["respawn_time"], label=label))
        elif mp in VEHICLE_TYPES:
            out["vehicles"].append(dict(item=name, tag=name, path=name, yaw=yaw, team=t, pos=pos,
                                        spawn_time=o["respawn_time"], label=label))
        elif mp == "powerup":
            # (custom, Nov 23, the owner's Beaver Creek report "These are overshields": its powerup_red was left out with
            # the other non-weapons, so no bot went for it; kept apart from the weapons' placements, brain/maps.py
            # power_items reads them)
            out["powerups"].append(dict(item=name, tag=name, path=name, yaw=yaw, team=t, pos=pos,
                                        spawn_time=o["respawn_time"], label=label))
        if mp in ("teleporter_2way", "teleporter_sender", "teleporter_receiver"):
            kinds = {"teleporter_2way": ["teleport from", "teleport to"], "teleporter_sender": ["teleport from"],
                     "teleporter_receiver": ["teleport to"]}[mp]
            for k in kinds:
                out["netgame_flags"].append(dict(common, type=k, id=o.get("channel", 0),
                                                 two_way=mp == "teleporter_2way"))
        if not label:
            continue
        if label == "ctf_flag_return":
            out["netgame_flags"] += [dict(common, type="ctf - flag", id=t), dict(common, type="CTF flag return", id=t)]
            continue
        f = dict(common, type=label, id=0, object=name, seq=o["spawn_sequence"], up=r(o["up"]),
                 gametype_specific=o["gametype_specific"], placed_at_start=o["placed_at_start"])
        if label.startswith("inv_"):
            f["phase"] = o["spawn_sequence"]
        b = _boundary(o["shape"])
        if b:
            f["boundary"] = {k: (round(x, 3) if isinstance(x, float) else x) for k, x in b.items()}
        out["netgame_flags"].append(f)
    return out


def killzones(v):
    """The variant's Forge kill and safe boundaries in the shared kill-zone schema (brain/oob.py reads it; tools/
    killzones.py writes the built-in maps' the same way): {"volumes": [volume]}, volume =
      kind      "hard" (kill_volume), "soft" (soft_kill_volume), "safe" (safe_volume: outside it kills),
                "soft_safe" (soft_safe_volume)
      shape     "box", "cylinder" or "sphere"
      center    [x, y, z] world units: the object's position moved along its up by (top - bottom) / 2 (box and
                cylinder), its position (sphere)
      size      box [width, length, top + bottom] (full extents; INFERRED: width along forward, length along left);
                cylinder [radius, radius, top + bottom]; sphere [radius, radius, radius] (as tools/killzones.py)
      radius, height   cylinder / sphere: the radius; cylinder: top + bottom (the same numbers as size, by name)
      rotation  {"forward": [x, y, z], "up": [x, y, z]} unit vectors (left = up x forward); left out when the object
                is not turned (forward 1, 0, 0, up 0, 0, 1)
      yaw       degrees about up (the file's angle)
      source    "mvar"; label: the piece's name (kill_volume ...); forge_label: its Forge label or None
      gametype_specific   True: it spawns only in game types that use forge_label (the file's flag)
      placed_at_start     False: it is not there when the match starts
      seq       its spawn sequence (Invasion's inv_gates: the phase it closes, brain/oob.py volumes)"""
    vols = []
    for o in v["objects"]:
        kind = BOUNDARY.get(o["name"] or "")
        sh = o["shape"]
        if not kind or not sh:
            continue
        up, f = o["up"], o["forward"]
        if sh["shape"] == "sphere":
            center, size = list(o["pos"]), [sh["radius"]] * 3
        else:
            h = sh["top"] + sh["bottom"]
            center = [o["pos"][k] + up[k] * (sh["top"] - sh["bottom"]) / 2 for k in range(3)]
            size = [sh["radius"], sh["radius"], h] if sh["shape"] == "cylinder" else [sh["width"], sh["length"], h]
        vol = dict(kind=kind, shape=sh["shape"], center=[round(c, 3) for c in center], size=[round(s, 3) for s in size],
                   yaw=round(o["yaw"], 3), source="mvar", label=o["name"],
                   forge_label=o["label"] if o["label"] != "none" else None,
                   gametype_specific=o["gametype_specific"], placed_at_start=o["placed_at_start"],
                   seq=o["spawn_sequence"])
        if sh["shape"] != "box":
            vol["radius"] = round(sh["radius"], 3)
            if sh["shape"] == "cylinder":
                vol["height"] = round(size[2], 3)
        if [round(c, 4) for c in f] != [1, 0, 0] or [round(c, 4) for c in up] != [0, 0, 1]:
            vol["rotation"] = dict(forward=f, up=up)
        vols.append(vol)
    return {"volumes": vols}


def write(name, v, share=None):
    """File a variant's objects (mvar_objects.json) and boundaries (killzones.json) in its folder maps/<name>/ and its
    file in variant.json "mvar". Returns (flags, spawns, volumes) counted."""
    d = os.path.join(ROOT, name)
    os.makedirs(d, exist_ok=True)
    objs = scenario_objects(v)
    objs["source"] = dict(file=os.path.basename(v["path"]), title=v["title"], map_id=v["map_id"], share=share)
    kz = killzones(v)
    for fn, data in (("mvar_objects.json", objs), ("killzones.json", kz)):
        tmp = os.path.join(d, fn + ".tmp")
        json.dump(data, open(tmp, "w", encoding="utf-8"), indent=1)
        os.replace(tmp, os.path.join(d, fn))
    from . import variants
    info = variants.info(name)
    if info is not None:
        info["mvar"] = objs["source"]
        info["name"] = info.get("name") or v["title"]
        variants.save(name, info)
    return len(objs["netgame_flags"]), len(objs["spawns"]), len(kz["volumes"])


# --- game variants (.bin, BLF chunk mpvr 0x5028): the script options a custom Invasion (or any Megalo mode) was saved
# with ("Attacking Team", "Phase 1 Objective", "Phase 1 Duration" ...). Field order and widths from ReachVariantTool
# (DavidJCobb, GPL-3.0, reference/ReachVariantEditor: game_variants/base.cpp, types/multiplayer.cpp, components/*,
# formats/ugc_header.cpp, formats/localized_string_table.cpp); read up to the script's string table, the rest (the
# script's code) is not needed here. A parse is right when every option's name comes out of the string table.
TRAIT_BITS = (4, 3, 4, 3, 4, 4, 2, 3, 2, 2, 4, 4, 8, 8, 4, 2, 2, 2, 2, 2, 2, 8, 5, 4, 4, 2, None, 3, 2, 2, 3, 4, 3, 3,
              2)
# (None: jump height, a presence bit and 9 bits when it is set)
LANGUAGES = 12


def _bits_of(n):
    return n.bit_length()                       # (cobb::bitcount: bits to hold n)


def _strings(b, max_count, max_size, off_bits=None, size_bits=None):
    """A localized string table: [[12 languages' text or None]]."""
    off_bits, size_bits = off_bits or _bits_of(max_size - 1), size_bits or _bits_of(max_size)
    n = b.u(_bits_of(max_count))
    offs = [[b.u(off_bits) if b.u(1) else None for _ in range(LANGUAGES)] for _ in range(n)]
    if not n:
        return []
    size = b.u(size_bits)
    buf = zlib.decompress(b.raw(b.u(size_bits))[4:]) if b.u(1) else b.raw(size)
    txt = lambda o: None if o is None else buf[o:buf.index(b"\0", o)].decode("utf-8", "replace")
    return [[txt(o) for o in row] for row in offs]


def _traits(b):
    for n in TRAIT_BITS:
        if n is None:
            b.u(9 if b.u(1) else 0)
        else:
            b.u(n)


def read_game_variant(path):
    """A Halo: Reach game variant file's title, engine icon and script options: dict(title, description, icon,
    options=[{name, value, values: [names], range}], labels_hint, ok)."""
    data = open(path, "rb").read()
    ch = chunks(data)
    if "mpvr" not in ch:
        raise ValueError("not a Halo: Reach game variant (no mpvr chunk)")
    off = ch["mpvr"][0]
    b = Bits(data, off + 12 + 0x1C)
    engine = b.u(4)                              # 1 forge, 2 multiplayer (megalo), ...
    b.u(32), b.u(32)                             # (encoding, engine version)
    ctype = b.u(4) - 1
    b.u(32), b.raw(32)
    activity, game_mode = b.u(3) - 1, b.u(3)
    b.u(3), b.u(32), b.u(8)
    for _ in range(2):
        b.raw(16), b.cstr(16), b.u(1)
    title, desc = b.wstr(128), b.wstr(128)
    icon = b.u(8) if ctype == 6 else None
    if activity == 2:
        b.u(16)
    if game_mode in (1, 2):
        raise ValueError("a campaign / Firefight variant")
    b.u(1)                                       # (built in)
    for n in (4, 8, 5, 4, 7, 5, 4, 6, 7, 8, 8, 8, 4, 4, 6):    # general, respawn options
        b.u(n)
    _traits(b)                                   # respawn traits
    b.u(1), b.u(2), b.u(5), b.u(6)               # social; map flags
    _traits(b)
    b.u(8), b.u(8)
    for _ in range(3):
        _traits(b)
    b.u(7), b.u(7), b.u(7)
    b.u(3), b.u(3), b.u(2)                       # team scoring, species, designator switch
    for _ in range(8):
        b.u(4)
        _strings(b, 1, 0x20, 5, 6)
        b.u(4), b.u(1), b.u(32), b.u(32), b.u(32), b.u(5)
    b.u(2)
    for _ in range(6 * 5):                       # loadout palettes
        b.u(1), b.u(0 if b.u(1) else 7), b.u(8), b.u(8), b.u(8), b.u(4)    # (name: absent when its bit is 1)
    for _ in range(b.u(_bits_of(16))):           # script traits
        b.u(7), b.u(7)
        _traits(b)
    options = []
    for _ in range(b.u(_bits_of(16))):
        o = dict(name=b.u(7), desc=b.u(7), range=bool(b.u(1)))
        if o["range"]:
            o["default"], o["min"], o["max"], o["value"] = b.u(10), b.u(10), b.u(10), b.u(10)
        else:
            o["default"] = b.u(3)
            o["values"] = [dict(value=b.u(10), name=b.u(7), desc=b.u(7)) for _ in range(b.u(4))]
            o["current"] = b.u(3)
        options.append(o)
    strings = _strings(b, 112, 0x4C00)
    en = lambda i: strings[i][0] if 0 <= i < len(strings) else None
    ok = bool(options) and all(en(o["name"]) for o in options)
    out = []
    for o in options:
        row = dict(name=en(o["name"]), description=en(o["desc"]), range=o["range"])
        if o["range"]:
            sign = lambda v: v - 1024 if v >= 512 else v          # (10-bit signed values)
            row.update(value=sign(o["value"]), default=sign(o["default"]), min=sign(o["min"]), max=sign(o["max"]))
        else:
            vals = o["values"]
            row["values"] = [en(v["name"]) for v in vals]
            cur = vals[o["current"]] if o["current"] < len(vals) else None
            row.update(value=en(cur["name"]) if cur else None, number=cur["value"] if cur else None)
        out.append(row)
    return dict(title=title, description=desc, icon=icon, engine=engine, options=out, ok=ok,
                strings=[s[0] for s in strings])


# --- Halo 3 map variants (mvar chunk version 12): one bitstream from the chunk's byte 12, a content header then the
# variant. Field order and widths from Sopitive's HaloMapStudio notes (crates/hms-app/src/h3/mvar.rs: halo3.dll
# c_map_variant::decode; read only, reference/HaloMapStudio). Objects are named by their quota: kind << 16 | index
# into the map's palettes (maps/_shapes/h3_palettes.json, tools/forge_palette.py --h3). Halo 3 has no Forge labels:
# an objective is its object (ctf_flag_spawn_point, koth_hill_static, territory_static ...); its game_engine_flags
# (16 bits, which modes it spawns in) are kept raw: which bit is which mode is UNKNOWN. Its Forge has no kill
# boundary objects (none in any map's palette), so no volumes.
H3_PALETTES = os.path.join(ROOT, "_shapes", "h3_palettes.json")


def _deq(q, lo, hi, bits, mid=False):
    steps = (1 << bits) - 1
    steps -= steps % 2 if mid else 0
    return lo if q == 0 else hi if q >= steps else ((steps - q) * lo + q * hi) / steps


def _h3_axes(b):
    if b.u(1):
        up = (0.0, 0.0, 1.0)
    else:
        q = b.u(19)
        a, c = _deq((q >> 3) & 0xFF, -1, 1, 8, True), _deq((q >> 11) & 0xFF, -1, 1, 8, True)
        up = _norm({0: (1, a, c), 1: (a, 1, c), 2: (a, c, 1), 3: (-1, a, c), 4: (a, -1, c), 5: (a, c, -1)}.get(q & 7,
                                                                                                          (0, 0, 1)))
    yaw = _deq(b.u(8), -math.pi, math.pi, 8, True)
    return up, _forward(up, yaw), yaw


def parse_h3(data):
    """A Halo 3 map variant: dict(title, map_id, version, bounds, objects, quotas, ok); objects [{slot, quota, pos, up,
    forward, yaw, object_type, mp_flags, engine_flags, team, spawn_time, shape, placed}] (placed False: a scenario
    object left where the map has it)."""
    ch = chunks(data)
    if "mvar" not in ch or ch["mvar"][2] != 12:
        raise ValueError("not a Halo 3 map variant (mvar chunk version 12)")
    off, size, _ = ch["mvar"]
    b = Bits(data[:off + size], off + 12)
    b.raw(8)
    title = b.wstr(16)
    b.cstr(128), b.cstr(16), b.u(5), b.u(1), b.raw(24), b.u(32), b.u(32)
    header_map, _ = b.u(32), b.u(4)
    b.u(3), b.u(16), b.raw(8)
    version, _ = b.u(8), b.u(32)
    n_scen, n_var, n_quota = b.u(10), b.u(10), b.u(9)
    map_id, _ = b.u(32), b.u(1)
    xs = [b.f32() for _ in range(6)]
    bounds = [(xs[0], xs[1]), (xs[2], xs[3]), (xs[4], xs[5])]
    b.u(4), b.f32(), b.f32()
    objects = []
    for slot in range(min(n_var, 640)):
        if not b.u(1):
            continue
        o = dict(slot=slot, flags=b.u(16), quota=b.u(32), placed=False)
        if o["quota"] >= 1 << 31:
            o["quota"] -= 1 << 32
        if b.u(1):
            b.raw(8)                             # (parent object id)
        if b.u(1):
            o["placed"] = True
            o["pos"] = [round(_deq(b.u(16), lo, hi, 16), 4) for lo, hi in bounds]
            up, f, yaw = _h3_axes(b)
            o.update(up=[round(c, 5) for c in up], forward=[round(c, 5) for c in f], yaw=round(math.degrees(yaw), 3))
            o["object_type"], o["mp_flags"], o["engine_flags"] = b.u(8), b.u(8), b.u(16)
            b.u(8)
            o["spawn_time"], o["team"], st = b.u(8), b.u(8), b.u(8)
            vals = [_deq(b.u(16), 0.0, 60.0, 16) for _ in range({1: 1, 2: 3, 3: 4}.get(st, 0))]
            o["shape"] = None if not vals else dict(zip({1: ("radius",), 2: ("radius", "top", "bottom"),
                                                          3: ("width", "length", "top", "bottom")}[st], vals),
                                                     shape=SHAPES[st])
        objects.append(o)
    for _ in range(14):
        b.u(9)
    quotas = [dict(definition=b.u(32), min=b.u(8), max=b.u(8), placed=b.u(8), allowed=b.u(8), price=b.f32())
              for _ in range(n_quota)]
    if version >= 14:
        b.raw(16)
    # (the quotas' placed counts are no check here: they match the objects in 87% of the shipped files' quotas only)
    ok = b.p <= (off + size) * 8 and version in (13, 14) and all(-1 <= o["quota"] < len(quotas) for o in objects)
    return dict(title=title, map_id=map_id, header_map_id=header_map, version=version, bounds=bounds,
                scenario_objects=n_scen, objects=objects, quotas=quotas, ok=ok)


def read_h3(path):
    """parse_h3() of a file with each object's name ("name", None when its palette is not exported) and the base map's
    folder ("map"), plus the objective objects (goals palette, kind 6) as "objectives" [(name, pos, team)]."""
    v = parse_h3(open(path, "rb").read())
    pal = (json.load(open(H3_PALETTES, encoding="utf-8")) if os.path.exists(H3_PALETTES) else {}).get(str(v["map_id"]))
    v["map"], v["path"] = pal["map"] if pal else None, path
    for o in v["objects"]:
        q = v["quotas"][o["quota"]] if 0 <= o["quota"] < len(v["quotas"]) else None
        kind, idx = (q["definition"] >> 16, q["definition"] & 0xFFFF) if q else (None, None)
        names = (pal or {}).get("kinds", {}).get(str(kind), [])
        o["kind"], o["name"] = kind, names[idx] if idx is not None and idx < len(names) else None
    v["objectives"] = [(o["name"], o["pos"], o["team"]) for o in v["objects"] if o["kind"] == 6 and o["placed"]]
    return v


# (upstream 0.3.0, build 20261114-1330) Halo 4 / H2A map variants, for tools/h3_forge_import.py (the LiDAR
# Simulator's layouts, note #19b): his parse_h4 / read_h4 and what they need (expand, _idx, H4_TYPES, H4_PHYSICS), as
# his; our find / candidates / layout_name / name_layouts are unchanged.
# --- Halo 4 (mvar chunk version 50) and Halo 2 Anniversary (52) map variants: the chunk's bitstream from byte 36, a
# content header, then Reach's layout with wider fields: 651 slots, palette index 8 bits (flat over the scenario's
# "map variant palettes" entries) + variant index 5 bits, Reach's position and rotation coding (axis steps capped at
# 0x400000), parent 10, scale 6, lock 1, shape (16-bit values), object type 6, placement flags 10 (H2A 11), then the
# type's tail; the quota table after the slots ({min, max, placed}: Halo 4 8 bits each, H2A 10). H2A adds a third byte
# after user data and a bsp index (2 bits) on an out-of-bounds position; MCC's own Forge saves body version 51 (Halo 4)
# / 53 (H2A) with a 16-byte map GUID before the slots. Field order and widths from Sopitive's HaloMapStudio notes
# (crates/hms-app/src/h4/mvar.rs; read only, reference/HaloMapStudio). The check: every quota's placed count equals the
# objects read with that palette index (tools/test_mvar_h4.py runs it on every file MCC has). Objects are named from
# maps/_shapes/h4_palettes.json / h2a_palettes.json (tools/forge_palette.py --h4h2a).
H4_TYPES = {1: "weapon", 2: "grenade", 5: "equipment", 7: "light vehicle", 8: "heavy vehicle", 9: "flying vehicle",
            11: "device", 12: "dominion pad", 13: "teleporter sender", 14: "teleporter receiver", 15: "teleporter 2-way",
            16: "player spawn", 17: "respawn zone", 26: "safe area", 27: "kill area", 31: "trait zone",
            32: "initial ordnance", 33: "random ordnance", 34: "objective ordnance"}
# placement bits 6-7 (not Reach's order): 3 on every Forge structure piece of the 452 files (shipped maps build on them:
# fixed), 0 on crates, vehicles, spawns (normal), 1 on some crates and spawn points (phased by elimination; unproven live,
# so the nav keeps those pieces solid: a wall missed walks bots into it, a phased crate kept costs a detour)
H4_PHYSICS = ("normal", "phased", "?", "fixed")


def expand(data):
    """A BLF file with its _cmp chunk (zlib, the mvar chunk inside) inflated in place; the file itself when none."""
    ch = chunks(data)
    if "_cmp" in ch and "mvar" not in ch:
        off, size, _ = ch["_cmp"]
        data = data[:off] + zlib.decompress(data[off + 17:off + size])
    return data


def _idx(b, n):
    return None if b.u(1) else b.u(n)


def parse_h4(data):
    """A Halo 4 or H2A map variant: dict(game, title, map_id, version, bounds, objects, quotas, ok); objects [{slot,
    quota, variant, pos, up, forward, yaw, parent, object_type, mp_type, placement, team, spawn_sequence, user_data,
    shape, placed}] (placed: drawn at the start, not a "place later" object)."""
    data = expand(data)
    ch = chunks(data)
    off, size, ver = ch.get("mvar", (0, 0, 0))
    if ver not in (50, 52):
        raise ValueError(f"not a Halo 4 / H2A map variant (mvar chunk version {ver})")
    h2a = ver == 52
    body = data[off:off + size] + bytes(max(0, 0x7428 - size))     # (a short H2A file: the rest is zeros)
    b = Bits(body, 36)
    ctype = b.u(4) - 1
    b.u(32), b.raw(32)                          # (file size; uid, parent, root, game ids)
    activity, _, engine = b.u(2), b.u(3), b.u(3)
    header_map, _ = b.u(32), b.u(8)
    authors = []
    for _ in range(2):
        b.raw(16)
        authors.append(b.cstr(16))
        b.u(1)
    title, description = b.wstr(128), b.wstr(128)
    b.u({3: 32, 4: 32, 6: 8}.get(ctype, 0))
    if activity == 2:
        b.u(16)
    b.u({3: 52, 4: 34}.get(engine, 0))
    version = b.u(8)
    b.u(32), b.u(32)
    n_quota, map_id = b.u(9), b.u(32)
    b.u(2)
    xs = [b.f32() for _ in range(6)]
    bounds = [(xs[0], xs[1]), (xs[2], xs[3]), (xs[4], xs[5])]
    budget = (b.u(32), b.u(32))
    n_labels = b.u(9)
    offs = [b.u(12) if b.u(1) else None for _ in range(n_labels)]
    labels = []
    if n_labels:
        length, packed = b.u(13), b.u(1)
        buf = zlib.decompress(b.raw(b.u(13))[4:]) if packed else b.raw(length)
        labels = [None if o is None or o >= len(buf) else buf[o:buf.index(b"\0", o)].decode("latin-1") for o in offs]
    if version >= (53 if h2a else 51):
        b.raw(16)                               # (map GUID)
    nb = _pos_bits(bounds, cap=0x400000)
    objects = []
    for slot in range(OBJECTS):
        if not b.u(1):
            continue
        o = dict(slot=slot, flags=b.u(2), quota=_idx(b, 8), variant=_idx(b, 5))
        inb = b.u(1)
        if h2a and not inb:
            _idx(b, 2)                          # (bsp index: the axes then count from that bsp's box, not kept)
        o["in_bounds"] = bool(inb)
        o["pos"] = [round((0.5 + b.u(n)) * ((hi - lo) / (1 << n)) + lo, 4) for n, (lo, hi) in zip(nb, bounds)]
        up = (0.0, 0.0, 1.0) if b.u(1) else _up(b.u(20))
        yaw = b.u(14) * 0.0003834952 - 3.1415927 + 0.0001917476
        f = _forward(up, yaw)
        o.update(up=[round(c, 5) for c in up], forward=[round(c, 5) for c in f], yaw=round(math.degrees(yaw), 3))
        o["parent"], o["scale_q"], o["locked"] = b.u(10) - 1, b.u(6), bool(b.u(1))
        st = b.u(2)
        vals = [b.u(16) / 256.0 for _ in range((0, 1, 3, 4)[st])]
        o["shape"] = None if not st else dict(zip((None, ("radius",), ("radius", "top", "bottom"),
                                                  ("width", "length", "top", "bottom"))[st], vals), shape=SHAPES[st])
        t = o["object_type"] = b.u(6)
        o["mp_type"] = H4_TYPES.get(t, "ordinary" if t == 0 else t)
        o["placement"] = b.u(11 if h2a else 10)
        o.update(team=-1, spawn_sequence=0, user_data=0, labels=[])
        if t == 32:
            o["team"], o["ordnance"] = b.u(4) - 1, [b.u(8)]
            b.u(16)
        elif t in (33, 34):
            if t == 34:
                b.u(8)
            o["ordnance"] = [b.u(8) for _ in range(8)]
        elif t != 35:
            o["team"], o["spawn_time"], o["color"] = b.u(4) - 1, b.u(8), _idx(b, 3)
            seq, ud = b.u(8), b.u(8)
            o["spawn_sequence"], o["user_data"] = seq - 256 if seq >= 128 else seq, ud - 256 if ud >= 128 else ud
            if h2a:
                b.u(8)
            o["labels"] = [labels[i] if i < len(labels) else None for i in (_idx(b, 8) for _ in range(4))
                           if i is not None]
            b.u(8 if t in (1, 12, 20) else 16 if t == 11 and h2a else 5 if t == 31 else 10)   # (type's tail)
        o["placed"] = not o["placement"] & 0x10          # (bit 4: not placed at the start; set in no file read)
        o["physics"] = H4_PHYSICS[o["placement"] >> 6 & 3]
        objects.append(o)
    w = 10 if h2a else 8
    quotas = [dict(min=b.u(w), max=b.u(w), placed=b.u(w)) for _ in range(n_quota)]
    counts = {}
    for o in objects:
        if o["quota"] is not None:
            counts[o["quota"]] = counts.get(o["quota"], 0) + 1
    m = (1 << w) - 1
    ok = b.p <= len(body) * 8 and all(q["placed"] == counts.get(i, 0) & m for i, q in enumerate(quotas))
    return dict(game="h2a" if h2a else "h4", title=title, description=description, authors=authors, map_id=map_id,
                header_map_id=header_map, version=version, bounds=bounds, budget=budget, labels=labels,
                objects=objects, quotas=quotas, ok=ok)


_H4PAL = {}


def read_h4(path):
    """parse_h4() of a file with each object's name ("name": the palette variant's object, short; None when the
    palette is not exported or the slot is empty), its palette entry ("entry") and the base map's folder ("map")."""
    v = parse_h4(open(path, "rb").read())
    g = v["game"]
    if g not in _H4PAL:
        f = os.path.join(ROOT, "_shapes", g + "_palettes.json")
        _H4PAL[g] = json.load(open(f, encoding="utf-8")) if os.path.exists(f) else {}
    pal = _H4PAL[g].get(str(v["map_id"]))
    v["map"], v["path"] = pal["map"] if pal else None, path
    ents = pal["entries"] if pal else []
    for o in v["objects"]:
        e = ents[o["quota"]] if o["quota"] is not None and o["quota"] < len(ents) else None
        objs = e[2] if e else []
        i = o["variant"] or 0
        o["entry"], o["name"] = e[1] if e else None, (objs[i] or None) if i < len(objs) else None
    return v


def find_game_variant(title, files=None):
    """The game variant file whose title is the running variant's (the game keeps its title in memory: LiveReach
    variant_name; case aside), newest first; None when none matches or reads."""
    want = (title or "").strip().upper()
    hits = []
    for path in library(kind="game") if files is None else files:
        try:
            with open(path, "rb") as f:
                head = f.read(0x1C0)         # (the content header's own title, chdr +0x90, UTF-16: a quick pass)
            if head[0xC0:0x1C0].decode("utf-16-le", "replace").partition("\0")[0].strip().upper() != want:
                continue
            g = read_game_variant(path)
        except (OSError, ValueError, zlib.error, struct.error, IndexError):
            continue
        if g["ok"] and g["title"].strip().upper() == want:
            hits.append((os.path.getmtime(path), path, g))
    if not hits:
        return None
    _, path, g = max(hits)
    return dict(g, path=path)


def phase_styles(gv):
    """{phase: "ctf" | "assault" | "territories"} from a custom Invasion's "Phase N Objective" options (the issue #2
    player's: 1 Assault, 2 Territories, 3 CTF), {} when it has none."""
    out = {}
    for o in (gv or {}).get("options", []):
        name = (o.get("name") or "").lower()
        if name.startswith("phase ") and name.endswith(" objective") and name.split()[1].isdigit() and o.get("value"):
            out[int(name.split()[1])] = o["value"].lower()
    return out


def drop_point_move(gv):
    """(custom, Nov 12) A Headhunter variant's "Drop point movement time" in s: 30 for "30 seconds", 60 for "1 minute",
    0 for "never"; None when it has no such option (brain/headhunter.py Skulls)."""
    for o in (gv or {}).get("options", []):
        if (o.get("name") or "").lower() != "drop point movement time":
            continue
        v = (o.get("value") or "").lower().split()
        if v and v[0] == "never":
            return 0
        if len(v) == 2 and v[0].isdigit():
            return int(v[0]) * (60 if v[1].startswith("minute") else 1)
        return o.get("number")
    return None


def territory_rules(gv):
    """(custom, Nov 13) A Territories variant's rules: dict(style "symmetric" | "asymmetric", lock: Capture Lock on,
    capture: its Capture Time in s), None when it has none of them. MCC's own: TERRITORIES Asymmetric, lock off, 30 s;
    LAND GRAB Symmetric, lock on, 30 s; 3-PLOT Symmetric, lock off, 5 s (brain/modes.py Watch, director.mode_slots)."""
    out = {}
    for o in (gv or {}).get("options", []):
        name, v = (o.get("name") or "").lower(), (o.get("value") or "").lower()
        if name == "style" and v in ("symmetric", "asymmetric"):
            out["style"] = v
        elif name == "capture lock":
            out["lock"] = v == "enabled"
        elif name == "capture time":
            w = v.split()
            if len(w) == 2 and w[0].isdigit():
                out["capture"] = float(int(w[0]) * (60 if w[1].startswith("minute") else 1))
    return out or None


def _main(argv):
    path = argv[0]
    if path.lower().endswith(".bin"):
        g = read_game_variant(path)
        print(f"{g['title']!r}, engine icon {g['icon']}, parse {'OK' if g['ok'] else 'FAILED'}")
        for o in g["options"]:
            print(f"  {o['name']} = {o['value']}  {o.get('values') or (o.get('min'), o.get('max'))}")
        return
    if chunks(open(path, "rb").read(0x2000)).get("mvar", (0, 0, 0))[2] == 12:
        v = read_h3(path)
        print(f"Halo 3 {v['title']!r} on {v['map']} ({v['map_id']}), {len(v['objects'])} objects, parse "
              f"{'OK' if v['ok'] else 'FAILED'}")
        for o in v["objects"]:
            if o["placed"]:
                print(f"{o['slot']:3} {o['name'] or '?'} kind={o['kind']} team={o['team']} "
                      f"engine_flags=0x{o['engine_flags']:x} pos={o['pos']} yaw={o['yaw']} shape={o['shape']}")
        return
    v = read(path)
    if "--json" in argv:
        print(json.dumps(v, indent=1))
        return
    print(f"{v['title']!r} on {v['map']} ({v['map_id']}), version {v['version']}, {len(v['objects'])} objects, "
          f"labels {v['labels']}, parse {'OK' if v['ok'] else 'FAILED'}")
    for o in v["objects"]:
        sh = o["shape"] or {}
        print(f"{o['index']:3} {o['name'] or '?'}:{o['folder']}/{o['item']} {o['mp_type']} label={o['label']} "
              f"team={o['team']} seq={o['spawn_sequence']} gts={int(o['gametype_specific'])} "
              f"start={int(o['placed_at_start'])} pos={o['pos']} yaw={o['yaw']} up={o['up']} "
              f"{' '.join(f'{k}={v if isinstance(v, str) else round(v, 2)}' for k, v in sh.items())}")


if __name__ == "__main__":
    _main(sys.argv[1:])
