"""Vehicle boost capture: the person's raw input while he drives, to find the bits his boost sets (read-only; custom,
Nov 14: bot Ghosts and Banshees holding the boost went no faster than without it, ~5.5 u/s, while people's reached
9-15; the owner: "boosting on controller is my left trigger ... you have to hold it down").

Each tick: player 0's raw action (botcore copies it to shared memory, hb_shared dbg_action, the way the old decodes
read it) and where he is, with what he rides. botcore has to be loaded (the bots on, a match running).

  python\\python.exe tools\\boost_capture.py reach [--minutes 10]   until Ctrl+C, logs/boost_capture_<game>_<stamp>/stop.txt
  python\\python.exe tools\\boost_capture.py h4
  python\\python.exe tools\\boost_capture.py --summary logs\\boost_capture_<game>_<stamp>

The test: in a Ghost on open ground, drive straight at full throttle 3 s, then hold the boost (left trigger) 3 s, let
go 3 s, five or six times; the same in a Banshee if there is one. Summary, per vehicle: every action bit and float that
is on for part of the time, how long it was on, and his speed with it on and off; the boost's bits are the ones on in
the holds that ran fast. Nothing is written to the game.
"""
import argparse
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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HZ = 60.0
ACT_N = 0xC0                 # bytes of the action kept (Reach's 0xB0-ish, Halo 4's: the words decoded so far all under it)
FLOATS = (0x10, 0x14, 0x1C, 0x20, 0x38, 0x3C)   # yaw, pitch, throttle forward / left, trigger, second trigger / vertical


def capture(game, out_dir, minutes):
    import botctl
    from brain.live import LiveH4F, LiveReach
    os.makedirs(out_dir, exist_ok=True)
    stop = os.path.join(out_dir, "stop.txt")
    m = botctl.shm()
    live, start, n, last, seq0 = None, time.monotonic(), 0, 0.0, None
    print(f"capturing {game} to {out_dir} (Ctrl+C, {stop} or {minutes} min to stop)", flush=True)
    with gzip.open(os.path.join(out_dir, "samples.jsonl.gz"), "wt", encoding="utf-8", compresslevel=1) as out:
        out.write(json.dumps(dict(meta=dict(game=game))) + "\n")
        try:
            while time.monotonic() - start < minutes * 60 and not os.path.exists(stop):
                tick = time.monotonic()
                try:
                    if live is None:
                        live = LiveReach() if game == "reach" else LiveH4F()
                    seq = struct.unpack_from("<I", m, botctl.OFF_DBG_SEQ)[0]
                    if seq == seq0:                        # (no new tick from the game yet)
                        time.sleep(0.004)
                        continue
                    seq0 = seq
                    act = bytes(m[botctl.OFF_DBG:botctl.OFF_DBG + ACT_N])
                    ps = [p for p in live.players() if p.get("pos") is not None]
                    me = ps[0] if ps else None
                    # (by its handle: one vehicle a group in the summary; which is the Ghost, the test's order says)
                    veh = f"vehicle {me['vehicle'] & 0xFFFFFFFF:08x}" \
                        if me is not None and me.get("vehicle", -1) not in (-1, None) else None
                    out.write(json.dumps(dict(t=round(tick - start, 4), act=act.hex(),
                                              pos=[round(c, 4) for c in me["pos"]] if me else None, veh=veh),
                                         separators=(",", ":")) + "\n")
                    n += 1
                    if tick - last > 2.0:
                        last = tick
                        print(f"{tick - start:6.1f}s  {('in ' + veh) if veh else 'on foot'}  ticks {n}", flush=True)
                    if n % 120 == 0:
                        out.flush()
                except Exception as e:      # the game not up, a map loading, a read racing the game
                    out.write(json.dumps(dict(t=round(time.monotonic() - start, 3), error=f"{type(e).__name__}: {e}")) + "\n")
                    live = None
                    time.sleep(1.0)
                    continue
                time.sleep(max(0.0, 1.0 / HZ - (time.monotonic() - tick)))
        except KeyboardInterrupt:
            pass
    print(f"done: {n} ticks", flush=True)
    summary(out_dir)


def rows(path):
    with gzip.open(os.path.join(path, "samples.jsonl.gz"), "rt", encoding="utf-8") as f:
        try:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    return
                if "act" in d:
                    yield d
        except EOFError:
            return


def with_speed(ds, window=0.25):
    """The rows with his flat speed (u/s) over the last `window` s."""
    out, hist = [], collections.deque()
    for d in ds:
        if d.get("pos") is None:
            hist.clear()
            continue
        hist.append((d["t"], d["pos"]))
        while len(hist) > 2 and d["t"] - hist[1][0] >= window:
            hist.popleft()
        (t0, p0), (t1, p1) = hist[0], hist[-1]
        if t1 - t0 >= window * 0.6:
            out.append((d, math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / (t1 - t0)))
    return out


def candidates(samples, min_on=0.03):
    """Every action bit (u64 words at 8-byte steps) and float (FLOATS) on for some of the ticks: (name, share on, speed
    on, speed off), fastest-on first. samples: [(row, speed)]."""
    on = collections.defaultdict(list)
    n = len(samples)
    for i, (d, sp) in enumerate(samples):
        b = bytes.fromhex(d["act"])
        for off in range(0, len(b) - 7, 8):
            w = struct.unpack_from("<Q", b, off)[0]
            while w:
                bit = (w & -w).bit_length() - 1
                on[f"+0x{off:02X} bit {bit}"].append(i)
                w &= w - 1
        for off in FLOATS:
            if off + 4 <= len(b) and abs(struct.unpack_from("<f", b, off)[0]) > 0.5:
                on[f"+0x{off:02X} float"].append(i)
    out = []
    speeds = [sp for _, sp in samples]
    for name, idx in on.items():
        share = len(idx) / n
        if not min_on <= share <= 1 - min_on:
            continue                                  # (always on or never: not a held button)
        s_on = sorted(speeds[i] for i in idx)
        idx_set = set(idx)
        s_off = sorted(speeds[i] for i in range(n) if i not in idx_set)
        out.append((name, share, s_on[len(s_on) // 2], s_off[len(s_off) // 2]))
    return sorted(out, key=lambda c: c[2] - c[3], reverse=True)


def summary(path):
    by_veh = collections.defaultdict(list)
    for d, sp in with_speed(rows(path)):
        by_veh[d.get("veh") or "on foot"].append((d, sp))
    if not by_veh:
        print("no ticks recorded")
    for veh, samples in by_veh.items():
        if len(samples) < 60:
            continue
        t = [d["t"] for d, _ in samples]
        print(f"\n({t[0]:.0f}-{t[-1]:.0f} s into the capture)", end="")
        sp = sorted(s for _, s in samples)
        print(f"\n{veh}: {len(samples)} ticks, speed median {sp[len(sp) // 2]:.2f}, top (p95) {sp[int(len(sp) * .95)]:.2f} u/s")
        print("  bit / float                share on   speed on   speed off")
        for name, share, s_on, s_off in candidates(samples)[:12]:
            print(f"  {name:24} {share:8.0%} {s_on:10.2f} {s_off:11.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game", nargs="?", choices=("reach", "h4"))
    ap.add_argument("--minutes", type=float, default=10.0)
    ap.add_argument("--summary")
    o = ap.parse_args()
    if o.summary:
        summary(o.summary)
        return
    if not o.game:
        ap.error("the game: reach or h4")
    capture(o.game, os.path.join(ROOT, "logs", f"boost_capture_{o.game}_{time.strftime('%Y%m%d-%H%M%S')}"), o.minutes)


if __name__ == "__main__":
    main()
