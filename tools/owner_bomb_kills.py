"""(custom, Nov 17) The person's Banshee bomb kills in a match, and only those: the owner, "I did the banshee bomb and
boost like at the same time. Only record the ones where i got kills with the bomb".

Reads a match's trace (logs/trace_<map>_<stamp>.jsonl: its kill rows, tools/kill_record.py) and its collect file
(logs/collect_<map>_<stamp>.jsonl: everyone's place every tick, tools/collector.py), keeps each kill the person made
with the Banshee bomb (damage type 30, tools/service_record_site/weapons.json "reach"), and writes his flight over the
3 s before the bomb's hit: speed, height over the man, range, nose pitch, heading off him. No buttons are recorded
anywhere in a match (the collector reads none), so his boost is told by his speed.

usage: python -I tools/owner_bomb_kills.py logs/trace_<map>_<stamp>.jsonl [--out file.json]
       (the collect file is found by the same stamp; written to logs/owner_bomb_kills_<map>_<stamp>.json)
"""
import bisect
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kill_record  # noqa: E402

BOMB = 30                 # Reach's "Banshee bomb" damage type
GT = 60.0                 # Reach game ticks a second (the kill row's hit ages)
BEFORE = (3.0, 2.5, 2.0, 1.5, 1.2, 1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0)
RELEASE_BEFORE = 0.5      # s: the bomb's flight from about 10 u (20 u/s and the Banshee's own speed): his release


def read(trace, collect):
    kills, names = [], {}
    with open(trace, encoding="utf-8") as f:
        for line in f:
            if '"kill"' in line[:30]:
                d = json.loads(line)
                if isinstance(d.get("kill"), dict):
                    kills.append((d["t"], d["kill"]))
            elif '"meta"' in line[:30]:
                m = json.loads(line)["meta"].get("bot") or {}
                names[m.get("id")] = m.get("name")
    track = {}
    with open(collect, encoding="utf-8") as f:
        for line in f:
            if '"p"' not in line[:20]:
                continue
            d = json.loads(line)
            for p in d.get("p", []):
                track.setdefault(p[0], []).append((d["t"], p[3], p[4], p[5], p[6], p[7], p[10], p[12]))
    return kills, names, track


def bomb_kills(kills, names, track):
    people = [i for i, tr in track.items() if tr and tr[0][7] == 0]
    out = []
    for pid in people:
        tr = track[pid]
        ts = [r[0] for r in tr]

        def at(t):
            return tr[min(max(bisect.bisect_left(ts, t), 0), len(tr) - 1)]

        def speed(t, w=0.3):
            a, b = at(t - w), at(t)
            return math.dist(a[1:4], b[1:4]) / max(b[0] - a[0], 1e-3)
        for t, k in kills:
            r = kill_record.read(k)
            if not r or r[0] != "kill" or r[1] != pid or r[2] != BOMB:
                continue
            hit = next((h for h in k["hits"] if h[0] == pid and h[1] == BOMB), None)
            th = t - (hit[5] / GT if hit else 0.0)
            v = k["vp"]
            rows = []
            for dt in BEFORE:
                q = at(th - dt)
                rows.append(dict(before=dt, speed=round(speed(th - dt), 2), over=round(q[3] - v[2], 2),
                                 flat=round(math.hypot(q[1] - v[0], q[2] - v[1]), 2), pitch=q[5],
                                 off=round(math.remainder(math.atan2(v[1] - q[2], v[0] - q[1]) - q[4], math.tau), 3),
                                 riding=bool(q[6])))
            out.append(dict(t=round(t, 2), hit_t=round(th, 2), by=pid, victim=names.get(k["v"], k["v"]), at=v,
                            in_vehicle=bool(at(th)[6]), flight=rows))
    return out


def summary(found):
    def col(before, key):
        return [next(r[key] for r in k["flight"] if r["before"] == before) for k in found]
    rel = [math.hypot(f, o) for f, o in zip(col(RELEASE_BEFORE, "flat"), col(RELEASE_BEFORE, "over"))]
    lines = [f"{len(found)} bomb kills"]
    if not found:
        return "\n".join(lines)
    med = statistics.median
    lines += [
        f"range at release (~{RELEASE_BEFORE} s before the hit): median {med(rel):.1f} u, {min(rel):.1f}-{max(rel):.1f}",
        f"height over him at release: median {med(col(RELEASE_BEFORE, 'over')):.1f} u",
        f"nose pitch at release: median {med(col(RELEASE_BEFORE, 'pitch')):+.2f} rad, at the hit {med(col(0.0, 'pitch')):+.2f}",
        f"speed 1.5 s before: median {med(col(1.5, 'speed')):.1f} u/s; at release {med(col(RELEASE_BEFORE, 'speed')):.1f}; "
        f"0.2 s before the hit {med(col(0.2, 'speed')):.1f}",
        f"heading off him at release: median {med([abs(x) for x in col(RELEASE_BEFORE, 'off')]):.2f} rad",
    ]
    return "\n".join(lines)


def main(argv):
    trace = argv[0]
    collect = trace.replace("trace_", "collect_", 1)
    if not os.path.exists(collect):
        sys.exit(f"no collect file {collect}: turn the Data collector on for the match")
    out = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(
        os.path.dirname(trace), os.path.basename(trace).replace("trace_", "owner_bomb_kills_", 1).replace(".jsonl", ".json"))
    found = bomb_kills(*read(trace, collect))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dict(trace=os.path.basename(trace), kills=found), f, indent=1)
    print(summary(found))
    print("written", out)


if __name__ == "__main__":
    main(sys.argv[1:])
