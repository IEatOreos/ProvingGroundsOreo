"""Paint the nav by hand on a map's roofless view ("would it be possible to get a roofless view of the maps? So that way we
can paint on top of that", "two types of fly meshes One low altitude (take off and swoop in attack) and high altitude
for navigating").

A local page (tools/paint_view.html, http://127.0.0.1:8796/) over the map's roofless pictures (tools/roofless.py):
pick a cut height, a layer and a brush, paint, save. Layers (maps/<map>/paint.json "layers", cells of half a unit,
each [x, y, z] with z the floor under it):
  walk      floor bots may walk that the level data lacks (added to the nav's floor)
  block     floor bots must not walk (entering it costs a wall)
  drive_s / drive_m / drive_l   ground small (Mongoose, Ghost), medium (Warthog) and large (Scorpion, Wraith) vehicles
            may drive (all three added to the vehicles' ground for now)
  fly_low   airspace aircraft take off in and swoop through to attack
  fly_high  airspace aircraft travel through
  jumps jumps bots should make: a
            take-off and a landing clicked on the view, each on its own height; maps/<map>/paint.json "jumps"
            [[x, y, z, x2, y2, z2], ...], added to the nav as people's jumps one way (brain/maps.py terrain()).
Read by brain/maps.py terrain() -> Terrain.apply_paint (blocked, drivable, flying) at the next match's start.
The page also shows the jumps people made that LiDAR recorded (green: bots made it, orange: not tried, red: retired)
and the map's objectives (Invasion's territories, core and delivery point).

The page sends each cell with the cut height it was painted at; here it is snapped to the highest walkable floor of
the level data at that spot under the cut (a cell painted where the data has no floor keeps the cut's floor height).

usage: python -I paint.py [--port 8796] [--open]       python -I paint.py --selftest
"""
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
MAPS = os.path.join(ROOT, "maps")
sys.path.insert(0, HERE)
LAYERS = ("walk", "block", "drive_s", "drive_m", "drive_l", "fly_low", "fly_high")
CELL = 0.5
MAX_CELLS = 400000                     # a whole big map at half a unit, all layers: far more than anyone paints
MAX_JUMPS = 2000
NAME = re.compile(r"^[a-z0-9_]+$")
CUT_HEAD = 1.6                         # tools/roofless.py: a cut this far over the floor it shows
_LOCK = threading.Lock()


def map_dir(name):
    """The map's folder, or None for a name that is not a map here (no paths from the page)."""
    if not isinstance(name, str) or not NAME.match(name):
        return None
    d = os.path.join(MAPS, name)
    return d if os.path.isdir(d) else None


def snap_z(hm, x, y, cut):
    """The highest walkable floor at (x, y) at or under the cut (None: no cut, the top floor); None if there is none."""
    j = int((y - float(hm["y0"])) / float(hm["cell"]))
    i = int((x - float(hm["x0"])) / float(hm["cell"]))
    fl = hm["floors"]
    if not (0 <= j < fl.shape[1] and 0 <= i < fl.shape[2]):
        return None
    col = fl[:, j, i]
    col = col[np.isfinite(col)]
    if cut is not None:
        col = col[col <= cut + 0.05]
    return float(col.max()) if col.size else None


def to_cells(name, sent):
    """{layer: [[x, y, cut or None] or [x, y, None, z] (a saved cell), ...]} from the page -> {layer: [[x, y, z], ...]} on the half-unit grid, one cell
    per spot and layer, z snapped to the floor (snap_z) or the cut's floor height."""
    d = map_dir(name)
    hm = np.load(os.path.join(d, "heightmap.npz")) if d and os.path.exists(os.path.join(d, "heightmap.npz")) else None
    out, total = {}, 0
    for layer in LAYERS:
        seen, cells = set(), []
        for c in sent.get(layer, []):
            if not (isinstance(c, (list, tuple)) and len(c) in (3, 4)):
                continue
            x, y, cut = c[:3]
            known = c[3] if len(c) == 4 and isinstance(c[3], (int, float)) else None   # a saved cell: its own height
            if not all(isinstance(v, (int, float)) for v in (x, y)) or not (cut is None or isinstance(cut, (int, float))):
                continue
            gx, gy = round(x / CELL) * CELL, round(y / CELL) * CELL
            z = known if known is not None else snap_z(hm, gx, gy, cut) if hm is not None else None
            if z is None:
                z = (cut - CUT_HEAD) if cut is not None else 0.0
            k = (gx, gy, round(z, 1))                # one cell a spot and floor (stacked floors keep both)
            if k in seen:
                continue
            seen.add(k)
            cells.append([gx, gy, round(z, 2)])
        total += len(cells)
        if total > MAX_CELLS:
            raise ValueError(f"over {MAX_CELLS} cells")
        if cells:
            out[layer] = cells
    return out


_MESH = {}


def surface_z(name, x, y, cut):
    """The height of the surface the roofless view shows at (x, y) on the cut (tools/roofless.py: the highest upward face
    wholly under the cut; no cut: the top), from the level mesh; None where there is none. (The heightmap's floors miss
    walked floors: a landing on Spire's ramp foot snapped 24 u down to the floor under it.)"""
    d = map_dir(name)
    src = os.path.join(d, "source", "bsp.obj") if d else None
    if src is None or not os.path.exists(src):
        return None
    if name not in _MESH:
        from heightmap import FLOOR_NZ, load_obj
        v, f = load_obj(src)
        P = v[f]
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        up = n[:, 2] / (np.linalg.norm(n, axis=1) + 1e-9) >= FLOOR_NZ * 0.5
        P = P[up]
        _MESH[name] = (P, P[:, :, 0].min(1), P[:, :, 0].max(1), P[:, :, 1].min(1), P[:, :, 1].max(1), P[:, :, 2].max(1))
    P, xa, xb, ya, yb, zt = _MESH[name]
    m = (xa <= x) & (x <= xb) & (ya <= y) & (y <= yb)
    if cut is not None:
        m &= zt <= cut + 0.05
    best = None
    for t in P[m]:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-12:
            continue
        l1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / det
        l2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / det
        l3 = 1.0 - l1 - l2
        if min(l1, l2, l3) < -1e-6:
            continue
        z = l1 * az + l2 * bz + l3 * cz
        best = z if best is None or z > best else best
    return None if best is None else float(best)


def to_jumps(name, sent):
    """[[x, y, cut, x2, y2, cut2, z or None, z2 or None], ...] from the page -> [[x, y, z, x2, y2, z2], ...]: each end on
    the floor under its own cut (snap_z), or its saved height."""
    d = map_dir(name)
    hm = np.load(os.path.join(d, "heightmap.npz")) if d and os.path.exists(os.path.join(d, "heightmap.npz")) else None
    out = []
    for j in sent if isinstance(sent, list) else []:
        if not (isinstance(j, (list, tuple)) and len(j) == 8):
            continue
        x, y, cut, x2, y2, cut2, z, z2 = j
        num = lambda q: isinstance(q, (int, float)) and not isinstance(q, bool)
        if not all(num(q) for q in (x, y, x2, y2)) or not all(q is None or num(q) for q in (cut, cut2, z, z2)):
            continue
        ends = []
        for px_, py_, c, known in ((x, y, cut, z), (x2, y2, cut2, z2)):
            zz = known if known is not None else surface_z(name, px_, py_, c)
            if zz is None and hm is not None:
                zz = snap_z(hm, px_, py_, c)
            if zz is None:
                zz = (c - CUT_HEAD) if c is not None else 0.0
            ends += [round(px_, 2), round(py_, 2), round(zz, 2)]
        out.append(ends)
        if len(out) > MAX_JUMPS:
            raise ValueError(f"over {MAX_JUMPS} jumps")
    return out


def recorded_links(d):
    """People's jumps LiDAR recorded on the map: [[x, y, z, x2, y2, z2, status]], status "used" (a bot made it),
    "untried" or "retired" (bots kept failing it: brain/maps.py usable_links leaves it out)."""
    path = os.path.join(d, "lidar.json")
    if not os.path.exists(path):
        return []
    out = []
    for k in json.load(open(path)).get("links", []):
        if k.get("kind") in ("crouch", "route") or "take_off" not in k or "land" not in k:
            continue
        st = "retired" if k.get("bot_fail", 0) >= 3 and not k.get("bot_ok", 0) else "used" if k.get("bot_ok", 0) else "untried"
        out.append([round(v, 2) for v in list(k["take_off"][:3]) + list(k["land"][:3])] + [st])
    return out


def objectives(d):
    """The map's Invasion objectives: [{kind, label, x, y, z, r}] (territories by phase, the core, the delivery point)."""
    path = os.path.join(d, "objects.json")
    if not os.path.exists(path):
        return []
    try:
        sys.path.insert(0, ROOT)
        from brain import invasion
        inv = invasion.layout(json.load(open(path)))
    except Exception:
        return []
    if inv is None:
        return []
    out = []
    for ph in (1, 2):
        for k, z in enumerate(inv["phases"][ph]):
            out.append(dict(kind="territory", label=f"Phase {ph} {'AB'[k] if k < 2 else k + 1}", x=z.x, y=z.y, z=z.z,
                            r=invasion.zone_radius(inv, z)))
    c = inv["core"]
    out.append(dict(kind="core", label="Core", x=c.x, y=c.y, z=c.z, r=0.6))
    dv = inv["phases"][3][0]
    out.append(dict(kind="delivery", label="Delivery", x=dv.x, y=dv.y, z=dv.z, r=invasion.zone_radius(inv, dv)))
    return out


def save(name, sent):
    d = map_dir(name)
    if d is None:
        raise ValueError(f"no map {name!r}")
    data = dict(map=name, cell=CELL, layers=to_cells(name, sent), jumps=to_jumps(name, sent.get("jumps", [])))
    path = os.path.join(d, "paint.json")
    with _LOCK:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)                  # whole or not at all: a match may load it any time
    return dict({k: len(v) for k, v in data["layers"].items()}, jumps=len(data["jumps"]))


def maps_list():
    out = []
    for name in sorted(os.listdir(MAPS)):
        d = map_dir(name)
        if d is None:
            continue
        has_view = os.path.exists(os.path.join(d, "roofless.json"))
        has_mesh = os.path.exists(os.path.join(d, "source", "bsp.obj")) and os.path.exists(os.path.join(d, "heightmap.npz"))
        if has_view or has_mesh:
            out.append(dict(name=name, view=has_view, painted=os.path.exists(os.path.join(d, "paint.json"))))
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, body, kind="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        name = (q.get("name") or [""])[0]
        if u.path in ("/", "/index.html"):
            return self.reply(200, open(os.path.join(HERE, "paint_view.html"), "rb").read(), "text/html; charset=utf-8")
        if u.path == "/api/maps":
            return self.reply(200, maps_list())
        if u.path == "/api/map":
            d = map_dir(name)
            if d is None:
                return self.reply(404, {"error": "no such map"})
            view = os.path.join(d, "roofless.json")
            paint = os.path.join(d, "paint.json")
            pd = json.load(open(paint)) if os.path.exists(paint) else {}
            return self.reply(200, dict(view=json.load(open(view)) if os.path.exists(view) else None,
                                        paint=pd.get("layers", {}), jumps=pd.get("jumps", []),
                                        links=recorded_links(d), marks=objectives(d)))
        m = re.match(r"^/view/([a-z0-9_]+)/(level_\d+\.png)$", u.path)
        if m and map_dir(m.group(1)):
            p = os.path.join(map_dir(m.group(1)), "roofless", m.group(2))
            if os.path.exists(p):
                return self.reply(200, open(p, "rb").read(), "image/png")
        return self.reply(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        name = (parse_qs(u.query).get("name") or [""])[0]
        if map_dir(name) is None:
            return self.reply(404, {"error": "no such map"})
        try:
            if u.path == "/api/build":
                import roofless
                return self.reply(200, roofless.build(name))
            if u.path == "/api/paint":
                n = int(self.headers.get("Content-Length", "0"))
                if n > 64 * 1024 * 1024:
                    return self.reply(413, {"error": "too big"})
                sent = json.loads(self.rfile.read(n) or b"{}")
                return self.reply(200, {"saved": save(name, sent)})
        except (ValueError, OSError, SystemExit) as e:
            return self.reply(400, {"error": str(e)})
        return self.reply(404, {"error": "not found"})


def selftest():
    """Snapping: a cell under a cut takes the highest floor below it, a cut over everything the top floor, a spot with
    no floor the cut's floor; one cell per spot; a name that is not a map refused."""
    hm = dict(x0=0.0, y0=0.0, cell=1.0, floors=np.array([[[0.0, np.nan]], [[3.0, np.nan]]]))
    assert snap_z(hm, 0.5, 0.5, 1.6) == 0.0 and snap_z(hm, 0.5, 0.5, None) == 3.0 and snap_z(hm, 1.5, 0.5, 1.6) is None
    assert map_dir("../tools") is None and map_dir("no_such_map_xyz") is None
    cells = to_cells("no_such_map_xyz", {"walk": [[1.1, 1.0, 2.0], [1.2, 0.9, 2.0], [5, 5, None]], "junk": [[0, 0, 0]]})
    assert cells == {"walk": [[1.0, 1.0, 0.4], [5.0, 5.0, 0.0]]}, cells
    assert to_cells("no_such_map_xyz", {"fly_low": [[2, 2, None, 7.25]]}) == {"fly_low": [[2.0, 2.0, 7.25]]}
    # a jump: each end on its own cut's floor, or its saved height; junk dropped
    assert to_jumps("no_such_map_xyz", [[1, 2, 3.0, 4, 5, None, None, -7.5], [1, "x", 0, 0, 0, 0, None, None], 5]) ==         [[1.0, 2.0, 1.4, 4.0, 5.0, -7.5]]
    print("paint OK")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8796
    url = f"http://127.0.0.1:{port}/"
    import appwindow                         # (its page opens as an app window)
    try:
        # (no address reuse: on Windows two copies could both serve the port; now the second one finds the first)
        srv = type("Server", (ThreadingHTTPServer,), dict(allow_reuse_address=False))(("127.0.0.1", port), Handler)
    except OSError:                          # it runs already (its window was closed): show it
        if "--open" in sys.argv:
            appwindow.open_window(url)
        print("Paint the nav already running:", url, flush=True)
        return
    print("Paint the nav:", url, flush=True)
    if "--open" in sys.argv:
        appwindow.open_window(url)
    srv.serve_forever()


if __name__ == "__main__":
    main()
