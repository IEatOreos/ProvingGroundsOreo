"""Where bot drivers wedge, learned from live match traces (Spire match 221404: three bots in two rounds pinned their
Warthogs at (-143.4, -352.7) and (-140.3, -353.5) with the throttle down, 70 half-seconds; the vehicle ground ran them
into a gap a Warthog does not fit through). A wedge: a bot at the wheel, under 1 u/s for half a second with the throttle
down; spots 1.5 u apart are merged; a spot counts once it held at least MIN_SAMPLES of them over at least two stops (two
bots, or one bot 20 s apart) and under half of them had another player or vehicle within BODY_R (a fight scrum).
Written to maps/<map>/wedges.json {"wedges": [[x, y, z, samples]]}, merged with what is
there; brain/maps.py terrain hands them to Terrain._build_vnav, which leaves the vehicle ground WEDGE_R round each one
(never the walking ground: a man fits through).

usage: python -I wedges.py <map> [trace ...]     (default: every logs/trace_<map>_*.jsonl)
       python -I wedges.py <map> --prune          only take out saved cells people have driven since
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
MIN_SAMPLES, MERGE, WEDGE_R = 6, 1.5, 2.5
BODY_R, BODY_SHARE, ABOARD_R = 3.0, 0.5, 1.6


def learn(paths, name):
    """Ground vehicles only (aircraft spool up and hover still: the Falcon at its River pad read as a wedge); never by a
    vehicle's spawn (3 u: boarding, waiting for crew) or by floor a person drove (1.5 u, the rides' people counts: it
    fits there; 2 u off the player's Warthog road on Spire otherwise)."""
    sys.path.insert(0, ROOT)
    from brain.vehicles import spec
    objs = json.load(open(os.path.join(ROOT, "maps", name, "objects.json"), encoding="utf-8"))
    pads = [v["pos"] for v in objs.get("vehicles", [])]
    people = driven(name)
    spots, kinds = [], {}                          # [x, y, z, samples, {stop keys}, body-blocked samples]
    for path in paths:
        last, stop, world = {}, {}, ((), ())
        for line in open(path, encoding="utf-8"):
            if '"world"' in line:
                w = json.loads(line)
                kinds.update({v[0]: v[1] for v in w.get("vehicles") or ()})
                world = ([(r[0], r[3:6]) for r in w.get("world") or () if r[2]],
                         [(v[0], v[2:5]) for v in w.get("vehicles") or ()])
                continue
            if '"seat": "driver"' not in line:
                continue
            d = json.loads(line)
            sp = spec(kinds.get(d.get("veh"), "")) or {}
            if sp.get("move") not in ("ground", "hover"):
                continue
            still = min(1.0, 0.15 * sp.get("speed", 10.0))   # (a crawling Elephant or tank is driving, not wedged)
            k, t, p = d["id"], d["t"], d["pos"]
            prev = last.get(k)
            if prev and t - prev[0] < 0.5:
                continue
            last[k] = (t, p)
            if not prev or t - prev[0] > 1.0 or abs(d["cmd"][0]) <= 0.3:
                continue
            if math.dist(p[:2], prev[1][:2]) / (t - prev[0]) >= still:
                continue
            if k not in stop or t - stop[k][1] > 20.0:
                stop[k] = (f"{os.path.basename(path)}#{k}@{round(t)}", t)
            stop[k] = (stop[k][0], t)
            body = blocked(k, d.get("veh"), p, world)
            s = next((s for s in spots if math.dist(s[:2], p[:2]) < MERGE and abs(s[2] - p[2]) < 1.5), None)
            if s is None:
                spots.append([p[0], p[1], p[2], 1, {stop[k][0]}, int(body)])
            else:
                s[3] += 1
                s[4].add(stop[k][0])
                s[5] += body
    # (a spot where half the samples or more had someone else beside the driver is a fight scrum, not scenery: Boneyard
    # 15 of 41 spots and Headlong 7 of 9, 2026-11-07, mostly in open middles a vehicle drives fine)
    found = [[round(x, 2), round(y, 2), round(z, 2), n] for x, y, z, n, stops, nb in spots if n >= MIN_SAMPLES
             and len(stops) >= 2 and nb < BODY_SHARE * n and not near((x, y, z), pads, 3.0)]
    # what the vehicle ground leaves: the floor round each spot (WEDGE_R, a half-unit lattice) no person drove. People
    # drove up to the Spire spot and turned west; the vehicle ground ran on south where nobody ever drove
    cells = sorted({(round(w[0] + dx * 0.5, 2), round(w[1] + dy * 0.5, 2), w[2]) for w in found
                    for dx in range(-5, 6) for dy in range(-5, 6) if math.hypot(dx * 0.5, dy * 0.5) <= WEDGE_R
                    and not near((w[0] + dx * 0.5, w[1] + dy * 0.5, w[2]), people, 0.75)})
    return found, [list(c) for c in cells]


def blocked(k, veh, p, world):
    """Another live player or another vehicle within BODY_R of the driver at the last world row: a stop against a body,
    not against the map. Who rides the driver's own vehicle (its gunner, within ABOARD_R of its middle; the world row
    holds no seat) is no block."""
    players, vehicles = world
    own = next((vp for h, vp in vehicles if h == veh), None)
    return any(pid != k and math.dist(pp[:2], p[:2]) < BODY_R and abs(pp[2] - p[2]) < 2.5
               and not (own is not None and math.dist(pp[:2], own[:2]) < ABOARD_R) for pid, pp in players) or \
        any(h != veh and math.dist(vp[:2], p[:2]) < BODY_R and abs(vp[2] - p[2]) < 2.5 for h, vp in vehicles)


def driven(name):
    """Where people drove on the map and its variants (rides.json "drive" rows with a person's count)."""
    return [r[:3] for f in glob.glob(os.path.join(ROOT, "maps", name, "**", "rides.json"), recursive=True)
            for r in json.load(open(f)).get("drive", []) if r[3] >= 1]


def near(p, pts, r):
    return any(math.dist(p[:2], q[:2]) < r and abs(p[2] - q[2]) < 1.5 for q in pts)


def prune(name):
    """Take out of a map's saved nodrive cells those people have driven over since (the live brain at each match's end,
    after its rides are saved: a cut a person drove through is no wall; the player's Spire matches drove over 53 and
    then 143 of them and tools/test_wedges.py failed on each). Returns how many came out."""
    path = os.path.join(ROOT, "maps", name, "wedges.json")
    if not os.path.exists(path):
        return 0
    old = json.load(open(path))
    cells = old.get("nodrive", [])
    people = driven(name)
    keep = [c for c in cells if not near(c, people, 0.75)]
    if len(keep) < len(cells):
        json.dump(dict(old, nodrive=keep), open(path, "w"), indent=1)
    return len(cells) - len(keep)


def keep_routes(name, found, cells, old_cells):
    """Each spot's cut kept only if every drive between the map's vehicle pads that arrived still arrives (Boneyard:
    the cut round (282.3, 93.4), 32 wedged half-seconds, also stopped the only drive from the east base's Scorpion
    pad to the north Ghost 23 u short). The vehicle ground is rebuilt per spot, the terrain built once."""
    sys.path.insert(0, ROOT)
    from brain.core import Vec
    from brain.maps import get_map, terrain
    from brain.vehicles import spec
    M = get_map(name)
    T = terrain(M)
    pads = [Vec(*v["pos"]) for v in M["objects"].get("vehicles", [])
            if (spec(v.get("item", "")) or {}).get("move") in ("ground", "hover")]
    pairs = [(a, b) for a in pads for b in pads if (a - b).flat() >= 15.0]

    def arrivals(nodrive):
        T.nodrive = nodrive
        T.__dict__.pop("graph_v", None)
        out = set()
        for k, (a, b) in enumerate(pairs):
            p = a
            for _ in range(60):
                q = T.vnav(p, b)
                if (q - p).flat() < 0.3:
                    break
                p = q
            if (p - b).flat() < 6.0:
                out.add(k)
        return out
    current = [list(c) for c in old_cells]
    base = arrivals(current)
    kept, dropped = [], []
    for w in sorted(found, key=lambda w: -w[3]):
        mine = [c for c in cells if math.dist(c[:2], w[:2]) <= WEDGE_R + 0.01 and abs(c[2] - w[2]) < 0.01]
        if base - arrivals(current + mine):
            dropped.append(w)
        else:
            kept.append(w)
            current += mine
    return kept, [c for c in cells if any(math.dist(c[:2], w[:2]) <= WEDGE_R + 0.01 for w in kept)], dropped


def main():
    args = [a for a in sys.argv[1:] if a != "--prune"]
    name = args[0]
    paths = args[1:] or sorted(glob.glob(os.path.join(ROOT, "logs", f"trace_{name}_*.jsonl")))
    path = os.path.join(ROOT, "maps", name, "wedges.json")
    if "--prune" in sys.argv:                     # only what people have driven since comes out; nothing new learned
        found, cells, paths = [], [], []
    else:
        found, cells = learn(paths, name)
        found, cells, dropped = keep_routes(name, found, cells,
                                            json.load(open(path)).get("nodrive", []) if os.path.exists(path) else [])
        if dropped:
            print(f"left out (their cut stopped a pad-to-pad drive that arrived): {dropped}")
    path = os.path.join(ROOT, "maps", name, "wedges.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    spots, nodrive = old.get("wedges", []), {tuple(c) for c in old.get("nodrive", [])}
    for w in found:                                # merged with what was learned before
        o = next((o for o in spots if math.dist(o[:2], w[:2]) < MERGE and abs(o[2] - w[2]) < 1.5), None)
        if o is None:
            spots.append(w)
        else:
            o[3] = max(o[3], w[3])
    nodrive |= {tuple(c) for c in cells}
    # (a cell saved before a person drove over it comes out: kept, it stood against his road, Spire, 4 cells)
    people = driven(name)
    nodrive = {c for c in nodrive if not near(c, people, 0.75)}
    json.dump(dict(wedges=spots, nodrive=sorted(list(c) for c in nodrive),
                   note="tools/wedges.py: bot drivers wedged at these spots in live matches; the vehicle ground leaves "
                        "the nodrive floor round them, which no person drove (brain/terrain.py _build_vnav)"),
              open(path, "w"), indent=1)
    print(name, f"{len(found)} wedge spots, {len(cells)} floor cells left out, from {len(paths)} traces ->",
          os.path.normpath(path), found)


if __name__ == "__main__":
    main()
