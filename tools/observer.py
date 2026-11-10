"""The Observer.

It reads the brain's traces (logs/trace_<map>_<date>-<time>.jsonl, one per match while logs/trace_on
exists, the newest 5 not saved and every saved one kept, each up to its last 15 minutes: the Recording settings,
tools/recording.py; older and hand-named ones, saved ones in logs/evidence,
simulator traces; and every other copy of the mod's on this PC, recording.py other_logs): every bot's position, facing, goal, fight reasons and overrides
each tick; every decision with its top scores, flags, director order and beliefs; every callout
(brain/tracefmt.py). Two ways in:

  python -I observer.py serve [--port 8799] [--open]     the page: map + layers, timeline, bot inspector
  python -I observer.py at <trace> <t>                   every bot at time t: what it did and why
  python -I observer.py bot <trace> <id> [t0 t1]         one bot's decisions over time
  python -I observer.py events <trace> [t0 t1]           callouts, deaths, goal changes, blitzes
  python -I observer.py spawns <trace> [player id]       every respawn: when, who, Invasion side and phase, where, the
                                                         nearest of the map's Invasion respawn flags
  python -I observer.py you <trace> [player id]          your numbers (the Data collector's file when there is one)
  python -I observer.py export <trace> [--keep-names]    the game as one shareable zip (tools/match_export.py; the page's
                                                         Export game button does the same)
"""
import bisect
import collections
import glob
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)                 # (python -I leaves this folder off the path: tools/recording.py)
ROOT = os.path.join(HERE, "..")
LOGS = os.path.join(ROOT, "logs")
MAPS = os.path.join(ROOT, "maps")
CACHE = os.path.join(LOGS, "observer_cache")
PORT = 8799
LIVE_S = 15.0            # a trace written to this recently is a match being played


# ---------------------------------------------------------------- traces

def trace_files():
    """Every trace there is, newest first: [{file, label, map, bytes, mtime, live, kept, copy}]. file: relative to
    logs, or for another copy of the mod's games (an install and a working repo: tools/recording.py other_logs) its
    full path, copy that copy's folder (None: this one's). kept: a match in the queue (tools/recording.py) saved or not;
    None for the rest (bug reports, imported, evidence: always kept)."""
    import recording
    out = []
    for logs in [LOGS] + recording.other_logs(LOGS):
        own, saved = logs == LOGS, recording.saved(logs)
        # bug reports belong to their game (Nov 6: not in the same list as the games):
        # each game lists its reports (bugs: [{t, time, text}]); a report's own copy of the recording shows only
        # when the game's recording is gone (rotated out), as that game
        reports = {os.path.basename(os.path.dirname(p)): p for p in glob.glob(os.path.join(logs, "bug_reports", "*", "trace.jsonl"))}
        games = {os.path.basename(p)[len("trace_"):-len(".jsonl")] for p in glob.glob(os.path.join(logs, "trace_*.jsonl"))}
        copies = [p for stem, p in reports.items() if stem not in games]
        for path in glob.glob(os.path.join(logs, "trace_*.jsonl")) + glob.glob(os.path.join(logs, "evidence", "*.jsonl")) \
                + glob.glob(os.path.join(logs, "sim_*.jsonl")) + copies \
                + glob.glob(os.path.join(logs, "qc_keep", "*.jsonl")) \
                + glob.glob(os.path.join(logs, "imported", "*", "trace_*.jsonl")):   # (games imported from a shared zip)
            try:
                st = os.stat(path)
            except OSError:
                continue                                  # (rotated out this second)
            rel = os.path.relpath(path, logs).replace("\\", "/")
            copy_of = os.path.basename(os.path.dirname(path)) if path in copies else None
            stem = copy_of or (os.path.basename(path)[len("trace_"):-len(".jsonl")] if rel.startswith("trace_") else None)
            bugs = game_bugs(reports[stem]) if stem in reports else []
            label = match_label(path) or (match_label(f"trace_{copy_of}.jsonl") if copy_of else None) \
                or rel.replace(".jsonl", "")
            if rel.startswith("imported/"):
                label = "Imported: " + label
            stamp = recording.stamp_of(path) if "/" not in rel else None
            out.append(dict(file=rel if own else path.replace("\\", "/"), label=label, map=trace_map(path),
                            bytes=st.st_size, mtime=st.st_mtime, live=time.time() - st.st_mtime < LIVE_S,
                            kept=(stamp in saved) if stamp else None, copy=None if own else os.path.dirname(logs),
                            bugs=bugs))
    return sorted(out, key=lambda d: -d["mtime"])


def game_bugs(report_trace):
    """A game's bug reports (bug_reports/<game>/reports.json): [{t, time, text}], in match order."""
    try:
        rs = json.load(open(os.path.join(os.path.dirname(report_trace), "reports.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for r in rs if isinstance(rs, list) else []:
        try:
            t = float(r.get("t"))
        except (TypeError, ValueError):
            continue
        out.append(dict(t=t, time=time.strftime("%H:%M:%S", time.localtime(r.get("unix", 0))) if r.get("unix") else "",
                        text=" ".join(str(r.get("description", "")).split())[:400]))
    return sorted(out, key=lambda b: b["t"])


def bug_label(path):
    """A match with bug reports (tools/bug_reports.py, one folder per match): "Bug reports, 6 reports: <what the
    player wrote first>"."""
    if os.path.basename(path) != "trace.jsonl" or os.path.basename(os.path.dirname(os.path.dirname(path))) != "bug_reports":
        return None
    try:
        rs = json.load(open(os.path.join(os.path.dirname(path), "reports.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not rs:
        return None
    when = time.strftime("%b %d %H:%M", time.localtime(rs[0].get("unix", 0)))
    text = " ".join(rs[0].get("description", "").split())
    n = f"{len(rs)} reports" if len(rs) > 1 else "1 report"
    return f"Bug reports {when}, {n}: {text[:50]}{'...' if len(text) > 50 else ''}"


TIER_NAME = {"novice": "Easy", "average": "Normal", "strong": "Heroic", "top": "Legendary", "demon": "Demon", "blind": "Blind"}


def match_label(path):
    """A recorded match's name in the game list, "Match, Easy": when it started and its difficulty
    (tools/play.py names them trace_<map>_<date>-<time>.jsonl)."""
    m = re.search(r"_(\d{8}-\d{6})\.jsonl$", path)
    if not m:
        return None
    tiers = set()
    try:
        with open(path) as f:
            for _ in range(400):
                line = f.readline()
                if not line:
                    break
                if '"meta"' in line and '"bot"' in line:
                    tiers.add(json.loads(line)["meta"]["bot"].get("tier"))
    except (OSError, ValueError, KeyError):
        pass
    level = (TIER_NAME.get(next(iter(tiers)), "") if len(tiers) == 1 else "Mixed") if tiers else ""
    when = time.strftime("%b %d %H:%M", time.strptime(m.group(1), "%Y%m%d-%H%M%S"))
    return f"Match {when}" + (f", {level}" if level else "")


def trace_map(path):
    """The map a trace is on: its meta line, else trace_<map>.jsonl, else None."""
    try:
        with open(path) as f:
            for _ in range(200):
                line = f.readline()
                if not line:
                    break
                if '"meta"' in line:
                    return json.loads(line)["meta"]["map"]
    except (OSError, ValueError, KeyError):
        pass
    name = os.path.basename(path)
    if name.startswith("trace_"):
        m = name[len("trace_"):-len(".jsonl")]
        while m and not os.path.isdir(os.path.join(MAPS, m)):
            m = m.rsplit("_", 1)[0] if "_" in m else ""
        return m or None
    return None


def listed(file):
    """(game list entry, path) for a file from the page, only if it is one of ours (no other files), else (None, None)."""
    d = next((d for d in trace_files() if d["file"] == file), None)
    return (d, file if os.path.isabs(file) else os.path.join(LOGS, file)) if d else (None, None)


def safe_trace(rel):
    """A trace path from the page, only if it is one of ours (no other files)."""
    return listed(rel)[1]


class Trace:
    """A trace in memory, by kind: bot lines and decisions per bot (time sorted), world lines, calls."""
    def __init__(s, path):
        s.path, s.meta, s.bots = path, {}, collections.defaultdict(list)
        s.thinks, s.world, s.calls, s.map = collections.defaultdict(list), [], [], None
        s.loadouts = []                               # loadout requests (brain/loadouts.py)
        s.coach = []                                  # the AI director's answers and link events (brain/coach.py)
        for line in open(path):
            try:
                d = json.loads(line)
            except ValueError:
                continue                              # a line being written right now
            if "meta" in d:
                s.map = d["meta"].get("map", s.map)
                b = d["meta"].get("bot")
                if b:
                    s.meta[b["id"]] = b
            elif "world" in d:
                s.world.append(d)
            elif "think" in d:
                s.thinks[d["id"]].append(d)
            elif "call" in d:
                s.calls.append(d)
            elif "coach" in d:
                if d["coach"] != "sent":
                    s.coach.append(d)
            elif "loadout" in d:
                s.loadouts.append(d)
            elif "id" in d:
                s.bots[d["id"]].append(d)
        s.map = s.map or trace_map(path)
        s.t_end = max([s.world[-1]["t"] if s.world else 0.0] + [v[-1]["t"] for v in s.bots.values() if v])

    @staticmethod
    def at(rows, t):
        """The last row at or before t (rows sorted by t), or None."""
        i = bisect.bisect_right([r["t"] for r in rows], t) - 1
        return rows[i] if i >= 0 else None

    def deaths(s):
        """[(t, id, team, pos)] from alive -> dead in the world lines (not when everyone goes at once)."""
        out, prev = [], {}
        for w in s.world:
            rows = {r[0]: r for r in w["world"]}
            gone = [pid for pid, r in rows.items() if not r[2] and prev.get(pid, [0, 0, False])[2]]
            if len(gone) < max(3, len(rows) // 2):    # half the players at once: the match ended
                out += [(w["t"], pid, rows[pid][1], prev[pid][3:6]) for pid in gone]
            prev = rows
        return out


def compass(yaw):
    """Facing in words: yaw 0 = +x (east), pi/2 = +y (north)."""
    names = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
    return f"{math.degrees(yaw) % 360:5.0f} deg {names[int(((yaw + math.pi / 8) % (2 * math.pi)) // (math.pi / 4))]}"


def describe_bot(tr, pid, t):
    """Text lines: one bot at time t."""
    b, th = tr.at(tr.bots[pid], t), tr.at(tr.thinks.get(pid, []), t)
    w = tr.at(tr.world, t)
    row = next((r for r in (w or {}).get("world", []) if r[0] == pid), None)
    m = tr.meta.get(pid, {})
    head = f"bot {pid} {m.get('name', '')} [{m.get('tier', '?')} {m.get('pers', '?')}] team {m.get('team', row[1] if row else '?')}"
    if row and not row[2]:
        return [head + ": dead"]
    out = [head]
    if b:
        pitch = b.get("pitch")
        out.append(f"  at {b['pos']} facing {compass(b['yaw'])}" + (f" pitch {math.degrees(pitch):+.0f} deg" if pitch is not None else "")
                   + (f", {b.get('wpn')}" if b.get("wpn") else "") + (f", shield {row[6]:.2f} health {row[7]:.2f}" if row else ""))
        out.append(f"  goal {b['goal']} {b['arg']}" + (f", waypoint {b['wp']}" if b.get("wp") else "")
                   + f", input fwd {b['cmd'][0]:+.2f} strafe {b['cmd'][1]:+.2f}" + (" FIRE" if b["cmd"][3] & 1 else ""))
        out.append("  eyes: " + (att_text(b["att"]) if b.get("att") else "not recorded") + squad_text(row))
        if b.get("veh", -1) not in (-1, None):         # riding: which vehicle (world lines' vehicles) and which seat
            v = next((v for v in (w or {}).get("vehicles", []) if v[0] == b["veh"]), None)
            out.append(f"  in a {v[1] if v else 'vehicle'}" + (f" ({b['seat']})" if b.get("seat") else "")
                       + (f", {v[5]} aboard" if v else ""))
        if b.get("fx"):
            out.append("  fight: " + ", ".join(f"{k} {v}" for k, v in b["fx"].items()))
        if b.get("eq"):
            out.append(f"  equipment {b['eq'][0]}" + (" (on)" if b["eq"][1] else ""))
        notes = sorted({n for r in tr.bots[pid] if t - 1.0 <= r["t"] <= t for n in r.get("notes", [])})
        if notes:
            out.append("  overrides (last 1 s): " + "; ".join(notes))
    if th:
        out.append(f"  decided at {th['t']:.2f}: chose {th['chose'][0]} {th['chose'][1]} | order {th['order'][0]} {th['order'][1]}"
                   f" | posture {th['posture']}")
        out.append("  weighed: " + ", ".join(f"{k} {a} = {v}" for k, a, v in th["think"]))
        f = {k: v for k, v in th["flags"].items() if v not in (False, 0)}
        if f:
            out.append("  because: " + ", ".join(f"{k}={v}" for k, v in f.items()))
        if th["beliefs"]:
            out.append("  believes: " + ", ".join(f"#{e} at {x},{y},{z} ({'seen' if sn else src} {age}s ago)"
                                                  for e, x, y, z, sn, src, age in th["beliefs"]))
    elif b:
        out.append("  (no decisions in this trace: recorded before the observer lines were added)")
    return out


SOURCE = {"eyes": "seen", "radar": "on radar", "callout": "called out", "hit": "shot us", "static": "radar static",
          "pv": "promethean vision", "fake": "a fake radar dot"}


def att_text(a):
    """A bot line's "att" (brain/tracefmt.py): what it looks at and why."""
    k, w = a[0], a[1]
    if k == "watch":
        who, _, src = str(w).partition(" ")
        if who == "static":
            return f"watching the radar static of #{src}"
        if who == "callout":
            return f"watching a callout: {src}"
        if not who.startswith("#"):
            return f"watching {SOURCE.get(who, who)}"
        return f"watching {who}" + (f" ({SOURCE.get(src, src)})" if src else "")
    return {"aim": f"aiming at #{w}", "grenade": f"grenade at #{w}", "gear": f"using {str(w).replace('_', ' ')}",
            "flank": f"checking its {w} flank"}.get(k, "looking where it walks")


def squad_text(row):
    """From a world row (on): how long it has stood still, the teammates formed up with it."""
    if not row or len(row) < 15:
        return ""
    return ((f", standing still {row[12]:.0f} s" if row[12] >= 1 else "")
            + (f", formed up with {' '.join(f'#{m}' for m in row[13])}" if row[13] else ", nobody with it"))


def aim_text(r, vehicles=()):
    """A person's world row's crosshair and ride (rows 15, 16: brain/tracefmt.py crosshair, seat_of), in words; vehicles:
    the world line's [handle, kind, ...] rows, to name the one it is on."""
    if len(r) < 16:
        return ""
    c, ride = r[15], r[16] if len(r) > 16 else None
    kind = {f"v{v[0]}": v[1] for v in vehicles}
    out = ", crosshair " + ("on the sky" if c is None else
                            f"on #{c[3]}" if isinstance(c[3], int) else
                            f"on the {kind.get(c[3], 'vehicle ' + c[3][1:])}" if c[3] else "on the level") + \
        (f" at {c[:3]} {math.dist(r[3:6], c[:3]):.1f} u off" if c is not None else "")
    if ride:
        out += f", riding {ride[0]}" + (f" on its {ride[1]}" if ride[1] else "")
    return out


def cmd_at(path, t):
    tr = Trace(path)
    print(f"{os.path.basename(path)} on {tr.map}, t = {t:.2f} of {tr.t_end:.1f} s")
    w = tr.at(tr.world, t)
    if w:
        print(f"score {w.get('score')} limit {w.get('limit')} time left {w.get('time_left')} posture {w.get('posture')}")
    for pid in sorted(tr.bots):
        print("\n".join(describe_bot(tr, pid, t)))
    for r in (w or {}).get("world", []):           # people: where they are, where their eyes are
        if not r[8] and r[2]:
            print(f"person {r[0]} team {r[1]} at {r[3:6]} facing {compass(r[10])}"
                  + (f", eyes on #{r[14]}" if len(r) > 14 and r[14] >= 0 else ", nobody in sights" if len(r) > 14 else "")
                  + squad_text(r) + aim_text(r, (w or {}).get("vehicles") or ()))
    calls = [c for c in tr.calls if t - 6.0 <= c["t"] <= t]
    if calls:
        print("callouts (last 6 s): " + "; ".join(f"{c['t']:.1f} team {c['team']} #{c['speaker']}: {c['call']}" for c in calls))
    for k in sorted({c["team"]: c for c in tr.coach if c["coach"] == "applied" and c["t"] <= t}.values(), key=lambda c: c["team"]):
        print(f"{k.get('commander') or 'team ' + str(k['team'])} ({t - k['t']:.0f} s ago): {k.get('play')} / {k.get('tempo')}"
              + (f" \"{k['coaching']}\"" if k.get("coaching") else ""))
    dead = [d for d in tr.deaths() if t - 6.0 <= d[0] <= t]
    if dead:
        print("deaths (last 6 s): " + "; ".join(f"{d[0]:.1f} #{d[1]} at {[round(v, 1) for v in d[3]]}" for d in dead))


def cmd_bot(path, pid, t0, t1):
    tr = Trace(path)
    m = tr.meta.get(pid, {})
    print(f"bot {pid} {m.get('name', '')} [{m.get('tier', '?')} {m.get('pers', '?')}] on {tr.map}, {t0:.0f}-{t1:.0f} s")
    last, deaths = None, [d for d in tr.deaths() if d[1] == pid]
    for th in tr.thinks.get(pid, []):
        if not t0 <= th["t"] <= t1:
            continue
        key = (th["chose"][0], json.dumps(th["chose"][1]))
        if key != last:
            last = key
            f = {k: v for k, v in th["flags"].items() if v not in (False, 0)}
            print(f"{th['t']:7.2f}  -> {th['chose'][0]} {th['chose'][1]}   top: "
                  + ", ".join(f"{k} {v}" for k, _, v in th["think"][:3]) + (f"   [{', '.join(f'{k}={v}' for k, v in f.items())}]" if f else ""))
    notes = collections.Counter(n for r in tr.bots.get(pid, []) if t0 <= r["t"] <= t1 for n in r.get("notes", []))
    if notes:
        print("overrides: " + ", ".join(f"{n} x{c}" for n, c in notes.most_common()))
    for d in deaths:
        if t0 <= d[0] <= t1:
            print(f"{d[0]:7.2f}  died at {[round(v, 1) for v in d[3]]}")
    if not tr.thinks.get(pid):
        print("(no decisions in this trace: recorded before the observer lines were added)")


def cmd_events(path, t0, t1):
    tr = Trace(path)
    ev = [(c["t"], f"call team {c['team']} #{c['speaker']}: {c['call']} ({c['kind']})") for c in tr.calls]
    ev += [(d[0], f"death #{d[1]} (team {d[2]}) at {[round(v, 1) for v in d[3]]}") for d in tr.deaths()]
    ev += [(d["t"], f"loadout #{d['id']} asks slot {d['loadout']}: {d['why']} x{d['n']} ({', '.join(d['guns'] or ['not seen yet'])})")
           for d in tr.loadouts]
    ev += [(k["t"], f"{k.get('commander') or 'team ' + str(k.get('team'))} {k['coach']}: " + (
        f"{k.get('play')} / {k.get('tempo')} \"{k.get('coaching') or ''}\" in {k.get('latency')} s" if k["coach"] == "applied"
        else "; ".join(k.get("reasons") or [k.get("text", "")]))) for k in tr.coach]
    was = {}
    for w in tr.world:                               # each team's blitz (director.blitz_tick): rally, go, over
        cur = w.get("blitz") or {}
        for team in sorted(set(was) | set(cur)):
            if cur.get(team) != was.get(team):
                ev.append((w["t"], f"team {team} blitz ({cur[team][0]}): {cur[team][1]}" if team in cur
                           else f"team {team} blitz over"))
        was = cur
    kinds = {v[0]: v[1] for w in tr.world for v in w.get("vehicles", [])}
    for pid, rows in tr.bots.items():                # vehicles: who got in (which seat) and out, where
        prev = -1
        for r in rows:
            v = r.get("veh", -1)
            if v != prev:
                ev.append((r["t"], f"#{pid} " + (f"in {kinds.get(v, 'a vehicle')} ({r.get('seat') or '?'})" if v != -1 else
                                                 f"out of {kinds.get(prev, 'a vehicle')}") + f" at {[round(x, 1) for x in r['pos']]}"))
                prev = v
    for t, text in sorted(e for e in ev if t0 <= e[0] <= t1):
        print(f"{t:7.2f}  {text}")
    switches = collections.Counter()
    for pid, rows in tr.thinks.items():
        prev = None
        for th in rows:
            if t0 <= th["t"] <= t1 and th["chose"][0] != prev:
                if prev:
                    switches[(prev, th["chose"][0])] += 1
                prev = th["chose"][0]
    if switches:
        print("goal switches: " + ", ".join(f"{a}->{b} {n}" for (a, b), n in switches.most_common(12)))


def cmd_spawns(path, who=None):
    """Every respawn in a match: the time, the player (you: the one who is no bot), team, Invasion's side and phase,
    where, the spawn it was (the spawn screen's name, maps/<map>/inv_spawns.json "named", within 3.5 u of its centre
    this phase; "ally #k": a teammate within 1.6 u; "-": neither) and the nearest of the map's Invasion respawn flags
    (objects.json inv_res_p1-3, their team = side, 0 attackers; * when it is the player's side's flag for this phase).
    Streamed: a match's trace is 100-250 MB. who: one player id."""
    name = re.match(r"trace_(.+?)_\d{8}-\d{6}", os.path.basename(path))
    objs = os.path.join(ROOT, "maps", name.group(1), "objects.json") if name else ""
    flags = [(f["type"], f.get("team"), f["pos"]) for f in (json.load(open(objs, encoding="utf-8")).get("netgame_flags", [])
             if os.path.exists(objs) else []) if f.get("type", "").startswith("inv_res_p")]
    named_path = os.path.join(ROOT, "maps", name.group(1), "inv_spawns.json") if name else ""
    named = json.load(open(named_path, encoding="utf-8")).get("named", []) if os.path.exists(named_path) else []
    alive, rows, before = {}, [], {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if '"world"' not in line:
                continue
            r = json.loads(line)
            inv = r.get("invasion") or [0, -1]
            for w in r["world"]:
                if w[2] and alive.get(w[0]) is False and (who is None or w[0] == who):
                    p = (w[3], w[4], w[5])
                    near = min(flags, key=lambda f: math.dist(p, f[2]), default=None)
                    side = ("att" if w[1] == inv[1] else "def") if inv[0] else ""
                    spot = next((n["name"] for n in named if n["side"] == side and str(inv[0]) in n["at"]
                                 and math.dist(p[:2], n["at"][str(inv[0])][:2]) <= 3.5), None)
                    mate = min((m for k, m in before.items() if k != w[0] and m[1] == w[1] and m[2]),
                               key=lambda m: math.dist(p, m[3:6]), default=None)
                    if spot is None and mate is not None and math.dist(p, mate[3:6]) <= 1.6:
                        spot = f"ally #{mate[0]}"
                    rows.append((r["t"], w[0], w[1], not w[8], side, inv[0], p, near, spot or "-"))
                alive[w[0]] = bool(w[2])
            before = {w[0]: w for w in r["world"]}
    print("      t  player    team side phase  where                      spawn          nearest Invasion respawn flag")
    for t, pid, team, you, side, phase, p, near, spot in rows:
        tag = f"#{pid} (you)" if you else f"#{pid}"
        flag = ""
        if near:
            here = near[0] == f"inv_res_p{phase}" and near[1] == (0 if side == "att" else 1)
            flag = f"{near[0]} team {near[1]}{' *' if here else ''}, {math.dist(p, near[2]):.1f} u"
        print(f"{t:7.1f}  {tag:9} {team:4} {side:4} {phase:5}  ({p[0]:7.1f}, {p[1]:7.1f}, {p[2]:6.1f})  {spot:14} {flag}")
    print(f"{len(rows)} respawns" + (f"; yours: {sum(1 for r in rows if r[3])}" if rows else ""))
    if named and rows:
        kinds = collections.Counter("named" if r[8][0].isupper() else "ally" if r[8].startswith("ally") else "other" for r in rows if r[4])
        print(f"Invasion respawns: {kinds['named']} at a named spawn, {kinds['ally']} on a teammate, {kinds['other']} "
              f"elsewhere")


# ---------------------------------------------------------------- the map picture

def base(map_name):
    """The map's picture for the page (cached): the level's top surface shaded by height, every floor
    LiDAR painted (people and bots walked there, all storeys) in teal, and its bounds and zones."""
    import numpy as np
    from PIL import Image
    d = os.path.join(MAPS, map_name)
    hm = np.load(os.path.join(d, "heightmap.npz"))
    top, x0, y0, cell = hm["top"], float(hm["x0"]), float(hm["y0"]), float(hm["cell"])
    h, w = top.shape
    os.makedirs(CACHE, exist_ok=True)
    png = os.path.join(CACHE, map_name + ".png")
    lidar = os.path.join(d, "lidar.json")
    newest = max(os.path.getmtime(os.path.join(d, "heightmap.npz")), os.path.getmtime(lidar) if os.path.exists(lidar) else 0)
    if not os.path.exists(png) or os.path.getmtime(png) < newest:
        # the scenery around the map (the level's top surface): dim
        z = np.where(np.isfinite(top) & (top < 900), top, np.nan)
        lo, hi = np.nanpercentile(z, 2), np.nanpercentile(z, 98)
        k = np.clip((np.nan_to_num(z, nan=lo) - lo) / max(1e-6, hi - lo), 0, 1)
        gy, gx = np.gradient(np.nan_to_num(z, nan=lo))
        shade = np.clip(0.8 + (gx - gy) * 0.6, 0.5, 1.2)
        rgb = np.stack([14 + 34 * k, 18 + 38 * k, 26 + 46 * k], -1) * shade[..., None]
        rgb[~np.isfinite(z)] = (8, 10, 14)
        # floor any player can reach (the nav): the highest reachable storey per cell, by height,
        # with a darker edge where the height steps a unit (storeys and ledges read as shapes)
        fz = np.full((h, w), np.nan)
        walked = np.zeros((h, w), bool)
        crouch = np.zeros((h, w), bool)
        try:
            sys.path.insert(0, ROOT)
            from brain.maps import get_map, terrain
            T = terrain(get_map(map_name))
            if T.lz.shape[1:] == (h, w):
                zs = np.where(T.reach, T.lz, np.nan)
                fz = np.nanmax(np.where(np.isfinite(zs), zs, -np.inf), axis=0)
                fz[~np.isfinite(fz)] = np.nan
        except Exception as e:                      # no nav for this map: scenery and LiDAR only
            print("observer: no nav floors for", map_name, e, flush=True)
        if os.path.exists(lidar):
            for x, y, zz, kind, n in json.load(open(lidar)).get("walk", []):   # LiDAR: 0.25 cells, z in 0.1
                i, j = int((x * 0.25 - x0) / cell), int((y * 0.25 - y0) / cell)
                if 0 <= i < w and 0 <= j < h:
                    walked[j, i] = True
                    crouch[j, i] |= kind == 3
                    if not np.isfinite(fz[j, i]):           # floor the nav lacks: LiDAR found it
                        fz[j, i] = zz * 0.1
        play = np.isfinite(fz)
        if play.any():
            flo, fhi = np.nanpercentile(fz, 2), np.nanpercentile(fz, 98)
            q = np.clip((np.nan_to_num(fz, nan=flo) - flo) / max(1e-6, fhi - flo), 0, 1)
            ramp = np.stack([40 + 90 * q, 70 + 120 * q, 80 + 110 * q], -1)            # low dark teal .. high pale
            band = np.floor(np.nan_to_num(fz, nan=-99) / 1.0)
            edge = (np.diff(band, axis=0, prepend=band[:1]) != 0) | (np.diff(band, axis=1, prepend=band[:, :1]) != 0)
            ramp[edge] *= 0.55
            ramp[walked] = ramp[walked] * 1.15 + 12
            ramp[crouch] = (190, 140, 60)
            rgb[play] = ramp[play]
        img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)[::-1])   # north (+y) up
        scale = max(2, min(6, int(1600 / max(h, w))))
        img.resize((w * scale, h * scale), Image.NEAREST).save(png)
        if play.any():                              # where people play: the page frames this, not the scenery
            js, iis = np.nonzero(play)
            json.dump([x0 + iis.min() * cell, y0 + js.min() * cell, x0 + (iis.max() + 1) * cell, y0 + (js.max() + 1) * cell],
                      open(png[:-4] + ".play.json", "w"))
    play_box = None
    if os.path.exists(png[:-4] + ".play.json"):
        play_box = json.load(open(png[:-4] + ".play.json"))
    zones = []
    cpath = os.path.join(d, "callouts.json")
    if os.path.exists(cpath):
        for name, z in (json.load(open(cpath)).get("zones") or {}).items():
            if z.get("poly"):
                zones.append(dict(name=name, side=z.get("side"), poly=z["poly"]))
    return dict(map=map_name, x0=x0, y0=y0, cell=cell, w=w, h=h, img=f"/base.png?map={map_name}", zones=zones, play=play_box)


# ---------------------------------------------------------------- the page

def you_source(path):
    """Your recording for a game: its Data collector file (same stamp, tools/collector.py), else the trace itself."""
    m = re.search(r"_(\d{8}-\d{6})\.jsonl$", path)
    hits = glob.glob(os.path.join(os.path.dirname(path), f"collect_*_{m.group(1)}.jsonl")) if m else []
    return hits[0] if hits else path


def you_view(path):
    """The "You" section's numbers (tools/player_stats.py), cached per file size and time: a finished game once."""
    sys.path.insert(0, HERE)                          # (python -I leaves this folder off the path)
    import player_stats
    src = you_source(path)
    st = os.stat(src)
    os.makedirs(CACHE, exist_ok=True)
    cache = os.path.join(CACHE, f"you_{os.path.basename(src)}_{int(st.st_mtime)}_{st.st_size}.json")
    if os.path.exists(cache):
        return open(cache, encoding="utf-8").read()
    body = json.dumps(player_stats.page(player_stats.analyze(src)))
    if time.time() - st.st_mtime > LIVE_S:              # a game still being written: not cached
        for old in glob.glob(os.path.join(CACHE, f"you_{os.path.basename(src)}_*.json")):
            os.remove(old)
        open(cache, "w", encoding="utf-8").write(body)
    return body


def serve(port, open_browser):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse
    page = os.path.join(HERE, "observer.html")

    class Handler(BaseHTTPRequestHandler):
        def log_message(s, *a):
            pass

        def send(s, body, ctype, code=200, headers=None):
            s.send_response(code)
            s.send_header("Content-Type", ctype)
            s.send_header("Cache-Control", "no-store")
            for k, v in (headers or {}).items():
                s.send_header(k, str(v))
            s.send_header("Content-Length", str(len(body)))
            s.end_headers()
            s.wfile.write(body)

        def do_POST(s):
            where = urlparse(s.path).path
            if where not in ("/import", "/keep", "/settings") or s.headers.get("X-Observer") != "1":   # (its own page)
                return s.send_error(404)
            n = int(s.headers.get("Content-Length") or 0)
            if where != "/import":                      # Keep game, Recording settings (tools/recording.py)
                import recording
                try:
                    body = json.loads(s.rfile.read(n) if 0 < n < 1 << 16 else b"{}")
                    if where == "/settings":
                        got = recording.save_settings({k: int(body[k]) for k in recording.LIMITS if k in body})
                        return s.send(json.dumps(got).encode(), "application/json")
                    d, path = listed(body.get("file", ""))
                    stamp = recording.stamp_of(path) if d and d["kept"] is not None else None
                    if not stamp:
                        return s.send(b'{"error": "only recorded matches can be kept"}', "application/json", 400)
                    logs = os.path.dirname(path)                # (this copy's logs, or the copy's that recorded it)
                    recording.keep(stamp, bool(body.get("keep")), logs)
                    return s.send(json.dumps(dict(kept=stamp in recording.saved(logs))).encode(), "application/json")
                except (ValueError, TypeError, KeyError, OSError) as e:
                    return s.send(json.dumps(dict(error=str(e))).encode(), "application/json", 400)
            if not 0 < n <= 1 << 30:
                return s.send(b'{"error": "no file, or bigger than 1 GB"}', "application/json", 400)
            try:
                sys.path.insert(0, HERE)
                import match_export
                path = match_export.import_game(s.rfile.read(n), LOGS)
                s.send(json.dumps(dict(file=os.path.relpath(path, LOGS).replace("\\", "/"))).encode(), "application/json")
            except ValueError as e:
                s.send(json.dumps(dict(error=str(e))).encode(), "application/json", 400)

        def do_GET(s):
            u = urlparse(s.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                if u.path in ("/", "/index.html"):
                    s.send(open(page, "rb").read(), "text/html; charset=utf-8")
                elif u.path == "/settings":                     # the Recording settings (tools/recording.py)
                    import recording
                    got = recording.settings()
                    # (and where games are looked for, for the page's empty list: this copy's logs, recording on or
                    # off (logs/trace_on, tools/setup.py), the other copies of the mod)
                    s.send(json.dumps(dict(games=got["games"], minutes=got["minutes"], limits=recording.LIMITS,
                                           logs=os.path.normpath(LOGS), on=os.path.exists(os.path.join(LOGS, "trace_on")),
                                           copies=[os.path.dirname(x) for x in recording.other_logs(LOGS)])).encode(),
                           "application/json")
                elif u.path == "/traces":
                    s.send(json.dumps(trace_files()).encode(), "application/json")
                elif u.path == "/maps":
                    s.send(json.dumps(sorted(m for m in os.listdir(MAPS) if os.path.exists(os.path.join(MAPS, m, "heightmap.npz")))).encode(),
                           "application/json")
                elif u.path == "/base":
                    name = q.get("map", "")
                    if not os.path.exists(os.path.join(MAPS, name, "heightmap.npz")) or "/" in name or "\\" in name:
                        return s.send(b'{"error": "no level data for this map"}', "application/json", 404)
                    s.send(json.dumps(base(name)).encode(), "application/json")
                elif u.path == "/base.png":
                    name = q.get("map", "")
                    path = os.path.join(CACHE, name + ".png")
                    if "/" in name or "\\" in name or not os.path.exists(path):
                        return s.send_error(404)
                    s.send(open(path, "rb").read(), "image/png")
                elif u.path == "/trace":
                    path = safe_trace(q.get("file", ""))
                    if path is None:
                        return s.send(b"unknown trace", "text/plain", 404)
                    off, cap = int(q.get("offset", 0)), int(q.get("max", 8 << 20))
                    size = os.path.getsize(path)
                    with open(path, "rb") as f:
                        f.seek(off)
                        chunk = f.read(min(cap, max(0, size - off)))
                    cut = chunk.rfind(b"\n") + 1               # whole lines only: the rest comes next time
                    s.send(chunk[:cut], "text/plain; charset=utf-8", headers={"X-Next-Offset": off + cut, "X-Size": size})
                elif u.path == "/you":                          # your numbers (tools/player_stats.py)
                    path = safe_trace(q.get("file", ""))
                    if path is None:
                        return s.send(b'{"error": "unknown trace"}', "application/json", 404)
                    try:
                        s.send(you_view(path).encode(), "application/json")
                    except Exception as e:                      # the analysis failing must not stop the observer
                        s.send(json.dumps(dict(error=f"{type(e).__name__}: {e}")).encode(), "application/json", 500)
                elif u.path == "/export":                       # one shareable file of this game (tools/match_export.py)
                    path = safe_trace(q.get("file", ""))
                    if path is None:
                        return s.send(b"unknown trace", "text/plain", 404)
                    try:
                        sys.path.insert(0, HERE)
                        import match_export
                        z = match_export.export(path, keep_names=q.get("names") == "1")
                        s.send(open(z, "rb").read(), "application/zip",
                               headers={"Content-Disposition": f'attachment; filename="{os.path.basename(z)}"'})
                    except Exception as e:                      # a failed export must not stop the observer
                        s.send(f"{type(e).__name__}: {e}".encode(), "text/plain; charset=utf-8", 500)
                else:
                    s.send_error(404)
            except (ValueError, OSError) as e:
                s.send(json.dumps(dict(error=str(e))).encode(), "application/json", 500)

    url = f"http://127.0.0.1:{port}/"
    if open_browser:
        sys.path.insert(0, HERE)
        import appwindow
    try:
        # (no address reuse: on Windows two Observers could both serve the port; now the second one finds the first)
        srv = type("Server", (ThreadingHTTPServer,), dict(allow_reuse_address=False))(("127.0.0.1", port), Handler)
    except OSError:                                     # an Observer runs already (its window was closed): show it
        if open_browser:
            appwindow.open_window(url)
        print(f"Observer already running: {url}", flush=True)
        return
    import recording
    recording.register()                                # (the other copies' Observers list this copy's games)
    print(f"Observer: {url}  (Ctrl+C to stop)", flush=True)
    if open_browser:
        appwindow.open_window(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    a = sys.argv[1:]
    if not a or a[0] == "serve":
        port = int(a[a.index("--port") + 1]) if "--port" in a else PORT
        return serve(port, "--open" in a)
    path = a[1] if os.path.exists(a[1]) else os.path.join(LOGS, a[1])
    if a[0] == "at":
        cmd_at(path, float(a[2]))
    elif a[0] == "bot":
        cmd_bot(path, int(a[2]), float(a[3]) if len(a) > 3 else 0.0, float(a[4]) if len(a) > 4 else 1e9)
    elif a[0] == "events":
        cmd_events(path, float(a[2]) if len(a) > 2 else 0.0, float(a[3]) if len(a) > 3 else 1e9)
    elif a[0] == "spawns":
        cmd_spawns(path, int(a[2]) if len(a) > 2 else None)
    elif a[0] == "you":
        sys.path.insert(0, HERE)
        import player_stats
        print(player_stats.report(player_stats.analyze(you_source(path), int(a[2]) if len(a) > 2 else None)))
    elif a[0] == "export":
        sys.path.insert(0, HERE)
        import match_export
        print("exported", match_export.export(path, keep_names="--keep-names" in a))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
