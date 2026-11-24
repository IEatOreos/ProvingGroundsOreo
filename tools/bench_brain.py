"""(custom, Nov 23) The brain's speed benchmark: 8v8 on the heaviest layouts, timed.

The owner, on keeping the bots fast according to their own tiers: "Yes both" (this benchmark, and brain/bot.py
tier_budget). It plays an 8v8 Slayer on each layout in tools/real_sim.py (the real brain, every player a bot) with the
live brain's helpers (tools/field_pool.py: route searches on other cores, asked ahead, the fixed targets kept) and its
pass clock (brain/bot.py PASS_CLOCK: the tiers' budgets), and times every think. A pass here is every bot's think one
after another, as the live brain's (tools/live_bots.py); it reports the passes' median and slowest tenth, and each
tier's think.

--save keeps the result as this PC's baseline (logs/bench/baseline.json: timings are this PC's, not kept in Git);
--check compares with it and exits 1 when a layout's median or slowest tenth is TOLERANCE times its baseline or more
(run it before a change ships, beside the tests).

usage: python -I tools/bench_brain.py [--maps renegade,utopie] [--seconds 20] [--seed 1] [--no-helpers]
                                      [--no-budgets] [--save | --check]
"""
import argparse
import json
import os
import statistics as st
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE]

LAYOUTS = {"renegade": "reach_forge_halo/variants/vf1ed8bb6", "utopie": "reach_forge_halo/variants/v9a4c6c2c",
           "paradiso": "reach_forge_halo/variants/v1cb8c7d4", "spire": "reach_35_island/variants/v704f87f3"}
# the owner's 8v8 roster (Renegade CTF 20261123-190955): 3 Demon, 3 Mythic, 5 Legendary, 3 Heroic, Tactician, Blind
RED = "demon,mythic,top,strong,top,mythic,tactician,top"
BLUE = "demon,mythic,top,strong,blind,top,demon,strong"
WARMUP_S = 5.0          # simulated seconds left out (the first fields, the helpers starting)
TOLERANCE = 1.25        # --check: this times the baseline or more fails
BASELINE = os.path.join(ROOT, "logs", "bench", "baseline.json")


def tier_of(p):
    from brain import profiles
    if profiles.fixed_noble(p):
        return "noble"
    if profiles.fixed_demon(p):
        return "demon"
    if profiles.fixed_mythic(p):
        return "mythic"
    return p.label or p.tier


def bench(name, seconds=20.0, seed=1, helpers=True, budgets=True):
    """One layout's numbers: dict(passes, pass_ms (median), pass_p90_ms, tiers {tier: mean think ms}, sim_s, real_s)."""
    import real_sim as RS
    from brain import bot as botmod
    from brain.bot import Bot
    import live_bots
    m = RS.RealMatch(name, seed, BLUE, 50, 8, quiet=True, red_tiers=RED, delay=True, time_limit=10 * 60.0)
    pool = None
    if helpers:
        from field_pool import Pool
        pool = Pool()
        if pool.bind(m.T):
            m.T.field_pool = pool
        else:
            pool = None
    think_ms, passes, cur = {}, [], [0.0]
    orig_think, orig_tick = Bot.think, m.tick
    tiers = {pid: tier_of(b.p) for pid, b in m.bots.items()}

    def think(b, *a, **k):
        t0 = time.perf_counter()
        try:
            return orig_think(b, *a, **k)
        finally:
            ms = (time.perf_counter() - t0) * 1000.0
            cur[0] += ms
            if m.now >= WARMUP_S:
                think_ms.setdefault(tiers.get(b.id, "?"), []).append(ms)

    pinned = [False]

    def tick():
        botmod.PASS_CLOCK[0] = time.perf_counter() if budgets else None
        if pool is not None and not pool.broken:
            snap = m.snapshot()
            if not pinned[0]:
                m.T.pin_targets(live_bots.fixed_targets(m.M, snap))
                pinned[0] = True
            live_bots.prefetch_routes(m.T, m.bots, snap)
        cur[0] = 0.0
        orig_tick()
        if m.now >= WARMUP_S:
            passes.append(cur[0])
    Bot.think, m.tick = think, tick
    t0 = time.time()
    try:
        while m.now < WARMUP_S + seconds and not m.over():
            m.tick()
    finally:
        Bot.think = orig_think
        botmod.PASS_CLOCK[0] = None
        if pool is not None:
            m.T.__dict__.pop("field_pool", None)
            pool.close()
    passes.sort()
    return dict(map=name, passes=len(passes), pass_ms=round(st.median(passes), 1) if passes else None,
                pass_p90_ms=round(passes[int(len(passes) * 0.9)], 1) if passes else None,
                tiers={k: round(st.mean(v), 2) for k, v in sorted(think_ms.items())},
                sim_s=round(m.now, 1), real_s=round(time.time() - t0, 1),
                helpers=pool is not None, budgets=budgets)


def compare(results, baseline, tolerance=TOLERANCE):
    """[(layout, what, now, baseline)] of every median or slowest tenth tolerance times its baseline or more."""
    out = []
    for key, r in results.items():
        b = baseline.get(key)
        if not b:
            continue
        for what in ("pass_ms", "pass_p90_ms"):
            if r.get(what) is not None and b.get(what) and r[what] >= tolerance * b[what]:
                out.append((key, what, r[what], b[what]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", default="renegade,utopie")
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--no-helpers", action="store_true")
    ap.add_argument("--no-budgets", action="store_true")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--check", action="store_true")
    o = ap.parse_args()
    results = {}
    for key in o.maps.split(","):
        name = LAYOUTS.get(key, key)
        r = bench(name, o.seconds, o.seed, helpers=not o.no_helpers, budgets=not o.no_budgets)
        results[key] = r
        print(json.dumps({key: r}), flush=True)
    if o.save:
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        old = {}
        if os.path.exists(BASELINE):
            with open(BASELINE, encoding="utf-8") as f:
                old = json.load(f)
        old.update(results)
        with open(BASELINE, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=1)
        print("baseline kept:", BASELINE, flush=True)
    if o.check:
        if not os.path.exists(BASELINE):
            print("no baseline on this PC yet: run with --save first", flush=True)
            return 0
        with open(BASELINE, encoding="utf-8") as f:
            slow = compare(results, json.load(f))
        for key, what, now, was in slow:
            print(f"SLOWER: {key} {what} {now} ms (baseline {was} ms)", flush=True)
        print("benchmark: " + ("slower than the baseline" if slow else "as fast as the baseline or faster"), flush=True)
        return 1 if slow else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
