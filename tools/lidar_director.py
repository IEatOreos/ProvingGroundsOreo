"""The LiDAR director: a model of the whole map's shape, a coverage map, and one assignment plan for every mapping bot.

Each mapping bot (tools/lidar.py Roomba) walks to its own nearest unpainted floor. That alone leaves patches: the
nearest-first search reaches only 40 / 150 units of path (farther floor is never picked: the bot wanders instead), it
looks at a random 2500 of the nodes in reach (small patches are missed), and the simulator stopped once no new floor
came for 45 s. The director looks at the whole map instead, every PERIOD seconds:
  - the map's shape: every walkable floor cell of the level data (Terrain.lwalk) sampled every STEP cells; reachable
    from the spawns (walking, teleporters, people's and bots' jumps: Terrain.reach over graph_h) or not; the map's kill
    and soft kill zones (Terrain.oob: brain/oob.py, maps/<map>/killzones.json) left out; regions: the reachable floor in
    connected pieces per floor level, cut into TILE-unit tiles (rooms, decks, corridors);
  - the coverage map: which samples someone painted (Recorder.explored_many); coverage = the painted share of the
    reachable floor, kill zones left out, with its history and the time it reached TARGET;
  - patches: each region's unpainted part (PATCH_MIN samples or more); islands: unpainted floor no walk reaches (a
    jump-up, a ledge, a lift's top): a called jump is the only way;
  - one plan: marked spots and gametype objectives first (_spots: at most OBJECTIVE_SHARE of the bots on objectives),
    then island jump jobs (late in the run), then every other bot paired with a patch, best pairs first (big and near),
    one bot a patch, so bots spread over different regions. A bot keeps its patch while it has unpainted floor and it
    paints some of it, else it gets another; a bot walking to its patch (fallback) that neither paints any of it nor
    gets closer for PATCH_S has failed a try (stuck, no way, killed on the way), and after PATCH_TRIES failed tries the
    patch is left, reported "no way found";
  - the bot's way: its own frontier (nearest first by path: early on nothing paints faster), its patch preferred
    (region_bias), every open patch's floor among its candidates (open_nodes); when that finds nothing within its
    search twice in a row (a 10 s wander between: the wander paints floor the frontier skips) and coverage is at
    TARGET, the bot walks to its patch's nearest floor (fallback: the last patches, wherever they are);
  - report(): coverage, regions, the patches and islands left with a reason each (lidar.json "coverage", the run's
    report, the simulator's log); view(): coverage and open patches for the LiDAR view.
"""
import math
import time

import numpy as np

STEP = 2                 # sample every 2nd nav cell each way (0.5 u apart, 0.25 u2 a sample)
PERIOD = 6.0             # seconds between plans
TARGET = 0.98            # coverage the director works to: this share of the reachable floor painted (kill zones out)
TILE = 16.0              # u: regions and patches are cut to tiles this size (a big unpainted area: a patch per tile)
PATCH_MIN = 2            # samples: smaller unpainted pieces are paint noise
MIN_CELLS = 6            # samples: smaller unreachable pieces are not islands worth a jump
PATCH_BONUS = 15.0       # path units a frontier candidate inside the bot's own patch is worth over nearer floor
PATCH_S = 90.0           # s: a bot walking to its patch that neither painted any of it nor came APPROACH closer this
                         # long has failed a try (45 s, no approach: long walks and called jumps on the way counted as
                         # failures and patches were left that bots do reach: Construct, ODST Data Hive)
APPROACH = 1.0           # u closer to its patch (flat + 2 x height) that counts as headway
PATCH_BIG = 16           # samples (4 u2): a patch this big still open keeps a run going past TARGET (done)
PATCH_TRIES = 2          # failed tries before a patch is left (for PATCH_RETRY s)
PATCH_RETRY = 240.0      # s: patches left are offered again this often
ISLAND_REACH = 30.0      # a bot this close (flat) to an island takes its jump job
JUMP_NEAR = 5.0          # at the take-off side: call the jump
JUMP_JOB_S = 40.0        # a jump job not reached by then is dropped
ISLANDS = True           # give out island jump jobs (off: A/B runs)
ISLAND_AFTER = 0.7       # ... once this share of the reachable floor is painted
ISLAND_BOTS = 2          # ... to this many bots at a time (half the bots once coverage is at TARGET)
ISLAND_TRIES = 3         # jump calls made for an island before it is left
SPOT_BOTS = 3            # bots sent to each spot a person marked to cover (the simulator's view)
SPOT_DONE_R = 2.5        # a bot this close (flat, within 2 u up or down) has covered the spot
SPOT_GIVE_UP = 120.0     # seconds: a spot no bot reached by then has no way there
OBJECTIVE_SHARE = 0.5    # at most this share of the bots on gametype objectives at a time (tools/lidar.py Objectives)
DETACHED = 6.0           # u: an island this far (flat) from any reachable floor is detached (a lift, a cannon, outside)
RIDE_NEAR = 12.0         # u: a lift, man cannon or teleporter this close to an island (or its take-off side) leads there


class LidarDirector:
    def __init__(s, T, rec, spawns=()):
        from scipy.ndimage import label  # noqa: F401  (checked here: the director needs SciPy's labelling)
        from brain.terrain import NAV_CELL
        s.T, s.rec, s.spawns = T, rec, list(spawns)
        s.cell = NAV_CELL * STEP
        walk = T.lwalk[:, ::STEP, ::STEP]
        s.l, s.j, s.i = np.nonzero(walk)
        s.shape = walk.shape
        jj, ii = s.j * STEP, s.i * STEP
        s.x = T.x0 + (ii + 0.5) * NAV_CELL
        s.y = T.y0 + (jj + 0.5) * NAV_CELL
        s.z = T.lz[s.l, jj, ii]
        s.bounds = (float(s.x.min()), float(s.y.min()), float(s.x.max()), float(s.y.max())) if len(s.x) else None
        tx, ty = np.floor((s.x - T.x0) / TILE).astype(np.int64), np.floor((s.y - T.y0) / TILE).astype(np.int64)
        ny = int(ty.max()) + 1 if len(ty) else 1
        s.tile, s.ntiles = tx * ny + ty, (int(tx.max()) + 1 if len(tx) else 1) * ny
        s.tries = np.zeros(len(s.x), np.int16)          # failed tries per sample (patches) / jump calls (islands)
        s.kz = np.zeros(len(s.x), bool)
        s.want = s.painted = s.reach = s.behind = np.zeros(len(s.x), bool)
        s.patch_of = np.zeros(len(s.x), np.int32)       # sample -> patch index + 1 (0: none)
        s.patch_grid = np.zeros(s.shape, np.int32)      # the same on the sample grid (region_bias)
        s.next_t, s.now, s.patches, s.islands, s.jobs = 0.0, 0.0, [], [], {}
        s.open_nodes = np.zeros(0, np.int64)            # every open patch's floor as nav nodes (Roomba.frontier)
        s.painted_share = s.coverage = s.reach_share = 0.0
        s.history, s.reached_at = [], None              # [(t, coverage)] each plan; when coverage reached TARGET
        s.retry_t = 0.0                                 # when the patches left were last offered again
        s.last_line = 0.0
        s.spots, s.new_spot_bots = [], []        # spots to cover (marked, objectives); bots just sent to one

    def add_spot(s, pos, bots=SPOT_BOTS, label=None):
        """A spot to cover: the nearest `bots` free bots go there first (replanned at once). label: a gametype
        objective's role (tools/lidar.py Objectives: one bot each), None for a spot a person marked."""
        sp = dict(pos=tuple(float(v) for v in pos), done=False, given_up=False, since=None, bots=bots, label=label)
        s.spots.append(sp)
        s.next_t = 0.0
        return sp

    def clear_spots(s):
        """The spots a person marked (the objectives stay)."""
        keep = [k for k, sp in enumerate(s.spots) if sp.get("label")]
        s.spots = [s.spots[k] for k in keep]
        s.jobs = {k: (*j[:2], keep.index(j[2]), *j[3:]) if j[0] == "spot" else j
                  for k, j in s.jobs.items() if j[0] != "spot" or j[2] in keep}
        s.next_t = 0.0

    def spot_view(s):
        """[{pos, done, given_up, bots}] for the view."""
        on = {}
        for j in s.jobs.values():
            if j[0] == "spot":
                on[j[2]] = on.get(j[2], 0) + 1
        return [dict(pos=[round(v, 2) for v in sp["pos"]], done=sp["done"], given_up=sp["given_up"], bots=on.get(k, 0),
                     label=sp.get("label")) for k, sp in enumerate(s.spots)]

    def _spots(s, now, bots):
        """Marks spots covered (a bot got there) or given up, and sends the nearest free bots to the open ones."""
        for k, sp in enumerate(s.spots):
            if sp["done"] or sp["given_up"]:
                continue
            x, y, z = sp["pos"]
            if any(math.hypot(p[0] - x, p[1] - y) < SPOT_DONE_R and abs(p[2] - z) < 2.0 for p in bots.values()):
                sp["done"] = True
            elif sp["since"] is not None and now - sp["since"] > SPOT_GIVE_UP:
                sp["given_up"] = True
        open_ = {k for k, sp in enumerate(s.spots) if not sp["done"] and not sp["given_up"]}
        s.jobs = {i: j for i, j in s.jobs.items() if j[0] != "spot" or (j[2] in open_ and i in bots)}
        cost = lambda p, sp: math.hypot(p[0] - sp["pos"][0], p[1] - sp["pos"][1]) + 2.0 * abs(p[2] - sp["pos"][2])
        is_free = lambda i: s.jobs.get(i, (None,))[0] not in ("spot", "jump")
        for k in sorted(open_):
            sp = s.spots[k]
            if sp.get("label"):
                continue                              # (objectives: below)
            have = sum(1 for j in s.jobs.values() if j[0] == "spot" and j[2] == k)
            free = sorted((cost(p, sp), i) for i, p in bots.items() if is_free(i))
            for _, i in free[:max(0, sp.get("bots", SPOT_BOTS) - have)]:
                s.jobs[i] = ("spot", sp["pos"], k, now)
                s.new_spot_bots.append(i)
            if sp["since"] is None and (have or free):
                sp["since"] = now
        # objectives: one bot each, the nearest free bot and objective paired first, at most OBJECTIVE_SHARE of the
        # bots at a time (the rest keep painting the map)
        taken = {j[2] for j in s.jobs.values() if j[0] == "spot"}
        want = [k for k in sorted(open_) if s.spots[k].get("label") and k not in taken]
        on = sum(1 for j in s.jobs.values() if j[0] == "spot" and s.spots[j[2]].get("label"))
        free = [i for i in bots if is_free(i)]
        while want and free and on < max(1, math.ceil(OBJECTIVE_SHARE * len(bots))):
            _, i, k = min((cost(bots[i], s.spots[k]), i, k) for i in free for k in want)
            s.jobs[i] = ("spot", s.spots[k]["pos"], k, now)
            s.new_spot_bots.append(i)
            if s.spots[k]["since"] is None:
                s.spots[k]["since"] = now
            free.remove(i)
            want.remove(k)
            on += 1

    def _reach(s):
        """Reachable sample cells: Terrain.reach, recomputed over graph_h (new links bots landed count at once)."""
        T = s.T
        if s.spawns:
            T.set_spawns(s.spawns)
        reach = getattr(T, "reach", None)
        if reach is None:
            return np.ones(len(s.x), bool)
        return reach[s.l, s.j * STEP, s.i * STEP]

    def _reach_safe(s, reach):
        """The reachable samples a walk gets to from the spawns without stepping on kill-zone floor (Terrain.oob): floor
        only a kill or soft kill zone leads to is behind it (live Zealot: the side decks past a soft kill walkway,
        where 30 bots died on the way). Cached per nav graph and kill-zone mask."""
        T, oob = s.T, getattr(s.T, "oob", None)
        g = getattr(T, "graph_h", getattr(T, "graph", None))
        if oob is None or g is None or not oob.any() or not s.spawns:
            return reach
        key = (id(g), g.nnz, id(oob), int(oob.sum()))
        if getattr(s, "_safe_key", None) != key:
            from scipy.sparse.csgraph import breadth_first_order
            from brain.core import Vec
            flat = oob.ravel()
            g2 = g.copy()
            g2.data[flat[g2.indices]] = 0          # (no edge into a kill-zone node)
            g2.eliminate_zeros()
            safe = np.zeros(flat.size, bool)
            for p in s.spawns:
                if not T.inside(p.x, p.y):
                    continue
                l, j, i = T._node(p if hasattr(p, "x") else Vec(*p))
                n = (l * T.nh + j) * T.nw + i
                if not flat[n] and not safe[n]:
                    safe[breadth_first_order(g2, n, directed=True, return_predecessors=False)] = True
            s._safe_key, s._safe = key, safe.reshape(oob.shape)
            s.safe_graph = g2                         # (Roomba.frontier searches on it: no goal across a kill zone)
        return reach & s._safe[s.l, s.j * STEP, s.i * STEP]

    def _pieces(s, mask, tiled=False, least=PATCH_MIN):
        """Connected pieces of the sample cells in mask, per floor level (8-neighbour in the plane), cut by tile if
        tiled: [(size, centre sample index, member sample indices)] with the centre the member nearest the piece's
        mean, biggest first; pieces under `least` samples left out."""
        from scipy.ndimage import label
        members = np.nonzero(mask)[0]
        if not len(members):
            return []
        grid = np.zeros(s.shape, bool)
        grid[s.l[members], s.j[members], s.i[members]] = True
        lab, _ = label(grid, structure=np.array([[[0] * 3] * 3, [[1] * 3] * 3, [[0] * 3] * 3]))
        key = lab[s.l[members], s.j[members], s.i[members]].astype(np.int64)
        if tiled:
            key = key * s.ntiles + s.tile[members]
        _, inv = np.unique(key, return_inverse=True)
        order = np.argsort(inv, kind="stable")
        cuts = np.searchsorted(inv[order], np.arange(inv.max() + 2))
        out = []
        for k in range(len(cuts) - 1):
            if cuts[k + 1] - cuts[k] < least:
                continue
            m = members[order[cuts[k]:cuts[k + 1]]]
            mx, my = s.x[m].mean(), s.y[m].mean()
            c = m[np.argmin((s.x[m] - mx) ** 2 + (s.y[m] - my) ** 2)]
            out.append((len(m), int(c), m))
        return sorted(out, key=lambda r: -r[0])

    def _open(s, m):
        """Is a patch (its members) still one to send bots to (not left after PATCH_TRIES failed tries)?"""
        return int(s.tries[m].max()) < PATCH_TRIES

    def plan(s, now, bots):
        """bots: {index: (x, y, z)} of the living mapping bots. Recomputes the coverage map and gives out jobs."""
        if now < s.next_t:
            return
        s.next_t, s.now = now + PERIOD, now
        t0 = time.time()
        s.painted = painted = s.rec.explored_many(s.x, s.y, s.z)
        reach = s._reach()
        oob = getattr(s.T, "oob", None)              # the map's kill zones and learned out of bounds (Terrain.set_oob)
        s.kz = oob[s.l, s.j * STEP, s.i * STEP] if oob is not None else np.zeros(len(s.x), bool)
        safe = s._reach_safe(reach)
        s.behind = reach & ~safe & ~s.kz            # reachable only through a kill zone: not floor to cover
        s.reach, s.want = reach, safe & ~s.kz
        want = s.want
        s.reach_share = float(reach.mean()) if len(reach) else 0.0
        s.coverage = s.painted_share = float((painted & want).sum() / max(1, want.sum()))
        s.history.append((round(now, 1), round(s.coverage, 4)))
        if s.reached_at is None and s.coverage >= TARGET:
            s.reached_at = now
        s.patches = s._pieces(want & ~painted, tiled=True)
        s.patch_of[:] = 0
        for k, (_, _, m) in enumerate(s.patches):
            s.patch_of[m] = k + 1
        s.patch_grid[:] = 0
        s.patch_grid[s.l, s.j, s.i] = s.patch_of
        s.islands = s._pieces(~reach & ~s.kz & ~painted, least=MIN_CELLS)
        if now - s.retry_t >= PATCH_RETRY:            # patches left are offered again (new links may reach them now)
            s.retry_t = now
            s.tries[want] = 0
        s._spots(now, bots)
        s.jobs = {i: j for i, j in s.jobs.items() if i in bots}   # (a dead bot respawns elsewhere: planned afresh)
        taken = set()
        for idx, pos in sorted(bots.items()):
            job = s.jobs.get(idx)
            if not job or job[0] == "spot":
                continue                              # (a marked spot or an objective: _spots keeps or ends it)
            if job[0] == "go":
                ids = s.patch_of[job[2]]
                ids = ids[ids > 0]
                k = int(np.bincount(ids).argmax()) - 1 if len(ids) else -1   # its patch now (painted floor drops out)
                if k < 0 or k in taken or not s._open(s.patches[k][2]):
                    s.jobs.pop(idx)                   # filled, or another bot's
                    continue
                m = s.patches[k][2]
                since, best = (now if len(m) < job[4] else job[3]), job[7]   # painted some: the clock starts again
                if job[6]:                            # walking there: a step closer (APPROACH) counts too (a long
                    p = pos                           # walk is no failed try; stuck, or going round in circles, is)
                    dn = float(np.min(np.hypot(s.x[m] - p[0], s.y[m] - p[1]) + 2.0 * np.abs(s.z[m] - p[2])))
                    if dn < best - APPROACH:
                        since, best = now, dn
                if now - since > PATCH_S:             # none painted for PATCH_S: another patch for it, and if it was
                    if job[6]:                        # walking there (fallback), a failed try
                        s.tries[m] += 1
                    s.jobs.pop(idx)
                    continue
                s.jobs[idx] = ("go", None, m, since, min(len(m), job[4]), k, job[6], best)
                taken.add(k)
                continue
            if job[0] == "jump" and now - job[3] < JUMP_JOB_S:
                continue                              # (a take-off it never gets to: dropped after JUMP_JOB_S)
            s.jobs.pop(idx, None)
        # islands: the nearest bot (not already on one) within reach of each, one bot an island
        on_island = {j[2] for j in s.jobs.values() if j[0] == "jump"}
        # (only once most of the walkable floor is painted: jump tries early on cost the walking bots a sixth of their
        # painting in the simulator, Boneyard; half the bots once the floor is at TARGET)
        late = ISLANDS and s.coverage >= ISLAND_AFTER
        most = ISLAND_BOTS if s.coverage < TARGET else max(ISLAND_BOTS, len(bots) // 2)
        isl = [r for r in s.islands if int(s.tries[r[2]].max()) < ISLAND_TRIES][:6] if late else []
        near = np.nonzero(want)[0]
        for size, c, members in isl:
            if c in on_island or len(on_island) >= most or not len(near):
                continue
            free = [(math.hypot(p[0] - s.x[c], p[1] - s.y[c]), idx) for idx, p in bots.items() if idx not in s.jobs]
            free = [f for f in free if f[0] < ISLAND_REACH]
            if not free:
                continue
            _, idx = min(free)
            # the take-off side: the reachable cell nearest the island, and the island's floor nearest it to aim at
            k = near[np.argmin((s.x[near] - s.x[c]) ** 2 + (s.y[near] - s.y[c]) ** 2)]
            a = members[np.argmin((s.x[members] - s.x[k]) ** 2 + (s.y[members] - s.y[k]) ** 2)]
            s.jobs[idx] = ("jump", (float(s.x[k]), float(s.y[k]), float(s.z[k])), c, now, members,
                           (float(s.x[a]), float(s.y[a]), float(s.z[a])))
            on_island.add(c)
        # patches: every free bot paired with an open patch, best pair first (big and near), one bot a patch
        free = [i for i in sorted(bots) if i not in s.jobs]
        cand = [k for k, (_, _, m) in enumerate(s.patches) if k not in taken and s._open(m)]
        if free and cand:
            cs = np.array([s.patches[k][1] for k in cand])
            size = np.array([s.patches[k][0] for k in cand], float)
            tries = np.array([int(s.tries[s.patches[k][2]].max()) for k in cand], float)
            B = np.array([bots[i] for i in free], float)
            d = np.hypot(B[:, None, 0] - s.x[cs][None], B[:, None, 1] - s.y[cs][None]) + 2.0 * np.abs(B[:, None, 2] - s.z[cs][None])
            v = np.sqrt(size)[None] / (1.0 + d / 20.0) / (1.0 + tries)[None]
            for _ in range(min(len(free), len(cand))):
                a, b = np.unravel_index(int(np.argmax(v)), v.shape)
                k, m = cand[b], s.patches[cand[b]][2]
                s.jobs[free[a]] = ("go", None, m, now, len(m), k, False, math.inf)
                v[a, :] = v[:, b] = -1.0
        # every open patch's floor, as nav nodes: Roomba.frontier's candidates (its random sample misses small patches).
        # Not slivers under MIN_CELLS: those are paint noise along edges, and chasing every one of them cost ODST Data
        # Hive 8% (the nearest unpainted node is then nearly always one)
        op = np.concatenate([m for n, _, m in s.patches if n >= MIN_CELLS and s._open(m)] or [np.zeros(0, np.int64)])
        s.open_nodes = (s.l[op] * s.T.nh + s.j[op] * STEP) * s.T.nw + s.i[op] * STEP
        s.plan_s = time.time() - t0

    def job(s, index, pos):
        """("go", target) / ("call", aim) for this bot, or None (its own frontier, its patch first). A jump job at its
        take-off side: ("call", the island's floor to aim at)."""
        j = s.jobs.get(index)
        if not j:
            return None
        if j[0] == "spot":
            return ("go", j[1])
        if j[0] == "jump":
            if math.hypot(pos[0] - j[1][0], pos[1] - j[1][1]) < JUMP_NEAR:
                s.jobs.pop(index, None)
                s.tries[j[4]] += 1                    # (a jump called for it: ISLAND_TRIES and it is left)
                return ("call", j[5])
            return j[:2]
        # a patch: the bot's own frontier (nearest unpainted floor by path) prefers it (region_bias); straight targets
        # ignored walls and floors and painted a third less (sim, Boneyard). Only when the frontier finds nothing near:
        # fallback
        return None

    def fallback(s, index, pos):
        """The bot's frontier found no unpainted floor within its search (150 units of path): the nearest floor of its
        patch to walk to, or of the best open patch no bot has (taken now), instead of wandering. None: nothing open, or
        coverage still under TARGET (A/B, 16 maps x 2 seeds in the simulator: walking off to far patches earlier lost
        Tower, Snowbound, Construct and Data Hive 2-9% against the wander, which paints floor the frontier skips)."""
        j = s.jobs.get(index)
        if s.coverage < TARGET or (j and j[0] in ("spot", "jump")):
            return None
        if not j:
            mine = {jj[5] for jj in s.jobs.values() if jj[0] == "go"}
            cand = [(math.sqrt(n) / (1.0 + (math.hypot(pos[0] - s.x[c], pos[1] - s.y[c]) + 2 * abs(pos[2] - s.z[c])) / 20.0), k)
                    for k, (n, c, m) in enumerate(s.patches) if k not in mine and s._open(m)]
            if not cand:
                return None
            k = max(cand)[1]
            m = s.patches[k][2]
            j = ("go", None, m, s.now, len(m), k, True, math.inf)
        m = j[2]
        k = int(np.argmin(np.hypot(s.x[m] - pos[0], s.y[m] - pos[1]) + 2.0 * np.abs(s.z[m] - pos[2])))
        # (walking there: no paint for PATCH_S from now is a failed try)
        s.jobs[index] = (*j[:3], j[3] if j[6] else s.now, j[4], j[5], True, j[7] if j[6] else math.inf)
        return (float(s.x[m[k]]), float(s.y[m[k]]), float(s.z[m[k]]))

    def region_bias(s, index, ll, jj, ii):
        """For Roomba.frontier: an extra score (in path units) for candidate nav nodes inside this bot's patch."""
        j = s.jobs.get(index)
        if not j or j[0] != "go":
            return 0.0
        g = s.patch_grid
        inside = g[ll, np.minimum(jj // STEP, g.shape[1] - 1), np.minimum(ii // STEP, g.shape[2] - 1)] == j[5] + 1
        return PATCH_BONUS * inside

    def open_work(s):
        """Is there still something to send bots to: the floor under TARGET (patches left are offered again every
        PATCH_RETRY s), an open patch of PATCH_BIG or more, or an objective (or a marked spot) not reached? (The
        simulator stops a map early only when there is not: stopping once every patch was left ended Tower at 89%.)"""
        if s.coverage < TARGET or any(n >= PATCH_BIG and s._open(m) for n, _, m in s.patches):
            return True
        return any(not sp["done"] and not sp["given_up"] for sp in s.spots)

    def done(s):
        """Coverage at TARGET, no open patch of PATCH_BIG samples or more, no objective (or marked spot) left to visit."""
        return s.coverage >= TARGET and not any(n >= PATCH_BIG and s._open(m) for n, _, m in s.patches) and             not any(not sp["done"] and not sp["given_up"] for sp in s.spots)

    def report(s):
        """What the map's shape is and what is left: coverage, regions and levels, the open patches and the islands,
        biggest first, each with its reason. Plain numbers (saved as JSON)."""
        a = s.cell ** 2                               # u2 a sample
        want, painted = s.want, s.painted
        regions = s._pieces(want, tiled=True, least=1)
        z = np.round(s.z[want] / 3.0).astype(int) if want.any() else np.zeros(0, int)
        lv, n = np.unique(z, return_counts=True)
        r2 = lambda p: [round(float(v), 1) for v in p]
        bots = {j[5]: i for i, j in s.jobs.items() if j[0] == "go"}
        patches = []
        for k, (n_, c, m) in enumerate(s.patches):
            t = int(s.tries[m].max())
            fell = s.rec.near_fall(float(s.x[c]), float(s.y[c]), float(s.z[c])) if hasattr(s.rec, "near_fall") else False
            why = (f"no way found: {t} bots sent there painted none of it" if t >= PATCH_TRIES else
                   f"bot {bots[k]} on it" if k in bots else
                   "a bot fell beside it: bots keep off" if fell else
                   "paint noise along an edge" if n_ < 6 else "not reached yet")
            patches.append(dict(pos=r2((s.x[c], s.y[c], s.z[c])), area=round(n_ * a, 2), reason=why, tries=t))
        islands = []
        rides = [f for f in getattr(s.rec, "features", ()) or () if f.get("kind") in ("lift", "launcher", "teleporter")
                 and len(f.get("pos") or ()) >= 2]
        near = np.nonzero(want)[0]
        for n_, c, m in s.islands:
            t = int(s.tries[m].max())
            if len(near):
                k = near[np.argmin((s.x[near] - s.x[c]) ** 2 + (s.y[near] - s.y[c]) ** 2)]
                gap, dz = float(math.hypot(s.x[k] - s.x[c], s.y[k] - s.y[c])), float(s.z[c] - s.z[k])
            else:
                gap, dz = float("inf"), 0.0
            kind = ("detached" if gap > DETACHED else "above" if dz > 1.0 else "below" if dz < -1.0 else "level")
            why = {"detached": f"no reachable floor within {DETACHED:g} u: a lift, man cannon or teleporter only, or "
                               "outside the play space",
                   "above": f"{dz:.1f} u above the reachable floor: a jump-up, lift or climb",
                   "below": f"{-dz:.1f} u below the reachable floor: a drop the nav does not take",
                   "level": "cut off at the same height: a gap or a wall between"}[kind]
            ride = next((f for f in rides if math.hypot(f["pos"][0] - s.x[c], f["pos"][1] - s.y[c]) < RIDE_NEAR
                         or math.hypot(f["pos"][0] - s.x[k], f["pos"][1] - s.y[k]) < RIDE_NEAR), None) if len(near) else None
            if ride is not None and kind != "below":
                why += f"; a {ride['kind']} near it" + (f" ({ride['name']})" if ride.get("name") else "") +                     " is the way (rides are learned in matches)"
            if t:
                why += f"; {t} jump call{'s' if t > 1 else ''} made for it"
            islands.append(dict(pos=r2((s.x[c], s.y[c], s.z[c])), area=round(n_ * a, 2), kind=kind, reason=why, tries=t))
        return dict(coverage=round(s.coverage, 4), target=TARGET,
                    reached_at=round(s.reached_at, 1) if s.reached_at is not None else None,
                    floor_u2=round(float(want.sum()) * a, 1), painted_u2=round(float((want & painted).sum()) * a, 1),
                    killzone_u2=round(float((s.kz & s.reach).sum()) * a, 1),
                    unreachable_u2=round(float(sum(r[0] for r in s.islands)) * a, 1),
                    behind_kill_zone_u2=round(float(s.behind.sum()) * a, 1),
                    behind_kill_zone=[dict(pos=r2((s.x[c], s.y[c], s.z[c])), area=round(n_ * a, 2),
                                           reason="behind a kill zone: every way there crosses kill-zone floor")
                                      for n_, c, _ in s._pieces(s.behind, least=MIN_CELLS)[:20]],
                    regions=len(regions), levels=int((n * a >= 4.0).sum()),
                    open_u2=round(float(sum(r[0] for r in s.patches)) * a, 1),
                    patches=patches[:40], islands=islands[:40], n_patches=len(patches), n_islands=len(islands),
                    history=s.history[::max(1, len(s.history) // 60)])

    def lines(s):
        """The report as markdown lines (logs/lidar_<map>.md, the simulator's log)."""
        r = s.report()
        out = [f"- Coverage {100 * r['coverage']:.1f}% of the reachable floor ({r['painted_u2']:.0f} of {r['floor_u2']:.0f} "
               f"u2; kill zones left out: {r['killzone_u2']:.0f} u2), target {100 * TARGET:.0f}%"
               + (f" reached at {r['reached_at']:.0f} s" if r["reached_at"] is not None else " not reached"),
               f"- Map shape: {r['regions']} regions ({TILE:g} u tiles of connected floor) over {r['levels']} levels; "
               f"{r['n_patches']} patches open ({r['open_u2']:.0f} u2), {r['n_islands']} islands no walk reaches "
               f"({r['unreachable_u2']:.0f} u2), {r['behind_kill_zone_u2']:.0f} u2 behind kill zones (left out)"]
        for p in r["patches"][:12]:
            out.append(f"  - patch {p['area']:.1f} u2 at {p['pos']}: {p['reason']}")
        for p in r["islands"][:12]:
            out.append(f"  - island {p['area']:.1f} u2 at {p['pos']}: {p['reason']}")
        for p in r["behind_kill_zone"][:8]:
            out.append(f"  - {p['area']:.1f} u2 at {p['pos']}: {p['reason']}")
        return out

    def view(s):
        """Coverage and the open patches for the LiDAR view: patches [x, y, z, area, state] (0 open, 1 a bot on it,
        2 left: no way found)."""
        a = s.cell ** 2
        on = {j[5] for j in s.jobs.values() if j[0] == "go"}
        return dict(coverage=round(s.coverage, 4), target=TARGET, open_u2=round(float(sum(r[0] for r in s.patches)) * a, 1),
                    patches=[[round(float(s.x[c]), 2), round(float(s.y[c]), 2), round(float(s.z[c]), 2), round(n * a, 2),
                              1 if k in on else 0 if s._open(m) else 2] for k, (n, c, m) in enumerate(s.patches[:150])],
                    islands=len(s.islands))

    def line(s, now):
        """A status line every 30 s (None in between)."""
        if now - s.last_line < 30.0:
            return None
        s.last_line = now
        jobs = ", ".join(f"{i}:{j[0]}" for i, j in sorted(s.jobs.items()))
        left = sum(1 for _, _, m in s.patches if not s._open(m))
        return (f"director: {100 * s.coverage:.0f}% of the reachable floor covered (target {100 * TARGET:.0f}%, kill zones "
                f"left out), {len(s.patches)} patches open" + (f" ({left} with no way found)" if left else "") +
                f", {len(s.islands)} islands, plan {getattr(s, 'plan_s', 0):.2f} s; jobs {jobs or 'none'}")
