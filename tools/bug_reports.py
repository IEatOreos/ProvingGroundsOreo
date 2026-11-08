"""the player's bug reports from the game.

botcore (native/overlay.cpp, s89) saves logs/bug_reports/<YYYYMMDD-HHMMSS>/report.json when the player presses Save in
the pause screen's "Report bot bug" window (or F9 in a match): {time, unix, title, how, description}. The brain
(tools/live_bots.py, attach_new) files it within a second into its match's folder and removes the single one:
  logs/bug_reports/<recording>/        one folder per match, named after its recording (reach_70_boneyard_20261025-...)
    trace.jsonl    the match recording (the Observer's replay), one copy: refreshed at each report, whole at the end
                   (finish); a {"t", "bug", "text"} line marks each report's moment in it
    reports.json   [report, ...] each: stamp, time, how, description, the match second t, map, mode, score, where every
                   player was and what each bot was doing then
The Observer lists bug_reports/<recording>/trace.jsonl and opens at a report's moment from the link main() prints.

usage: python -I bug_reports.py                 every report, newest match first: description, moment, Observer link
       python -I bug_reports.py <stamp>         one report in full (bots at the moment, what each was doing)
       python -I bug_reports.py --migrate       old one-folder-per-report reports into their match folders
"""
import glob
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DIR = os.path.join(ROOT, "logs", "bug_reports")
OBSERVER = "http://localhost:8799/"
STAMP = re.compile(r"^\d{8}-\d{6}$")     # a single report botcore saved, not filed yet
# where everyone was at each attach_new call (wall clock): a report takes the places nearest its own save, not the
# filing tick's (a filing retried 3.7 s later stored the player mid-flight from a man cannon, 22 u off; Forge run Nov 6)
_SEEN = []


def _places_at(unix, snap):
    """{id: (x, y, z)} nearest the wall-clock second unix among the recent calls, else the snapshot's."""
    best = min(_SEEN, key=lambda e: abs(e[0] - unix), default=None)
    if best is not None and abs(best[0] - unix) <= 5.0:
        return best[1]
    return {p.id: (p.pos.x, p.pos.y, p.pos.z) for p in snap.players}


def _load(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def match_dir(trace_path, t0):
    """The match's folder: named after its recording (trace_<map>_<date>-<time>.jsonl -> <map>_<date>-<time>), or the
    brain's start time when it records nothing."""
    if trace_path:
        name = os.path.basename(trace_path)
        name = name[len("trace_"):] if name.startswith("trace_") else name
        return os.path.join(DIR, name.rsplit(".", 1)[0])
    return os.path.join(DIR, "unrecorded_" + time.strftime("%Y%m%d-%H%M%S", time.localtime(t0)))


def _file(folder, entry):
    path = os.path.join(folder, "reports.json")
    entries = _load(path, [])
    entries.append(entry)
    os.makedirs(folder, exist_ok=True)
    json.dump(entries, open(path, "w", encoding="utf-8"), indent=1)


def attach_new(t0, now, snap, map_name, trace, trace_path, bots, critic_path=None, mode=None, stations=None, oob=None):
    """Called by the brain about once a second: every report saved during this match goes into the match's folder with its
    moment (trace time), map and mode, everyone's place and the bots' goals; a marker line in the trace, and the match's
    one recording refreshed. bots: {player index: Bot}. mode: the match's mode as last read (the brain's snapshot is
    still the raw one at the call), else snap.mode. stations (brain/stations.py): the stations nearest the player go in
    the report ("near") and his note becomes a mark on the map's stations. Returns the stamps filed."""
    done = []
    folder = match_dir(trace_path, t0)
    _SEEN.append((time.time(), {p.id: (p.pos.x, p.pos.y, p.pos.z) for p in snap.players}))
    del _SEEN[:-12]
    for rep in sorted(glob.glob(os.path.join(DIR, "*", "report.json"))):
        single = os.path.dirname(rep)
        stamp = os.path.basename(single)
        if not STAMP.match(stamp):
            continue
        r = _load(rep)
        if not r or r.get("unix", 0) < t0 - 5:
            continue                                   # an older match's report (the brain was not running then)
        t = round(max(0.0, now - (time.time() - r["unix"])), 1)   # the match second it was saved at
        at_save = _places_at(r["unix"], snap)
        players = []
        for p in snap.players:
            b = bots.get(p.id)
            q = at_save.get(p.id, (p.pos.x, p.pos.y, p.pos.z))
            players.append(dict(id=p.id, name=p.name, team=p.team, bot=b is not None, alive=p.alive,
                                pos=[round(q[0], 2), round(q[1], 2), round(q[2], 2)], vehicle=p.vehicle,
                                weapon=p.weapon, carrying=p.has_flag,
                                goal=(b.goal[0], str(b.goal[1])[:60]) if b is not None else None,
                                order=(b.order.role, str(b.order.point)[:60]) if b is not None else None,
                                tier=b.p.tier if b is not None else None,
                                style=getattr(b.p, "personality", None) if b is not None else None))
        entry = dict(r, stamp=stamp, t=t, map=map_name, mode=mode or snap.mode, score=snap.score, players=players)
        me = next((p for p in snap.players if bots.get(p.id) is None and not getattr(p, "is_bot", False) and p.alive),
                  None)
        at = tuple(at_save.get(me.id, (me.pos.x, me.pos.y, me.pos.z))) if me is not None else None
        if stations is not None and me is not None:
            entry["near"] = stations.near(at)
            stations.mark(r.get("description", ""), at, stamp, t)
        if oob is not None and me is not None and oob.flag(r.get("description", ""), at, t):
            entry["out_of_bounds"] = True             # his note names it: a soft wall where he stood (brain/oob.py)
        if trace is not None:
            trace.write(json.dumps(dict(t=t, bug=stamp, text=r.get("description", ""))) + "\n")
            trace.flush()
        else:
            entry["note"] = ("LiDAR run: no match recording" if mode == "lidar" else
                             "no recording: logs/trace_on was missing")
        _file(folder, entry)
        if trace is not None:
            catch_up(trace_path, os.path.join(folder, "trace.jsonl"))   # the one copy, up to now
        _critique(folder, critic_path)
        shutil.rmtree(single, ignore_errors=True)
        done.append(stamp)
    return done


def catch_up(src, dst):
    """dst brought up to src: just what was added since is written (a whole copy at every report wrote 13 GB for 28
    reports of a 457 MB recording, Forge, and the brain stalled through each). src may have dropped its oldest minutes
    since (the recording limit, tools/recording.py): then what follows dst's last line in src, or src's rows after its
    time when that line is gone too. The copy only grows, so each report's moment stays in it. A dst with no line src
    has, nor a time, is copied whole."""
    import recording
    have = os.path.getsize(dst) if os.path.exists(dst) else 0
    size = os.path.getsize(src)
    with open(src, "rb") as f:
        at = 0 if not have else None
        if have:
            with open(dst, "rb") as d:
                d.seek(max(0, have - (1 << 20)))
                tail = d.read()
            last = tail[tail.rfind(b"\n", 0, len(tail) - 1) + 1:]      # its last line, as written
            if have <= size:
                f.seek(have - len(last))
                if f.read(len(last)) == last:
                    at = have                              # (src only grew)
            pos = size
            while at is None and pos > 0:                  # src trimmed: dst's last line in it, from the end
                lo = max(0, pos - (8 << 20))
                f.seek(lo)
                i = f.read(pos - lo + len(last)).rfind(last)
                if i >= 0:
                    at = lo + i + len(last)
                pos = lo
            if at is None:
                t = recording.line_t(last)
                if t is None:
                    shutil.copyfile(src, dst)
                    return
                at = recording.first_at(f, 0, size, t + 1e-6)
        with open(dst, "ab") as g:
            f.seek(at)
            shutil.copyfileobj(f, g, 1 << 20)


def _critique(folder, critic_path):
    """The AI director critic's notes on this match (brain/critic.py, faults named by docs/BAD_AI_BEHAVIORS.md IDs) next
    to the reports: critique.jsonl, and critique.md once the match is over."""
    if not critic_path:
        return
    for src, name in ((critic_path, "critique.jsonl"), (critic_path[:-6] + ".md", "critique.md")):
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(folder, name))


def finish(trace_path, critic_path=None):
    """At the match's end: the whole recording and the critic's notes into the match's folder (what happened after the
    last report)."""
    if not trace_path or not os.path.exists(trace_path):
        return
    folder = match_dir(trace_path, 0)
    if os.path.exists(os.path.join(folder, "reports.json")):
        catch_up(trace_path, os.path.join(folder, "trace.jsonl"))
        _critique(folder, critic_path)


def migrate():
    """Old reports (one folder each, attached.json + a full trace copy each) into their match folders: one recording
    per match (the biggest copy is the whole match), the reports listed. Returns the stamps moved."""
    moved = []
    for att in sorted(glob.glob(os.path.join(DIR, "*", "attached.json"))):
        single = os.path.dirname(att)
        a, r = _load(att, {}), _load(os.path.join(single, "report.json"), {})
        folder = match_dir(a.get("recording"), r.get("unix", 0))
        entry = dict(r, **{k: v for k, v in a.items() if k != "recording"})
        _file(folder, entry)
        old, new = os.path.join(single, "trace.jsonl"), os.path.join(folder, "trace.jsonl")
        if os.path.exists(old) and (not os.path.exists(new) or os.path.getsize(old) > os.path.getsize(new)):
            shutil.copyfile(old, new)
        shutil.rmtree(single, ignore_errors=True)
        moved.append(entry.get("stamp", os.path.basename(single)))
    return moved


def reports():
    """[(match folder name or None, report entry, has recording)], newest first; single reports not filed yet have
    no match (the brain was not running, or the game closed first)."""
    out = []
    for path in glob.glob(os.path.join(DIR, "*", "reports.json")):
        folder = os.path.dirname(path)
        rec = os.path.exists(os.path.join(folder, "trace.jsonl"))
        out += [(os.path.basename(folder), e, rec) for e in _load(path, [])]
    for rep in glob.glob(os.path.join(DIR, "*", "report.json")):
        if STAMP.match(os.path.basename(os.path.dirname(rep))):
            out.append((None, dict(_load(rep, {}), stamp=os.path.basename(os.path.dirname(rep))), False))
    return sorted(out, key=lambda x: x[1].get("unix", 0), reverse=True)


def critic_near(match, t, span=90.0):
    """The AI director critic's faults (with their docs/BAD_AI_BEHAVIORS.md IDs) from the critiques within span s of a
    report's moment, as lines: 't team bot verdict: ID what (instead: ...)'."""
    out = []
    path = os.path.join(DIR, match, "critique.jsonl")
    if not os.path.exists(path):
        return out
    for l in open(path, encoding="utf-8"):
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if r.get("kind") != "director" or abs(r.get("t", -1e9) - t) > span:
            continue
        for b in (r.get("answer") or {}).get("bots", []):
            for f in b.get("faults", []):
                out.append(f"{r['t']:.0f} s team {r.get('team')} {b.get('bot')} {b.get('verdict')}: "
                           f"{f.get('id', '?')} {f.get('what', '')} (instead: {f.get('instead', '')})")
    return out


def link(match, t, bot=None):
    q = f"?file=bug_reports/{match}/trace.jsonl&t={t}"
    return OBSERVER + q + (f"&bot={bot}" if bot is not None else "")


def main():
    a = sys.argv[1:]
    if "--migrate" in a:
        print("moved", migrate())
        return
    rows = reports()
    if not rows:
        print("no bug reports yet (logs/bug_reports)")
        return
    if a:
        rows = [x for x in rows if x[1].get("stamp", "").startswith(a[0])]
    shown = None
    for match, e, rec in rows:
        if match != shown:
            print(f"\n## {match or 'not filed (no match data)'}")
            shown = match
        print(f"== {e.get('stamp')}  {e.get('time', '?')}  ({e.get('how', '?')})")
        print(f"   \"{e.get('description', '').strip()}\"")
        if match is None:
            continue
        print(f"   {e.get('map')}  mode {e.get('mode')}  score {e.get('score')}  at {e.get('t')} s into the match")
        if rec:
            print(f"   Observer: {link(match, e.get('t'))}")
        if a:
            for line in critic_near(match, e.get("t") or 0):
                print("   critic: " + line)
            for p in e.get("players", []):
                who = f"bot {p['id']} {p.get('tier') or ''} {p.get('style') or ''}" if p["bot"] else f"person {p['id']}"
                print(f"     {who:28s} {p['name']:16s} team {p['team']} {'alive' if p['alive'] else 'dead '} "
                      f"at {p['pos']} {('goal ' + ' '.join(p['goal'])) if p.get('goal') else ''}"
                      f"{('  order ' + p['order'][0]) if p.get('order') else ''}")


if __name__ == "__main__":
    main()
