"""Reach shot capture: where the person's shots start, which way they go and where they land, against where he aims
(read-only; custom, Nov 15: the owner's Ghost test on Reach, "shooting the ghost at ground level", as
tools/h4_shot_capture.py did for Halo 4's Ghost on Grind).

Each tick: the person (player 0 in a solo game): place (unit +0x44), aim (unit +0x208, as LiveReach.players reads it),
what he rides (+0x14) with its place (+0x44), forward (+0x50) and up (+0x5C, assumed after the forward as in Halo 3);
and every projectile (object type 5) with its place. Reach's view point is not decoded, so the aim line runs from his
seated unit's place. The summary is h4_shot_capture's (per vehicle: each shot's start in the vehicle's frame, its
flight's pitch and yaw against the aim, where it landed against the aim line). Nothing is written to the game.

  python\\python.exe tools\\reach_shot_capture.py [--minutes 15]      until Ctrl+C, logs/reach_shot_capture_<stamp>/stop.txt
  python\\python.exe tools\\reach_shot_capture.py --summary logs\\reach_shot_capture_<stamp>
"""
import argparse
import gzip
import json
import os
import struct
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from h4_shot_capture import HZ, PROJECTILE, summary, vec   # noqa: E402

VEHICLE = 1


def capture(out_dir, minutes):
    from brain.live import LiveReach
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
                        live = LiveReach()
                        print(f"attached: {live.map_name()}", flush=True)
                    objs = live.objects((VEHICLE, PROJECTILE))       # (vehicles too: their names are learned so)
                    ps = [p for p in live.players() if p.get("pos") is not None]
                    me = None
                    if ps:
                        p = ps[0]
                        me = dict(pos=list(p["pos"]), aim=list(p["aim"]) if p.get("aim") else None, view=None, veh=None)
                        if p["vehicle"] != -1:
                            vb = live.g.read(live.object(p["vehicle"]), 0x68)
                            me["veh"] = dict(handle=p["vehicle"], pos=vec(vb, 0x44), fwd=vec(vb, 0x50), up=vec(vb, 0x5C),
                                             name=live._names.get(struct.unpack_from("<I", vb, 0)[0], "unknown"))
                    proj = [[h, round(pos[0], 4), round(pos[1], 4), round(pos[2], 4)]
                            for h, typ, name, pos in objs if typ == PROJECTILE]
                    out.write(json.dumps(dict(t=round(tick - start, 4), me=me, proj=proj), separators=(",", ":")) + "\n")
                    n += 1
                    seen.update(q[0] for q in proj)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--summary")
    ap.add_argument("--minutes", type=float, default=15.0)
    o = ap.parse_args()
    if o.summary:
        summary(o.summary)
        return
    capture(os.path.join(ROOT, "logs", time.strftime("reach_shot_capture_%Y%m%d-%H%M%S")), o.minutes)


if __name__ == "__main__":
    main()
