"""(custom, Nov 23) How each kill in a real-rules match happened (tools/real_sim.py), for tuning Noble toward the
owner's 50-20: for every kill, the victim's and the killer's goal then, who hit the other first in their exchange,
how many enemies hurt the victim in its last 3 s, the range, the gun and the killer's health left. Then a tally per team.

usage: python -I real_sim_fights.py --seed 1 [--red-tiers noble] [--tiers demon] [--json out.json] [--minutes 12]"""
import argparse
import collections
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import real_sim as R  # noqa: E402


class Watched(R.RealMatch):
    def __init__(s, *a, **k):
        s.hits_log = collections.defaultdict(list)     # victim id -> [(t, attacker id)]
        s.kills_log = []
        super().__init__(*a, **k)

    def hurt(s, m, dmg, by, head=False, veh_shot=False, how="gun"):
        if m.alive and by is not None and by != m.id and not (getattr(m, "on", False) and m.kind == "armor_lock"):
            s.hits_log[m.id].append((s.now, by))
        super().hurt(m, dmg, by, head, veh_shot, how)

    def kill(s, m, killer, veh_shot, how):
        if m.alive and killer is not None and killer.id != m.id:
            recent = [(t, a) for t, a in s.hits_log[m.id] if s.now - t <= 3.0]
            hurters = {a for _, a in recent}
            mine = [t for t, a in s.hits_log[killer.id] if a == m.id and s.now - t <= 6.0]
            theirs = [t for t, a in s.hits_log[m.id] if a == killer.id and s.now - t <= 6.0]
            first = "killer" if theirs and (not mine or theirs[0] < mine[0]) else "victim" if mine else "none"
            vb, kb = s.bots[m.id], s.bots[killer.id]
            s.kills_log.append(dict(
                t=round(s.now, 1), killer=killer.tier, victim=m.tier, how=how, first_hit=first,
                hurters=len(hurters), range=round((killer.pos - m.pos).length(), 1),
                killer_goal=kb.goal[0], victim_goal=vb.goal[0], victim_notes=[n[:40] for n in vb.notes[:3]],
                killer_hp=round((killer.shield + max(0.0, killer.body)) / (R.BS.SHIELD + R.BS.BODY), 2),
                victim_kind=m.kind, killer_kind=killer.kind,
                victim_moving=round((m.vel.x ** 2 + m.vel.y ** 2) ** 0.5, 1)))
        s.hits_log.pop(m.id, None)
        super().kill(m, killer, veh_shot, how)


def tally(kills, tier):
    """What a tier's deaths and kills looked like."""
    deaths = [k for k in kills if k["victim"] == tier and k["killer"] != tier]
    wins = [k for k in kills if k["killer"] == tier and k["victim"] != tier]
    c = lambda xs, f: collections.Counter(f(x) for x in xs).most_common(6)
    return dict(kills=len(wins), deaths=len(deaths),
                deaths_first_hit=c(deaths, lambda k: k["first_hit"]), deaths_outnumbered=c(deaths, lambda k: k["hurters"]),
                deaths_goal=c(deaths, lambda k: k["victim_goal"]), kills_goal=c(wins, lambda k: k["killer_goal"]),
                deaths_how=c(deaths, lambda k: k["how"]), kills_hp_left=round(sum(k["killer_hp"] for k in wins) / max(1, len(wins)), 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--red-tiers", default="noble")
    ap.add_argument("--tiers", default="demon")
    ap.add_argument("--minutes", type=float, default=12.0)
    ap.add_argument("--json")
    ap.add_argument("--set", default="", help="Noble settings for this run, k=v,k=v (brain/noble.py OVERRIDE)")
    o = ap.parse_args()
    if o.set:
        from brain import noble
        noble.OVERRIDE = {k: float(v) for k, v in (kv.split("=") for kv in o.set.split(","))}
    t0 = time.time()
    m = Watched(R.ASYLUM, o.seed, o.tiers, R.LIMIT, 4, quiet=True, red_tiers=o.red_tiers, time_limit=o.minutes * 60)
    m.run()
    r = R.summary(m, o.seed)
    r["real_s"] = round(time.time() - t0, 1)
    r["kills"] = m.kills_log
    r["opener"] = [getattr(b, "noble_opener_stats", None) for b in m.bots.values()]
    print(json.dumps({k: v for k, v in r.items() if k != "kills"}), flush=True)
    for tier in sorted({o.red_tiers, o.tiers}):
        print(tier, json.dumps(tally(m.kills_log, tier)), flush=True)
    if o.json:
        with open(o.json, "w", encoding="utf-8") as f:
            json.dump(r, f, indent=1)


if __name__ == "__main__":
    main()
