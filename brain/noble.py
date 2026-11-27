"""(custom, Nov 20) Noble, the testing bot: what it learns. The owner: "I want Noble to be our testing bot. So anything
self learning we can give it ... we can try here"; "DO 1,2 and 4" (self-play tuning, shot learning, where it wins).
Demon and every other difficulty are untouched: each piece is read only for a Noble (profiles.fixed_noble).

1. Self-play tuning (tune, skips): Noble's fighting settings, which of Demon's rules it keeps and how hard it pushes,
   read from user/noble_tune.json (tools/noble_tune.py plays Noble against Demon in the simulator and writes the
   winner). With no file: DEFAULTS, Demon's rules all on (the 4v4 Asylum sims and the owner's three live games of
   Nov 20: Demon 4-0 and 3-0, the side that hit first won; Noble's pushes walked into held angles).
2. Shot learning (ShotWatch, gap, part): each press of a precision gun is watched for his shield or body dropping
   within SHOT_WINDOW s (a hit) or not (a miss), by distance band, the pace since its last shot and the part aimed at;
   kept in user/noble_shots.json (all Nobles share it). From it: the pace that lands the most rounds a second, and
   head or chest while his shield holds (a head shot counts only once it is down: the bigger part first if it lands
   more). Rounds a teammate may have landed are not counted.
3. Where it wins (spot_for): from the layout's map memory (brain/lore.py kills: where each killer and victim stood),
   each SPOT_CELL cell's wins and losses; a Noble walking at a man it cannot see takes a winning cell near it with a
   line to where he is and holds it (Bot.noble_spot) instead.

Nothing here reaches the game: settings and choices for the bot only."""
import json
import math
import os
import time

from . import profiles
from .core import Vec, dist

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(ROOT, "user")      # (tools/noble_tune.py and the tests point it elsewhere)
SAVE = True                                 # (the simulator's workers: False, nothing written)
TUNE_FILE = "noble_tune.json"
SHOTS_FILE = "noble_shots.json"

# --- 1. self-play tuning --------------------------------------------------------------------------------------------
# rule switches (1: Noble keeps Demon's rule, 0: off) and numbers. push: a fight with a man in view over its best other
# choice (0: Demon's own choice), only at push_shield or more; long_pace: x the paced gap past 10 u; spots: hold winning
# cells (3.); spot_hold_s: how long it holds one before walking on; explore: a share of shots tried at another pace or
# part (2.)
DEFAULTS = dict(recharge=1, no_new_fight=1, break_second=1, odds=1, peek=1, objective=1, chase=1,
                push=0.0, push_shield=0.95, long_pace=1.2, spots=1, spot_hold_s=3.0, shot_learn=1, explore=0.12,
                preaim=1, habits=1, dodge_learn=1, focus_learn=1,   # (Nov 22: brain/noble_habits.py's four)
                take_space=1,                                       # (Nov 22: Bot.take_space)
                owner_spots=1)                                      # (Nov 27: Bot.noble_rotation)
RULES = ("recharge", "no_new_fight", "break_second", "odds", "peek", "objective", "chase")
OVERRIDE = None                             # a dict: these settings over the file's (tools/noble_tune.py, tests)
_TUNE = {}


def _read(name):
    try:
        with open(os.path.join(STORE_DIR, name), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(name, data):
    if not SAVE:
        return False
    path = os.path.join(STORE_DIR, name)
    try:
        os.makedirs(STORE_DIR, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def tune(game=None):
    """Noble's settings for this game: DEFAULTS, the tuned ones of user/noble_tune.json over them, OVERRIDE over all."""
    key = (game or "", STORE_DIR)
    if key not in _TUNE:
        got = (_read(TUNE_FILE).get(game or "") or {}).get("settings") or {}
        _TUNE[key] = {k: type(DEFAULTS[k])(v) for k, v in got.items() if k in DEFAULTS}
    out = dict(DEFAULTS)
    out.update(_TUNE[key])
    if OVERRIDE:
        out.update({k: v for k, v in OVERRIDE.items() if k in DEFAULTS})
    return out


def reload():
    """Forget what was read (a new tune written, a test's own folder)."""
    _TUNE.clear()
    _BOOK.clear()
    from . import noble_habits      # (Nov 22: its four stores too)
    noble_habits.reload()


def skips(prof, rule, game=None):
    """A Noble with this Demon rule tuned off (1.): the rule is skipped for it."""
    return profiles.fixed_noble(prof) and not tune(game).get(rule, 1)


def save_tune(game, settings, **facts):
    """Write a tuned set for game (tools/noble_tune.py): settings and how it was found."""
    d = _read(TUNE_FILE)
    d[game] = dict(settings={k: settings[k] for k in DEFAULTS if k in settings}, when=time.strftime("%Y-%m-%d %H:%M"),
                   **facts)
    ok = _write(TUNE_FILE, d)
    _TUNE.clear()
    return ok


# --- 2. shot learning -----------------------------------------------------------------------------------------------
BANDS = (4.0, 8.0, 14.0, 22.0)              # u: the distance bands' upper edges (the last band past 22)
PACES = (0.8, 0.9, 1.0, 1.15, 1.3)          # x its base gap (FIRE_GAP, long_pace past 10 u): the paces tried
REST = 1.6                                  # x the base gap or more since the last shot: a first shot ("rest")
SHOT_WINDOW = 0.3                           # s after a press his shield or body must drop by (hitscan, the read lag)
DROP = 0.01                                 # of his shield + body: a drop this big or more is a hit
PRIOR_RATE, PRIOR_N = 0.8, 4.0              # a pace or part never tried: this hit rate, worth this many shots
PART_MIN = 10                               # shots at each part in a band before the learned part is used
PART_EDGE = 0.05                            # the chest's rate this much over the head's to aim at it
MATE_AIM = 0.2                              # rad: a teammate firing this near the line to him may have landed it
SAVE_EVERY_N, SAVE_EVERY_S = 20, 60.0       # new shots / seconds between writes of user/noble_shots.json
_BOOK = {}


def band(d):
    for i, edge in enumerate(BANDS):
        if d < edge:
            return i
    return len(BANDS)


def pace_bin(ratio):
    """The nearest of PACES to a gap / base gap, or "rest" for a first shot."""
    if ratio >= REST:
        return "rest"
    return min(PACES, key=lambda p: abs(p - ratio))


class Book:
    """The shared counts: {game: {weapon: {"band|pace|part": [shots, hits]}}}, written now and then."""

    def __init__(s):
        s.data = _read(SHOTS_FILE)
        s.new, s.saved_at = 0, time.time()

    def counts(s, game, weapon):
        return s.data.setdefault(game, {}).setdefault(weapon, {})

    def add(s, game, weapon, b, pace, part, hit):
        c = s.counts(game, weapon).setdefault(f"{b}|{pace}|{part}", [0, 0])
        c[0] += 1
        c[1] += 1 if hit else 0
        s.new += 1
        if s.new >= SAVE_EVERY_N or time.time() - s.saved_at > SAVE_EVERY_S:
            s.flush()

    def flush(s):
        if s.new and _write(SHOTS_FILE, s.data):
            s.new = 0
        s.saved_at = time.time()

    def rate(s, game, weapon, b, pace=None, part=None, prior=PRIOR_RATE):
        """(hit rate with the prior, shots) over the cells that match (None: any)."""
        n = h = 0
        for k, (cn, ch) in s.counts(game, weapon).items():
            kb, kp, kpart = k.split("|")
            if int(kb) == b and (pace is None or kp == str(pace)) and (part is None or kpart == part):
                n, h = n + cn, h + ch
        return (h + prior * PRIOR_N) / (n + PRIOR_N), n


def book():
    if STORE_DIR not in _BOOK:
        _BOOK[STORE_DIR] = Book()
    return _BOOK[STORE_DIR]


def vit(p):
    return p.shield + p.health


class ShotWatch:
    """One Noble's own presses, each resolved a hit or a miss (Bot.noble_learn every tick, Bot.noble_fired at a press)."""

    def __init__(s, game):
        s.game = game
        s.pending = []        # dicts: t, tid, vit, weapon, band, pace, part, mates {id: rounds}
        s.last_press = {}     # weapon: when it last pressed it
        s.hits = s.misses = s.skipped = s.dry_presses = 0

    @staticmethod
    def rounds(p):
        return sum(m for m in (p.mag or []) if m is not None and m >= 0)

    @staticmethod
    def mag_of(p, weapon):
        """Rounds in weapon's magazine (-1: not known, or not carried)."""
        w = list(p.weapons or [])
        if weapon not in w:
            return -1
        i = w.index(weapon)
        m = (p.mag or [])[i] if i < len(p.mag or []) else -1
        return m if m is not None else -1

    def pressed(s, now, snap, me, tid, d, weapon, head, base_gap):
        """A press of a precision gun at tid d u off, aiming at the head (or the chest), its base gap base_gap s."""
        target = snap.player(tid) if tid is not None else None
        s.resolve(now, snap, me)
        last = s.last_press.get(weapon)
        s.last_press[weapon] = now
        if target is None or not target.alive:
            return
        ratio = (now - last) / max(base_gap, 1e-3) if last is not None else REST
        mates = {p.id: s.rounds(p) for p in snap.players if p.team == me.team and p.id != me.id and p.alive}
        s.pending.append(dict(t=now, tid=tid, vit=vit(target), weapon=weapon, band=band(d), pace=pace_bin(ratio),
                              part="head" if head else "chest", mates=mates, mag=s.mag_of(me, weapon)))

    def mate_fired(s, snap, shot):
        """A teammate fired at him since the press (his rounds went down and he faces him): not ours to count."""
        target = snap.player(shot["tid"])
        for p in snap.players:
            was = shot["mates"].get(p.id)
            if was is None or not p.alive or s.rounds(p) >= was:
                continue
            if target is None:
                return True
            yaw = math.atan2(target.pos.y - p.pos.y, target.pos.x - p.pos.x)
            if abs(math.remainder(yaw - p.yaw, 2 * math.pi)) < MATE_AIM + math.atan2(0.5, max(dist(p.pos, target.pos), 0.5)):
                return True
        return False

    def resolve(s, now, snap, me):
        """Each shot whose man dropped (a hit), or whose window ran out (a miss); one a teammate may have hit: dropped."""
        keep = []
        for shot in s.pending:
            target = snap.player(shot["tid"])
            dropped = target is not None and (not target.alive or vit(target) < shot["vit"] - DROP)
            late = now - shot["t"] > SHOT_WINDOW
            if not dropped and not late:
                keep.append(shot)
                continue
            if target is None or s.mate_fired(snap, shot):
                s.skipped += 1
                continue
            m0, m1 = shot.get("mag", -1), s.mag_of(me, shot["weapon"])
            if m0 >= 0 and m1 >= 0 and m1 >= m0:
                # (Nov 20, live: presses while a grenade left the hand, or on an empty magazine, fired no round: 10-12
                # in a row, all counted as misses) his magazine never went down: no round, not a shot
                s.dry_presses += 1
                continue
            if dropped:
                s.hits += 1
            else:
                s.misses += 1
            book().add(s.game, shot["weapon"], shot["band"], shot["pace"], shot["part"], dropped)
        s.pending = keep


def gap(game, weapon, d, base, rng, settings=None):
    """The next press's gap: base (the paced gap, long_pace past 10 u) x the pace that lands the most rounds a second in
    this band (hit rate / pace, PRIOR_RATE for one never tried, a little lower for the faster ones until tried), now and
    then another pace (explore) so each keeps being measured."""
    st = settings or tune(game)
    base = base * (st["long_pace"] if d > 10.0 else 1.0)
    if not st["shot_learn"]:
        return base
    if rng.random() < st["explore"]:
        return base * rng.choice(PACES)
    b = band(d)
    bk = book()
    best, best_v = 1.0, -1.0
    for p in PACES:
        r, n = bk.rate(game, weapon, b, pace=p, prior=PRIOR_RATE * min(1.0, p) ** 2)
        v = r / p
        if v > best_v + 1e-9:
            best, best_v = p, v
    return base * best


def part(game, weapon, d, shield_up, want_head, chest_open, head_open, rng, settings=None):
    """Head (True) or chest: the head once his shield is down (or a line to the head only); while it holds, the part
    that lands more in this band once both have PART_MIN shots (the chest only PART_EDGE over the head), now and then
    the other (explore)."""
    st = settings or tune(game)
    if not st["shot_learn"] or not shield_up or not (chest_open and head_open):
        return want_head
    if rng.random() < st["explore"] * 0.5:
        return not want_head
    b = band(d)
    rh, nh = book().rate(game, weapon, b, part="head")
    rc, nc = book().rate(game, weapon, b, part="chest")
    if nh >= PART_MIN and nc >= PART_MIN:
        return not rc > rh + PART_EDGE
    return want_head


def accuracy(game=None):
    """{game: {weapon: {band: (shots, hits)}}} of the book (tools/noble_report.py)."""
    out = {}
    for g, guns in book().data.items():
        if game and g != game:
            continue
        for w, cells in guns.items():
            for k, (n, h) in cells.items():
                b = int(k.split("|")[0])
                t = out.setdefault(g, {}).setdefault(w, {}).setdefault(b, [0, 0])
                t[0] += n
                t[1] += h
    return out


# --- 3. where it wins -----------------------------------------------------------------------------------------------
SPOT_CELL = 2.0                 # u: the cells wins and losses are counted in
SPOT_MIN_N = 4                  # kills and deaths in a cell before it counts
SPOT_RATE = 0.6                 # its share of wins (with one win and one loss more) to be a winning cell
SPOT_R = 7.0                    # u: the farthest winning cell it walks to
SPOT_WALK_COST = 0.02           # of the rate a u farther
_SPOTS = {}


def _cell(x, y, z):
    return (int(math.floor(x / SPOT_CELL)), int(math.floor(y / SPOT_CELL)), int(math.floor(z / SPOT_CELL)))


def spot_table(lb):
    """{cell: [wins, losses, x, y, z]} (the mean place men stood there) from a map memory's kills; cached by its size."""
    kills = getattr(lb, "kills", None) or []
    key = id(lb)
    c = _SPOTS.get(key)
    if c is not None and c[0] == len(kills):
        return c[1]
    cells = {}
    for row in kills:
        if len(row) < 6:
            continue
        vx, vy, vz, kx, ky, kz = row[:6]
        for (x, y, z), won in (((kx, ky, kz), True), ((vx, vy, vz), False)):
            e = cells.setdefault(_cell(x, y, z), [0, 0, 0.0, 0.0, 0.0])
            e[0 if won else 1] += 1
            e[2], e[3], e[4] = e[2] + x, e[3] + y, e[4] + z
    _SPOTS[key] = (len(kills), cells)
    return cells


def cell_rate(e):
    return (e[0] + 1.0) / (e[0] + e[1] + 2.0)


def spot_for(lb, me_pos, threat, los, banned=(), reach=SPOT_R):
    """(spot, rate) the best winning cell within reach u of me_pos with a line onto threat (los(a, b), the level's), or
    None. Ranked by its rate less SPOT_WALK_COST a u off; cells in banned (their keys) are left out."""
    best, best_v = None, -1.0
    for k, e in spot_table(lb).items():
        n = e[0] + e[1]
        if n < SPOT_MIN_N or k in banned:
            continue
        r = cell_rate(e)
        if r < SPOT_RATE:
            continue
        p = Vec(e[2] / n, e[3] / n, e[4] / n)
        d = dist(p, me_pos)
        if d > reach:
            continue
        v = r - SPOT_WALK_COST * d
        if v <= best_v:
            continue
        try:
            if not los(p, threat):
                continue
        except Exception:
            continue
        best, best_v = (p, r, k), v
    return best
