"""(custom, Nov 22) Noble, the testing bot: four more things it learns (the owner: "Do pre aim first and then into
number 4, then number 5, and number 6 until completion, noble only"). Read only for a Noble (profiles.fixed_noble);
Demon and every other difficulty are untouched. Kept in user/ (this PC's own, never committed: players' names).

4. Pre-aim (Sights, preaim): each time a Noble first sees a man (Perception's new sighting, none of him in its own
   eyes for SIGHT_GAP s), the cell it stood in and where he came into view. With nobody known, a Noble looks where men
   came into view most from where it stands (its cell, the next cells at half weight), a line to it, at head height.
5. Each player's habits (the same sightings by name, Escapes): a person's sightings count PLAYER_W x more while he
   is on the other team, so his own angles win out as his count grows; and where a person (not a bot) went
   ESCAPE_AFTER s after he left a Noble's sight hurt (shield ESCAPE_SHIELD or less): a Noble guessing where he hides
   now takes the place he went most from there once he has ESCAPE_MIN such escapes (all people's together:
   ESCAPE_MIN_ALL).
6. Dodging (Dodges): each juke a Noble makes under fire is one of DODGES; the damage it takes in the next DODGE_WINDOW
   s, less the damage the man it fights takes, is that dodge's cost. It picks the one that cost least (his own count PLAYER_W x more against a person), now
   and then another (DODGE_EXPLORE).
7. Team focus (Focus): each fight a Noble has is "focus" (a teammate fought the same man in it) or "solo"; its value
   is 1 for his death, -1 for its own and -FOCUS_MATE_COST per teammate lost meanwhile. Once both have FOCUS_MIN
   fights in a distance band and one is FOCUS_EDGE better, a Noble leans on it: joining a teammate's man, or
   spreading off him.

Nothing here reaches the game: choices for the bot only."""
import math
import time

from . import noble
from .core import Vec, dist

SIGHTS_FILE = "noble_sights.json"
ESCAPES_FILE = "noble_escapes.json"
DODGES_FILE = "noble_dodges.json"
FOCUS_FILE = "noble_focus.json"
SAVE_EVERY_N, SAVE_EVERY_S = 20, 60.0

CELL = 2.0                  # u: the cells places are counted in
HEAD = 0.62                 # u over a place's mean: a standing man's head (as spawn_look, danger_look)

# --- 4. pre-aim ---
SIGHT_GAP = 3.0             # s: not in its own eyes this long before, a sighting counts
SIGHT_MIN = 3.0             # weighted sightings at an angle before it is pre-aimed
SIGHT_NEAR_W = 0.5          # the weight of the next cells' sightings (its own cell 1)
SIGHT_R = (3.0, 45.0)       # u: the angles pre-aimed at, this near and far
PREAIM_KEEP = 0.4           # s a pre-aim is kept before it is looked for again
PLAYER_W = 2.0              # x a person's own count, while he plays on the other team (5.: fades in as it grows)
CELLS_MAX = 6000            # cells kept a layout (the least seen go)

# --- 5. a person's escapes ---
ESCAPE_SHIELD = 0.5
ESCAPE_AFTER = 2.5          # s after he left its sight: where he got to
ESCAPE_MIN, ESCAPE_MIN_ALL = 3, 6
ESCAPE_SHARE = 0.4          # of his escapes from there that went to one place, to guess it
ESCAPE_GUESS_AFTER = 1.0    # s since it last knew where he was before the learned place is guessed

# --- 6. dodges ---
DODGES = ("flip", "keep", "crouch", "jump", "stop")
DODGE_WINDOW = 0.6          # s: the damage taken this long after the juke is its cost
DODGE_PRIOR, DODGE_PRIOR_N = 0.0, 3.0      # a dodge never tried: this cost (taken less dealt), worth this many
DODGE_EXPLORE = 0.15

# --- 7. team focus ---
FOCUS_BANDS = (8.0, 16.0)   # u: the bands' upper edges
FOCUS_MIN = 8
FOCUS_EDGE = 0.1
FOCUS_MATE_COST = 0.5
FOCUS_DROP_S = 3.0          # s off him (another goal) before a fight is over as a break (not counted)
FOCUS_BONUS = 1.3           # x the threat of a man a teammate fights (focus better), or / it (solo better)


def cell(p):
    return f"{int(math.floor(p.x / CELL))},{int(math.floor(p.y / CELL))},{int(math.floor(p.z / CELL))}"


def near_cells(p):
    """(key, weight): p's cell (1) and the 8 round it on its floor (SIGHT_NEAR_W)."""
    cx, cy, cz = int(math.floor(p.x / CELL)), int(math.floor(p.y / CELL)), int(math.floor(p.z / CELL))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            yield f"{cx + dx},{cy + dy},{cz}", (1.0 if dx == dy == 0 else SIGHT_NEAR_W)


def vit(p):
    return p.shield + p.health


class Store:
    """One file's counts, written every SAVE_EVERY_N changes or SAVE_EVERY_S s (noble._write: nothing in the sim)."""

    def __init__(s, name):
        s.name = name
        s.data = noble._read(name)
        s.new, s.saved_at = 0, time.time()

    def changed(s):
        s.new += 1
        if s.new >= SAVE_EVERY_N or time.time() - s.saved_at > SAVE_EVERY_S:
            s.flush()

    def flush(s):
        if s.new and noble._write(s.name, s.data):
            s.new = 0
        s.saved_at = time.time()


_STORES = {}


def store(name):
    key = (name, noble.STORE_DIR)
    if key not in _STORES:
        _STORES[key] = Store(name)
    return _STORES[key]


def reload():
    _STORES.clear()


def flush_all():
    for st in _STORES.values():
        st.flush()


# --- 4. pre-aim, and 5. a person's angles --------------------------------------------------------------------------
def add_sight(layout, me_pos, his_pos, name=None):
    """A Noble at me_pos first saw a man at his_pos (name: a person's, None for a bot)."""
    if not layout:
        return
    st = store(SIGHTS_FILE)
    cells = st.data.setdefault(layout, {})
    mine = cells.setdefault(cell(me_pos), {})
    e = mine.setdefault(cell(his_pos), [0, 0.0, 0.0, 0.0, {}])
    e[0] += 1
    e[1], e[2], e[3] = round(e[1] + his_pos.x, 2), round(e[2] + his_pos.y, 2), round(e[3] + his_pos.z, 2)
    if name:
        e[4][name] = e[4].get(name, 0) + 1
    if len(cells) > CELLS_MAX:
        least = min(cells, key=lambda k: sum(v[0] for v in cells[k].values()))
        del cells[least]
    st.changed()


def preaim(layout, me_pos, eye_pos, los, people=(), ok=None):
    """(point, weighted count) where men came into view most from where a Noble stands, a line from eye_pos to it, or
    None. people: the names of the persons on the other team now (their own sightings PLAYER_W x more); ok(point):
    a further check (the walking cone)."""
    cells = store(SIGHTS_FILE).data.get(layout) if layout else None
    if not cells:
        return None
    pool = {}
    for key, w in near_cells(me_pos):
        for k, e in (cells.get(key) or {}).items():
            n = e[0]
            if n <= 0:
                continue
            own = sum(e[4].get(nm, 0) for nm in people) if people else 0
            got = pool.setdefault(k, [0.0, 0.0, 0.0, 0.0, 0.0])    # score, sums of x y z, weighted count
            got[0] += w * (n + PLAYER_W * own)
            got[1], got[2], got[3] = got[1] + w * e[1], got[2] + w * e[2], got[3] + w * e[3]
            got[4] += w * n
    best = None
    for k, g in sorted(pool.items(), key=lambda kv: -kv[1][0]):
        if g[0] < SIGHT_MIN:
            break
        wn = g[4]
        q = Vec(g[1] / wn, g[2] / wn, g[3] / wn + HEAD)
        if not SIGHT_R[0] < dist(me_pos, q) < SIGHT_R[1]:
            continue
        if ok is not None and not ok(q):
            continue
        try:
            if not los(eye_pos, q):
                continue
        except Exception:
            continue
        best = (q, g[0])
        break
    return best


# --- 5. a person's escapes -----------------------------------------------------------------------------------------
def add_escape(layout, name, from_pos, to_pos):
    if not layout or not name:
        return
    st = store(ESCAPES_FILE)
    who = st.data.setdefault(layout, {}).setdefault(name, {})
    e = who.setdefault(cell(from_pos), {}).setdefault(cell(to_pos), [0, 0.0, 0.0, 0.0])
    e[0] += 1
    e[1], e[2], e[3] = round(e[1] + to_pos.x, 2), round(e[2] + to_pos.y, 2), round(e[3] + to_pos.z, 2)
    st.changed()


def escape_to(layout, name, from_pos):
    """(place, n, share) where the person name went most, hurt, from where he left a Noble's sight: his own once he has
    ESCAPE_MIN escapes from there, else all people's once ESCAPE_MIN_ALL; None otherwise."""
    lay = store(ESCAPES_FILE).data.get(layout) if layout else None
    if not lay or not name:
        return None
    key = cell(from_pos)
    for rows, need in (([lay.get(name, {}).get(key, {})], ESCAPE_MIN),
                       ([w.get(key, {}) for w in lay.values()], ESCAPE_MIN_ALL)):
        tot = {}
        for r in rows:
            for k, e in r.items():
                t = tot.setdefault(k, [0, 0.0, 0.0, 0.0])
                for i in range(4):
                    t[i] += e[i]
        n_all = sum(t[0] for t in tot.values())
        if n_all < need:
            continue
        k, t = max(tot.items(), key=lambda kv: kv[1][0])
        share = t[0] / n_all
        if share < ESCAPE_SHARE:
            return None
        return Vec(t[1] / t[0], t[2] / t[0], t[3] / t[0]), t[0], share
    return None


class EscapeWatch:
    """One Noble's men leaving its sight hurt, each resolved ESCAPE_AFTER s on to where he got (persons only)."""

    def __init__(s, layout):
        s.layout = layout
        s.pending = []          # (t, id, name, from)
        s.seen_prev = set()

    def tick(s, now, snap, me, seen_now):
        """seen_now: the ids in its own eyes this tick (dead: nobody left its sight, it stopped looking)."""
        if not me.alive:
            seen_now, s.seen_prev = (), set()
        for k in s.seen_prev - set(seen_now):
            e = snap.player(k)
            if (e is not None and e.alive and not e.is_bot and e.team != me.team and e.shield <= ESCAPE_SHIELD
                    and e.vehicle in (None, -1)):
                s.pending.append((now, k, e.name, e.pos))
        s.seen_prev = set(seen_now)
        keep = []
        for t, k, name, p in s.pending:
            if now - t < ESCAPE_AFTER:
                keep.append((t, k, name, p))
                continue
            e = snap.player(k)
            if e is not None and e.alive and e.name == name:
                add_escape(s.layout, name, p, e.pos)
        s.pending = keep


# --- 6. dodges -----------------------------------------------------------------------------------------------------
def _dodge_rows(game, name):
    d = store(DODGES_FILE).data.setdefault(game or "", {})
    return d.setdefault("all", {}), (d.setdefault("who", {}).setdefault(name, {}) if name else {})


def dodge_cost(game, style, name=None):
    """(cost, n): the mean damage a dodge took in DODGE_WINDOW s (his own PLAYER_W x more against a person), with the
    prior."""
    allr, mine = _dodge_rows(game, name)
    n = s = 0.0
    a = allr.get(style)
    if a:
        n, s = n + a[0], s + a[1]
    m = mine.get(style) if mine else None
    if m:
        n, s = n + PLAYER_W * m[0], s + PLAYER_W * m[1]
    return (s + DODGE_PRIOR * DODGE_PRIOR_N) / (n + DODGE_PRIOR_N), n


def dodge_pick(game, rng, name=None):
    if rng.random() < DODGE_EXPLORE:
        return rng.choice(DODGES)
    return min(DODGES, key=lambda st: (dodge_cost(game, st, name)[0], DODGES.index(st)))


def add_dodge(game, style, cost, name=None):
    st = store(DODGES_FILE)
    allr, mine = _dodge_rows(game, name)
    for rows in ((allr, mine) if name else (allr,)):
        e = rows.setdefault(style, [0, 0.0])
        e[0] += 1
        e[1] = round(e[1] + cost, 4)
    st.changed()


class DodgeWatch:
    """One Noble's jukes under fire, each resolved DODGE_WINDOW s on: the damage taken meanwhile less the damage the
    man it fights took (a dodge that spoils its own shots costs too: in the simulator, scored on damage taken alone,
    it learnt to jump on 6 of 10 jukes)."""

    def __init__(s, game):
        s.game = game
        s.pending = []          # (t, style, vitals, name, his id, his vitals)

    def juked(s, now, me, style, name=None, foe=None):
        s.pending.append((now, style, vit(me), name, getattr(foe, "id", None), vit(foe) if foe is not None else None))

    def tick(s, now, me, snap=None):
        keep = []
        for row in s.pending:
            t, style, v0, name, fid, f0 = row
            dead = me is None or not me.alive
            if not dead and now - t < DODGE_WINDOW:
                keep.append(row)
                continue
            cost = v0 if dead else max(0.0, v0 - vit(me))
            foe = snap.player(fid) if snap is not None and fid is not None else None
            if foe is not None and f0 is not None:
                cost -= f0 if not foe.alive else max(0.0, f0 - vit(foe))
            add_dodge(s.game, style, cost, name)
        s.pending = keep


# --- 7. team focus -------------------------------------------------------------------------------------------------
def focus_band(d):
    for i, edge in enumerate(FOCUS_BANDS):
        if d < edge:
            return i
    return len(FOCUS_BANDS)


def add_fight(game, kind, b, value):
    st = store(FOCUS_FILE)
    e = st.data.setdefault(game or "", {}).setdefault(kind, {}).setdefault(str(b), [0, 0.0])
    e[0] += 1
    e[1] = round(e[1] + value, 3)
    st.changed()


def focus_lean(game, b):
    """+1: joining a teammate's man has done better in band b, -1: fighting a man of its own has, 0: not known yet."""
    d = store(FOCUS_FILE).data.get(game or "", {})
    f, o = d.get("focus", {}).get(str(b)), d.get("solo", {}).get(str(b))
    if not f or not o or f[0] < FOCUS_MIN or o[0] < FOCUS_MIN:
        return 0
    vf, vo = f[1] / f[0], o[1] / o[0]
    if vf > vo + FOCUS_EDGE:
        return 1
    if vo > vf + FOCUS_EDGE:
        return -1
    return 0


class FocusWatch:
    """One Noble's fights: started on a man in its eyes, focus once a teammate fought him meanwhile, over at his death
    (1), its own (-1, and that is the value), or off him FOCUS_DROP_S s (a break: not counted)."""

    def __init__(s, game):
        s.game = game
        s.fight = None          # dict: k, t, band, focus, mates_alive, off

    def tick(s, now, snap, me, k, in_sight, mate_on):
        f = s.fight
        mates = {p.id for p in snap.players if me is not None and p.team == me.team and p.id != me.id and p.alive}
        if f is not None:
            e = snap.player(f["k"])
            f["lost"] |= f["mates"] - mates          # (a teammate down meanwhile, back or not by the end)
            lost = len(f["lost"])
            if me is None or not me.alive:
                s.end(f, -1.0 - FOCUS_MATE_COST * lost)
                return
            if e is None or not e.alive:
                s.end(f, 1.0 - FOCUS_MATE_COST * lost)
                return
            if k == f["k"]:
                f["off"] = None
                f["focus"] = f["focus"] or mate_on
            elif f["off"] is None:
                f["off"] = now
            elif now - f["off"] > FOCUS_DROP_S:
                s.fight = None
            if s.fight is not None:
                return
        if me is not None and me.alive and k is not None and in_sight:
            e = snap.player(k)
            if e is not None and e.alive:
                s.fight = dict(k=k, t=now, band=focus_band(dist(me.pos, e.pos)), focus=mate_on, mates=set(mates),
                               lost=set(), off=None)

    def end(s, f, value):
        add_fight(s.game, "focus" if f["focus"] else "solo", f["band"], value)
        s.fight = None
