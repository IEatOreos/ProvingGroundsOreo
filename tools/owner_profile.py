"""Play like the owner (custom): the owner's habits per map, from his recorded matches.

Scans logs/trace_<map>_<stamp>.jsonl with its .carnage.xml and keeps only matches the person played: his own kills in
the game's carnage report above --min-kills (default 1: a match he spectated, 0 kills, is left out). From the trace's
world rows (4 a second: everyone's position, aim, shield, health, who is in whose sights) it measures, per map:

- spots: where he stood when he got his kills (clustered within SPOT_R), with his kills, deaths and time there, his
  visits and how long each lasted, and how high over his victims he was
- engagements: distance, height over the victim, the victim's state when he started on him (aiming at nobody, at him,
  at someone else; who had whom in sights first), time to kill
- fights (an enemy in his sights 0.5 s or more, held through 0.5 s gaps): won, lost, broken off; the health+shield he
  started them at and broke them off at
- disengage: the health+shield (0-2) at which he broke off fights he was losing ground in, and lived

and writes maps/<map>/owner_profile.json (or --out DIR). Measures as tools' fight reports: "in his sights" is the
trace's chest pick or the aim within the same window of the head; kills are attributed to the enemy with the victim in
his sights (approximate, a little high: steals count), the counts beside them are the game's own.

usage: python -I tools/owner_profile.py [--player NAME] [--min-kills 1] [--maps reach_30_settlement ...] [--dry]
"""
import argparse
import bisect
import collections
import datetime
import glob
import json
import math
import os
import re
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LOGS = os.path.join(ROOT, "logs")
# each match read is kept here as a summary (tools/recording.py rotates only trace_/collect_/critique_ files): the
# profile keeps every match it ever read after the recording itself is gone (5 unsaved games by default)
CACHE = os.path.join(LOGS, "owner_profile")
SPOT_R = 3.5          # u: kills this near each other were got from one spot
GAP = 0.5             # s: a fight's target is held through sight-test gaps this long (4 samples a second)
TOP_SPOTS = 8


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def carnage(path):
    """[(name, team, kills, deaths, is_matchmaking-free row)] from a carnage report."""
    x = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<Player [^>]*mGamertagText="([^"]*)"[^>]*mTeamId="(\d+)"[^>]*mKills="(\d+)" mDeaths="(\d+)"', x):
        out.append((m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))))
    gt = re.search(r'GameTypeName="([^"]*)"', x)
    return out, gt.group(1) if gt else ""


def read_trace(path):
    """(map name, {bot id: name}, [(t, {id: world row})])."""
    names, rows, map_name = {}, [], None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if '"meta"' in line[:40]:
                m = json.loads(line)["meta"]
                map_name = map_name or m.get("map")
                names[m["bot"]["id"]] = m["bot"]["name"]
            elif '"world"' in line:
                r = json.loads(line)
                rows.append((r["t"], {w[0]: w for w in r["world"]}))
    return map_name, names, rows


def off(p, e, h):
    dx, dy, dz = e[3] - p[3], e[4] - p[4], (e[5] + h) - (p[5] + 0.62)
    return math.hypot(wrap(math.atan2(dy, dx) - p[10]), math.atan2(dz, math.hypot(dx, dy)) - p[11]), math.hypot(dx, dy)


def sights(p, W):
    """The enemy in p's sights: the trace's chest pick, else the enemy whose head is within the same window."""
    if not p or not p[2]:
        return -1
    if len(p) > 14 and p[14] not in (-1, None):
        return p[14]
    best, bo = -1, 9.0
    for e in W.values():
        if e[1] == p[1] or not e[2] or e[0] == p[0]:
            continue
        o, d = off(p, e, 0.62)
        if d < 80 and o < max(0.12, math.atan2(0.6, max(d, 0.1))) and o < bo:
            best, bo = e[0], o
    return best


def analyse(rows, me):
    """One match: the person `me`'s kills, deaths, fights and positions."""
    T = [t for t, _ in rows]

    def dead_between(i, t0, t1):
        for k in range(bisect.bisect_left(T, t0), bisect.bisect_right(T, t1)):
            w = rows[k][1].get(i)
            if w and not w[2]:
                return T[k]
        return None

    kills, deaths = [], []
    for k in range(1, len(rows)):
        t, W = rows[k]
        W0 = rows[k - 1][1]
        for i, v in W.items():
            p = W0.get(i)
            if not (p and p[2] and not v[2]):
                continue
            cands = [e for e in W0.values() if e[1] != p[1] and e[2]]
            kl = next((e for e in cands if sights(e, W0) == i), None)
            if kl is None:
                best = min(cands, key=lambda e: off(e, p, 0.35)[0], default=None)
                kl = best if best is not None and off(best, p, 0.35)[0] < 0.25 else None
            if i == me:
                deaths.append(dict(t=t, pos=p[3:6], killer=kl[0] if kl else None))
            if kl is None or kl[0] != me:
                continue
            # the engagement: back from the kill while he kept the victim in sights (gaps under 1.5 s)
            start, last, vic_hp, vic_aim, first = t, t, None, None, False
            for m in range(k - 1, -1, -1):
                tm, Wm = rows[m]
                if t - tm > 12:
                    break
                e, v2 = Wm.get(me), Wm.get(i)
                if not (e and v2 and e[2] and v2[2]):
                    break
                if sights(e, Wm) == i:
                    start = last = tm
                    vic_hp, vic_aim = v2[6] + v2[7], sights(v2, Wm)
                elif last - tm > 1.5:
                    break
            for m in range(k - 1, -1, -1):
                tm, Wm = rows[m]
                if tm < start - 3:
                    break
                if tm < start and sights(Wm.get(i), Wm) == me:
                    first = True
            e = W0[me]
            kills.append(dict(t=t, pos=e[3:6], dist=math.dist(e[3:6], p[3:6]), dz=e[5] - p[5], ttk=t - start,
                              vic_hp=vic_hp, vic_aim=("nobody" if vic_aim in (-1, None) else "you" if vic_aim == me
                                                      else "other"), saw_first=first, hp_left=e[6] + e[7]))
    fights, cur = [], None
    for t, W in rows:
        w = W.get(me)
        tgt = sights(w, W) if w else -1
        if cur and (not (w and w[2]) or (tgt not in (-1, None) and tgt != cur["tgt"])
                    or (tgt in (-1, None) and t - cur["seen"] > GAP)):
            if cur["seen"] - cur["t0"] >= 0.5:
                fights.append(cur)
            cur = None
        if w and w[2] and tgt not in (-1, None):
            if cur is None:
                cur = dict(tgt=tgt, t0=t, seen=t, hp0=w[6] + w[7], hp1=w[6] + w[7], minhp=w[6] + w[7])
            cur["seen"], cur["hp1"] = t, w[6] + w[7]
            cur["minhp"] = min(cur["minhp"], w[6] + w[7])
    for f in fights:
        me_d = dead_between(me, f["t0"], f["seen"] + 1.0)
        him_d = dead_between(f["tgt"], f["t0"], f["seen"] + 1.5)
        f["result"] = "lost" if me_d and (not him_d or me_d <= him_d) else "won" if him_d else "broke off"
    track, last = [], -9.0
    for t, W in rows:                       # where he was, once a second (spot time and visits)
        if me in W and t - last >= 1.0:
            track.append((round(t, 2), [round(v, 2) for v in W[me][3:6]], bool(W[me][2])))
            last = t
    return kills, deaths, fights, track, (T[-1] - T[0]) / 60 if T else 0.0


def cached(tr):
    """The kept summary of trace tr (still current: same size and time), else None."""
    path = os.path.join(CACHE, os.path.basename(tr)[:-len(".jsonl")] + ".json")
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    st_ = os.stat(tr)
    return d if d.get("size") == st_.st_size and d.get("mtime") == int(st_.st_mtime) else None


def keep(tr, map_name, info, a):
    os.makedirs(CACHE, exist_ok=True)
    st_ = os.stat(tr)
    d = dict(map=map_name, info=info, size=st_.st_size, mtime=int(st_.st_mtime),
             kills=a[0], deaths=a[1], fights=a[2], track=a[3], minutes=a[4])
    json.dump(d, open(os.path.join(CACHE, os.path.basename(tr)[:-len(".jsonl")] + ".json"), "w", encoding="utf-8"))


def unpack(d):
    return d["map"], d["info"], (d["kills"], d["deaths"], d["fights"], [tuple(x) for x in d["track"]], d["minutes"])


def cluster(points, r=SPOT_R):
    """Greedy clusters of (x, y, z) points: [(centre, [indices])], biggest first."""
    left = list(range(len(points)))
    out = []
    while left:
        best = max(left, key=lambda i: sum(1 for j in left if math.dist(points[i], points[j]) < r))
        members = [j for j in left if math.dist(points[best], points[j]) < r]
        centre = [round(st.median(points[j][c] for j in members), 2) for c in range(3)]
        out.append((centre, members))
        left = [j for j in left if j not in members]
    return out


def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def med(v):
    v = [x for x in v if x is not None]
    return round(st.median(v), 2) if v else None


def profile(matches):
    """The per-map profile from [(match info, analysis)]."""
    kills = [k for _, a in matches for k in a[0]]
    deaths = [d for _, a in matches for d in a[1]]
    fights = [f for _, a in matches for f in a[2]]
    minutes = sum(a[4] for _, a in matches)
    res = collections.Counter(f["result"] for f in fights)
    broke = [f for f in fights if f["result"] == "broke off"]
    losing = [f for f in broke if f["minhp"] < f["hp0"] - 0.2]
    spots = []
    for centre, members in cluster([k["pos"] for k in kills])[:TOP_SPOTS]:
        ks = [kills[j] for j in members]
        there, visits, run = 0.0, [], None
        for info, a in matches:
            track = a[3]
            for (t0, p0, al0), (t1, _, _) in zip(track, track[1:]):
                near = al0 and math.dist(p0, centre) < SPOT_R
                if near:
                    there += t1 - t0
                    run = (run[0] if run else t0, t1)
                elif run:
                    visits.append(run[1] - run[0])
                    run = None
            if run:
                visits.append(run[1] - run[0])
                run = None
        spots.append(dict(pos=centre, kills=len(ks), deaths=sum(1 for d in deaths if math.dist(d["pos"], centre) < SPOT_R),
                          minutes=round(there / 60, 2), visits=len(visits), median_visit_s=med(visits),
                          kills_per_min=round(len(ks) / (there / 60), 2) if there > 30 else None,
                          over_victim=med(k["dz"] for k in ks), distance=med(k["dist"] for k in ks)))
    return dict(
        matches=[m for m, _ in matches], minutes=round(minutes, 1),
        kills=dict(game=sum(m["kills"] for m, _ in matches), found=len(kills)),
        deaths=sum(m["deaths"] for m, _ in matches),
        engage=dict(distance=med(k["dist"] for k in kills), over_victim=med(k["dz"] for k in kills),
                    above_victim_pct=pct(sum(k["dz"] > 1.0 for k in kills), len(kills)),
                    victim_aiming=dict(nobody=pct(sum(k["vic_aim"] == "nobody" for k in kills), len(kills)),
                                       at_you=pct(sum(k["vic_aim"] == "you" for k in kills), len(kills)),
                                       at_other=pct(sum(k["vic_aim"] == "other" for k in kills), len(kills))),
                    victim_saw_you_first_pct=pct(sum(k["saw_first"] for k in kills), len(kills)),
                    victim_hp_at_start=med(k["vic_hp"] for k in kills), time_to_kill_s=med(k["ttk"] for k in kills),
                    your_hp_left=med(k["hp_left"] for k in kills)),
        fights=dict(count=len(fights), won_pct=pct(res["won"], len(fights)), lost_pct=pct(res["lost"], len(fights)),
                    broke_off_pct=pct(res["broke off"], len(fights)),
                    started_full_pct=pct(sum(f["hp0"] >= 1.9 for f in fights), len(fights)),
                    median_hp_at_start=med(f["hp0"] for f in fights)),
        disengage=dict(fights_backed_out_of=len(losing), median_hp_when_you_left=med(f["hp1"] for f in losing),
                       median_hp_lost_before_leaving=med(f["hp0"] - f["hp1"] for f in losing)),
        spots=spots)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--player", help="the person's gamertag (default: the one human in each carnage report)")
    ap.add_argument("--min-kills", type=int, default=1, help="leave out matches where he got fewer kills (spectating)")
    ap.add_argument("--maps", nargs="*", help="only these maps")
    ap.add_argument("--out", help="write <out>/<map>.json instead of maps/<map>/owner_profile.json")
    ap.add_argument("--dry", action="store_true", help="print, write nothing")
    o = ap.parse_args()
    per_map = collections.defaultdict(list)
    skipped = []
    seen = set()

    def take(map_name, info, a, how):
        if o.maps and map_name not in o.maps:
            return
        if o.player is not None and info["player"] != o.player:
            return
        if info["kills"] < o.min_kills:
            skipped.append((info["trace"], f"{info['player']} {info['kills']} kills: spectating"))
            return
        per_map[map_name].append((info, a))
        print(f"  {info['trace']}: {info['player']} {info['kills']}-{info['deaths']} ({info['gametype']}, "
              f"{info['minutes']} min traced{how})", flush=True)

    for tr in sorted(glob.glob(os.path.join(LOGS, "trace_*.jsonl"))):
        cr = tr[:-len(".jsonl")] + ".carnage.xml"
        if not os.path.exists(cr):
            skipped.append((os.path.basename(tr), "no carnage report"))
            continue
        seen.add(os.path.basename(tr))
        c = cached(tr)
        if c is not None:
            take(*unpack(c), "")
            continue
        players, gametype = carnage(cr)
        map_name, names, rows = read_trace(tr)
        if not rows or map_name is None:
            continue
        humans = [p for p in players if p[0] not in names.values() and (o.player is None or p[0] == o.player)]
        if len(humans) != 1:
            skipped.append((os.path.basename(tr), f"{len(humans)} matching people"))
            continue
        name, team, k, d = humans[0]
        ids = {i for _, W in rows for i, w in W.items() if not w[8]}
        if len(ids) != 1:
            skipped.append((os.path.basename(tr), f"{len(ids)} people in the trace"))
            continue
        a = analyse(rows, ids.pop())
        info = dict(trace=os.path.basename(tr), gametype=gametype, player=name, kills=k, deaths=d, minutes=round(a[4], 1))
        if not o.dry:
            keep(tr, map_name, info, a)
        take(map_name, info, a, "")
    for f in sorted(glob.glob(os.path.join(CACHE, "trace_*.json"))):
        if os.path.basename(f)[:-len(".json")] + ".jsonl" in seen:
            continue
        try:
            take(*unpack(json.load(open(f, encoding="utf-8"))), "; recording gone, kept summary")
        except (OSError, ValueError, KeyError):
            skipped.append((os.path.basename(f), "unreadable summary"))
    for tr, why in skipped:
        print(f"  skipped {tr}: {why}")
    for map_name, matches in sorted(per_map.items()):
        prof = dict(map=map_name, player=matches[0][0]["player"], generated=datetime.date.today().isoformat(),
                    tool="tools/owner_profile.py", **profile(matches))
        e, f, g = prof["engage"], prof["fights"], prof["disengage"]
        print(f"\n== {map_name}: {len(matches)} match(es), {prof['minutes']} min, {prof['kills']['game']}-{prof['deaths']}")
        print(f"   fights {f['count']}: won {f['won_pct']}%, lost {f['lost_pct']}%, broke off {f['broke_off_pct']}%; "
              f"started at full {f['started_full_pct']}%")
        print(f"   kills: {e['distance']} u away, {e['over_victim']} u above (above in {e['above_victim_pct']}%), victims "
              f"aiming at nobody {e['victim_aiming']['nobody']}%, saw you first {e['victim_saw_you_first_pct']}%, "
              f"{e['time_to_kill_s']} s to kill")
        print(f"   backed out of {g['fights_backed_out_of']} losing fights at health+shield {g['median_hp_when_you_left']} "
              f"(after losing {g['median_hp_lost_before_leaving']})")
        for k_, s in enumerate(prof["spots"], 1):
            print(f"   spot {k_}: {s['pos']} kills {s['kills']}, deaths {s['deaths']}, {s['minutes']} min over "
                  f"{s['visits']} visits (median {s['median_visit_s']} s), {s['distance']} u shots, {s['over_victim']} u above")
        if o.dry:
            continue
        out = os.path.join(o.out, f"{map_name}.json") if o.out else os.path.join(ROOT, "maps", map_name, "owner_profile.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump(prof, open(out, "w"), indent=1)
        print(f"   -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
