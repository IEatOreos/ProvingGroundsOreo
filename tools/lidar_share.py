r"""Share LiDAR map scans between players (GitHub #19; the repository's lidar-maps/ folder keeps them by game).

(custom, Nov 24) Upstream 0.3.0's tools/lidar_share.py (build 20261123-0037): export, bundle and list (note #1), and
import by hand from a zip the owner picks (note #63). Upstream's fetch (downloading the author's bundles from the
releases page or his website) is not here, and nothing here downloads anything.

export: one map's scan (maps/<map>/lidar.json: the floor walked, the jumps people landed, lifts, teleporters, cover,
        weapons) into a small zip, lidar-share/<map>_<date>.zip beside the mod, with a manifest (map, game, build,
        what is in it). Nothing about the player goes in: no names (people are "human", bots "bot"), no folders, and
        the scan is checked for anything private before it is written (private(): e-mail addresses, user folders,
        Xbox ids, and our installer's privacy scan, tools/privacy.py: this PC's user name and profile path and the
        terms in .private_terms; what was found is named, the private words themselves never printed).
bundle: every scan of one game on this PC in one zip, lidar-maps-<game>.zip (bundle.json + <map>/manifest.json +
        <map>/lidar.json).
import: a shared zip (one map's, or a game's bundle) merged into this PC's scans, never replacing them: floor counts
        added, deaths and jump heights appended (the scan's own limits), jump links, teleporters, cover spots and
        weapons joined with exact duplicates dropped and every distinct variant kept. (custom, Nov 24) Their links are
        filtered as our own save filters ours (tools/lidar.py saved_link: never the map's rides, found_by "map", never
        a crouch-jump no person made), and an import is refused while a match runs (tools/match_lock.py: the match's
        LiDAR save rewrites lidar.json). The scan before is kept as lidar.json.before-import-<date>. A scan already
        imported (maps/<map>/lidar_imported.json) is skipped, so importing twice adds nothing twice. A map this
        version of the mod does not have is skipped.

usage: python -I lidar_share.py export <map>           (e.g. h3_construct, reach_20_sword_slayer, beavercreek)
       python -I lidar_share.py bundle <game>          (halo-ce halo-2 halo-2-anniversary halo-3 halo-3-odst halo-reach
                                                         halo-4)
       python -I lidar_share.py import <file.zip>
       python -I lidar_share.py list                   maps with a scan on this PC
"""
import hashlib
import json
import os
import re
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
MAPS = os.path.join(ROOT, "maps")
OUT = os.path.join(ROOT, "lidar-share")
GAMES = (("h2a_", "Halo 2 Anniversary"), ("h2_", "Halo 2"), ("h3_", "Halo 3"), ("odst_", "Halo 3: ODST"),
         ("reach_", "Halo: Reach"), ("h4_", "Halo 4"))
SLUGS = {"Halo: CE": "halo-ce", "Halo 2": "halo-2", "Halo 2 Anniversary": "halo-2-anniversary", "Halo 3": "halo-3",
         "Halo 3: ODST": "halo-3-odst", "Halo: Reach": "halo-reach", "Halo 4": "halo-4"}
LIMITS = {"deaths": 3000, "jumps": 2000}          # tools/lidar_saver.py merge_save keeps the same tails
MEMBER_MAX = 64 << 20                            # bytes: a scan in a zip larger than this is skipped (launcher's cap)
# private data a scan must never carry (make_release's own scan is a developer tool, not in a player's install: export
# there failed on its import, 0.2.2 builds 0929 / 1306)
PRIVATE = (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}",                       # an e-mail address
           r"(?i)[A-Z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+",                           # a user folder
           r"(?i)(?<![0-9a-f.])(?:0x)?0009[0-9a-f]{12}(?![0-9a-f])")                # an Xbox user id


def game_of(name):
    return next((g for p, g in GAMES if name.startswith(p)), "Halo: CE")


def scans():
    return sorted(d for d in os.listdir(MAPS) if os.path.exists(os.path.join(MAPS, d, "lidar.json")))


PRIVATE_WHAT = ("an e-mail address", "a user folder", "an Xbox user id")


def private(text, root=None):
    """What private a scan's text holds ([] when nothing), as descriptions, never the private words themselves: the
    patterns above, and (custom, Nov 24) our installer's own privacy scan (tools/privacy.py, as build_installer's
    privacy_scan): this PC's profile path and user name, and the owner's personal terms in .private_terms."""
    found = [what for what, p in zip(PRIVATE_WHAT, PRIVATE) if re.search(p, text)]
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import privacy
    user, word = privacy.user_word()
    got = privacy.hits(text, privacy.load_terms(root or ROOT), user, word)
    if word is not None and user in got:
        found.append("this PC's user name")
    if any(t != user for t in got):
        found.append("a personal term or this PC's profile path")
    return found


def _scan(name):
    """(manifest, text) of a map's scan, privacy-checked."""
    src = os.path.join(MAPS, name, "lidar.json")
    if not os.path.exists(src):
        raise SystemExit(f"no LiDAR scan of {name} on this PC (play it, or run the LiDAR Simulator on it first)")
    text = open(src, encoding="utf-8").read()
    hit = private(text)
    if hit:
        raise SystemExit(f"{name}: the scan holds something private ({hit}); not exported")
    d = json.loads(text)
    b = os.path.join(ROOT, "BUILD")
    manifest = dict(map=name, game=game_of(name), build=open(b, encoding="utf-8").read().strip() if os.path.exists(b) else "",
                    made=time.strftime("%Y-%m-%d"), human_minutes=d.get("human_minutes", 0),
                    bot_minutes=d.get("bot_minutes", 0),
                    counts={k: len(v) for k, v in d.items() if isinstance(v, (list, dict))})
    return manifest, text


def export(name, out=OUT):
    """The zip's path. Refuses a map with no scan, or a scan holding something private."""
    manifest, text = _scan(name)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{name}_{manifest['made']}.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=1))
        z.writestr("lidar.json", text)
    return path


def bundle(slug, out=OUT, kind="author"):
    """Every scan of one game in one zip: (path, maps)."""
    game = next((g for g, s in SLUGS.items() if s == slug), None)
    if game is None:
        raise SystemExit(f"{slug}: not a game (one of {', '.join(SLUGS.values())})")
    names = [d for d in scans() if game_of(d) == game]
    if not names:
        raise SystemExit(f"no {game} scans on this PC")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"lidar-maps-{slug}.zip")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            manifest, text = _scan(n)
            z.writestr(f"{n}/manifest.json", json.dumps(manifest, indent=1))
            z.writestr(f"{n}/lidar.json", text)
        z.writestr("bundle.json", json.dumps(dict(game=game, slug=slug, kind=kind, maps=names,
                                                  made=time.strftime("%Y-%m-%d")), indent=1))
    return path, names


# (upstream 0.3.0, build 20261112-1342) import: _key, _join, merge, _ok_name, _import_one, import_any, import_zip,
# summary; with our link filter and match check (custom, Nov 24)
def _key(x):
    return json.dumps(x, sort_keys=True)


def _join(a, b):
    """a then the items of b not already in a (exact duplicates only)."""
    seen = {_key(x) for x in a}
    return a + [x for x in b if _key(x) not in seen and not seen.add(_key(x))]


def _saved_link(link):
    """(custom, Nov 24) Our own save's rule for a link (tools/lidar.py saved_link)."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    from lidar import saved_link
    return isinstance(link, dict) and saved_link(link)


def merge(mine, theirs):
    """Their scan joined into mine (a new dict). Floors: counts added per cell (cell, height step, kind); deaths and jump
    heights appended to the scan's limits; links, teleports, cover, weapons, holds and objectives joined. (custom,
    Nov 24) Their links are filtered first as our save filters ours (_saved_link)."""
    if not isinstance(theirs, dict):
        raise SystemExit("the shared scan is not a LiDAR scan")
    if (mine.get("cell"), mine.get("zstep")) != (theirs.get("cell"), theirs.get("zstep")) and mine:
        raise SystemExit("the shared scan uses another grid (cell / height step): made by a different version")
    if "links" in theirs:
        theirs = dict(theirs, links=[x for x in theirs["links"] if _saved_link(x)])
    walk = {}
    for w in mine.get("walk", []) + theirs.get("walk", []):
        k = tuple(w[:3]) + ((w[3],) if len(w) == 5 else (0,))     # (an old scan's cell has no kind: a bot's, 0, as lidar.py)
        walk[k] = walk.get(k, 0) + w[-1]
    out = dict(mine)
    out.update(cell=theirs.get("cell", mine.get("cell")), zstep=theirs.get("zstep", mine.get("zstep")),
               runs=mine.get("runs", 0) + theirs.get("runs", 0),
               bot_minutes=round(mine.get("bot_minutes", 0) + theirs.get("bot_minutes", 0), 1),
               human_minutes=round(mine.get("human_minutes", 0) + theirs.get("human_minutes", 0), 1),
               walk=[[*k, n] for k, n in sorted(walk.items())])
    for k, cap in LIMITS.items():
        out[k] = (mine.get(k, []) + theirs.get(k, []))[-cap:]
    for k in ("links", "teleports", "cover", "weapons", "objectives"):
        if k in mine or k in theirs:
            out[k] = _join(mine.get(k, []), theirs.get(k, []))
    if "holds" in mine or "holds" in theirs:
        holds = dict(mine.get("holds", {}))
        for h, v in theirs.get("holds", {}).items():
            holds[h] = _join(holds.get(h, []), v) if isinstance(v, list) else holds.get(h, v)
        out["holds"] = holds
    return out


def _ok_name(name):
    return bool(name) and not any(c in name for c in "/\\:.") and os.path.isdir(os.path.join(MAPS, name))


def _import_one(name, text):
    """Merge one scan's text into maps/<name>: ("merged" | "already imported", links before, links after)."""
    sig = hashlib.sha1(text.encode()).hexdigest()
    seen_path = os.path.join(MAPS, name, "lidar_imported.json")
    seen = []
    if os.path.exists(seen_path):
        with open(seen_path, encoding="utf-8") as f:
            seen = json.load(f)
    dst = os.path.join(MAPS, name, "lidar.json")
    mine = {}
    if os.path.exists(dst):
        with open(dst, encoding="utf-8") as f:
            mine = json.load(f)
    if sig in seen:
        return "already imported", len(mine.get("links", [])), len(mine.get("links", []))
    out = merge(mine, json.loads(text))
    if mine:
        os.replace(dst, f"{dst}.before-import-{time.strftime('%Y%m%d-%H%M%S')}")
    tmp = dst + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    os.replace(tmp, dst)
    with open(seen_path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(seen + [sig], f)
    os.replace(seen_path + ".tmp", seen_path)
    return "merged", len(mine.get("links", [])), len(out.get("links", []))


def match_running():
    """(custom, Nov 24) The running match's {pid, map, t} (tools/match_lock.py), or None."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import match_lock
    return match_lock.running()


def import_any(path):
    """A map's zip or a game's bundle: [(map, result, links before, links after)]; maps this version lacks are
    reported as "not in this version" and skipped. Raises SystemExit on a zip that is neither, and (custom, Nov 24)
    while a match runs, before anything is read or written."""
    if match_running():
        raise SystemExit("a match is running: import after it ends (its LiDAR save rewrites the scans)")
    out = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if "bundle.json" in names:
            maps = json.loads(z.read("bundle.json")).get("maps", [])
            items = [(m, f"{m}/lidar.json") for m in maps if isinstance(m, str)]
        elif {"manifest.json", "lidar.json"} <= names:
            items = [(str(json.loads(z.read("manifest.json")).get("map", "")), "lidar.json")]
        else:
            raise SystemExit("not a LiDAR scan zip (no manifest.json / bundle.json)")
        for m, member in items:
            if not _ok_name(m) or member not in names or z.getinfo(member).file_size > MEMBER_MAX:
                out.append((m, "not in this version", 0, 0))
                continue
            out.append((m, *_import_one(m, z.read(member).decode("utf-8"))))
    return out


def import_zip(path):
    """One map's zip: (map, links before, links after) (kept for its callers); refuses a map this version lacks."""
    got = import_any(path)
    if len(got) != 1 or got[0][1] == "not in this version":
        raise SystemExit(f"{got[0][0] if got else '?'}: no such map in this version of the mod")
    return got[0][0], got[0][2], got[0][3]


def summary(got):
    merged = [m for m, r, *_ in got if r == "merged"]
    old = [m for m, r, *_ in got if r == "already imported"]
    missing = [m for m, r, *_ in got if r == "not in this version"]
    new_links = sum(b - a for _, r, a, b in got if r == "merged")
    if not merged:
        return ("Nothing new: " + (f"{len(old)} map{'s' if len(old) != 1 else ''} already imported" if old else
                                    "none of its maps are in this version")
                + (f", {len(missing)} not in this version" if old and missing else ""))
    return (f"{len(merged)} map{'s' if len(merged) != 1 else ''} added to your scans ({new_links} new jumps and rides)"
            + (f", {len(old)} already imported" if old else "") + (f", {len(missing)} not in this version" if missing else ""))


def main(argv):
    if not argv or argv[0] not in ("export", "bundle", "import", "list"):
        raise SystemExit(__doc__)
    if argv[0] == "list":
        for d in scans():
            print(f"{d:32} {game_of(d)}")
    elif argv[0] == "export" and len(argv) > 1:
        print("written", export(argv[1]))
    elif argv[0] == "bundle" and len(argv) > 1:
        path, names = bundle(argv[1])
        print(f"written {path}: {len(names)} maps")
    elif argv[0] == "import" and len(argv) > 1:
        print(summary(import_any(argv[1])))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
