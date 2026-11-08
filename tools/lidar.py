"""LiDAR mode: a match full of bots that do nothing but map the map, like Roombas, with a live 3D
view (tools/lidar_view.html, served at http://127.0.0.1:8797/).

Every player's path goes through one tracker: each position is ground or air by its vertical
acceleration over +-0.25 s (a walk up a ramp is a straight line in height over time, a jump or a
fall is a parabola). Ground marks the floor at once. Air waits: landing and staying alive for
CONFIRM_S (5 s) sets the trail in stone (marks plus a link from take-off to landing); dying in the
air or within those 5 s erases it (the player's rules).

People get special attention: a jump a person lands is a link in the map's LiDAR data (take-off,
run-up, landing, the arc), and the nav gives it to every bot that jumps at all (brain/maps.py ->
Terrain.add_human_links). LiDAR Roombas walk to a person's jump and try it themselves: the link
counts bot successes and failures. People's jumps are also caught in normal bot matches
(live_bots uses HumanWatch).

Roombas walk straight at the least-explored ground near them (not along the level data's paths, so they find floors
the data misses), keep off drops the level data or earlier falls show to be deadly, and jump now and then where that
is safe. Placed pieces (a Forge map variant's, read from the game: level_data) are in the level data face by face,
each a floor, ramp or wall by its angle; floor marked on a piece's ramp is also marked KIND_RAMP (orange in the
view), and the paint calls a face too steep to walk up a wall.

Output, merged over runs: maps/<map>/lidar.json (walked cells by kind, links, deaths, jump
heights), logs/lidar_<map>.md (written every minute too: the mapper is killed when a match
ends), and fall edges where the level data claimed floor taught to the nav (nav_learned.json).
Every vehicle anyone drives or flies goes into maps/<map>/rides.json (RideWatch, as in normal matches): the vehicles'
ground and roads and the aircraft heights the bots use from the next match, drawn in the view as it is driven.

usage: python -I lidar.py <map> [seconds=300] [--game h2a]   (bots already added: play.py --lidar)
       python -I lidar.py --view [map] [--open]      the 3D view of a map's stored data (newest map)
       python -I lidar.py --replay <trace.jsonl> <map> [--speed 4] [--human-id N] [--save]
       python -I lidar.py --selftest
"""
import argparse
import json
import math
import os
import random
import re
import struct
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

HZ = 30
CELL, ZSTEP = 0.25, 0.1          # recorded grid: x/y cell, height step (world units)
COVER = 1.0                      # exploration grid (what counts as "been there")
FALL = 3.0                       # a death after dropping more than this is a fall
STUCK_S = 2.5                    # pushing without moving this long: give up on the target
HEADWAY_S, HEADWAY_U = 1.5, 0.4   # less ground than this gained in this long while walking: a wall (Roomba.steer)
SPAN = 0.25                      # half window of the ground / air test, s (the read clock jitters
                                 # about a game tick; 0.25 s keeps a fast ramp under AIR_ACC)
AIR_ACC = 1.5                    # |vertical acceleration| over this (units/s^2) = in the air:
                                 # gravity: CE 3.15, H2A 3.8, the others 4.1-4.5 (tools/jumpphys.py)
BLIP_S, BLIP_Z = 0.4, 0.35       # shorter and flatter "air" is a step or a ramp corner: ground
STEEP = 1.0                      # rising or sinking faster than this x the speed over the ground is
                                 # not walking (Halo ramps and stairs stay under 45 degrees)
SETTLE_S = 0.1                   # in the air, ground must hold this long to count as a landing (the
                                 # acceleration estimate crosses zero for a moment after take-off)
LINK_MIN_XY, LINK_MIN_RISE = 0.8, 0.3   # a landed jump is a link if it covers this much or climbs this much
MERGE = 0.6                      # links with take-offs and landings this close are one jump
PORT = 8797
BTN_JUMP, BTN_CROUCH, BTN_ACTION = 2, 4, 32   # botctl.BTN (kept here so the self-test needs no game)
WEAPON_REACH = 8.0               # a weapon lying this close is worth a detour to pick it up
PICKUP_GAMES = {"ce", "h2"}      # bots can pick weapons up here (H2: botcore sends the interaction);
                                 # H2A / H4 need the interaction fields decoded (OWNER_PICKUPS log)
KIND_BOT, KIND_HUMAN, KIND_AIR, KIND_CROUCH, KIND_SPREAD, KIND_WALL, KIND_AIRSPACE = 0, 1, 2, 3, 4, 5, 6
KIND_RAMP = 7                    # also on floor marked on a placed piece's walkable slope (Recorder.on_ramp)
KIND_WINDOW, KIND_FENCE = 8, 9   # walls you see through (glass) / see and shoot through (fences): tools/lidar_walls.py
POCKET_P = 0.3                   # share of Roomba goals that are a called jump (Roomba.pocket)
CALL_XY, CALL_Z = 0.5, 0.2       # a called jump counts only landing this close to the call
POCKET_LIMIT = 120.0             # called-jump search: path cost from the bot (big maps stay quick)
# crouch-jump: crouching in the air lifts the feet by the biped's standing minus crouching height (OBSERVED, the kits'
# player bipeds, physics "height standing" / "height crouching": H3 masterchief 0.725 / 0.5, ODST odst_recon 0.61 /
# 0.45, Reach spartans 0.65 / 0.5, H4 spartans_midnight 0.65 / 0.5, H2A storm_masterchief 0.725 / 0.5; their "jump
# velocity" 3.08 / 2.6 / 2.3 / 2.36 / 2.34 matches jumpphys); it adds no height (docs/research/05 1.3). CE and Halo 2
# not read (H2EK's export has other field names): no crouch-jump calls there.
CROUCH_TUCK = {"h3": 0.225, "odst": 0.16, "reach": 0.15, "h4": 0.15, "h2a": 0.225}
RIDE_P = 0.15                    # share of Roomba goals that ride an untested man cannon or lift (in matches)
USE_P = 0.1                      # share that go and press an untried switch (games where Use works for bots)
RIDE_TRIES = 3                   # a launcher that threw nobody this many times is left alone
SPREAD_R = 2.5                   # paint spreads this far around a player, over connected floor only (1.25 until)
SPREAD_STEP = 0.3                # floor continues if the next cell is within this height (not a cliff)
CRAWL_MIN = 1.0                  # a crouched walk this long (units) is a crouch route
CONFIRM_S = 5.0                  # a landing counts only if the player is still alive this long after
                                 # it (the player: land on a slope, slip off and die -> it must not
                                 # count)
GAME_GONE_S = 10.0               # reads failing this long: the match is over, stop and report
WALL_HS = (0.3, 0.55, 0.85, 1.1)  # heights above the floor a face is looked for (knee to over the head)
BUMP_S = 0.3                     # a bot pushing, alone, stopped this long has bumped into something
SHOT_P = 0.25                    # share of goal picks that go replay a recorded shot nobody replayed this match
BTN_FIRE = 1
PATH_MAX_S = 180.0               # a recording longer than this was forgotten: dropped
PROBE_P = 0.15                   # share of Roomba goals that probe floor the nav cannot reach (Roomba.probe)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def r2(p):
    return [round(float(v), 2) for v in p]


class Track:
    """One player's path, classified ground / air; see the module docstring."""

    def __init__(s):
        s.waiting = []           # [(time, "land" | "crawl", info)]: done, not yet alive for CONFIRM_S
        s.reset()

    def reset(s):
        s.buf = []               # [(t, (x, y, z))], about the last 5 s
        s.k = 0                  # next sample to classify (needs SPAN of future)
        s.air = False
        s.pending = []           # air samples since take-off, not set in stone yet
        s.takeoff = None         # (t, pos): the last ground sample before the air
        s.runup = None           # where the player stood about 0.4 s before taking off
        s.ground = []            # ground samples of the last second
        s.settle = []            # ground samples while in the air, until SETTLE_S says landed
        s.cbuf = {}              # sample time -> crouch held (the player's input)
        s.gbuf = {}              # sample time -> on the ground (when the caller knows)
        s.crawl = []             # ground samples walked crouched, in a row

    def update(s, t, pos, crouch=False, ground=None):
        """Feed one position (and whether crouch is held); returns events ("ground", pos),
        ("crouch", pos) (ground walked crouched), ("air", pos), and after CONFIRM_S alive ("land",
        info) / ("crawl", info) (a crouch route). ground: on the ground or not, when the caller
        knows (the simulator; its level-data floors have kinks a real ramp does not)."""
        pos = tuple(float(v) for v in pos)
        if s.buf and math.dist(pos[:2], s.buf[-1][1][:2]) > 3.0 and t - s.buf[-1][0] < 0.25:
            s.reset()            # a teleporter or a respawn: a new path, no fall between
        if s.buf and t <= s.buf[-1][0]:
            return []
        s.buf.append((t, pos))
        s.cbuf[t] = bool(crouch)
        if ground is not None:
            s.gbuf[t] = bool(ground)
        out = []
        while s.k < len(s.buf) and t - s.buf[s.k][0] >= SPAN:
            tc, pc = s.buf[s.k]
            b = next((j for j in range(s.k - 1, -1, -1) if s.buf[j][0] <= tc - SPAN), None)
            a = next(j for j in range(s.k + 1, len(s.buf)) if s.buf[j][0] >= tc + SPAN)
            if tc in s.gbuf:
                air = not s.gbuf.pop(tc)
            elif b is None:
                air = False      # the start of a path counts as standing
            else:
                (tb, pb), (ta, pa) = s.buf[b], s.buf[a]
                acc = 2 * ((pa[2] - pc[2]) / (ta - tc) - (pc[2] - pb[2]) / (tc - tb)) / (ta - tb)
                vz = (pa[2] - pb[2]) / (ta - tb)
                vh = math.dist(pa[:2], pb[:2]) / (ta - tb)
                # a parabola (jump, fall) or a climb steeper than any floor (a lift: steady speed
                # up, no acceleration; Zenith's lift drew a column of "floor" before this)
                air = abs(acc) > AIR_ACC or abs(vz) > vh * STEEP + 0.4
            out += s._feed(tc, pc, air)
            s.k += 1
        while s.waiting and t - s.waiting[0][0] >= CONFIRM_S:     # alive 5 s after: it counts
            _, kind, info = s.waiting.pop(0)
            out.append((kind, info))
        if len(s.buf) > 160:
            cut = len(s.buf) - 160
            for tt, _ in s.buf[:cut]:
                s.cbuf.pop(tt, None)
            s.buf, s.k = s.buf[cut:], s.k - cut
        return out

    def _feed(s, t, p, air):
        if s.air and not air:
            s.settle.append((t, p))
            if s.settle[-1][0] - s.settle[0][0] < SETTLE_S:
                return []
            (t, p), rest, s.settle = s.settle[0], s.settle[1:], []
            out = s._landed(t, p)
            for tt, q in rest:
                out += s._ground(tt, q)
            return out
        if air:
            out0 = s._end_crawl(t)               # a crouch jump ends a crouch route
            if s.settle:                         # it was not a landing: still in the air
                s.pending += s.settle
                s.settle = []
            if not s.air:
                s.air, s.pending = True, []
                s.takeoff = s.ground[-1] if s.ground else (t, p)
                t0 = s.takeoff[0]
                s.runup = min(s.ground, key=lambda g: abs(g[0] - (t0 - 0.4)))[1] if s.ground else None
            s.pending.append((t, p))
            return out0 + [("air", p)]
        return s._ground(t, p)

    def _landed(s, t, p):
        s.air = False
        t0, p0 = s.takeoff
        # the test looks SPAN ahead, so the last ~0.2 s on the ground before a jump read as air:
        # the real take-off is the last of those still at take-off height (else bots copying the
        # jump took off ~0.4 units early)
        flat = 0
        while flat < len(s.pending) and abs(s.pending[flat][1][2] - p0[2]) < 0.03:
            flat += 1
        if flat:
            (t0, p0), s.pending = s.pending[flat - 1], s.pending[flat:]
        apex = max([q[2] for _, q in s.pending] + [p0[2], p[2]])
        if t - t0 < BLIP_S and abs(p[2] - p0[2]) < BLIP_Z and apex - max(p0[2], p[2]) < 0.15:
            out = [("ground", q) for _, q in s.pending]              # a step or a ramp corner
        else:
            out = []
            s.waiting.append((t, "land", dict(takeoff=p0, t0=t0, landing=p, apex=apex, air_s=round(t - t0, 2),
                                              runup=s.runup, trail=[q for _, q in s.pending])))
        s.pending = []
        return out + s._ground(t, p)

    def _ground(s, t, p):
        s.ground = [g for g in s.ground if t - g[0] < 1.0] + [(t, p)]
        if s.cbuf.get(t):
            if not s.crawl:
                s.crawl_t0 = t
            s.crawl.append(p)
            return [("crouch", p)]
        return s._end_crawl(t) + [("ground", p)]

    def _end_crawl(s, t):
        """Crouch let go (or a jump): a crouched walk of CRAWL_MIN or more waits to be a route."""
        path, s.crawl = s.crawl, []
        if sum(math.dist(a[:2], b[:2]) for a, b in zip(path, path[1:])) >= CRAWL_MIN:
            s.waiting.append((t, "crawl", dict(path=path, start=path[0], end=path[-1], t0=s.crawl_t0)))
        return []

    def shown_trail(s):
        """What the view draws white: the air path now, and landings still inside their 5 s."""
        return ([q for _, kind, info in s.waiting if kind == "land" for q in info["trail"]] + [q for _, q in s.pending])[-120:]

    def die(s):
        """The unit is gone. A fall in progress dies with it, and so do landings less than
        CONFIRM_S old: their trails are not set in stone. Returns where it last was, where it last
        stood and how far it dropped (None if no path)."""
        lost, s.waiting, s.crawl = len(s.waiting), [], []
        if not s.buf:
            s.reset()
            return None
        last = s.buf[-1][1]
        if s.air and s.takeoff:
            stood = s.takeoff[1]
        else:
            stood = s.ground[-1][1] if s.ground else last
        top = max([q[2] for _, q in s.pending] + [stood[2]] + [q[2] for _, q in s.buf[s.k:]])
        info = dict(pos=r2(last), stood=r2(stood), drop=round(top - last[2], 2),
                    in_air=bool(s.air or (s.buf[s.k:] and last[2] < stood[2] - 1.0)), trail_lost=len(s.pending),
                    landings_lost=lost)
        info["cause"] = "fall" if info["drop"] > FALL else "other"
        s.reset()
        return info


def load(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return {}


class Recorder:
    """What a run found (cells by kind, deaths, jump heights) plus the map's links, merged into
    maps/<map>/lidar.json on save. `events` lists each newly marked cell for the live view."""

    def __init__(s, map_name, count_run=True, T=None, path=None):
        s.map, s.T = map_name, T                    # T: the level data, to tell real jumps from hops
        s.path = path or os.path.join(ROOT, "maps", map_name, "lidar.json")
        s.phys = None                               # jumpphys.Phys: lets Roombas call their jumps
        s.ok_key, s.fail_key, s.found_as = "bot_ok", "bot_fail", "bot"   # the simulator: sim_ok, sim_fail, sim
        s.failed_calls = {}                         # called jump key -> misses (shared: no bot calls it a third time)
        s.calls = dict(made=0, missed=0)
        s.features = load_features(map_name).get("features", [])   # the map's weapons, objectives, interactables
        s.feat_tries = {}                           # (kind, x, y) -> tries: launchers ridden, switches pressed
        shots = load(os.path.join(ROOT, "maps", map_name, "shots.json"))
        s.shot_recipes = shots if isinstance(shots, list) else []   # F7 recordings (ShotRec): bots replay them
        s.damage_reader = None                      # ShotRec.read_field in a live match: replays measure damage
        # recorded shots open things once a match: one bot claims a shot; once anyone (a bot, the player,
        # another player) has done it, nobody shoots it again this match
        s.shot_claims, s.shot_done, s.shot_base, s.shot_hits = {}, set(), {}, {}
        s.stored = load(s.path)
        for w in s.stored.get("walk", []):          # first format: [x, y, z, n], bot floor
            if len(w) == 4:
                w.insert(3, KIND_BOT)
        s.links = s.stored.get("links", [])        # shared: grows during the run, saved whole
        s.stored_deaths = s.stored.get("deaths", [])
        s.walk = {}                                 # this run: (ix, iy, iz, kind) -> samples
        s.cover = {(int(x * CELL // COVER), int(y * CELL // COVER), int(z * ZSTEP // 1.0))
                   for x, y, z, k, n in s.stored.get("walk", []) if k != KIND_AIR}
        s.crouch_cells = {crouch_key(x * CELL, y * CELL, z * ZSTEP)
                          for x, y, z, k, n in s.stored.get("walk", []) if k == KIND_CROUCH}
        s.floor_keys = {crouch_key(x * CELL, y * CELL, z * ZSTEP)    # floor someone stood on (half units)
                        for x, y, z, k, n in s.stored.get("walk", []) if k in (KIND_BOT, KIND_HUMAN, KIND_CROUCH)}
        s.targets = {}                              # Roomba index -> its goal (Roombas spread out)
        s.players_pos = []                          # every live player's position this tick (main)
        s.deaths, s.jumps, s.events = [], [], []
        s.spread_done = set()                       # half-unit spots already painted around
        s.cover_spots = {(round(c[0] * 4), round(c[1] * 4), round(c[2] * 2)): c for c in s.stored.get("cover", [])}
        s.glass = load_glass(map_name)              # see-through faces (windows): not cover
        s.fence = load_glass(map_name, "fence")     # see- and shoot-through faces (fences): not cover
        s.fall_grid = {}                             # (round x, round y) -> [z]: spots bots fell from
        for d in s.stored_deaths:
            if d.get("cause") == "fall":
                s.add_fall(d["stood"], d.get("pos"))
        s.count_run, s.saved_deaths, s.saved_walk = count_run, 0, {}
        s.weapons = s.stored.get("weapons", [])     # [{name, pos, seen, picked}]: where weapons lie
        s.ground = []                               # weapons lying now: [(handle, name, pos)] (main loop)
        s.pickup_ok = True                          # can bots pick weapons up in this game?
        s.lock = threading.Lock()

    def add_fall(s, p, to=None):
        """A spot a bot fell from, and which way (to: where it died; the flat direction, or none)."""
        ux = uy = 0.0
        if to is not None:
            n = math.hypot(to[0] - p[0], to[1] - p[1])
            if n > 0.1:
                ux, uy = (to[0] - p[0]) / n, (to[1] - p[1]) / n
        # a walk off an edge, or not: the level data has floor on that way from the spot -> the bot left the ground
        # some other way (a lift, a jump, a push): no edge for walkers there (live Construct: 2,512 of 2,895 refused
        # steps had floor ahead, behind spots bots were thrown from by a lift or jumped from into the pit)
        walk = True
        if (ux or uy) and s.T is not None:
            try:
                import jumpphys
                walk = jumpphys.walk_step(jumpphys.prepare(s.T), list(p[:3]), p[0] + ux * 0.4, p[1] + uy * 0.4)[0] != "ok"
            except Exception:
                walk = True
        s.fall_grid.setdefault((round(p[0]), round(p[1])), []).append((p[0], p[1], p[2], ux, uy, walk))

    def near_fall(s, x, y, z, r=0.8, frm=None):
        """A spot a bot fell from within r (and 1.5 in height)? (A 1-unit grid keeps this cheap.) frm: the walker's
        position: then only a step the way that bot fell counts (one coming nearer, for a fall with no direction): with
        "any step near it" bots near Construct's 35 learned pit falls froze, half the bot time idle (live Nov 4)."""
        gx, gy = round(x), round(y)

        def toward(fx, fy, ux, uy):                  # (a walker's step that heads the way that bot fell, or nearer)
            if frm is None:
                return True
            sx, sy = x - frm[0], y - frm[1]
            if ux or uy:
                return sx * ux + sy * uy > 0.3 * math.hypot(sx, sy)
            return math.hypot(fx - x, fy - y) < math.hypot(fx - frm[0], fy - frm[1]) - 0.05
        return any(abs(f[0] - x) < r and abs(f[1] - y) < r and abs(f[2] - z) < 1.5 and
                   (frm is None or f[5]) and toward(f[0], f[1], *f[3:5])
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) for f in s.fall_grid.get((gx + dx, gy + dy), ()))

    def mark(s, p, kind):
        k = (round(p[0] / CELL), round(p[1] / CELL), round(p[2] / ZSTEP), kind)
        n = s.walk.get(k, 0)
        s.walk[k] = n + 1
        if not n:
            s.events.append(k)
        if kind not in (KIND_AIR, KIND_AIRSPACE):
            s.cover.add((int(p[0] // COVER), int(p[1] // COVER), int(p[2] // 1.0)))
        if kind in (KIND_BOT, KIND_HUMAN, KIND_CROUCH):
            s.floor_keys.add(crouch_key(*p[:3]))
        if kind == KIND_CROUCH:
            s.crouch_cells.add(crouch_key(*p[:3]))
        if kind in (KIND_BOT, KIND_HUMAN, KIND_CROUCH, KIND_SPREAD) and s.on_ramp(p):
            s.mark(p, KIND_RAMP)

    def on_ramp(s, p):
        """Is floor p on a placed piece's walkable slope, a ramp? Steeper faces are walls, painted where the flood meets
        them (spread, wall_out). The level's own slopes are not marked."""
        T = s.T
        if T is None or getattr(T, "tz", None) is None:
            return False
        import numpy as np
        from brain.core import Vec
        from brain.terrain import FLAT_NZ
        j, i = T._cell(Vec(p[0], p[1], p[2]))
        dz = np.abs(T.lz[:, j, i] - p[2])
        with np.errstate(invalid="ignore"):
            if not (dz < 0.3).any():
                return False
        return float(T.tz[int(np.nanargmin(dz)), j, i]) > math.tan(math.acos(FLAT_NZ))

    def walked(s, x, y, z):
        """Did someone stand on floor here (half-unit square, about this height)?"""
        kx, ky, kz = crouch_key(x, y, z)
        return any((kx, ky, kz + dz) in s.floor_keys for dz in (-1, 0, 1))

    def spread(s, p):
        """Paint the floor around p (a player standing there): a flood over the level data's
        walkable cells, each step onto floor within SPREAD_STEP of the last (so it stops at a cliff
        or a drop), up to SPREAD_R. Where the flood meets a wall (wall_out: upright or leaning, not
        a curb or a step) that wall is painted (red in the view) and the floor in front of it is a
        cover spot, unless the face is glass. Needs level data."""
        T = s.T
        if T is None:
            return
        key = (round(p[0] * 2), round(p[1] * 2), round(p[2]))
        if key in s.spread_done:
            return
        s.spread_done.add(key)
        import numpy as np
        from brain.core import Vec
        from brain.terrain import NAV_CELL
        j0, i0 = T._cell(Vec(p[0], p[1], p[2]))
        here = [(abs(float(T.lz[l, j0, i0]) - p[2]), l) for l in range(T.L) if np.isfinite(T.lz[l, j0, i0])]
        if not here or min(here)[0] > 1.0:
            return                                   # floor the level data lacks: nothing to spread over
        start = (min(here)[1], j0, i0)
        r2 = (SPREAD_R / NAV_CELL) ** 2
        seen, todo = {start}, [start]
        while todo:
            l, j, i = todo.pop()
            z = float(T.lz[l, j, i])
            for dj, di in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                jj, ii = j + dj, i + di
                if not (0 <= jj < T.nh and 0 <= ii < T.nw) or (jj - j0) ** 2 + (ii - i0) ** 2 > r2:
                    continue
                nxt = next((ll for ll in range(T.L) if T.lwalk[ll, jj, ii] and abs(float(T.lz[ll, jj, ii]) - z) <= SPREAD_STEP), None)
                if nxt is not None:
                    if (nxt, jj, ii) not in seen:
                        seen.add((nxt, jj, ii))
                        todo.append((nxt, jj, ii))
                        c = T._center(nxt, jj, ii)
                        s.mark((c.x, c.y, c.z), KIND_SPREAD)
                    continue
                if s.wall_out(T, jj, ii, dj, di, z):
                    wx, wy = T.x0 + (ii + 0.5) * NAV_CELL, T.y0 + (jj + 0.5) * NAV_CELL
                    see = s.see_through(wx, wy, z)
                    if see is not None:
                        s.mark((wx, wy, z), see)     # a window or a fence: a wall, but no cover behind it
                        continue
                    s.mark((wx, wy, z), KIND_WALL)
                    c = T._center(l, j, i)
                    s.cover_spots.setdefault((round(c.x * 4), round(c.y * 4), round(c.z * 2)),
                                             [round(c.x, 2), round(c.y, 2), round(c.z, 2), di, dj])

    @staticmethod
    def wall_out(T, j, i, dj, di, z):
        """A wall from floor z out through nav cell (j, i), heading (dj, di)? A steep face at two of
        WALL_HS (one of them chest height or higher) in that cell or the next two out: a leaning
        wall crosses each cell's column over part of that height only, so the old test (chest and
        head in the first cell) missed it. Or that cell's floor rises above chest height (a block, a
        ledge too high to step up)."""
        import numpy as np
        n, hit = T.nstep, set()
        for k in range(3):
            jj, ii = j + dj * k, i + di * k
            if not (0 <= jj < T.nh and 0 <= ii < T.nw):
                break
            block = T.walls[jj * n:(jj + 1) * n, ii * n:(ii + 1) * n].reshape(-1, T.walls.shape[-1])
            for h in WALL_HS:
                if h not in hit and T._wall_bit(block, np.full(len(block), z + h)).any():
                    hit.add(h)
            if k == 0:
                f = T.lz[:, jj, ii]
                with np.errstate(invalid="ignore"):
                    if np.any((f > z + 0.55) & (f < z + 2.5)):
                        return True
        return len(hit) >= 2 and max(hit) >= 0.55

    def bumped(s, p, d):
        """A bot pushed into something, alone, stopped, and did not get up onto it: a wall, whatever
        the level data says. Painted red with the floor in front a cover spot (not glass: no cover
        behind that); where the level data claims open floor the nav learns the spot
        (Terrain.learn_stuck: on its second report)."""
        ahead = (p[0] + d[0] * 0.35, p[1] + d[1] * 0.35, p[2])
        with s.lock:
            see = s.see_through(*ahead)
            if see is not None:
                s.mark(ahead, see)
            else:
                s.mark(ahead, KIND_WALL)
                s.cover_spots.setdefault((round(p[0] * 4), round(p[1] * 4), round(p[2] * 2)),
                                         [round(p[0], 2), round(p[1], 2), round(p[2], 2), round(d[0], 2), round(d[1], 2)])
        if s.T is not None and s.T.ground_ok(ahead[0], ahead[1], p[2], drop=0.3):
            from brain.core import Vec
            s.T.learn_stuck(Vec(*ahead))

    def routed(s, path, who):
        """A route recorded with F6 (PathRec), alive CONFIRM_S at its end: a one-way link with its
        path [[x, y, z, flags]]. The same route again counts again."""
        p0, p1 = list(path[0][:3]), list(path[-1][:3])
        with s.lock:
            link = s.find_link(p0, p1, "route")
            if link is None:
                link = dict(kind="route", take_off=p0, land=p1, runup=None, apex=round(max(q[2] for q in path), 2),
                            air_s=0.0, path=path, ways="one-way", found_by=who, human=0, bot_ok=0, bot_fail=0,
                            t=round(time.time()))
                s.links.append(link)
            link["human" if who == "human" else "bot_ok"] += 1
            return link

    def is_glass(s, x, y, z, table=None):
        """A see-through face (glass) here at chest to head height above floor z? (within a quarter unit: a nav cell's
        centre is up to that far off the face)"""
        table = s.glass if table is None else table
        kx, ky = round(x * 4), round(y * 4)
        for dx in (0, -1, 1):
            for dy in (0, -1, 1):
                for zlo, zhi in table.get((kx + dx, ky + dy), ()):
                    if zlo <= z + 1.0 and zhi >= z + 0.3:
                        return True
        return False

    def see_through(s, x, y, z):
        """KIND_FENCE / KIND_WINDOW for a fence / window face here (chest to head height over floor z), else None."""
        if s.is_glass(x, y, z, getattr(s, "fence", {})):
            return KIND_FENCE
        return KIND_WINDOW if s.is_glass(x, y, z) else None

    def explored(s, x, y, z):
        return any((int(x // COVER) + dx, int(y // COVER) + dy, int(z // 1.0) + dz) in s.cover
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0))

    def explored_many(s, xs, ys, zs):
        """explored() for arrays of points, at once."""
        import numpy as np
        out = np.zeros(len(xs), bool)
        if not s.cover:
            return out
        enc = lambda a, b, c: (a.astype(np.int64) + 50000) * 10 ** 10 + (b.astype(np.int64) + 50000) * 10 ** 5 + (c.astype(np.int64) + 500)
        have = enc(*np.array(list(s.cover)).T)
        cx, cy, cz = np.floor(np.asarray(xs) / COVER), np.floor(np.asarray(ys) / COVER), np.floor(np.asarray(zs))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0):
                    out |= np.isin(enc(cx + dx, cy + dy, cz + dz), have)
        return out

    def worth_a_link(s, p0, p1):
        """A jump is worth knowing if walking from its take-off to its landing is impossible or
        much longer (a gap, a ledge, a lift). A hop across open floor is not (a person strafing in a
        fight made 30 of those on Zenith in a replay). Without level data every jump counts."""
        if s.T is None:
            return True
        from brain.core import Vec
        walk = float(s.T._field(Vec(*p1))[s.T._node(Vec(*p0))])
        return not math.isfinite(walk) or walk > 2.0 * math.dist(p0[:2], p1[:2]) + 3.0

    def find_link(s, p0, p1, kind="jump"):
        """The known link from p0 to p1 (a crouch route also from p1 to p0: it works both ways)."""
        for l in s.links:
            if l.get("kind", "jump") != kind:
                continue
            if math.dist(l["take_off"], p0) < MERGE and math.dist(l["land"], p1) < MERGE:
                return l
            if kind == "crouch" and math.dist(l["take_off"], p1) < MERGE and math.dist(l["land"], p0) < MERGE:
                return l
        return None

    def apex(s):
        """The map's measured jump height (median apex), 0.8 until 20 jumps are measured."""
        j = sorted(s.stored.get("jumps", []) + s.jumps)
        return j[len(j) // 2] if len(j) >= 20 else 0.8

    def classify(s):
        """Every jump link: "two-way" or "one-way" (brain.terrain.jump_ways)."""
        from brain.terrain import jump_ways
        apex = s.apex()
        for l in s.links:
            if l.get("kind", "jump") == "jump":
                l["ways"] = jump_ways(l, s.T, apex)

    def found_weapon(s, name, pos, how):
        """A weapon a bot came close to ("seen") or picked up ("picked"): its name at its spot."""
        if not name or name in ("unknown", "none"):
            return None
        with s.lock:
            w = next((w for w in s.weapons if w["name"] == name and math.dist(w["pos"], pos) < 1.5), None)
            if w is None:
                w = dict(name=name, pos=r2(pos), seen=0, picked=0)
                s.weapons.append(w)
            w[how] += 1
            return w

    def crawled(s, info, who):
        """A crouched walk of CRAWL_MIN or more (alive CONFIRM_S after): a crouch route both ways."""
        p0, p1 = info["start"], info["end"]
        with s.lock:
            link = s.find_link(p0, p1, "crouch")
            if link is None:
                path = info["path"]
                path = path[::max(1, len(path) // 24)] + [p1]
                link = dict(kind="crouch", take_off=r2(p0), land=r2(p1), runup=None, apex=round(max(q[2] for q in path), 2),
                            air_s=0.0, path=[r2(q) for q in path], found_by=who, human=0, bot_ok=0, bot_fail=0,
                            t=round(time.time()))
                s.links.append(link)
            link["human" if who == "human" else "bot_ok"] += 1
            return link

    def landed(s, info, who):
        """A landing alive: the trail is set in stone; a person's real jump or drop becomes (or reuses)
        a link. A bot's landing measures the jump only: a bot's jump counts only when it called it
        and landed on the call. Returns the link or None."""
        p0, p1 = info["takeoff"], info["landing"]
        with s.lock:
            for q in info["trail"]:
                s.mark(q, KIND_AIR)
            # a jump: rose clearly above the take-off (a jump up onto a ledge or a roof lands near
            # its own apex: Battle Creek's roofs were missed when the apex had to clear the landing)
            jump = info["apex"] >= p0[2] + 0.3 or info["apex"] >= max(p0[2], p1[2]) + 0.15
            if jump:
                s.jumps.append(round(info["apex"] - p0[2], 3))
            if who != "human":
                return None
            xy, rise = math.dist(p0[:2], p1[:2]), p1[2] - p0[2]
            if not (jump or abs(rise) >= 1.0) or (xy < LINK_MIN_XY and rise < LINK_MIN_RISE):
                return None                         # a hop in place, or a step (a lift ride is a link)
            link = s.find_link(p0, p1)
            if link is None:                       # the same jump the other way: it is two-way
                back = s.find_link(p1, p0)
                if back is not None:
                    back["back"] = back.get("back", 0) + 1
                    back["human" if who == "human" else "bot_ok"] += 1
                    return back
            climb = who == "human" and rise >= LINK_MIN_RISE   # a person climbing: always worth knowing
            if link is None and not climb and not s.worth_a_link(p0, p1):
                return None
            if link is None:
                trail = info["trail"]
                path = [p0] + trail[::max(1, len(trail) // 16)] + [p1]
                link = dict(take_off=r2(p0), land=r2(p1), runup=r2(info["runup"]) if info["runup"] else None,
                            apex=round(info["apex"], 2), air_s=info["air_s"], path=[r2(q) for q in path],
                            found_by=who, human=0, bot_ok=0, bot_fail=0, t=round(time.time()))
                s.links.append(link)
            link["human" if who == "human" else "bot_ok"] += 1
            return link

    def died(s, info, who, t):
        with s.lock:
            d = dict(t=round(t, 1), who=who, **info)
            s.deaths.append(d)
            if d["cause"] == "fall":
                s.add_fall(d["stood"], d.get("pos"))
            return d

    def save(s, bot_seconds=0.0, human_seconds=0.0):
        """Merge this run into maps/<map>/lidar.json (atomic). Safe to call every minute."""
        s.classify()
        # what is new, copied under the lock; the file read, merge and write outside it (Spire's 3.5 MB took about 100
        # ms, and with the lock held the bots' tick waited on it once a minute: review). One save at a time
        with s.lock:
            new_walk = {k: n - s.saved_walk.get(k, 0) for k, n in s.walk.items()}
            s.saved_walk = dict(s.walk)
            deaths, jumps, run = s.deaths[s.saved_deaths:], s.jumps, s.count_run
            # (a copy of each weapon record: dict() of the list failed every save on a map with weapons, since 7f95635)
            # (not the map's rides, tools/lidar_rides.py, rebuilt each run; not crouch-jumps bots found: the fighting
            # brain does not crouch in the air yet, and a plain try of one falls short)
            keep = [l for l in s.links if l.get("found_by") != "map" and not (l.get("crouch") and not l.get("human"))]
            links, weapons, cover = json.loads(json.dumps(keep)), [dict(w) for w in s.weapons], sorted(s.cover_spots.values())
            s.count_run, s.saved_deaths, s.jumps = False, len(s.deaths), []
        with s.__dict__.setdefault("save_lock", threading.Lock()):
            old = load(s.path)
            walk = {}
            for w in old.get("walk", []):
                if len(w) == 4:
                    w.insert(3, KIND_BOT)
                walk[tuple(w[:4])] = w[4]
            for k, n in new_walk.items():           # only what is new since the last save
                walk[k] = walk.get(k, 0) + n
            out = dict(cell=CELL, zstep=ZSTEP,
                       runs=old.get("runs", 0) + (1 if run else 0),
                       bot_minutes=round(old.get("bot_minutes", 0) + bot_seconds / 60, 1),
                       human_minutes=round(old.get("human_minutes", 0) + human_seconds / 60, 1),
                       walk=[[*k, n] for k, n in sorted(walk.items())],
                       deaths=(old.get("deaths", []) + deaths)[-3000:],
                       jumps=(old.get("jumps", []) + jumps)[-2000:],
                       links=links, weapons=weapons, cover=cover)
            objectives = s.objectives.saved() if getattr(s, "objectives", None) is not None else old.get("objectives")
            if objectives:                           # every gametype objective place, reached or not (Objectives)
                out["objectives"] = objectives
            if getattr(s, "director", None) is not None and s.director.history:   # this run's coverage, what is left
                out["coverage"] = s.director.report()
            os.makedirs(os.path.dirname(s.path), exist_ok=True)
            tmp = s.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(out, f)
            os.replace(tmp, s.path)
            return out


_SCAN_INFO = {}
ART = os.path.join(HERE, "view_art")   # map_art.py: MCC's game logos, map pictures and real map names
_TITLES = None


def map_titles():
    global _TITLES
    if _TITLES is None:
        _TITLES = load(os.path.join(ART, "names.json"))
    return _TITLES


def map_title(name):
    """A map's real name (Battle Creek for beavercreek); a level MCC does not have keeps its folder name. A map variant
    (brain/variants.py): its base map's, then its own name once known, else its id."""
    base, _, vid = name.partition("/variants/")
    title = map_titles().get(base) or re.sub(r"^(h2a|h2|h3|h4|odst|reach)_", "", base).replace("_", " ").title()
    if vid:
        from brain.variants import info
        v = info(name) or {}
        seen = (v.get("first_seen") or "")[:10]
        when = ""
        if seen:
            try:
                when = ", first played " + time.strftime("%b %d", time.strptime(seen, "%Y-%m-%d")).replace(" 0", " ")
            except ValueError:
                pass
        title += ": " + (v.get("name") or f"Forge layout {vid[1:5].upper()}{when}")
    return title


MAP_NAME = re.compile(r"[a-z0-9_]+(/variants/v[0-9a-f]{8})?")    # a map, or a map variant filed under it


def map_ok(name):
    """A map name the view may open: a map with level data, or a map variant of one."""
    return bool(MAP_NAME.fullmatch(name)) and os.path.exists(
        os.path.join(ROOT, "maps", name.partition("/")[0], "heightmap.npz"))


def file_name(name):
    """A map name as part of a file name (a map variant's has slashes)."""
    return name.replace("/variants/", "@")


def seat_places(live, players):
    """Every vehicle [{handle, kind, pos}], and a rider's place made his vehicle's (players: live.players dicts, changed in
    place, "riding" set): a seated unit's own is its seat's offset, read as about (0, 0, 0) (the player's Forge run: his
    bug reports from vehicles filed at the origin, his floor painted there, links of 180-200 u). A gun riding on a
    vehicle (a Warthog's turret) gives its vehicle's place, as tools/live_bots.py snapshot does."""
    objs = live.objects(getattr(live, "VEHICLE_TYPES", (1,)))   # (Halo 4: its giants too, the Mantis)
    pos = {h: p for h, typ, path, p in objs}
    parent = {}
    for h, *_ in objs:
        try:
            par = struct.unpack("<I", live.g.read(live.object(h) + getattr(live, "PARENT_AT", 0x14), 4))[0]
        except Exception:
            continue
        if par != 0xFFFFFFFF:
            parent[h] = par
    kind = {h: path.rsplit("\\", 1)[-1] for h, typ, path, p in objs}
    for p in players:
        h = p.get("vehicle", -1)
        if h in (-1, None):
            continue
        if h in parent:
            p["turret"] = kind.get(h, "")           # (on the gun riding on it: its name, the vehicle is its parent's)
        for _ in range(3):
            h = parent.get(h, h)
        p["pos"], p["riding"], p["vehicle_top"] = pos.get(h), True, h
    return [dict(handle=h, kind=kind[h], pos=p) for h, typ, path, p in objs if h not in parent]


def people_states(players, bot_ids, alive, prev):
    """The players as brain.core.PlayerState (for the Data collector and the bug reports): place, speed from last tick's
    place (prev: index -> (x, y, z), updated), aim, guns, equipment."""
    from brain.core import PlayerState, Vec
    out = []
    for p in players:
        if not p.get("pos"):
            continue
        q, pos = prev.get(p["index"]), Vec(*p["pos"])
        vel = Vec((pos.x - q[0]) * HZ, (pos.y - q[1]) * HZ, (pos.z - q[2]) * HZ) if q and math.dist(q, p["pos"]) < 1.0 else Vec()
        prev[p["index"]] = tuple(p["pos"])
        fx, fy, fz = p.get("aim") or (1.0, 0.0, 0.0)
        out.append(PlayerState(p["index"], p.get("team", 0), p.get("name", ""), pos, vel, math.atan2(fy, fx),
                               math.atan2(fz, math.hypot(fx, fy)), alive(p), p.get("shield", 1.0), p.get("health", 1.0),
                               p.get("weapon", "none"), p.get("weapons", []), p.get("ammo", []), p.get("mag", []),
                               p.get("vehicle_top", p.get("vehicle", -1)), gunner_seat=bool(p.get("turret")),
                               turret=p.get("turret", ""),
                               is_bot=p["index"] in bot_ids, equipment=p.get("equipment", ""),
                               ability_on=bool(p.get("ability_on", False))))
    return out


def pickups_path(name):
    """logs/owner_pickups_<map>.jsonl: the player's weapon pickups with his input, for decoding the game's pickup."""
    return os.path.join(ROOT, "logs", f"owner_pickups_{file_name(name)}.jsonl")


def map_list_names():
    """Every map with level data (maps/<map>/heightmap.npz), each followed by the Forge layouts filed under it
    (maps/<map>/variants/<id>, brain/variants.py)."""
    names = []
    for name in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        if name.startswith("_") or not os.path.exists(os.path.join(ROOT, "maps", name, "heightmap.npz")):
            continue
        names.append(name)
        vd = os.path.join(ROOT, "maps", name, "variants")
        names += [f"{name}/variants/{v}" for v in sorted(os.listdir(vd))] if os.path.isdir(vd) else []
    return names


def map_list():
    """Every map with level data, for the view's map picker: its game, and its LiDAR scans (from
    matches: lidar.json; from the simulator: lidar_sim.json) with runs, minutes and floor cells. Map variants filed
    under a map (brain/variants.py) follow it, each with its own scans."""
    import jumpphys
    out = []
    for name in map_list_names():
        d = os.path.join(ROOT, "maps", name)
        item = dict(name=name, title=map_title(name), mcc=name.partition("/")[0] in map_titles(),
                    game=jumpphys.game_of(name.partition("/")[0]))
        for key, fn in (("scan", "lidar.json"), ("sim", "lidar_sim.json")):
            p = os.path.join(d, fn)
            if os.path.exists(p):
                stamp = os.path.getmtime(p)
                if _SCAN_INFO.get(p, (None,))[0] != stamp:   # read once per change
                    data = load(p)
                    walk = data.get("walk", [])
                    _SCAN_INFO[p] = (stamp, dict(runs=data.get("runs", 0), bot_minutes=data.get("bot_minutes", 0),
                                                 human_minutes=data.get("human_minutes", 0), links=len(data.get("links", [])),
                                                 human_links=sum(1 for l in data.get("links", []) if l.get("human")),
                                                 cells=sum(1 for w in walk if len(w) == 5 and w[3] not in (KIND_AIR, KIND_AIRSPACE)),
                                                 updated=round(stamp)))
                info = _SCAN_INFO[p][1]
                # (the simulator also writes its jumps into lidar.json: a lidar.json with no floor and only bots'
                # links is the simulator's, not a scan from matches; the view opens the simulator's scan for it)
                if info["cells"] or (info["human_links"] if key == "scan" else info["links"]):
                    item[key] = info
        out.append(item)
    return out


def remove_refused(h, name, src, header):
    """Why the view may not remove this scan (an HTTP status), or None. The header: a page from another
    site cannot send it without asking first (CORS), and this server never says yes."""
    if header != "remove":
        return 403
    if src not in ("scan", "sim") or not map_ok(name):
        return 404
    if name == h.rec.map and h.mode != "stored":
        return 409                                   # being scanned now: the run would write it back
    return None


def remove_scan(name, src, root=None):
    """The maps list's Remove. "scan": the scan from matches (lidar.json: floor, walls, deaths, weapons, every
    jump and path, people's too). "sim": the simulator's scan (lidar_sim.json) and what it put into
    lidar.json (its jumps, its results on the others). Nothing is deleted: the files go to
    backups/lidar/<map>_<time>_<file> (copy one back into maps/<map>/ to restore it). Returns the backups."""
    import shutil
    root = root or ROOT
    d, bak = os.path.join(root, "maps", name), os.path.join(root, "backups", "lidar")
    os.makedirs(bak, exist_ok=True)
    stamp, kept = time.strftime("%Y%m%d-%H%M%S"), []

    def keep(fn, move):
        p, n = os.path.join(bak, f"{file_name(name)}_{stamp}_{fn}"), 1
        while os.path.exists(p):                     # two removals in one second: never overwrite a backup
            p, n = os.path.join(bak, f"{file_name(name)}_{stamp}-{n}_{fn}"), n + 1
        kept.append(p)
        (shutil.move if move else shutil.copy2)(os.path.join(d, fn), p)

    main = os.path.join(d, "lidar.json")
    if src == "scan":
        if os.path.exists(main):
            keep("lidar.json", True)
        return kept
    if os.path.exists(os.path.join(d, "lidar_sim.json")):
        keep("lidar_sim.json", True)
    data = load(main)
    links = data.get("links", [])
    if any(l.get("found_by") == "sim" or l.get("sim_ok") or l.get("sim_fail") for l in links):
        keep("lidar.json", False)
        data["links"] = [{**l, "sim_ok": 0, "sim_fail": 0} if ("sim_ok" in l or "sim_fail" in l) else l
                         for l in links if l.get("found_by") != "sim"]
        if data["links"] or data.get("walk"):
            json.dump(data, open(main + ".tmp", "w"))
            os.replace(main + ".tmp", main)
        else:
            os.remove(main)                          # the simulator's jumps were all it held (backed up)
    return kept


def load_features(map_name, stations=None, oob=None):
    """maps/<map>/features.json (tools/map_features.py): weapons, objective points, interactables; {} when it was not
    built (a map variant: its base map's). With the stations read live (brain/stations.py, a Forge layout's own: armor
    abilities, teleporters and the pairs people took, man cannons, lifts, zones, spawns, the player's marks; stations:
    the running Stations, else its stations.json) where the map's own data has nothing of that kind within 1 u. And the
    out of bounds learned (brain/oob.py: oob, the running Oob, else its oob.json), drawn as zones."""
    d = load(os.path.join(ROOT, "maps", map_name.partition("/")[0], "features.json"))
    from brain import stations as S
    feats, pairs = S.features(map_name, None if stations is None else
                              dict(objects=stations.objects, teleports=stations.teleports, marks=stations.marks))
    own = d.get("features", [])
    feats = [f for f in feats if not any(g.get("kind") == f["kind"] and math.dist(g["pos"], f["pos"]) < 1.0 for g in own)]
    from brain import oob as O
    feats += O.features(map_name, None if oob is None else dict(spots=oob.spots))
    if feats or pairs:
        d = dict(d, features=own + feats, teleporters=list(d.get("teleporters", [])) + pairs)
    return d


OBJ_MERGE = 2.5          # objective places this close are one place to visit (lidar_director.SPOT_DONE_R)
OBJ_REACH_R, OBJ_REACH_Z = 2.5, 2.0   # anyone this close (flat, and up or down) has been at an objective
OBJ_NAV_Z = 2.5          # the nav's floor at an objective this far up or down from it: not on the nav there


def objective_points(map_name, stations=None):
    """Every gametype objective place of a map, all modes at once: [{pos, roles, names, src}], places within OBJ_MERGE
    merged. The map's own come from its scenario as the editing kits export it (objects.json netgame flags and Forge
    labels: flag stands and returns, hills, oddball and bomb spawns, plant points, territories, havens, drop points,
    race checkpoints, Invasion zones ...; roles by tools/map_features.py), which the game itself only spawns for the mode
    being played. Plus objective objects read live (brain/stations.py; a Forge layout's own). A Forge canvas variant
    (no layout of the base map's own, brain/variants.py base_area) has only the live ones."""
    import map_features as F
    from brain import stations as S
    from brain.variants import base_area, base_of
    base = base_of(map_name)
    objs = load(os.path.join(ROOT, "maps", base, "objects.json"))
    found = []
    if base == map_name or base_area(objs):
        for f in F.from_objects(objs)[0] if objs else []:
            if f["kind"] == "objective":
                found.append((f["role"], f["name"], f["pos"], "map"))
    mv = load(os.path.join(ROOT, "maps", map_name, "mvar_objects.json")) if base != map_name else None
    for f in F.from_objects(mv)[0] if mv else []:     # the variant's own file (brain/mvar.py): every mode's labelled
        if f["kind"] == "objective":                   # objectives, spawned or not by the game type being played
            found.append((f["role"], f["name"], f["pos"], "mvar"))
    for o in (stations.objects if stations is not None else S.load(map_name)["objects"]):
        if o.get("kind") == "objective":
            found.append((F.role_of(o["what"]) or "objective", o["what"], o["pos"], "live"))
    out = []
    for role, name, pos, src in found:
        if not all(math.isfinite(v) for v in pos):
            continue
        p = next((q for q in out if math.dist(q["pos"], pos) < OBJ_MERGE), None)
        if p is None:
            out.append(dict(pos=[round(float(v), 2) for v in pos], roles=[role], names=[name], src=src))
        else:
            p["roles"] += [role] if role not in p["roles"] else []
            p["names"] += [name] if name not in p["names"] else []
            p["src"] = p["src"] if p["src"] == src else "map+live"
    return out


class Objectives:
    """Every gametype objective place (objective_points) as goals in a LiDAR run (a match or the simulator): one LiDAR
    bot walks to each (the director's spots, label = its role), and the floor round it gets painted; reached once
    anyone (bot or person) stood within OBJ_REACH_R. Saved in lidar.json "objectives" (lidar_sim.json for the
    simulator) with the nav's verdict (on: the nav has floor there; reach: walkable from the spawns), merged over runs:
    reached once stays reached, and places already reached are not sent again."""

    def __init__(s, map_name, T, stored=(), stations=None):
        s.map, s.T, s.spots = map_name, T, {}
        old = {tuple(o["pos"]): o for o in stored or ()}
        s.points = objective_points(map_name, stations)
        for p in s.points:
            o = old.get(tuple(p["pos"]))
            p["reached"] = bool(o and o.get("reached"))
            p["given_up"] = bool(o and o.get("given_up")) and not p["reached"]
            p.update(s.nav_of(p["pos"]))
        s.kept = [o for k, o in old.items() if not any(tuple(p["pos"]) == k for p in s.points)]   # (another layout's)

    def nav_of(s, pos):
        """{floor, on, reach}: the nav's floor under the objective, whether it is there, walkable from the spawns."""
        T = s.T
        if T is None or not T.inside(pos[0], pos[1]):
            return dict(floor=None, on=False, reach=False)
        from brain.core import Vec
        l, j, i = T._node(Vec(*pos))
        c = T._center(l, j, i)
        on = bool(T.lwalk[l, j, i]) and math.isfinite(c.z) and abs(c.z - pos[2]) < OBJ_NAV_Z
        reach = getattr(T, "reach", None)
        return dict(floor=[round(c.x, 2), round(c.y, 2), round(c.z, 2)] if math.isfinite(c.z) else None, on=on,
                    reach=bool(on and (reach is None or reach[l, j, i])))

    @staticmethod
    def goal(p):
        """Where a place is reached: the nav's floor there, else the objective itself (a stand on something the nav
        lacks, or over a drop: only someone up there reaches it)."""
        return p["floor"] if p["on"] else p["pos"]

    def seed(s, director):
        """Each place not yet reached as a spot for one bot (goal)."""
        s.spots = {}
        if director is None:
            return 0
        for k, p in enumerate(s.points):
            if not p["reached"]:
                s.spots[k] = director.add_spot(s.goal(p), bots=1, label=p["roles"][0])
        return len(s.spots)

    def add_live(s, stations, director):
        """Objective objects the running game has spawned (stations, brain/stations.py) that no place covers yet: new
        places, each a spot for one bot now (a Forge layout's first run). The new places."""
        import map_features as F
        new = []
        for o in stations.objects:
            if o.get("kind") != "objective" or not all(math.isfinite(v) for v in o["pos"]):
                continue
            if any(math.dist(p["pos"], o["pos"]) < OBJ_MERGE for p in s.points):
                continue
            p = dict(pos=[round(float(v), 2) for v in o["pos"]], roles=[F.role_of(o["what"]) or "objective"],
                     names=[o["what"]], src="live", reached=False, given_up=False)
            p.update(s.nav_of(p["pos"]))
            s.points.append(p)
            if director is not None:
                s.spots[len(s.points) - 1] = director.add_spot(s.goal(p), bots=1, label=p["roles"][0])
            new.append(p)
        return new

    def update(s, positions, now):
        """positions: where every living player (bots and people) is now; marks places reached (and their spots).
        Twice a second at most (now: the run's clock)."""
        if now - getattr(s, "last_t", -9.0) < 0.5:
            return
        s.last_t = now
        for k, p in enumerate(s.points):
            if p["reached"]:
                continue
            x, y, z = s.goal(p)
            if any(math.hypot(q[0] - x, q[1] - y) < OBJ_REACH_R and abs(q[2] - z) < OBJ_REACH_Z for q in positions):
                p["reached"], p["given_up"] = True, False
                if k in s.spots:
                    s.spots[k]["done"] = True
            elif k in s.spots and s.spots[k]["done"]:   # (a bot the director sent got there)
                p["reached"], p["given_up"] = True, False
            elif k in s.spots and s.spots[k]["given_up"]:
                p["given_up"] = True

    def saved(s):
        for p in s.points:                            # (the nav learns during a run: new jumps reach more)
            p.update(s.nav_of(p["pos"]))
        return [dict(p) for p in s.points] + s.kept

    def line(s):
        n, r = len(s.points), sum(p["reached"] for p in s.points)
        off = sum(not p["reach"] for p in s.points)
        return f"objectives: {r} of {n} places reached, {off} not reachable on the nav from the spawns"


def wall_kinds_view(map_name):
    """The map's windows and fences for the view (maps/<map>/wall_kinds.json, tools/lidar_walls.py): {kind: [[x, y, z low,
    z high]]} in units, upright faces and flat decks alike (a breaking window in "window_breaks")."""
    d = load(os.path.join(ROOT, "maps", map_name.partition("/")[0], "wall_kinds.json"))
    out = dict(window=[], window_breaks=[], fence=[])
    for k in ("window", "window_floor", "fence", "fence_floor"):
        for r in d.get(k, []):
            kind = "fence" if k.startswith("fence") else "window_breaks" if len(r) > 4 and r[4] else "window"
            out[kind].append([r[0] / 4, r[1] / 4, r[2], r[3]])
    for r in load(os.path.join(ROOT, "maps", map_name.partition("/")[0], "walls_learned.json")) or []:
        out["fence"].append([r[0] / 4, r[1] / 4, r[2], r[3]])   # (rounds went through there: Terrain.learn_shot_through)
    out["source"] = d.get("source", [])
    return out


def load_glass(map_name, kind="window"):
    """Quarter-unit cells -> [(z low, z high)] of see-through faces: windows (maps/<map>/glass.json, tools/glass_mask.py,
    and wall_kinds.json's windows, tools/lidar_walls.py) or kind "fence" (wall_kinds.json's fences and the walls rounds
    went through in matches, walls_learned.json). Empty when the map has none or they were not built. (A map variant:
    its base map's.)"""
    base = os.path.join(ROOT, "maps", map_name.partition("/")[0])
    cells = load(os.path.join(base, "glass.json")).get("cells", []) if kind == "window" else []
    out = {}
    learned = load(os.path.join(base, "walls_learned.json")) if kind == "fence" else []
    learned = [r for r in learned if not r[4]] if isinstance(learned, list) else []   # (walls rounds went through)
    for r in list(cells) + list(load(os.path.join(base, "wall_kinds.json")).get(kind, [])) + learned:
        out.setdefault((r[0], r[1]), []).append((r[2], r[3]))
    return out


def crouch_key(x, y, z):
    """Crouch floor at half-unit resolution (bots crouch on and next to it)."""
    return (round(x * 2), round(y * 2), round(z))


def self_safe(T, ph, a, ux, uy, back, turn):
    """Does a jump from take-off a toward (ux, uy), taken `back` units early and `turn` radians off,
    still come down on something, softly enough to live?"""
    import jumpphys
    c, s = math.cos(turn), math.sin(turn)
    out, _, _, _, impact = jumpphys.fly(T, ph, (a[0] - ux * back, a[1] - uy * back, a[2]),
                                        (ux * c - uy * s) * ph.run, (ux * s + uy * c) * ph.run, dt=1.0 / HZ)
    return out == "land" and impact < ph.lethal_v


def _lands_near(flight, p):
    """A fly_tuck flight came down alive-ish on the floor p was (0.6 u flat, 0.3 u up or down)."""
    out, q = flight[0], flight[1]
    return out == "land" and math.dist(q[:2], p[:2]) < 0.6 and abs(q[2] - p[2]) < 0.3


def fly_tuck(T, ph, p, vx, vy, tuck, dt=1 / 30, max_t=6.0):
    """jumpphys.fly with the feet lifted by tuck at the apex (crouch held in the air: CROUCH_TUCK); tuck 0 is a plain
    jump. (outcome, where it ended, highest z, seconds, impact speed)."""
    import jumpphys
    if not tuck:
        return jumpphys.fly(T, ph, p, vx, vy, dt=dt, max_t=max_t)
    jumpphys.prepare(T)
    p, v = list(p), [vx, vy, ph.v0]
    top, t, done = p[2], 0.0, False
    while t < max_t:
        if not done and v[2] <= 0.0:
            p[2] += tuck
            done = True
        out, impact = jumpphys.air_step(T, ph, p, v, dt)
        t += dt
        top = max(top, p[2])
        if out != "air":
            return out, p, top, t, impact
    return "air", p, top, t, 0.0


def route_path(samples):
    """A recorded route's samples [(t, pos, crouch held)] -> its path [[x, y, z, flags]]: a point
    about every 0.3 units, each take-off that rose flagged jump (walking off a ledge needs no
    jump), points walked crouched flagged crouch (brain.terrain ROUTE_JUMP / ROUTE_CROUCH)."""
    from brain.terrain import ROUTE_JUMP, ROUTE_CROUCH
    tr, jumps, seen = Track(), set(), []
    for t, p, c in samples:                         # the same ground / air test as everything else
        tr.update(t, p, c)
        for _, kind, info in tr.waiting:            # each landing waits CONFIRM_S there: seen once
            if kind == "land" and not any(info is x for x in seen):
                seen.append(info)
                if info["apex"] >= info["takeoff"][2] + 0.15:
                    jumps.add(info["t0"])
    out, last = [], None
    for t, p, c in samples:
        f = (ROUTE_JUMP if t in jumps else 0) | (ROUTE_CROUCH if c else 0)
        if last is None or f & ROUTE_JUMP or math.dist(p, last) >= 0.3 or t == samples[-1][0]:
            out.append(r2(p) + [f])
            last = p
        elif f:
            out[-1][3] |= f
    return out


class PathRec:
    """F6: record a route by doing it. F6, do it (walk, jump, crouch), F6 at its end; still alive
    CONFIRM_S later it is saved as a one-way route (Recorder.routed) that every bot may take to
    get there. Dying first, or recording longer than PATH_MAX_S, loses it."""

    def __init__(s, rec, send):
        s.rec, s.send, s.state, s.samples = rec, send, None, []

    def key(s, now):
        if s.state is None:
            s.state, s.samples, s.t0 = "rec", [], now
            s.send("RECORDING PATH", "Do the route, then press F6 at its end")
        elif s.state == "rec":
            pts = [q for _, q, _ in s.samples]
            if sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) < 1.0:
                s.state = None
                s.send("PATH TOO SHORT", "Nothing saved")
                return
            s.state, s.t_end = "confirm", now
            s.send("PATH ENDED", f"Stay alive {CONFIRM_S:.0f} s to save it")

    def update(s, now, pos, alive, crouch=False):
        """the player's position each tick; returns the link when a route is saved."""
        if s.state is None:
            return None
        if not alive or pos is None:
            s.state = None
            s.send("PATH LOST", "You died before it was saved")
            return None
        if s.state == "rec":
            if now - s.t0 > PATH_MAX_S:
                s.state = None
                s.send("PATH LOST", f"Over {PATH_MAX_S / 60:.0f} minutes: press F6 again at the route's end")
                return None
            s.samples.append((now, tuple(float(v) for v in pos), bool(crouch)))
            return None
        if now - s.t_end < CONFIRM_S:
            return None
        s.state = None
        link = s.rec.routed(route_path(s.samples), "human")
        s.send("PATH SAVED", "Bots take it from now on when it is their way there")
        return link

    def view(s):
        """For the 3D view: None, or the state and the path so far."""
        if s.state is None:
            return None
        return dict(state=s.state, path=[r2(q) for _, q, _ in s.samples[::3]][-600:])


def hits_needed(r, near=0.8):
    """How many of the player's recorded shots landed on the target: what it took him (at least 1)."""
    return max(1, sum(1 for q in r.get("shots", []) if math.dist(q["impact"], r["target"]) < near))


class ShotRec:
    """F7: F7, shoot what opens something (a gate button, a bridge lock), F7. Every shot he fires meanwhile
    (a projectile leaving within 2.5 of him, followed until it is gone: its last position is the impact)
    and every object that moved between the two presses is saved as a recipe in maps/<map>/shots.json:
    stand here, aim there, fire this long. Roombas replay each recipe."""
    SKIP_TYPES = (0, 2, 5)           # bipeds, weapons, projectiles: always moving, not what a shot opened

    # H2A / H4 object types (device_probe.py): 7 machines, 8 controls, 10 crates; all but SKIP_TYPES are read
    DEV_BYTES = 0x600

    def __init__(s, live, map_name, send, rec=None):
        s.live, s.map, s.send, s.state, s.rec = live, map_name, send, None, rec
        s.path = os.path.join(ROOT, "maps", map_name, "shots.json")
        if rec is not None:
            rec.damage_reader = s.read_field             # bots measure the damage they deal on replay

    def device_memory(s):
        """{handle: (type, pos, bytes)} of the devices and crates (empty where the game has no object reader)."""
        out = {}
        if not hasattr(s.live, "object"):
            return out
        try:
            for h, t, n, p in s.live.objects():      # every kind (Stonetown bridge locks: not 7, 8 or 10)
                if t in s.SKIP_TYPES:
                    continue
                a = s.live.object(h)
                b = s.live.g.read(a, s.DEV_BYTES) if a else None
                if b and len(b) == s.DEV_BYTES:
                    out[h] = (t, p, b)
        except Exception:
            pass
        return out

    def read_field(s, typ, pos, off):
        """The float at +off of the live object of this type nearest pos (within 1 unit), or None."""
        try:
            best = min(((math.dist(p, pos), h) for h, t, n, p in s.live.objects({typ})), default=None)
            if best is None or best[0] > 1.0:
                return None
            v = struct.unpack("<f", s.live.g.read(s.live.object(best[1]) + off, 4))[0]
            return v if math.isfinite(v) else None
        except Exception:
            return None

    def damage_field(s, before, after, target):
        """the player's damage, not his shot count (the player: an SMG spray and a battle rifle are not the
        same number of shots): on the devices near where his shots landed, the float that dropped most
        while he fired, leaving out offsets that also changed on far objects (timers)."""
        far_changed = {}
        for h, (t, p, a) in before.items():
            if h in after and math.dist(p, target) > 4.0:
                b = after[h][2]
                for off in range(0, len(a) - 3, 4):
                    if a[off:off + 4] != b[off:off + 4]:
                        far_changed[off] = far_changed.get(off, 0) + 1
        n_far = max(1, sum(1 for h, v in before.items() if math.dist(v[1], target) > 4.0))
        best = None
        for h, (t, p, a) in before.items():
            if h not in after or math.dist(p, target) > 2.0:
                continue
            b = after[h][2]
            for off in range(0, len(a) - 3, 4):
                if far_changed.get(off, 0) > n_far // 2:
                    continue
                x, y = struct.unpack_from("<f", a, off)[0], struct.unpack_from("<f", b, off)[0]
                if not (math.isfinite(x) and math.isfinite(y)) or abs(x) > 1e6 or abs(y) > 1e6:
                    continue
                if x - y > 1.0 and (best is None or x - y > best["drop"]):
                    best = dict(type=t, pos=r2(p), offset=off, drop=round(x - y, 2))
        return best

    def objects(s, types=None):
        try:
            return {h: (t, p) for h, t, n, p in s.live.objects(types)}
        except Exception as e:
            if not getattr(s, "warned", False):          # say it once: a silent {} looked like "no shots"
                s.warned = True
                print(f"shot recording: object read failed ({type(e).__name__}: {e})", flush=True)
            return {}

    def key(s, now, person):
        if not hasattr(s.live, "objects"):
            s.send("SHOTS NOT RECORDED", "This game's objects are not read yet")
            return
        if s.state is None:
            s.state, s.t0, s.shots, s.track, s.ignored, s.seen, s.first_d = "rec", now, [], {}, set(), 0, []
            s.before = {h: v for h, v in s.objects().items() if v[0] not in s.SKIP_TYPES}
            s.dev_before = s.device_memory()
            s.weapon = (person or {}).get("weapon")
            s.send("RECORDING SHOTS", "Shoot what opens it, then press F7")
            return
        s.state = None
        s.finish_tracks(set())
        after = {h: v for h, v in s.objects().items() if v[0] not in s.SKIP_TYPES}
        changed = [dict(type=t, frm=r2(s.before[h][1]), to=r2(p)) for h, (t, p) in after.items()
                   if h in s.before and math.dist(p, s.before[h][1]) > 0.05]
        changed += [dict(type=t, new=r2(p)) for h, (t, p) in after.items() if h not in s.before]
        changed += [dict(type=t, gone=r2(p)) for h, (t, p) in s.before.items() if h not in after]
        print(f"{now:6.1f}s shot recording: {s.seen} projectiles seen, {len(s.shots)} on the person's aim line; "
              f"first seen this far from him: {sorted(s.first_d)[:12]}", flush=True)
        if not s.shots:
            s.send("NO SHOTS SEEN", "Nothing saved (fire while recording)")
            return
        mid = lambda pts: [sorted(v)[len(v) // 2] for v in zip(*pts)]
        target = mid([q["impact"] for q in s.shots])
        recipe = dict(t=round(time.time()), stand=r2(mid([q["stand"] for q in s.shots])),
                      target=r2(target), seconds=round(now - s.t0, 1), weapon=s.weapon,
                      damage=s.damage_field(s.dev_before, s.device_memory(), target),
                      shots=s.shots[:40], changed=changed[:60])
        data = load(s.path) if os.path.exists(s.path) else []
        data = data if isinstance(data, list) else []
        data.append(recipe)
        tmp = s.path + ".tmp"
        json.dump(data, open(tmp, "w"), indent=0)
        os.replace(tmp, s.path)
        if s.rec is not None:
            s.rec.shot_recipes.append(recipe)        # bots may replay it in later matches;
            s.rec.shot_done.add(len(s.rec.shot_recipes) - 1)   # this match the player just did it
        dmg = recipe["damage"]
        s.send("SHOTS SAVED", (f"damage {dmg['drop']:g} measured" if dmg else f"{len(s.shots)} shots (no damage reading)")
               + "; bots deal 2x that")
        print(f"shots recorded: {len(s.shots)} at {recipe['target']} from {recipe['stand']}, {len(changed)} objects changed",
              flush=True)

    def watch(s, now):
        """Every tick, recording or not: has anyone (a bot, the player, another player) done a recorded
        shot this match? With a damage reading: its field dropped by the player's amount since the
        match began. Without: bullets from anyone ended on its target as often as the player's did."""
        rec = s.rec
        if rec is None or not rec.shot_recipes or not hasattr(s.live, "objects"):
            return
        proj = s.objects({5})
        if not hasattr(s, "seen_proj"):
            s.seen_proj = {}
            rec.watching_hits = True
        for h, (t, p) in proj.items():
            s.seen_proj[h] = p
        for h in [h for h in s.seen_proj if h not in proj]:
            p = s.seen_proj.pop(h)                   # gone: it hit something here
            for k, r in enumerate(rec.shot_recipes):
                if math.dist(p, r["target"]) < 0.8:
                    rec.shot_hits[k] = rec.shot_hits.get(k, 0) + 1
        if now < getattr(s, "next_check", 0.0):
            return
        s.next_check = now + 1.0
        for k, r in enumerate(rec.shot_recipes):
            if k in rec.shot_done:
                continue
            dmg = r.get("damage")
            if dmg:
                cur = s.read_field(dmg["type"], dmg["pos"], dmg["offset"])
                if cur is None:
                    continue
                base = rec.shot_base.setdefault(k, cur)
                done = base - cur >= dmg["drop"]
            else:
                done = rec.shot_hits.get(k, 0) >= hits_needed(r) and k not in rec.shot_claims
            if done:
                rec.shot_done.add(k)
                print(f"{now:6.1f}s recorded shot {k + 1} done this match: nobody shoots it again", flush=True)

    def finish_tracks(s, alive):
        for h in [h for h in s.track if h not in alive]:
            q = s.track.pop(h)
            s.shots.append(dict(stand=q["stand"], aim=q["aim"], impact=r2(q["last"])))

    @staticmethod
    def on_aim_line(p, pos, aim, eye=0.6):
        """Is p on the player's aim line (within 1.5 units, 0..100 ahead of his eye)? A bullet first
        seen there is his: H2A bullets fly far past 2.5 units in one tick (the player: 'nothing seen
        even though I fired' with the old 2.5-unit-from-him rule)."""
        n = math.sqrt(sum(v * v for v in aim))
        if n < 1e-6:
            return math.dist(p, pos) < 2.5
        ux, uy, uz = (v / n for v in aim)
        dx, dy, dz = p[0] - pos[0], p[1] - pos[1], p[2] - (pos[2] + eye)
        along = dx * ux + dy * uy + dz * uz
        if not -1.0 <= along <= 100.0:
            return False
        return math.sqrt(max(0.0, dx * dx + dy * dy + dz * dz - along * along)) < 1.5

    def update(s, now, person):
        if s.state != "rec" or not person or not person.get("pos"):
            return
        proj = s.objects({5})
        aim = person.get("aim") or (0, 0, 0)
        for h, (t, p) in proj.items():
            if h in s.track:
                s.track[h]["last"] = p
            elif h not in s.ignored:
                s.seen += 1
                s.first_d.append(round(math.dist(p, person["pos"]), 1))
                if s.on_aim_line(p, person["pos"], aim):
                    s.track[h] = dict(stand=r2(person["pos"]), aim=[round(v, 4) for v in aim], last=p)
                else:
                    s.ignored.add(h)                     # someone else's (or a grenade off the line)
        s.finish_tracks(set(proj))


def nav_learn(T, map_name, links):
    """Give the nav every usable link now (people's new jumps and routes, during the run) and
    the places they make reachable (goals snap to reachable floor)."""
    from brain.maps import get_map, usable_links
    from brain.core import Vec
    use = usable_links(links)
    oob = getattr(T, "oob", None)
    if oob is not None:                              # not a jump or ride that lands in a kill zone (Zealot's lift rides
        use = [l for l in use if not (l.get("land") and T.inside(l["land"][0], l["land"][1])   # onto the soft kill
                                      and oob[T._node(Vec(*l["land"][:3]))])]                    # walkway: bots died there)
    T.add_human_links(use)
    m = get_map(map_name)
    T.set_spawns([p for mode in m["spawns"].values() for team in mode.values() for p in team])


def on_events(rec, track_events, who, kind, roomba=None):
    """Apply one player's tracker events to the recorder (and to a Roomba trying a link)."""
    for ev, x in track_events:
        if ev in ("ground", "crouch"):
            with rec.lock:
                rec.mark(x, KIND_CROUCH if ev == "crouch" else kind)
                rec.spread(x)
        elif ev == "crawl":
            link = rec.crawled(x, who)
            if roomba is not None:
                roomba.crawled(x, link, rec)
        elif ev == "land":
            link = rec.landed(x, who)
            if roomba is not None:
                roomba.landed(x, link, rec)


class Roomba:
    """A mapping bot. With level data it walks the nav to the nearest unexplored floor it can get to
    (frontier), away from the other Roombas' goals; the nav knows, during the run, every jump and
    route people recorded and the spots bots fell from or bumped into. It keeps off deadly drops,
    marks walls it bumps into, picks up weapons it comes across, and takes a recorded jump or
    route only when it is the way to the place it wants to go."""

    def __init__(s, index, rng):
        s.index, s.rng = index, rng
        s.track = Track()
        s.target, s.target_t = None, 0.0      # (x, y, z)
        s.last = None
        s.stuck_t, s.wiggle_until, s.wiggle = 0.0, 0.0, (0.0, 0.0)
        s.win, s.walls, s.blocked = None, 0, None   # headway window (t, pos); walls met in a row; (heading, until)
        s.next_jump = rng.uniform(3, 8)
        s.trial, s.phase, s.trial_t, s.trial_s = None, None, 0.0, 30.0
        s.next_way, s.way_wp, s.straight = 0.0, None, False   # straight: a probe goal, no nav
        s.weapon, s.tried = None, {}          # the weapon going for: (handle, name, pos, until); handle -> retry time
        s.bump, s.pushed, s.heading = None, False, 0.0   # a push that stopped: (time, pos, heading)
        s.skip_links = {}                     # (take-off x, y, landing x, y) -> until: a jump this bot gave up on

    # --- safety: the spots bots fell from, and the level data's deadly drops (not where people walk)
    def deadly(s, x, y, z, rec, T, frm=None):
        if rec.near_fall(x, y, z, frm=frm):
            return True
        if rec.walked(x, y, z):
            return False
        return T is not None and not T.ground_ok(x, y, z, drop=4.0)

    def walk_off_kills(s, pos, mx, my, rec, T):
        """Does the next step leave the floor (an edge) into a fall this game's physics says kills?
        Running off an edge carries on: the floor straight below the edge is not where you land."""
        n = math.hypot(mx, my)
        if T is None or rec.phys is None or n < 0.1:
            return False
        import jumpphys
        out, _ = jumpphys.walk_step(T, list(pos), pos[0] + mx / n * 0.3, pos[1] + my / n * 0.3)
        if out != "off":
            return False
        ph = rec.phys
        out, _, _, _, impact = jumpphys.fly(T, ph, pos, mx / n * ph.run, my / n * ph.run, vz=0.0, dt=1.0 / HZ)
        return out != "land" or impact >= ph.lethal_v

    def line_ok(s, pos, x, y, rec, T):
        """Floor all along a straight walk (every 0.5 units), up or down a few units."""
        d = math.dist(pos[:2], (x, y))
        n = max(1, int(d / 0.5))
        for k in range(1, n + 1):
            px, py = pos[0] + (x - pos[0]) * k / n, pos[1] + (y - pos[1]) * k / n
            if T is not None and not T.ground_ok(px, py, pos[2] + 3.0, drop=7.0):
                return False
            if rec.near_fall(px, py, pos[2], 0.6):
                return False
        return True

    def pick(s, now, pos, rec, T, bounds):
        """A new goal: with level data the frontier, or now and then (PROBE_P) a probe; without
        (or nothing left to explore) the best of 24 random points 6-24 units away (unexplored,
        reachable in a straight line, near). A bot standing in a kill or soft kill zone first walks out of it."""
        best, s.straight, s.escaping = None, False, False
        out = s.escape(pos, T, getattr(getattr(rec, "director", None), "_safe", None))
        if out is not None:
            s.escaping = True                          # (live Zealot: rides landed bots on the soft kill walkway, where
            s.target, s.target_t, s.next_way = out, now, 0.0   # the frontier, kept off kill-zone floor, found nothing
            rec.targets[s.index] = out                # and the wander walked them along it to die, 13 in 5 min)
            return
        if T is not None and rec.shot_recipes and s.rng.random() < SHOT_P:
            go = s.shot_trial(pos, rec, T)
            if go is not None:                       # a recorded shot (F7): stand there, shoot that
                s.trial, s.phase, s.trial_t, s.crawl_path, s.trial_s = go, "go", now, None, 60.0
                s.target, s.target_t, s.next_way = tuple(go["take_off"]), now, 0.0
                rec.targets[s.index] = s.target
                return
        roll = s.rng.random()
        kinds = ("launcher", "lift") if roll < RIDE_P else ("control",) if roll < RIDE_P + USE_P and rec.pickup_ok else ()
        if T is not None and kinds:
            go = s.interactable(pos, rec, T, kinds)
            if go is not None:                       # ride it / press it: interact_steer
                s.trial, s.phase, s.trial_t, s.crawl_path, s.trial_s = go, "go", now, None, 40.0
                s.target, s.target_t, s.next_way = tuple(go["take_off"]), now, 0.0
                rec.targets[s.index] = s.target
                return
        if T is not None and rec.phys is not None and s.rng.random() < POCKET_P:
            call = s.pocket(pos, rec, T)
            if call is not None:                     # a called jump: the trial walks there and jumps
                s.trial, s.phase, s.trial_t, s.crawl_path, s.trial_s = call, "go", now, None, 30.0
                s.target, s.target_t, s.next_way = tuple(call["land"]), now, 0.0
                rec.targets[s.index] = s.target
                return
        if T is not None and s.rng.random() < PROBE_P:
            best = s.probe(pos, rec, T)
            s.straight = best is not None
        d = getattr(rec, "director", None)           # the LiDAR director's job for this bot (tools/lidar_director.py)
        job = d.job(s.index, pos) if d is not None and T is not None and best is None else None
        if job and job[0] == "call" and rec.phys is not None:
            call = s.pocket(pos, rec, T, aim=job[1])   # at the take-off side of an island: call the jump onto it
            if call is not None:
                s.trial, s.phase, s.trial_t, s.crawl_path, s.trial_s = call, "go", now, None, 30.0
                s.target, s.target_t, s.next_way = tuple(call["land"]), now, 0.0
                rec.targets[s.index] = s.target
                return
        elif job:
            best = job[1]                            # a spot or an objective (or an island's take-off side)
        if T is not None and best is None and now >= getattr(s, "no_frontier_until", 0.0):
            best = s.frontier(pos, rec, T)
            s.dry = 0 if best is not None else getattr(s, "dry", 0) + 1
            if best is None and d is not None and s.dry >= 2:   # all painted within reach twice, a 10 s wander
                best = d.fallback(s.index, pos)      # between: the director's patch farther off (at the first time
                # it walked off at once: the wander paints floor its frontier skips, Tower / Snowbound lost 5-8%)
            if best is None:                         # nothing: wander a while before searching again
                s.no_frontier_until = now + 10.0
        best_v = -1e9
        from brain.core import Vec
        for _ in range(0 if best else 24):
            a, r = s.rng.uniform(-math.pi, math.pi), s.rng.uniform(6, 24)
            x, y = pos[0] + math.cos(a) * r, pos[1] + math.sin(a) * r
            if bounds and not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
                continue
            if s.blocked and now < s.blocked[1] and math.cos(a - s.blocked[0]) > 0.5:
                continue                             # the way it just met a wall (above)
            if not s.line_ok(pos, x, y, rec, T) or (T is not None and T.out_of_bounds(Vec(x, y, pos[2]))):
                continue
            v = (0.0 if rec.explored(x, y, pos[2]) else 10.0) - r * 0.15 + s.rng.uniform(0, 2)
            if v > best_v:
                best, best_v = (x, y, pos[2]), v
        s.target = best or (pos[0] + s.rng.uniform(-6, 6), pos[1] + s.rng.uniform(-6, 6), pos[2])
        s.target_t, s.next_way = now, 0.0
        rec.targets[s.index] = s.target

    def escape(s, pos, T, safe=None):
        """The nearest floor out of the kill zones (Terrain.oob) when the bot stands in one, by walking (40 u of path at
        most), on the floor the spawns reach without crossing a kill zone when known (safe: the director's; out to the
        floor behind the zone, Zealot's walkway led on to the decks and the bots died at its far lip); None when it does
        not stand in one (or no way out is near)."""
        if T is None or getattr(T, "oob", None) is None:
            return None
        from brain.core import Vec
        if not T.out_of_bounds(Vec(*pos)):
            return None
        import numpy as np
        from scipy.sparse.csgraph import dijkstra
        l, j, i = T._node(Vec(*pos))
        d = dijkstra(getattr(T, "graph_h", T.graph), directed=True, indices=(l * T.nh + j) * T.nw + i, limit=40.0)
        ok = np.isfinite(d) & ~T.oob.ravel() & T.lwalk.ravel()
        if safe is not None and safe.shape == T.lwalk.shape and (ok & safe.ravel()).any():
            ok &= safe.ravel()
        if not ok.any():
            return None
        n = int(np.argmin(np.where(ok, d, np.inf)))
        c = T._center(*np.unravel_index(n, T.lwalk.shape))
        return (c.x, c.y, c.z)

    def frontier(s, pos, rec, T):
        """The nearest (by path) floor nobody has painted that this bot can get to, over the
        level data plus every jump and route people recorded (graph_h), not within 8 units of
        another Roomba's goal and not where a bot fell. Searched out to 40, then 150 units of
        path, then everywhere. None if the reachable map is all painted."""
        import numpy as np
        from scipy.sparse.csgraph import dijkstra
        from brain.core import Vec
        from brain.terrain import NAV_CELL
        l, j, i = T._node(Vec(*pos))
        director = getattr(rec, "director", None)
        # the nav graph with no step onto kill-zone floor (the director's): graph_h's paths cross soft kill zones (their
        # barrier cost is on the reversed graphs only), so live Zealot's bots went for the unpainted decks behind one
        # and 48 died on its walkway
        g = getattr(director, "safe_graph", None)
        g = g if g is not None and g.shape == getattr(T, "graph_h", T.graph).shape else getattr(T, "graph_h", T.graph)
        others = [t for k, t in rec.targets.items() if k != s.index]
        pick = np.random.default_rng(s.rng.randrange(1 << 30))
        extra = getattr(director, "open_nodes", None)    # the director's open patches: every one of their nodes
        for limit in (40.0, 150.0):                  # (none within 150 of path: wander, search again later)
            d = dijkstra(g, directed=True, indices=(l * T.nh + j) * T.nw + i, limit=limit)
            cand = np.nonzero(np.isfinite(d) & (d > 3.0))[0]
            if len(cand) > 2500:                     # ponytail: a sample, not every node; plenty to find a gap
                cand = cand[pick.choice(len(cand), 2500, replace=False)]
            if extra is not None and len(extra):     # (a sample misses small patches: those are why patches stayed)
                cand = np.union1d(cand, extra[np.isfinite(d[extra]) & (d[extra] > 3.0)])
            ll, rest = np.divmod(cand, T.nh * T.nw)
            jj, ii = np.divmod(rest, T.nw)
            xs, ys, zs = T.x0 + (ii + 0.5) * NAV_CELL, T.y0 + (jj + 0.5) * NAV_CELL, T.lz[ll, jj, ii]
            ok = ~rec.explored_many(xs, ys, zs)
            for tx, ty, _ in others:
                ok &= np.hypot(xs - tx, ys - ty) >= 8.0
            score = -d[cand] + pick.uniform(0, 6, len(cand))
            if director is not None:                 # the LiDAR director's patch for this bot, preferred
                score = score + director.region_bias(s.index, ll, jj, ii)
            for n in np.nonzero(ok)[0][np.argsort(-score[ok])][:20]:
                x, y, z = float(xs[n]), float(ys[n]), float(zs[n])
                if not rec.near_fall(x, y, z):
                    return (x, y, z)
        return None

    def interactable(s, pos, rec, T, kinds):
        """The nearest (by walking) map feature of these kinds (tools/map_features.py) not tried out
        yet: a man cannon or lift nobody has ridden (no ride link from it, under RIDE_TRIES tries), or
        a switch nobody pressed. Returns its trial or None."""
        import numpy as np
        from scipy.sparse.csgraph import dijkstra
        from brain.core import Vec
        l, j, i = T._node(Vec(*pos))
        d = dijkstra(T.graph, directed=True, indices=(l * T.nh + j) * T.nw + i, limit=POCKET_LIMIT).reshape(T.L, T.nh, T.nw)
        best = None
        for f in rec.features:
            if f["kind"] not in kinds:
                continue
            key = (f["kind"], round(f["pos"][0], 1), round(f["pos"][1], 1))
            if rec.feat_tries.get(key, 0) >= (RIDE_TRIES if f["kind"] != "control" else 1):
                continue
            if f["kind"] != "control" and any(l.get("ride") and math.dist(l["take_off"][:2], f["pos"][:2]) < 1.5 for l in rec.links):
                continue                             # ridden already: the nav knows where it throws you
            n = T._node(Vec(*f["pos"]))
            cost = d[n]
            if np.isfinite(cost) and abs(T.lz[n] - f["pos"][2]) < 1.5 and (best is None or cost < best[0]):
                best = (cost, f, key)
        if best is None:
            return None
        _, f, key = best
        kind = "use" if f["kind"] == "control" else "ride"
        return dict(kind=kind, name=f["name"], take_off=r2(f["pos"]), land=r2(f["pos"]), runup=None,
                    human=0, bot_ok=0, bot_fail=0, _feat=key)

    def interact_steer(s, now, pos, rec, T, l):
        """A ride or a switch: walk there by the nav; a switch: press Use on it for 2 s; a man cannon
        or lift: step onto its middle and let it throw you (hands off in the air; landed() makes the
        landing a link). 6 s on it without a throw: not one a walking bot can ride."""
        to = l["take_off"]
        yaw = math.atan2(to[1] - pos[1], to[0] - pos[0])
        if s.phase == "go":
            from brain.core import Vec
            if not math.isfinite(T._field(Vec(*to))[T._node(Vec(*pos))]):
                s.tried_feat(l, rec)
                return None
            if math.dist(pos[:2], to[:2]) < 0.5:
                s.phase, s.on_t = "on", now
            w = T.nav(Vec(*pos), Vec(*to))
            return 1.0, 0.0, math.atan2(w.y - pos[1], w.x - pos[0]), 0
        if s.phase == "on":
            close = math.dist(pos[:2], to[:2]) < 0.15
            if l["kind"] == "use":
                if now - s.on_t > 2.0:
                    s.tried_feat(l, rec)
                    return None
                return (0.0 if close else 0.3), 0.0, yaw, BTN_ACTION if int(now * 10) % 2 == 0 else 0
            if s.track.air or pos[2] > to[2] + 1.0:  # thrown
                s.phase, s.fly_t = "fly", now
            elif now - s.on_t > 6.0:
                s.tried_feat(l, rec)
                return None
            return (0.0 if close else 0.6), 0.0, yaw, 0
        if now - s.fly_t > 12.0 + CONFIRM_S:        # never came down alive
            s.tried_feat(l, rec)
            return None
        st = l.get("steer")                          # a map ride (tools/lidar_rides.py): drift out the way it lands
        if st and (s.track.air or pos[2] > l["take_off"][2] + 1.0):   # (a lift's steady climb reads as ground to the
            return 1.0, 0.0, math.atan2(st[1], st[0]), 0             # tracker: live Zealot's bots rose straight up, no drift)
        return 0.0, 0.0, yaw, 0

    def shot_trial(s, pos, rec, T):
        """The first recorded shot (F7) nobody replayed this match that this bot can walk to: a trial
        with the player's stand point, his impact point and his eye height over his position (from
        his own shots: impact height minus the drop along his aim, so it holds in every game)."""
        from brain.core import Vec
        here = T._node(Vec(*pos))
        for k, r in enumerate(rec.shot_recipes):
            key = ("shoot", k, 0)
            claim = rec.shot_claims.get(k)                 # (bot, time): a claim lapses after 90 s (a bot that died)
            if k in rec.shot_done or (claim is not None and claim[0] != s.index and time.time() - claim[1] < 90.0):
                continue                             # done this match, or another bot is on it
            if not math.isfinite(T._field(Vec(*r["stand"]))[here]):
                continue
            eyes = []
            for q in r.get("shots", []):
                (sx, sy, sz), (ix, iy, iz), (ax, ay, az) = q["stand"], q["impact"], q["aim"]
                h = math.hypot(ix - sx, iy - sy)
                if h > 0.5 and math.hypot(ax, ay) > 1e-3:
                    eyes.append(iz - sz - az / math.hypot(ax, ay) * h)
            eye = min(1.0, max(0.0, sorted(eyes)[len(eyes) // 2])) if eyes else 0.6
            rec.shot_claims[k] = (s.index, time.time())   # mine: the others leave it alone
            return dict(kind="shoot", name=f"recorded shot {k + 1}", take_off=r["stand"], land=r["target"],
                        target=r["target"], eye=eye, damage=r.get("damage"), k=k, hits=hits_needed(r),
                        seconds=min(15.0, max(3.0, 2.0 * float(r.get("seconds", 4.0)))),   # no reading: 2x his time
                        runup=None, human=0, bot_ok=0, bot_fail=0, _feat=key)
        return None

    def shoot_steer(s, now, pos, rec, T, l):
        """A recorded shot: walk to where the player stood (by the nav), then aim at where his shots
        landed and fire in bursts as long as he did. Returns (fwd, strafe, yaw, buttons, pitch)."""
        from brain.core import Vec
        to, tg = l["take_off"], l["target"]
        if s.phase == "go":
            if not math.isfinite(T._field(Vec(*to))[T._node(Vec(*pos))]):
                s.tried_feat(l, rec)
                return None
            if math.dist(pos[:2], to[:2]) < 0.4:
                s.phase, s.on_t = "on", now
            w = T.nav(Vec(*pos), Vec(*to))
            return 1.0, 0.0, math.atan2(w.y - pos[1], w.x - pos[0]), 0
        k = l.get("k")
        if k in rec.shot_done:                       # someone else did it meanwhile: nothing left to shoot
            print(f"{now:6.1f}s bot {s.index} left {l['name']}: already done", flush=True)
            s.tried_feat(l, rec)
            return None
        # fire until it has dealt twice the player's damage (the device's own damage field; the player:
        # match the damage, not his SMG spray with a battle rifle); without a reading, until twice his
        # hits landed on it (anyone's bullets ending there, ShotRec.watch), else for 2x his firing time
        dmg, read = l.get("damage"), getattr(rec, "damage_reader", None)
        base = None
        if getattr(s, "dmg_trial", None) is not l:
            s.dmg_trial, s.dmg_t, s.dmg_dealt, s.hits0 = l, now, 0.0, rec.shot_hits.get(k, 0)
            s.dmg_base = read(dmg["type"], dmg["pos"], dmg["offset"]) if dmg and read else None
        if dmg and read:
            base = s.dmg_base
            if base is not None and now - s.dmg_t >= 0.25:
                s.dmg_t = now
                cur = read(dmg["type"], dmg["pos"], dmg["offset"])
                s.dmg_dealt = base - cur if cur is not None else s.dmg_dealt
                if s.dmg_dealt >= 2.0 * dmg["drop"]:
                    print(f"{now:6.1f}s bot {s.index} replayed {l['name']}: dealt {s.dmg_dealt:g} "
                          f"(2x the person's {dmg['drop']:g})", flush=True)
                    rec.shot_done.add(k)
                    s.tried_feat(l, rec)
                    return None
        hits = rec.shot_hits.get(k, 0) - s.hits0
        if base is None and hits >= 2 * l.get("hits", 1) and getattr(rec, "watching_hits", False):
            print(f"{now:6.1f}s bot {s.index} replayed {l['name']}: {hits} hits (2x the person's {l.get('hits', 1)})", flush=True)
            rec.shot_done.add(k)
            s.tried_feat(l, rec)
            return None
        if now - s.on_t > (20.0 if base is not None else l["seconds"]):
            enough = (s.dmg_dealt >= dmg["drop"]) if base is not None else (hits >= l.get("hits", 1) or
                                                                             not getattr(rec, "watching_hits", False))
            if enough:                               # at least a skilled player's amount: it is open
                rec.shot_done.add(k)
            print(f"{now:6.1f}s bot {s.index} replayed {l['name']}"
                  + (f": dealt {s.dmg_dealt:g} of {2 * dmg['drop']:g} in 20 s" if base is not None else f" ({hits} hits, by time)")
                  + ("" if enough else ": not enough, another bot may try"), flush=True)
            s.tried_feat(l, rec)
            return None
        dx, dy, dz = tg[0] - pos[0], tg[1] - pos[1], tg[2] - (pos[2] + l["eye"])
        fire = BTN_FIRE if int(now * 10) % 4 < 2 else 0     # pull and release (burst weapons)
        return 0.0, 0.0, math.atan2(dy, dx), fire, math.atan2(dz, math.hypot(dx, dy))

    def tried_feat(s, l, rec):
        with rec.lock:
            rec.feat_tries[l["_feat"]] = rec.feat_tries.get(l["_feat"], 0) + 1
            if l.get("kind") == "shoot" and (rec.shot_claims.get(l.get("k")) or (None,))[0] == s.index:
                rec.shot_claims.pop(l["k"], None)    # done (shot_done) or failed: free for another bot
        s.trial = None

    def pocket(s, pos, rec, T, aim=None):
        """Call a jump: the nearest floors this bot cannot walk to (within 25 units; nearest the director's aim, an
        island's floor, when given), a take-off on
        floor it can, with room to run up, and a full-speed jump whose arc (jumpphys.fly over the
        level data, this game's run, jump and gravity) comes down on that floor, alive: the call
        is that landing spot. It counts only landing within CALL_XY / CALL_Z of the call and alive
        5 s (landed); then it is a link every bot may use. A call missed twice is not made again
        (by any bot). Returns the trial (a link-shaped dict, called=True) or None."""
        import numpy as np
        from scipy.sparse.csgraph import dijkstra
        from brain.core import Vec
        from brain.terrain import MAX_DROP, NAV_CELL
        import jumpphys
        ph = rec.phys
        jumpphys.prepare(T)
        l, j, i = T._node(Vec(*pos))                 # within 120 of path: big maps (Mombasa: 3 million nodes) stay quick
        # walking only (and teleporters): the bot walks to the take-off; with people's jumps counted it
        # picked take-offs it could not walk to and pushed into a wall for 30 s (Battle Creek)
        d = dijkstra(T.graph, directed=True, indices=(l * T.nh + j) * T.nw + i, limit=POCKET_LIMIT)
        can = np.isfinite(d).reshape(T.L, T.nh, T.nw)
        r = 100                                      # 25 units of quarter-unit cells
        j0, j1, i0, i1 = max(0, j - r), min(T.nh, j + r + 1), max(0, i - r), min(T.nw, i + r + 1)
        ls, js, is_ = np.nonzero(T.lwalk[:, j0:j1, i0:i1] & ~can[:, j0:j1, i0:i1])
        js, is_ = js + j0, is_ + i0
        far = int(math.ceil(float(jumpphys.reach(ph, -MAX_DROP)) / NAV_CELL)) + 1
        seen = []
        tj, ti = T._cell(Vec(*aim)) if aim is not None else (j, i)
        for k in np.argsort((js - tj) ** 2 + (is_ - ti) ** 2):
            want = T._center(int(ls[k]), int(js[k]), int(is_[k]))
            if any(abs(want.x - a) < 1.5 and abs(want.y - b) < 1.5 for a, b in seen) or rec.near_fall(want.x, want.y, want.z):
                continue
            seen.append((want.x, want.y))
            if len(seen) > 20:
                break
            wj0, wj1 = max(0, int(js[k]) - far), min(T.nh, int(js[k]) + far + 1)
            wi0, wi1 = max(0, int(is_[k]) - far), min(T.nw, int(is_[k]) + far + 1)
            al, aj, ai = np.nonzero(can[:, wj0:wj1, wi0:wi1] & T.lwalk[:, wj0:wj1, wi0:wi1])
            aj, ai = aj + wj0, ai + wi0
            ax, ay, az = T.x0 + (ai + 0.5) * NAV_CELL, T.y0 + (aj + 0.5) * NAV_CELL, T.lz[al, aj, ai]
            dist, dz = np.hypot(want.x - ax, want.y - ay), want.z - az
            tuck = CROUCH_TUCK.get(getattr(ph, "game", None), 0.0)
            cands = []                               # plain jumps first, then crouch-jumps (feet tucked at the apex)
            for tk in ((0.0, tuck) if tuck else (0.0,)):
                with np.errstate(invalid="ignore"):
                    miss = np.abs(dist - jumpphys.reach(ph, dz - tk))   # a full-speed jump comes down about here
                    ok = (dist >= 0.5) & (dz - tk <= ph.apex * 0.9) & (dz >= -MAX_DROP) & (miss < 0.75)
                    if tk:
                        ok &= dz > ph.apex * 0.9 - 0.05  # (only where a plain jump falls short)
                cands += [(n, tk) for n in np.nonzero(ok)[0][np.argsort(miss[ok])][:8 if not tk else 3]]
            for n, tk in cands:
                a = (float(ax[n]), float(ay[n]), float(az[n]))
                ux, uy = (want.x - a[0]) / dist[n], (want.y - a[1]) / dist[n]
                run = Vec(a[0] - ux * 0.8, a[1] - uy * 0.8, a[2])
                rl, rj, ri = T._node(run)
                if not (can[rl, rj, ri] and abs(T.lz[rl, rj, ri] - a[2]) < 0.3):
                    continue                         # no room to run up
                if rec.near_fall(a[0], a[1], a[2], 1.2) or rec.near_fall(run.x, run.y, a[2], 1.2):
                    continue                         # a take-off where bots fell: the walk there is refused (deadly),
                    #                                  so the call was dropped at once and counted missed (Construct
                    #                                  live 0 of 155: 47 of 49 replayed misses were these)
                oob = getattr(T, "oob", None)
                if oob is not None and (oob[T._node(Vec(*a))] or oob[T._node(run)]):
                    continue                         # (a take-off in a kill zone)
                out, p, top, t, impact = fly_tuck(T, ph, a, ux * ph.run, uy * ph.run, tk, dt=1.0 / HZ)
                if out != "land" or impact >= ph.lethal_v:
                    continue
                pl, pj, pi = T._node(Vec(*p))
                if can[pl, pj, pi] and abs(T.lz[pl, pj, pi] - p[2]) < 0.3:
                    continue                         # came down on floor it can walk to: no new way
                key = (round(a[0] * 2), round(a[1] * 2), round(p[0] * 2), round(p[1] * 2))
                if rec.failed_calls.get(key, 0) >= 2 or rec.find_link(a, p) or rec.near_fall(p[0], p[1], p[2]):
                    continue
                if oob is not None and oob[T._node(Vec(*p))]:
                    continue                         # (it lands in a kill zone)
                if not all(self_safe(T, ph, a, ux, uy, back, turn) for back, turn in ((0.15, 0.0), (0.0, 0.05), (0.0, -0.05))):
                    continue                         # a slightly early or crooked try would kill it: not a call it makes
                if tk and not all(_lands_near(fly_tuck(T, ph, a, (ux * c - uy * sn) * ph.run * f, (ux * sn + uy * c) * ph.run * f,
                                                       tk, dt=1.0 / HZ), p)
                                  for f, c, sn in ((0.96, 1.0, 0.0), (1.0, math.cos(0.035), math.sin(0.035)),
                                                   (1.0, math.cos(0.035), -math.sin(0.035)))):
                    continue                         # a crouch-jump is a ledge at the edge of reach: only one a 4% slow or
                    #                                  2 degree crooked take-off still lands (the simulator missed 2 in 3)
                mid = (a[0] + (p[0] - a[0]) / 2, a[1] + (p[1] - a[1]) / 2, top)
                return dict(kind="jump", take_off=r2(a), land=r2(p), runup=r2((run.x, run.y, a[2])), apex=round(top, 2),
                            air_s=round(t, 2), path=[r2(a), r2(mid), r2(p)], called=True, found_by=rec.found_as,
                            human=0, bot_ok=0, bot_fail=0, t=round(time.time()), _key=key, **({"crouch": 1} if tk else {}))
        return None

    def probe(s, pos, rec, T):
        """Unpainted floor the level data has within 20 units that its nav cannot get to from here
        (Battle Creek's upper floors and roofs: steps the nav's 0.18 step limit refuses, people
        walk and hop up): the nearest, walked at straight (the bump, jump and sidestep when stuck
        do the climbing). A climb two bots land becomes a link the nav uses for everyone."""
        import numpy as np
        from scipy.sparse.csgraph import dijkstra
        from brain.core import Vec
        l, j, i = T._node(Vec(*pos))
        d = dijkstra(getattr(T, "graph_h", T.graph), directed=True, indices=(l * T.nh + j) * T.nw + i)
        d = d.reshape(T.L, T.nh, T.nw)
        r = 80                                      # 20 units of quarter-unit cells
        j0, j1, i0, i1 = max(0, j - r), min(T.nh, j + r + 1), max(0, i - r), min(T.nw, i + r + 1)
        ls, js, is_ = np.nonzero(T.lwalk[:, j0:j1, i0:i1] & ~np.isfinite(d[:, j0:j1, i0:i1]))
        others = [t for k, t in rec.targets.items() if k != s.index]
        for k in np.argsort((js + j0 - j) ** 2 + (is_ + i0 - i) ** 2)[:600]:
            c = T._center(int(ls[k]), int(js[k] + j0), int(is_[k] + i0))
            if abs(c.z - pos[2]) < 3.0 and math.dist((c.x, c.y), pos[:2]) >= 2.0 and not rec.explored(c.x, c.y, c.z) \
                    and not rec.near_fall(c.x, c.y, c.z) \
                    and not any(math.dist((c.x, c.y), t[:2]) < 8.0 for t in others):
                return (c.x, c.y, c.z)
        return None

    def way_in(s, now, pos, rec, T):
        """The nav's next point toward our goal, 4 times a second (None without level data). If
        it is a recorded jump or route starting here (the nav's best way to the goal, never a
        detour), take it as a trial: landing where it lands (or reaching the route's end) and
        staying alive 5 s confirms it. A probe walks straight: None."""
        if T is None or s.target is None or s.straight:
            return None
        if now < s.next_way:
            return s.way_wp
        s.next_way = now + 0.25
        from brain.core import Vec
        w = T.nav(Vec(*pos), Vec(*s.target), human=True)
        s.way_wp, l = (w.x, w.y, w.z), None
        if hasattr(w, "sx"):
            l = rec.find_link((w.sx, w.sy, pos[2]), (w.x, w.y, w.z)) or \
                next((l for l in rec.links if math.dist(l["take_off"][:2], (w.sx, w.sy)) < MERGE
                      and math.dist(l["land"][:2], (w.x, w.y)) < MERGE), None)
            if l is None:                          # a two-way jump, taken back the other way
                back = next((l for l in rec.links if math.dist(l["land"][:2], (w.sx, w.sy)) < MERGE
                             and math.dist(l["take_off"][:2], (w.x, w.y)) < MERGE), None)
                if back is not None:
                    from brain.terrain import reverse_jump
                    l = dict(back, _of=back, **reverse_jump(back))   # (landed() credits back)
        elif hasattr(w, "path"):
            a, b = w.path[0][:3], w.path[-1][:3]
            l = rec.find_link(a, b, "crouch") or rec.find_link(a, b, "route")
        if l is not None and now < s.skip_links.get((round(l["take_off"][0], 1), round(l["take_off"][1], 1),
                                                    round(l["land"][0], 1), round(l["land"][1], 1)), -1.0):
            l = None                                 # (given up on lately: walk on, the nav finds another way next time)
        if l is not None and l.get("ride"):          # a lift or man cannon on the way: step on, let it throw you
            to = l["take_off"]                       # (interact_steer; a map ride steers its way in the air)
            l = dict(l, kind="ride", _of=l, _feat=("ride", round(to[0], 1), round(to[1], 1)))
        if l is not None:
            s.trial, s.phase, s.trial_t, s.crawl_path = l, "go", now, None
            s.trial_s = 30.0 + 0.5 * len(l.get("path") or ()) + (l.get("air_s") or 0.0)   # a long route takes longer
        return s.way_wp

    def weapon_steer(s, now, pos, rec, T):
        """A weapon lying within WEAPON_REACH that we did not try lately: walk to it, press Use
        on it (a tap every other tick), give up after 12 s. Returns (fwd, yaw, buttons) or None."""
        if not rec.pickup_ok:                         # not in this game yet: no detour to stand on it
            return None
        if s.weapon is None:
            near = [g for g in rec.ground if s.tried.get(g[0], 0) < now and math.dist(g[2][:2], pos[:2]) < WEAPON_REACH
                    and abs(g[2][2] - pos[2]) < 1.5 and s.line_ok(pos, g[2][0], g[2][1], rec, T)]
            if not near:
                return None
            h, name, wpos = min(near, key=lambda g: math.dist(g[2], pos))
            s.weapon = (h, name, wpos, now + 12.0)
        h, name, wpos, until = s.weapon
        if now > until or not any(g[0] == h for g in rec.ground):     # taken, or could not get there
            s.tried[h], s.weapon = now + 60.0, None
            return None
        yaw = math.atan2(wpos[1] - pos[1], wpos[0] - pos[0])
        if math.dist(wpos[:2], pos[:2]) < 0.9:
            return 0.3, yaw, BTN_ACTION if int(now * 10) % 2 == 0 else 0
        return 1.0, yaw, 0

    def trial_steer(s, now, pos, rec, T):
        """Go to the run-up point (by the nav when there is level data), run to the take-off,
        jump, fly at the landing. Returns (fwd, strafe, yaw, buttons) or None when not trying."""
        l = s.trial
        if l is None:
            return None
        if now - s.trial_t > s.trial_s:            # could not get there: try something else
            if l.get("called") and l.get("kind", "jump") == "jump":
                s.score(l, False, rec, jumped=s.phase == "fly")
                s.why = f"call given up: {s.trial_s:.0f} s in phase {s.phase}"
            if "_feat" in l:
                s.tried_feat(l, rec)
            s.trial = None
            return None
        to, land = l["take_off"], l["land"]
        if l.get("kind") in ("crouch", "route"):
            return s.route_steer(now, pos, rec, T, l)
        if l.get("kind") == "shoot":
            return s.shoot_steer(now, pos, rec, T, l)
        if l.get("kind") in ("ride", "use"):
            return s.interact_steer(now, pos, rec, T, l)
        run = l["runup"] or [to[0] - (land[0] - to[0]) * 0.5, to[1] - (land[1] - to[1]) * 0.5, to[2]]
        if s.phase == "go":                        # by the nav (it goes straight when it can)
            goal = run
            if T is not None:
                from brain.core import Vec
                if not math.isfinite(T._field(Vec(*run))[T._node(Vec(*pos))]):
                    if l.get("called"):                 # no walking way to the run-up from here: drop it
                        s.score(l, False, rec, jumped=False)
                        s.why = "call dropped: no walking way to its run-up"
                    s.trial = None
                    return None
                w = T.nav(Vec(*pos), Vec(*run))
                goal = (w.x, w.y, w.z)
            if math.dist(pos[:2], run[:2]) < 0.35:
                s.phase = "run"
                if getattr(s, "runups_for", None) is not l:
                    s.runups_for, s.runups = l, 0
                s.runups += 1
                if s.runups > 3:                     # three run-ups and no jump: not one this bot makes from here
                    s.score(l, False, rec, jumped=False)
                    s.why = "jump given up: 3 run-ups"
                    s.skip_links[(round(to[0], 1), round(to[1], 1), round(land[0], 1), round(land[1], 1))] = now + 60.0
                    s.trial = None
                    return None
            return 1.0, 0.0, math.atan2(goal[1] - pos[1], goal[0] - pos[0]), 0
        if s.phase == "run":                       # jump on the spot: within a tick's travel, or passing it
            d = math.dist(pos[:2], to[:2])
            # past the take-off along the run-up line (run -> to), not along the jump: a jump that turns from its run-up
            # (a recorded Construct jump from (0.51, -3.84, 11.82): run-up north, landing south-east) read "passed" at the
            # run-up itself and the bot went run-up, run, run-up ... standing still, 290 bot-seconds live
            passed = (to[0] - pos[0]) * (to[0] - run[0]) + (to[1] - pos[1]) * (to[1] - run[1]) <= 0
            jump = d < 0.6 * (rec.phys.run if rec.phys else 2.25) / HZ or (d < 0.3 and passed)
            if passed and not jump:                  # ran past it off the line: run up again
                s.phase = "go"
                return 0.0, 0.0, math.atan2(to[1] - pos[1], to[0] - pos[0]), 0
            if jump:
                s.phase, s.fly_t = "fly", now
            aim = land if jump else to
            return 1.0, 0.0, math.atan2(aim[1] - pos[1], aim[0] - pos[0]), BTN_JUMP if jump else 0
        if now - s.fly_t > 4.0 + CONFIRM_S:         # never landed, or not confirmed: give up
            if l.get("called"):
                s.score(l, False, rec)
            s.trial = None
            return None
        yaw = math.atan2(land[1] - pos[1], land[0] - pos[0])
        if not l.get("called") and now - s.fly_t > 0.6 and not s.track.air:
            # a known jump taken on the way: down is done (scored on where it came down, no 5 s wait standing still: live
            # Construct's bots stood 350 of 639 still bot-seconds in such waits)
            s.score(l, math.dist(pos[:2], land[:2]) < 1.0 and abs(pos[2] - land[2]) < 0.6, rec)
            s.trial = None
            return None
        if now - s.fly_t > 0.6 and not s.track.air:  # down: stand still while the 5 s run out
            return 0.0, 0.0, yaw, 0
        if pos[2] <= land[2] + 0.05 or math.dist(pos[:2], land[:2]) < 0.3:
            return 0.0, 0.0, yaw, 0                  # down on it (the tracker lags): pushing on ran bots off ledges
        return 1.0, 0.0, yaw, (BTN_CROUCH if l.get("crouch") else 0)   # a crouch-jump: crouch held in the air

    def route_steer(s, now, pos, rec, T, l):
        """A crouch route (from its nearer end) or a recorded route (from its start): get there,
        follow its points (crouched where flagged, jumping at take-offs), then stay alive CONFIRM_S
        at the end. A crouch route is scored by the tracker (crawled()), a recorded route here."""
        from brain.terrain import route_points, ROUTE_JUMP, ROUTE_CROUCH
        if s.crawl_path is None:
            pts = route_points(l)
            if l.get("kind") == "crouch" and math.dist(pts[-1][:3], pos) < math.dist(pts[0][:3], pos):
                pts = pts[::-1]
            s.crawl_path = pts
        if s.phase == "go":
            start = s.crawl_path[0]
            goal = start
            if T is not None:
                from brain.core import Vec
                w = T.nav(Vec(*pos), Vec(*start[:3]))
                goal = (w.x, w.y, w.z)
            if math.dist(pos[:2], start[:2]) < 0.4:
                s.phase = "crawl"
            return 1.0, 0.0, math.atan2(goal[1] - pos[1], goal[0] - pos[0]), 0
        if s.phase == "crawl":
            jump = False
            while len(s.crawl_path) > 1 and math.dist(s.crawl_path[0][:2], pos[:2]) < 0.4:
                jump |= bool(s.crawl_path.pop(0)[3] & ROUTE_JUMP)    # a take-off: jump here
            q = s.crawl_path[0]
            if len(s.crawl_path) == 1 and math.dist(q[:2], pos[:2]) < 0.4:
                s.phase, s.fly_t = "wait", now
                return 0.0, 0.0, 0.0, 0                 # let go of crouch: the tracker closes a crouch route
            return (1.0, 0.0, math.atan2(q[1] - pos[1], q[0] - pos[0]),
                    (BTN_JUMP if jump else 0) | (BTN_CROUCH if q[3] & ROUTE_CROUCH else 0))
        if now - s.fly_t > CONFIRM_S + (2.0 if l.get("kind") == "crouch" else 0.0):
            if l.get("kind") == "route":               # alive at its end 5 s on: done it
                with rec.lock:
                    l[rec.ok_key] = l.get(rec.ok_key, 0) + 1
            s.trial = None
            return None
        return 0.0, 0.0, 0.0, 0

    def crawled(s, info, link, rec):
        """This Roomba finished a crouched walk and stayed alive 5 s: the route it was trying?"""
        l = s.trial
        if l is None or l.get("kind") != "crouch" or s.phase != "wait":
            return
        ok = min(math.dist(info["end"], l["land"]), math.dist(info["end"], l["take_off"])) < 1.0
        with rec.lock:
            if link is not l:
                k = rec.ok_key if ok else rec.fail_key
                l[k] = l.get(k, 0) + 1
        s.trial = None

    def landed(s, info, link, rec):
        """This Roomba landed and stayed alive 5 s, trying a jump: did it land where it meant to?
        A jump it called counts only on the call (CALL_XY, CALL_Z) and then becomes a link every
        bot may use; a person's jump within a unit of where he landed."""
        l = s.trial
        if l is None or s.phase != "fly":
            return
        if info.get("t0", 1e9) < getattr(s, "fly_t", 0.0) - 0.5:
            return                                   # an earlier hop's landing, confirmed only now: not this jump
        if l.get("kind") == "ride":
            s.rode(info, l, rec)
            return
        tol = (CALL_XY, CALL_Z) if l.get("called") else (1.0, 0.6)
        ok = math.dist(info["landing"][:2], l["land"][:2]) < tol[0] and abs(info["landing"][2] - l["land"][2]) < tol[1]
        s.score(l, ok, rec)
        s.trial = None

    def rode(s, info, l, rec):
        """Thrown by a man cannon or a lift and alive 5 s after landing: where it throws you is a
        one-way link (ride=True) every bot may use: walk onto it, let it throw you."""
        p0, p1 = l["take_off"], info["landing"]
        with rec.lock:
            rec.feat_tries[l["_feat"]] = rec.feat_tries.get(l["_feat"], 0) + 1
            if math.dist(p0[:2], p1[:2]) > 2.0 or abs(p1[2] - p0[2]) > 1.5:
                link = rec.find_link(p0, p1)
                if link is None:
                    trail = info["trail"]
                    link = dict(kind="jump", ride=True, name=l["name"], take_off=r2(p0), land=r2(p1), runup=r2(p0),
                                apex=round(info["apex"], 2), air_s=info["air_s"],
                                path=[r2(p0)] + [r2(q) for q in trail[::max(1, len(trail) // 16)]] + [r2(p1)],
                                found_by=rec.found_as, human=0, bot_ok=0, bot_fail=0, t=round(time.time()))
                    rec.links.append(link)
                link[rec.ok_key] = link.get(rec.ok_key, 0) + 1
        s.trial = None

    def score(s, l, ok, rec, jumped=True):
        """A tried jump's result: on the link (a two-way jump taken backwards: on its own link, and
        it was done back); a new called jump made becomes a link, one missed is remembered."""
        with rec.lock:
            new = "_key" in l and not any(x is l for x in rec.links)    # a fresh call (pocket()), not a known link
            if new:                                  # (a call given up before its jump: dropped, not missed)
                k = "made" if ok else "missed" if jumped else "dropped"
                rec.calls[k] = rec.calls.get(k, 0) + 1
                if not ok:
                    rec.failed_calls[l["_key"]] = rec.failed_calls.get(l["_key"], 0) + 1
                    return
                l.pop("_key", None)
                l[rec.ok_key] = 1
                rec.links.append(l)
                return
            src = l.get("_of", l)
            k = rec.ok_key if ok else rec.fail_key
            src[k] = src.get(k, 0) + 1
            if ok and "_of" in l:
                src["back"] = src.get("back", 0) + 1
            fails, oks = src.get(rec.fail_key, 0), src.get(rec.ok_key, 0)
            if not ok and src.get("crouch") and not src.get("human") and fails >= 3 and fails > 2 * oks:
                # a crouch-jump bots keep missing: out of the nav, never called again (live Construct: one landed once
                # then missed 54 times, bots queued on it and the floor behind it stayed at 91%; usable_links keeps any
                # link landed once)
                rec.links[:] = [x for x in rec.links if x is not src]
                to, la = src["take_off"], src["land"]
                rec.failed_calls[(round(to[0] * 2), round(to[1] * 2), round(la[0] * 2), round(la[1] * 2))] = 2

    def died(s, rec):
        if s.trial is not None and "_feat" in s.trial:
            s.tried_feat(s.trial, rec)
        elif s.trial is not None and s.phase in ("fly", "crawl", "wait"):
            if s.trial.get("kind", "jump") == "jump":
                s.score(s.trial, False, rec)
            else:
                with rec.lock:
                    s.trial[rec.fail_key] = s.trial.get(rec.fail_key, 0) + 1
        s.trial, s.target, s.bump = None, None, None

    def bumps(s, now, pos, moved, rec):
        """the player's wall rule, for bots: pushing forward, on the ground, nobody within 1 unit, and
        stopped for BUMP_S is a bump. If 1.5 s on the bot has not got up onto it (the jump and sidestep
        that follow lift it onto a lip, never onto a wall) it was a wall (Recorder.bumped)."""
        if s.bump is None:
            if s.pushed and not moved and s.stuck_t >= BUMP_S and not s.track.air and not any(
                    0.01 < math.dist(q, pos) and math.dist(q[:2], pos[:2]) < 1.0 for q in rec.players_pos):
                s.bump = (now, pos, s.heading)
            return
        t0, p0, a = s.bump
        if now - t0 >= 1.5 and not s.track.air:
            s.bump = None
            if pos[2] < p0[2] + 0.25:
                rec.bumped(p0, (math.cos(a), math.sin(a)))

    def think(s, now, pos, rec, T, bounds):
        s.why = ""                                   # (what decided this tick: the decision log, tools/lidar.py main)
        steer = s.trial_steer(now, pos, rec, T)
        if steer is not None:
            fwd, strafe, move, buttons = steer[:4]
            pitch = steer[4] if len(steer) > 4 else 0.0    # aiming trials (recorded shots) look up or down
            pad = s.trial.get("kind") == "ride" and math.dist(pos[:2], s.trial["take_off"][:2]) < 1.5
            if s.phase == "go" and fwd > 0.5 and not pad and \
                    (s.deadly(pos[0] + math.cos(move) * 0.3, pos[1] + math.sin(move) * 0.3, pos[2], rec, T, frm=pos)
                     or s.walk_off_kills(pos, math.cos(move), math.sin(move), rec, T)):
                # (stepping onto a lift or cannon pad is no deadly edge: its column has no floor and the guard dropped the
                # ride every tick, Aftship's bots piled up at the big lift, the simulator froze at 49%)
                if s.trial.get("called") and s.trial.get("kind", "jump") == "jump":
                    s.score(s.trial, False, rec, jumped=False)   # the way to the take-off runs off a deadly edge
                    s.why = "call dropped: " + ("fall spot" if rec.near_fall(pos[0] + math.cos(move) * 0.3,
                                                                            pos[1] + math.sin(move) * 0.3, pos[2], frm=pos)
                                                else "edge on the way")
                if "_feat" in s.trial:
                    s.tried_feat(s.trial, rec)       # (a ride whose way runs off an edge: counted, not recreated forever)
                s.trial = None
                s.last = pos
                return 0.0, 0.0, move, 0.0, 0
            stuck = fwd > 0.5 and s.phase in ("go", "run") and s.last is not None and math.dist(s.last[:2], pos[:2]) <= 0.01
            s.stuck_t = s.stuck_t + 1.0 / HZ if stuck else 0.0
            if s.stuck_t > 1.0 and now >= s.wiggle_until:   # caught on a corner on the way: sidestep, run up again
                a = s.rng.choice((-1, 1)) * s.rng.uniform(0.8, 2.0)
                s.wiggle, s.wiggle_until, s.stuck_t, s.phase = (math.cos(a), math.sin(a)), now + 0.4, 0.0, "go"
            if now < s.wiggle_until and s.phase == "go":
                fwd, strafe = s.wiggle
            s.last, s.pushed, s.bump = pos, False, None
            return fwd, strafe, move, pitch, buttons
        t = s.target
        if T is not None and getattr(T, "oob", None) is not None and not getattr(s, "escaping", False):
            from brain.core import Vec
            if T.out_of_bounds(Vec(*pos)):
                t = None                             # into a kill zone on the way: out of it first (pick: escape)
        if t is None or (math.dist(t[:2], pos[:2]) < 1.0 and abs(t[2] - pos[2]) < 0.6) or \
                now - s.target_t > (20 if T is None or s.straight else 40):
            s.why = "new goal: " + ("none" if t is None else "reached" if math.dist(t[:2], pos[:2]) < 1.0 else "timeout")
            s.pick(now, pos, rec, T, bounds)
        wp = s.way_in(now, pos, rec, T)
        if s.trial is not None:
            s.last, s.pushed = pos, False
            return 0.0, 0.0, 0.0, 0.0, 0
        if wp is not None and math.dist(wp[:2], pos[:2]) < 0.05 and math.dist(s.target[:2], pos[:2]) > 1.0:
            s.why = "way ends here"
            s.pick(now, pos, rec, T, bounds)         # the nav's way ends here (the goal snapped to this spot)
            wp = None
        grab = s.weapon_steer(now, pos, rec, T)
        if grab is not None:
            fwd, move, use = grab
            s.last, s.pushed = pos, False
            return fwd, 0.0, move, 0.0, use
        goal = wp or s.target
        move = math.atan2(goal[1] - pos[1], goal[0] - pos[0])
        fwd, strafe = 1.0, 0.0
        moved = s.last is not None and math.dist(s.last[:2], pos[:2]) > 0.01
        s.last = pos
        s.stuck_t = 0.0 if moved else s.stuck_t + 1.0 / HZ
        s.bumps(now, pos, moved, rec)
        jump = False
        if s.stuck_t > 0.8 and now >= s.wiggle_until:        # a step or a lip: jump and sidestep
            a = s.rng.choice((-1, 1)) * s.rng.uniform(0.8, 2.0)
            s.wiggle, s.wiggle_until, jump = (math.cos(a), math.sin(a)), now + 0.5, True
        if s.stuck_t > STUCK_S:
            s.why = "stuck"
            s.pick(now, pos, rec, T, bounds)
            s.stuck_t = 0.0
        # headway over a window, not a tick: pressed into a wall a bot jitters or slides a hundredth of a unit a tick,
        # so the tick check never fired and it pushed until the 20-40 s target timeout, then chose another goal behind
        # the same wall. Under HEADWAY_U in HEADWAY_S: sidestep and jump; twice: a new goal, not that way again for a
        # while
        if s.win is None or now - s.win[0] >= HEADWAY_S:
            if s.win is not None and math.dist(s.win[1][:2], pos[:2]) < HEADWAY_U:
                s.walls += 1
                if s.walls >= 2:
                    s.blocked, s.walls = (move, now + 20.0), 0
                    s.why = "no headway"
                    s.pick(now, pos, rec, T, bounds)
                else:
                    a = s.rng.choice((-1, 1)) * s.rng.uniform(1.2, 2.2)
                    s.wiggle, s.wiggle_until, jump = (math.cos(a), math.sin(a)), now + 0.8, True
            else:
                s.walls = 0
            s.win = (now, pos)
        if now < s.wiggle_until:
            fwd, strafe = s.wiggle
        # the step ahead: a deadly drop (level data, or where a bot already fell) -> stop, new goal.
        # On the nav's path only just ahead: a long probe overshoots the next corner of a walkway
        mx, my = math.cos(move) * fwd - math.sin(move) * strafe, math.sin(move) * fwd + math.cos(move) * strafe
        if any(s.deadly(pos[0] + mx * k, pos[1] + my * k, pos[2], rec, T, frm=pos) for k in ((0.3,) if wp else (0.6, 1.2))) \
                or s.walk_off_kills(pos, mx, my, rec, T):
            s.why = "edge: " + ("fall spot" if any(rec.near_fall(pos[0] + mx * k, pos[1] + my * k, pos[2], frm=pos)
                                                 for k in ((0.3,) if wp else (0.6, 1.2)))
                                else "walk-off kills" if s.walk_off_kills(pos, mx, my, rec, T) else "level-data drop")
            s.pick(now, pos, rec, T, bounds)
            s.pushed = False
            return 0.0, 0.0, move, 0.0, 0
        if now >= s.next_jump:                               # measure the jump now and then, where safe
            s.next_jump = now + s.rng.uniform(4, 10)
            jump = jump or not any(s.deadly(pos[0] + math.cos(a) * 1.5, pos[1] + math.sin(a) * 1.5, pos[2], rec, T)
                                   for a in [k * math.pi / 4 for k in range(8)])
        n = math.hypot(mx, my)
        if jump and T is not None and rec.phys is not None and n > 0.1:
            jump = self_safe(T, rec.phys, pos, mx / n, my / n, 0.0, 0.0)   # any jump: only where its arc lands it alive
        ahead = (pos[0] + mx * 0.5, pos[1] + my * 0.5, pos[2])
        crouch = crouch_key(*pos) in rec.crouch_cells or crouch_key(*ahead) in rec.crouch_cells   # people crouched here
        s.pushed, s.heading = now >= s.wiggle_until, move
        return fwd, strafe, move, 0.0, (BTN_JUMP if jump and not crouch else 0) | (BTN_CROUCH if crouch else 0)


class HumanWatch:
    """People's paths in any match (normal bot matches too): their floor, their deaths, and every
    jump they land, into the map's LiDAR data. live_bots: update() each tick, save() now and then."""

    def __init__(s, map_name, rec=None, T=None):
        s.rec = rec or Recorder(map_name, count_run=False, T=T)
        s.tracks, s.alive, s.t_last, s.seconds = {}, {}, None, 0.0
        s.steered = {}           # index -> times he pressed jump (None from the reader: unknown = yes)
        s.skipped = 0            # landings without a jump press (pushed by a bot): not his jumps

    def update(s, now, people):
        """people: [(index, (x, y, z) or None, alive[, crouch held[, jump pressed[, riding]]])] for every
        player who is not a bot. jump pressed None = unknown (counts as pressed). Riding a vehicle: their
        track starts over (a seat is no floor and a bump no jump of theirs), no death recorded."""
        if s.t_last is not None and people:
            s.seconds += now - s.t_last
        s.t_last = now
        for index, pos, alive, *extra in people:
            crouch = extra[:1]
            steering = extra[1] if len(extra) > 1 else None
            if len(extra) > 2 and extra[2] and alive:
                s.tracks[index], s.alive[index] = Track(), True
                continue
            if steering is not False:
                st = s.steered.setdefault(index, [])
                st.append(now)
                if len(st) > 600:
                    del st[:300]
            tr = s.tracks.setdefault(index, Track())
            up = alive and pos is not None
            if s.alive.get(index) and not up:
                info = tr.die()
                if info:
                    s.rec.died(info, "human", now)
            s.alive[index] = up
            if up:
                evs = tr.update(now, pos, bool(crouch and crouch[0]))
                on_events(s.rec, [e for e in evs if s.meant(index, e)], "human", KIND_HUMAN)

    def meant(s, index, ev):
        """A jump is his only if he pressed jump around its take-off: bots walking into an idle
        player pushed him off ledges and into a lift on Lockdown, which counted as his jumps. (A
        crouch path needs crouch held, so it is always his.)"""
        kind, info = ev
        if kind != "land" or "t0" not in info:
            return True
        t0 = info["t0"]
        ok = any(t0 - 1.0 <= t <= t0 + 0.3 for t in s.steered.get(index, ()))
        if not ok:
            s.skipped += 1
        return ok

    def save(s):
        sec, s.seconds = s.seconds, 0.0
        return s.rec.save(human_seconds=sec)


class RideWatch:
    """Every vehicle someone rides, into the map's ride data. Ground and hover vehicles leave the cells they drove over
    (the vehicles' ground, brain/maps.py rides_layers); aircraft their flown cells with the height over the floor
    under them, a histogram of those heights (the strafing and travelling heights), and their take-offs, landings and
    turn-backs (the heading reversed in 3 s: the edges people fly to). People and bots alike, kept apart (a person's
    drive counts at once, the heights come from people's flying). live_bots and LiDAR mode (main): update each tick,
    save with the LiDAR save. The LiDAR view draws every sample as it comes (feed, since)."""
    DRIVE_STEP, AIR_STEP = 0.25, 1.0    # u travelled between samples (a drive sample: a nav cell, 0.25 u)
    UP, DOWN = 1.5, 0.8                 # over the floor: airborne once above UP, landed once under DOWN
    FEED_MAX = 300000                   # samples kept for the live view (about 2 hours of driving)
    # the live view's sample kinds (rides_view uses the same): a person's drive, a bots-only drive, flown air
    FEED_DRIVE, FEED_BOT_DRIVE, FEED_AIR = 0, 1, 2

    def __init__(s, map_name, T=None, path=None):
        s.map, s.T = map_name, T
        s.path = path or os.path.join(ROOT, "maps", map_name, "rides.json")
        s.v = {}                        # vehicle handle -> its track
        s.new = s._empty()
        s.feed, s.feed_base = [], 0     # [x, y, z, kind] since the run began (feed_base: how many were dropped)
        s.feed_lock = threading.Lock()

    def _feed(s, x, y, z, kind):
        with s.feed_lock:
            s.feed.append([round(x, 2), round(y, 2), round(z, 2), kind])
            if len(s.feed) > s.FEED_MAX:
                drop = len(s.feed) - s.FEED_MAX
                del s.feed[:drop]
                s.feed_base += drop

    def since(s, n, most=40000):
        """(samples after the first n of this run, the count after them) for the live view's polling."""
        with s.feed_lock:
            i = max(0, n - s.feed_base)
            out = s.feed[i:i + most]
            return out, s.feed_base + i + len(out)

    @staticmethod
    def _empty():
        return dict(drive={}, air={}, takeoff=[], landing=[], turnback=[], h={"human": {}, "bot": {}})

    def update(s, now, vehicles, players, bots):
        """vehicles: the snapshot's (handle, kind, pos); players: its players (vehicle, id, alive); bots: the bots'
        player ids. A vehicle counts while someone alive rides it."""
        from brain import vehicles as V
        riders = {}
        for p in players:
            if p.alive and p.vehicle not in (None, -1):
                riders.setdefault(p.vehicle, []).append(p.id)
        for v in vehicles:
            who, sp = riders.get(v["handle"]), V.spec(v["kind"])
            if not who or not sp or sp["move"] == "none":
                s.v.pop(v["handle"], None)
                continue
            src = "bot" if all(i in bots for i in who) else "human"
            st = s.v.setdefault(v["handle"], dict(last=None, air=None, heads=[], turn_at=-9.0, ground_pt=None))
            x, y, z = (float(c) for c in v["pos"])
            if not all(math.isfinite(c) for c in (x, y, z)):
                continue
            if sp["move"] == "air":
                s._fly(now, st, x, y, z, src)
            elif st["last"] is None or math.dist((x, y, z), st["last"]) >= s.DRIVE_STEP:
                st["last"] = (x, y, z)
                c = s.new["drive"].setdefault((round(x * 4) / 4, round(y * 4) / 4, round(z, 1)), [0, 0])
                c[src == "bot"] += 1
                s._feed(x, y, z, s.FEED_BOT_DRIVE if src == "bot" else s.FEED_DRIVE)

    def _fly(s, now, st, x, y, z, src):
        if s.T is None:
            return
        h = s.T.height_over(x, y, z)
        was = st["air"]
        air = h > (s.DOWN if was else s.UP)
        if was is False and air:        # took off, from where it last stood
            gx, gy, gz = st["ground_pt"] or (x, y, z - h)
            s.new["takeoff"].append([round(gx, 2), round(gy, 2), round(gz, 2), src])
        if was and not air:
            s.new["landing"].append([round(x, 2), round(y, 2), round(z, 2), src])
        if not air:
            st["ground_pt"] = (x, y, z)
        st["air"] = air
        if not air or (st["last"] is not None and math.dist((x, y, z), st["last"]) < s.AIR_STEP):
            return
        if st["last"] is not None:      # turn-backs: the way it flies turned over 126 degrees within 3 s
            st["heads"] = [hd for hd in st["heads"] if now - hd[0] <= 3.0] + [
                (now, math.atan2(y - st["last"][1], x - st["last"][0]))]
            if abs(wrap(st["heads"][-1][1] - st["heads"][0][1])) > 2.2 and now - st["turn_at"] > 6.0:
                st["turn_at"] = now
                s.new["turnback"].append([round(x, 2), round(y, 2), round(z, 2), src])
        st["last"] = (x, y, z)
        c = s.new["air"].setdefault((round(x * 2), round(y * 2)), [round(z - h, 2), 0.0, 0, 9e9, -9e9])
        c[1], c[2], c[3], c[4] = c[1] + h, c[2] + 1, min(c[3], h), max(c[4], h)
        s._feed(x, y, z, s.FEED_AIR)
        b = str(round(h * 2) / 2)
        s.new["h"][src][b] = s.new["h"][src].get(b, 0) + 1

    def save(s):
        """Merge what was recorded since the last save into the map's rides.json (written whole, then moved over the
        old one). True when there was anything new."""
        new, s.new = s.new, s._empty()
        if not any(new[k] for k in ("drive", "air", "takeoff", "landing", "turnback")):
            return False
        d = {}
        if os.path.exists(s.path):
            with open(s.path, encoding="utf-8") as f:
                d = json.load(f)
        drive = {tuple(r[:3]): list(r[3:5]) for r in d.get("drive", [])}
        for k, (hn, bn) in new["drive"].items():
            c = drive.setdefault(k, [0, 0])
            c[0], c[1] = c[0] + hn, c[1] + bn
        air = {tuple(r[:2]): list(r[2:]) for r in d.get("air", [])}
        for k, (gz, sh, n, lo, hi) in new["air"].items():
            c = air.get(k)
            air[k] = [gz, sh, n, lo, hi] if c is None else [c[0], c[1] + sh, c[2] + n, min(c[3], lo), max(c[4], hi)]
        out = dict(drive=[list(k) + v for k, v in drive.items()],
                   air=[list(k) + [round(v[0], 2), round(v[1], 1)] + v[2:3] + [round(v[3], 2), round(v[4], 2)]
                        for k, v in air.items()],
                   h={src: dict(d.get("h", {}).get(src, {})) for src in ("human", "bot")})
        for src in ("human", "bot"):
            for b, n in new["h"][src].items():
                out["h"][src][b] = out["h"][src].get(b, 0) + n
        for k in ("takeoff", "landing", "turnback"):
            out[k] = (d.get(k, []) + new[k])[-2000:]
        os.makedirs(os.path.dirname(s.path), exist_ok=True)
        tmp = s.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f)
        os.replace(tmp, s.path)
        return True


def rides_view(map_name, path=None):
    """A map's stored drives and flights (maps/<map>/rides.json, RideWatch) for the LiDAR view: dict(drive=[[x, y, z,
    kind]], air=[[x, y, z]], people=cells a person drove). Drive kinds as RideWatch's feed; only the cells the vehicles'
    ground uses (brain/maps.py rides_layers: a person once or bots twice). Flown air at its mean flown height."""
    p = path or os.path.join(ROOT, "maps", map_name, "rides.json")
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return dict(drive=[], air=[], people=0)
    drive, people = [], 0
    for r in d.get("drive", []):
        if len(r) < 5:
            continue
        if r[3] >= 1:
            people += 1
            drive.append([r[0], r[1], r[2], RideWatch.FEED_DRIVE])
        elif r[4] >= 2:
            drive.append([r[0], r[1], r[2], RideWatch.FEED_BOT_DRIVE])
    air = [[r[0] / 2, r[1] / 2, round(r[2] + r[3] / max(r[4], 1), 2)] for r in d.get("air", []) if len(r) >= 5]
    return dict(drive=drive, air=air, people=people)


class Notices:
    """LiDAR mode's notices over the game (botcore draws them): a person's jump just learned, and
    the first time bots have done one twice. Each once per jump; jumps from earlier runs stay quiet."""

    def __init__(s, rec, send):
        s.rec, s.send = rec, send
        s.learned = {id(l) for l in rec.links if l["human"]}
        s.confirmed = {id(l) for l in rec.links if l["human"] and l["bot_ok"] >= 2}

    def check(s):
        for l in s.rec.links:
            kind = l.get("kind")
            if l["human"] and id(l) not in s.learned:
                s.learned.add(id(l))
                if kind == "crouch":
                    s.send("CROUCH PATH LEARNED", "LiDAR bots use it now, every bot from the next match")
                elif kind != "route":                # a recorded route has its own PATH SAVED
                    s.send("JUMP LEARNED", "LiDAR bots use it now, every bot from the next match")
            if l["human"] and l["bot_ok"] >= 2 and id(l) not in s.confirmed:
                s.confirmed.add(id(l))
                s.send({"crouch": "BOTS DID YOUR CROUCH PATH", "route": "BOTS DID YOUR PATH"}.get(kind, "BOTS DID YOUR JUMP"),
                       f"Bots have done it {l['bot_ok']} times")


# --- the live 3D view (tools/lidar_view.html polls these)
class Hub:
    def __init__(s, rec, mode):
        s.rec, s.mode = rec, mode
        s.session = f"{rec.map}-{int(time.time() * 1000)}"   # a new run (new match, new map): the page resets
        s.players = {}           # index -> dict(name, human, pos, air, alive, trail)
        s.lock = threading.Lock()
        s.note = ""
        s.recording = None       # PathRec.view(): a route being recorded (F6)

    def set_player(s, index, **kw):
        with s.lock:
            s.players.setdefault(index, {}).update(kw)

    def stored_view(s):
        d = s.rec.stored
        return dict(map=s.rec.map, title=map_title(s.rec.map), mode=s.mode, session=s.session, cell=CELL, zstep=ZSTEP, walk=d.get("walk", []),
                    deaths=d.get("deaths", [])[-1500:], runs=d.get("runs", 0), bot_minutes=d.get("bot_minutes", 0),
                    features=load_features(s.rec.map), links=d.get("links", []), weapons=d.get("weapons", []),
                    wall_kinds=wall_kinds_view(s.rec.map), rides=rides_view(s.rec.map))

    def live(s, since, rsince=0):
        """rsince: drive and flight samples of this run the page already has (RideWatch.since; s.rides, LiDAR mode)."""
        if time.time() - getattr(s, "classified", 0) > 2:   # two-way / one-way for new jumps too
            s.classified = time.time()
            s.rec.classify()
        with s.rec.lock:
            cells = s.rec.events[since:since + 40000]
            links = [{k: v for k, v in l.items() if not k.startswith("_")} for l in s.rec.links]
            deaths = s.rec.deaths[-1500:]
        with s.lock:
            players = [dict(index=i, **{k: v for k, v in p.items()}) for i, p in s.players.items()]
        weapons = [dict(w) for w in s.rec.weapons]
        extra = {}
        st = getattr(s, "stations", None)               # (brain/stations.py: sent again whenever they change)
        ob = getattr(s, "oob", None)                    # (and the out of bounds learned: brain/oob.py)
        ver = (st.version if st is not None else None, ob.version if ob is not None else None)
        if (st is not None or ob is not None) and (ver != getattr(s, "sent_ver", None) or since == 0):
            s.sent_ver, extra["features"] = ver, load_features(s.rec.map, st, ob)
        d = getattr(s.rec, "director", None)            # coverage and the open patches (tools/lidar_director.py)
        if d is not None and d.history:
            extra["coverage"] = d.view()
        rw = getattr(s, "rides", None)                  # drives and flights recorded this run, as they come
        if rw is not None:
            extra["rides"], extra["rseq"] = rw.since(rsince)
        return dict(map=s.rec.map, mode=s.mode, session=s.session, note=s.note, seq=since + len(cells), cells=cells, weapons=weapons,
                    players=players, deaths=deaths, links=links, recording=s.recording, calls=s.rec.calls, t=round(time.time(), 2),
                    **extra)


def serve(hub, port=PORT):
    """The 3D view on http://127.0.0.1:<port>/ (this machine only). None if the port is taken."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlparse
    page = os.path.join(HERE, "lidar_view.html")

    class Handler(BaseHTTPRequestHandler):
        def log_message(s, *a):
            pass

        def send(s, body, ctype, cache=False):
            s.send_response(200)
            s.send_header("Content-Type", ctype)
            s.send_header("Cache-Control", "max-age=3600" if cache else "no-store")
            s.send_header("Content-Length", str(len(body)))
            s.end_headers()
            s.wfile.write(body)

        def answer(s, code, data):                   # (custom) a JSON answer with its status: Edit spots
            body = json.dumps(data).encode()
            s.send_response(code)
            s.send_header("Content-Type", "application/json")
            s.send_header("Cache-Control", "no-store")
            s.send_header("Content-Length", str(len(body)))
            s.end_headers()
            s.wfile.write(body)

        def do_GET(s):
            u = urlparse(s.path)
            h = getattr(hub, "current", hub)         # the simulator swaps hubs map by map
            q = parse_qs(u.query)
            if u.path in ("/", "/index.html"):
                s.send(open(page, "rb").read(), "text/html; charset=utf-8")
            elif u.path == "/maps":
                s.send(json.dumps(dict(maps=map_list(), live=h.rec.map, mode=h.mode)).encode(), "application/json")
            elif u.path == "/map":
                name, src = (q.get("name") or [""])[0], (q.get("src") or ["scan"])[0]
                if not name or (name == h.rec.map and src == ("sim" if h.mode == "sim" else getattr(h, "view_src", "scan"))):
                    view = h.stored_view()
                    if getattr(h, "view_src", "scan") == "sim":
                        view.update(src="sim")
                    s.send(json.dumps(view).encode(), "application/json")
                elif map_ok(name):
                    if src == "scan":                # no scan from matches, a simulator one: show that
                        it = next((m for m in map_list() if m["name"] == name), {})
                        if "scan" not in it and "sim" in it:
                            src = "sim"
                    path = os.path.join(ROOT, "maps", name, "lidar_sim.json" if src == "sim" else "lidar.json")
                    view = Hub(Recorder(name, count_run=False, path=path), "stored").stored_view()
                    view.update(browse=True, src=src)  # another map than the one being mapped: stored data only
                    s.send(json.dumps(view).encode(), "application/json")
                else:
                    s.send_error(404)
            elif re.fullmatch(r"/art/(games|maps)/[a-z0-9_]+\.(png|jpg)", u.path) and \
                    os.path.exists(os.path.join(ART, *u.path.split("/")[2:])):
                s.send(open(os.path.join(ART, *u.path.split("/")[2:]), "rb").read(),
                       "image/png" if u.path.endswith(".png") else "image/jpeg", cache=True)
            elif u.path == "/live":
                try:
                    since = int((q.get("since") or ["0"])[0])
                    rsince = int((q.get("rsince") or ["0"])[0])
                except ValueError:
                    return s.send_error(400)
                d = h.live(max(0, since), max(0, rsince))
                ctl = getattr(hub, "control", None)  # the simulator's state for its panel (tools/lidar_sim.py)
                if ctl is not None:
                    d["sim"] = ctl.state()
                    hub.last_seen = time.time()
                s.send(json.dumps(d).encode(), "application/json")
            elif u.path in ("/spots", "/spots/floor"):   # (custom) Edit spots: the spots bots use (tools/spots.py)
                import spots
                s.answer(*spots.handle("GET", u.path, (q.get("name") or [""])[0]))
            else:
                s.send_error(404)

        def do_POST(s):                              # /remove?name=<map>&src=scan|sim: the maps list's Remove
            u = urlparse(s.path)
            h = getattr(hub, "current", hub)
            q = parse_qs(u.query)
            if u.path == "/yield":                   # a LiDAR match wants this address: a stored view gives it up
                if getattr(h, "mode", None) != "stored":
                    return s.send_error(409)
                s.send(b"{}", "application/json")
                hub.yielded = True
                threading.Thread(target=lambda: (box["srv"].shutdown(), box["srv"].server_close()), daemon=True).start()
                return
            if u.path == "/spots":                   # (custom) Edit spots' Save (tools/spots.py)
                import spots
                n = int(s.headers.get("Content-Length") or 0)
                if not 0 < n < 1 << 20:
                    return s.answer(413 if n else 400, dict(error="no edit" if not n else "too big"))
                return s.answer(*spots.handle("POST", u.path, (q.get("name") or [""])[0], s.rfile.read(n),
                                              s.headers.get("X-LiDAR")))
            ctl = getattr(hub, "control", None)
            if u.path == "/sim" and ctl is not None:     # the simulator's panel: pick, all, speed, pause, stop, spots
                if s.headers.get("X-LiDAR") != "sim":    # (a page from another site cannot send it without asking)
                    return s.send_error(403)
                try:
                    n = int(s.headers.get("Content-Length") or 0)
                    code, answer = ctl.command(json.loads(s.rfile.read(n) or b"{}") if 0 < n < 65536 else {})
                except (ValueError, KeyError, TypeError) as e:
                    code, answer = 400, dict(error=f"bad request: {e}")
                body = json.dumps(answer).encode()
                s.send_response(code)
                s.send_header("Content-Type", "application/json")
                s.send_header("Content-Length", str(len(body)))
                s.end_headers()
                s.wfile.write(body)
                return
            name, src = (q.get("name") or [""])[0], (q.get("src") or ["scan"])[0]
            if u.path != "/remove":
                return s.send_error(404)
            refused = remove_refused(h, name, src, s.headers.get("X-LiDAR"))
            if refused:
                return s.send_error(refused)
            kept = remove_scan(name, src)
            if name == h.rec.map:                    # the stored map this view shows: empty from now on
                h.rec = Recorder(name, count_run=False, path=h.rec.path)
            s.send(json.dumps(dict(kept=[os.path.relpath(p, ROOT) for p in kept])).encode(), "application/json")

    class Server(ThreadingHTTPServer):
        # no address reuse: on Windows it let a stored view and a LiDAR match both serve this port and the
        # browser got the stored map
        allow_reuse_address = False

    box = {}
    for attempt in range(12):
        try:
            box["srv"] = srv = Server(("127.0.0.1", port), Handler)
            break
        except OSError as e:
            if getattr(getattr(hub, "current", hub), "mode", None) == "stored" or attempt == 11:
                print(f"3D view not started: port {port} is in use ({e})", flush=True)
                return None
            if attempt == 0:                         # a live match: ask a stored view there to step aside
                try:
                    import urllib.request
                    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/yield", data=b"",
                                                                  method="POST"), timeout=2).read()
                except Exception:
                    pass
            time.sleep(0.3)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"3D view: http://127.0.0.1:{port}/", flush=True)
    return srv


def report(rec, data, T=None):
    """logs/lidar_<map>.md: what the bots and people found, against the level data the brain uses."""
    walk = data["walk"]
    floor = [w for w in walk if w[3] != KIND_AIR]
    cells2d = {(x, y) for x, y, z, k, n in floor}
    lines = [f"# LiDAR report: {rec.map}", "",
             f"Runs {data['runs']}, {data['bot_minutes']} bot-minutes, {data.get('human_minutes', 0)} minutes of people. "
             f"{len(floor)} floor cells ({len(cells2d) * CELL * CELL:.0f} square units), "
             f"{sum(1 for w in walk if w[3] == KIND_HUMAN)} of them walked by people.", ""]
    objs = data.get("objectives") or []
    if objs:                                         # every gametype objective place (Objectives)
        bad = [p for p in objs if not p.get("reached") or not p.get("reach")]
        lines += [f"Gametype objective places: {len(objs)}, {sum(1 for p in objs if p.get('reached'))} reached by "
                  f"someone, {sum(1 for p in objs if not p.get('reach'))} not reachable on the nav from the spawns.", ""]
        lines += [f"- {'/'.join(p['roles'])} at ({p['pos'][0]:.1f}, {p['pos'][1]:.1f}, {p['pos'][2]:.1f}): "
                  f"{'reached' if p.get('reached') else 'no way found' if p.get('given_up') else 'not reached yet'}, "
                  f"{'on the nav' if p.get('reach') else 'nav floor there but not reached from the spawns' if p.get('on') else 'no nav floor there'}"
                  for p in bad[:40]]
        lines.append("")
    if getattr(rec, "director", None) is not None:   # coverage of the reachable floor, what is left and why
        lines += ["Coverage (the LiDAR director, tools/lidar_director.py):", ""] + rec.director.lines() + [""]
    if T is not None and floor:
        miss = [(x * CELL, y * CELL, z * ZSTEP, n) for x, y, z, k, n in floor
                if not T.ground_ok(x * CELL, y * CELL, z * ZSTEP, drop=0.6)]
        lines += [f"Floors the level data lacks: {len(miss)} of {len(floor)} cells "
                  f"({len(miss) / len(floor):.1%}). Most walked:", ""]
        lines += [f"- ({x:.1f}, {y:.1f}, {z:.1f}): {n} samples" for x, y, z, n in sorted(miss, key=lambda m: -m[3])[:15]]
        lines.append("")
    links = data.get("links", [])
    crawls = [l for l in links if l.get("kind") == "crouch"]
    lines += [f"Crouch floor: {sum(1 for w in walk if w[3] == KIND_CROUCH)} cells. Crouch routes (both ways): {len(crawls)}.", ""]
    lines += [f"- {l['found_by']}: {l['take_off']} <-> {l['land']} ({len(l['path'])} points); people {l['human']}, "
              f"bots ok {l['bot_ok']} / failed {l['bot_fail']}" for l in crawls[:20]]
    routes = [l for l in links if l.get("kind") == "route"]
    lines += ["", f"Routes recorded with F6 (one way): {len(routes)}.", ""]
    lines += [f"- {l['take_off']} -> {l['land']} ({len(l['path'])} points, {sum(1 for q in l['path'] if q[3] & 2)} jumps); "
              f"people {l['human']}, bots ok {l['bot_ok']} / failed {l['bot_fail']}" for l in routes[:20]]
    links = [l for l in links if l.get("kind", "jump") not in ("crouch", "route")]
    jl = [l for l in links if l.get("kind", "jump") == "jump"]
    lines += ["", f"Jumps, evaluated: {sum(1 for l in jl if l.get('ways') == 'two-way')} two-way (back and forth), "
              f"{sum(1 for l in jl if l.get('ways') == 'one-way')} one-way (no way back)."]
    lines += ["", f"Jumps people landed (links bots may use): {sum(1 for l in links if l['human'])}; "
              f"found by bots: {sum(1 for l in links if not l['human'])}.", ""]
    for l in sorted(links, key=lambda l: -(l["human"] * 10 + l["bot_ok"]))[:25]:
        state = ("bots can do it" if l["bot_ok"] >= 2 else "bots fail it: needs a technique?" if l["bot_fail"] >= 3 and not l["bot_ok"]
                 else "not confirmed by bots yet")
        lines.append(f"- {l['found_by']}: {l['take_off']} -> {l['land']} (apex {l['apex']}, {l['air_s']} s); "
                     f"{l.get('ways', '?')}; people {l['human']}, bots ok {l['bot_ok']} / failed {l['bot_fail']}: {state}")
    ws = data.get("weapons", [])
    lines += ["", f"Weapons found: {len(ws)} spots."] + [f"- {w['name']} at {w['pos']}: seen {w['seen']}, picked up {w['picked']}"
                                                        for w in sorted(ws, key=lambda w: w["name"])]
    falls = [d for d in data["deaths"] if d.get("cause") == "fall"]
    lines += ["", f"Deaths {len(data['deaths'])}, falls {len(falls)} (dropped more than {FALL} units); latest:", ""]
    lines += [f"- {d.get('who', 'bot')} stood at {d['stood']}, fell {d['drop']} to {d['pos']}" for d in falls[-20:]]
    j = sorted(data["jumps"])
    if j:
        lines += ["", f"Jumps measured {len(j)}: apex above take-off median {j[len(j) // 2]:.2f}, "
                      f"90th percentile {j[int(len(j) * 0.9)]:.2f} units."]
    path = os.path.join(ROOT, "logs", f"lidar_{file_name(rec.map)}.md")
    open(path, "w").write("\n".join(lines) + "\n")
    return path


def teach_falls(rec, deaths, T):
    """Falls off edges the nav would walk off (the level data shows floor within its 3-unit drop
    rule just past the edge): report that spot to the nav, as the edge guard does. The nav learns
    a spot on its second report. Returns how many spots it actually learned."""
    from brain.core import Vec
    from brain.maps import get_map, save_learned
    from brain.terrain import MAX_DROP
    before = len(T.stuck)
    for d in deaths:
        if d.get("cause") != "fall":
            continue
        a, b = Vec(*d["stood"]), Vec(*d["pos"])
        v = Vec(b.x - a.x, b.y - a.y, 0)
        if v.flat() > 0.05:
            p = a + v * (0.4 / v.flat())
            if T.ground_ok(p.x, p.y, a.z, drop=MAX_DROP):
                T.learn_stuck(p)
    n = len(T.stuck) - before
    if n:
        save_learned(get_map(rec.map))
    return n


def ground_weapons(live, players):
    """Weapons lying on the map now: [(handle, name, pos)]. A weapon in someone's hands is not
    lying: the H2A / H4 reader knows them (held handles); elsewhere, one at a player's position."""
    try:
        objs = live.objects((2,))
    except Exception:
        return []
    held = getattr(live, "_held", None)
    out = []
    for h, typ, name, pos in objs:
        if held is not None and h in held:
            continue
        if held is None and any(p["pos"] and math.dist(p["pos"], pos) < 0.6 for p in players):
            continue
        name = name.replace("\\", "/").rsplit("/", 1)[-1] if name else "unknown"
        out.append((h, name, tuple(pos)))
    return out


def level_data(map_name, live=None):
    """(the map's terrain, its bounds, the map name). With a running Reach game (live) that is a map variant of its own,
    the variant's name, "<base>/variants/<id>": its LiDAR data and navmesh are filed under the base map, its nav covers
    its window (grown by the main loop) and its Forge pieces go in face by face, each a floor, ramp or wall by its
    angle."""
    name = map_name
    try:
        from brain.maps import get_map, terrain
        from brain.terrain import NAV_CELL
        if live is not None and type(live).__name__ == "LiveReach":
            try:
                from brain.forge import live_pieces
                from brain.variants import base_area, base_placed, identify
                objs = get_map(map_name)["objects"]
                name = identify(map_name, live_pieces(live), base_placed(objs), game="reach", area=base_area(objs))
            except Exception as e:
                print("could not read the game's placed objects:", e, flush=True)
        m = get_map(name)
        T = terrain(m)
        if "variant" in m:
            print(f"map variant {name}: {m['variant']['count']} objects of its own, {len(m['live_blocks'])} pieces "
                  f"({getattr(T, 'face_kinds', {})}), {len(m['shields'])} shields, nav window {m['window']}", flush=True)
        return T, (T.x0, T.y0, T.x0 + T.nw * NAV_CELL, T.y0 + T.nh * NAV_CELL), name
    except Exception as e:                          # a map without level data: explore blind
        print("no level data for", map_name, "-", e, flush=True)
        return None, None, name


def main(o):
    import botctl
    from brain.live import Live, LiveH2, LiveH3, LiveReach, LiveODST, LiveH4F
    live = {"ce": Live, "h2": LiveH2, "h3": LiveH3, "reach": LiveReach, "odst": LiveODST,
            "h2a": lambda: LiveH4F("groundhog.dll"), "h4": LiveH4F}[o.game]()
    m = botctl.shm()
    T, bounds, o.map = level_data(o.map, live)     # (a map variant: its own name, its data in its folder)
    rec = Recorder(o.map, T=T)
    rec.pickup_ok = o.game in PICKUP_GAMES
    import jumpphys                                 # bots call their jumps with this game's physics
    rec.phys = jumpphys.Phys(o.game, rec.apex() if len(rec.stored.get("jumps", [])) >= 20 else None)
    if T is not None:                                # the map's lifts and man cannons, read from its tags: ride links
        import lidar_rides                           # the nav uses at once (never saved: rebuilt every run)
        rides = lidar_rides.ride_links(o.map, T, rec.phys)
        if rides:
            rec.links += rides
            nav_learn(T, o.map, rec.links)
        print(f"{len(rides)} lift and man cannon rides from the map's tags", flush=True)
    owner_acts, owner_had, dbg_seq = [], None, None
    if T is not None and hasattr(live, "set_map"):  # weapon names come from the map's placements
        from brain.maps import get_map
        live.set_map(get_map(o.map)["objects"])     # (a map variant: its base map's scenario)
    hub = Hub(rec, "live")
    held, seen_w, next_w = {}, set(), 0.0
    srv = serve(hub)
    people = HumanWatch(o.map, rec)
    # every vehicle driven or flown -> the map's drive mesh and airspace (rides.json, as in normal matches: live_bots),
    # drawn live in the view (Hub.live); the bots' vehicles use it from the next match
    drives = hub.rides = RideWatch(o.map, T=T)       # (rides above: the map's lifts and man cannons, another thing)
    rides_err = [False]

    def save_rides():
        try:
            if drives.save():
                print(f"drives and flights saved: {os.path.relpath(drives.path, ROOT)}", flush=True)
        except Exception as e:                      # never stops the mapping (nor the LiDAR save after it)
            print(f"rides not saved: {type(e).__name__}: {e}", flush=True)
    send = lambda title, line: botctl.notice(m, title, line)
    notices, paths = Notices(rec, send), PathRec(rec, send)
    shots = ShotRec(live, o.map, send, rec)          # F7: shots that open things (gate buttons, bridge locks)
    told = False
    from brain.maps import usable_links
    nav_sig, next_sync = [id(l) for l in usable_links(rec.links)], 0.0   # what the nav was given at load
    stuck0 = len(T.stuck) if T is not None else 0
    bots, alive = {}, {}
    rng = random.Random(11)
    from brain.maps import get_map, grow as map_grow, spawn_points, swap as map_swap
    gm, grow_at = get_map(o.map), [-9.0]
    if T is not None:                                # the LiDAR director: the whole map's plan (tools/lidar_director.py)
        from lidar_director import LidarDirector
        rec.director = LidarDirector(T, rec, spawn_points(gm))
    stations, st_check = None, [-9.0, -9.0, -9.0]    # every gameplay object: abilities, teleporters ... (brain/stations.py)
    if o.game in ("h3", "reach", "h4", "h2a"):
        from brain.stations import Stations, scan as station_scan
        stations = hub.stations = Stations(o.map)
    if T is not None:                                # every gametype objective place: one bot to each (Objectives)
        rec.objectives = Objectives(o.map, T, rec.stored.get("objectives"), stations)
        print(f"{rec.objectives.seed(rec.director)} objective places to visit; {rec.objectives.line()}", flush=True)
    from brain.core import Vec
    from brain.oob import Oob                    # out of bounds, learned here too (brain/oob.py): a soft wall for bots
    oob = hub.oob = Oob(o.map)
    oob_seen = [oob.version, 0.0]
    if oob.spots or oob.volumes:                 # (and the map's own kill zones: maps/<map>/killzones.json)
        T.set_oob(oob.spots, oob.version, oob.volumes)
        nav_learn(T, o.map, rec.links)           # (links landing in a kill zone out of the nav, now that it knows them)
    import bug_reports
    import types
    run_stamp = time.strftime("%Y%m%d-%H%M%S")
    dec_t = {}                                       # each bot's decisions, twice a second and on every new goal
    dec = open(os.path.join(ROOT, "logs", f"lidar_decisions_{file_name(o.map)}_{run_stamp}.jsonl"), "a", buffering=1)
    t0 = last_save = time.time()
    collector, last_at = None, {}                  # your play recorded in LiDAR runs too (the player's boot camp demos:
    try:                                           # LiDAR mode kept no Data collector, so his ability use was lost)
        from collector import Collector
        collector = Collector(os.path.join(ROOT, "logs", f"collect_{file_name(o.map)}_{run_stamp}.jsonl"), o.map, o.game,
                              lambda: time.time() - t0)
        print("data collector on:", collector.path, flush=True)
    except Exception as e:                          # never stops the mapping
        print(f"data collector could not start: {type(e).__name__}: {e}", flush=True)
    bot_s, ok_at = 0.0, time.time()
    try:
        while time.time() - t0 < o.seconds:
            tick = time.time()
            now = tick - t0
            try:
                players = live.players()
            except Exception as e:
                players, why = [], e
            else:
                why = "no players"
            if not players:                          # the match ended (or a read raced it)
                if tick - ok_at > GAME_GONE_S:
                    print(f"game gone ({why}): stopping", flush=True)
                    break
                time.sleep(0.5)
                continue
            ok_at = tick
            try:
                vehicles = seat_places(live, players)    # (a rider's place: his vehicle's)
            except Exception:
                vehicles = []
            if not told:
                told = True
                send("LIDAR MODE", "The bots are mapping this map. Play along: your jumps, routes and drives teach them too")
            ps = {p["index"]: p for p in players}
            mine = botctl.status(m)["bots"]
            is_up = lambda p: bool(p and p["pos"] and p.get("health", 1.0) > 0)
            rec.players_pos = [tuple(p["pos"]) for p in players if is_up(p)]
            if T is not None and gm.get("window") is not None:   # a map variant's nav grows as players near its edges
                if now - grow_at[0] > 1.0:
                    grow_at[0] = now
                    w = map_grow(gm, rec.players_pos)
                    if w:
                        print(f"{now:6.1f}s nav window growing to {w}", flush=True)
                if map_swap(gm):                     # (T is the same object, grown; the director's samples were not)
                    rec.director = LidarDirector(T, rec, spawn_points(gm))
                    if getattr(rec, "objectives", None) is not None:
                        rec.objectives.seed(rec.director)
                    print(f"{now:6.1f}s nav grown: window {gm['window']}", flush=True)
            gone = [i for i in mine.values() if alive.get(i) and not is_up(ps.get(i))]
            reset = len(gone) >= 3 and len(gone) >= len(mine) / 2   # most bots gone in one tick: a new round
            if reset:                                                # or the match end (Battle Creek, 16 at once), not deaths
                print(f"{now:6.1f}s {len(gone)} bots gone at once: a new round, not counted as deaths", flush=True)
            if now >= next_w:                          # weapons lying around, twice a second
                next_w = now + 0.5
                rec.ground = ground_weapons(live, players)
            # a skilled player's input, kept 2 s: when he picks a weapon up it is saved, so the
            # game's pickup fields (H2A / H4: not decoded yet) can be read from a real pickup
            seq = struct.unpack_from("<I", m, botctl.OFF_DBG_SEQ)[0]
            if seq != dbg_seq:
                dbg_seq = seq
                owner_acts = [a for a in owner_acts if now - a[0] < 2.0] + [(now, bytes(m[botctl.OFF_DBG:botctl.OFF_DBG + 0x100]).hex())]
            o0 = ps.get(0)
            if o0 and o0.get("pos"):
                had = set(o0.get("weapons") or [])
                for name in had - (owner_had if owner_had is not None else had):
                    rec.found_weapon(name, o0["pos"], "picked")
                    # (a Forge layout's map name has slashes: written to logs/owner_pickups_reach_forge_halo/variants/..
                    # the run died on the player's first pickup, Forge; a failed note never stops the mapping)
                    try:
                        with open(pickups_path(o.map), "a") as f:
                            f.write(json.dumps(dict(t=round(now, 2), weapon=name, pos=r2(o0["pos"]),
                                                    ground=[(hex(h), n, r2(q)) for h, n, q in rec.ground if math.dist(q, o0["pos"]) < 2.0],
                                                    actions=owner_acts)) + chr(10))
                        print(f"{now:6.1f}s person picked up {name}: his input saved for decoding", flush=True)
                    except OSError as e:
                        print(f"{now:6.1f}s person picked up {name}: not saved ({e})", flush=True)
                owner_had = had
            bot_ids = set(mine.values())
            if stations is not None:                    # every gameplay object, teleports taken (brain/stations.py)
                try:
                    stations.watch([(p["index"], tuple(p["pos"]) if p["pos"] else None, is_up(p)) for p in players])
                    if now - st_check[0] > 2.0:
                        st_check[0] = now
                        stations.update(station_scan(live, o.game), {p.get("vehicle_top", p["vehicle"]) for p in players if p.get("vehicle", -1) != -1},
                                        [tuple(p["pos"]) for p in players if is_up(p)])
                        if getattr(rec, "objectives", None) is not None:   # objectives the game spawned: visit them too
                            for p in rec.objectives.add_live(stations, rec.director):
                                print(f"{now:6.1f}s objective seen in the game: {'/'.join(p['names'])} at {p['pos']}", flush=True)
                    if now - st_check[1] > 30.0:
                        st_check[1] = now
                        stations.save()
                except Exception as e:                  # never stops the mapping: off for the rest of the run
                    print(f"{now:6.1f}s stations stopped: {type(e).__name__}: {e}", flush=True)
                    stations = None
            try:
                states = people_states(players, bot_ids, is_up, last_at)
            except Exception as e:                      # (never stops the mapping)
                print(f"{now:6.1f}s players not read for the recordings: {type(e).__name__}: {e}", flush=True)
                states = []
            try:                                        # drives and flights (RideWatch): a rider's place is his vehicle's
                drives.update(now, vehicles, states, bot_ids)
            except Exception as e:                      # (never stops the mapping; said once)
                if not rides_err[0]:
                    rides_err[0] = True
                    print(f"{now:6.1f}s drive recording failed: {type(e).__name__}: {e}", flush=True)
            if collector is not None:                   # your play, every tick (tools/collector.py): what you do with
                try:                                    # each ability, for the bots
                    from brain.tracefmt import crosshair, seat_of
                    collector.tick(now, states, None, {q.id: (crosshair(q, states, vehicles, T), seat_of(q, vehicles))
                                                       for q in states if not q.is_bot})
                except Exception as e:
                    print(f"{now:6.1f}s data collector stopped: {type(e).__name__}: {e}", flush=True)
                    collector.close()
                    collector = None
            if now - st_check[2] > 1.0:                 # the player's bug reports, filed with where he stood (bug_reports.py)
                st_check[2] = now
                try:
                    snap = types.SimpleNamespace(mode="lidar", score={}, players=states)
                    for stamp in bug_reports.attach_new(t0, now, snap, o.map, None, f"lidar_{file_name(o.map)}_{run_stamp}.jsonl",
                                                        {}, mode="lidar", stations=stations, oob=oob):
                        print(f"{now:6.1f}s bug report {stamp}: filed with the stations near the person", flush=True)
                except Exception as e:
                    print(f"{now:6.1f}s bug report filing failed: {type(e).__name__}: {e}", flush=True)
            crouching = botctl.owner_crouch(m)          # player 0 = the player (None: not decoded for this game)
            steering = botctl.owner_jumping(m)
            shots.update(now, o0)
            shots.watch(now)                             # anyone did a recorded shot: done for the match
            paths.update(now, o0["pos"] if o0 else None, is_up(o0), bool(crouching))
            hub.recording = paths.view()
            try:                                         # deaths nobody caused, the player's flags (brain/oob.py)
                for x, y, z, counted in oob.watch(now, [(i, p.get("team", -1), tuple(p["pos"]) if p["pos"] else None,
                                                         p.get("health", 1.0) > 0, p.get("health", 1.0), p.get("shield", 1.0),
                                                         bool(p.get("riding"))) for i, p in ps.items()],
                                                  lambda a, b: T.los(Vec(*a), Vec(*b))):
                    print(f"{now:6.1f}s out of bounds: a death nobody caused at ({x:.1f}, {y:.1f}, {z:.1f})"
                          + ("" if counted else ", once (a second one there counts)"), flush=True)
                if oob.version != oob_seen[0]:
                    T.set_oob(oob.spots, oob.version)
                    if now - oob_seen[1] > 30.0:
                        oob_seen[:] = [oob.version, now]
                        oob.save()
            except Exception as e:
                print(f"{now:6.1f}s out of bounds watch failed: {type(e).__name__}: {e}", flush=True)
            people.update(now, [(i, p["pos"], p.get("health", 1.0) > 0, bool(crouching) and i == 0,
                                 steering if i == 0 else None, bool(p.get("riding")))   # (a seat is no floor)
                                for i, p in ps.items() if i not in bot_ids])
            for i, p in ps.items():
                if i not in bot_ids:
                    tr = people.tracks.get(i)
                    hub.set_player(i, name=p["name"], human=True, pos=r2(p["pos"]) if p["pos"] else None,
                                   alive=bool(p["pos"]), air=bool(tr and tr.air), trail=[r2(q) for q in tr.shown_trail()] if tr else [])
            for slot, index in mine.items():
                b = bots.setdefault(index, Roomba(index, rng))
                me = ps.get(index)
                up = bool(me and me["pos"] and me.get("health", 1.0) > 0)
                if alive.get(index) and not up:
                    info = b.track.die()
                    b.died(rec)
                    if info and not reset:
                        d = rec.died(info, "bot", now)
                        print(f"{now:6.1f}s bot {index} died: {d['cause']} (drop {d['drop']})", flush=True)
                        if d["cause"] == "fall" and T is not None:
                            teach_falls(rec, [d], T)    # the nav learns the edge now, not after the match
                alive[index] = up
                hub.set_player(index, name=me["name"] if me else f"bot {index}", human=False,
                               pos=r2(me["pos"]) if up else None, alive=up, air=b.track.air,
                               trail=[r2(q) for q in b.track.shown_trail()], trying=b.trial is not None,
                               call=b.trial["land"] if b.trial is not None and b.trial.get("called") else None)
                if not up:
                    continue
                pos = tuple(me["pos"])
                on_events(rec, b.track.update(now, pos), "bot", KIND_BOT, b)
                have = set(me.get("weapons") or [])
                for name in have - held.get(index, have):  # a weapon it did not have: picked up
                    if rec.found_weapon(name, pos, "picked"):
                        print(f"{now:6.1f}s bot {index} picked up {name}", flush=True)
                held[index] = have
                for h, name, wpos in rec.ground:           # came close to a weapon: found it
                    if h not in seen_w and math.dist(wpos, pos) < 5.0 and rec.found_weapon(name, wpos, "seen"):
                        seen_w.add(h)
                fwd, strafe, yaw, pitch, buttons = b.think(now, pos, rec, T, bounds)
                if now - dec_t.get(index, -9.0) >= 0.5 or b.why:   # the decision log: what each bot did and why
                    dec_t[index] = now
                    tr, job = b.trial, (rec.director.jobs.get(b.index) if getattr(rec, "director", None) else None)
                    dec.write(json.dumps(dict(
                        t=round(now, 2), i=b.index, pos=r2(pos), act=[round(fwd, 2), round(strafe, 2), round(yaw, 2), buttons],
                        why=b.why, target=r2(b.target) if b.target else None, wp=r2(b.way_wp) if b.way_wp else None,
                        trial=[tr.get("kind", "jump"), b.phase, bool(tr.get("called")), bool(tr.get("crouch")),
                               r2(tr["take_off"]), r2(tr["land"])] if tr else None,
                        job=job[0] if job else None, dry=getattr(b, "dry", 0), stuck=round(b.stuck_t, 1))) + chr(10))
                botctl.act(m, slot, fwd, strafe, yaw, pitch, buttons)
            notices.check()
            if getattr(rec, "director", None) is not None:
                rec.director.plan(now, {i: tuple(ps[i]["pos"]) for i in bot_ids if alive.get(i) and ps.get(i) and ps[i]["pos"]})
                for i in rec.director.new_spot_bots:     # (sent to a spot or an objective: drop the old goal, go now)
                    if i in bots and bots[i].trial is None:
                        bots[i].target = None
                rec.director.new_spot_bots.clear()
                if getattr(rec, "objectives", None) is not None:
                    rec.objectives.update(rec.players_pos, now)   # (people count too)
                line = rec.director.line(now)
                if line:
                    print(f"{now:6.1f}s {line}" + (f"; {rec.objectives.line()}" if getattr(rec, "objectives", None)
                                                    is not None else ""), flush=True)
            if T is not None and now >= next_sync:     # new usable jumps / routes: into the nav now
                next_sync = now + 2.0
                sig = [id(l) for l in usable_links(rec.links)]
                if sig != nav_sig:
                    nav_sig, t_nav = sig, time.time()
                    nav_learn(T, o.map, rec.links)
                    print(f"{now:6.1f}s nav: {len(sig)} links in use ({time.time() - t_nav:.2f} s)", flush=True)
            bot_s += len([1 for i in alive if alive[i]]) / HZ
            if tick - last_save > 60:                # the mapper is killed when the match ends
                save_rides()
                data = rec.save(bot_seconds=bot_s, human_seconds=people.seconds)
                bot_s, people.seconds, last_save = 0.0, 0.0, tick
                report(rec, data, T)
            time.sleep(max(0.0, 1.0 / HZ - (time.time() - tick)))
    finally:
        if collector is not None:
            collector.close()
        if stations is not None:
            try:
                print("stations:", stations.save(), flush=True)
            except Exception as e:
                print("stations not saved:", e, flush=True)
        try:
            if oob.version != oob_seen[0]:
                print("out of bounds:", oob.save(), flush=True)
        except Exception as e:
            print("out of bounds not saved:", e, flush=True)
        save_rides()
        data = rec.save(bot_seconds=bot_s, human_seconds=people.seconds)
        taught = len(T.stuck) - stuck0 if T is not None else 0   # falls and bump walls, learned during the run
        if taught:
            from brain.maps import get_map, save_learned
            save_learned(get_map(o.map))
        print("report", report(rec, data, T), f"({len(rec.deaths)} deaths this run, {taught} spots learned by the nav)", flush=True)
        if srv:
            srv.shutdown()


def view(o):
    """The stored data of a map in the 3D view (no game needed); the newest map by default. If
    the live view already runs (a LiDAR match), just open it."""
    import appwindow
    name, src = o.map, "scan"
    if not name:
        # the newest scan with floor in it, from matches or from the simulator (a simmed map has a lidar.json with
        # only the simulator's jumps: map_list leaves that out)
        found = []
        for m in map_list():
            for key in ("scan", "sim"):
                if key in m:
                    found.append((m[key]["updated"], m["name"], key))
        if not found:
            sys.exit("no LiDAR data yet: run a LiDAR match or the LiDAR Simulator first")
        _, name, src = max(found)
    elif "sim" in (it := next((m for m in map_list() if m["name"] == name), {})) and "scan" not in it:
        src = "sim"                                  # a map named with only a simulator scan: show that one
    path = os.path.join(ROOT, "maps", name, "lidar_sim.json") if src == "sim" else None
    hub = Hub(Recorder(name, count_run=False, path=path), "stored")
    hub.view_src = src                               # (the page's label: SIMULATOR SCAN; the window reopened shows it too)
    srv = serve(hub, getattr(o, "port", PORT))       # (--port: a second view beside a running one)
    url = f"http://127.0.0.1:{getattr(o, 'port', PORT)}/"
    if o.open:
        appwindow.open_window(url)
    if srv is None:
        return                                       # the live view is up: opened it
    print(f"showing {name}; Ctrl+C to stop", flush=True)
    try:
        while True:
            time.sleep(1)
            if getattr(hub, "yielded", False):
                print("A LiDAR match took over the 3D view (same address, the page now shows it live). "
                      "This window can close.", flush=True)
                return
    except KeyboardInterrupt:
        srv.shutdown()


def replay(o):
    """Feed a brain trace (logs/trace_*.jsonl: every bot's position) through the recorder and the
    live view, as a test without the game. --human-id makes one bot count as a person."""
    rows = sorted((json.loads(l) for l in open(o.replay)), key=lambda r: r["t"])
    T, _, _ = level_data(o.map)
    rec = Recorder(o.map, count_run=bool(o.save), T=T)
    hub = Hub(rec, "replay")
    srv = serve(hub, o.port)
    tracks, seen = {}, {}
    start, t_first = time.time(), rows[0]["t"] if rows else 0.0
    for r in rows:
        t = r["t"]
        while (time.time() - start) * o.speed < t - t_first:
            time.sleep(0.01)
        human = r["id"] == o.human_id
        who, kind = ("human", KIND_HUMAN) if human else ("bot", KIND_BOT)
        for i, last in list(seen.items()):              # no rows for 0.6 s: that bot died
            if t - last > 0.6:
                info = tracks[i].die()
                if info:
                    rec.died(info, "human" if i == o.human_id else "bot", t)
                hub.set_player(i, alive=False, pos=None, trail=[])
                del seen[i]
        tr = tracks.setdefault(r["id"], Track())
        on_events(rec, tr.update(t, r["pos"]), who, kind)
        seen[r["id"]] = t
        hub.set_player(r["id"], name=("you" if human else f"bot {r['id']}"), human=human, pos=r2(r["pos"]), alive=True,
                       air=tr.air, trail=[r2(q) for q in tr.shown_trail()])
    hub.note = "replay finished"
    if o.save:
        print("report", report(rec, rec.save(), T), flush=True)
    print(f"replayed {len(rows)} rows: {len(rec.events)} cells, {len(rec.links)} links, {len(rec.deaths)} deaths", flush=True)
    if srv and o.hold:
        time.sleep(o.hold)
    if srv:
        srv.shutdown()


def selftest():
    """Tracker: a ramp is ground, a jump lands as one link with its arc, a fall that ends alive
    is set in stone, a fall that kills leaves no trail; Roomba: explores and jumps where safe;
    people's jumps merge; the view's JSON is valid and served."""
    g, dt = 5.7, 1 / HZ
    # 1. a ramp at 1.35 units/s up (CE base ramp at run speed), with read-clock jitter
    rng = random.Random(4)
    tr, t, evs = Track(), 0.0, []
    for k in range(90):
        t += dt + rng.uniform(-0.008, 0.008)
        evs += tr.update(t, (k * 0.075, 0.0, k * 0.045))
    assert not any(e == "air" for e, _ in evs), "a ramp counted as air"
    # 2. a running jump across a gap: 2 units/s, up at 3 units/s, landing 0.2 lower
    tr, evs, t = Track(), [], 0.0
    path = [(x * 0.066, 0.0, 0.0) for x in range(30)]
    x0, t_air = path[-1][0], 0.0
    while True:
        t_air += dt
        z = 3.0 * t_air - 0.5 * g * t_air ** 2
        if z < -0.2:
            break
        path.append((x0 + 2.0 * t_air, 0.0, z))
    landed_at = len(path)
    after = [(path[-1][0] + 0.066 * k, 0.0, -0.2) for k in range(1, int(HZ * (CONFIRM_S + 1)))]
    path += after
    when = None
    for k, p in enumerate(path):
        e = tr.update(k * dt, p)
        if any(x == "land" for x, _ in e) and when is None:
            when = k * dt - landed_at * dt
        evs += e
    lands = [x for e, x in evs if e == "land"]
    assert len(lands) == 1, f"{len(lands)} landings for one jump"
    assert CONFIRM_S <= when <= CONFIRM_S + 0.6, f"the landing counted {when:.2f} s after touching down"
    L = lands[0]
    assert abs(L["apex"] - 9 / (2 * g)) < 0.12 and L["trail"], L
    rec = Recorder("_selftest", count_run=False)
    rec.links = []
    link = rec.landed(L, "human")
    assert link and link["human"] == 1 and math.dist(link["take_off"][:2], L["takeoff"][:2]) < 0.01
    assert rec.landed(L, "human") is link and link["human"] == 2, "the same jump twice is one link"
    assert any(k[3] == KIND_AIR for k in rec.walk), "a landed jump's trail is set in stone"
    # 2b. the same jump, then a slip off a slope and death 2 s after landing: it does not count
    tr, rec6 = Track(), Recorder("_selftest", count_run=False)
    rec6.links = []
    for k, p in enumerate(path[:landed_at + int(HZ * 2)]):
        on_events(rec6, tr.update(k * dt, p), "human", KIND_HUMAN)
    info = tr.die()
    assert not rec6.links and not any(k[3] == KIND_AIR for k in rec6.walk), "a jump that died 2 s after landing counted"
    assert info["landings_lost"] == 1, info
    # 3. walking off a 6-unit ledge and dying in the air: no trail, a fall
    tr, rec2 = Track(), Recorder("_selftest", count_run=False)
    rec2.links, t = [], 0.0
    for k in range(40):
        on_events(rec2, tr.update(k * dt, (k * 0.066, 0.0, 0.0)), "bot", KIND_BOT)
    for k in range(1, 46):                              # 1.5 s: about 6.4 units down
        tt = k * dt
        on_events(rec2, tr.update(40 * dt + tt, (40 * 0.066 + 2 * tt, 0.0, -0.5 * g * tt * tt)), "bot", KIND_BOT)
    info = tr.die()
    assert info and info["cause"] == "fall" and info["drop"] > 2.0 and info["in_air"], info
    assert not any(k[3] == KIND_AIR for k in rec2.walk), "a deadly fall left a trail"
    # 4. a Roomba on open flat ground explores and jumps
    rec3 = Recorder("_selftest", count_run=False)
    rec3.links, rec3.cover, rec3.fall_grid = [], set(), {}
    b, pos, jumps = Roomba(1, random.Random(3)), [0.0, 0.0, 0.0], 0
    for k in range(HZ * 20):
        fwd, strafe, yaw, _, buttons = b.think(k / HZ, tuple(pos), rec3, None, (-50, -50, 50, 50))
        on_events(rec3, b.track.update(k / HZ, tuple(pos)), "bot", KIND_BOT, b)
        jumps += bool(buttons & BTN_JUMP)
        pos[0] += math.cos(yaw) * fwd * 0.1
        pos[1] += math.sin(yaw) * fwd * 0.1
    assert len(rec3.cover) > 30, f"explored only {len(rec3.cover)} cells"
    assert jumps >= 1, "never jumped"
    # 4b. a wall that stops it (no level data: Rat's Nest): the position only jitters a hundredth a tick. Within 5 s it
    # gives the goal up and the next goal is not the way of the wall
    w, wall_x, t0 = Roomba(2, random.Random(5)), 3.0, 0.0
    wp, goals = [0.0, 0.0, 0.0], []
    w.target, w.target_t = (10.0, 0.0, 0.0), 0.0
    for k in range(HZ * 6):
        fwd, strafe, yaw, _, _ = w.think(k / HZ, tuple(wp), rec3, None, (-50, -50, 50, 50))
        wp[0] = min(wall_x, wp[0] + math.cos(yaw) * fwd * 0.1) - 0.012 * (k % 2)   # pressed on x = 3: jitter
        wp[1] += 0.0 if wp[0] >= wall_x - 0.05 else math.sin(yaw) * fwd * 0.1
        goals.append(w.target)
    assert w.blocked is not None, "pushed on a wall 5 s and never gave the goal up"
    assert w.target[0] < 10.0 or abs(w.target[1]) > 3.0, f"the next goal {w.target} is the way of the wall again"
    # 5. a known fall spot stops a Roomba walking at it
    rec3.add_fall((pos[0] + math.cos(yaw) * 0.6, pos[1] + math.sin(yaw) * 0.6, 0.0))
    b.target, b.target_t = (pos[0] + math.cos(yaw) * 10, pos[1] + math.sin(yaw) * 10, 0.0), 20 * HZ
    assert b.think(21.0, tuple(pos), rec3, None, None)[0] == 0.0, "walked at a known fall"
    # 5b. crouch: a person crouch-walks 2 units -> crouch floor, a crouch route after 5 s alive, a
    # Roomba crouches there, and the route is the same walked the other way
    tr, rec7 = Track(), Recorder("_selftest", count_run=False)
    rec7.links, rec7.crouch_cells = [], set()
    walk = [(k * 0.04, 5.0, 0.0, 30 <= k < 80) for k in range(int(HZ * (CONFIRM_S + 4)))]   # crouched for 50 ticks
    for k, (x, y, z, c) in enumerate(walk):
        on_events(rec7, tr.update(k * dt, (x, y, z), c), "human", KIND_HUMAN)
    crawls = [l for l in rec7.links if l.get("kind") == "crouch"]
    assert len(crawls) == 1 and crawls[0]["human"] == 1, rec7.links
    assert any(k[3] == KIND_CROUCH for k in rec7.walk), "no crouch floor"
    rb = Roomba(9, random.Random(9))
    rb.target, rb.target_t = (3.0, 5.0, 0.0), 0.0
    assert rb.think(0.1, (1.8, 5.0, 0.0), rec7, None, None)[4] & BTN_CROUCH, "a Roomba did not crouch on crouch floor"
    back = {"start": crawls[0]["land"], "end": crawls[0]["take_off"], "path": crawls[0]["path"][::-1]}
    assert rec7.crawled(back, "bot") is crawls[0] and crawls[0]["bot_ok"] == 1, "the way back is another route"
    # 5c. a weapon 3 units away: the Roomba walks to it, presses Use on it; found_weapon merges
    rec8 = Recorder("_selftest", count_run=False)
    rec8.links, rec8.weapons, rec8.cover, rec8.fall_grid = [], [], set(), {}
    rec8.ground = [(77, "battle_rifle", (3.0, 0.0, 0.0))]
    rb, p8, used = Roomba(4, random.Random(4)), [0.0, 0.0, 0.0], False
    for k in range(HZ * 4):
        fwd, _, yaw, _, buttons = rb.think(k / HZ, tuple(p8), rec8, None, (-50, -50, 50, 50))
        used = used or bool(buttons & BTN_ACTION)
        p8[0] += math.cos(yaw) * fwd * 0.06
        p8[1] += math.sin(yaw) * fwd * 0.06
    assert used and math.dist(p8[:2], (3.0, 0.0)) < 1.0, ("did not go for the weapon", p8, used)
    rec8.found_weapon("battle_rifle", (3.0, 0.0, 0.0), "seen")
    rec8.found_weapon("battle_rifle", (3.3, 0.2, 0.0), "picked")
    assert len(rec8.weapons) == 1 and rec8.weapons[0]["picked"] == 1, rec8.weapons
    assert rec8.found_weapon("unknown", (0, 0, 0), "seen") is None
    # 5d. a person pushed off a ledge while idle (not steering) does not get a jump; steering does
    hw = HumanWatch("_selftest", Recorder("_selftest", count_run=False))
    hw.rec.links = []
    for k, p in enumerate(path):
        hw.update(k * dt, [(0, p, True, False, False)])     # the jump path from 2., hands off
    assert not hw.rec.links and hw.skipped == 1, ("a push counted as his jump", hw.rec.links)
    hw2 = HumanWatch("_selftest", Recorder("_selftest", count_run=False))
    hw2.rec.links = []
    for k, p in enumerate(path):
        hw2.update(k * dt, [(0, p, True, False, True)])
    assert len(hw2.rec.links) == 1, "a steered jump did not count"
    hw3 = HumanWatch("_selftest", Recorder("_selftest", count_run=False))
    hw3.rec.links = []
    for k, p in enumerate(path):
        hw3.update(k * dt, [(0, p, True, False, True, True)])   # the same arc in a vehicle's seat
    assert not hw3.rec.links and not hw3.rec.deaths, "a vehicle bump counted as a jump of theirs"
    # 5e. two-way / one-way: a level gap is two-way, a 3-unit drop one-way; the jump back merges
    from brain.terrain import jump_ways
    gap = dict(take_off=[0, 0, 0], land=[2.5, 0, 0.1])
    drop = dict(take_off=[0, 0, 3], land=[2.5, 0, 0])
    assert jump_ways(gap) == "two-way" and jump_ways(drop) == "one-way", (jump_ways(gap), jump_ways(drop))
    assert jump_ways(dict(drop, back=1)) == "two-way", "a drop somebody jumped back up is two-way"
    # ... an arc 5 u over both ends is a launch (Spire link 218, live), a lift ride up to its landing keeps its way
    assert jump_ways(dict(gap, apex=5.0)) == "one-way", "a launcher's arc read as a two-way jump"
    assert jump_ways(dict(take_off=[0, 0, 0], land=[1.0, 0, 0.5], apex=0.6)) == "two-way", "a plain hop read as a launch"
    rec9 = Recorder("_selftest", count_run=False)
    rec9.links = []
    fwd = dict(takeoff=(0.0, 0.0, 0.0), landing=(3.0, 0.0, 0.0), apex=0.8, air_s=0.8, runup=None, trail=[(1.5, 0.0, 0.8)])
    rev = dict(takeoff=(3.0, 0.0, 0.0), landing=(0.0, 0.0, 0.0), apex=0.8, air_s=0.8, runup=None, trail=[(1.5, 0.0, 0.8)])
    l1, l2 = rec9.landed(fwd, "human"), rec9.landed(rev, "human")
    assert l1 is l2 and len(rec9.links) == 1 and l1["back"] == 1 and l1["human"] == 2, rec9.links
    assert rec9.landed(fwd, "bot") is None and l1["human"] == 2, "a bot's uncalled landing counted"
    # 5f. a called jump: on the call it becomes a link every bot may use; 0.7 off the call it
    # does not count and is remembered as missed
    from brain.maps import usable_links
    rec10 = Recorder("_selftest", count_run=False)
    rec10.links = []
    for off, made in ((0.2, True), (0.7, False)):
        call = dict(kind="jump", take_off=[0.0, 0.0, 0.0], land=[2.0, 0.0, 0.5], runup=None, called=True, human=0,
                    bot_ok=0, bot_fail=0, _key=(0, 0, 4, int(off * 10)))
        rb = Roomba(7, random.Random(7))
        rb.trial, rb.phase = call, "fly"
        rb.landed(dict(landing=(2.0 + off, 0.0, 0.5)), None, rec10)
        assert any(l is call for l in rec10.links) == made, (off, rec10.links)
    assert rec10.calls == dict(made=1, missed=1) and list(rec10.failed_calls.values()) == [1], (rec10.calls, rec10.failed_calls)
    assert usable_links(rec10.links) == rec10.links and "_key" not in rec10.links[0], "a made call is not usable"
    # 6. a lift: 4 units straight up at 2.5 units/s, then off at the top -> no floor column, one link
    tr, rec4 = Track(), Recorder("_selftest", count_run=False)
    rec4.links, t = [], 0.0
    path = [(0.0, k * 0.05, 0.0) for k in range(20)] + [(0.0, 1.0, 2.5 * k * dt) for k in range(1, 49)]
    path += [(0.0, 1.0 + min(k, 29) * 0.066, path[-1][2]) for k in range(1, int(HZ * (CONFIRM_S + 1)))]
    for k, p in enumerate(path):
        on_events(rec4, tr.update(k * dt, p), "human", KIND_BOT)
    column = [k for k in rec4.walk if k[3] == KIND_BOT and 0.5 < k[2] * ZSTEP < 3.5]
    assert not column, f"the lift ride marked {len(column)} floor cells"
    assert len(rec4.links) == 1 and rec4.links[0]["land"][2] > 3.5, rec4.links
    # 7. notices: a new person's jump once, bots confirming it once, old jumps quiet
    sent = []
    rec5 = Recorder("_selftest", count_run=False)
    rec5.links = [dict(take_off=[0, 0, 0], land=[3, 0, 0], human=1, bot_ok=0, bot_fail=0)]
    nt = Notices(rec5, lambda title, line: sent.append(title))
    nt.check()
    rec5.links.append(dict(take_off=[5, 0, 0], land=[8, 0, 0], human=1, bot_ok=1, bot_fail=0))
    nt.check(); nt.check()
    rec5.links[1]["bot_ok"] = 2
    nt.check(); nt.check()
    assert sent == ["JUMP LEARNED", "BOTS DID YOUR JUMP"], sent
    # 9. bumping into a wall (the player's rule): pushing, alone, stopped and not up onto it ->
    # a red wall and a cover spot; a lip the bot jumps up onto is not a wall, nor a player in
    # the way
    def bump_run(lip=False, crowd=False):
        r = Recorder("_selftest", count_run=False)
        r.links, r.cover, r.fall_grid, r.cover_spots, r.walk = [], set(), {}, {}, {}
        rb, p, up = Roomba(5, random.Random(5)), [0.0, 0.0, 0.0], False
        rb.target, rb.target_t = (10.0, 0.0, 0.0), 0.0
        for k in range(HZ * 4):
            t = k / HZ
            r.players_pos = [tuple(p)] + ([(p[0] + 0.5, p[1], p[2])] if crowd else [])
            fwd, strafe, yaw, _, buttons = rb.think(t, tuple(p), r, None, None)
            rb.track.update(t, tuple(p))
            up = up or (lip and bool(buttons & BTN_JUMP) and p[0] >= 1.7)
            p[0] += (math.cos(yaw) * fwd - math.sin(yaw) * strafe) * 0.1
            p[1] += (math.sin(yaw) * fwd + math.cos(yaw) * strafe) * 0.1
            if up:
                p[2] = 0.3                                   # jumped up onto the lip
            else:
                p[0] = min(p[0], 1.75)                       # its face (or the wall)
        return [k for k in r.walk if k[3] == KIND_WALL], r
    walls, rw = bump_run()
    assert walls and all(1.9 <= k[0] * CELL <= 2.3 for k in walls) and rw.cover_spots, ("bumping a wall did not paint it", walls)
    assert not bump_run(lip=True)[0], "a lip the bot jumped onto counted as a wall"
    assert not bump_run(crowd=True)[0], "a player in the way counted as a wall"
    # 10. F6 route: walk 2 units, jump up onto a 1-unit ledge, crouch-walk on; F6 at the end and
    # 5 s alive saves a one-way route: a jump flag at the real take-off, crouch flags; dying in
    # those 5 s loses it
    from brain.terrain import ROUTE_JUMP, ROUTE_CROUCH
    samples, tt, x = [], 0.0, 0.0
    for k in range(30):
        tt, x = tt + dt, x + 0.066
        samples.append((tt, (x, 0.0, 0.0), False))
    ta, x0 = 0.0, x
    while True:
        ta += dt
        z = 4.0 * ta - 0.5 * g * ta * ta
        if ta > 0.4 and z <= 1.0:
            break
        tt += dt
        samples.append((tt, (x0 + 2.0 * ta, 0.0, z), False))
    x = x0 + 2.0 * ta
    for k in range(40):
        tt, x = tt + dt, x + 0.04
        samples.append((tt, (x, 0.0, 1.0), True))
    for k in range(20):
        tt += dt
        samples.append((tt, (x, 0.0, 1.0), False))
    sent, recR = [], Recorder("_selftest", count_run=False)
    recR.links = []
    def record(die_at=None):
        pr = PathRec(recR, lambda title, line: sent.append(title))
        pr.key(0.0)
        for t, p, c in samples:
            pr.update(t, p, True, c)
        pr.key(tt)
        for k in range(1, int(HZ * (CONFIRM_S + 0.5))):
            dead = die_at is not None and k * dt >= die_at
            pr.update(tt + k * dt, None if dead else samples[-1][1], not dead)
    record()
    routes = [l for l in recR.links if l.get("kind") == "route"]
    assert sent == ["RECORDING PATH", "PATH ENDED", "PATH SAVED"] and len(routes) == 1, (sent, recR.links)
    pth = routes[0]["path"]
    jumps_at = [q for q in pth if q[3] & ROUTE_JUMP]
    assert len(jumps_at) == 1 and abs(jumps_at[0][0] - x0) < 0.15 and jumps_at[0][2] < 0.05, ("the take-off", jumps_at, x0)
    assert any(q[3] & ROUTE_CROUCH for q in pth) and not pth[0][3] & ROUTE_CROUCH and routes[0]["land"][2] > 0.9, pth
    record(die_at=2.0)
    assert sent[-1] == "PATH LOST" and len([l for l in recR.links if l.get("kind") == "route"]) == 1, sent
    # 11. a Roomba takes the route: jumps at its take-off, crouches where it was crouched, waits
    # out the 5 s at its end and scores it
    route = routes[0]
    rb, p, jumped, crouched = Roomba(6, random.Random(6)), [0.0, 0.0, 0.0], None, False
    rb.trial, rb.phase, rb.trial_t, rb.crawl_path, rb.trial_s = route, "go", 0.0, None, 60.0
    for k in range(HZ * 14):
        fwd, strafe, yaw, _, buttons = rb.think(k / HZ, tuple(p), recR, None, None)
        if buttons & BTN_JUMP and jumped is None:
            jumped = p[0]
        crouched |= bool(buttons & BTN_CROUCH)
        p[0] += math.cos(yaw) * fwd * 0.066
        p[1] += math.sin(yaw) * fwd * 0.066
        if jumped is None:
            p[0] = min(p[0], x0 + 0.2)                       # the ledge's face, until it jumps
        elif p[0] > x0 + 1.0:
            p[2] = 1.0
        if rb.trial is None:
            break
    assert jumped is not None and abs(jumped - x0) < 0.45 and crouched and route["bot_ok"] == 1, (jumped, x0, crouched, route["bot_ok"])
    # 8. the view: JSON serialisable, page and data served
    hub = Hub(rec, "replay")
    hub.set_player(0, name="you", human=True, pos=[0, 0, 0], alive=True, air=False, trail=[])
    json.dumps(hub.live(0)); json.dumps(hub.stored_view())
    srv = serve(hub, PORT + 50)
    if srv:
        import urllib.request
        page = urllib.request.urlopen(f"http://127.0.0.1:{PORT + 50}/").read()
        live = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT + 50}/live?since=0").read())
        maps = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT + 50}/maps").read())
        other = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT + 50}/map?name=beavercreek").read())
        art = os.path.exists(os.path.join(ART, "games", "h2a.png"))     # (made from MCC by tools/map_art.py)
        logo = urllib.request.urlopen(f"http://127.0.0.1:{PORT + 50}/art/games/h2a.png").read() if art else b"\x89PNG"
        thumb = urllib.request.urlopen(f"http://127.0.0.1:{PORT + 50}/art/maps/h2a_ca_lockout.jpg").read() if art \
            else b"\xff\xd8"
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT + 50}/map?name=..%5Cbrain")
            bad = "served"
        except urllib.error.HTTPError as e:
            bad = e.code
        try:                                         # Remove without the view's header: refused before anything
            urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT + 50}/remove?name=beavercreek", method="POST"))
            nohead = "removed"
        except urllib.error.HTTPError as e:
            nohead = e.code
        srv.shutdown()
        assert nohead == 403, f"a remove without the header was {nohead}"
        assert b"<canvas" in page and live["players"][0]["human"] and live["links"], "view not served"
        games = {m["game"] for m in maps["maps"]}
        assert len(maps["maps"]) > 100 and games == {"ce", "h2", "h2a", "h3", "odst", "reach", "h4"}, ("map list", len(maps["maps"]), games)
        assert other["browse"] and other["map"] == "beavercreek" and other["features"], "another map's scan not served"
        assert bad == 404, f"a bad map name was {bad}"
        titles = {m["name"]: m["title"] for m in maps["maps"]}
        assert other["title"] == "Battle Creek" and titles["h2a_ca_lockout"] == "Lockdown" and titles["putput"] == "Chiron TL-34", \
            "real map names missing (python -I tools/map_art.py)"
        assert logo[:4] == b"\x89PNG" and thumb[:2] == b"\xff\xd8", "logo or map picture not served"
        assert sum(m["mcc"] for m in maps["maps"]) >= 119, "maps without their MCC name"
    # 9. Remove (maps list): refused without the header, for a bad name, for the map being scanned; the
    #    files go to backups/lidar; removing the simulator's scan keeps people's jumps, drops its own
    import tempfile
    import types
    h9 = types.SimpleNamespace(rec=types.SimpleNamespace(map="beavercreek"), mode="live")
    assert remove_refused(h9, "beavercreek", "scan", None) == 403
    assert remove_refused(h9, "..\\brain", "scan", "remove") == 404 and remove_refused(h9, "bloodgulch", "x", "remove") == 404
    assert remove_refused(h9, "beavercreek", "scan", "remove") == 409 and remove_refused(h9, "bloodgulch", "sim", "remove") is None
    h9.mode = "stored"
    assert remove_refused(h9, "beavercreek", "scan", "remove") is None
    with tempfile.TemporaryDirectory() as tmp:
        d9 = os.path.join(tmp, "maps", "x")
        os.makedirs(d9)
        mine = dict(take_off=[0, 0, 0], land=[1, 0, 0], human=1, sim_ok=2)
        json.dump(dict(walk=[[0, 0, 0, KIND_BOT, 1]], links=[mine, dict(take_off=[0, 0, 0], land=[2, 0, 0], found_by="sim", sim_ok=1)]),
                  open(os.path.join(d9, "lidar.json"), "w"))
        json.dump(dict(walk=[[0, 0, 0, KIND_BOT, 1]]), open(os.path.join(d9, "lidar_sim.json"), "w"))
        kept = remove_scan("x", "sim", tmp)
        left = load(os.path.join(d9, "lidar.json"))
        assert len(kept) == 2 and all(os.path.exists(k) for k in kept) and not os.path.exists(os.path.join(d9, "lidar_sim.json"))
        assert left["links"] == [dict(mine, sim_ok=0, sim_fail=0)] and left["walk"], left
        kept2 = remove_scan("x", "scan", tmp)
        assert len(kept2) == 1 and kept2[0] not in kept and not os.path.exists(os.path.join(d9, "lidar.json"))
        assert load(kept2[0])["links"] == left["links"] and len(load(kept[1])["links"]) == 2, "a backup was overwritten"
    print("lidar self-check OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument("map", nargs="?")
        ap.add_argument("seconds", type=float, nargs="?", default=300)
        ap.add_argument("--game", default="h2a")
        ap.add_argument("--view", action="store_true")
        ap.add_argument("--open", action="store_true")
        ap.add_argument("--replay")
        ap.add_argument("--speed", type=float, default=4.0)
        ap.add_argument("--human-id", type=int, default=-1)
        ap.add_argument("--save", action="store_true")
        ap.add_argument("--hold", type=float, default=0.0, help="replay: keep the view up this long after")
        ap.add_argument("--port", type=int, default=PORT)
        o = ap.parse_args()
        if o.replay:
            replay(o)
        elif o.view:
            view(o)
        elif not o.map:
            ap.error("map required")
        else:
            main(o)
