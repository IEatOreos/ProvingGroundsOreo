"""Halo 4 vehicle seat capture: where a seated Spartan's head, view and bones are, seat by seat (read-only).

Why: brain/live.py h4_spartan_pose reads the animated head and the view point only on foot, so Halo 4 Demon's aim
(brain/bot.py h4_demon_fire) cannot aim at a man in a Warthog or a Mongoose. This records the seated poses to validate
that read in each seat and to learn which parts of a rider show from where. Nothing is sent to the game and no game
memory is written; it can run beside the bot brain.

How (the owner, a solo Halo 4 custom game on a map with a Warthog and a Mongoose, bots optional):
  python\\python.exe tools\\h4_seat_capture.py          start before or after loading in; the capture runs until
                                                       Ctrl+C, logs/h4_seat_capture_<stamp>/stop.txt or --minutes
  Sit about 30-60 s in each seat: driver, passenger, gunner (Warthog), driver and passenger (Mongoose). In each: still,
  then look around, then drive or steer (the gunner turns the turret all the way round). The console line names the
  seat it sees; get out on foot between seats for a few seconds.
  python\\python.exe tools\\h4_seat_capture.py --summary logs\\h4_seat_capture_<stamp>
                                                       per vehicle and seat: the head and view in the vehicle's frame,
                                                       their spread, and which on-foot reader guards a seated pose fails

Output (local, gitignored logs/): samples.jsonl.gz (one row a tick, the full 120-node bone block every BONES_EVERY
ticks), status.json while it runs, summary.json at the end.
"""
import argparse
import base64
import collections
import gzip
import json
import math
import os
import struct
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

HZ = 30.0
BONES_EVERY = 6              # ticks between full bone-block copies (about 5 a second)
NODES, NODE_SIZE, HEAD_NODE = 120, 52, 54
HEAD_MARKER = (-6.9422384e-8, 0.02300628, -0.006868857)   # target_head on node 54 (brain/live.py h4_spartan_pose)
NONE = 0xFFFFFFFF


def vec(b, off):
    return list(struct.unpack_from("<3f", b, off))


def head_from(offset, raw):
    """The target_head marker from a unit's bone block (no guards); (head, scale, axes ok) or None."""
    start = offset + HEAD_NODE * NODE_SIZE
    if start + NODE_SIZE > len(raw):
        return None
    scale, *m = struct.unpack_from("<13f", raw, start)
    if not all(map(math.isfinite, (scale, *m))):
        return None
    axes = [m[k:k + 3] for k in (0, 3, 6)]
    ortho = all(abs(sum(x * y for x, y in zip(a, b)) - float(i == j)) <= 0.08
                for i, a in enumerate(axes) for j, b in enumerate(axes))
    head = [m[9 + i] + scale * sum(HEAD_MARKER[j] * m[j * 3 + i] for j in range(3)) for i in range(3)]
    return head, scale, ortho


def frame(fwd, up):
    """(forward, left, up) unit vectors of a vehicle from its forward and up reads, or None."""
    if not fwd or not up:
        return None
    f = fwd
    u = up
    left = (u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0])
    n = math.sqrt(sum(c * c for c in left))
    if not 0.5 < n < 1.5:
        return None
    return f, tuple(c / n for c in left), u


def local(p, origin, fr):
    """p in the vehicle frame: (forward, left, up) from its origin."""
    d = [p[i] - origin[i] for i in range(3)]
    return [round(sum(d[i] * axis[i] for i in range(3)), 4) for axis in fr]


def guards(head, view, base, pos):
    """Which of h4_spartan_pose's on-foot checks a pose fails (its order, brain/live.py)."""
    out = []
    if math.hypot(head[0] - pos[0], head[1] - pos[1]) > 0.8:
        out.append("head xy over 0.8 from place")
    if not -0.2 < head[2] - pos[2] < 1.05:
        out.append("head z off place")
    if math.hypot(view[0] - base[0], view[1] - base[1]) > 0.2:
        out.append("view xy over 0.2 from base")
    if not 0.3 < view[2] - base[2] < 0.8:
        out.append("view z off base")
    if sum((view[k] - pos[k]) ** 2 for k in range(3)) > 1.0:
        out.append("view over 1 from place")
    if sum((view[k] - head[k]) ** 2 for k in range(3)) > 0.25:
        out.append("view over 0.5 from head")
    return out


class Capture:
    def __init__(s, out_dir, everyone=False, live=None):
        if live is None:
            from brain.live import LiveH4F
            s.Live = LiveH4F
        s.live = live                # (a test passes a stand-in reader)
        s.dir = out_dir
        s.everyone = everyone
        s.names = {}
        s.count = 0
        s.seat_counts = collections.Counter()

    def read(s, live, handle, n):
        a = live.object(handle) if handle not in (None, NONE, -1) else None
        if not a:
            return None, None
        b = live.g.read(a, n)
        return a, b

    def vehicle_info(s, live, handle, depth=2):
        """[name, handle, pos, fwd, up, parent handle] up the parent chain (a Warthog's chaingun rides the Warthog)."""
        out = []
        while handle not in (None, NONE, -1) and depth > 0:
            a, b = s.read(live, handle, 0x90)
            if not b or len(b) < 0x88:
                break
            parent = struct.unpack_from("<I", b, live.PARENT_AT)[0]
            fwd, up = (vec(b, live.ORIENT_AT), vec(b, live.ORIENT_AT + 12)) if live.ORIENT_AT else (None, None)
            out.append(dict(name=s.names.get(handle, "unknown"), handle=handle, pos=vec(b, 0x40), fwd=fwd, up=up,
                            parent=None if parent == NONE else parent))
            handle, depth = (None if parent == NONE else parent), depth - 1
        return out

    def row(s, live, p, bones):
        unit = p["unit"]
        a, head_b = s.read(live, unit, 0x1C0)
        if not head_b or len(head_b) < 0x1C0:
            return None
        size, offset = struct.unpack_from("<HH", head_b, 0x1BC)
        n = max(0xD60, offset + NODES * NODE_SIZE + 4) if size == NODES * NODE_SIZE and 0x700 <= offset <= 0x8000 else 0xD60
        raw = live.g.read(a, n)
        if not raw or len(raw) < 0xD5C:
            return None
        pos, base, view = vec(raw, 0x40), vec(raw, 0x64), vec(raw, 0xD50)
        seat = struct.unpack_from("<h", raw, 0x2C)[0]
        parent = struct.unpack_from("<I", raw, live.PARENT_AT)[0]
        r = dict(id=p["index"], name=p["name"], pos=pos, base=base, view=view, seat=seat,
                 parent=None if parent == NONE else parent, aim=p.get("aim"), sh=p.get("shield"), hp=p.get("health"),
                 node_block=[size, offset])
        hd = head_from(offset, raw) if size == NODES * NODE_SIZE else None
        if hd:
            r["head"], r["scale"], r["ortho"] = [round(c, 5) for c in hd[0]], round(hd[1], 4), hd[2]
            r["fails"] = guards(hd[0], view, base, pos)
        reader = live.h4_spartan_pose(a, raw[:0x668] if len(raw) >= 0x668 else raw, pos)
        r["reader_ok"] = reader[0] is not None
        if r["parent"] is not None:
            chain = s.vehicle_info(live, r["parent"])
            r["ride"] = chain
            top = chain[-1] if chain else None
            if top:
                fr = frame(top["fwd"], top["up"])
                if fr:
                    r["frame_of"] = top["name"]
                    for k in ("head", "view", "pos", "base"):
                        if r.get(k) is not None:
                            r[k + "_v"] = local(r[k], top["pos"], fr)
        if bones and size == NODES * NODE_SIZE and offset + NODES * NODE_SIZE <= len(raw):
            r["bones"] = base64.b64encode(raw[offset:offset + NODES * NODE_SIZE]).decode()
        return r

    def seat_label(s, r):
        if r.get("parent") is None:
            return "on foot"
        chain = r.get("ride") or []
        names = " on ".join(c["name"] for c in chain) or "unknown"
        return f"seat {r['seat']} in {names}"

    def run(s, minutes):
        os.makedirs(s.dir, exist_ok=True)
        stop = os.path.join(s.dir, "stop.txt")
        start = time.monotonic()
        last_print = 0.0
        print(f"capturing to {s.dir} (Ctrl+C, {stop} or {minutes} min to stop)", flush=True)
        with gzip.open(os.path.join(s.dir, "samples.jsonl.gz"), "wt", encoding="utf-8", compresslevel=1) as out:
            while time.monotonic() - start < minutes * 60 and not os.path.exists(stop):
                tick = time.monotonic()
                try:
                    if s.live is None:
                        s.live = s.Live()
                        print(f"attached: {s.live.map_name()}", flush=True)
                    live = s.live
                    for h, typ, name, _ in live.objects(live.VEHICLE_TYPES):
                        s.names[h] = name
                    players = [p for p in live.players() if p.get("pos") is not None]
                    if not players:
                        time.sleep(0.2)
                        continue
                    people = players if s.everyone else players[:1]   # (solo: index 0 is the person)
                    bones = s.count % BONES_EVERY == 0
                    rows = [x for x in (s.row(live, p, bones) for p in people) if x]
                    out.write(json.dumps(dict(t=round(tick - start, 3), map=live.map_name(), rows=rows),
                                         separators=(",", ":")) + "\n")
                    s.count += 1
                    if rows:
                        lab = s.seat_label(rows[0])
                        s.seat_counts[lab] += 1
                        if tick - last_print > 1.0:
                            last_print = tick
                            r = rows[0]
                            hv = r.get("head_v") or r.get("head")
                            print(f"{tick - start:6.1f}s  {lab:42s} samples {s.seat_counts[lab]:5d}  head "
                                  f"{[round(c, 2) for c in hv] if hv else None}  reader {'ok' if r['reader_ok'] else 'refuses'}"
                                  f"{'  fails: ' + ', '.join(r.get('fails', [])) if r.get('fails') else ''}", flush=True)
                            with open(os.path.join(s.dir, "status.json"), "w", encoding="utf-8") as f:
                                json.dump(dict(elapsed=round(tick - start, 1), samples=s.count, seats=dict(s.seat_counts)), f,
                                          indent=1)
                    if s.count % 30 == 0:
                        out.flush()
                except KeyboardInterrupt:
                    break
                except Exception as e:      # the game not up yet, a map loading, a read racing the game
                    out.write(json.dumps(dict(t=round(time.monotonic() - start, 3), error=f"{type(e).__name__}: {e}")) + "\n")
                    s.live = None
                    time.sleep(1.0)
                    continue
                time.sleep(max(0.0, 1.0 / HZ - (time.monotonic() - tick)))
        print(f"done: {s.count} samples; by seat {dict(s.seat_counts)}", flush=True)
        summary(s.dir)


def summary(path):
    """Per (vehicle chain, seat): samples, the head and view in the vehicle frame (median, p10-p90), head minus view,
    the on-foot reader's acceptance and which guards a seated pose fails."""
    groups = collections.defaultdict(list)
    with gzip.open(os.path.join(path, "samples.jsonl.gz"), "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            for r in d.get("rows", []):
                key = "on foot" if r.get("parent") is None else (
                    " on ".join(c["name"] for c in r.get("ride") or []) + f" seat {r['seat']}")
                groups[key].append(r)

    def stats(vals):
        vals = sorted(vals)
        if not vals:
            return None
        q = lambda p: vals[min(len(vals) - 1, int(p * len(vals)))]
        return [round(q(0.5), 3), round(q(0.1), 3), round(q(0.9), 3)]

    out = {}
    for key, rows in sorted(groups.items()):
        g = dict(samples=len(rows), reader_ok=round(sum(r["reader_ok"] for r in rows) / len(rows), 3))
        for k in ("head_v", "view_v"):
            v = [r[k] for r in rows if r.get(k)]
            if v:
                g[k] = {axis: stats([x[i] for x in v]) for i, axis in enumerate(("forward", "left", "up"))}
        hv = [[r["head"][i] - r["view"][i] for i in range(3)] for r in rows if r.get("head")]
        if hv:
            g["head_minus_view"] = {axis: stats([x[i] for x in hv]) for i, axis in enumerate(("x", "y", "z"))}
        fails = collections.Counter(x for r in rows for x in r.get("fails", []))
        g["guard_fails"] = {k: round(v / len(rows), 3) for k, v in fails.most_common()}
        g["bone_blocks"] = sum(1 for r in rows if r.get("bones"))
        out[key] = g
    with open(os.path.join(path, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    for key, g in out.items():
        print(f"{key}: {g['samples']} samples, on-foot reader accepts {100 * g['reader_ok']:.0f}%")
        for k in ("head_v", "view_v"):
            if k in g:
                print(f"   {k[:-2]:5s} in the vehicle frame (median, p10, p90): " +
                      ", ".join(f"{a} {v}" for a, v in g[k].items()))
        if g["guard_fails"]:
            print("   guards failed:", g["guard_fails"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--summary", help="summarize a capture folder instead of capturing")
    ap.add_argument("--minutes", type=float, default=15.0, help="stop after this long (default 15)")
    ap.add_argument("--everyone", action="store_true", help="every player, not only the first (the person in a solo game)")
    a = ap.parse_args()
    if a.summary:
        summary(a.summary)
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    Capture(os.path.join(ROOT, "logs", f"h4_seat_capture_{stamp}"), everyone=a.everyone).run(a.minutes)


if __name__ == "__main__":
    main()
