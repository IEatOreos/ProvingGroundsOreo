"""Reload capture: the person's raw input while he reloads, to find the bits Reach's reload takes (read-only; custom,
Nov 20). Bots never reloaded in Reach: native/reach.cpp writes jump, fire and use into a bot's action itself and
maps/_inputs/reach.json has no "reload" entry, so the brain's reload press (botctl BTN reload, HB_BTN_RELOAD) never
reached the game; of 186-200 "reload between fights" presses a match, 8-26 were followed by a fuller magazine (the
game's own reload of an empty one). Live Asylum 20261120-232338; the same back to Nov 13, every difficulty.

Each tick: player 0's raw action (botcore copies it to shared memory, hb_shared dbg_action, as tools/boost_capture.py
reads it) and his gun and its magazine. botcore has to be loaded (the bots on, a match running).

  python\\python.exe tools\\reload_capture.py [--minutes 5]     until Ctrl+C, or logs/reload_capture_<stamp>/stop.txt
  python\\python.exe tools\\reload_capture.py --summary logs\\reload_capture_<stamp>

The test: a DMR in hand, no enemy near. Fire 3 rounds, wait 2 s, press reload once (a tap), wait until it is done
and 2 s more; eight times or so. Then two or three times press the reload with a full magazine (nothing happens: a
control). Summary: each reload is where the magazine went up with the same gun; every action bit that came on in the
REACH_S before it, how many of the reloads had it, and how often it came on away from them; the reload's bits are
on before most reloads and seldom otherwise. Nothing is written to the game."""
import argparse
import collections
import gzip
import json
import os
import struct
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HZ = 60.0
ACT_N = 0xC0
REACH_S = (0.1, 3.0)          # s before the magazine goes up: where the press is looked for (a DMR reload ~1.5-2 s)


def capture(out_dir, minutes):
    import botctl
    from brain.live import LiveReach
    os.makedirs(out_dir, exist_ok=True)
    stop = os.path.join(out_dir, "stop.txt")
    m = botctl.shm()
    live, start, n, last, seq0, gun_at = None, time.monotonic(), 0, 0.0, None, 0.0
    gun = (None, None)
    print(f"capturing reach to {out_dir} (Ctrl+C, {stop} or {minutes} min to stop)", flush=True)
    with gzip.open(os.path.join(out_dir, "samples.jsonl.gz"), "wt", encoding="utf-8", compresslevel=1) as out:
        out.write(json.dumps(dict(meta=dict(game="reach"))) + "\n")
        try:
            while time.monotonic() - start < minutes * 60 and not os.path.exists(stop):
                tick = time.monotonic()
                try:
                    if live is None:
                        live = LiveReach()
                    seq = struct.unpack_from("<I", m, botctl.OFF_DBG_SEQ)[0]
                    if seq == seq0:
                        time.sleep(0.004)
                        continue
                    seq0 = seq
                    act = bytes(m[botctl.OFF_DBG:botctl.OFF_DBG + ACT_N])
                    if tick - gun_at > 0.05:            # (his gun and magazine 20 times a second)
                        gun_at = tick
                        ps = [p for p in live.players() if p.get("pos") is not None]
                        me = ps[0] if ps else None
                        if me is not None and me.get("weapon") in (me.get("weapons") or []):
                            i = me["weapons"].index(me["weapon"])
                            mags = me.get("mag") or []
                            gun = (me["weapon"], mags[i] if i < len(mags) else None)
                    out.write(json.dumps(dict(t=round(tick - start, 4), act=act.hex(), w=gun[0], mag=gun[1]),
                                         separators=(",", ":")) + "\n")
                    n += 1
                    if tick - last > 2.0:
                        last = tick
                        print(f"{tick - start:6.1f}s  {gun[0]} {gun[1]}  ticks {n}", flush=True)
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


def bits(act_hex):
    """{"+0xOO bit N"} on in this action (u64 words at 8-byte steps)."""
    b = bytes.fromhex(act_hex)
    on = set()
    for off in range(0, len(b) - 7, 8):
        w = struct.unpack_from("<Q", b, off)[0]
        while w:
            bit = (w & -w).bit_length() - 1
            on.add(f"+0x{off:02X} bit {bit}")
            w &= w - 1
    return on


def reloads(ds):
    """The times his magazine went up with the same gun in hand (a reload done)."""
    out, prev = [], None
    for d in ds:
        if d.get("mag") is None:
            continue
        if prev is not None and d["w"] == prev["w"] and d["mag"] > prev["mag"]:
            out.append(d["t"])
        prev = d
    return out


def analyse(ds):
    """(reload times, [(bit, reloads it rose before, rises away from them, typical ticks held)], ticks)."""
    ds = list(ds)
    done = reloads(ds)
    near = lambda t: any(r - REACH_S[1] <= t <= r - REACH_S[0] for r in done)
    before = collections.defaultdict(set)      # bit: the reloads it rose in the window before
    away = collections.Counter()               # bit: rises outside every window
    held = collections.defaultdict(list)
    was, since = set(), {}
    for d in ds:
        on = bits(d["act"])
        for b in on - was:
            since[b] = d["t"]
            hits = [k for k, r in enumerate(done) if r - REACH_S[1] <= d["t"] <= r - REACH_S[0]]
            if hits:
                before[b].update(hits)
            else:
                away[b] += 1
        for b in was - on:
            if b in since:
                held[b].append(d["t"] - since.pop(b))
        was = on
    names = set(before) | set(away)
    out = []
    for b in names:
        h = sorted(held[b])
        out.append((b, len(before[b]), away[b], h[len(h) // 2] if h else None))
    out.sort(key=lambda x: (-x[1], x[2]))
    return done, out, len(ds)


def summary(path):
    done, cands, n = analyse(rows(path))
    print(f"{n} ticks, {len(done)} reloads seen (the magazine up with the same gun)")
    if not done:
        print("no reload in the capture: fire a few rounds, then press reload")
        return
    print("  bit               before reloads   rises elsewhere   held (median s)")
    for b, k, a, h in cands[:16]:
        print(f"  {b:16} {k:7} of {len(done):<4} {a:12}     {'' if h is None else f'{h:.3f}'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutes", type=float, default=5.0)
    ap.add_argument("--summary")
    o = ap.parse_args()
    if o.summary:
        summary(o.summary)
        return
    capture(os.path.join(ROOT, "logs", f"reload_capture_{time.strftime('%Y%m%d-%H%M%S')}"), o.minutes)


if __name__ == "__main__":
    main()
