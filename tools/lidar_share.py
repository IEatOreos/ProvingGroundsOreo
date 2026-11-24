r"""Share LiDAR map scans between players (GitHub #19; the repository's lidar-maps/ folder keeps them by game).

(custom, Nov 24) Upstream 0.3.0's tools/lidar_share.py (build 20261123-0037), its export, bundle and list only. The
owner: "Yes, export only". Upstream's import and fetch (merging a shared zip into this PC's scans, downloading the
author's bundles) are not here: they wait for the "LiDAR scans in the launcher" item.

export: one map's scan (maps/<map>/lidar.json: the floor walked, the jumps people landed, lifts, teleporters, cover,
        weapons) into a small zip, lidar-share/<map>_<date>.zip beside the mod, with a manifest (map, game, build,
        what is in it). Nothing about the player goes in: no names (people are "human", bots "bot"), no folders, and
        the scan is checked for anything private before it is written (private(): e-mail addresses, user folders,
        Xbox ids, and our installer's privacy scan, tools/privacy.py: this PC's user name and profile path and the
        terms in .private_terms; what was found is named, the private words themselves never printed).
bundle: every scan of one game on this PC in one zip, lidar-maps-<game>.zip (bundle.json + <map>/manifest.json +
        <map>/lidar.json).

usage: python -I lidar_share.py export <map>           (e.g. h3_construct, reach_20_sword_slayer, beavercreek)
       python -I lidar_share.py bundle <game>          (halo-ce halo-2 halo-2-anniversary halo-3 halo-3-odst halo-reach
                                                         halo-4)
       python -I lidar_share.py list                   maps with a scan on this PC
"""
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


def main(argv):
    if not argv or argv[0] not in ("export", "bundle", "list"):
        raise SystemExit(__doc__)
    if argv[0] == "list":
        for d in scans():
            print(f"{d:32} {game_of(d)}")
    elif argv[0] == "export" and len(argv) > 1:
        print("written", export(argv[1]))
    elif argv[0] == "bundle" and len(argv) > 1:
        path, names = bundle(argv[1])
        print(f"written {path}: {len(names)} maps")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
