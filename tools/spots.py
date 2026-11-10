"""Spots the bots use, edited by hand in the LiDAR view (custom, Nov 8: "can we make a tool to where I can implement Hot
zones, Patrol Areas, and other spots the bots use so I dont have to have you do it for me all the time?").

The view (tools/lidar_view.html, Edit spots) reads and writes three kinds of spot, each in the file the brain reads it
from (brain/maps.py load_map), so an edit is what the next match loads:
  hot     owner power positions: positions.json rows marked "owner" (as tools/power_positions.py --add makes them),
          score 1.0, over every computed row: Slayer anchors hold them and rotate between them (director.slayer_slots).
          The computed rows are shown, kept and not edited here; one within 1 u of an owner spot gives way to it.
  patrol  infantry patrol points: infantry_patrols.json {name: [x, y, z]} or {name: {pos, team}}; up to three free
          bots go to one nobody of the team has stood near for 25 s (director.infantry_patrol_orders; not in Invasion).
  hold    team holds: callouts.json "holds" red / blue, the team's safe spots: a CTF carrier waits at one (the 2nd on)
          while its own flag must come home first (director.carry_point), the Oddball carrier takes the one farthest
          from the enemies, Firefight falls back to them, and a map with no power positions holds them instead
          (director.positions). Each team keeps at least one. A Forge layout's own callouts are made again when its
          layout changes (tools/variant_strategy.py), and its holds with them.
  ride    gravity lifts and man cannons (custom, Nov 9): owner_rides.json {rides: [{name, kind lift | cannon, take_off,
          land}]} in the folder of the map or layout shown (brain/maps.py owner_rides): a one-way people's ride link
          from where you step in to where it puts you down, and a lift / launcher marker at the pad the map lacks, so bots
          ride it as they ride the ones people recorded. Save warns of an end the nav cannot use (the nav skips it).
  lane    CTF attack lanes (custom, Nov 9): callouts.json "lanes" [[x, y, z]], waypoints both teams pass through on
          their way to the enemy flag and a carrier on its way home (director.pick_route: each lane is a one-stop
          route, the one with the least recent threat), and split attacks' pushers stand on them. None at all is
          allowed: bots then run the shortest way.
  sneak   sneak routes (custom, Nov 9): callouts.json "sneak" {red: [[[x, y, z], ...]], blue: [...]}, each a route of
          waypoints in order from the team's own base to the enemy flag; the carrier runs it backwards home. Skilled
          bots prefer them (director.pick_route: routes skill squared). Each needs at least two points.
          A Forge layout's lanes and sneak routes are made again with its callouts, as its holds are.
Every save keeps the files it replaces in backups/spots/ and writes each one whole (a match may read it any time).

usage: python -I spots.py --selftest
"""
import json
import math
import os
import re
import shutil
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
MAPS = os.path.join(ROOT, "maps")
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MAP_NAME = re.compile(r"[a-z0-9_]+(/variants/v[0-9a-f]{8})?")   # tools/lidar.py MAP_NAME: a map or a layout of one
TEAMS = ("red", "blue")
MAX_HOT, MAX_PATROL, MAX_HOLD, MAX_RIDE = 32, 32, 16, 32
MAX_LANE, MAX_SNEAK, MAX_SNEAK_POINTS = 12, 8, 32   # lanes; sneak routes a team; waypoints a route
RIDE_KINDS = ("lift", "cannon")
NEAR = 1.0                        # a computed power position this close to an owner spot gives way (power_positions --add)
LIMIT = 20000.0                   # no map reaches this far from its origin
LEVEL_POINTS = 200000             # the level floor sent to the view at most (its cells thinned to fit)
_LOCK = threading.Lock()


def map_ok(name):
    return isinstance(name, str) and bool(MAP_NAME.fullmatch(name)) and os.path.exists(
        os.path.join(MAPS, name.partition("/")[0], "heightmap.npz"))


def _read(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def files(name):
    """{kind: path} of the file the brain reads each kind from for map `name` (brain/maps.py load_map's own()): a Forge
    layout's own callouts and positions where it has them (a built-in map's layout: the base map's), the patrols always
    the base map's."""
    from brain import variants
    base = variants.base_of(name)
    d = os.path.join(MAPS, base)
    vd = os.path.join(variants.ROOT, name) if name != base else d
    builtin = vd != d and bool(variants.base_area(_read(os.path.join(d, "objects.json"), {})))
    own = lambda fn: (os.path.join(vd, fn) if os.path.exists(os.path.join(vd, fn)) and not builtin
                      else os.path.join(d, fn))
    return dict(hot=own("positions.json"), patrol=os.path.join(d, "infantry_patrols.json"), hold=own("callouts.json"),
                ride=os.path.join(vd, "owner_rides.json"))   # (its own folder: the brain reads each of data_names)


def _rel(path, start=ROOT):
    """A path as the install's own (maps/...), or whole where it is elsewhere (another drive)."""
    try:
        return os.path.relpath(path, start).replace("\\", "/")
    except ValueError:
        return path


def _xyz(p):
    """[x, y, z] rounded, or None for anything that is not three finite numbers in reach."""
    if not isinstance(p, (list, tuple)) or len(p) != 3:
        return None
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and abs(v) < LIMIT for v in p):
        return None
    return [round(float(v), 2) for v in p]


def load(name):
    """What the view shows: {hot: [{pos, owner, score, sees, height, duck}], patrol: [{name, pos, team}],
    hold: {red: [pos], blue: [pos]}, lane: [pos], sneak: {red: [[pos]], blue: [[pos]]}, files: {kind: path from the
    install}, shared: {kind: bool}} (lanes and sneak routes: in the holds' callouts.json, files["hold"])."""
    f = files(name)
    rows = _read(f["hot"], [])
    hot = [dict(pos=r["pos"], owner=bool(r.get("owner")), score=r.get("score", 0.0), sees=r.get("sees", 0),
                height=r.get("height", 0.0), duck=bool(r.get("duck")))
           for r in rows if isinstance(r, dict) and _xyz(r.get("pos"))]
    patrol = []
    for k, v in _read(f["patrol"], {}).items():
        pos = _xyz(v.get("pos") if isinstance(v, dict) else v)
        if pos:
            patrol.append(dict(name=k, pos=pos, team=v.get("team") if isinstance(v, dict) and v.get("team") in TEAMS else None))
    cfg = _read(f["hold"], {})
    holds = cfg.get("holds") or {}
    hold = {t: [p for p in map(_xyz, holds.get(t, [])) if p] for t in TEAMS}
    lane = [p for p in map(_xyz, cfg.get("lanes") or []) if p]
    sneaks = cfg.get("sneak") if isinstance(cfg.get("sneak"), dict) else {}
    sneak = {t: [pts for pts in ([p for p in map(_xyz, r) if p] for r in sneaks.get(t, []) if isinstance(r, list))
                 if len(pts) >= 2] for t in TEAMS}
    ride = [dict(name=r.get("name") or "", kind=r["kind"], take_off=_xyz(r.get("take_off")), land=_xyz(r.get("land")))
            for r in _read(f["ride"], {}).get("rides", []) if isinstance(r, dict) and r.get("kind") in RIDE_KINDS
            and _xyz(r.get("take_off")) and _xyz(r.get("land"))]
    rel = {k: _rel(p) for k, p in f.items()}
    shared = {k: "/variants/" in name and "/variants/" not in rel[k] for k in rel}
    return dict(map=name, hot=hot, patrol=patrol, hold=hold, ride=ride, lane=lane, sneak=sneak, files=rel, shared=shared)


def check(sent):
    """The view's edit, checked: (owner hot spots [pos], patrols [(name, pos, team)], holds {team: [pos]}). Raises
    ValueError for anything malformed (nothing is written then)."""
    if not isinstance(sent, dict):
        raise ValueError("not an edit")
    hot = []
    for r in sent.get("hot", []):
        pos = _xyz(r.get("pos") if isinstance(r, dict) else None)
        if pos is None:
            raise ValueError("a hot spot without a place")
        hot.append(pos)
    patrol, names = [], set()
    for r in sent.get("patrol", []):
        pos = _xyz(r.get("pos") if isinstance(r, dict) else None)
        nm = r.get("name") if isinstance(r, dict) else None
        nm = " ".join(nm.split())[:60] if isinstance(nm, str) else ""
        team = r.get("team") if isinstance(r, dict) else None
        if pos is None or not nm or team not in TEAMS + (None,):
            raise ValueError("a patrol point needs a place, a name and a team (red, blue or both)")
        if nm.lower() in names:
            raise ValueError(f"two patrol points are called {nm!r}")
        names.add(nm.lower())
        patrol.append((nm, pos, team))
    holds = sent.get("hold")
    if not isinstance(holds, dict):
        raise ValueError("no team holds")
    hold = {}
    for t in TEAMS:
        pts = holds.get(t)
        if not isinstance(pts, list) or not pts:
            raise ValueError(f"the {t} team needs at least one hold")
        hold[t] = [_xyz(p) for p in pts]
        if None in hold[t]:
            raise ValueError(f"a {t} hold without a place")
    if len(hot) > MAX_HOT or len(patrol) > MAX_PATROL or any(len(v) > MAX_HOLD for v in hold.values()):
        raise ValueError(f"at most {MAX_HOT} hot spots, {MAX_PATROL} patrol points and {MAX_HOLD} holds a team")
    ride = []
    for r in sent.get("ride", []):
        r = r if isinstance(r, dict) else {}
        a, b, kind = _xyz(r.get("take_off")), _xyz(r.get("land")), r.get("kind")
        nm = " ".join(r["name"].split())[:60] if isinstance(r.get("name"), str) else ""
        if a is None or b is None or kind not in RIDE_KINDS:
            raise ValueError("a lift or man cannon needs where you step in, where it puts you down and its kind")
        if math.dist(a, b) < 0.5:
            raise ValueError(f"{nm or 'a ride'}: where you step in and where it puts you down are the same spot")
        ride.append((nm or ("Gravity lift" if kind == "lift" else "Man cannon"), kind, a, b))
    if len(ride) > MAX_RIDE:
        raise ValueError(f"at most {MAX_RIDE} lifts and man cannons")
    # (an edit without "lane" / "sneak", a view from before they could be edited: None, the file's kept as they are)
    if "lane" not in sent and "sneak" not in sent:
        return hot, patrol, hold, ride, None, None
    lane = []
    for p in sent.get("lane", []):
        pos = _xyz(p)
        if pos is None:
            raise ValueError("a lane point without a place")
        lane.append(pos)
    if len(lane) > MAX_LANE:
        raise ValueError(f"at most {MAX_LANE} lane points")
    sneaks = sent.get("sneak") if isinstance(sent.get("sneak"), dict) else {}
    sneak = {}
    for t in TEAMS:
        routes = sneaks.get(t, [])
        if not isinstance(routes, list) or len(routes) > MAX_SNEAK:
            raise ValueError(f"at most {MAX_SNEAK} {t} sneak routes")
        sneak[t] = []
        for k, r in enumerate(routes, 1):
            pts = [_xyz(p) for p in r] if isinstance(r, list) else [None]
            if None in pts:
                raise ValueError(f"{t} sneak route {k}: a waypoint without a place")
            if len(pts) < 2:
                raise ValueError(f"{t} sneak route {k} needs at least two waypoints (from your base to their flag)")
            if len(pts) > MAX_SNEAK_POINTS:
                raise ValueError(f"{t} sneak route {k}: at most {MAX_SNEAK_POINTS} waypoints")
            sneak[t].append(pts)
    return hot, patrol, hold, ride, lane, sneak


def hot_rows(old, hot, describe=None):
    """positions.json after the edit: the owner spots first (in the view's order; one kept where it was keeps its
    measures, a new or moved one measured by describe(pos), else a plain row), then the computed rows none of them is
    within NEAR of."""
    before = {tuple(r["pos"]): r for r in old if isinstance(r, dict) and r.get("owner") and _xyz(r.get("pos"))}
    mine = []
    for pos in hot:
        row = before.get(tuple(pos))
        if row is None:
            row = None
            if describe is not None:
                try:
                    row = describe(pos)
                except Exception as e:                # (a nav that cannot load: the spot still counts)
                    print(f"spots: could not measure the hot spot at {pos}: {type(e).__name__}: {e}", flush=True)
            row = dict(row or dict(pos=pos, score=1.0, sees=0, height=0.0, duck=False), pos=pos, owner=True)
        mine.append(row)
    rest = [r for r in old if isinstance(r, dict) and not r.get("owner") and _xyz(r.get("pos"))
            and all(math.hypot(r["pos"][0] - p[0], r["pos"][1] - p[1]) > NEAR for p in hot)]
    return mine + rest


def patrol_text(patrol):
    """infantry_patrols.json as the hand-made ones are laid out: one point a line."""
    lines = [f"  {json.dumps(nm)}: " + (json.dumps(pos) if team is None else json.dumps(dict(pos=pos, team=team)))
             for nm, pos, team in patrol]
    return "{\n" + ",\n".join(lines) + ("\n" if lines else "") + "}\n"


def _measure(name):
    """describe(pos) for new hot spots: tools/power_positions.py describe on the map's nav (built once a process)."""
    import power_positions
    from brain.maps import get_map, terrain
    m = get_map(name)
    T = terrain(m)
    return lambda pos: power_positions.describe(m, T, pos)


def _write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)                       # whole or not at all


def save(name, sent, describe=None, root=None):
    """Write the view's edit of map `name`. Returns {kind: count, backups: [paths], changed: [paths]}. Only files
    whose contents change are written; each is copied to backups/spots/ first."""
    if not map_ok(name):
        raise ValueError(f"no map {name!r}")
    hot, patrol, hold, ride, lane, sneak = check(sent)
    f = files(name)
    with _LOCK:
        old_rows = _read(f["hot"], [])
        changed_hot = [r["pos"] for r in old_rows if isinstance(r, dict) and r.get("owner")] != hot
        rows = hot_rows(old_rows, hot, (describe or _measure(name)) if changed_hot and hot else None)
        cfg = _read(f["hold"], None)
        if cfg is None:
            raise ValueError(f"{_rel(f['hold'])} cannot be read")
        cfg = dict(cfg, holds={t: hold[t] for t in TEAMS})
        if lane is not None:
            cfg.update(lanes=lane, sneak={t: sneak[t] for t in TEAMS})
        else:
            lane, sneak = cfg.get("lanes") or [], {t: (cfg.get("sneak") or {}).get(t, []) for t in TEAMS}
        out = {"hot": json.dumps(rows, indent=1) + "\n", "patrol": patrol_text(patrol),
               "hold": json.dumps(cfg, indent=1) + "\n"}
        if not patrol and not os.path.exists(f["patrol"]):
            out.pop("patrol")                   # no patrols and no file: none made
        out["ride"] = json.dumps(dict(rides=[dict(name=nm, kind=k, take_off=a, land=b) for nm, k, a, b in ride]), indent=1) + "\n"
        if not ride and not os.path.exists(f["ride"]):
            out.pop("ride")
        bak = os.path.join(root or ROOT, "backups", "spots")
        stamp, kept, changed = time.strftime("%Y%m%d-%H%M%S"), [], []
        for k, text in out.items():
            path = f[k]
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    if json.loads(fh.read() or "null") == json.loads(text):
                        continue                # the same data: left as it is
                os.makedirs(bak, exist_ok=True)
                to = os.path.join(bak, f"{name.replace('/variants/', '@')}_{stamp}_{os.path.basename(path)}")
                n = 1
                while os.path.exists(to):
                    to, n = os.path.join(bak, f"{name.replace('/variants/', '@')}_{stamp}-{n}_{os.path.basename(path)}"), n + 1
                shutil.copy2(path, to)
                kept.append(_rel(to, root or ROOT))
            _write(path, text)
            changed.append(_rel(path))
    return dict(hot=len(hot), patrol=len(patrol), hold={t: len(hold[t]) for t in TEAMS}, ride=len(ride), lane=len(lane),
                sneak={t: len(sneak[t]) for t in TEAMS}, backups=kept,
                changed=changed, warnings=ride_problems(name, ride) if ride else [])


def ride_problems(name, ride):
    """Why the nav would skip a ride (Terrain.add_human_links: each end on a walkable node, within 0.7 u of its floor
    height, the two ends on different nodes): [text], one a ride with a problem. [] when the nav cannot be loaded."""
    try:
        from brain.core import Vec
        from brain.maps import get_map, terrain
        T = terrain(get_map(name))
    except Exception as e:
        print(f"spots: no nav to check the rides of {name}: {type(e).__name__}: {e}", flush=True)
        return []
    out = []
    for nm, _kind, a, b in ride:
        why, nodes = [], []
        for label, p in (("where you step in", a), ("where it puts you down", b)):
            if not T.inside(p[0], p[1]):
                why.append(f"{label} is outside the map's nav")
                continue
            n = T._node(Vec(*p))
            nodes.append(n)
            if not T.lwalk[n] or abs(float(T.lz[n]) - p[2]) > 0.7:
                why.append(f"{label} is not on floor bots can walk")
        if not why and nodes[0] == nodes[1]:
            why.append("both ends are on the same spot of the nav")
        if why:
            out.append(f"{nm}: " + "; ".join(why) + ". Bots will not use it until it is moved.")
    return out


def level_floor(name):
    """The floor bots can walk to, for the view to click on where no LiDAR scan covers it: the nav's reachable floor
    (as tools/power_positions.py picks from; the level data's every upward face put spots on roofs and the sky's
    ledges), else the level data's floors; [x, y, z, ...] flat, thinned to LEVEL_POINTS, with the cell it was thinned to."""
    import numpy as np
    try:
        from brain.maps import get_map, terrain
        from brain.terrain import NAV_CELL
        T = terrain(get_map(name))
        l, j, i = np.nonzero(T.lwalk & T.reach)
        k = max(1, math.ceil(len(l) / LEVEL_POINTS))
        l, j, i = l[::k], j[::k], i[::k]
        if len(l):
            x = T.x0 + (i + 0.5) * NAV_CELL * T.nstep
            y = T.y0 + (j + 0.5) * NAV_CELL * T.nstep
            pts = np.round(np.stack([x, y, T.lz[l, j, i]], 1), 2)
            return dict(cell=NAV_CELL * T.nstep * math.sqrt(k), points=pts.ravel().tolist(), source="nav")
    except Exception as e:                       # (a nav that cannot load: the level data's floors)
        print(f"spots: no nav floor for {name}: {type(e).__name__}: {e}", flush=True)
    from brain.variants import base_of
    path = os.path.join(MAPS, base_of(name), "heightmap.npz")
    hm = np.load(path)
    fl = hm["floors"]
    cell = float(hm["cell"])
    total = int(np.isfinite(fl).sum())
    step = max(1, math.ceil(math.sqrt(total / LEVEL_POINTS)))
    sub = fl[:, ::step, ::step]
    lv, j, i = np.nonzero(np.isfinite(sub))
    x = float(hm["x0"]) + (i * step + 0.5) * cell
    y = float(hm["y0"]) + (j * step + 0.5) * cell
    pts = np.round(np.stack([x, y, sub[lv, j, i]], 1), 2)
    return dict(cell=cell * step, points=pts.ravel().tolist(), source="level")


def handle(method, path, name, body=None, header=None):
    """The view's requests (tools/lidar.py serve): (status, answer). GET /spots, GET /spots/floor, POST /spots (with
    the X-LiDAR: spots header: a page from another site cannot send it without asking first, and this server never
    says yes)."""
    if not map_ok(name):
        return 404, dict(error="no such map")
    try:
        if method == "GET" and path == "/spots":
            return 200, load(name)
        if method == "GET" and path == "/spots/floor":
            return 200, level_floor(name)
        if method == "POST" and path == "/spots":
            if header != "spots":
                return 403, dict(error="refused")
            return 200, dict(saved=save(name, json.loads(body or b"{}")), spots=load(name))
    except ValueError as e:
        return 400, dict(error=str(e))
    except OSError as e:
        return 500, dict(error=f"could not write: {e}")
    return 404, dict(error="not found")


def selftest():
    """Checks on a scratch copy of a map's spot files: owner rows replace a computed one beside them and keep their
    measures when kept, a moved one is measured again; patrols round-trip with teams; holds need a spot a team; a
    malformed edit writes nothing; an unchanged save writes nothing; the backups are made."""
    global files
    import tempfile
    tmp = tempfile.mkdtemp(prefix="spots_")
    try:
        computed = [dict(pos=[0.0, 0.0, 1.0], score=0.9, sees=10, height=2.0, duck=True),
                    dict(pos=[20.0, 0.0, 1.0], score=0.5, sees=4, height=0.5, duck=False)]
        kept = dict(pos=[5.0, 5.0, 2.0], score=1.0, sees=7, height=3.0, duck=True, owner=True)
        rows = hot_rows(computed + [kept], [[5.0, 5.0, 2.0], [0.5, 0.0, 1.0]],
                        lambda p: dict(pos=p, score=1.0, sees=3, height=1.0, duck=False, owner=True))
        assert [r["pos"] for r in rows] == [[5.0, 5.0, 2.0], [0.5, 0.0, 1.0], [20.0, 0.0, 1.0]], rows
        assert rows[0]["sees"] == 7 and rows[1]["sees"] == 3 and all(r["owner"] for r in rows[:2]) and not rows[2].get("owner")
        assert hot_rows(computed, [[9.0, 9.0, 9.0]], None)[0] == dict(pos=[9.0, 9.0, 9.0], score=1.0, sees=0, height=0.0,
                                                                      duck=False, owner=True)
        text = patrol_text([("North spawn", [1.0, 2.0, 3.0], None), ("Red rockets", [4.0, 5.0, 6.0], "red")])
        assert json.loads(text) == {"North spawn": [1.0, 2.0, 3.0], "Red rockets": {"pos": [4.0, 5.0, 6.0], "team": "red"}}
        for bad in ({"hold": {"red": [], "blue": [[0, 0, 0]]}}, {"hold": {"red": [[0, 0, 0]], "blue": [[0, 0, "x"]]}},
                    {"hot": [{"pos": [0, 0]}], "hold": {"red": [[0, 0, 0]], "blue": [[0, 0, 0]]}},
                    {"patrol": [{"name": "a", "pos": [0, 0, 0]}, {"name": "A", "pos": [1, 1, 1]}],
                     "hold": {"red": [[0, 0, 0]], "blue": [[0, 0, 0]]}},
                    {"patrol": [{"name": "a", "pos": [0, 0, 0], "team": "green"}], "hold": {"red": [[0, 0, 0]], "blue": [[0, 0, 0]]}},
                    {"hold": {"red": [[float("nan"), 0, 0]], "blue": [[0, 0, 0]]}},
                    {"hold": {"red": [[0, 0, 0]], "blue": [[0, 0, 0]]}, "lane": [[0, 0]]},
                    {"hold": {"red": [[0, 0, 0]], "blue": [[0, 0, 0]]}, "sneak": {"red": [[[0, 0, 0]]]}},       # one point
                    {"hold": {"red": [[0, 0, 0]], "blue": [[0, 0, 0]]}, "sneak": {"blue": [[[0, 0, 0], "x"]]}},
                    {"hold": {"red": [[0, 0, 0]], "blue": [[0, 0, 0]]}, "sneak": {"red": "route"}}):
            try:
                check(bad)
            except ValueError:
                continue
            raise AssertionError(f"accepted {bad}")
        # a real map's files, copied: save writes them, keeps backups, an unchanged save writes nothing
        name = "reach_cex_headlong"
        if map_ok(name):
            real = files(name)
            fake = {k: os.path.join(tmp, os.path.basename(p)) for k, p in real.items()}
            for k in real:
                if os.path.exists(real[k]):
                    shutil.copy2(real[k], fake[k])
            was = files
            files = lambda n: fake
            try:
                cur = load(name)
                edit = dict(hot=[{"pos": [1.0, 2.0, 3.0]}] + [r for r in cur["hot"] if r["owner"]],
                            patrol=cur["patrol"] + [dict(name="Test point", pos=[1.5, 2.5, 3.5], team="blue")],
                            hold=dict(cur["hold"], red=cur["hold"]["red"] + [[3.0, 3.0, 3.0]]))
                fl = level_floor(name)["points"]           # a ride between two nav floor points, and one off the map
                good = dict(name="Lift 1", kind="lift", take_off=fl[0:3], land=fl[3000:3003])
                edit["ride"] = [good, dict(name="", kind="cannon", take_off=[9000.0, 9000.0, 0.0], land=fl[0:3])]
                edit["lane"] = cur["lane"] + [[7.0, 8.0, 9.0]]
                route = [[1.0, 1.0, 1.0], [2.0, 2.0, 2.0], [3.0, 3.0, 3.0]]
                edit["sneak"] = dict(red=cur["sneak"]["red"] + [route], blue=cur["sneak"]["blue"])
                r = save(name, edit, describe=lambda p: dict(pos=p, score=1.0, sees=1, height=0.0, duck=False), root=tmp)
                assert len(r["changed"]) == 4 and len(r["backups"]) == 3, r          # (owner_rides.json is new)
                assert len(r["warnings"]) == 1 and r["warnings"][0].startswith("Man cannon: where you step in is outside"), r
                after = load(name)
                assert [x["name"] for x in after["ride"]] == ["Lift 1", "Man cannon"]
                assert after["ride"][0]["take_off"] == [round(v, 2) for v in good["take_off"]]
                assert after["hot"][0]["pos"] == [1.0, 2.0, 3.0] and after["hot"][0]["owner"]
                assert dict(name="Test point", pos=[1.5, 2.5, 3.5], team="blue") in after["patrol"]
                assert after["hold"]["red"][-1] == [3.0, 3.0, 3.0]
                cfg = _read(fake["hold"], {})
                assert cfg["zones"] == _read(real["hold"], {})["zones"]          # the rest of callouts.json kept
                assert after["lane"][-1] == [7.0, 8.0, 9.0] and after["sneak"]["red"][-1] == route
                assert cfg["lanes"][-1] == [7.0, 8.0, 9.0] and cfg["sneak"]["red"][-1] == route   # as maps.load_map reads them
                same = dict(hot=[{"pos": p["pos"]} for p in after["hot"] if p["owner"]], patrol=after["patrol"],
                            hold=after["hold"], ride=after["ride"])
                r = save(name, dict(same, lane=after["lane"], sneak=after["sneak"]), root=tmp)
                assert r["changed"] == [] and r["backups"] == [], r
                r = save(name, same, root=tmp)              # a view without lanes / sneak: they are kept, not wiped
                assert r["changed"] == [] and r["lane"] == len(after["lane"]), r
                assert load(name)["sneak"]["red"][-1] == route
                try:
                    save(name, dict(hot=[], patrol=[], hold=dict(red=[], blue=[[0, 0, 0]])), root=tmp)
                    raise AssertionError("saved a team with no hold")
                except ValueError:
                    pass
                assert load(name)["hold"]["red"][-1] == [3.0, 3.0, 3.0]          # nothing written by the refused one
            finally:
                files = was
            assert handle("GET", "/spots", "../brain")[0] == 404
            assert handle("POST", "/spots", name, b"{}", header=None)[0] == 403
            fl = level_floor(name)
            assert fl["points"] and len(fl["points"]) % 3 == 0 and len(fl["points"]) <= 3 * LEVEL_POINTS
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("spots OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(__doc__)
