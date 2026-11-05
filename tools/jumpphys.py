"""Jump, walk and fall physics over a map's level data (brain.terrain.Terrain), per game: what LiDAR
bots use to call their jumps and what the offline LiDAR simulator (tools/lidar_sim.py) moves its
bots with.

Numbers (world units, seconds):
- gravity and jump speed MEASURED in real matches (tools/fit_physics.py over logs/trace_*.jsonl:
  the curvature of every half-second-plus arc in the air, the slope where a jump left the ground).
  The kits' biped "jump velocity" agrees for CE 2.1, H2 3.08, H3 3.08, ODST 2.6, Reach 2.3 (within
  2-4%); H2A and H4 jump harder in game (2.82 / 2.84) than their kits' 2.34 / 2.36 say. Jump heights
  agree with LiDAR: CE 0.65 (Battle Creek 0.64), H2A 1.04 (Lockdown 1.03). Base gravity is not in
  any tag (an engine constant; CE's is 0.003565 per tick^2, 3.21 at 30 ticks/s).
- run speed: the kits' globals "player information" run forward (CE, H2, H3, ODST, Reach, H4, H2A
  MP kits; bots in the traces strafe while fighting, so their speeds do not show the top run speed).
- lethal fall: CE, H2, H3, ODST from globals "harmful falling distance" (damage up to its upper end:
  CE 3-6, the others 6-10). Reach, H4, H2A have no harmful distance and a zero-damage hard landing;
  INFERRED: their 1000-damage "falling" effect applies past the biped's maximum hard landing
  velocity (Reach 8.5, H4 / H2A 10), as a height at the measured gravity. Confirm in game.
Fewer arcs back ODST (41) and H4 (44) than the rest (400-5000). A map's own measured apex (20+
LiDAR jumps) replaces the jump speed.
"""
import math

import numpy as np

# game: (run speed, jump speed, gravity, lethal fall height)
PHYS = {
    "ce":    (2.25, 2.025, 3.148, 6.0),
    "h2":    (2.25, 3.022, 4.101, 10.0),
    "h2a":   (2.30, 2.818, 3.818, 13.1),   # lethal fall INFERRED (10 u/s landing)
    "h3":    (2.25, 3.013, 4.099, 10.0),
    "odst":  (1.85, 2.534, 4.386, 10.0),   # gravity from 41 arcs only
    "reach": (2.20, 2.346, 4.094, 8.8),    # lethal fall INFERRED (8.5 u/s landing)
    "h4":    (2.20, 2.841, 4.483, 11.2),   # gravity from 44 arcs only; lethal fall INFERRED (10 u/s)
}
AIR_ACCEL = 1.05                 # airborne acceleration (every kit's globals; CE 0.035 per tick): air control
AIR_FACES = (0.45, 0.65)         # in the air a face at either height above the feet stops a body
HEAD = 0.7                       # (faces come in 0.25-unit height bins: lower would catch curbs)
STEP_DOWN = 0.25                 # walking: a floor this much lower is still the next step


def game_of(map_name):
    for prefix, game in (("h2a_", "h2a"), ("h2_", "h2"), ("h3_", "h3"), ("reach_", "reach"), ("odst_", "odst"), ("h4_", "h4")):
        if map_name.startswith(prefix):
            return game
    return "ce"


class Phys:
    def __init__(s, game, apex=None):
        s.game = game
        s.run, s.v0, s.g, s.lethal = PHYS[game]
        if apex:                                     # the map's measured jump height wins
            s.v0 = math.sqrt(2 * s.g * apex)
        s.apex = s.v0 ** 2 / (2 * s.g)
        s.lethal_v = math.sqrt(2 * s.g * s.lethal)   # landing faster than this kills


def reach(ph, dz):
    """How far a full-speed running jump carries before it comes down dz higher (negative: lower);
    nan where dz is above the jump's apex. Works on arrays."""
    dz = np.asarray(dz, dtype=float)
    with np.errstate(invalid="ignore"):
        t = (ph.v0 + np.sqrt(ph.v0 ** 2 - 2 * ph.g * dz)) / ph.g
    return ph.run * t


def _cell(T, x, y):
    i, j = int((x - T.x0) / 0.25), int((y - T.y0) / 0.25)
    if 0 <= j < T.nh and 0 <= i < T.nw:
        return j, i
    return None


def _face(T, j, i, z):
    """A steep face at height z in nav cell (j, i)?"""
    w = T.walls[j * T.nstep + T.nstep // 2, i * T.nstep + T.nstep // 2]
    return bool(T._wall_bit(w, np.float64(z)))


def _smooth(T, x, y, j, i, f):
    """The floor height at (x, y), not just its cell's: leaning toward the next cell's floor (when it
    is the same surface) by how far toward it we are. A ramp is smooth in the game; read cell by cell
    it is a staircase whose bumps the LiDAR tracker takes for jumps."""
    z = f
    for dj, di, off in ((0, 1, (x - T.x0) / 0.25 - i - 0.5), (1, 0, (y - T.y0) / 0.25 - j - 0.5)):
        s = 1 if off > 0 else -1
        jj, ii = j + dj * s, i + di * s
        if 0 <= jj < T.nh and 0 <= ii < T.nw:
            nb = T.lz[:, jj, ii]
            near = nb[np.isfinite(nb) & (np.abs(nb - f) < 0.3)]
            if near.size:
                z += abs(off) * (float(near[np.argmin(np.abs(near - f))]) - f)
    return z


def walk_step(T, p, x, y):
    """One walking step from p to (x, y): ("ok", new position on the next floor), ("off", (x, y,
    z)) walking off an edge into the air, or ("blocked", p) (a wall at chest and head height, a
    step too high for walking). The nav's own rules (BODY, MAX_RISE), so the sim walks where the
    nav says it can."""
    from brain.terrain import BODY, MAX_RISE
    c = _cell(T, x, y)
    if c is None:
        return "off", [x, y, p[2]]                   # off the level: the void
    j, i = c
    z = p[2]
    if _face(T, j, i, z + BODY[0]) and _face(T, j, i, z + BODY[1]):
        return "blocked", p
    f = T.lz[:, j, i]
    if not np.isfinite(f).any():                     # no floor: steep rock or a bump (its top surface), or the void
        if not np.isfinite(T.low[j * T.nstep, i * T.nstep]):
            return "off", [x, y, z]
        top = float(T.top[j * T.nstep, i * T.nstep])
        if top > z + MAX_RISE:
            return "blocked", p
        return ("ok", [x, y, top]) if top >= z - STEP_DOWN else ("off", [x, y, z])
    best = None
    for l in range(T.L):
        if np.isfinite(f[l]) and -STEP_DOWN <= f[l] - z <= MAX_RISE and (best is None or abs(f[l] - z) < abs(best[1] - z)):
            best = (l, float(f[l]))
    if best is not None:                             # into a cell a wall runs through: no (unless already in it)
        if not (T.lwalk[best[0], j, i] or _cell(T, p[0], p[1]) == (j, i)):
            return "blocked", p
        return "ok", [x, y, _smooth(T, x, y, j, i, best[1])]
    with np.errstate(invalid="ignore"):
        if np.any((f > z + MAX_RISE) & (f <= z + 1.2)) or not np.any(f < z):
            return "blocked", p                      # a step up, or floor only overhead
    return "off", [x, y, z]                          # a drop


def air_step(T, ph, p, v, dt):
    """One step of a body in the air (p, v: [x, y, z] lists, changed in place): gravity, faces at
    AIR_FACES stop it sideways, a floor slab overhead stops it rising, crossing a floor on the way
    down lands it. Returns ("air", 0), ("land", impact speed) or ("void", 0)."""
    x, y, z = p
    nx, ny = x + v[0] * dt, y + v[1] * dt
    nz = z + v[2] * dt - 0.5 * ph.g * dt * dt
    v[2] -= ph.g * dt
    c = _cell(T, nx, ny)
    if c is None:
        p[:] = [nx, ny, nz]
        return ("void", 0.0) if nz < T.zmin - 10 else ("air", 0.0)
    j, i = c

    def floor_crossed(j, i):
        f = T.lz[:, j, i]
        hit = None
        for l in range(T.L):
            if np.isfinite(f[l]) and nz <= f[l] <= z + 0.05 and (hit is None or f[l] > f[hit]):
                hit = l
        return hit

    def inside(j, i):                                # below the column's lowest floor, or in rock with no floor
        f = T.lz[:, j, i]
        fin = f[np.isfinite(f)]
        if fin.size:
            return nz < fin.min() - 0.05
        top = float(T.top[j * T.nstep, i * T.nstep])
        return top < 999 and nz < top - 0.05 and z < top - 0.05

    moved = (nx, ny) != (x, y)
    if moved and (_face(T, j, i, nz + AIR_FACES[0]) or _face(T, j, i, nz + AIR_FACES[1]) or inside(j, i)):
        v[0] = v[1] = 0.0                            # into a wall: stop sideways, drop down it in our column
        nx, ny = x, y
        j, i = _cell(T, x, y) or (j, i)
    f = T.lz[:, j, i]
    if v[2] > 0:                                     # rising: a slab overhead stops the rise
        with np.errstate(invalid="ignore"):
            if np.any((f > z + HEAD) & (f <= nz + HEAD + 0.1)):
                v[2] = 0.0
                nz = z
    else:                                            # falling: crossing a floor lands on it
        hit = floor_crossed(j, i)
        if hit is not None:
            impact = -v[2]
            p[:] = [nx, ny, float(f[hit])]
            v[:] = [0.0, 0.0, 0.0]
            return "land", impact
        top = float(T.top[j * T.nstep, i * T.nstep])
        if not np.isfinite(f).any() and top < 999 and nz <= top <= z + 0.05:
            impact = -v[2]                           # steep rock or a bump, no floor on it: down on it
            p[:] = [nx, ny, top]
            v[:] = [0.0, 0.0, 0.0]
            return "land", impact
    p[:] = [nx, ny, nz]
    if nz < T.zmin - 10:
        return "void", 0.0
    return "air", 0.0


def fly(T, ph, p, vx, vy, vz=None, dt=1 / 30, max_t=6.0):
    """A whole jump (vz None: a jump's take-off speed) from p: (outcome "land" | "void" | "air",
    where it ended, highest z, seconds, impact speed)."""
    prepare(T)          # callers need not have: LiDAR's walk_off_kills flew first and crashed
    p, v = list(p), [vx, vy, ph.v0 if vz is None else vz]
    top, t = p[2], 0.0
    while t < max_t:
        out, impact = air_step(T, ph, p, v, dt)
        t += dt
        top = max(top, p[2])
        if out != "air":
            return out, p, top, t, impact
    return "air", p, top, t, 0.0


def prepare(T):
    """Per map, once: the lowest floor (falls far below it are into the void)."""
    if not hasattr(T, "zmin"):
        f = T.lz[np.isfinite(T.lz)]
        T.zmin = float(f.min()) if f.size else 0.0
    return T
