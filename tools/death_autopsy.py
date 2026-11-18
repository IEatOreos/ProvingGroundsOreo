"""Why bots die (custom, Nov 18): every recorded death of a bot, sorted into one cause, from the match traces.

The owner wants a Demon that puts staying alive first; this says which deaths a rule would save. A trace with kill rows
(tools/kill_record.py: who the game credits, what killed, who damaged the body lately) and the bot's own rows (its
shield and health, its goal, who it believed it saw) gives, for each death of a bot:

- the fatal fight: its damage since the last FIGHT_GAP without any (the bot's shield + health falling more than 0.01,
  as Bot.hurt_by counts a hit), and the shield and health it went into that fight with
- shooters: the enemies whose damage is on the body (the game's own list, 4 at most)
- whether it had seen the man who killed it (its beliefs, seen by eye) before his first damage
- its goal when the fight started ("fight"/"hunt": it took the fight; anything else: caught on its way), and at death
- what killed it, how far off he was, how long it had been alive, the killer's own shield + health at the death

and one cause, the first of CAUSES that holds. The causes overlap, so the report also counts every condition across all
the deaths. Kills by the same bots give their K/D, and their time alive deaths per 10 minutes alive.

The Reach shield read can be 0 with the shield full; as the brain (SHIELD_BACK), a bot untouched for 10 s went in full.

    python -I tools\\death_autopsy.py                    Demon deaths in every trace with kill rows
    python -I tools\\death_autopsy.py --last 4 --list    the 4 newest traces, one line a death
    python -I tools\\death_autopsy.py --tier all         every bot tier, and each tier's causes side by side
    python -I tools\\death_autopsy.py logs\\trace_x.jsonl ...
"""
import argparse
import collections
import glob
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import kill_record                                      # noqa: E402

LOGS = os.path.join(ROOT, "logs")
FULL = 0.95             # the shield a Demon waits for (brain DEMON_FULL)
SHIELD_BACK = 10.0      # s untouched: the shield is full whatever the read says (brain SHIELD_BACK)
LOW_HEALTH = 0.6        # health under this going in (Reach refills health only so far) counts as started hurt
FIGHT_GAP = 2.0         # s without damage: the exchange before it is over; the fatal one is the damage after the last
                        # (4 s merged a break, 3 s of recharge and the re-peek into one fight "gone into" at full)
KEEP = 25.0             # s of each bot's rows kept before a death
SEEN_BEFORE = 3.0       # s: the killer seen by eye this long before his first damage, or
SEEN_GRACE = 0.25       # s after it (one look of the bot), counts as seen
SPAWN_S = 5.0           # s alive: died off its spawn
GRENADES = {11, 22}     # frag, plasma
POWER = {7, 8, 9, 10, 12, 20, 21, 64}   # shotgun, sniper, rockets, laser, grenade launcher, hammer, sword, fuel rod
TICKS = 60.0            # Reach game ticks a second (a kill row's hits count ticks before the death)
HURT_STEP = 0.01       # shield + health falling more than this between two rows is a hit (Bot.hurt_by)

CAUSES = [
    ("no killer", "a fall, its own grenade or a teammate"),
    ("vehicle", "in a vehicle, or killed by one"),
    ("outnumbered", "2 or more enemies' damage on the body"),
    ("grenade", "killed by a grenade"),
    ("never saw him", "the killer unseen until he had shot it"),
    ("started hurt", "went into the fight under full shield or low on health"),
    ("power weapon", "shotgun, sniper, rockets, sword, hammer and the like"),
    ("lost a 1v1", "none of the above: one man, seen, it went in healthy"),
]
TAGS = [
    ("outnumbered", "2+ enemies damaged it"),
    ("never saw him", "killer unseen before his first damage"),
    ("started hurt", "went in under full shield / low health"),
    ("took the fight", "its goal was fight/hunt when the fight started"),
    ("caught on its way", "any other goal when the fight started"),
    ("breaking off", "its goal was retreat when it died"),
    ("off its spawn", f"alive under {SPAWN_S:.0f} s"),
    ("he was nearly dead", "the killer's shield was gone when it died"),
    ("power weapon", "killed by one"),
    ("grenade", "killed by one"),
    ("vehicle", "in one or killed by one"),
]

_KEY = re.compile(r'^\{"t": [^,]+, "(\w+)": ')
_ID = re.compile(r'^\{"t": [^,]+, "id": (\d+), "(\w+)"')


def weapon_names():
    try:
        with open(os.path.join(HERE, "service_record_site", "weapons.json"), encoding="utf-8") as fh:
            r = json.load(fh)["reach"]
        return {int(k): v for k, v in r["names"].items()}, set(r["vehicles"])
    except (OSError, ValueError, KeyError):
        return {}, set(range(24, 41)) | {59}


NAMES, VEHICLES = weapon_names()


def has_kills(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return '"kill_record"' in fh.readline()
    except OSError:
        return False


class Bot:
    def __init__(s, tier, name, team):
        s.tier, s.name, s.team = tier, name, team
        s.rows = collections.deque()        # (t, shield, health, goal, veh, foes, pos)
        s.thinks = collections.deque()      # (t, {enemy id seen by eye}, enemies seen)
        s.dead_at = -99.0
        s.life_from = None
        s.last_t = None
        s.alive_s = 0.0
        s.kills = 0

    def row(s, t, r):
        hp = r.get("hp") or [1.0, 1.0]
        if s.last_t is not None and 0 < t - s.last_t < 1.0 and hp[1] > 0:
            s.alive_s += t - s.last_t
        s.last_t = t
        if s.life_from is None and t > s.dead_at + 0.5 and hp[1] > 0:
            s.life_from = t
        s.rows.append((t, hp[0], hp[1], r.get("goal"), r.get("veh", -1), r.get("foes") or [], r.get("pos")))
        while s.rows and t - s.rows[0][0] > KEEP:
            s.rows.popleft()

    def think(s, t, r):
        seen = {b[0] for b in r.get("beliefs") or [] if len(b) > 4 and b[4]}
        s.thinks.append((t, seen, (r.get("flags") or {}).get("seen", 0)))
        while s.thinks and t - s.thinks[0][0] > KEEP:
            s.thinks.popleft()


def fatal_fight(rows):
    """(index of the fight's first damaged row, index of the last row before it, recent damage before the fight) in
    rows up to the death: the damage since the last FIGHT_GAP without any."""
    hits = [i for i in range(1, len(rows))
            if (rows[i - 1][1] + rows[i - 1][2]) - (rows[i][1] + rows[i][2]) > HURT_STEP and rows[i][2] > 0
            or (rows[i][2] <= 0 < rows[i - 1][2])]
    if not hits:
        return len(rows) - 1, max(0, len(rows) - 2), False      # (killed between two rows)
    k = len(hits) - 1
    while k > 0 and rows[hits[k]][0] - rows[hits[k - 1]][0] <= FIGHT_GAP:
        k -= 1
    first = hits[k]
    before = [i for i in hits[:k] if rows[first][0] - rows[i][0] <= SHIELD_BACK]
    return first, first - 1, bool(before)


def autopsy(b, k, t, victim):
    """One death of bot b at t from kill row k: a dict of what was found."""
    rows = [r for r in b.rows if r[0] <= t + 0.05]
    kind, killer, weapon = kill_record.read(k) or ("death", None, k.get("c"))
    d = dict(t=t, who=b.name, tier=b.tier, kind=kind, killer=killer, weapon=weapon, c=k.get("c"),
             killer_bot=bool(k.get("kb")), life=(t - b.life_from) if b.life_from is not None else None)
    if not rows:
        d.update(shield=None, health=None, goal=None, end_goal=None, seen=None, shooters=1, veh=False, killer_hp=None,
                 recent=False, dist=None)
        return d
    first, pre, recent = fatal_fight(rows)
    t0 = rows[first][0]
    sh, hl = rows[pre][1], rows[pre][2]
    if sh < FULL and not recent and t0 - (b.life_from or -99.0) >= 0:     # (the 0 read: untouched, it was full)
        sh = 1.0
    enemies = {f[0] for r in rows for f in r[5]}
    window = (t - t0 + 0.5) * TICKS                             # (damage of the fatal fight, not one before it)
    shooters = {h[0] for h in k.get("hits") or [] if h[0] is not None and h[0] != victim and h[0] in enemies
                and (h[3] or 0) + (h[4] or 0) > 0 and (h[5] or 0) <= window}
    if killer is not None and killer in enemies:
        shooters.add(killer)
    seen = None
    if killer is not None:
        seen = any(killer in s_ for tt, s_, _ in b.thinks if t0 - SEEN_BEFORE <= tt <= t0 + SEEN_GRACE)
    foes = {f[0]: f for f in rows[-1][5]}
    kh = foes.get(killer)
    vp, kp = k.get("vp"), k.get("kp")
    d.update(shield=sh, health=hl, goal=rows[pre][3], end_goal=rows[-1][3], seen=seen, shooters=len(shooters),
             veh=any(r[4] not in (None, -1) for r in rows[-3:]), killer_hp=(kh[1], kh[2]) if kh else None,
             recent=recent, fight_s=t - t0,
             dist=math.dist(vp, kp) if vp and kp else None,
             seen_n=max((n for tt, _, n in b.thinks if t0 - 0.5 <= tt <= t), default=0))
    return d


def tags(d):
    c = d.get("c")
    out = set()
    if d["shooters"] >= 2:
        out.add("outnumbered")
    if d.get("seen") is False:
        out.add("never saw him")
    if d.get("shield") is not None and (d["shield"] < FULL or d["health"] < LOW_HEALTH):
        out.add("started hurt")
    if d.get("goal") is not None:
        out.add("took the fight" if d["goal"] in ("fight", "hunt") else "caught on its way")
    if d.get("end_goal") == "retreat":
        out.add("breaking off")
    if d.get("life") is not None and d["life"] < SPAWN_S:
        out.add("off its spawn")
    if d.get("killer_hp") and d["killer_hp"][0] <= 0.02:
        out.add("he was nearly dead")
    if c in POWER:
        out.add("power weapon")
    if c in GRENADES:
        out.add("grenade")
    if d.get("veh") or c in VEHICLES:
        out.add("vehicle")
    return out


def cause(d):
    if d["kind"] != "kill":
        return "no killer"
    tg = tags(d)
    for name, _ in CAUSES[1:-1]:
        if name in tg:
            return name
    return "lost a 1v1"


def read_trace(path):
    """(deaths, bots) of one trace: deaths a list of autopsy dicts (with "map"), bots {id: Bot}."""
    bots, deaths, mp = {}, [], os.path.basename(path)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = _ID.match(line)
            if m:
                i = int(m.group(1))
                if i not in bots:
                    continue
                r = json.loads(line)
                (bots[i].think if m.group(2) == "think" else bots[i].row)(r["t"], r)
                continue
            m = _KEY.match(line)
            if not m:
                continue
            key = m.group(1)
            if key == "meta":
                r = json.loads(line)
                b = r["meta"].get("bot") or {}
                mp = r["meta"].get("map", mp)
                if "id" in b and b["id"] not in bots:
                    bots[b["id"]] = Bot(b.get("tier", "?"), b.get("name", "?"), b.get("team"))
            elif key == "kill":
                r = json.loads(line)
                k, t = r["kill"], r["t"]
                if k.get("st") == kill_record.OVER:
                    continue
                kind, killer, _ = kill_record.read(k) or (None, None, None)
                if kind == "kill" and killer in bots:
                    bots[killer].kills += 1
                v = k.get("v")
                if v in bots:
                    d = autopsy(bots[v], k, t, v)
                    d["map"] = mp
                    deaths.append(d)
                    bots[v].dead_at, bots[v].life_from = t, None
    return deaths, bots


def pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "-"


def report(deaths, bots, tier, matches, out=print):
    mine = [d for d in deaths if tier == "all" or d["tier"] == tier]
    them = [b for bb in bots for b in bb.values() if tier == "all" or b.tier == tier]
    alive = sum(b.alive_s for b in them)
    kills = sum(b.kills for b in them)
    n = len(mine)
    out(f"{tier} bots: {n} deaths in {matches} matches, {kills} kills (K/D {kills / n:.2f})" if n else
        f"{tier} bots: no deaths in {matches} matches ({kills} kills)")
    if alive:
        out(f"  {10 * 60 * n / alive:.1f} deaths per 10 minutes alive ({alive / 60:.0f} bot-minutes)")
    if not n:
        return
    by = collections.Counter(cause(d) for d in mine)
    out("\ncause (each death once, the first that holds)")
    for name, what in CAUSES:
        ds = [d for d in mine if cause(d) == name]
        if not ds:
            continue
        hum = sum(not d["killer_bot"] for d in ds if d["kind"] == "kill")
        dists = [d["dist"] for d in ds if d.get("dist") is not None]
        out(f"  {name:16} {by[name]:4}  {pct(by[name], n):>4}   human killer {hum:3}   "
            f"median {statistics.median(dists):5.1f} u   {what}" if dists else
            f"  {name:16} {by[name]:4}  {pct(by[name], n):>4}   {what}")
    out("\nalso true of the deaths (they overlap)")
    tc = collections.Counter(t_ for d in mine for t_ in tags(d))
    for name, what in TAGS:
        out(f"  {name:20} {tc[name]:4}  {pct(tc[name], n):>4}   {what}")
    hurt = [d for d in mine if "started hurt" in tags(d)]
    if hurt:
        out(f"  (started hurt: median shield {statistics.median(d['shield'] for d in hurt):.2f}, "
            f"health {statistics.median(d['health'] for d in hurt):.2f} going in)")
    ws = collections.Counter(NAMES.get(d["c"], f"type {d['c']}") for d in mine if d["c"] is not None)
    out("\nkilled with: " + ", ".join(f"{w} {c}" for w, c in ws.most_common(8)))
    goals = collections.Counter(d["goal"] for d in mine if d.get("goal"))
    out("its goal when the fatal fight started: " + ", ".join(f"{g} {c}" for g, c in goals.most_common(8)))


def by_tier(deaths, out=print):
    tiers = sorted({d["tier"] for d in deaths})
    out("\nshare of each tier's deaths by cause")
    out(f"  {'':16}" + "".join(f"{t:>9}" for t in tiers))
    for name, _ in CAUSES:
        row = []
        for t in tiers:
            ds = [d for d in deaths if d["tier"] == t]
            row.append(pct(sum(cause(d) == name for d in ds), len(ds)))
        out(f"  {name:16}" + "".join(f"{x:>9}" for x in row))
    out(f"  {'deaths':16}" + "".join(f"{sum(d['tier'] == t for d in deaths):>9}" for t in tiers))


def listing(deaths, tier, out=print):
    out("\nevery death")
    for d in deaths:
        if tier != "all" and d["tier"] != tier:
            continue
        sh = "  -  " if d.get("shield") is None else f"{d['shield']:.2f}/{d['health']:.2f}"
        kh = f"{d['killer_hp'][0]:.2f}" if d.get("killer_hp") else " -  "
        far = "" if d.get("dist") is None else f"{d['dist']:.0f} u"
        out(f"  {d['map'][:24]:24} t={d['t']:6.1f} {d['who'][:14]:14} {cause(d):15} went in {sh} "
            f"goal {str(d.get('goal'))[:9]:9} -> {str(d.get('end_goal'))[:9]:9} "
            f"{NAMES.get(d['c'], d['c'])!s:16} {far:>5} "
            f"shooters {d['shooters']} saw {d.get('seen')!s:5} his shield {kh} "
            f"{'bot' if d['killer_bot'] else 'human'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("traces", nargs="*")
    ap.add_argument("--tier", default="demon", help="demon (default), top, ..., or all")
    ap.add_argument("--last", type=int, default=0, help="only the N newest traces with kill rows")
    ap.add_argument("--list", action="store_true", help="one line a death")
    a = ap.parse_args(argv)
    paths = a.traces or sorted((p for p in glob.glob(os.path.join(LOGS, "trace_*.jsonl")) if has_kills(p)),
                               key=os.path.getmtime)
    if a.last:
        paths = paths[-a.last:]
    if not paths:
        print("no traces with kill rows (tools/kill_record.py writes them in recorded Reach matches)")
        return 1
    deaths, bots = [], []
    for p in paths:
        ds, bs = read_trace(p)
        deaths += ds
        bots.append(bs)
    report(deaths, bots, a.tier, len(paths))
    if a.tier == "all":
        by_tier(deaths)
    if a.list:
        listing(deaths, a.tier)
    return 0


if __name__ == "__main__":
    sys.exit(main())
