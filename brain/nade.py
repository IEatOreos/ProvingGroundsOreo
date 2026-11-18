"""(custom, Nov 18) Grenade throws solved like Halo Infinite's bots (the owner: "try to copy what they did but in a way
that works with our code and doesn't break it"). What Infinite does, read from its own executable (HaloInfinite.exe,
build HI_1_13_0, decompiled with Ghidra for this comparison only; none of its code is here):

1. a landing point, not the man: a bouncing grenade aims short of him so it lands and skips in. Past
   longRangeBounceGrenadeThrow (8) it aims distToThrowBounceGrenadeInFront (3) in front of him, on the thrower's side;
   closer, PercentageOfDistToAimBounceGrenade (0.8) of the way back toward the thrower. The point is lowered 0.2.
2. a ballistic solve from the grenade's own launch speed and gravity (its projectile tag): the launch direction that
   lands there, the low arc or the high one, none when it cannot reach.
3. the throw only within 30 degrees of where the bot faces (cos 0.866).
4. the arc walked in 0.2 s steps through the level (a grenade-sized sweep): a throw into a wall, a ceiling or a ledge is
   not made.

Ours, the same steps on our own data: LANDING_* (Reach units, tuned; Infinite's own in INFINITE), solve(), the facing
cone, arc_clear() through the level's own lines (Terrain.point_los). The one thing our data lacks is each game's grenade
launch speed, gravity and how the throw leaves relative to the view: no editing kit is installed and the map files'
projectile tags are not read. So they are learned from the bots' own throws (FlightWatch: the grenade object after a
bot's press, its first fraction of a second fitted to a parabola) into user/grenade_flights.json. Until a game has
MIN_FLIGHTS of them, model() is None and bots throw as before (along their aim).
"""
import json
import math
import os
import statistics

from .core import Vec, dist

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLIGHTS = os.path.join(ROOT, "user", "grenade_flights.json")

# Infinite's own (HaloInfinite.exe defaults; its units are not known to be ours): for the record and the tests
INFINITE = dict(long_r=8.0, short=3.0, close_frac=0.8, drop=0.2, cone_cos=0.866025, step=0.2)
# ours, in each game's world units. Infinite's rule with Reach-sized numbers: past LANDING_LONG_R aim LANDING_SHORT in
# front of him; closer, LANDING_CLOSE_FRAC of the way back toward us (Infinite's 0.8 would land a Reach frag at our own
# feet: the fight's throws start at 4 u, a frag's blast is about 3). The point LANDING_DROP under his feet (Infinite
# lowers its point 0.2; ours is the man's feet already)
LANDING_LONG_R, LANDING_SHORT, LANDING_CLOSE_FRAC, LANDING_DROP = 8.0, 1.0, 0.15, 0.0
CONE_COS = INFINITE["cone_cos"]       # the throw within 30 degrees of the view, as Infinite's
STEP_S = INFINITE["step"]            # s: the arc walked in these steps (Infinite's 0.2)
END_MARGIN = 0.6                     # u: the arc's walk stops this short of the landing (the ground there is no wall)
MIN_FLIGHTS = 3                      # learned throws before a game's model is used
MAX_FLIGHTS = 60                     # kept per game (the newest)
LEAD = 0.6                           # of a moving man's way over the flight time aimed ahead (a person leads less than
                                     # all the way: he may stop or turn)


def landing_point(src, target, long_r=LANDING_LONG_R, short=LANDING_SHORT, close_frac=LANDING_CLOSE_FRAC,
                  drop=LANDING_DROP):
    """Where a bouncing grenade should land to skip into a man at target thrown from src (Infinite's FUN_1426fb7c0):
    past long_r, short u in front of him on our side; closer, close_frac of the way from him back to us."""
    t = Vec(target.x, target.y, target.z - drop)
    d = dist(src, t)
    if d < 1e-6:
        return t
    k = short / d if d > long_r else close_frac
    return t + (src - t) * k


def solve(origin, at, speed, gravity, high=False):
    """The launch (yaw, pitch, time of flight) that lands a grenade thrown at speed (u/s) under gravity (u/s^2, down)
    from origin on at: the low arc, or the high one; None when at is out of its reach (Infinite's FUN_14316427c, the
    closed form)."""
    dx, dy, dz = at.x - origin.x, at.y - origin.y, at.z - origin.z
    flat = math.hypot(dx, dy)
    yaw = math.atan2(dy, dx)
    if speed <= 0.0:
        return None
    if gravity <= 1e-6:                               # (no gravity: straight at it, FUN_14316471c)
        return yaw, math.atan2(dz, max(flat, 1e-6)), math.sqrt(flat * flat + dz * dz) / speed
    if flat < 1e-3:
        return None                                   # (straight up or down: not a throw)
    v2 = speed * speed
    disc = v2 * v2 - gravity * (gravity * flat * flat + 2.0 * dz * v2)
    if disc < 0.0:
        return None                                   # out of reach at this speed
    root = math.sqrt(disc)
    pitch = math.atan((v2 + root) / (gravity * flat)) if high else math.atan((v2 - root) / (gravity * flat))
    t = flat / (speed * math.cos(pitch))
    return yaw, pitch, t


def arc_points(origin, yaw, pitch, speed, gravity, t_end, step=STEP_S):
    """The arc's points every step s from launch to t_end (both ends)."""
    vx, vy = speed * math.cos(pitch) * math.cos(yaw), speed * math.cos(pitch) * math.sin(yaw)
    vz = speed * math.sin(pitch)
    n = max(1, int(math.ceil(t_end / step)))
    out = []
    for i in range(n + 1):
        t = min(t_end, i * step)
        out.append(Vec(origin.x + vx * t, origin.y + vy * t, origin.z + vz * t - 0.5 * gravity * t * t))
    return out


def arc_clear(line, origin, yaw, pitch, speed, gravity, t_land):
    """Whether the arc to its landing is open: each STEP_S segment a clear line (line(a, b): the level's own,
    Terrain.point_los), up to END_MARGIN u short of the landing (Infinite's FUN_14263e95c walks it in 0.2 s steps)."""
    horiz = speed * math.cos(pitch)
    t_end = max(0.0, t_land - END_MARGIN / max(horiz, 1e-3))
    pts = arc_points(origin, yaw, pitch, speed, gravity, t_end)
    return all(line(a, b) for a, b in zip(pts, pts[1:]))


# --- learned physics ---------------------------------------------------------------------------------------------
_CACHE = {}


def load(path=FLIGHTS):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def model(game, path=FLIGHTS, flights=None):
    """A game's grenade physics, the medians of its learned throws: dict(speed, gravity, pitch_off, delay, n), or None
    with fewer than MIN_FLIGHTS. pitch_off: the launch's pitch over the view's (a throw leaves a little above the
    crosshair in some games); delay: s from the press to the grenade out of the hand."""
    if flights is None:
        key = (game, path)
        if key not in _CACHE:
            _CACHE[key] = load(path).get(game, [])
        flights = _CACHE[key]
    good = [f for f in flights if f.get("speed", 0) > 0 and f.get("gravity", 0) > 0]
    if len(good) < MIN_FLIGHTS:
        return None
    med = lambda k: statistics.median(f.get(k, 0.0) for f in good)
    return dict(speed=med("speed"), gravity=med("gravity"), pitch_off=med("pitch_off"), yaw_off=med("yaw_off"),
                delay=med("delay"), n=len(good))


def fit(samples):
    """A grenade's flight from (t, Vec) samples (its first moments, before a bounce): its velocity at the first sample
    and its gravity, by least squares (x, y straight; z a parabola). None with under 4 samples or a fit off by more
    than 0.08 u (a bounce or a wrong object): the last samples are dropped until it fits."""
    pts = list(samples)
    while len(pts) >= 4:
        t0 = pts[0][0]
        ts = [t - t0 for t, _ in pts]
        n = len(ts)
        st, stt = sum(ts), sum(t * t for t in ts)

        def line(vals):
            sv, stv = sum(vals), sum(t * v for t, v in zip(ts, vals))
            den = n * stt - st * st
            if abs(den) < 1e-12:
                return None
            b = (n * stv - st * sv) / den
            return (sv - b * st) / n, b

        lx, ly = line([p.x for _, p in pts]), line([p.y for _, p in pts])
        # z = c + d t + e t^2 (normal equations, 3x3)
        s3, s4 = sum(t ** 3 for t in ts), sum(t ** 4 for t in ts)
        zs = [p.z for _, p in pts]
        sz, stz, sttz = sum(zs), sum(t * z for t, z in zip(ts, zs)), sum(t * t * z for t, z in zip(ts, zs))
        A = [[n, st, stt], [st, stt, s3], [stt, s3, s4]]
        B = [sz, stz, sttz]
        sol = _solve3(A, B)
        if lx is None or ly is None or sol is None:
            return None
        c, dz, e = sol
        worst = max(math.dist((p.x, p.y, p.z), (lx[0] + lx[1] * t, ly[0] + ly[1] * t, c + dz * t + e * t * t))
                    for t, (_, p) in zip(ts, pts))
        if worst <= 0.08:
            return dict(t0=t0, pos=Vec(lx[0], ly[0], c), vel=Vec(lx[1], ly[1], dz), gravity=-2.0 * e)
        pts = pts[:-1]
    return None


def _solve3(A, B):
    """A 3x3 linear solve (Cramer); None when singular."""
    def det(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    D = det(A)
    if abs(D) < 1e-12:
        return None
    out = []
    for i in range(3):
        M = [row[:] for row in A]
        for r in range(3):
            M[r][i] = B[r]
        out.append(det(M) / D)
    return out


class FlightWatch:
    """Learns a game's grenade physics from the bots' own throws (tools/live_bots.py): pressed() at a bot's grenade
    press, observe() each tick with the projectile objects; a new projectile first seen within NEAR u of the thrower
    within FIRST_S s is followed until WATCH_S, fitted (fit), and kept (save) when it is a grenade: falling (gravity
    over 1), slower than 60 u/s."""
    NEAR, FIRST_S, WATCH_S, FOLLOW_S = 2.5, 0.8, 2.0, 0.6

    def __init__(s, game, path=FLIGHTS):
        s.game, s.path = game, path
        s.presses = []           # dicts: t, id, eye, yaw, pitch, known (handles seen before), track {handle: [(t, pos)]}
        s.kept = 0

    def active(s, now):
        s.presses = [p for p in s.presses if now - p["t"] < s.WATCH_S]
        return bool(s.presses)

    def pressed(s, now, bot_id, eye, yaw, pitch, known=()):
        if any(p["id"] == bot_id and now - p["t"] < 1.0 for p in s.presses):
            return                                       # (a held press: the first tick only)
        s.presses.append(dict(t=now, id=bot_id, eye=eye, yaw=yaw, pitch=pitch, known=set(known), track=None, mine=None))

    def observe(s, now, projectiles):
        """projectiles: [(handle, Vec)] in the world now."""
        done = []
        for p in s.presses:
            if p["mine"] is None:
                if now - p["t"] > s.FIRST_S:
                    done.append(p)
                    continue
                new = [(h, q) for h, q in projectiles if h not in p["known"] and dist(q, p["eye"]) < s.NEAR]
                if new:
                    h, q = min(new, key=lambda x: dist(x[1], p["eye"]))
                    p["mine"], p["track"] = h, [(now, q)]
                    p["first"] = now
                else:
                    p["known"] |= {h for h, _ in projectiles}
                continue
            q = next((q for h, q in projectiles if h == p["mine"]), None)
            if q is not None and now - p["first"] <= s.FOLLOW_S:
                p["track"].append((now, q))
            else:
                done.append(p)
        for p in done:
            s.presses.remove(p)
            f = s.flight(p)
            if f is not None:
                s.save(f)

    def flight(s, p):
        """The kept record of one followed press, or None (not a grenade, or too few points)."""
        if not p.get("track"):
            return None
        r = fit(p["track"])
        if r is None or not (1.0 < r["gravity"] < 60.0):
            return None
        v = r["vel"]
        # its velocity at launch: back from the first sample by the time since the press's delay (gravity only)
        speed = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
        if not (1.0 < speed < 60.0):
            return None
        launch_pitch = math.atan2(v.z, max(math.hypot(v.x, v.y), 1e-6))
        yaw_off = (math.atan2(v.y, v.x) - p["yaw"] + math.pi) % (2 * math.pi) - math.pi
        return dict(t=round(p["t"], 2), speed=round(speed, 3), gravity=round(r["gravity"], 3),
                    pitch_off=round(launch_pitch - p["pitch"], 4), yaw_off=round(yaw_off, 4),
                    delay=round(p["first"] - p["t"], 3), n=len(p["track"]))

    def save(s, f):
        d = load(s.path)
        rows = (d.get(s.game) or []) + [f]
        d[s.game] = rows[-MAX_FLIGHTS:]
        try:
            os.makedirs(os.path.dirname(s.path), exist_ok=True)
            with open(s.path, "w", encoding="utf-8") as fh:
                json.dump(d, fh, indent=1)
            s.kept += 1
        except OSError:
            pass
