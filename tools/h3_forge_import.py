r"""The map layouts MCC lists for custom games in Halo 3, Reach, Halo 4 and Halo 2 Anniversary (custom_layouts: the
player's Forge saves in LocalFiles\<xuid>\<Halo3|Halo4|Halo2A>\Map and MCC's built-in ones, <game>\map_variants: Halo 3's
MLG versions, SAND TARP) filed as variants of their base maps (maps/<base>/variants/<id>/variant.json; its pieces read from the .mvar: brain/mvar.read_h3,
read_h4), so the LiDAR simulator lists them and the nav stands their Forge pieces up (maps/_shapes/<game>.json,
tools/object_shapes.py). Halo 3 has no live piece reader, so the file is its only source; a Halo 4 / H2A layout seen
live already (brain/variants.identify: no file behind it) sharing SAME of its objects is that folder, given the file's
pieces (a live read can miss some), else a new folder by the file's own id (two of the player's Halo 3 maps sharing
their spawns came out as one variant when matched by layout). Run by the LiDAR simulator at its start
(tools/lidar_sim.py); safe to run again (a filed one is rewritten from its file).

(upstream 0.3.0, build 20261114-1330) His file, with (custom, Nov 24) the owner's rule (note #19b): Halo 3, Halo 4 and
Halo 2 Anniversary only, NEVER Reach. On Reach it would rewrite the variant.json pieces the bots' nav reads (Renegade's,
say) and file the owner's Forge Printer saves as layouts; Reach layouts stay filed as our own code files them (brain/
variants.identify live, brain/mvar.write). So: no Reach reader (his read_reach is not here), GAMES lists the three, and
file_one refuses a Reach file or a reach_* base before reading anything, whoever calls it.

usage: python -I h3_forge_import.py      -> one line a variant
"""
import hashlib
import os
import sys
import time

if __name__ == "__main__":     # (run as a script: tools/ off the path; imported, the caller's path stays: live_bots
    # and lidar import tls and variant_strategy from tools/ after it)
    sys.path[:] = [p for p in sys.path if os.path.abspath(p or ".") != os.path.dirname(os.path.abspath(__file__))]
sys.path.insert(0,os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from brain import forge, maps, mvar, variants  # noqa: E402
from brain.callouts import read_json  # noqa: E402

CAPS = {"mlg", "ffa", "ctf", "swat", "koth", "tu", "2v2", "4v4"}


def title_of(v, path):
    """A layout's name: its own title, or for MCC's built-in ones whose title is a string id ("$h4_mvar_relay_name",
    "$halo2a_mvar_coag") its file's ("ca_forge_bonanza_relay" -> "Relay", "bloodline_classic" -> "Bloodline Classic",
    "hr_forgeWorld_asylum" -> "ForgeWorld Asylum")."""
    t = v.get("title") or ""
    if t and not t.startswith("$"):
        return t
    stem = os.path.splitext(os.path.basename(path))[0]
    for pre in ("hr_", "ca_forge_"):
        if stem.startswith(pre):
            stem = stem[len(pre):].partition("_")[2] if pre == "ca_forge_" else stem[len(pre):]
    return " ".join(w.upper() if w.lower() in CAPS else w[:1].upper() + w[1:] for w in stem.split("_") if w)


GAMES = ("h3", "h4", "h2a")     # (custom, Nov 24: the owner, "H3/H4/H2A only"; never "reach")
READERS = {"h3": mvar.read_h3, "h4": mvar.read_h4, "h2a": mvar.read_h4}


def never_reach(path, game):
    """(custom, Nov 24) A Reach file: by its game, or in a HaloReach / haloreach folder (mvar.USER_DIRS, GAME_DIRS)."""
    parts = {p.lower() for p in os.path.normpath(path).split(os.sep)}
    return game not in GAMES or bool(parts & {mvar.USER_DIRS["reach"].lower(), mvar.GAME_DIRS["reach"].lower()})


def pieces_of(v):
    """[(name, pos, (forward, left, up))] of a read variant's placed, named objects."""
    out = []
    for o in v["objects"]:
        if not o["placed"] or not o["name"]:
            continue
        up, fw = tuple(o.get("up") or (0, 0, 1)), tuple(o.get("forward") or (1, 0, 0))
        left = (up[1] * fw[2] - up[2] * fw[1], up[2] * fw[0] - up[0] * fw[2], up[0] * fw[1] - up[1] * fw[0])
        out.append((o["name"], tuple(o["pos"]), (fw, left, up)))
    return out


def seen_live(base, keys, fname, exact=False):
    """The id of a filed variant of base with this very layout (keys, from any file: MCC copies the running variant to
    Temporary\\UserContent under a new name at every match start), else one with no file behind it (or this file)
    sharing SAME of keys, the best; None. exact: this very layout only (Reach: its live read is the whole layout, and a
    similar file filed onto a layout the bots learned replaced its pieces and name, Nov 14)."""
    best = None
    for vid, (theirs, file, _) in sorted(filed(base).items()):
        if theirs == keys:
            return vid
        if exact or file not in (None, fname):
            continue
        share = len(keys & theirs) / max(1, min(len(keys), len(theirs)))
        if share >= variants.SAME and (best is None or share > best[0]):
            best = (share, vid)
    return best and best[1]


_FILED = {}      # base -> {vid: (object keys, its file or None, the file's mtime when filed)}, read once a run


def filed(base):
    """base's filed layouts (800+ of them across the games: read once, not a folder rescan a file)."""
    if base not in _FILED:
        d, _FILED[base] = os.path.join(maps.ROOT, base, variants.SUB), {}
        for vid in os.listdir(d) if os.path.isdir(d) else ():
            old = read_json(os.path.join(d, vid, "variant.json"))
            if old:
                m = old.get("mvar") or {}
                _FILED[base][vid] = ({tuple(k) for k in old.get("objects", [])}, m.get("file"), m.get("seen") or {})
    return _FILED[base]


IMPORT_V = 2     # a change to how a file is filed (2: readable built-in titles) reads every file once again


def stamp(path):
    """A file's record in its layout's "seen": its modified time and IMPORT_V."""
    return f"{round(os.path.getmtime(path))}:{IMPORT_V}"


def unchanged(path, base=None):
    """This file is filed already as it is now (its name and modified time in a layout's record): nothing to read."""
    fid, mt = file_id(path), stamp(path)
    return any(seen.get(fid) == mt for b in ([base] if base else list(_FILED)) for _, _, seen in filed(b).values())


def file_id(path):
    """A file's name for its variant's id and record: the player's own saves by their file name (as filed since Nov 8),
    MCC's built-in and playlist ones with their folder too (one file name in two playlists, two layouts)."""
    if "LocalFiles" in path:
        return os.path.basename(path)
    return os.path.basename(os.path.dirname(path)) + "/" + os.path.basename(path)


def file_one(path, game="h3"):
    """File one .mvar; (title, base, map name, pieces, solid pieces) or None (unreadable, no base map here, or (custom,
    Nov 24) a Reach file or base: never filed here, never read)."""
    if never_reach(path, game):
        return None
    v = READERS[game](path)
    v["title"] = title_of(v, path)
    base = v["map"]
    if not v.get("ok") or not base or base.startswith("reach_") or not os.path.isdir(os.path.join(maps.ROOT, base)):
        return None
    pieces = pieces_of(v)
    objs = read_json(os.path.join(maps.ROOT, base, "objects.json"))
    mine = variants.own([(n, p) for n, p, _ in pieces], variants.base_placed(objs))
    if len(mine) < variants.MIN_OWN:
        return None
    keys = {variants._key(n, p) for n, p in mine}
    fname = file_id(path)
    vid = seen_live(base, keys, fname) or "v" + hashlib.sha1(fname.encode()).hexdigest()[:8]
    name = f"{base}/{variants.SUB}/{vid}"
    old = variants.info(name) or {}
    now = time.strftime("%Y-%m-%d %H:%M")
    mt = stamp(path)
    seen = dict((old.get("mvar") or {}).get("seen") or {}, **{fname: mt})    # (every file with this layout, as filed)
    data = dict(old, id=vid, base=base, game=game, name=v["title"], first_seen=old.get("first_seen", now),
                last_seen=now, objects=[list(k) for k in sorted(keys)], count=len(keys),
                window=list(variants.union(old.get("window"), variants.window_of(
                    [p for _, p in mine] + list(variants.base_area(objs))))),
                pieces=[[n] + [round(c, 4) for c in tuple(p) + tuple(x for ax in a for x in ax)] for n, p, a in pieces],
                mvar=dict(file=fname, title=v["title"], mtime=mt, seen=seen))
    variants.save(name, data)
    filed(base)[vid] = (keys, fname, seen)
    solid = sum(1 for n, p, a in pieces if forge.block(n, p, a, game=game))
    return v["title"], base, name, len(pieces), solid


def custom_layouts(game):
    """The layout files MCC lists in its custom game lobby: the player's own (LocalFiles) and its built-in ones
    (<game>\\map_variants). Not the playlists' (hopper_map_variants: matchmaking versions the lobby never shows) nor
    Temporary\\UserContent (MCC's copy of the layout each match runs: one of these again). The player, Nov 14: "theres
    only 2 versions of sand trap on my pc, sand trap and sand tarp but on the simulator theres 7" (5 were playlists')."""
    return [f for f in mvar.library(game)
            if "LocalFiles" in f or os.path.basename(os.path.dirname(f)).lower() == "map_variants"]


def main():
    """The layouts MCC lists for custom games (custom_layouts: the player, Nov 14: Sandtrap's "SAND TARP" and the MLG
    layouts were missing, only his own saves were filed), each filed under its map; files filed already and unchanged
    are not read again."""
    for base in os.listdir(maps.ROOT):
        if not base.startswith("reach_") and os.path.isdir(os.path.join(maps.ROOT, base, variants.SUB)):
            filed(base)                             # (custom, Nov 24: Reach's layouts are not read either)
    for game in GAMES:                              # (custom, Nov 24: H3, H4, H2A; never Reach)
        for f in custom_layouts(game):
            if never_reach(f, game) or unchanged(f):
                continue
            try:
                got = file_one(f, game)
            except Exception as e:                  # (one unreadable file never stops the rest)
                print(f"{os.path.basename(f)}: {type(e).__name__}: {e}")
                continue
            if got:
                print(f"{got[0]!r} on {got[1]}: {got[3]} pieces, {got[4]} solid -> {got[2]}")


if __name__ == "__main__":
    main()
