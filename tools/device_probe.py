"""Map devices live (H2A / H4: switches, doors, bridges the map variant places;, Stonetown's
shoot-to-open gate and bridge locks). Needs a match started with the test override's "brain": "none"
(play.py adds the bots and leaves them to this tool).

usage: python -I device_probe.py list [dll]                         objects by type (+ the map's known doors/controls)
       python -I device_probe.py watch <seconds> [dll]               objects that move (gates opening, bridges extending)
       python -I device_probe.py shoot <x> <y> <z> [--from x y] [--seconds 8] [--map NAME] [dll]
           bot slot 0 walks to --from (by the nav), aims at (x, y, z) and fires; prints what moved
"""
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import botctl  # noqa: E402
from brain.live import LiveH4F  # noqa: E402

PEOPLE_TYPES = (0, 2)          # bipeds and weapons move all the time: not devices
EYE = 0.24                     # H2A position sits 0.38 over the floor; eye ~0.62 over the floor


def snap(L):
    return {h: (typ, name, pos) for h, typ, name, pos in L.objects()}


def moved(a, b, skip=PEOPLE_TYPES):
    out = []
    for h, (typ, name, p) in b.items():
        if typ in skip or h not in a:
            continue
        q = a[h][2]
        d = math.dist(p, q)
        if d > 0.05:
            out.append((h, typ, name, [round(v, 2) for v in q], [round(v, 2) for v in p], round(d, 2)))
    return out


def cmd_list(L, map_name):
    objs = L.objects()
    by = {}
    for h, typ, name, p in objs:
        by.setdefault(typ, []).append((h, name, p))
    for typ, xs in sorted(by.items()):
        print(f"type {typ}: {len(xs)}  e.g. " + ", ".join(f"{n}@{[round(v, 1) for v in p]}" for _, n, p in xs[:4]))
    fpath = os.path.join(ROOT, "maps", map_name, "features.json")
    if os.path.exists(fpath):
        for f in json.load(open(fpath))["features"]:
            if f["kind"] in ("door", "control", "lift", "launcher", "shield"):
                near = min(objs, key=lambda o: math.dist(o[3], f["pos"]))
                print(f"{f['kind']} {f['name']} at {[round(v, 1) for v in f['pos']]}: nearest live object type {near[1]} "
                      f"{near[2]} {math.dist(near[3], f['pos']):.2f} away")


def cmd_watch(L, seconds):
    a = snap(L)
    t0, seen = time.time(), {}
    while time.time() - t0 < seconds:
        time.sleep(0.5)
        for row in moved(a, snap(L)):
            seen[row[0]] = row
    for row in seen.values():
        print("moved:", row)
    print(f"{len(seen)} objects moved in {seconds:.0f} s")


def bot_pos(L, index):
    for p in L.players():
        if p["index"] == index:
            return p["pos"]
    return None


def cmd_shoot(L, target, stand, seconds, map_name):
    m = botctl.shm()
    st = botctl.status(m)
    if not st["bots"]:
        sys.exit("no bot slots: start the match with the test override's red/blue and brain none")
    slot, index = sorted(st["bots"].items())[0]
    from brain.core import Vec
    if stand:
        from brain.maps import get_map, terrain
        T = terrain(get_map(map_name))
        t0 = time.time()
        while time.time() - t0 < 60:
            p = bot_pos(L, index)
            if p is None:
                time.sleep(0.2)
                continue
            if math.dist(p[:2], stand[:2]) < 0.4:
                break
            w = T.nav(Vec(*p), Vec(stand[0], stand[1], p[2]))
            botctl.act(m, slot, 1.0, 0.0, math.atan2(w.y - p[1], w.x - p[0]), 0.0, 0)
            time.sleep(1 / 30)
        print("at", [round(v, 2) for v in bot_pos(L, index)])
    a = snap(L)
    t0, k, seen = time.time(), 0, {}
    while time.time() - t0 < seconds:
        p = bot_pos(L, index)
        if p is None:
            time.sleep(0.2)
            continue
        dx, dy, dz = target[0] - p[0], target[1] - p[1], target[2] - (p[2] + EYE)
        yaw, pitch = math.atan2(dy, dx), math.atan2(dz, math.hypot(dx, dy))
        k += 1
        botctl.act(m, slot, 0.0, 0.0, yaw, pitch, 1 if k % 6 < 3 else 0)   # pull, release (burst weapons)
        if k % 10 == 0:
            for row in moved(a, snap(L)):
                seen[row[0]] = row
        time.sleep(1 / 30)
    botctl.act(m, slot, 0.0, 0.0, yaw, pitch, 0)
    for row in seen.values():
        print("moved:", row)
    print(f"{len(seen)} objects moved while shooting at {target}")


def main():
    args = sys.argv[1:]
    dll = next((a for a in args if a.endswith(".dll")), "groundhog.dll")
    args = [a for a in args if not a.endswith(".dll")]
    L = LiveH4F(dll)
    L.players()
    map_name = "h2a_ca_zanzibar"
    if "--map" in args:
        i = args.index("--map")
        map_name = args[i + 1]
        del args[i:i + 2]
    if args[0] == "list":
        cmd_list(L, map_name)
    elif args[0] == "watch":
        cmd_watch(L, float(args[1]))
    elif args[0] == "shoot":
        target = [float(v) for v in args[1:4]]
        stand = None
        if "--from" in args:
            i = args.index("--from")
            stand = [float(args[i + 1]), float(args[i + 2])]
        seconds = float(args[args.index("--seconds") + 1]) if "--seconds" in args else 8.0
        cmd_shoot(L, target, stand, seconds, map_name)


if __name__ == "__main__":
    main()
