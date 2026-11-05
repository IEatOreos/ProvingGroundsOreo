"""Bots' sword and hammer attacks in a trace (issue #3 live check): per trigger press with a sword or hammer in hand, the
range to the man it fought, how far it moved toward him in the next 0.3 s against the same for its sword-in-hand rows
with no press (a lunge carries the body faster than a run: LUNGE_GAIN more counts as one) and whether he died within
0.6 s; melee presses with a sword (the clash follow-up) and with a hammer (should be
none); grenades thrown with either in hand (should be none). Game memory only (the trace's positions and the bots'
own commands).

usage: python -I lunge_check.py logs/trace_<map>_<stamp>.jsonl [...]
"""
import json
import math
import sys

LUNGE_GAIN = 0.4       # u in 0.3 s past the run's median (INFERRED: a lunge's speed is not measured yet)


def main(paths):
    for path in paths:
        bots, world = {}, []                       # id -> [(t, pos, wpn, buttons, target id, d)]; [(t, {id: (alive, pos)})]
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if "world" in r:
                world.append((r["t"], {w[0]: (w[2], w[3:6]) for w in r["world"]}))
            elif "id" in r and "cmd" in r and "pos" in r:
                att = r.get("att") or [None, None]
                bots.setdefault(r["id"], []).append((r["t"], r["pos"], r.get("wpn"), int(r["cmd"][3]),
                                                     att[1] if att[0] == "aim" else None, (r.get("fx") or {}).get("d")))
        def alive(pid, t):
            snap = next((w for tt, w in world if tt >= t), None)
            return None if snap is None or pid not in snap else snap[pid][0]
        rows = {"sword": [], "gravity_hammer": []}
        runs = {"sword": [], "gravity_hammer": []}
        melee = {"sword": 0, "gravity_hammer": 0}
        nades = 0
        for bid, rs in bots.items():
            for k, (t, pos, w, btn, tid, d) in enumerate(rs):
                if w not in rows:
                    continue
                prev = rs[k - 1][3] if k else 0
                melee[w] += bool(btn & 16 and not prev & 16)
                nades += bool(btn & 8 and not prev & 8)
                if not isinstance(tid, int) or d is None:
                    continue
                press = bool(btn & 1 and not prev & 1)
                if not press and not 1.5 < d < 4.0:
                    continue
                later = [q for tt, q, *_ in rs[k:] if tt - t <= 0.3]
                foe = next((ws[tid][1] for tt, ws in world if tt >= t and tid in ws), None)
                toward = 0.0
                if foe is not None and later:
                    ux, uy = foe[0] - pos[0], foe[1] - pos[1]
                    n = math.hypot(ux, uy) or 1.0
                    toward = max(((q[0] - pos[0]) * ux + (q[1] - pos[1]) * uy) / n for q in later)
                if not press:
                    runs[w].append(toward)
                    continue
                died = alive(tid, t) and alive(tid, t + 0.6) is False
                rows[w].append((d, toward, bool(died), t, bid, tid))
        print(path)
        for w, rs in rows.items():
            if not rs:
                continue
            rs.sort()
            ds = [r[0] for r in rs]
            run = sorted(runs[w])[len(runs[w]) // 2] if runs[w] else 0.0
            gain = sorted(r[1] for r in rs)[len(rs) // 2]
            lk = [r for r in rs if r[1] >= run + LUNGE_GAIN and r[2]]
            print(f"  {w}: {len(rs)} presses, range median {ds[len(ds) // 2]:.2f} u (max {ds[-1]:.2f}), toward him in "
                  f"0.3 s median {gain:.2f} u (running {run:.2f}), lunged {sum(r[1] >= run + LUNGE_GAIN for r in rs)}, "
                  f"kills within 0.6 s {sum(r[2] for r in rs)}, lunge kills {len(lk)}")
            for d, g, _, t, b, v in lk[:3]:
                print(f"    lunge kill: {t:.2f} s bot {b} -> {v} from {d:.2f} u, {g:.2f} u toward him in 0.3 s")
        print(f"  melee presses: sword {melee['sword']} (clash follow-ups), hammer {melee['gravity_hammer']} (want 0); "
              f"grenades with either in hand {nades} (want 0)")


if __name__ == "__main__":
    main(sys.argv[1:])
