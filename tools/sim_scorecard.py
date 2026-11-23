"""(custom, Nov 21) Sim-vs-live scorecard: the same fight metrics from live Reach traces (logs/trace_reach_*.jsonl) and
from offline matches of tools/banshee_sim.py (the real brain, no game), side by side, so the simulator's results can be
weighed against the game's. Test tool only: it reads traces and writes nothing but the JSON it is asked for.

Metrics (one parser for both: the sim's recorder writes rows in the live trace's shape):
- DMR accuracy, by the range to the target (<3, 3-6, 6-12, 12+ u) and by his sideways speed across the shot (<0.5,
  0.5-1.5, >1.5 u/s). A round = the bot's DMR magazine dropping between two of its rows; its target = the bot's
  att ["aim", id, ...] of that row or the one before; a hit = the target's shield + health lower in the first world row
  at or after the round (within HIT_S) than in the last one before the bot's previous row;
- kills: the time from the victim's first damage (the first drop after his last full world row) to his death, the
  distance at the kill, and how often the first hitter won (the killer's own damage started at or after the victim's;
  "hurt before" when the killer was already hurt HURT_BEFORE_S before the fight began);
- the alive time by goal (hunt, fight, retreat, objective, item ...) and retreating with the shield down.

The owner's row in live traces is player 0: a target, a killer and a victim, not a shooter (no magazine read).

usage: python -I sim_scorecard.py [--live TRACE ...] [--sim GAMES] [--delay] [--seed 1] [--limit 50] [--minutes 12]
                                  [--json out.json] [--show a.json b.json ...] [--delays]
  (no --live: every Asylum match in logs/ (the owner, Nov 23: "All games on ayslum to count"), any mode and tiers,
   pooled, and its 1v1s alone again; --delays: Noble's measured read-to-action ages over them, banshee_sim DELAY_Q)
"""
import argparse
import bisect
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
LOGS = os.path.join(ROOT, "logs")
ASYLUM = "reach_forge_halo/variants/v8e4a8930"     # the owner's Asylum Team Slayer DMR variant
RANGES = ((0.0, 3.0, "<3u"), (3.0, 6.0, "3-6u"), (6.0, 12.0, "6-12u"), (12.0, 1e9, "12+u"))
SIDE = ((0.0, 0.5, "<0.5u/s"), (0.5, 1.5, "0.5-1.5u/s"), (1.5, 1e9, ">1.5u/s"))
HIT_S = 0.35          # s: a round's damage shows in the first world row at most this long after it (rows ~0.27 s apart)
FULL = 1.98           # shield + health this high (of 2) is a full man
HURT_BEFORE_S = 2.0   # s: the killer's damage began this long before the victim's: an earlier fight, not this one
OWNER = 0
BOT_KEYS = ("t", "pos", "goal", "wpn", "inv", "mag", "hp", "att", "veh", "lead")


def asylum_traces(logs=LOGS, variant=ASYLUM):
    """Every live trace in logs whose match ran on the variant (its meta rows), oldest first."""
    out = []
    for name in sorted(os.listdir(logs)):
        if not (name.startswith("trace_reach_") and name.endswith(".jsonl")):
            continue
        path = os.path.join(logs, name)
        with open(path, encoding="utf-8") as f:
            for k, line in enumerate(f):
                if k > 400:
                    break
                if '"meta"' in line[:30]:
                    try:
                        if json.loads(line)["meta"].get("variant") == variant:
                            out.append(path)
                    except (ValueError, KeyError, AttributeError):
                        pass
                    break
    return out


def leads(rec, tier="noble"):
    """The tier's logged lead (its read-to-action age, Bot.noble_lead_s), every row that has one."""
    return [r["lead"] for pid, rows in rec.bots.items() if rec.tier(pid) == tier for r in rows
            if isinstance(r.get("lead"), (int, float))]


def quantiles(xs, steps=20):
    """xs' quantiles 1 / steps apart (banshee_sim DELAY_Q's shape), () for none."""
    xs = sorted(xs)
    return tuple(xs[min(len(xs) - 1, int(k / steps * len(xs)))] for k in range(steps + 1)) if xs else ()


def band(x, bands):
    for lo, hi, name in bands:
        if lo <= x < hi:
            return name
    return bands[-1][2]


class Rec:
    """One match's rows: tiers {id: tier}, bots {id: [row]}, world [(t, {id: (team, alive, x, y, z, total)})], kills."""

    def __init__(s):
        s.tiers, s.bots, s.world, s.kills = {}, collections.defaultdict(list), [], []
        s.wt = []

    def add(s, r):
        if "meta" in r:
            b = r["meta"].get("bot") or {}
            if "id" in b:
                s.tiers[b["id"]] = b.get("tier", "?")
        elif "kill" in r:
            k = r["kill"]
            s.kills.append((r["t"], k.get("v"), k.get("k"), k.get("vp"), k.get("kp")))
        elif "world" in r:
            w = {}
            for p in r["world"]:
                w[p[0]] = (p[1], bool(p[2]), p[3], p[4], p[5], (p[6] or 0.0) + (p[7] or 0.0))
            s.world.append((r["t"], w))
            s.wt.append(r["t"])
        elif "id" in r and "cmd" in r:
            s.bots[r["id"]].append({k: r[k] for k in BOT_KEYS if k in r})   # (what is read only: 30 traces in memory)

    def tier(s, pid):
        return "owner" if pid == OWNER and pid not in s.tiers else s.tiers.get(pid, "?")

    # --- the world rows --------------------------------------------------------------------------------------------
    def row_before(s, t):
        i = bisect.bisect_right(s.wt, t) - 1
        return s.world[i] if i >= 0 else None

    def row_after(s, t):
        i = bisect.bisect_left(s.wt, t)
        return s.world[i] if i < len(s.world) else None

    def place(s, pid, t):
        """His place at t (eased between the world rows round it) and velocity, or None."""
        i = bisect.bisect_right(s.wt, t) - 1
        if i < 0 or i + 1 >= len(s.world):
            return None
        (t0, w0), (t1, w1) = s.world[i], s.world[i + 1]
        a, b = w0.get(pid), w1.get(pid)
        if a is None or b is None or not a[1] or not b[1] or t1 - t0 <= 0 or t1 - t0 > 0.6:
            return None
        f = (t - t0) / (t1 - t0)
        p = tuple(a[2 + k] + (b[2 + k] - a[2 + k]) * f for k in range(3))
        v = tuple((b[2 + k] - a[2 + k]) / (t1 - t0) for k in range(3))
        if math.hypot(v[0], v[1]) > 10.0:          # (a respawn between the rows)
            return None
        return p, v


def load_trace(path):
    rec = Rec()
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec.add(json.loads(line))
            except ValueError:
                continue
    return rec


def dmr_mag(r):
    inv, mag = r.get("inv") or [r.get("wpn")], r.get("mag") or []
    if "dmr" not in inv:
        return None
    i = inv.index("dmr")
    return mag[i] if i < len(mag) else None


def aim_of(r):
    a = r.get("att")
    return a[1] if a and a[0] == "aim" and isinstance(a[1], int) else None


def rounds(rec):
    """(t, shooter, target, t_prev, shooter's place): every DMR round the bots spent, by their magazines."""
    out = []
    for pid, rows in rec.bots.items():
        for p, r in zip(rows, rows[1:]):
            a, b = dmr_mag(p), dmr_mag(r)
            if a is None or b is None or b >= a or r["t"] - p["t"] > 0.5:
                continue
            tgt = aim_of(p)
            tgt = tgt if tgt is not None else aim_of(r)
            for _ in range(a - b):
                out.append((r["t"], pid, tgt, p["t"], r["pos"]))
    return out


def accuracy(rec):
    """{(shooter tier, target kind): {band: [rounds, hits]}}; target kind "owner" / "bot"."""
    acc = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for t, pid, tgt, tp, mpos in rounds(rec):
        if tgt is None:
            continue
        him = rec.place(tgt, t)
        if him is None:
            continue
        (hx, hy, hz), v = him
        mx, my, mz = mpos
        dx, dy, dz = hx - mx, hy - my, hz - mz
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        fl = math.hypot(dx, dy) or 1e-6
        ux, uy = dx / fl, dy / fl
        side = abs(v[0] * -uy + v[1] * ux)
        before, after = rec.row_before(tp), rec.row_after(t)
        if before is None or after is None or after[0] - t > HIT_S or tgt not in before[1] or tgt not in after[1]:
            continue
        hit = after[1][tgt][5] < before[1][tgt][5] - 0.02
        kind = "owner" if tgt == OWNER and tgt not in rec.tiers else "bot"
        for key in ((rec.tier(pid), kind), (rec.tier(pid), "all")):
            for b in ("all", band(d, RANGES), band(side, SIDE)):
                c = acc[key][b]
                c[0] += 1
                c[1] += int(hit)
    return acc


def damage_start(rec, pid, t):
    """When his damage began before t: the first world row after his last full one (None: full at t)."""
    i = bisect.bisect_right(rec.wt, t) - 1
    last = None
    while i >= 0:
        w = rec.world[i][1].get(pid)
        if w is None or not w[1] or w[5] >= FULL:
            break
        last = rec.world[i][0]
        i -= 1
    return last


def kills(rec):
    """[(killer tier, victim tier, time from first hit, distance, first hitter won: True / False / None)]."""
    out = []
    for t, v, k, vp, kp in rec.kills:
        if k is None or v is None or k == v or k < 0:
            continue
        vs = damage_start(rec, v, t - 0.01)
        ks = damage_start(rec, k, t + 0.01)
        if vp is None or kp is None:
            a, b = rec.place(v, t - 0.3), rec.place(k, t - 0.3)
            vp, kp = (a[0] if a else None), (b[0] if b else None)
        d = math.dist(vp, kp) if vp and kp else None
        ttk = t - vs if vs is not None else 0.0
        if ks is None:
            won = True
        elif vs is not None and ks < vs - HURT_BEFORE_S:
            won = None                                   # (hurt before this fight)
        else:
            won = vs is not None and ks >= vs
        out.append((rec.tier(k), rec.tier(v), ttk, d, won))
    return out


def goals(rec):
    """{tier: Counter(goal)} over the bots' alive rows, and "retreat_hurt": retreating with the shield down."""
    g = collections.defaultdict(collections.Counter)
    for pid, rows in rec.bots.items():
        tier = rec.tier(pid)
        for r in rows:
            if r.get("veh", -1) not in (-1, None):
                continue
            g[tier][r.get("goal")] += 1
            g[tier]["_rows"] += 1
            hp = r.get("hp") or [1.0, 1.0]
            if r.get("goal") == "retreat" and hp[0] < 0.99:
                g[tier]["_retreat_hurt"] += 1
    return g


def partial(rec):
    """One match's counts (small: a match's rows can go once these are taken)."""
    return accuracy(rec), kills(rec), goals(rec)


def metrics(recs, parts=None):
    """The scorecard of several matches pooled (recs, or their partial() counts): plain JSON."""
    acc = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    ks, gs = [], collections.defaultdict(collections.Counter)
    n = 0
    for a, k, g in (parts if parts is not None else (partial(r) for r in recs)):
        n += 1
        for key, bands in a.items():
            for b, c in bands.items():
                acc[key][b][0] += c[0]
                acc[key][b][1] += c[1]
        ks += k
        for tier, c in g.items():
            gs[tier].update(c)
    out = dict(matches=n, accuracy={}, kills={}, goals={})
    for (tier, kind), bands in acc.items():
        out["accuracy"][f"{tier}>{kind}"] = {b: [c[0], round(c[1] / c[0], 3) if c[0] else None] for b, c in bands.items()}
    for who in sorted({k[0] for k in ks}) + ["all"]:
        sel = [k for k in ks if who == "all" or k[0] == who]
        if not sel:
            continue
        ttk = sorted(k[2] for k in sel)
        dd = sorted(k[3] for k in sel if k[3] is not None)
        w = [k[4] for k in sel if k[4] is not None]
        out["kills"][who] = dict(n=len(sel), ttk_med=round(ttk[len(ttk) // 2], 2),
                                 ttk_p90=round(ttk[int(len(ttk) * 0.9)], 2),
                                 dist_med=round(dd[len(dd) // 2], 1) if dd else None,
                                 dist_p90=round(dd[int(len(dd) * 0.9)], 1) if dd else None,
                                 first_hitter_won=round(sum(w) / len(w), 3) if w else None,
                                 hurt_before=sum(1 for k in sel if k[4] is None))
    for tier, c in gs.items():
        rows = c["_rows"] or 1
        sh = {g: round(v / rows, 3) for g, v in c.most_common() if not str(g).startswith("_")}
        sh["retreat_shield_down"] = round(c["_retreat_hurt"] / rows, 3)
        out["goals"][tier] = sh
    return out


# --- the sim ---------------------------------------------------------------------------------------------------------
def sim_match(seed=1, limit=50, minutes=12.0, delay=False, red="demon", blue="noble", per_team=4, game_map=ASYLUM):
    """One banshee_sim Match (team 0 red, team 1 blue; the owner's Asylum: 4 Demon vs 4 Noble Team Slayer DMR) recorded
    into a Rec the live way. Returns (rec, the match's result)."""
    import banshee_sim as B

    class Recorded(B.Match):
        def __init__(s, *a, **kw):
            s.rec, s.mag = Rec(), {}
            super().__init__(*a, **kw)
            for m in s.men.values():
                s.rec.add(dict(t=0.0, meta=dict(bot=dict(id=m.id, team=m.team, tier=m.tier))))

        def fire_gun(s, m, a):
            n = s.stats["rounds"]
            super().fire_gun(m, a)
            if s.stats["rounds"] > n and m.weapon == "dmr":
                s.mag[m.id] = s.mag.get(m.id, 15) - 1 if s.mag.get(m.id, 15) > 1 else 15
            # (the trace's reload: up to 15 again; the parser counts only drops)

        def kill(s, m, killer, veh_shot, how):
            was = m.alive
            pos = m.pos
            super().kill(m, killer, veh_shot, how)
            if was and not m.alive:
                s.rec.add(dict(t=round(s.now, 3), kill=dict(v=m.id, k=killer.id if killer else None,
                                                            vp=[pos.x, pos.y, pos.z],
                                                            kp=[killer.pos.x, killer.pos.y, killer.pos.z]
                                                            if killer else None)))

        def tick(s):
            super().tick()
            t = round(s.now, 3)
            for m in s.men.values():
                if not m.alive:
                    continue
                b = s.bots[m.id]
                s.rec.add(dict(t=t, id=m.id, pos=[m.pos.x, m.pos.y, m.pos.z], goal=b.goal[0], wpn=m.weapon,
                               inv=list(m.weapons), mag=[s.mag.get(m.id, 15), 32], cmd=[0, 0, 0, 0, 0],
                               hp=[m.shield / B.SHIELD, max(0.0, m.body) / B.BODY], att=b.att, veh=m.vehicle))
            if s.ticks % 8 == 0:
                s.rec.add(dict(t=t, world=[[m.id, m.team, int(m.alive), m.pos.x, m.pos.y, m.pos.z,
                                            max(0.0, m.shield) / B.SHIELD, max(0.0, m.body) / B.BODY]
                                           for m in s.men.values()]))

    m = Recorded(game_map, seed, blue, limit, per_team=per_team, quiet=True, red_tiers=red, delay=delay)
    r = m.run(minutes)
    r["delays"] = sorted(m.ages)[len(m.ages) // 2] if m.ages else None
    return m.rec, r


# --- the table -------------------------------------------------------------------------------------------------------
def show(cols):
    """cols: [(label, metrics)]: the scorecard side by side."""
    w = 16
    lines = []

    def row(name, vals):
        lines.append(f"{name:<34}" + "".join(f"{v if v is not None else '-':>{w}}" for v in vals))
    row("", [c[0][:w - 1] for c in cols])
    row("matches", [c[1]["matches"] for c in cols])
    keys = sorted({k for c in cols for k in c[1]["accuracy"]})
    for k in keys:
        lines.append(f"DMR accuracy {k} (rounds hit %)")
        for b in ["all"] + [x[2] for x in RANGES] + [x[2] for x in SIDE]:
            vals = []
            for c in cols:
                e = c[1]["accuracy"].get(k, {}).get(b)
                vals.append(f"{e[0]} {e[1] * 100:.0f}%" if e and e[1] is not None else None)
            row("  " + b, vals)
    whos = sorted({k for c in cols for k in c[1]["kills"]})
    for who in whos:
        lines.append(f"kills by {who}")
        for f in ("n", "ttk_med", "ttk_p90", "dist_med", "dist_p90", "first_hitter_won", "hurt_before"):
            row("  " + f, [c[1]["kills"].get(who, {}).get(f) for c in cols])
    tiers = sorted({k for c in cols for k in c[1]["goals"]})
    for tier in tiers:
        lines.append(f"alive time by goal, {tier}")
        gl = sorted({g for c in cols for g in c[1]["goals"].get(tier, {})}, key=str)
        for g in gl:
            row("  " + str(g), [c[1]["goals"].get(tier, {}).get(g) for c in cols])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", nargs="*", help="live traces (default: the owner's Asylum matches of Nov 21)")
    ap.add_argument("--sim", type=int, default=0, help="this many sim matches (4 Demon vs 4 Noble, Asylum)")
    ap.add_argument("--delay", action="store_true", help="the sim with the game's delays (banshee_sim Match(delay))")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--minutes", type=float, default=12.0)
    ap.add_argument("--json", help="write this run's metrics here")
    ap.add_argument("--show", nargs="*", help="metrics JSON files to print side by side (label: the file name)")
    ap.add_argument("--delays", action="store_true", help="print Noble's measured delay quantiles over the live traces")
    o = ap.parse_args()
    cols = []
    for p in o.show or []:
        with open(p) as f:
            got = json.load(f)
        # (a file of one run's metrics, or of several by label)
        cols += [(os.path.splitext(os.path.basename(p))[0], got)] if "matches" in got else list(got.items())
    if o.show is not None and not o.sim and o.live is None:
        print(show(cols))
        return
    out = {}
    if o.sim:
        sys.path.insert(0, HERE)
        recs = []
        for g in range(o.sim):
            rec, r = sim_match(o.seed + g, o.limit, o.minutes, o.delay)
            print(f"sim game {g + 1}: {r['score']} in {r['t']:.0f} s (real {r['real_s']:.0f} s)"
                  + (f", median delay {r['delays'] * 1000:.0f} ms" if r.get("delays") else ""), flush=True)
            recs.append(rec)
        out["sim" + ("+delay" if o.delay else "")] = metrics(recs)
    else:
        paths = (asylum_traces() if o.live is None else
                 [p if os.path.exists(p) else os.path.join(LOGS, p) for p in o.live])
        parts, solo, ages = [], [], []
        for p in paths:
            rec = load_trace(p)                  # (one at a time: 30 traces' rows do not fit in memory together)
            parts.append(partial(rec))
            if len(rec.tiers) == 1:
                solo.append(parts[-1])
            ages += leads(rec)
            print(f"{os.path.basename(p)}: {dict(collections.Counter(rec.tiers.values()))}, {len(rec.kills)} kills",
                  flush=True)
            del rec
        out["live Asylum" if o.live is None else "live"] = metrics(None, parts)
        if o.live is None and solo:
            out["live 1v1"] = metrics(None, solo)
        if o.delays:
            print(f"Noble delay quantiles over {len(ages)} rows: {quantiles(ages)}")
    cols += list(out.items())
    if o.json:
        with open(o.json, "w") as f:
            json.dump(out, f, indent=1)
    print(show(cols))


if __name__ == "__main__":
    main()
