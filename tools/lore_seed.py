"""(custom, Nov 19) File this PC's old match recordings into each layout's map memory (brain/lore.py, maps/<layout>/
lore.json): every credited kill's two places (tools/kill_record.py rows, Reach since Nov 15) and every respawn (the
world lines: dead, then alive; his place a world line on). A recording already filed (its stamp in the memory, the
live match's too) is skipped, so this can be run again any time. Forge World recordings with no layout named (before
Nov 18) are skipped: which layout they were on is not known.

    python\\python.exe tools\\lore_seed.py              file every logs\\trace_*.jsonl
    python\\python.exe tools\\lore_seed.py --dry        count only, write nothing
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "tools")]
from brain import lore  # noqa: E402
import kill_record  # noqa: E402

FORGE = ("reach_forge_halo", "h4_ca_forge_ravine", "h4_forge_erosion", "h4_forge_impact")


def read_trace(path):
    """(layout, kills [(vp, kp)] or None when it recorded none, spawns [(mode, pos, team)]) of one recording; layout
    None: not one to file."""
    layout, kills, spawns, has_kills = None, [], [], False
    alive, back = {}, {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if layout is None and '"meta"' in line:
                try:
                    m = json.loads(line)["meta"]
                except (ValueError, KeyError):
                    continue
                layout = m.get("variant") or m.get("map")
                if not m.get("variant") and layout in FORGE:
                    return None, [], []
            elif '"kill_record"' in line:
                has_kills = True
            elif '"kill": {' in line:
                try:
                    row = json.loads(line)["kill"]
                except (ValueError, KeyError):
                    continue
                said = kill_record.read(row)
                if said is not None and said[0] == "kill" and row.get("kp") is not None:
                    kills.append((row["vp"], row["kp"]))
            elif '"world": [' in line:
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                for r in o.get("world") or []:
                    i, up = r[0], bool(r[2])
                    if i in back and up:
                        del back[i]
                        spawns.append((o.get("mode"), (r[3], r[4], r[5]), r[1]))
                    if up and alive.get(i) is False:
                        back[i] = True              # (his place on the next world line, 0.25 s on)
                    elif not up:
                        back.pop(i, None)
                    alive[i] = up
    return layout, (kills if has_kills else None), spawns


def main():
    dry = "--dry" in sys.argv
    books, total = {}, {}
    for path in sorted(glob.glob(os.path.join(ROOT, "logs", "trace_*.jsonl"))):
        st = re.search(r"_(\d{8}-\d{6})\.jsonl$", path)
        if not st:
            continue
        layout, kills, spawns = read_trace(path)
        if layout is None or not os.path.isdir(lore.folder_of(layout)):
            print(f"skip {os.path.basename(path)}: {'no layout' if layout is None else 'no map folder ' + layout}")
            continue
        b = books.setdefault(layout, lore.book(layout))
        if st.group(1) in b.matches:
            print(f"skip {os.path.basename(path)}: filed already")
            continue
        if kills is not None and not dry:
            b.kill_match(st.group(1))
        kills = kills or []
        if not dry:
            b.match(st.group(1))
            for vp, kp in kills:
                b.add_kill(vp, kp)
            for mode, p, team in spawns:
                b.add_spawn(mode, p, team)
        t = total.setdefault(layout, [0, 0, 0])
        t[0], t[1], t[2] = t[0] + 1, t[1] + len(kills), t[2] + len(spawns)
        print(f"{os.path.basename(path)}: {layout} {len(kills)} kills, {len(spawns)} respawns", flush=True)
    for layout, b in books.items():
        if not dry:
            b.save()
        n, k, sp = total.get(layout, [0, 0, 0])
        print(f"{layout}: +{n} matches (now {len(b.matches)}, {len(b.kill_matches)} with kills"
              f"{', danger trusted' if b.trusted() else ''}), +{k} kills, "
              f"+{sp} respawns; lanes {len(b.lanes())}")


if __name__ == "__main__":
    main()
