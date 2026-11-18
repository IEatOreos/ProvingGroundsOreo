"""Why players die (custom, Nov 18): every recorded death, the owner's and the bots', sorted into one cause, from the
match traces, so a Demon's deaths can be set beside his.

The owner wants a Demon that puts staying alive first; this says which deaths a rule would save, and how he dies
compared with it ("Just as you have the demon autopsy report, you also have one for me, and then we can compare the
demon difficulties to what I do as well"). A trace with kill rows (tools/kill_record.py: who the game credits, what
killed, who damaged the body lately) and its world rows (everyone, 4 a second: position, aim, shield, health, the enemy
in their sights; brain/tracefmt.py Everyone) give, for each death, measured the same way for a person and a bot:

- the fatal fight: the damage since the last FIGHT_GAP without any (shield + health falling more than 0.01, as
  Bot.hurt_by counts a hit), and the shield and health he went into it with
- shooters: the enemies whose damage of that fight is on the body (the game's own list, 4 at most)
- whether he saw the man who killed him before his first damage: in his field of view (HFOV, the owner's MCC setting)
  with a line of sight on the map's terrain: a Forge layout's own, with its pieces (the trace's meta "variant", or
  variant_of for a trace from before it: on the bare canvas 63% of Forge World pairs read clear, 14% with the pieces)
- whether he took the fight: an enemy in his sights (row 14) in the second before the first damage; else caught
- what killed him, how far off the killer was, how long he had been alive, the killer's own shield at the death;
  for a bot also its goal when the fight started and at death (its own rows)

and one cause, the first of CAUSES that holds. The causes overlap, so the report also counts every condition. Kills
give K/D, the time alive deaths per 10 minutes alive. A trace's one person is "you" (the owner); with two or more
people in the match they are "people" (who is who is not in the trace).

The Reach shield read can be 0 with the shield full; as the brain (SHIELD_BACK), a player untouched for 10 s went in
full.

    python -I tools\\death_autopsy.py                   you beside each bot tier (the comparison)
    python -I tools\\death_autopsy.py --tier demon      one group's report: demon, top, you, people, all ...
    python -I tools\\death_autopsy.py --last 4 --list   the 4 newest traces, one line a death
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
sys.path.insert(0, ROOT)
import kill_record                                      # noqa: E402

LOGS = os.path.join(ROOT, "logs")
FULL = 0.95             # the shield a Demon waits for (brain DEMON_FULL)
SHIELD_BACK = 10.0      # s untouched: the shield is full whatever the read says (brain SHIELD_BACK)
LOW_HEALTH = 0.6        # health under this going in (Reach refills health only so far) counts as started hurt
FIGHT_GAP = 2.0         # s without damage: the exchange before it is over; the fatal one is the damage after the last
                        # (4 s merged a break, 3 s of recharge and the re-peek into one fight "gone into" at full)
KEEP = 25.0             # s of world rows kept before a death
SEEN_BEFORE = 3.0       # s: the killer in view this long before his first damage, or
SEEN_GRACE = 0.25       # s after it (a look), counts as seen
TOOK = 1.0              # s before the first damage: an enemy in his sights then, he took the fight
EXPOSE_EVERY = 0.5      # s: how often everyone's exposure is counted (the enemies with him in view, a line of sight)
EXPOSE_R = 40.0         # u: an enemy farther off is not counted as seeing him (past DMR range for a fight)
TWO_DIED = 2.0          # s: dead this soon after 2+ enemies stopped seeing him, that 2-on-1 killed him
SPAWN_S = 5.0           # s alive: died off his spawn
GRENADES = {11, 22}     # frag, plasma
POWER = {7, 8, 9, 10, 12, 20, 21, 64}   # shotgun, sniper, rockets, laser, grenade launcher, hammer, sword, fuel rod
TICKS = 60.0            # Reach game ticks a second (a kill row's hits count ticks before the death)
HURT_STEP = 0.01        # shield + health falling more than this between two rows is a hit (Bot.hurt_by)
EYE, AIM_Z = 0.62, 0.35                 # tools/player_stats.py: eye over the feet, the body's middle
HFOV = math.radians(105.0)              # the owner's MCC field of view (player_stats)
VFOV = 2 * math.atan(math.tan(HFOV / 2) * 9 / 16)
YOU, PEOPLE = "you", "people"
NAMES_OF = {"top": "Legendary", "demon": "Demon", YOU: "you", PEOPLE: "people"}

CAUSES = [
    ("no killer", "a fall, his own grenade or a teammate"),
    ("vehicle", "in a vehicle, or killed by one"),
    ("outnumbered", "2 or more enemies' damage on the body"),
    ("grenade", "killed by a grenade"),
    ("never saw him", "the killer not in view until he had shot"),
    ("started hurt", "went into the fight under full shield or low on health"),
    ("power weapon", "shotgun, sniper, rockets, sword, hammer and the like"),
    ("lost a 1v1", "none of the above: one man, seen, went in healthy"),
]
TAGS = [
    ("outnumbered", "2+ enemies damaged him"),
    ("never saw him", "killer not in view before his first damage"),
    ("started hurt", "went in under full shield / low health"),
    ("took the fight", "an enemy in his sights as the fight began"),
    ("caught", "nobody in his sights as the fight began"),
    ("breaking off", "a bot's goal was retreat when it died"),
    ("off his spawn", f"alive under {SPAWN_S:.0f} s"),
    ("he was nearly dead", "the killer's shield was gone"),
    ("power weapon", "killed by one"),
    ("grenade", "killed by one"),
    ("vehicle", "in one or killed by one"),
]

_KEY = re.compile(r'^\{"t": [^,]+, "(\w+)": ')
_ID = re.compile(r'^\{"t": [^,]+, "id": (\d+), "pos"')


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


_TERRAIN = {}
_STAMP = re.compile(r"_(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})\d{2}\.jsonl$")


def variant_of(path, mp):
    """The map variant a trace was played on ("<map>/variants/<id>": a Forge layout, its pieces in its terrain), for a
    trace written before its meta named it: the variant last (or first) seen at the trace's own start minute
    (variant.json last_seen, written as the match starts). None: not a variant, or not known."""
    m = _STAMP.search(os.path.basename(path))
    vd = os.path.join(ROOT, "maps", mp or "", "variants")
    if not m or not mp or not os.path.isdir(vd):
        return None
    stamp = f"{m[1]}-{m[2]}-{m[3]} {m[4]}:{m[5]}"
    for v in sorted(os.listdir(vd)):
        try:
            with open(os.path.join(vd, v, "variant.json"), encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if stamp in (d.get("last_seen"), d.get("first_seen")):
            return f"{mp}/variants/{v}"
    return None


def map_los(name):
    """A line-of-sight test on map `name`'s terrain (a map variant's: with its Forge pieces), (a, b) -> bool, or None
    when it cannot be loaded (then "seen" is the field of view alone)."""
    if name not in _TERRAIN:
        try:
            from brain.core import Vec
            from brain.maps import get_map, terrain
            T = terrain(get_map(name))
            _TERRAIN[name] = lambda a, b: T.los(Vec(a[0], a[1], a[2]), Vec(b[0], b[1], b[2]))
        except Exception:
            _TERRAIN[name] = None
    return _TERRAIN[name]


TERRAIN_USED = {}       # trace basename -> the map or map variant whose terrain its line of sight was read on


def terrain_los(path, mp, variant=None):
    """The trace's line-of-sight test: its map variant's terrain (named in its meta, else variant_of), else the base
    map's, else none (field of view alone)."""
    for name in (variant or variant_of(path, mp), mp):
        if name and map_los(name) is not None:
            TERRAIN_USED[os.path.basename(path)] = name
            return map_los(name)
    TERRAIN_USED[os.path.basename(path)] = None
    return lambda a, b: True


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def in_view(p, e, los):
    """Is e (a world row) in p's field of view with a line of sight?"""
    if not (p[2] and e[2]):
        return False
    dx, dy = e[3] - p[3], e[4] - p[4]
    d = math.hypot(dx, dy)
    if d > 80.0:
        return False
    dz = (e[5] + AIM_Z) - (p[5] + EYE)
    if abs(wrap(math.atan2(dy, dx) - p[10])) > HFOV / 2 or abs(math.atan2(dz, max(d, 1e-6)) - p[11]) > VFOV / 2:
        return False
    if los is None:
        return True
    try:
        return bool(los(p[3:6], e[3:6]))
    except Exception:
        return True


def exposure(W, los):
    """{id: how many enemies have him in their field of view with a line of sight within EXPOSE_R} of everyone alive
    on foot in world rows W."""
    out = {}
    alive = [w for w in W.values() if w[2]]
    for p in alive:
        if len(p) > 16 and p[16] is not None:
            continue                        # (in a vehicle: seen or not, it is not the angle play on foot)
        out[p[0]] = sum(1 for e in alive if e[1] != p[1] and math.hypot(e[3] - p[3], e[4] - p[4]) <= EXPOSE_R
                        and in_view(e, p, los))
    return out


class Player:
    def __init__(s, pid):
        s.id = pid
        s.bot = None            # (tier, name) from the trace's meta; None: a person
        s.goals = collections.deque()       # a bot's (t, goal, vehicle)
        s.life_from = None
        s.was_alive = False
        s.last_t = None
        s.alive_s = 0.0
        s.kills = 0
        s.seen_by = collections.Counter()   # seconds alive with 0, 1, 2+ enemies seeing him (exposure)
        s.twos = []                         # [start, end, died] of each time 2+ enemies saw him at once
        s.open_two = None

    def two(s, t, on):
        if on and s.open_two is None:
            s.open_two = [t, t, False]
            s.twos.append(s.open_two)
        elif on:
            s.open_two[1] = t
        else:
            s.open_two = None

    def world(s, t, w):
        if s.last_t is not None and w[2] and 0 < t - s.last_t < 1.0:
            s.alive_s += t - s.last_t
        s.last_t = t
        if w[2] and not s.was_alive:
            s.life_from = t
        s.was_alive = bool(w[2])

    def goal(s, t, r):
        s.goals.append((t, r.get("goal"), r.get("veh", -1)))
        while s.goals and t - s.goals[0][0] > KEEP:
            s.goals.popleft()


def fatal_fight(rows):
    """(index of the fight's first damaged row, index of the last row before it, damage before the fight within
    SHIELD_BACK) in rows (t, shield, health) up to the death: the damage since the last FIGHT_GAP without any."""
    hits = [i for i in range(1, len(rows))
            if (rows[i - 1][1] + rows[i - 1][2]) - (rows[i][1] + rows[i][2]) > HURT_STEP]
    if not hits:
        return len(rows) - 1, max(0, len(rows) - 2), False      # (killed between two rows)
    k = len(hits) - 1
    while k > 0 and rows[hits[k]][0] - rows[hits[k - 1]][0] <= FIGHT_GAP:
        k -= 1
    first = hits[k]
    before = [i for i in hits[:k] if rows[first][0] - rows[i][0] <= SHIELD_BACK]
    return first, first - 1, bool(before)


def autopsy(pl, k, t, world, los):
    """One death of player pl at t from kill row k, world: [(t, {id: world row})] before it."""
    v = pl.id
    kind, killer, weapon = kill_record.read(k) or ("death", None, k.get("c"))
    d = dict(t=t, id=v, kind=kind, killer=killer, weapon=weapon, c=k.get("c"), killer_bot=bool(k.get("kb")),
             life=(t - pl.life_from) if pl.life_from is not None else None, goal=None, end_goal=None)
    snaps = [(tt, W) for tt, W in world if tt <= t + 0.05 and v in W and W[v][2]
             and (pl.life_from is None or tt >= pl.life_from)]
    if not snaps:
        d.update(shield=None, health=None, seen=None, took=None, shooters=1, veh=False, killer_hp=None, dist=None)
        return d
    rows = [(tt, W[v][6], W[v][7]) for tt, W in snaps]
    first, pre, recent = fatal_fight(rows)
    t0 = rows[first][0]
    sh, hl = rows[pre][1], rows[pre][2]
    if sh < FULL and not recent:            # (the 0 read: untouched SHIELD_BACK s before the fight, it was full)
        sh = 1.0
    me = snaps[-1][1][v]
    enemies = {i for _, W in snaps for i, w in W.items() if w[1] != me[1]}
    window = (t - t0 + 0.5) * TICKS                             # (damage of the fatal fight, not one before it)
    shooters = {h[0] for h in k.get("hits") or [] if h[0] is not None and h[0] != v and h[0] in enemies
                and (h[3] or 0) + (h[4] or 0) > 0 and (h[5] or 0) <= window}
    if killer is not None and killer in enemies:
        shooters.add(killer)
    seen = None
    if killer is not None and killer in enemies:
        seen = any(killer in W and in_view(W[v], W[killer], los) for tt, W in snaps
                   if t0 - SEEN_BEFORE <= tt <= t0 + SEEN_GRACE)
    took = any(len(W[v]) > 14 and W[v][14] not in (-1, None) for tt, W in snaps if t0 - TOOK <= tt <= t0 + 0.05)
    kw = snaps[-1][1].get(killer)
    veh = len(me) > 16 and me[16] is not None
    if pl.bot is not None:
        g = [x for x in pl.goals if x[0] <= t + 0.05]
        before = [x for x in g if x[0] <= t0] or g[:1]
        d.update(goal=before[-1][1] if before else None, end_goal=g[-1][1] if g else None)
        veh = veh or any(x[2] not in (None, -1) for x in g[-3:])
    vp, kp = k.get("vp"), k.get("kp")
    d.update(shield=sh, health=hl, seen=seen, took=took, shooters=len(shooters), veh=veh,
             killer_hp=(kw[6], kw[7]) if kw else None, fight_s=t - t0,
             dist=math.dist(vp, kp) if vp and kp else None)
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
    if d.get("took") is not None:
        out.add("took the fight" if d["took"] else "caught")
    if d.get("end_goal") == "retreat":
        out.add("breaking off")
    if d.get("life") is not None and d["life"] < SPAWN_S:
        out.add("off his spawn")
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


def read_trace(path, los=None):
    """(deaths, players) of one trace: deaths a list of autopsy dicts (each with "map", "group", "who"), players
    {id: Player}. los: a line-of-sight test (default: the trace's map, map_los)."""
    players, deaths, mp, world, expose_t = {}, [], None, collections.deque(), -99.0
    variant = None
    get = lambda i: players.setdefault(i, Player(i))           # noqa: E731
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = _ID.match(line)
            if m:
                i = int(m.group(1))
                if i in players and players[i].bot is not None:
                    r = json.loads(line)
                    players[i].goal(r["t"], r)
                continue
            m = _KEY.match(line)
            if not m:
                continue
            key = m.group(1)
            if key == "meta":
                r = json.loads(line)
                b = r["meta"].get("bot") or {}
                mp = mp or r["meta"].get("map")
                variant = variant or r["meta"].get("variant")
                if "id" in b:
                    get(b["id"]).bot = (b.get("tier", "?"), b.get("name", "?"))
            elif key == "mode":
                r = json.loads(line)
                if "world" not in r:
                    continue
                t, W = r["t"], {w[0]: w for w in r["world"]}
                for i, w in W.items():
                    get(i).world(t, w)
                if t - expose_t >= EXPOSE_EVERY:
                    if los is None and mp is not None:
                        los = terrain_los(path, mp, variant)
                    ex = exposure(W, los)
                    for i, n in ex.items():
                        players[i].seen_by[min(n, 2)] += t - expose_t if t - expose_t < 2 * EXPOSE_EVERY else EXPOSE_EVERY
                    for p in players.values():
                        p.two(t, ex.get(p.id, 0) >= 2)
                    expose_t = t
                world.append((t, W))
                while world and t - world[0][0] > KEEP:
                    world.popleft()
            elif key == "kill":
                r = json.loads(line)
                k, t = r["kill"], r["t"]
                if k.get("st") == kill_record.OVER:
                    continue
                kind, killer, _ = kill_record.read(k) or (None, None, None)
                if kind == "kill" and killer is not None:
                    get(killer).kills += 1
                v = k.get("v")
                if isinstance(v, int):
                    if los is None and mp is not None:
                        los = terrain_los(path, mp, variant)
                    deaths.append(autopsy(get(v), k, t, world, los))
                    get(v).life_from, get(v).was_alive = None, False
    people = [i for i, p in players.items() if p.bot is None and p.last_t is not None]
    for p in players.values():
        p.group = p.bot[0] if p.bot else (YOU if len(people) == 1 else PEOPLE)
        p.name = p.bot[1] if p.bot else p.group
    for d in deaths:
        p = players[d["id"]]
        d.update(map=mp or os.path.basename(path), group=p.group, who=p.name)
        for x in p.twos:                    # (died while 2+ saw him, or within TWO_DIED s after)
            if x[0] <= d["t"] <= x[1] + TWO_DIED:
                x[2] = True
    return deaths, players


def pct(n, d):
    return f"{100 * n / d:.0f}%" if d else "-"


def label(g):
    return NAMES_OF.get(g, g)


def summary(deaths, players, group):
    mine = [d for d in deaths if group == "all" or d["group"] == group]
    them = [p for pp in players for p in pp.values() if (group == "all" or p.group == group) and p.last_t is not None]
    alive = sum(p.alive_s for p in them)
    kills = sum(p.kills for p in them)
    return mine, kills, alive


def report(deaths, players, group, matches, out=print):
    mine, kills, alive = summary(deaths, players, group)
    n = len(mine)
    out(f"{label(group)}: {n} deaths in {matches} matches, {kills} kills (K/D {kills / n:.2f})" if n else
        f"{label(group)}: no deaths in {matches} matches ({kills} kills)")
    if alive:
        out(f"  {10 * 60 * n / alive:.1f} deaths per 10 minutes alive ({alive / 60:.0f} minutes alive)")
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
        far = f"median {statistics.median(dists):5.1f} u" if dists else " " * 14
        out(f"  {name:16} {by[name]:4}  {pct(by[name], n):>4}   killed by a person {hum:3}   {far}   {what}")
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
    if goals:
        out("a bot's goal when the fatal fight started: " + ", ".join(f"{g} {c}" for g, c in goals.most_common(8)))


def order(groups):
    first = [g for g in (YOU, PEOPLE, "demon", "top") if g in groups]
    return first + sorted(g for g in groups if g not in first)


def compare(deaths, players, out=print, groups=None):
    """Every group side by side: the rates, each cause's share and each condition's."""
    groups = groups or order({d["group"] for d in deaths})
    cols = []
    for g in groups:
        mine, kills, alive = summary(deaths, players, g)
        cols.append((g, mine, kills, alive))
    w = 11
    out("side by side (share of each one's deaths)")
    out(f"  {'':22}" + "".join(f"{label(g)[:w - 1]:>{w}}" for g in groups))
    out(f"  {'deaths':22}" + "".join(f"{len(m):>{w}}" for _, m, _, _ in cols))
    out(f"  {'K/D':22}" + "".join(f"{(k / len(m) if m else 0):>{w}.2f}" for _, m, k, _ in cols))
    out(f"  {'deaths / 10 min alive':22}" + "".join(f"{(600 * len(m) / a if a else 0):>{w}.1f}" for _, m, _, a in cols))
    out("  cause")
    for name, _ in CAUSES:
        out(f"    {name:20}" + "".join(f"{pct(sum(cause(d) == name for d in m), len(m)):>{w}}" for _, m, _, _ in cols))
    out("  also true of")
    for name, _ in TAGS:
        out(f"    {name:20}" + "".join(f"{pct(sum(name in tags(d) for d in m), len(m)):>{w}}" for _, m, _, _ in cols))
    out("  time alive on foot (every 0.5 s: the enemies within 40 u with him in view and a line of sight)")
    seen = []
    for g in groups:
        c = collections.Counter()
        for pp in players:
            for p in pp.values():
                if g == "all" or p.group == g:
                    c.update(p.seen_by)
        seen.append(c)
    for n, what in ((0, "seen by nobody"), (1, "seen by 1 enemy"), (2, "seen by 2+ at once")):
        out(f"    {what:20}" + "".join(f"{pct(c[n], sum(c.values())):>{w}}" for c in seen))
    out(f"    {'2+ of all time seen':20}" + "".join(f"{pct(c[2], c[1] + c[2]):>{w}}" for c in seen))
    out("  each time 2+ enemies saw him at once")
    twos = [[x for pp in players for p in pp.values() if g == "all" or p.group == g for x in p.twos] for g in groups]
    out(f"    {'times / 10 min alive':20}" + "".join(
        f"{(600 * len(x) / a if a else 0):>{w}.1f}" for x, (_, _, _, a) in zip(twos, cols)))
    out(f"    {'died in it':20}" + "".join(f"{pct(sum(y[2] for y in x), len(x)):>{w}}" for x in twos))
    for what, pick in (("lasted, survived s", lambda y: not y[2]), ("lasted, died s", lambda y: y[2])):
        out(f"    {what:20}" + "".join(
            f"{statistics.median(y[1] - y[0] + EXPOSE_EVERY for y in x if pick(y)):>{w}.1f}"
            if any(pick(y) for y in x) else f"{'-':>{w}}" for x in twos))
    out("  median of the fatal fight")
    for key, what in (("dist", "killer's distance u"), ("fight_s", "fight length s")):
        row = []
        for _, m, _, _ in cols:
            v = [d[key] for d in m if d.get(key) is not None and d["kind"] == "kill"]
            row.append(f"{statistics.median(v):>{w}.1f}" if v else f"{'-':>{w}}")
        out(f"    {what:20}" + "".join(row))


def listing(deaths, group, out=print):
    out("\nevery death")
    for d in deaths:
        if group != "all" and d["group"] != group:
            continue
        sh = "  -  " if d.get("shield") is None else f"{d['shield']:.2f}/{d['health']:.2f}"
        kh = f"{d['killer_hp'][0]:.2f}" if d.get("killer_hp") else " -  "
        far = "" if d.get("dist") is None else f"{d['dist']:.0f} u"
        goal = f" goal {str(d.get('goal'))[:9]:9} -> {str(d.get('end_goal'))[:9]:9}" if d.get("goal") else ""
        out(f"  {d['map'][:24]:24} t={d['t']:6.1f} {d['who'][:14]:14} {cause(d):15} went in {sh} "
            f"{'took it' if d.get('took') else 'caught '} {NAMES.get(d['c'], d['c'])!s:16} {far:>5} "
            f"shooters {d['shooters']} saw {d.get('seen')!s:5} his shield {kh} "
            f"{'bot' if d['killer_bot'] else 'person'}{goal}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("traces", nargs="*")
    ap.add_argument("--tier", help="one group's report: demon, top, ..., you, people or all (default: the comparison)")
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
    deaths, players = [], []
    for p in paths:
        ds, ps = read_trace(p)
        deaths += ds
        players.append(ps)
    if a.tier:
        report(deaths, players, a.tier, len(paths))
    else:
        print(f"{len(deaths)} deaths in {len(paths)} matches with kill rows")
        compare(deaths, players)
    if a.list:
        listing(deaths, a.tier or "all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
