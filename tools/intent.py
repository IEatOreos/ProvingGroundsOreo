"""Engagement intent: a person vs the bots by tier, from game memory only (Data collector files or traces; no keys).
Every player gets the same measures at 10 samples a second (traces: their 4):
  contact     an episode with one enemy: he comes into my view + line of sight after 1 s unseen; it ends when either
              dies or he is unseen 5 s
  hit_t       episode start -> my first hit on him (his shield+body drops while my aim is on him and no team-mate's is)
  shot_t      episode start -> my first shot (person: magazine; bot: the trace's trigger), when known
  close/hold/back  share of in-view time my own velocity toward him is > +1 / within 1 / < -1 u/s
  disengage   episodes ending unseen with both alive: did I back off (moved away > 1 u/s over the next 3 s), hold, or
              chase; my vitals (share of my full) when I backed off
  pop_push    his shield pops (> 0.1 -> ~0) while I see him: my speed toward him the next 2 s, share of it in view
  kill_push   an enemy dies within 20 u of me: my speed toward the nearest living enemy the next 3 s (minus my mean)
  repeek      I lose sight of him inside an episode: time until I see him again; chase = toward where he was, 2 s
  chase_hurt  the same when he was under half health: speed toward his last seen spot, re-seen within 3 s
  melee       share of episodes that come inside 1.5 u
  idle_known  share of my alive on-foot time standing (< 0.5 u/s) with an enemy seen in the last 3 s but not now
Made to measure how hard Legendary bots press their fights next to a skilled player (docs/HANDOFF.md has the
numbers). Tiers come from the match's trace (logs/, logs/verify/traces, logs/bug_reports/<map>_<stamp>/),
else its fluidity report, else --tiers.

usage: python -I intent.py <collect or trace> [...] [--tiers id=Tier,..]   pooled table by tier (person = "you")
"""
import collections
import glob
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)
import player_stats as ps  # noqa: E402

_orig = ps.companion_trace


def companion(path):
    hit = _orig(path)
    if hit:
        return hit
    m = re.search(r"_(\d{8}-\d{6})\.jsonl$", path)
    if not m or os.path.basename(path).startswith("trace_"):
        return None
    hits = glob.glob(os.path.join(ROOT, "logs", "bug_reports", f"*_{m.group(1)}", "trace.jsonl"))
    return hits[0] if hits else None


ps.companion_trace = companion
X, Y, Z, SH, HP, ALIVE, RIDE = ps.X, ps.Y, ps.Z, ps.SH, ps.HP, ps.ALIVE, ps.RIDE


def tiers_for(path, m):
    """id -> tier: the trace's meta, else the match's fluidity report."""
    out = {i: ps.TIER_NAME.get(b.get("tier"), b.get("tier")) for i, b in m.meta.items()}
    stem = os.path.basename(path)[8:-6] if os.path.basename(path).startswith("collect_") else None
    fl = os.path.join(ROOT, "logs", f"fluidity_{stem}.json") if stem else None
    if fl and os.path.exists(fl):
        for r in json.load(open(fl))["rows"]:
            if r["bot"] and r["tier"] not in ("?", ""):
                out.setdefault(r["id"], r["tier"])
    return out


def measure(path, tier_over=None):
    m = ps.Match(path)
    tiers = tiers_for(path, m)
    tiers.update(tier_over or {})
    step = 3 if m.dt < 0.1 else 1
    idx = np.arange(0, m.n, step)
    tt = m.t[idx]
    dt = float(np.median(np.diff(tt)))
    pos = {i: m.P[i][idx][:, [X, Y, Z]] for i in m.ids}
    al = {i: m.alive[i][idx] for i in m.ids}
    foot = {i: al[i] & (np.nan_to_num(m.P[i][idx, RIDE]) == 0) for i in m.ids}
    vit = {}
    for i in m.ids:
        v = np.nan_to_num(m.P[i][idx, SH]) + np.nan_to_num(m.P[i][idx, HP])
        full = np.percentile(v[al[i]], 99) if al[i].any() else 1.0
        vit[i] = v / max(full, 1e-3)
    shield = {i: np.nan_to_num(m.P[i][idx, SH]) for i in m.ids}
    vel = {}
    for i in m.ids:
        p = pos[i]
        v = np.zeros_like(p)
        v[1:-1] = (p[2:] - p[:-2]) / (2 * dt)
        ok = foot[i].copy()
        ok[1:-1] &= foot[i][2:] & foot[i][:-2]
        ok[[0, -1]] = False
        v[~ok] = np.nan
        v[np.hypot(v[:, 0], v[:, 1]) > 15] = np.nan
        vel[i] = v
    P = {}
    for me in m.ids:
        for foe in m.enemies(me):
            P[(me, foe)] = m.pair(me, foe, step)

    def toward(me, k, tgt):
        """My own speed toward point tgt at sample k (u/s; nan when unknown)."""
        d = tgt[:2] - pos[me][k, :2]
        n = np.hypot(*d)
        if n < 0.3 or np.isnan(vel[me][k, 0]):
            return np.nan
        return float(vel[me][k, :2] @ (d / n))

    fire = {i: m.fire[i][idx] for i in m.fire}
    res = {}
    for me in m.ids:
        tier = "you" if not m.bot[me] else tiers.get(me, "?")
        r = collections.defaultdict(list)
        mates = [j for j in m.ids if j != me and m.team[j] == m.team[me]]
        known = np.zeros(len(idx), bool)
        inview = np.zeros(len(idx), bool)
        for foe in m.enemies(me):
            _, d, vis, aim, body = P[(me, foe)]
            inview |= vis
            last = None
            for k in np.nonzero(vis)[0]:
                known[k:k + int(3 / dt) + 1] = True
            others = np.zeros(len(idx), bool)
            for j in mates:
                if (j, foe) in P:
                    others |= P[(j, foe)][3]
            hv = vit[foe]
            drop = np.r_[False, (hv[:-1] - hv[1:] > 0.02) & al[foe][:-1] & al[foe][1:]]
            mine_hit = drop & (aim | np.r_[False, aim[:-1]]) & ~others
            # episodes
            k, nn = 0, len(idx)
            vis_idx = np.nonzero(vis)[0]
            prev_seen = -1e9
            j0 = 0
            while j0 < len(vis_idx):
                s0 = vis_idx[j0]
                if tt[s0] - prev_seen <= ps.NEW_AFTER:
                    prev_seen = tt[s0]
                    j0 += 1
                    continue
                # walk the episode
                e = s0
                last_seen = s0
                ended = "lost"
                gaps = []
                gap_start = None
                while e + 1 < nn:
                    e += 1
                    if not (al[me][e] and al[foe][e]):
                        ended = "me_dead" if not al[me][e] else "foe_dead"
                        break
                    if vis[e]:
                        if gap_start is not None:
                            gaps.append((gap_start, e))
                            gap_start = None
                        last_seen = e
                    else:
                        if gap_start is None:
                            gap_start = e
                        if tt[e] - tt[last_seen] > 5.0:
                            break
                if gap_start is not None and ended == "lost":
                    gaps.append((gap_start, None))
                seg = np.arange(s0, last_seen + 1)
                r["episodes"].append(1)
                # first hit / shot
                h = np.nonzero(mine_hit[s0:min(e, s0 + int(5 / dt)) + 1])[0]
                r["hit_t"].append(float(h[0] * dt) if len(h) else None)
                if me in fire:
                    f = np.nonzero(fire[me][s0:min(nn, s0 + int(3 / dt) + 1)])[0]
                    r["shot_t"].append(float(f[0] * dt) if len(f) else None)
                # closing while in view
                for q in seg[vis[seg]]:
                    v = toward(me, q, pos[foe][q])
                    if not np.isnan(v):
                        r["tow"].append(v)
                r["min_d"].append(float(np.nanmin(d[seg])))
                r["ended"].append(ended)
                # disengage
                if ended == "lost":
                    q1 = last_seen
                    q2 = min(nn - 1, q1 + int(3 / dt))
                    if q2 > q1 and al[me][q2] and al[foe][q2]:
                        away = pos[me][q2, :2] - pos[me][q1, :2]
                        u = pos[me][q1, :2] - pos[foe][q1, :2]
                        un = np.hypot(*u)
                        if un > 0.3:
                            sp = float(away @ (u / un)) / (tt[q2] - tt[q1])
                            kind = "back" if sp > 1.0 else "chase" if sp < -1.0 else "hold"
                            r["dis"].append(kind)
                            r["dis_vit"].append((kind, float(vit[me][q1]), float(vit[foe][q1])))
                # gaps inside the episode: re-peek
                for g0, g1 in gaps:
                    if g1 is None and ended != "lost":
                        continue
                    wait = (tt[g1] - tt[g0]) if g1 is not None else None
                    if g1 is None:
                        continue                  # the end of a lost episode is a disengage, counted above
                    r["repeek"].append(float(wait))
                    spot = pos[foe][g0 - 1]
                    ws = [toward(me, q, spot) for q in range(g0, min(g1, g0 + int(2 / dt)))]
                    ws = [w for w in ws if not np.isnan(w)]
                    if ws:
                        r["gap_tow"].append(float(np.mean(ws)))
                    if vit[foe][g0 - 1] < 0.5:
                        r["hurt_seen3"].append(wait <= 3.0)
                        if ws:
                            r["hurt_tow"].append(float(np.mean(ws)))
                # a lost episode on a hurt foe: did I go after him
                if ended == "lost" and vit[foe][last_seen] < 0.5:
                    r["hurt_seen3"].append(False)
                    after = range(last_seen + 1, min(nn, last_seen + 1 + int(2 / dt)))
                    ws = [toward(me, q, pos[foe][last_seen]) for q in after]
                    ws = [w for w in ws if not np.isnan(w)]
                    if ws:
                        r["hurt_tow"].append(float(np.mean(ws)))
                prev_seen = tt[last_seen]
                while j0 < len(vis_idx) and vis_idx[j0] <= last_seen:
                    j0 += 1
            # shield pops while I see him
            sh = shield[foe]
            for q in np.nonzero((sh[:-1] > 0.1) & (sh[1:] <= 0.02) & al[foe][1:])[0] + 1:
                if not vis[max(0, q - int(0.5 / dt)):q + 1].any() or d[q] > 30 or not al[me][q]:
                    continue
                q2 = min(len(idx), q + int(2 / dt))
                ws = [toward(me, z, pos[foe][z]) for z in range(q, q2) if al[me][z] and al[foe][z]]
                ws = [w for w in ws if not np.isnan(w)]
                if ws:
                    r["pop_tow"].append(float(np.mean(ws)))
                r["pop_vis"].append(float(vis[q:q2].mean()))
                fd = np.nonzero(~al[foe][q:min(len(idx), q + int(3 / dt))])[0]
                r["pop_kill3"].append(bool(len(fd)))
        # kill push
        foes = m.enemies(me)
        nearest_tow = []
        for k in range(1, len(idx)):
            if not foot[me][k]:
                continue
            live = [f for f in foes if al[f][k]]
            if not live:
                continue
            f = min(live, key=lambda f: np.hypot(*(pos[f][k, :2] - pos[me][k, :2])))
            v = toward(me, k, pos[f][k])
            nearest_tow.append(v)
        base = float(np.nanmean(nearest_tow)) if nearest_tow else 0.0
        for foe in foes:
            for q in np.nonzero(al[foe][:-1] & ~al[foe][1:])[0] + 1:
                if not al[me][q] or np.hypot(*(pos[foe][q - 1, :2] - pos[me][q, :2])) > 20:
                    continue
                ws = []
                for z in range(q, min(len(idx), q + int(3 / dt))):
                    live = [f for f in foes if al[f][z]]
                    if not live or not al[me][z]:
                        continue
                    f = min(live, key=lambda f: np.hypot(*(pos[f][z, :2] - pos[me][z, :2])))
                    w = toward(me, z, pos[f][z])
                    if not np.isnan(w):
                        ws.append(w)
                if ws:
                    r["kill_push"].append(float(np.mean(ws)) - base)
        sp = np.hypot(vel[me][:, 0], vel[me][:, 1])
        okf = foot[me] & ~np.isnan(sp)
        idle = okf & (sp < 0.5) & known & ~inview
        r["idle_known"] = [float(idle.sum() / max(okf.sum(), 1))]
        r["stand_inview"] = [float((okf & (sp < 0.5) & inview).sum() / max((okf & inview).sum(), 1))]
        r["alive_min"] = [float(al[me].sum() * dt / 60)]
        res[str(me)] = dict(tier=tier, bot=m.bot[me], team=m.team[me], r=dict(r))
    return dict(file=os.path.basename(path), map=m.map, game=m.game, rate=1 / dt, players=res)


ORDER = ["you", "Legendary", "Heroic", "Normal", "Easy"]


def med(v):
    v = [x for x in v if x is not None]
    return f"{np.median(v):.2f}" if v else "-"


def share(v, f):
    v = [x for x in v if x is not None]
    return f"{100 * sum(map(f, v)) / len(v):.0f}%" if v else "-"


def row(r):
    tow = r["tow"]
    dis = r["dis"]
    dv = [v for k, v, _ in r["dis_vit"] if k == "back"]
    eps = len(r["episodes"])
    alive = sum(r["alive_min"])
    return [
        f"{eps}", f"{eps / alive:.1f}" if alive else "-",
        med(r["hit_t"]), share(r["hit_t"], lambda x: x <= 1.5) if r["hit_t"] else "-",
        med(r["shot_t"]),
        share(tow, lambda v: v > 1.0), share(tow, lambda v: abs(v) <= 1.0), share(tow, lambda v: v < -1.0),
        f"{np.mean(tow):+.2f}" if tow else "-",
        share(dis, lambda k: k == "back"), share(dis, lambda k: k == "chase"), med(dv), share(dv, lambda v: v >= 0.75),
        med(r["pop_tow"]), med(r["pop_vis"]), share(r["pop_kill3"], bool), f"{len(r['pop_tow'])}",
        med(r["kill_push"]),
        med(r["repeek"]), share(r["repeek"], lambda x: x <= 1.5), med(r["gap_tow"]),
        share(r["hurt_seen3"], bool), med(r["hurt_tow"]),
        share(r["min_d"], lambda x: x < 1.5),
        f"{100 * np.average(r['idle_known'], weights=r['alive_min']):.1f}%",
        f"{100 * np.average(r['stand_inview'], weights=r['alive_min']):.0f}%",
    ]


HEAD = ["ep", "ep/min", "hit_t", "hit<=1.5", "shot_t", "close", "hold", "back", "tow", "dis_back", "dis_chase",
        "back_vit", "back@>=75%", "pop_tow", "pop_vis", "pop_kill3", "pops", "kill_push", "repeek", "repeek<=1.5",
        "gap_tow", "hurt_reseen3", "hurt_tow", "melee_ep", "idle_known", "stand_inview"]


def main():
    args = sys.argv[1:]
    over = {}
    if "--tiers" in args:
        k = args.index("--tiers")
        for kv in args[k + 1].split(","):
            a, b = kv.split("=")
            over[int(a)] = b
        del args[k:k + 2]
    if not args:
        raise SystemExit(__doc__)
    pool = collections.defaultdict(lambda: collections.defaultdict(list))
    for path in args:
        out = measure(path, over)
        for p in out["players"].values():
            if p["tier"] == "you" and sum(p["r"].get("alive_min", [0])) < 1:
                continue                          # (a host who only watched)
            for k, v in p["r"].items():
                pool[p["tier"]][k] += v
    print("| tier | " + " | ".join(HEAD) + " |")
    for t in sorted(pool, key=lambda t: ORDER.index(t) if t in ORDER else 9):
        print(f"| {t} | " + " | ".join(row(collections.defaultdict(list, pool[t]))) + " |")


if __name__ == "__main__":
    main()
