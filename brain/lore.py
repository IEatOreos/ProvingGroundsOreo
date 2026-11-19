"""(custom, Nov 19) Map memory: what a layout taught over many matches, for Legendary and up (profiles.map_memory:
fixed Legendary, Mythic, Blind, Tactician and Demon; Scaling and Heroic down play as before). Owner: "Danger map,
Spawns, Movement facts ... only give it to legendary and up".

One file a layout, maps/<layout>/lore.json (this PC's own, as nav_learned.json: never committed):

  "matches"  the match stamps whose facts are in here (a recording is counted once: tools/lore_seed.py and the live
             match share them); "kill_matches" those that recorded their kills (Reach, since Nov 15)
  "kills"    [[victim x, y, z, killer x, y, z], ...]: every kill the game credited to another player, where each stood
             (tools/kill_record.py rows; the newest KILLS_MAX kept)
  "spawns"   {game mode: [[x, y, z, team], ...]}: where players came back after dying (the newest SPAWNS_MAX a mode;
             team -1: not known)
  "jumps"    {"x,y": [made, short]}: a bot's planned jump (by its take-off, Bot.judge_jump) or a people's route (by its
             first point, Bot.judge_route), landed or short

What it answers:
  shooters(p)   the spots men shot from when people died near p: where to look first walking through (Bot.danger_look)
  lanes()       where the most people died: ways round them when one is about as short (Terrain.nav avoid)
  spawn_spots   where people come back in this mode: what to watch after a kill (Bot.spawn_look)
  jump_bad(k)   a jump bots keep falling short of: another way from the start (Bot.jump_blocked)

Danger facts count once DANGER_MATCHES matches with kills are in (a match or two is where one player happened to stand); spawns
and jumps from their own counts."""
import json
import math
import os
import threading

from .core import Vec

FILE = "lore.json"
KILLS_MAX, SPAWNS_MAX = 6000, 3000
DANGER_MATCHES = 3        # matches recorded before the danger facts are trusted
NEAR_R, NEAR_DZ = 6.0, 2.5   # u: deaths this near a spot (and this near its height) are deaths "here"
SPOT_CELL = 2.0           # u: shooting spots are counted in cells this size
SPOT_MIN = 3              # kills from a cell before it is a known shooting spot
LANE_CELL = 4.0           # u: deaths are counted in cells this size for lanes
LANE_MIN, LANE_SHARE, LANES = 8, 0.02, 10   # deaths a lane needs (and this share of all of them); at most this many
LANE_R = 2.5              # u: the disk round a lane's middle a way round goes past
SPAWN_CELL, SPAWN_MIN = 3.0, 3   # u, respawns a cell needs to be a spawn spot
JUMP_SHORT, JUMP_RATIO = 3, 2.0  # a jump short this often and this many times more than made: left


def _cell(x, y, z, c):
    return (math.floor(x / c), math.floor(y / c), math.floor(z / 3.0))


class Lore:
    def __init__(s, folder):
        s.path = os.path.join(folder, FILE) if folder else None
        s.matches, s.kill_matches, s.kills, s.spawns, s.jumps = [], [], [], {}, {}
        s.dirty = False
        s.lock = threading.Lock()
        s._cache = {}
        if s.path and os.path.exists(s.path):
            try:
                with open(s.path, encoding="utf-8") as f:
                    d = json.load(f)
                s.matches = [str(m) for m in d.get("matches", [])]
                s.kill_matches = [str(m) for m in d.get("kill_matches", [])]
                s.kills = [list(map(float, k[:6])) for k in d.get("kills", []) if len(k) >= 6]
                s.spawns = {str(m): [list(map(float, p[:3])) + [int(p[3]) if len(p) > 3 else -1] for p in ps
                                     if len(p) >= 3] for m, ps in d.get("spawns", {}).items()}
                s.jumps = {str(k): [int(v[0]), int(v[1])] for k, v in d.get("jumps", {}).items()}
            except (OSError, ValueError, TypeError, IndexError):
                pass        # (a broken file: start over; it is written whole again at the next save)

    # --- learning
    def match(s, stamp):
        """This match's facts go in from now (once per stamp); False when they are in already."""
        if not stamp or stamp in s.matches:
            return False
        with s.lock:
            s.matches.append(stamp)
            s.dirty = True
        return True

    def kill_match(s, stamp):
        """This match records its kills (Reach, kill_record): it counts toward DANGER_MATCHES."""
        if stamp and stamp not in s.kill_matches:
            with s.lock:
                s.kill_matches.append(stamp)
                s.dirty = True
                s._cache.clear()

    def add_kill(s, vp, kp):
        if vp is None or kp is None:
            return
        with s.lock:
            s.kills.append([round(float(c), 2) for c in (*vp, *kp)])
            del s.kills[:-KILLS_MAX]
            s.dirty = True
            s._cache.clear()

    def add_spawn(s, mode, p, team=None):
        with s.lock:
            ps = s.spawns.setdefault(str(mode or "any"), [])
            ps.append([round(float(c), 2) for c in p[:3]] + [int(team) if team is not None else -1])
            del ps[:-SPAWNS_MAX]
            s.dirty = True
            for k in [k for k in s._cache if k[0] == "spawns"]:
                del s._cache[k]

    def add_jump(s, key, made):
        k = f"{key[0]:.1f},{key[1]:.1f}"
        with s.lock:
            v = s.jumps.setdefault(k, [0, 0])
            v[0 if made else 1] += 1
            s.dirty = True

    def save(s):
        if not (s.dirty and s.path and os.path.isdir(os.path.dirname(s.path))):
            return
        with s.lock:
            data = dict(v=1, matches=list(s.matches), kill_matches=list(s.kill_matches), kills=list(s.kills),
                        spawns={m: list(ps) for m, ps in s.spawns.items()}, jumps=dict(s.jumps))
            s.dirty = False
        tmp = s.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        os.replace(tmp, s.path)

    # --- what it answers
    def trusted(s):
        return len(s.kill_matches) >= DANGER_MATCHES

    def shooters(s, p):
        """[(spot, kills), ...] most first: the cells men shot from (SPOT_MIN kills or more) when people died within
        NEAR_R of p; [] until trusted. Cached by p's own 2 u cell."""
        if not s.trusted():
            return []
        key = ("shoot",) + _cell(p.x, p.y, p.z, SPOT_CELL)
        out = s._cache.get(key)
        if out is None:
            cells = {}
            for vx, vy, vz, kx, ky, kz in s.kills:
                if abs(vz - p.z) < NEAR_DZ and math.hypot(vx - p.x, vy - p.y) < NEAR_R:
                    c = _cell(kx, ky, kz, SPOT_CELL)
                    n, sx, sy, sz = cells.get(c, (0, 0.0, 0.0, 0.0))
                    cells[c] = (n + 1, sx + kx, sy + ky, sz + kz)
            out = sorted(((Vec(sx / n, sy / n, sz / n), n) for n, sx, sy, sz in cells.values() if n >= SPOT_MIN),
                         key=lambda sn: -sn[1])
            s._cache[key] = out
        return out

    def lanes(s):
        """((x, y, z, LANE_R), ...): the middles of the cells where the most people died (LANE_MIN and LANE_SHARE of all
        deaths at least, LANES at most); () until trusted. Rounded, so the route fields are cached by them."""
        if not s.trusted():
            return ()
        out = s._cache.get(("lanes",))
        if out is None:
            cells = {}
            for vx, vy, vz, *_ in s.kills:
                c = _cell(vx, vy, vz, LANE_CELL)
                n, sx, sy, sz = cells.get(c, (0, 0.0, 0.0, 0.0))
                cells[c] = (n + 1, sx + vx, sy + vy, sz + vz)
            need = max(LANE_MIN, LANE_SHARE * len(s.kills))
            top = sorted((v for v in cells.values() if v[0] >= need), key=lambda v: -v[0])[:LANES]
            out = tuple((round(sx / n, 1), round(sy / n, 1), round(sz / n, 1), LANE_R) for n, sx, sy, sz in top)
            s._cache[("lanes",)] = out
        return out

    def spawn_spots(s, mode, not_team=None):
        """[(spot, respawns), ...] most first: cells SPAWN_MIN respawns or more in this mode (else in every mode), of
        players not on not_team (a respawn with no team known counts for everyone)."""
        m = str(mode or "any")
        key = ("spawns", m, not_team)
        out = s._cache.get(key)
        if out is None:
            pts = s.spawns.get(m) or [p for ps in s.spawns.values() for p in ps]
            cells = {}
            for x, y, z, *t in pts:
                if not_team is not None and t and t[0] == not_team:
                    continue
                c = _cell(x, y, z, SPAWN_CELL)
                n, sx, sy, sz = cells.get(c, (0, 0.0, 0.0, 0.0))
                cells[c] = (n + 1, sx + x, sy + y, sz + z)
            out = sorted(((Vec(sx / n, sy / n, sz / n), n) for n, sx, sy, sz in cells.values() if n >= SPAWN_MIN),
                         key=lambda sn: -sn[1])
            s._cache[key] = out
        return out

    def jump_bad(s, key):
        """A jump (by its take-off, rounded to 0.1 u) short JUMP_SHORT times or more and JUMP_RATIO times as often as
        made."""
        v = s.jumps.get(f"{key[0]:.1f},{key[1]:.1f}")
        return v is not None and v[1] >= JUMP_SHORT and v[1] >= JUMP_RATIO * v[0]


_BOOKS = {}


def folder_of(name):
    from .maps import ROOT
    return os.path.join(ROOT, name)


def book(m):
    """The layout's Lore (m: a map dict, or its name), loaded once."""
    name = m if isinstance(m, str) else (m or {}).get("name")
    if not name:
        return Lore(None)
    if name not in _BOOKS:
        _BOOKS[name] = Lore(folder_of(name))
    return _BOOKS[name]


def save(m):
    name = m if isinstance(m, str) else (m or {}).get("name")
    if name in _BOOKS:
        _BOOKS[name].save()
