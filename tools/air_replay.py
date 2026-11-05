"""Closed-loop replay of a bot pilot against a match's real enemies: the bot flies (a point-mass aircraft on the map's
level: its throttle, view yaw and pitch are its heading, speed SPEED[kind] u/s at full throttle, boost x1.6), the
enemies move as the trace has them. Measures the attack runs: share of run ticks inside the cannons' range, fire ticks
per run, pull-up notes a minute, ticks under the floor. Used by tools/test_air_runs.py; run on a live trace:

usage: python -I air_replay.py <trace.jsonl> <bot id> <from s> <to s> [kind]  -> the numbers for that pilot's window
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from brain import vehicles  # noqa: E402
from brain.bot import CANNON_R, Bot, Order  # noqa: E402
from brain.core import PlayerState, Snapshot, Vec  # noqa: E402
from brain.maps import get_map, terrain  # noqa: E402
from brain.profiles import make_profile  # noqa: E402

SPEED = {"banshee": 9.0, "storm_banshee_mp": 9.0, "h2a_banshee": 9.0, "hornet": 8.0, "h2a_hornet": 8.0, "falcon": 7.0, "sabre": 20.0, "seraph": 20.0}   # u/s, full throttle
HZ = 30
HANDLE = 0x7777


def fly(M, start, yaw, enemies_at, seconds, kind="banshee", team=0, seed=1, tier="top"):
    """enemies_at(t) -> [(id, team, Vec)] (t from 0). The pilot starts at `start` facing yaw. Returns the metrics."""
    T = terrain(M)
    b = Bot(1, team, make_profile(tier, "rusher", random.Random(seed)), M, random.Random(seed))
    b._terrain = T
    b.order = Order("mid", start)
    pos, vel, pitch = Vec(start.x, start.y, start.z), Vec(), 0.0
    m = dict(ticks=0, run=0, run_in=0, fire=0, fire_run=0, pulls=0, under=0, runs=0, d_run=[], notes={})
    phase = None
    for k in range(int(seconds * HZ)):
        t = k / HZ
        me = PlayerState(1, team, "pilot", pos, vel, yaw, pitch, vehicle=HANDLE, weapon="none")
        foes = [PlayerState(i, tm, f"e{i}", p, is_bot=True) for i, tm, p in enemies_at(t)]
        v = dict(handle=HANDLE, kind=kind, pos=(pos.x, pos.y, pos.z), occupied=True, riders=1, team=team,
                 fwd=(math.cos(yaw), math.sin(yaw), 0.0), up=(0.0, 0.0, 1.0), turrets=[], manned=[])
        snap = Snapshot(100.0 + t, [me] + foes, vehicles=[v], mode="slayer")
        a = b.think(100.0 + t, 1 / HZ, snap, T.los, T.nav, [])
        yaw, pitch = a.yaw, a.pitch
        vtol = (vehicles.spec(kind) or {}).get("vtol") or vehicles.TAKE_OFF.get(vehicles.kind_of(kind), ("",))[0] == "up"
        vert = getattr(a, "vertical", 0.0)
        boost = 1.6 if not vtol and b.game == "reach" and (a.fire2 or vert > 0.75) else 1.0
        sp = SPEED.get(kind, 8.0) * max(-0.5, min(1.0, a.forward)) * boost
        cp = math.cos(a.pitch)
        # (a VTOL's vertical input lifts and lowers it, 3 u/s: a Hornet's or Falcon's take-off)
        vel = Vec(math.cos(yaw) * cp * sp, math.sin(yaw) * cp * sp, math.sin(a.pitch) * sp + (3.0 * vert if vtol else 0.0))
        pos = pos + vel * (1 / HZ)
        floor = pos.z - T.height_over(pos.x, pos.y, pos.z)
        if pos.z < floor + 0.5:                    # (the level stops it: no flying through the floor)
            pos = Vec(pos.x, pos.y, floor + 0.5)
            m["under"] += 1
        notes = b.notes or []
        m["ticks"] += 1
        m["pulls"] += any("pull up" in n or "pulling out" in n for n in notes)
        for n in notes:
            m["notes"][n[:40]] = m["notes"].get(n[:40], 0) + 1
        m["fire"] += a.fire
        att = b.att or [None]
        if att[0] == "run":
            m["run"] += 1
            q = next((p for i, tm, p in enemies_at(t) if i == att[1]), None)
            d = (q - pos).length() if q is not None else 99.0
            m["d_run"].append(d)
            m["run_in"] += d < CANNON_R
            if q is not None and d < CANNON_R:          # the nose's error on him, in range
                ya = math.atan2(q.y - pos.y, q.x - pos.x)
                pa = math.atan2(q.z + 0.6 - pos.z, max(0.1, math.hypot(q.x - pos.x, q.y - pos.y)))
                m.setdefault("err", []).append(math.degrees(max(abs(math.remainder(ya - a.yaw, 2 * math.pi)), abs(pa - a.pitch))))
                if os.environ.get("AIR_DEBUG"):
                    bel = b.per.beliefs.get(att[1])
                    print(round(t, 2), "err", round(m["err"][-1], 1), "dyaw", round(math.degrees(math.remainder(ya - a.yaw, 2 * math.pi)), 1),
                          "dpitch", round(math.degrees(pa - a.pitch), 1), "d", round(d, 1), "belief off",
                          round((bel.pos - q).length(), 1) if bel else None, "seen", bool(bel and bel.seen), notes)
            m["fire_run"] += a.fire
        if att[0] in ("run", "pass") and att[0] != phase and att[0] == "run":
            m["runs"] += 1
        phase = att[0]
        if os.environ.get("AIR_TRACE") and k % 10 == 0:
            q = next((p for i, tm, p in enemies_at(t) if len(att) > 1 and i == att[1]), None)
            print(round(t, 1), att[0], "d", round((q - pos).length(), 1) if q is not None else None,
                  "h", round(T.height_over(pos.x, pos.y, pos.z), 1), "fwd", round(a.forward, 2), "pitch", round(a.pitch, 2),
                  "fire", int(a.fire), "goal", b.goal[0], notes)
    mins = m["ticks"] / HZ / 60.0
    d = sorted(m.pop("d_run")) or [99.0]
    m["notes"] = dict(sorted(m["notes"].items(), key=lambda e: -e[1])[:6])
    e = sorted(m.pop("err", [])) or [99.0]
    m["nose_err_deg_p25_50_75"] = [round(e[int(len(e) * f)], 1) for f in (0.25, 0.5, 0.75)]
    m.update(in_range=round(m["run_in"] / max(1, m["run"]), 2), fire_per_run=round(m["fire_run"] / max(1, m["runs"]), 1),
             pulls_per_min=round(m["pulls"] / max(1e-6, mins), 1), d_run_median=round(d[len(d) // 2], 1))
    return m


def trace_enemies(path, pilot, t0, t1):
    """The pilot's enemies through [t0, t1] from a trace's world rows: (start pos, yaw, enemies_at, map, team)."""
    rows, meta_map, team, start = [], None, None, None
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if "meta" in r:
                meta_map = r["meta"]["map"]
                if r["meta"]["bot"]["id"] == pilot:
                    team = r["meta"]["bot"]["team"]
            if "world" in r and t0 <= r["t"] <= t1:
                rows.append((r["t"] - t0, [(p[0], p[1], Vec(p[3], p[4], p[5])) for p in r["world"] if p[2]]))
                if start is None:
                    me = next((p for p in r["world"] if p[0] == pilot), None)
                    if me:
                        start = (Vec(me[3], me[4], me[5]), me[10])
    foes = lambda t: next((e for tt, e in reversed(rows) if tt <= t), rows[0][1])
    return start, (lambda t: [e for e in foes(t) if e[1] != team and e[0] != pilot]), meta_map, team


def main():
    path, pilot, t0, t1 = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    (pos, yaw), enemies, mp, team = trace_enemies(path, pilot, t0, t1)
    kind = sys.argv[5] if len(sys.argv) > 5 else "banshee"
    print(mp, fly(get_map(mp), pos, yaw, enemies, t1 - t0, kind=kind, team=team))


if __name__ == "__main__":
    main()
