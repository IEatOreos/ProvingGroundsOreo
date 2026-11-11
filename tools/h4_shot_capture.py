"""Halo 4 shot capture: where the person's shots start, which way they go and where they land, against where he aims
(read-only; custom, Nov 10: "the bots are shooting at spartans above their head so im doing a test to shoot straight
at a wall for you to record the height and angle of the ghost shots").

Each tick: the person (player 0 in a solo game): place, aim (unit +0x4E0), view point (+0xD50), what he rides (+0x24)
with its place and orientation; and every projectile (object type 5) with its place. A projectile is followed from the
tick it shows to the tick it is gone: its first place is where it left the gun, its last where it hit.

  python\\python.exe tools\\h4_shot_capture.py [--minutes 15]      until Ctrl+C, logs/h4_shot_capture_<stamp>/stop.txt
  python\\python.exe tools\\h4_shot_capture.py --summary logs\\h4_shot_capture_<stamp>

Summary, per vehicle (or on foot): each shot's start in the vehicle's frame (forward, left, up from its origin), its
flight's pitch and yaw against the aim at the tick it was fired, and where it landed against the aim line from the view
point (along it, and how far above / beside it). Nothing is written to the game.
"""
import argparse
import gzip
import json
import math
import os
import struct
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

HZ = 60.0
NONE = 0xFFFFFFFF
PROJECTILE = 5


def vec(b, off):
    return list(struct.unpack_from("<3f", b, off))


def frame(fwd, up):
    if not fwd or not up:
        return None
    f, u = fwd, up
    left = (u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0])
    n = math.sqrt(sum(c * c for c in left))
    if not 0.5 < n < 1.5:
        return None
    return f, tuple(c / n for c in left), u


def local(p, origin, fr):
    d = [p[i] - origin[i] for i in range(3)]
    return [round(sum(d[i] * axis[i] for i in range(3)), 4) for axis in fr]


def capture(out_dir, minutes):
    from brain.live import LiveH4F
    os.makedirs(out_dir, exist_ok=True)
    stop = os.path.join(out_dir, "stop.txt")
    live, start, n, last = None, time.monotonic(), 0, 0.0
    seen = set()
    print(f"capturing to {out_dir} (Ctrl+C, {stop} or {minutes} min to stop)", flush=True)
    with gzip.open(os.path.join(out_dir, "samples.jsonl.gz"), "wt", encoding="utf-8", compresslevel=1) as out:
        try:
            while time.monotonic() - start < minutes * 60 and not os.path.exists(stop):
                tick = time.monotonic()
                try:
                    if live is None:
                        live = LiveH4F()
                        print(f"attached: {live.map_name()}", flush=True)
                    ps = [p for p in live.players() if p.get("pos") is not None]
                    me = None
                    if ps:
                        p = ps[0]
                        a = live.object(p["unit"])
                        raw = live.g.read(a, 0xD5C) if a else None
                        me = dict(pos=list(p["pos"]), aim=list(p["aim"]) if p.get("aim") else None,
                                  view=vec(raw, 0xD50) if raw and len(raw) >= 0xD5C else None, veh=None)
                        if p["vehicle"] != -1:
                            vb = live.g.read(live.object(p["vehicle"]), 0x90)
                            me["veh"] = dict(handle=p["vehicle"], pos=vec(vb, 0x40),
                                             fwd=vec(vb, live.ORIENT_AT) if live.ORIENT_AT else None,
                                             up=vec(vb, live.ORIENT_AT + 12) if live.ORIENT_AT else None,
                                             name=live._names.get(struct.unpack_from("<I", vb, 0x8)[0], "unknown")
                                             if hasattr(live, "_names") else "unknown")
                    proj = [[h, round(pos[0], 4), round(pos[1], 4), round(pos[2], 4)]
                            for h, typ, name, pos in live.objects((PROJECTILE,))]
                    out.write(json.dumps(dict(t=round(tick - start, 4), me=me, proj=proj), separators=(",", ":")) + "\n")
                    n += 1
                    new = [q[0] for q in proj if q[0] not in seen]
                    seen.update(new)
                    if tick - last > 2.0:
                        last = tick
                        ride = me and me["veh"] and me["veh"]["name"]
                        print(f"{tick - start:6.1f}s  {'in ' + ride if ride else 'on foot'}  shots seen {len(seen)}  "
                              f"({len(proj)} in flight)", flush=True)
                    if n % 60 == 0:
                        out.flush()
                except Exception as e:      # the game not up, a map loading, a read racing the game
                    out.write(json.dumps(dict(t=round(time.monotonic() - start, 3), error=f"{type(e).__name__}: {e}")) + "\n")
                    live = None
                    time.sleep(1.0)
                    continue
                time.sleep(max(0.0, 1.0 / HZ - (time.monotonic() - tick)))
        except KeyboardInterrupt:
            pass
    print(f"done: {n} samples, {len(seen)} shots", flush=True)
    summary(out_dir)


def rows(path):
    with gzip.open(os.path.join(path, "samples.jsonl.gz"), "rt", encoding="utf-8") as f:
        try:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    return
                if "error" not in d:
                    yield d
        except EOFError:
            return


def shots(path):
    """Each projectile: its places over time, and the person's state the tick before it first showed (when fired)."""
    tracks, prev, out = {}, None, []
    for d in rows(path):
        here = {q[0]: q[1:] for q in d["proj"]}
        for h, p in here.items():
            if h not in tracks:
                tracks[h] = dict(fired=prev["me"] if prev else d["me"], at=d["me"], pts=[(d["t"], p)])
            else:
                tracks[h]["pts"].append((d["t"], p))
        for h in [h for h in tracks if h not in here]:
            out.append(tracks.pop(h))
        prev = d
    return out + list(tracks.values())


def angles(v):
    return math.degrees(math.atan2(v[1], v[0])), math.degrees(math.atan2(v[2], math.hypot(v[0], v[1])))


def summary(path):
    groups = {}
    for s in shots(path):
        me = s["fired"]
        if not me or not me.get("aim") or len(s["pts"]) < 3:
            continue
        p0, p1, pl = s["pts"][0][1], s["pts"][2][1], s["pts"][-1][1]
        d = [p1[i] - p0[i] for i in range(3)]
        if math.sqrt(sum(c * c for c in d)) < 0.05:
            continue                            # (still: a grenade lying, a mine)
        dt = s["pts"][2][0] - s["pts"][0][0]
        yaw_s, pitch_s = angles(d)
        yaw_a, pitch_a = angles(me["aim"])
        veh = me.get("veh")
        key = veh["name"] if veh else "on foot"
        g = groups.setdefault(key, [])
        r = dict(t=s["pts"][0][0], speed=round(math.dist(p0, p1) / dt, 1) if dt > 0 else None,
                 pitch_off=round(pitch_s - pitch_a, 2), yaw_off=round(((yaw_s - yaw_a + 180) % 360) - 180, 2),
                 aim_pitch=round(pitch_a, 2), flight=round(math.dist(p0, pl), 2), flew_s=round(s["pts"][-1][0] - s["pts"][0][0], 3))
        if veh:
            fr = frame(veh.get("fwd"), veh.get("up"))
            if fr:
                r["start_v"] = local(p0, veh["pos"], fr)
                r["view_v"] = local(me["view"], veh["pos"], fr) if me.get("view") else None
        o = me.get("view") or me["pos"]
        a = me["aim"]
        n = math.sqrt(sum(c * c for c in a))
        a = [c / n for c in a]
        rel = [pl[i] - o[i] for i in range(3)]
        along = sum(rel[i] * a[i] for i in range(3))
        perp = [rel[i] - a[i] * along for i in range(3)]
        r["land_along"] = round(along, 2)
        r["land_above"] = round(perp[2], 3)                  # (above the aim line at that distance; negative: below)
        r["land_aside"] = round(math.hypot(perp[0], perp[1]), 3)
        g.append(r)
    out = {}

    def st(vals):
        vals = sorted(v for v in vals if v is not None)
        if not vals:
            return None
        q = lambda f: vals[min(len(vals) - 1, int(f * len(vals)))]
        return [round(q(0.5), 3), round(q(0.1), 3), round(q(0.9), 3)]
    for key, g in groups.items():
        out[key] = dict(shots=len(g), speed=st([r["speed"] for r in g]), pitch_off=st([r["pitch_off"] for r in g]),
                        yaw_off=st([r["yaw_off"] for r in g]), land_above=st([r["land_above"] for r in g]),
                        land_along=st([r["land_along"] for r in g]),
                        start_v={ax: st([r["start_v"][i] for r in g if r.get("start_v")]) for i, ax in
                                 enumerate(("forward", "left", "up"))},
                        view_v={ax: st([r["view_v"][i] for r in g if r.get("view_v")]) for i, ax in
                                enumerate(("forward", "left", "up"))},
                        rows=g)
    with open(os.path.join(path, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    for key, g in out.items():
        print(f"{key}: {g['shots']} shots (median, p10, p90)")
        for k in ("speed", "pitch_off", "yaw_off", "land_along", "land_above", "start_v", "view_v"):
            print(f"   {k}: {g[k]}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--summary")
    ap.add_argument("--minutes", type=float, default=15.0)
    o = ap.parse_args()
    if o.summary:
        summary(o.summary)
        return
    capture(os.path.join(ROOT, "logs", time.strftime("h4_shot_capture_%Y%m%d-%H%M%S")), o.minutes)


if __name__ == "__main__":
    main()
