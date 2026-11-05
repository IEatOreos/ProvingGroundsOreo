"""Tag names of a map by tag index, read from its MCC .map file (Reach, Halo 3, Halo 4, Halo 2 Anniversary). The game
keeps no tag names in memory, so a live object's tag id (low 16 bits: the tag index) names it through this list:
brain/forge.py identifies Forge pieces by it (e.g. objects\\levels\\forge\\ff_column\\ff_column), brain/live.py names
guns and objective items, brain/stations.py names whatever it reads from the object table.

The names come from the file's tag name index: one int32 offset per tag (-1: no name) into a buffer of null-terminated
paths. The index has to be followed entry by entry: the buffer is not stored in index order.

usage: python -I reach_tag_names.py <map> [reach|h3|h4|h2a]   (e.g. forge_halo) -> maps/_shapes/<game>_tags_<map>.json
       python -I reach_tag_names.py --check                     reads every saved list's .map file again and compares
"""
import json
import os
import struct
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from brain import paths  # noqa: E402  (where MCC is installed)

MCC = paths.mcc()
GAME_DIR = {"reach": "haloreach", "h3": "halo3", "h4": "halo4", "h2a": "groundhog"}
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "maps", "_shapes")


# Where an MCC cache file's header keeps its tag name table: name count at 32, names buffer pointer at 36, index pointer
# at 44, and the section offset table at 1228 (Reach, Halo 3) or 1220 (Halo 4, Halo 2 Anniversary). The two pointers
# are in the file's first section: file offset = pointer + that section's offset, wrapping at 32 bits (the offset is
# stored as its two's complement). The first layout whose table reads as tag paths wins.
LAYOUTS = ((32, 36, 44, 1228), (32, 36, 44, 1220))


def names_of(path):
    """[name by tag index] ("" where a tag has none), from the .map file's own tag name index."""
    with open(path, "rb") as f:
        head = f.read(0x1000)
        size = os.fstat(f.fileno()).st_size
        for n_at, buf_at, idx_at, sec_at in LAYOUTS:
            n, buf, idx = (struct.unpack_from("<I", head, o)[0] for o in (n_at, buf_at, idx_at))
            base = struct.unpack_from("<I", head, sec_at)[0]
            buf, idx = (buf + base) & 0xFFFFFFFF, (idx + base) & 0xFFFFFFFF
            if not 0 < n < 200000 or idx + 4 * n > size or buf >= size:
                continue
            f.seek(idx)
            offsets = struct.unpack(f"<{n}i", f.read(4 * n))
            f.seek(buf)
            blob = f.read(max(offsets) + 1024)
            names = [blob[o:blob.find(b"\0", o)].decode("ascii", "replace") if o >= 0 else "" for o in offsets]
            sample = [s for s in names if s][:50]
            if sample and all(s.isprintable() and "�" not in s for s in sample):
                return names
    raise SystemExit(f"{path}: no tag name table found (a newer MCC update may have moved it)")


def cached(map_name, game="reach"):
    """The map's tag names by index, from maps/_shapes/<game>_tags_<map>.json, made from the .map file the first time."""
    dst = os.path.join(OUT, f"{game}_tags_{map_name}.json")
    if not os.path.exists(dst):
        names = names_of(os.path.join(MCC, GAME_DIR[game], "maps", map_name + ".map"))
        os.makedirs(OUT, exist_ok=True)
        json.dump(names, open(dst, "w"))
    return json.load(open(dst))


def check():
    """Every saved list against a fresh read of its .map file: (maps that match, [(map, first differing index)])."""
    same, bad = 0, []
    for fn in sorted(os.listdir(OUT)):
        game, _, rest = fn.partition("_tags_")
        if not rest.endswith(".json") or game not in GAME_DIR:
            continue
        saved = json.load(open(os.path.join(OUT, fn)))
        fresh = names_of(os.path.join(MCC, GAME_DIR[game], "maps", rest[:-5] + ".map"))
        diff = next((i for i in range(max(len(saved), len(fresh)))
                     if (saved[i] if i < len(saved) else "") != (fresh[i] if i < len(fresh) else "")), None)
        if diff is None:
            same += 1
        else:
            bad.append((fn, diff))
    return same, bad


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]:
        same, bad = check()
        print(f"{same} maps match" + "".join(f"\n  {fn}: differs from index {i}" for fn, i in bad))
        raise SystemExit(1 if bad else 0)
    n = cached(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "reach")
    print(f"{sys.argv[1]}: {len(n)} tag names")
