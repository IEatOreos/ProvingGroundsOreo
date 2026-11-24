"""Which vehicles Reach Invasion spawns for each side, and from which phase: maps/<map>/inv_vehicles.json from the map's
scenario (maps/<map>/source/scenario.xml, the editing kit's export). Invasion's own vehicles carry the megalo label
"inv_vehicle", an owner team (attacker / defender) and a spawn order (the phase they first appear in: order 2 = phases 2
and 3; seen live on Spire, the River Warthog from phase 2, the Falcon and the defenders' Banshee from phase 3). None
spawn in phase 1 on the three built-in maps. A custom map variant's come from its own labels (brain/invasion.py layout).

usage: python -I tools/inv_vehicles.py [map ...]     (default: every map with a source/scenario.xml and inv_ labels)

(upstream 0.3.0, build 20261118-1714) The files it writes are game-derived (from the editing kit's scenario export) and
stay on this PC: maps/*/inv_vehicles.json is in .gitignore and never committed.
"""
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FIELDS = ("type", "position", "megalo label", "owner team", "spawn order")


def read(path):
    """[dict(kind, pos, side "att" / "def", phase)] for the inv_vehicle objects in a scenario.xml."""
    out, cur = [], None

    def done(c):
        if c and c.get("type") == "vehicle" and c.get("megalo label") == "inv_vehicle":
            side = {"attacker": "att", "defender": "def"}.get(c.get("owner team"))
            order = int(c.get("spawn order") or 0)
            pos = [round(float(v), 3) for v in c["position"].split(",")]
            out.append(dict(kind=c["name"], pos=pos, side=side, phase=order if order in (1, 2, 3) else 1))

    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r'\s*<element index="\d+" name="\s*([^"]*)">', line)
        if m:
            done(cur)
            cur = {"name": m.group(1).strip()}
            continue
        f = re.match(r'\s*<field name="([^"]+)" value="([^"]*)"', line)
        if f and cur is not None and f.group(1) in FIELDS:
            if f.group(1) == "type":
                cur["type"] = f.group(2)        # (the object's own type field comes last: vehicle)
            else:
                cur.setdefault(f.group(1), f.group(2))
    done(cur)
    return out


def main(names):
    maps = os.path.join(ROOT, "maps")
    names = names or [m for m in sorted(os.listdir(maps)) if os.path.exists(os.path.join(maps, m, "inv_spawns.json"))]
    for m in names:
        src = os.path.join(maps, m, "source", "scenario.xml")
        if not os.path.exists(src):
            print(f"{m}: no source/scenario.xml")
            continue
        v = read(src)
        if not v:
            print(f"{m}: no Invasion vehicles")
            continue
        json.dump(dict(note="tools/inv_vehicles.py: Invasion's own vehicles (inv_vehicle), side and first phase",
                       vehicles=v), open(os.path.join(maps, m, "inv_vehicles.json"), "w", encoding="utf-8"), indent=1)
        print(f"{m}: " + ", ".join(f"{x['side']} {x['kind']} p{x['phase']}+" for x in v))


if __name__ == "__main__":
    main(sys.argv[1:])
