"""(custom, Nov 20) Noble's self-play tuning: Noble's settings (brain/noble.py DEFAULTS: which of Demon's rules it
keeps, how hard it pushes, its winning spots) played against Demon in the simulator, the winner written to
user/noble_tune.json for the live bots. The owner: "anything self learning we can give it ... we can try here"; "DO 1".

Each game is 4 Noble against 4 Demon, DMRs, Team Slayer (tools/banshee_sim.py's match loop: the real brain, no game) on
Asylum by default: the 4v4 that matched the owner's three live games of Nov 20 (Demon 50-24, 50-35, 50-43; the sims
50-31 on average). Every set is played on the same seeds, the sides swapped every other game; its score is Noble's kills
less Demon's a game. A round tries --tries neighbours of the best so far (one or two settings changed); the best of them
takes over only --gain kills a game over it. --save writes the best found when it beats where it started.

Not tuned here: long_pace, explore, shot_learn. The simulator has no bloom (a fixed ASSUMED spread), so pace there says
nothing; Noble's own shots set its pace live (brain/noble.py gap).

Each game is a worker process at below-normal priority (MCC keeps the CPU). Writes nothing else: the workers' Nobles
learn into a temporary folder (noble.SAVE off).

usage: python -I tools/noble_tune.py [--map reach_forge_halo/variants/v8e4a8930] [--games 4] [--tries 4] [--rounds 1]
                                     [--limit 30] [--minutes 12] [--jobs 3] [--seed 1] [--gain 2.0] [--save]
       python -I tools/noble_tune.py --worker '<settings json>' SEED SWAP OUT.json [--map M] [--limit N] [--minutes M]"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

ASYLUM = "reach_forge_halo/variants/v8e4a8930"      # (tools/bot_sim.py: hr_forgeWorld_asylum.mvar, Forge World map 21)
# the settings tried and their values (brain/noble.py DEFAULTS); the rules on (1) or off (0)
GRID = dict(push=(0.0, 0.15, 0.3), push_shield=(0.5, 0.75, 0.95), spots=(0, 1), spot_hold_s=(2.0, 3.0, 5.0),
            recharge=(0, 1), no_new_fight=(0, 1), break_second=(0, 1), odds=(0, 1), peek=(0, 1), chase=(0, 1))
BELOW_NORMAL = 0x00004000


# --- one game ---------------------------------------------------------------------------------------------------------
def play(settings, seed, swap, map_name=ASYLUM, limit=30, minutes=12.0):
    """One 4v4 game, Noble (these settings) against Demon: dict(noble, demon kills, score, t)."""
    from brain import noble
    noble.SAVE = False
    noble.STORE_DIR = tempfile.mkdtemp(prefix="noble_tune_")
    noble.OVERRIDE = dict(settings)
    noble.reload()
    import banshee_sim as B
    from brain.core import Vec

    class Match(B.Match):
        def spawn(s, m, first=False):
            super().spawn(m, first)
            flags = s.M.get("flags") or {}
            mid = flags.get(8)
            if mid is None and 0 in flags and 1 in flags:
                mid = (flags[0] + flags[1]) * 0.5
            if mid is not None:
                m.yaw = math.atan2(mid.y - m.pos.y, mid.x - m.pos.x)   # (banshee_sim faces Boneyard's middle)

    red, blue = ("demon", "noble") if swap else ("noble", "demon")
    m = Match(map_name, seed, blue, limit, per_team=4, quiet=True, red_tiers=red)
    r = m.run(minutes=minutes)
    k = {"noble": 0, "demon": 0}
    for x in m.men.values():
        k[x.tier] += x.kills
    return dict(noble=k["noble"], demon=k["demon"], score=r["score"], t=r["t"], seed=seed, swap=swap)


# --- the search -------------------------------------------------------------------------------------------------------
def neighbours(base, n, rng):
    """n sets one or two settings off base, each new."""
    out, seen = [], {json.dumps(base, sort_keys=True)}
    tries = 0
    while len(out) < n and tries < 200:
        tries += 1
        c = dict(base)
        for key in rng.sample(sorted(GRID), rng.choice((1, 1, 2))):
            opts = [v for v in GRID[key] if v != base.get(key)]
            c[key] = rng.choice(opts)
        sig = json.dumps(c, sort_keys=True)
        if sig not in seen:
            seen.add(sig)
            out.append(c)
    return out


def run_games(jobs, sets, seeds, o):
    """Every set on every seed (side swapped on odd seeds), jobs workers at a time: {set index: [results]}."""
    todo = [(i, s) for i in range(len(sets)) for s in seeds]
    out = {i: [] for i in range(len(sets))}
    running = []
    tmp = tempfile.mkdtemp(prefix="noble_tune_out_")
    py = sys.executable
    while todo or running:
        while todo and len(running) < jobs:
            i, seed = todo.pop(0)
            path = os.path.join(tmp, f"{i}_{seed}.json")
            args = [py, "-I", os.path.abspath(__file__), "--worker", json.dumps(sets[i]), str(seed), str(seed % 2),
                    path, "--map", o.map, "--limit", str(o.limit), "--minutes", str(o.minutes)]
            flags = BELOW_NORMAL if os.name == "nt" else 0
            p = subprocess.Popen(args, cwd=ROOT, creationflags=flags, stdout=subprocess.DEVNULL,
                                 stderr=open(path + ".err", "w"))
            running.append((p, i, seed, path))
        time.sleep(1.0)
        for item in list(running):
            p, i, seed, path = item
            if p.poll() is None:
                continue
            running.remove(item)
            try:
                with open(path, encoding="utf-8") as f:
                    r = json.load(f)
                out[i].append(r)
                print(f"  set {i} seed {seed}: Noble {r['noble']} - Demon {r['demon']} ({r['t']:.0f} s)", flush=True)
            except (OSError, ValueError):
                print(f"  set {i} seed {seed}: failed (see {path}.err)", flush=True)
    return out


def margin(results):
    return sum(r["noble"] - r["demon"] for r in results) / len(results) if results else float("-inf")


def changed(a, b):
    return {k: b[k] for k in b if a.get(k) != b[k]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", nargs=4, metavar=("SETTINGS", "SEED", "SWAP", "OUT"))
    ap.add_argument("--map", default=ASYLUM)
    ap.add_argument("--games", type=int, default=4)
    ap.add_argument("--tries", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--minutes", type=float, default=12.0)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--gain", type=float, default=2.0)
    ap.add_argument("--save", action="store_true")
    o = ap.parse_args()
    if o.worker:
        settings, seed, swap, out = o.worker
        r = play(json.loads(settings), int(seed), int(swap), o.map, o.limit, o.minutes)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(r, f)
        return
    from brain import noble
    start = noble.tune("reach")
    tuned = {k: start[k] for k in noble.DEFAULTS}
    rng = random.Random(o.seed)
    seeds = list(range(o.seed, o.seed + o.games))
    print(f"start: {changed(noble.DEFAULTS, tuned) or 'the defaults'}; {o.games} games a set to {o.limit}, "
          f"{o.jobs} at a time", flush=True)
    best, best_m, games = tuned, None, 0
    history = []
    for rnd in range(o.rounds):
        cands = neighbours(best, o.tries, rng)
        sets = ([best] if best_m is None else []) + cands
        print(f"round {rnd + 1}: {len(sets)} sets", flush=True)
        res = run_games(o.jobs, sets, seeds, o)
        games += sum(len(v) for v in res.values())
        offset = 0
        if best_m is None:
            best_m = margin(res[0])
            history.append(dict(settings=changed(noble.DEFAULTS, best), margin=round(best_m, 2), games=len(res[0])))
            print(f"  start set: {best_m:+.1f} kills a game", flush=True)
            offset = 1
        top_i, top_m = None, best_m
        for j, c in enumerate(cands):
            m_ = margin(res[j + offset])
            history.append(dict(settings=changed(noble.DEFAULTS, c), margin=round(m_, 2), games=len(res[j + offset])))
            print(f"  {changed(best, c)}: {m_:+.1f} kills a game", flush=True)
            if m_ > top_m + o.gain:
                top_i, top_m = j, m_
        if top_i is not None:
            best, best_m = cands[top_i], top_m
            print(f"  new best: {changed(noble.DEFAULTS, best)} at {best_m:+.1f}", flush=True)
    print(f"best: {changed(noble.DEFAULTS, best) or 'the defaults'} at {best_m:+.1f} kills a game ({games} games)")
    if o.save:
        if best != tuned:
            ok = noble.save_tune("reach", best, map=o.map, vs="demon", margin=round(best_m, 2), games=games,
                                 per_set=o.games, limit=o.limit, history=history)
            print("saved to user/noble_tune.json" if ok else "could not write user/noble_tune.json")
        else:
            print("nothing better than where it started: user/noble_tune.json left as it was")


if __name__ == "__main__":
    main()
