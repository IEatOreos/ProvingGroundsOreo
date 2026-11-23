"""(custom, Nov 23) Noble experiments in the real-rules sim (tools/real_sim_fights.py), for the owner's 50-20 goal: each
experiment (a name and Noble settings, brain/noble.py OVERRIDE) on the same seeds, run as parallel processes, never while
MCC runs (the owner's matches come first: a launch waits until it is closed). Results in logs/real_sim/<name>_<seed>.json
(kept: a finished run is not run again) and a table per experiment: Noble's and Demon's scores, wins, the 50-20 test.

usage: python -I real_sim_sweep.py --exp "base:" --exp "noodds:odds=0" [--seeds 1-6] [--jobs 12] [--minutes 12]"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "logs", "real_sim")
PY = os.path.join(ROOT, "python", "python.exe")


def mcc_running():
    try:
        r = subprocess.run(["tasklist", "/NH", "/FO", "CSV"], capture_output=True, text=True, timeout=20)
        return any(line.strip('"').upper().startswith("MCC") for line in r.stdout.splitlines())
    except Exception:
        return False


def seeds_of(text):
    out = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return out


def table(exps, seeds):
    rows = []
    for name, _ in exps:
        res = []
        for sd in seeds:
            p = os.path.join(OUT, f"{name}_{sd}.json")
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
                res.append((d["score"].get("noble", 0), d["score"].get("demon", 0)))
        if res:
            n = sum(a for a, _ in res)
            dm = sum(b for _, b in res)
            wins = sum(a > b for a, b in res)
            goal = sum(a >= 50 and b <= 20 for a, b in res)
            rows.append(dict(exp=name, games=len(res), noble=n, demon=dm, wins=wins, goal_50_20=goal,
                             mean=f"{n / len(res):.1f}-{dm / len(res):.1f}", scores=res))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", action="append", required=True, help="name:k=v,k=v (no settings: Noble as it is)")
    ap.add_argument("--seeds", default="1-6")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--minutes", type=float, default=12.0)
    o = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    exps = [tuple(e.split(":", 1)) if ":" in e else (e, "") for e in o.exp]
    seeds = seeds_of(o.seeds)
    queue = [(n, s, sd) for n, s in exps for sd in seeds if not os.path.exists(os.path.join(OUT, f"{n}_{sd}.json"))]
    running = []
    while queue or running:
        running = [(p, job) for p, job in running if p.poll() is None]
        while queue and len(running) < o.jobs:
            if mcc_running():
                print(time.strftime("%H:%M"), "MCC is running: waiting", flush=True)
                time.sleep(60)
                break
            n, s, sd = queue.pop(0)
            args = [PY, "-I", os.path.join(HERE, "real_sim_fights.py"), "--seed", str(sd), "--minutes", str(o.minutes),
                    "--json", os.path.join(OUT, f"{n}_{sd}.json")]
            if s:
                args += ["--set", s]
            log = open(os.path.join(OUT, f"{n}_{sd}.log"), "w")
            running.append((subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT), (n, sd)))
        time.sleep(5)
    for r in table(exps, seeds):
        print(json.dumps(r), flush=True)


if __name__ == "__main__":
    main()
