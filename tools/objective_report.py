"""Objective play in a match trace.

CTF: every flag run (who, how long, how it ended: captured, killed, dropped), teammates with the carrier (escort),
the hunt on an enemy carrying our flag, defenders at home when our flag was pulled, the roles each team played.
King of the Hill: time on the hill per team. Oddball: time with the ball, guards around the carrier.
Every mode: what each team spent its time on (goals) and each bot's roles.

usage: python -I objective_report.py [trace.jsonl] [--save]    (default: the newest logs/trace_*.jsonl;
       --save also writes logs/verify/objective_<trace name>.txt)
"""
import glob
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)

ESCORT_R = 10.0     # a teammate this close to the carrier is with him
HOME_R = 12.0       # a player this close to his team's flag stand is home
HUNT_R = 15.0       # a player this close to an enemy carrier is on him
GOAL = re.compile(r'"id": (\d+), "pos": .*?"goal": "(\w+)"')


def load(path):
    meta, worlds, orders, goals = {"bots": {}}, [], defaultdict(list), defaultdict(Counter)
    with open(path) as f:
        for line in f:
            if '"world"' in line:
                worlds.append(json.loads(line))
            elif '"think"' in line:
                d = json.loads(line)
                orders[d["id"]].append((d["t"], (d.get("order") or ["?"])[0]))
            elif '"meta"' in line:
                d = json.loads(line)["meta"]
                meta.setdefault("map", d.get("map"))
                if d.get("bot"):
                    meta["bots"][d["bot"]["id"]] = d["bot"]
            else:
                m = GOAL.search(line)
                if m:
                    goals[int(m.group(1))][m.group(2)] += 1
    return meta, worlds, orders, goals


def role_at(orders, pid, t):
    """The bot's role at time t: its newest order at or before t."""
    best = None
    for tt, role in orders.get(pid, ()):
        if tt > t:
            break
        best = role
    return best


def flat(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def mark_homes(worlds, stands):
    """Each world row gets _homes {team: (x, y)}: where that team's flag sat when last seen home (One Flag: the one
    flag keeps stand 0 while the sides swap, so it belongs to whichever team spawns beside it that round)."""
    cur = {t: s[:2] for t, s in stands.items()}
    for w in worlds:
        for k, v in (w.get("flags") or {}).items():
            if v[0] == "home":
                cur[int(k)] = (v[1], v[2])
        w["_homes"] = dict(cur)


def ctf(worlds, orders, stands, name):
    """Flag runs from the carriers (world row [9]) and the scores; [lines]."""
    runs, active, last = [], {}, None
    pulls = []      # (t, carrier team, defenders home, defenders assigned)
    for w in worlds:
        t, rows = w["t"], {r[0]: r for r in w["world"]}
        score = {int(k): v for k, v in (w.get("score") or {}).items()}
        if last is not None:
            for team, v in score.items():
                if v > last.get(team, v):             # a capture: that team's run that just ended
                    run = max((r for r in runs if r["team"] == team and t - r["t1"] < 1.5), key=lambda r: r["t1"],
                              default=None) or active.get(next((p for p, r in active.items() if r["team"] == team), -1))
                    if run:
                        run["end"] = "captured"
        last = score
        for pid, r in rows.items():
            carrying = r[2] and r[9]
            run = active.get(pid)
            if carrying and run is None:
                fk = next((int(k) for k, v in (w.get("flags") or {}).items() if v[4] == pid), 1 - r[1] % 2)
                home = w["_homes"].get(fk)                                   # the carried flag's stand
                goal = max(stands.values(), key=lambda s: flat(s, home)) if home and stands else None   # the other
                mine = [q for q in rows.values() if q[1] != r[1] and q[2]]   # the team whose flag it is
                at_home = sum(1 for q in mine if home and flat(q[3:5], home) < HOME_R + 4)
                assigned = sum(1 for q in mine if role_at(orders, q[0], t) == "defender")
                if home and flat(r[3:5], home) < 3.0:
                    pulls.append((t, r[1], at_home, assigned))
                run = active[pid] = dict(id=pid, team=r[1], t0=t, t1=t, end="?", start=r[3:5], near=[], hunt=[],
                                         escorts=Counter(), dist0=None, goal=goal)
            if run is None:
                continue
            if carrying:
                mates = [q for q in rows.values() if q[1] == r[1] and q[0] != pid and q[2]]
                foes = [q for q in rows.values() if q[1] != r[1] and q[2]]
                run["near"].append(sum(1 for q in mates if flat(q[3:5], r[3:5]) < ESCORT_R))
                run["hunt"].append(sum(1 for q in foes if flat(q[3:5], r[3:5]) < HUNT_R))
                for q in mates:
                    if flat(q[3:5], r[3:5]) < ESCORT_R:
                        run["escorts"][q[0]] += 1
                run["t1"], run["last"] = t, r[3:5]
            else:
                run["end"] = "killed" if not r[2] else "dropped"
                run["t1"] = t
                runs.append(active.pop(pid))
    runs += active.values()
    out = [f"CTF: {len(runs)} flag runs, {len(pulls)} pulls off a stand"]
    for team in sorted({r["team"] for r in runs} | {0, 1}):
        mine = [r for r in runs if r["team"] == team]
        caps = sum(r["end"] == "captured" for r in mine)
        out.append(f"  team {team}: {len(mine)} runs, {caps} captured, {sum(r['end'] == 'killed' for r in mine)} carrier "
                   f"killed, {sum(r['end'] == 'dropped' for r in mine)} dropped")
    for r in runs:
        n = len(r["near"]) or 1
        with_one = sum(1 for k in r["near"] if k >= 1) / n
        top = ", ".join(f"{name(p)} {c / n:.0%}" for p, c in r["escorts"].most_common(3))
        left = f", ended {flat(r['last'], r['goal']):.0f} u from the capture point" if r["goal"] and r.get("last") else ""
        out.append(f"  {r['t0']:6.1f}-{r['t1']:6.1f}s {name(r['id'])} (team {r['team']}) {r['end']}{left}: a teammate "
                   f"within {ESCORT_R:.0f} u {with_one:.0%} of the run (mean {sum(r['near']) / n:.1f}); enemies "
                   f"within {HUNT_R:.0f} u mean {sum(r['hunt']) / n:.1f}; with him: {top or 'nobody'}")
    for t, team, home, assigned in pulls:
        out.append(f"  pull at {t:6.1f}s by team {team}: the other team had {home} at home, {assigned} told to defend")
    return out


def king(worlds):
    on, moves, last = Counter(), 0, None
    for w in worlds:
        h = w.get("hill")
        if not h:
            continue
        if last and flat(h, last) > 2.0:
            moves += 1
        last = h
        teams = {r[1] for r in w["world"] if r[2] and flat(r[3:5], h) < h[3] and abs(r[5] - h[2]) < 3.0}
        on["contested" if len(teams) > 1 else f"team {teams.pop()}" if teams else "empty"] += 1
    n = sum(on.values()) or 1
    return [f"King of the Hill: {moves} hill moves; time on the hill: " +
            ", ".join(f"{k} {v / n:.0%}" for k, v in sorted(on.items()))] if on else ["King of the Hill: no hill seen"]


def oddball(worlds, name):
    held, guard, n_held = Counter(), [], 0
    for w in worlds:
        b = w.get("ball")
        if not b:
            continue
        rows = {r[0]: r for r in w["world"]}
        c = rows.get(b[3]) if b[3] is not None else None
        held[f"team {c[1]}" if c else "loose"] += 1
        if c:
            n_held += 1
            guard.append(sum(1 for q in rows.values() if q[1] == c[1] and q[0] != c[0] and q[2]
                             and flat(q[3:5], c[3:5]) < ESCORT_R))
    n = sum(held.values()) or 1
    if not held:
        return ["Oddball: no ball seen"]
    return [f"Oddball: ball " + ", ".join(f"{k} {v / n:.0%}" for k, v in sorted(held.items())) +
            (f"; guards within {ESCORT_R:.0f} u of the carrier: mean {sum(guard) / len(guard):.1f}, none "
             f"{sum(1 for g in guard if g == 0) / len(guard):.0%} of the time" if guard else "")]


def roles(worlds, orders, stands, meta, name):
    """Each bot's role share, and for defenders: share of that time spent home."""
    share, home_t = defaultdict(Counter), defaultdict(lambda: [0, 0])
    for w in worlds:
        for r in w["world"]:
            if not r[2] or not r[8]:
                continue
            role = role_at(orders, r[0], w["t"]) or "?"
            share[r[0]][role] += 1
            st = w["_homes"].get(r[1])
            if role == "defender" and st:
                home_t[r[0]][0] += 1
                home_t[r[0]][1] += flat(r[3:5], st) < HOME_R
    out = ["Roles (share of each bot's living time):"]
    for pid in sorted(share):
        n = sum(share[pid].values()) or 1
        b = meta["bots"].get(pid, {})
        d = home_t.get(pid)
        extra = f"; defending: home {d[1] / d[0]:.0%} of it" if d and d[0] else ""
        out.append(f"  {name(pid):<14} team {b.get('team', '?')} {b.get('tier', ''):<7} {b.get('pers', ''):<9} " +
                   ", ".join(f"{k} {v / n:.0%}" for k, v in share[pid].most_common(4)) + extra)
    return out


def report(path):
    meta, worlds, orders, goals = load(path)
    from brain.maps import get_map
    mp = get_map(meta["map"]) if meta.get("map") else {}
    stands = {t: (v.x, v.y, v.z) for t, v in (mp.get("flags") or {}).items()}
    names = {pid: b["name"] for pid, b in meta["bots"].items()}
    name = lambda pid: names.get(pid, f"player {pid}")      # noqa: E731
    modes = Counter(w.get("mode") for w in worlds)
    last = worlds[-1] if worlds else {}
    out = [f"{os.path.basename(path)}: {meta.get('map')}, {len(worlds) * 0.25:.0f} s of world rows, modes {dict(modes)}, "
           f"final score {last.get('score')} (limit {last.get('limit')})"]
    mark_homes(worlds, stands)
    if modes.get("ctf"):
        out += ctf(worlds, orders, stands, name)
    if modes.get("king"):
        out += king(worlds)
    if modes.get("oddball"):
        out += oddball(worlds, name)
    out += roles(worlds, orders, stands, meta, name)
    out.append("Goals (share of each team's bot ticks):")
    by_team = defaultdict(Counter)
    for pid, c in goals.items():
        by_team[meta["bots"].get(pid, {}).get("team", "?")].update(c)
    for team, c in sorted(by_team.items(), key=lambda kv: str(kv[0])):
        n = sum(c.values()) or 1
        out.append(f"  team {team}: " + ", ".join(f"{k} {v / n:.0%}" for k, v in c.most_common(6)))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else max(glob.glob(os.path.join(ROOT, "logs", "trace_*.jsonl")), key=os.path.getmtime)
    text = "\n".join(report(path))
    print(text)
    if "--save" in sys.argv:
        dst = os.path.join(ROOT, "logs", "verify", "objective_" + os.path.basename(path).replace(".jsonl", ".txt"))
        open(dst, "w").write(text + "\n")
        print("saved", dst)


if __name__ == "__main__":
    main()
