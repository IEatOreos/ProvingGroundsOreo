"""Offline LiDAR simulator: LiDAR bots on every map's level data at high speed, watched in the
LiDAR 3D view on its own address (http://127.0.0.1:8798/, "LiDAR Simulator.bat"; the LiDAR Viewer and a LiDAR match's
live view keep 8797, so a simulator left open never stops a match's live view from starting).

The walking bots are the real LiDAR Roombas (tools/lidar.py: nearest unpainted floor by the nav,
called jumps, bump walls, the nav learning as the map fills); jumpphys moves them: walking by the
nav's step rule, jumps and falls by each game's physics, with a little take-off error (a hand is
never exact). A jump counts only when a bot called it and came down on the call; it is then a
link every bot uses: here at once, in matches from the next one (merged into
maps/<map>/lidar.json as found_by "sim", sim_ok). Aircraft fly the air over the walked floor, up
to the map's ceiling, and paint the airspace.

What it cannot know: anything the level data gets wrong (floors it lacks, steps the game lets you
walk up), and its physics has ASSUMED numbers (jumpphys). In matches LiDAR bots try every sim jump
and stop using ones they keep failing.

Steered from its window (the LiDAR view's Simulator panel, Control below): pick a map (or a Forge layout the bots
have played on) or every map, the speed (1x to 16x real time, or as fast as it runs), pause, stop, and spots on the
map for the bots to cover first (click the map). Started with no map names it waits for a pick.

Writes maps/<map>/lidar_sim.json (paint, airspace, deaths), merges called jumps into
maps/<map>/lidar.json, and a line per map to logs/lidar_sim.md.

usage: python -I lidar_sim.py [maps... | --all] [--game ce] [--minutes 6] [--walkers 16] [--aircraft 8]
                              [--speed 0] [--max-real 240] [--open] [--port 8798] [--hold 0]
  maps      names to run in turn (none: wait for a pick in the view); --all: every map with level data
  --speed   simulated seconds per real second (0: as fast as it runs)
  --max-real  real seconds at most per map (a huge campaign map would take hours)
  --hold    keep the view up this many seconds after the last map
"""
import argparse
import json
import math
import os
import random
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import jumpphys as J  # noqa: E402
import lidar  # noqa: E402
import lidar_rides  # noqa: E402
from lidar_director import TARGET  # noqa: E402
from lidar import BTN_CROUCH, BTN_JUMP, KIND_AIRSPACE, KIND_BOT, Hub, Recorder, Roomba, load, map_title, on_events, r2  # noqa: E402

HZ = 20
RIDE_P = lidar.RIDE_P            # share of Roomba goals that ride an untried lift or cannon (the simulator pushes them)
PORT = 8798                      # (not lidar.PORT, the LiDAR Viewer's and a LiDAR match's)
AIR_SPEED = 6.0                  # aircraft, units/s (ASSUMED: about a Banshee)
AIR_SENSE = 2                    # voxels around an aircraft it paints (a 5x5x5 block)
AIR_NEAR = 3.0                   # airspace: columns within this of walked floor
AIR_GAP = 2.5                    # air above a floor that has something over it (undersides are not in the data)
GAMES = ["ce", "h2a", "h2", "h3", "odst", "reach", "h4"]
MAX_FIELDS = 20                  # nav fields kept per map (each one is the size of the map)
DONE_AFTER = 360.0               # sim s: a map at the director's coverage target ends from here (time to find jumps)


class Body:
    """A walking bot's body: position, velocity, on the ground or not."""

    def __init__(s, p):
        s.p, s.v, s.ground, s.alive, s.dead_t = list(p), [0.0, 0.0, 0.0], True, True, 0.0

    def step(s, T, ph, act, dt, rng):
        """Move by the bot's action. Returns None, "fall" (landed too hard) or "void"."""
        fwd, strafe, yaw, _, buttons = act
        sh = getattr(T, "phantoms", None)            # in a gravity lift or a man cannon's push (tools/lidar_rides.py):
        if sh and not getattr(s, "ride", None) and lidar_rides.push(sh, s.p, s.v, dt):
            s.ground, s.air_t = False, 0.0           # pushed, in the air (air control and gravity below; a lift ride is not lost air)
        if getattr(s, "ride", None):                 # thrown by a man cannon: along the arc a real match recorded
            path, t, dur = s.ride
            t += dt
            k = min(1.0, t / max(dur, 0.1)) * (len(path) - 1)
            a, b = path[int(k)], path[min(int(k) + 1, len(path) - 1)]
            s.p = [a[n] + (b[n] - a[n]) * (k - int(k)) for n in range(3)]
            s.ride = (path, t, dur) if t < dur else None
            s.ground = s.ride is None
            return None
        if s.ground:
            for a, path, dur in getattr(T, "rides", ()):    # onto a ridden man cannon or lift
                if math.hypot(s.p[0] - a[0], s.p[1] - a[1]) < 0.5 and abs(s.p[2] - a[2]) < 1.0:
                    s.ride, s.ground = ([list(q) for q in path], 0.0, dur), False
                    return None
            mx, my = math.cos(yaw) * fwd - math.sin(yaw) * strafe, math.sin(yaw) * fwd + math.cos(yaw) * strafe
            n = math.hypot(mx, my)
            sp = ph.run * min(1.0, n)
            ux, uy = (mx / n, my / n) if n > 1e-6 else (0.0, 0.0)
            if buttons & BTN_JUMP:
                a = rng.gauss(0.0, 0.035)            # take-off error: about 2 degrees, a few % of speed
                sp *= rng.uniform(0.96, 1.02)
                ux, uy = ux * math.cos(a) - uy * math.sin(a), ux * math.sin(a) + uy * math.cos(a)
                s.v, s.ground = [ux * sp, uy * sp, ph.v0], False
                return None
            if sp <= 0:
                return None
            for a, b in getattr(T, "teleporters", ()):   # in a teleporter's trigger: out at its exit
                if math.hypot(s.p[0] + ux * sp * dt - a.x, s.p[1] + uy * sp * dt - a.y) < 0.75 and -0.5 <= s.p[2] - a.z <= 1.5:
                    s.p = [b.x, b.y, b.z]                    # (the nav's trigger: Terrain.add_links; Battle
                    return None                              # Creek's pads sit in a ring with no floor cells)
            out, q = J.walk_step(T, s.p, s.p[0] + ux * sp * dt, s.p[1] + uy * sp * dt)
            if out == "ok":
                s.p = q
            elif out == "off":
                s.p, s.v, s.ground = q, [ux * sp, uy * sp, 0.0], False
            return None
        mx, my = math.cos(yaw) * fwd - math.sin(yaw) * strafe, math.sin(yaw) * fwd + math.cos(yaw) * strafe
        if math.hypot(mx, my) > 0.1 and (s.v[0] or s.v[1] or s.v[2]):   # air control: toward where it steers
            n = math.hypot(mx, my)
            dvx, dvy = mx / n * ph.run - s.v[0], my / n * ph.run - s.v[1]
            dv = math.hypot(dvx, dvy)
            if dv > 1e-9:
                k = min(1.0, J.AIR_ACCEL * dt / dv)
                s.v[0] += dvx * k
                s.v[1] += dvy * k
        if buttons & BTN_CROUCH and not getattr(s, "tucked", False) and s.v[2] <= 0.0:
            s.p[2] += lidar.CROUCH_TUCK.get(ph.game, 0.0)   # crouched in the air: feet up at the apex (a crouch-jump)
            s.tucked = True
        out, impact = J.air_step(T, ph, s.p, s.v, dt)
        s.air_t = getattr(s, "air_t", 0.0) + dt
        if out == "land":
            s.ground, s.air_t, s.tucked = True, 0.0, False
            return "fall" if impact >= ph.lethal_v else None
        return "void" if out == "void" or s.air_t > 8.0 else None   # 8 s without ground: lost


class Airspace:
    """The free air over the walked floor up to the map's ceiling, in voxels, and what the
    aircraft have flown. Free: above every surface in its column, or between a floor and the next
    floor above it (at most AIR_GAP up where something is overhead: undersides are not in the level
    data), and not on a steep face. Only air connected to the air just over walked floor counts."""

    def __init__(s, T, ceiling):
        s.T = T
        width, depth = T.nw * 0.25, T.nh * 0.25
        s.z0 = math.floor(T.zmin) - 1.0
        height = max(2.0, ceiling - s.z0)
        s.v = max(1.0, (width * depth * height / 2.5e6) ** (1 / 3))   # voxel size: 2.5 million cells at most
        s.nx, s.ny, s.nz = int(math.ceil(width / s.v)), int(math.ceil(depth / s.v)), int(math.ceil(height / s.v))
        ii = np.clip(((np.arange(s.nx) + 0.5) * s.v / 0.25).astype(int), 0, T.nw - 1)
        jj = np.clip(((np.arange(s.ny) + 0.5) * s.v / 0.25).astype(int), 0, T.nh - 1)
        F = T.lz[:, jj][:, :, ii]
        top = T.top[jj * T.nstep][:, ii * T.nstep]
        W = T.walls[jj * T.nstep][:, ii * T.nstep]
        Fi = np.where(np.isfinite(F), F, np.inf)
        above = [np.where(Fi > Fi[l][None] + 0.3, Fi, np.inf).min(axis=0) for l in range(T.L)]
        s.free = np.zeros((s.nz, s.ny, s.nx), bool)
        with np.errstate(invalid="ignore"):
            for k in range(s.nz):
                z = s.z0 + (k + 0.5) * s.v
                f = (z > top + 0.3) & (top < 999)
                for l in range(T.L):
                    f |= (F[l] + 0.2 < z) & (z < np.minimum(above[l], F[l] + AIR_GAP) - 0.3)
                s.free[k] = f & ~T._wall_bit(W, np.full((s.ny, s.nx), z))
        s.flown = np.zeros_like(s.free)
        s.want = np.zeros_like(s.free)
        s.graph, s.version = None, 0

    def vox(s, p):
        return (min(max(int((p[2] - s.z0) / s.v), 0), s.nz - 1), min(max(int((p[1] - s.T.y0) / s.v), 0), s.ny - 1),
                min(max(int((p[0] - s.T.x0) / s.v), 0), s.nx - 1))

    def centre(s, k, j, i):
        return (s.T.x0 + (i + 0.5) * s.v, s.T.y0 + (j + 0.5) * s.v, s.z0 + (k + 0.5) * s.v)

    def update(s, rec):
        """The air to fly: free air in columns near walked floor, connected to the air just over it."""
        from scipy import ndimage
        foot = np.zeros((s.ny, s.nx), bool)
        low = np.full((s.ny, s.nx), s.nz, int)
        for kx, ky, kz in rec.floor_keys:
            k, j, i = s.vox((kx / 2, ky / 2, kz))
            foot[j, i] = True
            low[j, i] = min(low[j, i], k)
        if not foot.any():
            return
        r = max(1, int(round(AIR_NEAR / s.v)))
        disk = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
        env = s.free & ndimage.binary_dilation(foot, disk)[None]
        lab, n = ndimage.label(env)
        ks = np.arange(s.nz)[:, None, None]
        seed = env & foot[None] & (ks >= low[None]) & (ks <= low[None] + max(1, int(1.5 / s.v)))
        keep = np.unique(lab[seed])
        s.want = np.isin(lab, keep[keep > 0])
        s.version += 1

    def route(s, p):
        """Voxel centres from p through free air to the nearest air not flown yet ([] if none)."""
        from scipy.sparse.csgraph import breadth_first_order
        if s.graph is None:
            s.graph = s._graph()
        todo = s.want & ~s.flown
        if not todo.any():
            return []
        k, j, i = s.vox(p)
        start = (k * s.ny + j) * s.nx + i
        if not s.free[k, j, i]:
            near = np.argwhere(todo)
            k, j, i = near[np.argmin(((near - (k, j, i)) ** 2).sum(1))]
            return [s.centre(k, j, i)]           # inside geometry (a spawn): out to the nearest air
        for dk, dj, di in ((0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0)):
            q = (k + dk, j + dj, i + di)         # the next unflown voxel right beside: no search
            if 0 <= q[0] < s.nz and 0 <= q[1] < s.ny and 0 <= q[2] < s.nx and todo[q]:
                return [s.centre(*q)]
        order, pred = breadth_first_order(s.graph, start, directed=False, return_predecessors=True)
        hit = order[todo.ravel()[order]]
        if not len(hit):
            return []
        n, path = int(hit[0]), []
        while n != start and n >= 0:
            path.append(n)
            n = pred[n]
        return [s.centre(*np.unravel_index(q, s.free.shape)) for q in reversed(path)]

    def _graph(s):
        from scipy.sparse import coo_matrix
        idx = np.arange(s.free.size).reshape(s.free.shape)
        rows, cols = [], []
        for ax in range(3):
            a = [slice(None)] * 3
            b = [slice(None)] * 3
            a[ax], b[ax] = slice(0, -1), slice(1, None)
            both = s.free[tuple(a)] & s.free[tuple(b)]
            rows.append(idx[tuple(a)][both])
            cols.append(idx[tuple(b)][both])
        r, c = np.concatenate(rows), np.concatenate(cols)
        return coo_matrix((np.ones(len(r), np.int8), (r, c)), shape=(s.free.size, s.free.size)).tocsr()

    def paint(s, p, rec):
        """An aircraft at p: the air around it is flown (painted in the view). Returns how many new."""
        k, j, i = s.vox(p)
        a = AIR_SENSE
        sl = (slice(max(0, k - a), k + a + 1), slice(max(0, j - a), j + a + 1), slice(max(0, i - a), i + a + 1))
        new = s.want[sl] & ~s.flown[sl]
        if not new.any():
            return 0
        s.flown[sl] |= new
        for dk, dj, di in np.argwhere(new):
            rec.mark(s.centre(sl[0].start + dk, sl[1].start + dj, sl[2].start + di), KIND_AIRSPACE)
        return int(new.sum())


class Craft:
    def __init__(s, k, p):
        s.k, s.p, s.path, s.idle = k, list(p), [], -1   # idle: the airspace version it ran out at

    def step(s, air, dt, rec):
        if not s.path and s.idle != air.version:
            s.path = air.route(s.p)
            s.idle = -1 if s.path else air.version
        left = AIR_SPEED * dt
        while s.path and left > 0:
            q = s.path[0]
            d = math.dist(q, s.p)
            if d <= left:
                s.p, left = list(q), left - d
                s.path.pop(0)
                air.paint(s.p, rec)
            else:
                s.p = [s.p[n] + (q[n] - s.p[n]) * left / d for n in range(3)]
                left = 0


def ceiling_of(name, T):
    """The airspace's top: maps/<map>/air.json "ceiling" (map research) if there is one, else 2
    units over the map's highest surface (the level data has no sky or kill ceilings)."""
    d = load(os.path.join(ROOT, "maps", name, "air.json"))
    if "ceiling" in d:
        return float(d["ceiling"]), "air.json"
    top = T.top[T.top < 999]
    return float(top.max()) + 2.0, "highest surface + 2"


def merge_links(name, links):
    """Called jumps the simulator found, and its results on known links, into maps/<map>/lidar.json
    (only "links" is touched). Returns how many new links went in."""
    path = os.path.join(ROOT, "maps", name, "lidar.json")
    d = load(path) or dict(cell=lidar.CELL, zstep=lidar.ZSTEP)
    have, new = d.setdefault("links", []), 0
    for l in links:
        m = next((x for x in have if x.get("kind", "jump") == l.get("kind", "jump")
                  and math.dist(x["take_off"], l["take_off"]) < 0.01 and math.dist(x["land"], l["land"]) < 0.01), None)
        if m is None and l.get("found_by") == "sim" and not l.get("crouch"):   # (crouch-jumps: lidar.CROUCH_TUCK)
            have.append({k: v for k, v in l.items() if not k.startswith("_")})
            new += 1
        elif m is not None:
            for k in ("sim_ok", "sim_fail"):
                if l.get(k):
                    m[k] = l[k]
    if new or any(l.get("sim_ok") or l.get("sim_fail") for l in links):
        tmp = path + ".tmp"
        json.dump(d, open(tmp, "w"))
        os.replace(tmp, path)
    return new


def run_map(name, o, switch, k, n, log, ctl=None):
    from brain.core import Vec
    from brain.maps import _TERRAIN, get_map, terrain, usable_links
    m = get_map(name)
    T = J.prepare(terrain(m))
    T.teleporters = m["teleporters"]
    game = J.game_of(name)
    real = load(os.path.join(ROOT, "maps", name, "lidar.json"))
    rec = Recorder(name, count_run=True, T=T, path=os.path.join(ROOT, "maps", name, "lidar_sim.json"))
    rec.links = real.get("links", [])               # people's jumps and routes, earlier sim jumps
    rec.cover, rec.floor_keys = set(), set()        # every run maps afresh (earlier runs show dimmed)
    rec.ok_key, rec.fail_key, rec.found_as = "sim_ok", "sim_fail", "sim"
    jumps = sorted(real.get("jumps", []))
    rec.phys = J.Phys(game, jumps[len(jumps) // 2] if len(jumps) >= 20 else None)
    lidar.PROBE_P, lidar.HZ = 0.0, HZ               # a probe needs the game's own leniency: not here
    lidar.USE_P = 0.0                               # nor can it press switches
    T.phantoms = lidar_rides.all_shapes(lidar_rides.load(name))   # lifts and man cannons push (their tags' numbers)
    lidar.RIDE_P = RIDE_P if T.phantoms else 0.0    # (without them rides come from real matches)
    T.rides = [(l["take_off"], l["path"], l.get("air_s") or 1.5) for l in usable_links(rec.links) if l.get("ride")
               and l.get("found_by") != "map"]      # (recorded rides replay their path; map rides are flown)
    rides = lidar_rides.ride_links(name, T, rec.phys) if T.phantoms else []
    if rides:                                        # the nav routes through them at once
        rec.links += rides
        lidar.nav_learn(T, name, rec.links)
    hub = Hub(rec, "sim")
    switch.current = hub
    bounds = (T.x0, T.y0, T.x0 + T.nw * 0.25, T.y0 + T.nh * 0.25)
    # each spawn on the nearest reachable floor: a spawn whose own cell has no floor gave a NaN height
    # (Halo 3 Sandtrap, Reach Sword Base and Condemned failed the tour)
    spawns = [T._center(*T._reachable_node(*T._node(p), p.z)) for mode in m["spawns"].values() for team in mode.values() for p in team]
    spawns = [(c.x, c.y, c.z) for c in spawns if not math.isnan(c.z)]
    if not spawns:                                   # no spawn points: any reachable floor
        c = T._center(*map(int, np.argwhere(T.lwalk & T.reach)[0]))
        spawns = [(c.x, c.y, c.z)]
    rng = random.Random(sum(map(ord, name)))
    walkers = [(Roomba(i, rng), Body(spawns[i % len(spawns)])) for i in range(o.walkers)]
    from brain import oob                            # the map's kill zones: bots keep out as in a match, the director
    vols = oob.volumes(name)                         # leaves them out of the floor to cover (brain/oob.py)
    if vols:
        T.set_oob([], 0, vols)
    if not getattr(o, "no_director", False):         # the LiDAR director (tools/lidar_director.py)
        from lidar_director import LidarDirector
        rec.director = LidarDirector(T, rec, [Vec(*p) for p in spawns])
        rec.objectives = lidar.Objectives(name, T)   # every gametype objective place, visited afresh each run
        rec.objectives.seed(rec.director)
    ceiling, why = ceiling_of(name, T)
    air = Airspace(T, ceiling)
    crafts = [Craft(c, (sp[0], sp[1], sp[2] + 2.5)) for c, sp in enumerate(rng.sample(spawns * o.aircraft, o.aircraft))]
    sig = [id(l) for l in usable_links(rec.links)]
    t, dt, last_new, floor_n, t0 = 0.0, 1.0 / HZ, 0.0, 0, time.time()
    deaths = falls = 0
    if ctl is not None:
        ctl.started(name, T, getattr(rec, "director", None))
    speed, anchor, ran = None, (0.0, time.time()), 0.0       # pacing from the last speed change; real s run
    while t < o.minutes * 60 and (ran < o.max_real or (ctl is not None and ctl.speed > 0)):
        if ctl is not None:
            if ctl.stop_now:
                break
            while ctl.paused and not ctl.stop_now:
                hub.note = f"{map_title(name)}: paused at {t / 60:.1f} sim min"
                time.sleep(0.1)
                speed = None                          # (paced afresh from here)
            ctl.feed(rec)
        tick0 = time.time()
        want = ctl.speed if ctl is not None else o.speed
        if want != speed:
            speed, anchor = want, (t, time.time())
        hub.note = (f"map {k} of {n}: " if n > 1 else "") + \
            f"{map_title(name)} ({game}) · {t / 60:.1f} sim min · " + (f"{speed:g}x" if speed else "full speed")
        if ctl is not None:
            ctl.t = t
            ctl.rate(t)
        rec.players_pos = [tuple(b.p) for _, b in walkers if b.alive]
        if getattr(rec, "director", None) is not None:
            rec.director.plan(t, {rb.index: tuple(b.p) for rb, b in walkers if b.alive})
            for i in rec.director.new_spot_bots:     # (sent to a marked spot: drop the old goal, go now)
                if i < len(walkers) and walkers[i][0].trial is None:
                    walkers[i][0].target = None
            rec.director.new_spot_bots.clear()
            rec.objectives.update(rec.players_pos, t)
        for rb, b in walkers:
            if not b.alive:
                if t - b.dead_t >= 2.0:              # respawn
                    b.__init__(rng.choice(spawns))
                continue
            pos = tuple(b.p)
            on_events(rec, rb.track.update(t, pos, ground=b.ground), "bot", KIND_BOT, rb)
            act = rb.think(t, pos, rec, T, bounds)
            res = b.step(T, rec.phys, act, dt, rng)
            if res:
                info = rb.track.die()
                rb.died(rec)
                b.alive, b.dead_t = False, t
                deaths += 1
                if info:
                    d = rec.died(info, "bot", t)
                    if d["cause"] == "fall" or res == "void":
                        falls += 1
                        st, ps = Vec(*d["stood"]), Vec(*d["pos"])
                        v = Vec(ps.x - st.x, ps.y - st.y, 0)
                        if v.flat() > 0.05:          # the nav learns the edge (in memory: not the real map's file)
                            T.learn_stuck(st + v * (0.4 / v.flat()))
            tr = rb.trial
            hub.set_player(rb.index, name=f"bot {rb.index}", human=False, pos=r2(b.p) if b.alive else None,
                           alive=b.alive, air=not b.ground, trail=[r2(q) for q in rb.track.shown_trail()][-40:],
                           trying=tr is not None, call=tr["land"] if tr is not None and tr.get("called") else None)
        for c in crafts:
            c.step(air, dt, rec)
            hub.set_player(1000 + c.k, name=f"aircraft {c.k}", human=False, kind="air", pos=r2(c.p), alive=True, air=True, trail=[])
        step = int(round(t * HZ))
        if step % (HZ * 15) == 0:                    # the airspace follows the walked floor
            air.update(rec)
        if step % (HZ * 5) == 0:                     # called jumps made: into the nav at once
            now_sig = [id(l) for l in usable_links(rec.links)]
            if now_sig != sig:
                sig = now_sig
                lidar.nav_learn(T, name, rec.links)
            for cache in (T._fields, getattr(T, "_hfields", {}), getattr(T, "_jfields", {})):
                if len(cache) > MAX_FIELDS:
                    cache.clear()
            fn = sum(1 for key in rec.walk if key[3] in (lidar.KIND_BOT, lidar.KIND_SPREAD))
            if fn > floor_n + 5:
                floor_n, last_new = fn, t
            dr = getattr(rec, "director", None)      # (with a director: only once it has nothing left to send bots to,
            if t > 90 and t - last_new > 45 and all(c.idle == air.version for c in crafts) and \
                    (dr is None or not dr.open_work()):  # coverage at its target or every patch left, objectives done)
                break                                # nothing new for 45 s and the air is flown
            if dr is not None and t >= DONE_AFTER and dr.done() and all(c.idle == air.version for c in crafts):
                break                                # the director's target reached, objectives visited, air flown
        t += dt
        if speed:
            ahead = (t - anchor[0]) / speed - (time.time() - anchor[1])
            if ahead > 0:
                time.sleep(min(ahead, 0.5))
        ran += time.time() - tick0
    d = getattr(rec, "director", None)
    if d is not None:                                # the coverage at the end (not the last plan's, up to 6 s old)
        d.next_t = 0.0
        d.plan(t, {rb.index: tuple(b.p) for rb, b in walkers if b.alive})
    rec.save(bot_seconds=t * len(walkers))
    new = merge_links(name, rec.links)
    want, flown = int(air.want.sum()), int((air.want & air.flown).sum())
    reach_cells = int((T.lwalk & T.reach).sum())
    line = (f"| {name} | {game} | {t / 60:.1f} | {floor_n} | {reach_cells} | {rec.calls['made']} | {rec.calls['missed']} | "
            f"{new} | {deaths} | {falls} | {flown}/{want} ({air.v:.1f} u) | {ceiling:.1f} ({why}) | {time.time() - t0:.0f} s | " +
            (f"{100 * d.coverage:.1f}% | " + (f"{d.reached_at:.0f} s |" if d.reached_at is not None else "not reached |")
             if d is not None else " | |"))
    print(line, flush=True)
    log.write(line + "\n")
    log.flush()
    _TERRAIN.pop(name, None)                         # 122 maps: keep memory flat
    if ctl is not None:
        ctl.finished(name, floor_n, new, t, stopped=ctl.stop_now)
    return rec


class Switch:
    current = None
    control = None
    last_seen = 0.0          # the view's last poll (lidar.serve): the simulator stops a while after it closes


class Control:
    """What the view asks of the simulator (POST /sim, tools/lidar.py serve) and what it shows (state() in /live).
    The view's thread sets; the simulator's loop reads at every tick."""
    SPEEDS = (1, 2, 4, 8, 16, 0)        # simulated seconds per real second; 0: as fast as it runs

    def __init__(s, names):
        s.lock = threading.Lock()
        s.names, s.queue = list(names), []
        s.current, s.T, s.director, s.t = None, None, None, 0.0
        s.speed, s.paused, s.stop_now = 4.0, False, False
        s.pending, s.clear = [], False
        s.last = None                   # the last map finished: (name, floor cells, new jumps, sim minutes, stopped)

    def command(s, d):
        """One request from the view: (HTTP status, answer)."""
        act = d.get("action")
        with s.lock:
            if act == "pick":
                name = d.get("name")
                if name not in s.names:
                    return 404, dict(error="no level data for that map")
                s.queue = [name]
                s.stop_now, s.paused = s.current is not None, False   # (the map running now ends, this one starts)
            elif act == "all":
                s.queue = [m for m in s.names if "/variants/" not in m]
                s.stop_now, s.paused = s.current is not None, False
            elif act == "speed":
                v = float(d.get("speed", 4))
                if v not in s.SPEEDS:
                    return 400, dict(error="speed must be one of " + ", ".join(map(str, s.SPEEDS)))
                s.speed, s._rate, s.actual = v, None, 0.0     # (measured afresh at the new speed)
            elif act in ("pause", "resume"):
                s.paused = act == "pause" and s.current is not None
            elif act == "stop":
                s.queue, s.paused = [], False
                s.stop_now = s.current is not None
            elif act == "spot":
                if s.T is None or s.current is None:
                    return 409, dict(error="start a map first, then click where the bots should go")
                pos = s.snap(float(d["x"]), float(d["y"]), float(d["z"]))
                if pos is None:
                    return 404, dict(error="no floor there: click on the map's ground")
                s.pending.append(pos)
                return 200, dict(spot=[round(v, 2) for v in pos])
            elif act == "clear_spots":
                s.clear, s.pending = True, []
            else:
                return 400, dict(error="unknown action")
        return 200, dict(ok=True)

    def snap(s, x, y, z):
        """The walkable floor nearest a clicked point (its level nearest z, within 3 u), or None."""
        from brain.core import Vec
        T = s.T
        if not (T.x0 <= x < T.x0 + T.nw * 0.25 and T.y0 <= y < T.y0 + T.nh * 0.25):
            return None
        c = T._center(*T._reachable_node(*T._node(Vec(x, y, z)), z))
        if math.isnan(c.z) or math.hypot(c.x - x, c.y - y) > 3.0:
            return None
        return (c.x, c.y, c.z)

    def next_map(s):
        with s.lock:
            s.stop_now = False
            return s.queue.pop(0) if s.queue else None

    def started(s, name, T, director):
        with s.lock:
            s.current, s.T, s.director, s.t, s._rate, s.actual = name, T, director, 0.0, None, 0.0
            s.pending, s.clear = [], False

    def feed(s, rec):
        """Hands new spots (and a clear) to the running map's director: on the simulator's own thread."""
        d = getattr(rec, "director", None)
        with s.lock:
            pend, clr, s.pending, s.clear = s.pending, s.clear, [], False
        if d is not None:
            if clr:
                d.clear_spots()
            for pos in pend:
                d.add_spot(pos)

    def finished(s, name, cells, links, t, stopped):
        with s.lock:
            s.current, s.T, s.director, s.paused = None, None, None, False
            s.last = dict(name=name, title=map_title(name), cells=cells, links=links, minutes=round(t / 60, 1),
                          stopped=bool(stopped))

    def rate(s, t):
        """Keeps the speed actually reached: simulated seconds per real second over the last 2-3 s."""
        now = time.time()
        r = getattr(s, "_rate", None)
        if r is None or t < r[0] or now - r[1] > 3.0:
            if r is not None and t >= r[0] and now > r[1]:
                s.actual = (t - r[0]) / (now - r[1])
            s._rate = (t, now)

    def state(s):
        d = s.director
        return dict(current=s.current, title=map_title(s.current) if s.current else None, minutes=round(s.t / 60, 1),
                    speed=s.speed, actual=round(getattr(s, "actual", 0.0), 1) if s.current else 0.0,
                    speeds=list(s.SPEEDS), paused=s.paused, queue=len(s.queue), last=s.last,
                    spots=d.spot_view() if d is not None else [], painted=round(getattr(d, "painted_share", 0.0), 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("maps", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--game")
    ap.add_argument("--minutes", type=float, default=20.0, help="sim minutes at most (a map ends sooner once the "
                    "director has nothing left to send bots to and no new floor came for 45 s)")
    ap.add_argument("--walkers", type=int, default=16)
    ap.add_argument("--aircraft", type=int, default=8)
    ap.add_argument("--speed", type=float, default=0.0)
    ap.add_argument("--max-real", type=float, default=240.0, help="real seconds at most per map (huge maps)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--hold", type=float, default=0.0)
    ap.add_argument("--no-director", action="store_true", help="bots pick their own goals (no LiDAR director): A/B runs")
    o = ap.parse_args()
    every = sorted(lidar.map_list_names(), key=lambda d: (GAMES.index(J.game_of(d.partition("/")[0])), d))
    names = o.maps or ([m for m in every if "/variants/" not in m] if o.all else [])
    if o.game:
        names = [d for d in names if J.game_of(d) == o.game]
    switch = Switch()
    switch.control = ctl = Control(every)
    ctl.queue = list(names)
    idle = os.path.join(ROOT, "logs", "lidar_sim_idle.json")       # (waiting: an empty view, no old scan behind it)
    switch.current = Hub(Recorder((names or every)[0], count_run=False, path=idle if not names else None), "sim")
    switch.current.note = "Pick a map to simulate (Simulator panel)"
    srv = lidar.serve(switch, o.port)
    if o.open:
        import appwindow
        appwindow.open_window(f"http://127.0.0.1:{o.port}/")
    if srv is None:                                   # another simulator holds its address: two would
        print("Another LiDAR simulator is already running: its window shows it. Not starting a second "
              "one (both would save the same maps).", flush=True)
        return
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    waiting = not names                            # (no maps named: the view picks)
    with open(os.path.join(ROOT, "logs", "lidar_sim.md"), "a") as log:
        log.write(f"\n## Run {time.strftime('%Y-%m-%d %H:%M')}: {len(names) or 'picked'} maps, {o.walkers} bots, {o.aircraft} aircraft\n\n"
                  "| map | game | sim min | floor cells painted | reachable cells (level data) | calls made | missed | "
                  "new links | deaths | falls | air flown / to fly (voxel) | ceiling | real time | reachable floor covered "
                  f"(kill zones out) | {100 * TARGET:.0f}% at |\n|" + "---|" * 15 + "\n")
        k = 0
        switch.last_seen = time.time()
        while True:
            name = ctl.next_map()
            if name is None:
                if not waiting and not o.open:
                    break                             # (named maps, no window: done)
                if time.time() - switch.last_seen > 90:
                    break                             # (its window closed a while ago)
                time.sleep(0.3)
                continue
            k += 1
            try:
                run_map(name, o, switch, k, k + len(ctl.queue), log, ctl)
            except Exception as e:                    # one broken map must not stop the tour
                import traceback
                print(f"{name}: FAILED {type(e).__name__}: {e}\n{traceback.format_exc(limit=-9)}", flush=True)
                log.write(f"| {name} | FAILED {type(e).__name__}: {e} |\n")
    if srv and o.hold:
        time.sleep(o.hold)
    if srv:
        srv.shutdown()


if __name__ == "__main__":
    main()
