"""Your numbers from a match, for the Observer, with the same measures for every bot in it, so you and the Legendary
bots line up side by side.

Input: a Data collector file (logs/collect_<map>_<stamp>.jsonl, tools/collector.py: everyone 30 times a second, your
guns, rounds and equipment) or, for older matches, a brain trace (its world lines: everyone 4 times a second). Your
shots are told by your magazine going down; no keys are read.
The match's trace (same stamp) gives the bots' names, difficulty and trigger. Measures, for every player:

- reaction: an enemy comes into view (line of sight, inside a 105 degree view: the player's MCC setting) after 1 s
  unseen; the time until the aim is on him (brain/tracefmt.py's in-sights rule) and, for you, until the first shot.
  Already aimed there when he appears: "pre-aimed". No aim on him within 3 s: not counted.
- reaction to being shot: shields start dropping after 2 s untouched; the time until the aim is on an enemy.
- pace: engagements (aim on an enemy, firing or being hit; closer than 3 s apart = one) per minute alive, their
  length and the time between them, time from a spawn to the first; speed, time standing, jumps, strafe in fights.
- positioning: time per callout zone, fight distance, height over the man fought, the first look (who got the aim on
  the other first when two players saw each other), how much of the time an enemy had you in view.
- accuracy: the share of trigger time on the body; damage dealt (a full shield and body = 2.0); kills; for you, by
  gun; with the gun's rounds known (CE, Halo 2, Halo 3), shots too.
- guns and equipment (you): time per gun, switches, pickups, shots; ability uses, when and for how long.

usage: python -I player_stats.py <collect or trace file> [player id]      prints the report
"""
import collections
import glob
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

EYE, AIM_Z = 0.62, 0.35                 # eye over the feet; where an aim counts (brain/tracefmt.py sights)
HFOV = math.radians(105.0)              # the player's MCC field of view (GameUserSettings.ini FOVSetting)
VFOV = 2 * math.atan(math.tan(HFOV / 2) * 9 / 16)
NEW_AFTER, REACT_MAX, GAP = 1.0, 3.0, 3.0
TEAM, ALIVE, X, Y, Z, YAW, PITCH, SH, HP, RIDE, FLAG, BOT = range(12)
TIER_NAME = {"novice": "Easy", "average": "Normal", "strong": "Heroic", "top": "Legendary"}


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def load(path):
    """dict(kind, map, game, t [n], P {id: array [n, 12], nan where absent}, gear [...], meta, cmds). Key rows of
    files from before 0.2.0 are skipped."""
    lines = open(path, encoding="utf-8").read().splitlines()
    head, ts, raw, gear, meta, cmds = {}, [], [], [], {}, collections.defaultdict(list)
    for k, x in enumerate(lines):
        try:
            d = json.loads(x)
        except ValueError:
            if k == len(lines) - 1:
                break                                 # a line still being written
            raise
        if "collect" in d:
            head = d
        elif "p" in d:
            ts.append(d["t"])
            raw.append(d["p"])
        elif "world" in d:                            # a trace: [id, team, alive, x, y, z, sh, hp, bot, flag, yaw, pitch, ..]
            ts.append(d["t"])
            raw.append([[r[0], r[1], r[2], r[3], r[4], r[5], r[10], r[11], r[6], r[7], 0, r[9], r[8]] for r in d["world"]])
        elif "meta" in d and d["meta"].get("bot"):
            head.setdefault("map", d["meta"].get("map"))
            head.setdefault("game", d["meta"].get("game"))
            meta[d["meta"]["bot"]["id"]] = d["meta"]["bot"]
        elif "wpn" in d and "id" in d and "cmd" not in d:
            gear.append(d)
        elif "cmd" in d:                              # a trace's bot line: its trigger this tick
            cmds[d["id"]].append((d["t"], d["cmd"][3] & 1))
    t = np.array(ts)
    ids = sorted({r[0] for rows in raw for r in rows})
    P = {i: np.full((len(t), 12), np.nan) for i in ids}
    for k, rows in enumerate(raw):
        for r in rows:
            P[r[0]][k] = r[1:13]                      # (people's rows go on: crosshair, ride)
    return dict(kind="collect" if "collect" in head else "trace", map=head.get("map"), game=head.get("game"), t=t,
                P=P, gear=gear, meta=meta, cmds=cmds)


def companion_trace(path):
    """The brain's trace of the same match (same stamp), for the bots' names, difficulty and trigger."""
    m = re.search(r"_(\d{8}-\d{6})\.jsonl$", path)
    if not m or os.path.basename(path).startswith("trace_"):
        return None
    hits = glob.glob(os.path.join(ROOT, "logs", f"trace_*_{m.group(1)}.jsonl")) + \
        glob.glob(os.path.join(ROOT, "logs", "verify", "traces", f"trace_*_{m.group(1)}.jsonl"))
    return hits[0] if hits else None


def trace_extras(path):
    """(meta {id: bot}, fire {id: [(t, 0/1)]}) from a trace, read line by line (they run to 70 MB)."""
    meta, fire = {}, collections.defaultdict(list)
    for x in open(path, encoding="utf-8"):
        if '"meta"' in x:
            try:
                b = json.loads(x)["meta"].get("bot")
                if b:
                    meta[b["id"]] = b
            except ValueError:
                pass
        elif '"cmd"' in x:
            try:
                d = json.loads(x)
                fire[d["id"]].append((d["t"], d["cmd"][3] & 1))
            except (ValueError, KeyError):
                pass
    return meta, fire


def on_ticks(t, events):
    """A held state per tick from [(t, 0/1)] changes or samples (the last value at or before each tick)."""
    out = np.zeros(len(t), bool)
    if not events:
        return out
    et = np.array([e[0] for e in events])
    ev = np.array([e[1] for e in events], bool)
    k = np.searchsorted(et, t, side="right") - 1
    ok = k >= 0
    out[ok] = ev[k[ok]]
    return out


def shot_times(gear, me):
    """[(t, rounds)] person me fired, from the collector's gear lines: the gun in hand's magazine going down with the
    same guns carried (a reload, a swap or a pickup is not a shot)."""
    g = [x for x in gear if x["id"] == me]
    out = []
    for a, b in zip(g, g[1:]):
        if a["wpn"] == b["wpn"] and a["wpn"] in a["inv"] and a["inv"] == b["inv"]:
            i = a["inv"].index(a["wpn"])
            if i < len(a["mag"]) and i < len(b["mag"]) and 0 <= b["mag"][i] < a["mag"][i]:
                out.append((b["t"], a["mag"][i] - b["mag"][i]))
    return out


def firing(t, shots, hold=0.1):
    """Per tick: a shot in the last hold seconds (the trigger, as the game saw it)."""
    st = np.array([x[0] for x in shots])
    if not len(st):
        return np.zeros(len(t), bool)
    return np.searchsorted(st, t, side="right") - np.searchsorted(st, t - hold, side="right") > 0


class Match:
    def __init__(s, path, los=None, zones=None):
        s.path = path
        d = load(path)
        s.__dict__.update(d)
        extra = companion_trace(path)
        s.trace = extra
        if extra:
            meta, fire = trace_extras(extra)
            s.meta.update(meta)
            for i, ev in fire.items():
                s.cmds.setdefault(i, ev)
        if los is None or zones is None:
            from brain.core import Vec
            from brain.maps import get_map, terrain
            mp = get_map(s.map)
            T = terrain(mp)
            los = los or (lambda a, b: T.los(Vec(*a), Vec(*b)))
            zones = zones or (lambda p: mp["zones"].name(Vec(*p)))
        s.los, s.zone_of = los, zones
        s.n = len(s.t)
        s.dt = float(np.median(np.diff(s.t))) if s.n > 1 else 0.033
        s.ids = sorted(s.P)
        s.alive = {i: np.nan_to_num(s.P[i][:, ALIVE]) > 0 for i in s.ids}
        s.team = {i: int(np.nanmax(s.P[i][:, TEAM])) for i in s.ids}
        s.bot = {i: bool(np.nanmax(s.P[i][:, BOT])) for i in s.ids}
        s.shots = {i: shot_times(s.gear, i) for i in s.ids if not s.bot[i]}
        s.fire = {i: firing(s.t, sh) for i, sh in s.shots.items() if sh}   # (your magazine: the collector)
        for i, ev in s.cmds.items():
            if i in s.P:
                s.fire[i] = on_ticks(s.t, ev)
        s.pairs = {}

    # --- what each player sees of each enemy
    def pair(s, me, foe, step):
        """For ticks 0, step, 2 step ..: (idx, d, vis, aim, body): in view with line of sight, aim on him (the
        sights rule), aim on his body (tight)."""
        key = (me, foe, step)
        if key in s.pairs:
            return s.pairs[key]
        idx = np.arange(0, s.n, step)
        a, b = s.P[me][idx], s.P[foe][idx]
        both = s.alive[me][idx] & s.alive[foe][idx]
        dx, dy = b[:, X] - a[:, X], b[:, Y] - a[:, Y]
        dz = (b[:, Z] + AIM_Z) - (a[:, Z] + EYE)
        d = np.hypot(dx, dy)
        dyaw = wrap(np.arctan2(dy, dx) - a[:, YAW])
        dpitch = np.arctan2(dz, np.maximum(d, 1e-6)) - a[:, PITCH]
        off = np.hypot(dyaw, dpitch)
        inview = both & (np.abs(dyaw) < HFOV / 2) & (np.abs(dpitch) < VFOV / 2) & (d < 80.0)
        vis = np.zeros(len(idx), bool)
        for k in np.nonzero(inview)[0]:
            vis[k] = s.los((a[k, X], a[k, Y], a[k, Z]), (b[k, X], b[k, Y], b[k, Z]))
        dd = np.nan_to_num(d, nan=99.0)
        aim = vis & (off < np.maximum(0.12, np.arctan2(0.6, np.maximum(dd, 0.1))))
        body = vis & (off < np.maximum(0.035, np.arctan2(0.4, np.maximum(dd, 0.1))))
        s.pairs[key] = out = (idx, dd, vis, aim, body)
        return out

    def enemies(s, me):
        return [j for j in s.ids if j != me and s.team[j] != s.team[me]]

    def step_for(s, me):
        """Every tick for people, every 3rd (10 a second) for bots: line of sight is the cost."""
        return 1 if not s.bot[me] or s.dt > 0.1 else 3

    # --- the measures
    def reactions(s, me):
        step = s.step_for(me)
        tt = s.t[np.arange(0, s.n, step)]
        fire_t = np.array([t for t, _ in s.shots.get(me, [])])
        aims, fires, pre, lost = [], [], 0, 0
        for foe in s.enemies(me):
            idx, d, vis, aim, body = s.pair(me, foe, step)
            last = -1e9
            for k in np.nonzero(vis)[0]:
                if tt[k] - last <= NEW_AFTER:
                    last = tt[k]
                    continue
                last = tt[k]
                if aim[k]:
                    pre += 1
                    continue
                got, seen = None, tt[k]
                for j in range(k + 1, len(tt)):
                    if tt[j] - tt[k] > REACT_MAX or tt[j] - seen > 0.5:
                        break                         # too slow, or he left the view first
                    if vis[j]:
                        seen = tt[j]
                    if aim[j]:
                        got = j
                        break
                if got is None:
                    lost += 1
                    continue
                aims.append(float(tt[got] - tt[k]))
                if len(fire_t):
                    f = fire_t[(fire_t >= tt[k]) & (fire_t <= tt[k] + REACT_MAX)]
                    if len(f):
                        fires.append(float(f[0] - tt[k]))
        return dict(aim=aims, fire=fires, pre=pre, lost=lost)

    def shot_reactions(s, me):
        step = s.step_for(me)
        idx = np.arange(0, s.n, step)
        tt = s.t[idx]
        hpv = np.nan_to_num(s.P[me][idx, SH] + s.P[me][idx, HP])
        alive = s.alive[me][idx]
        on = np.zeros(len(idx), bool)
        for foe in s.enemies(me):
            on |= s.pair(me, foe, step)[3]
        out, ready, quiet_since = [], 0, tt[0] if len(tt) else 0.0
        for k in range(1, len(idx)):
            hit = alive[k] and alive[k - 1] and hpv[k] < hpv[k - 1] - 0.02
            if hit and tt[k] - quiet_since >= 2.0 and on[k - 1]:
                ready += 1                            # already on someone when the first hit landed
            elif hit and tt[k] - quiet_since >= 2.0:
                for j in range(k, len(idx)):
                    if tt[j] - tt[k] > REACT_MAX:
                        break
                    if on[j]:
                        out.append(float(tt[j] - tt[k]))
                        break
            if hit or not alive[k]:
                quiet_since = tt[k]
        return dict(times=out, ready=ready)

    def damage(s, me):
        """Damage dealt (shield + body, 2.0 = a full kill) by this player, kills, and per-tick body-on-target while firing.
        A drop in an enemy's shield or body is his when he was on that enemy's body and firing in the last 0.3 s."""
        if me not in s.fire:
            return None
        step = s.step_for(me)
        idx = np.arange(0, s.n, step)
        tt, fire, mine = s.t[idx], s.fire[me][idx], s.alive[me][idx]
        recent = fire.copy()                          # fired in the last 0.3 s
        for k in range(1, max(1, int(round(0.3 / max(s.dt * step, 1e-3)))) + 1):
            recent[k:] |= fire[:-k]
        dealt, kills, events = 0.0, 0, []
        any_body = np.zeros(len(idx), bool)
        for foe in s.enemies(me):
            _, d, vis, aim, body = s.pair(me, foe, step)
            any_body |= body
            hv = np.nan_to_num(s.P[foe][idx, SH] + s.P[foe][idx, HP])
            al = s.alive[foe][idx]
            drop = hv[:-1] - hv[1:]
            hit = al[:-1] & (drop > 0.005) & recent[1:] & (body[1:] | body[:-1] | aim[:-1])
            amount = np.where(al[1:], np.minimum(drop, 2.0), hv[:-1])
            dealt += float(amount[hit].sum())
            when = tt[1:][hit]
            events += [(float(w), foe, float(a)) for w, a in zip(when, amount[hit])]
            for td in tt[1:][al[:-1] & ~al[1:]]:          # his deaths: ours when our last hit was under 1.5 s before
                k = np.searchsorted(when, td, side="right")
                kills += bool(k and td - when[k - 1] < 1.5)
        fire_n = int((fire & mine).sum())
        on_body = int((fire & mine & any_body).sum())
        return dict(dealt=round(dealt, 2), kills=kills, events=events, on_body=on_body / fire_n if fire_n else None,
                    fire_s=fire_n * s.dt * step)

    def engagements(s, me):
        step = s.step_for(me)
        idx = np.arange(0, s.n, step)
        tt = s.t[idx]
        combat = np.zeros(len(idx), bool)
        for foe in s.enemies(me):
            combat |= s.pair(me, foe, step)[3]
        if me in s.fire:
            combat |= s.fire[me][idx]
        hpv = np.nan_to_num(s.P[me][idx, SH] + s.P[me][idx, HP])
        combat[1:] |= hpv[1:] < hpv[:-1] - 0.02
        combat &= s.alive[me][idx]
        segs, start, last = [], None, None
        for k in np.nonzero(combat)[0]:
            if start is None:
                start = last = tt[k]
            elif tt[k] - last > GAP:
                segs.append((start, last))
                start = tt[k]
            last = tt[k]
        if start is not None:
            segs.append((start, last))
        segs = [g for g in segs if g[1] - g[0] >= 0.5]
        spawns = [float(tt[k]) for k in range(1, len(idx)) if s.alive[me][idx][k] and not s.alive[me][idx][k - 1]]
        ends = spawns[1:] + [float("inf")]                  # a first fight is in the same life
        firsts = [next((g[0] - sp for g in segs if sp <= g[0] < nxt), None) for sp, nxt in zip(spawns, ends)]
        alive_min = s.alive[me][idx].sum() * s.dt * step / 60.0
        gaps = [b[0] - a[1] for a, b in zip(segs, segs[1:])]
        return dict(n=len(segs), per_min=len(segs) / alive_min if alive_min else 0.0, starts=[float(g[0]) for g in segs],
                    length=[g[1] - g[0] for g in segs], gaps=gaps, to_first=[f for f in firsts if f is not None])

    def movement(s, me):
        a = s.P[me]
        al = s.alive[me] & (np.nan_to_num(a[:, RIDE]) == 0)
        dt = np.diff(s.t)
        v = np.hypot(np.diff(a[:, X]), np.diff(a[:, Y])) / np.maximum(dt, 1e-3)
        vz = np.diff(a[:, Z]) / np.maximum(dt, 1e-3)
        ok = al[1:] & al[:-1] & (dt < max(0.25, 2.5 * s.dt)) & (v < 15.0)      # (a trace samples every 0.25 s)
        sp = v[ok]
        # a jump: the climb rate crosses 1.8 u/s from a calm one (under 1.3 in the 2 samples before), one a half second.
        # A take-off spans two collector samples in every game (+1.5, then +2.6 u/s): the old rule (over 2.5, Reach 1.8,
        # right after a sample under 0.5) matched 23 of the player's 52 jump presses in Halo 4 (Blood Crash), 22 / 76 in
        # H2A, 32 / 81 in Halo 3, 51 / 147 in Reach; this one 51, 73, 78, 127 (logs/tmp/jump_rules.py). A trace's 4
        # samples a second see only a take-off's average: 1.5 there
        lift = 1.8 if s.dt < 0.1 else 1.5
        prev1 = np.r_[0.0, vz[:-1]]
        prev2 = np.r_[0.0, prev1[:-1]]
        jumps, last = 0, -1.0
        for i in np.nonzero((vz > lift) & ok & (prev1 <= lift) & (np.minimum(prev1, prev2) <= 1.3))[0]:
            if s.t[i + 1] - last > 0.5:
                jumps, last = jumps + 1, s.t[i + 1]
        minutes = ok.sum() * s.dt / 60.0
        # sideways speed in fights: across the line to the man the aim is on
        side = []
        step = s.step_for(me)
        for foe in s.enemies(me):
            idx, d, vis, aim, body = s.pair(me, foe, step)
            for k in np.nonzero(aim)[0]:
                i = idx[k]
                if 0 < i < s.n and ok[i - 1]:
                    ux, uy = s.P[foe][i, X] - a[i, X], s.P[foe][i, Y] - a[i, Y]
                    L = math.hypot(ux, uy) or 1.0
                    vx = (a[i, X] - a[i - 1, X]) / max(s.t[i] - s.t[i - 1], 1e-3)
                    vy = (a[i, Y] - a[i - 1, Y]) / max(s.t[i] - s.t[i - 1], 1e-3)
                    side.append(abs(vx * -uy / L + vy * ux / L))
        return dict(speed=float(np.median(sp)) if len(sp) else 0.0, p90=float(np.percentile(sp, 90)) if len(sp) else 0.0,
                    standing=float((sp < 0.3).mean()) if len(sp) else 0.0, jumps_min=jumps / minutes if minutes else 0.0,
                    strafe=float(np.median(side)) if side else None)

    def positioning(s, me):
        step = s.step_for(me)
        dist, height = [], []
        seen_by = np.zeros(len(np.arange(0, s.n, step)), bool)
        first_won, first_lost = 0, 0
        for foe in s.enemies(me):
            idx, d, vis, aim, body = s.pair(me, foe, step)
            for k in np.nonzero(aim)[0]:
                dist.append(d[k])
                height.append(s.P[me][idx[k], Z] - s.P[foe][idx[k], Z])
            fstep = s.step_for(foe)
            fidx, fd, fvis, faim, fbody = s.pair(foe, me, fstep)
            seen_by |= np.interp(s.t[idx], s.t[fidx], fvis.astype(float)) > 0.5
            # the first look: both in view of each other; whose aim got on the other first
            mine = s.t[idx][aim]
            his = s.t[fidx][faim]
            both = s.t[idx][vis & (np.interp(s.t[idx], s.t[fidx], fvis.astype(float)) > 0.5)]
            last = -1e9
            for tk in both:
                if tk - last > NEW_AFTER:
                    a1 = mine[(mine >= tk) & (mine <= tk + REACT_MAX)]
                    a2 = his[(his >= tk) & (his <= tk + REACT_MAX)]
                    if len(a1) or len(a2):
                        if len(a1) and (not len(a2) or a1[0] <= a2[0]):
                            first_won += 1
                        else:
                            first_lost += 1
                last = tk
        alive = s.alive[me][np.arange(0, s.n, step)]
        zones = collections.Counter()
        for k in range(0, s.n, max(1, int(1.0 / max(s.dt, 1e-3)))):      # once a second
            if s.alive[me][k]:
                zones[s.zone_of((s.P[me][k, X], s.P[me][k, Y], s.P[me][k, Z]))] += 1
        total = sum(zones.values()) or 1
        return dict(fight_dist=float(np.median(dist)) if dist else None,
                    height=float(np.median(height)) if height else None,
                    first_look=first_won / (first_won + first_lost) if first_won + first_lost else None,
                    looks=first_won + first_lost, in_view=float(seen_by[alive].mean()) if alive.any() else 0.0,
                    zones=[(z, n / total) for z, n in zones.most_common(8)])

    def deaths(s, me):
        al = s.alive[me]
        everyone = np.array([s.alive[i] for i in s.ids])
        out = 0
        for k in range(1, s.n):
            if al[k - 1] and not al[k]:
                gone = int((everyone[:, k - 1] & ~everyone[:, k]).sum())
                out += gone < max(3, len(s.ids) // 2)          # half the players at once: the match ended
        return out

    def gear_report(s, me):
        """Your guns, switches, pickups, shots and ability uses from the collector's gear lines."""
        g = [x for x in s.gear if x["id"] == me]
        if not g:
            return None
        guns = collections.Counter()
        switches, pickups, uses, use_len = 0, collections.Counter(), [], []
        alive_t = lambda t0, t1: float(s.alive[me][(s.t >= t0) & (s.t < t1)].sum() * s.dt)
        for a, end in zip(g, [x["t"] for x in g[1:]] + [float(s.t[-1]) if s.n else g[-1]["t"]]):
            guns[a["wpn"]] += alive_t(a["t"], end)            # the gun in hand until the next change
        for a, b in zip(g, g[1:]):
            if b["wpn"] != a["wpn"] and sorted(b["inv"]) == sorted(a["inv"]):
                switches += 1
            if a["inv"] and "none" not in a["inv"] + b["inv"]:   # (a respawn's loadout or a gun not read yet: no pickup)
                for w in set(b["inv"]) - set(a["inv"]):
                    pickups[w] += 1
            if b["ab"] and not a["ab"]:
                uses.append((b["t"], b["eq"]))
            if a["ab"] and not b["ab"] and uses:
                use_len.append(b["t"] - uses[-1][0])
        return dict(guns=guns.most_common(), switches=switches, pickups=dict(pickups), uses=uses, use_len=use_len,
                    shots=sum(n for _, n in s.shots.get(me, [])))

    def player(s, me):
        r = s.reactions(me)
        out = dict(id=me, team=s.team[me], bot=s.bot[me], name=s.meta.get(me, {}).get("name", "you" if not s.bot[me] else f"#{me}"),
                   tier=TIER_NAME.get(s.meta.get(me, {}).get("tier"), "" if s.bot[me] else "you"),
                   reaction=r, shot_reaction=s.shot_reactions(me), pace=s.engagements(me), move=s.movement(me),
                   place=s.positioning(me), damage=s.damage(me), deaths=s.deaths(me))
        if not s.bot[me]:
            out.update(gear=s.gear_report(me))
        return out


def med(v):
    return float(np.median(v)) if v else None


def summary(p):
    """One row of the side-by-side table."""
    dmg = p["damage"] or {}
    return dict(name=p["name"], tier=p["tier"], aim=med(p["reaction"]["aim"]), fire=med(p["reaction"]["fire"]),
                pre=p["reaction"]["pre"], n=len(p["reaction"]["aim"]), shot=med(p["shot_reaction"]["times"]), ready=p["shot_reaction"]["ready"],
                fights_min=p["pace"]["per_min"], fight_len=med(p["pace"]["length"]), between=med(p["pace"]["gaps"]),
                to_first=med(p["pace"]["to_first"]), speed=p["move"]["speed"], standing=p["move"]["standing"],
                strafe=p["move"]["strafe"], first_look=p["place"]["first_look"], in_view=p["place"]["in_view"],
                dist=p["place"]["fight_dist"], height=p["place"]["height"], on_body=dmg.get("on_body"),
                dealt=dmg.get("dealt"), kills=dmg.get("kills"), deaths=p["deaths"])


def analyze(path, who=None, los=None, zones=None):
    m = Match(path, los=los, zones=zones)
    people = [i for i in m.ids if not m.bot[i]]
    you = who if who is not None else (people[0] if people else None)
    players = {i: m.player(i) for i in m.ids}
    by_tier = collections.defaultdict(list)
    for i, p in players.items():
        if p["bot"]:
            by_tier[p["tier"] or "bots"].append(i)
    tiers = {}
    for tier, ids in by_tier.items():
        aims = [x for i in ids for x in players[i]["reaction"]["aim"]]
        shots = [x for i in ids for x in players[i]["shot_reaction"]["times"]]
        on = [players[i]["damage"]["on_body"] for i in ids if players[i]["damage"] and players[i]["damage"]["on_body"] is not None]
        tiers[tier] = dict(aim=med(aims), n=len(aims), shot=med(shots),
                           fights_min=float(np.mean([players[i]["pace"]["per_min"] for i in ids])),
                           speed=float(np.mean([players[i]["move"]["speed"] for i in ids])),
                           standing=float(np.mean([players[i]["move"]["standing"] for i in ids])),
                           strafe=med([players[i]["move"]["strafe"] for i in ids if players[i]["move"]["strafe"] is not None]),
                           first_look=med([players[i]["place"]["first_look"] for i in ids if players[i]["place"]["first_look"] is not None]),
                           on_body=float(np.mean(on)) if on else None)
    heat, fights = [], []
    if you is not None:                               # for the observer's map: where you were, where fights began
        a, cells = m.P[you], collections.Counter()
        for k in np.nonzero(m.alive[you])[0]:
            cells[(2 * round(a[k, X] / 2), 2 * round(a[k, Y] / 2))] += m.dt
        heat = [[float(x), float(y), round(float(sec), 2)] for (x, y), sec in cells.items()]
        fights = [[round(float(np.interp(t, m.t, a[:, X])), 2), round(float(np.interp(t, m.t, a[:, Y])), 2), round(t, 1)]
                  for t in players[you]["pace"]["starts"]]
    return dict(file=os.path.basename(path), kind=m.kind, map=m.map, game=m.game, seconds=float(m.t[-1] - m.t[0]) if m.n else 0.0,
                rate=round(1.0 / m.dt) if m.dt else None, trace=os.path.basename(m.trace) if m.trace else None, you=you,
                players={str(i): p for i, p in players.items()}, table=[summary(players[i]) for i in m.ids],
                tiers=tiers, heat=heat, fights=fights)


def page(a):
    """What the Observer's "You" section shows (no per-event lists: the page needs the numbers)."""
    you = a["players"].get(str(a["you"])) if a["you"] is not None else None
    v = {k: a[k] for k in ("file", "kind", "map", "game", "seconds", "rate", "trace", "tiers", "heat", "fights")}
    if you:
        dm = you["damage"] or {}
        v["you"] = dict(row=summary(you), pre=you["reaction"]["pre"], shot_ready=you["shot_reaction"]["ready"],
                        zones=you["place"]["zones"], looks=you["place"]["looks"], jumps=you["move"]["jumps_min"],
                        p90=you["move"]["p90"], fire_s=dm.get("fire_s"), gear=you.get("gear"),
                        fights=you["pace"]["n"])
    return v


def fmt(x, unit="", nd=2, pct=False):
    if x is None:
        return "-"
    return f"{100 * x:.0f}%" if pct else f"{x:.{nd}f}{unit}"


def report(a):
    out = [f"{a['file']}: {a['map']} ({a['game']}), {a['seconds']:.0f} s, {a['rate']} samples a second"
           + (f"; bots' names and triggers from {a['trace']}" if a["trace"] else "")]
    if a["rate"] and a["rate"] < 10:
        out.append("  (a trace: 4 samples a second, so times are good to about 0.25 s, and your shots are not known)")
    you = a["players"].get(str(a["you"])) if a["you"] is not None else None
    if you:
        r, pa, mv, pl, dm = you["reaction"], you["pace"], you["move"], you["place"], you["damage"] or {}
        out.append("YOU")
        out.append(f"  reaction: aim on a man who comes into view {fmt(med(r['aim']), ' s')} (median of {len(r['aim'])}), "
                   f"first shot {fmt(med(r['fire']), ' s')}; pre-aimed {r['pre']} times; "
                   f"aim on someone after being shot {fmt(med(you['shot_reaction']['times']), ' s')} "
                   f"(already on someone when hit {you['shot_reaction']['ready']} times)")
        out.append(f"  pace: {pa['n']} fights, {pa['per_min']:.1f} a minute alive, {fmt(med(pa['length']), ' s', 1)} long, "
                   f"{fmt(med(pa['gaps']), ' s', 1)} between; first fight {fmt(med(pa['to_first']), ' s', 1)} after a spawn")
        out.append(f"  movement: {mv['speed']:.2f} units/s median ({mv['p90']:.2f} at the 90th percentile), standing "
                   f"{fmt(mv['standing'], pct=True)}, {mv['jumps_min']:.1f} jumps a minute, strafe in fights {fmt(mv['strafe'], ' units/s')}")
        out.append(f"  positioning: fights at {fmt(pl['fight_dist'], ' units', 1)}, {fmt(pl['height'], ' units', 1)} over the man; "
                   f"first look won {fmt(pl['first_look'], pct=True)} of {pl['looks']}; an enemy had you in view "
                   f"{fmt(pl['in_view'], pct=True)} of the time")
        out.append("  zones: " + ", ".join(f"{z} {fmt(sh, pct=True)}" for z, sh in pl["zones"]))
        if dm:
            out.append(f"  accuracy: on the body {fmt(dm.get('on_body'), pct=True)} of {dm.get('fire_s', 0):.0f} s of trigger; "
                       f"damage dealt {dm.get('dealt')}; kills {dm.get('kills')}; deaths {you['deaths']}")
        else:
            out.append(f"  accuracy: needs your shots (the Data collector records your rounds); deaths {you['deaths']}")
        g = you.get("gear")
        if g:
            out.append("  guns: " + ", ".join(f"{w} {sec:.0f} s" for w, sec in g["guns"]) + f"; {g['switches']} switches; "
                       f"pickups {g['pickups'] or 'none'}" + (f"; {g['shots']} shots counted" if g["shots"] else ""))
            out.append(f"  equipment: {len(g['uses'])} uses" + (f" ({', '.join(sorted({e for _, e in g['uses']}))}), "
                       f"{fmt(med(g['use_len']), ' s', 1)} each" if g["uses"] else ""))
    out.append("SIDE BY SIDE (bots by difficulty: the same measures)")
    out.append(f"  {'who':12s} {'aim s':>6s} {'shot s':>6s} {'fights/min':>10s} {'speed':>6s} {'stand':>6s} {'strafe':>6s} "
               f"{'1st look':>8s} {'on body':>8s}")
    rows = ([("YOU", summary(you))] if you else []) + [(t, v) for t, v in sorted(a["tiers"].items(),
                                                                                key=lambda kv: list(TIER_NAME.values()).index(kv[0]) if kv[0] in TIER_NAME.values() else 9)]
    for name, v in rows:
        out.append(f"  {name:12s} {fmt(v.get('aim')):>6s} {fmt(v.get('shot')):>6s} {fmt(v.get('fights_min'), nd=1):>10s} "
                   f"{fmt(v.get('speed')):>6s} {fmt(v.get('standing'), pct=True):>6s} {fmt(v.get('strafe')):>6s} "
                   f"{fmt(v.get('first_look'), pct=True):>8s} {fmt(v.get('on_body'), pct=True):>8s}")
    return "\n".join(out)


def main():
    path = sys.argv[1] if os.path.exists(sys.argv[1]) else os.path.join(ROOT, "logs", sys.argv[1])
    a = analyze(path, int(sys.argv[2]) if len(sys.argv) > 2 else None)
    print(report(a))


if __name__ == "__main__":
    main()
