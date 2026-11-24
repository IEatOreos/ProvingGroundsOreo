"""(custom, Nov 23) Route-search helpers: the nav's route fields (brain/terrain.py Terrain._field, a Dijkstra over every node
of the map) worked out in helper processes on other cores.

The owner, on 8v8: "The bots play really bad in 8v8 and idk why, Almost unplayable"; then, of the ways to give the bots
room, "Do 1 and 4 through completion". The brain runs on one thread; full route fields were about half of its slow
passes (8v8 Forge World CTF, logs/brain_profile_reach_forge_halo_20261123-190955.txt, 33 ms each on its 3.46 million
nodes). Python's threads take turns (8 searches on 8 threads: 1.1x), so the helpers are processes.

How it works:
- The helpers hold a copy of the nav's graphs in shared memory (Pool.bind / publish), never the brain's own: the brain
  changes edge weights in place for a moment (Terrain._field's risky edges) and for good (a learned stuck spot, out of
  bounds: Terrain._fields cleared, FieldCache.gen), and a changed graph is published again under a new version; a
  result worked out on an older version is dropped.
- Results land in shared-memory slots (SLOTS of the map's node count), read in place: no copy. A slot is used again
  only once nothing has read its field for SLOT_HOLD_S (a field in use by a think is never overwritten).
- Terrain._field asks the pool (lookup) before it searches: a field the pool finished goes into the cache; one a helper
  is working on is waited for (WAIT_S); while a helper works out a field, one the cache has for a goal within NEAR_R of it
  (the same floor, the same search) stands in, so a chase never waits for its moving target's field.
- tools/live_bots.py asks ahead (Terrain.prefetch) at the start of each pass for the fields its bots are likely to
  want: their goals', worked out on the helpers while the bots think.

Only numpy and scipy in the helpers: they start quickly and load nothing of the brain.
usage (Pool starts them): python -I field_pool.py --worker   (one JSON request a line in, one JSON reply a line out)
"""
import json
import math
import os
import queue
import subprocess
import sys
import threading
import time

WORKERS = 3            # helper processes (the PC: 8 cores; the game, the brain and Windows keep the rest)
SLOTS = 24             # result slots (each the map's node count of float64: 27.7 MB on a 3.46 million node layout)
SLOT_HOLD_S = 0.5      # s: a slot read this lately is not used again (a think may still hold its field)
WAIT_S = 0.08          # s: the longest a field a helper is working on is waited for
NEAR_R, NEAR_DZ = 1.5, 0.6   # u: a cached field this near (flat; up or down) stands in while the exact one is worked out
PENDING_MAX = 48       # requests waiting for a helper, the oldest dropped past this
JOB_OLD_S = 1.0        # s: a request waiting this long is dropped (its bot has moved on)
KINDS = ("walk", "jump", "h")
# (custom, Nov 23, the owner: "And then 3 afterwards") the fixed targets' fields (flag stands, objectives, posts, power
# items: tools/live_bots.py fixed_targets), worked out by the helpers at the match's start and kept all match (pin): no
# bot searches its way to one again. PIN_BYTES of them at most (a 3.46 million node layout: 21 fields)
PIN_BYTES = 600e6


def _python():
    exe = sys.executable
    head, tail = os.path.split(exe)
    if tail.lower() == "pythonw.exe" and os.path.exists(os.path.join(head, "python.exe")):
        return os.path.join(head, "python.exe")
    return exe


class _Helper:
    def __init__(s, cmd):
        flags = 0x08000000 if os.name == "nt" else 0          # CREATE_NO_WINDOW
        s.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  creationflags=flags)
        s.replies = queue.Queue()
        s.job = None                                          # the job it is on: (jid, cache name, ckey, slot)
        out, q = s.proc.stdout, s.replies

        def read():
            try:
                for line in out:
                    q.put(line)
            except (OSError, ValueError):
                pass
            q.put(None)
        threading.Thread(target=read, daemon=True).start()

    def send(s, msg):
        s.proc.stdin.write((json.dumps(msg) + "\n").encode("utf-8"))
        s.proc.stdin.flush()

    def alive(s):
        return s.proc.poll() is None

    def stop(s):
        try:
            s.proc.stdin.close()
            s.proc.wait(timeout=3)
        except Exception:
            try:
                s.proc.kill()
                s.proc.wait(timeout=3)
            except Exception:
                pass
        try:
            s.proc.stdout.close()
        except Exception:
            pass


def _locked(fn):
    """(custom, Nov 23) One of the Pool's methods at a time: the bots may think on several threads (brain/threads.py)."""
    import functools

    @functools.wraps(fn)
    def run(s, *a, **k):
        with s._lock:
            return fn(s, *a, **k)
    return run


class Pool:
    """The helpers and their shared memory, for one Terrain at a time (bind). Its methods take turns (a lock: the bots may
    think on several threads); no_wait: a think thread never waits for a helper's field (it searches it itself)."""

    def __init__(s, workers=WORKERS, slots=SLOTS, cmd=None):
        s._lock = threading.RLock()
        s.no_wait = False
        s.cmd = cmd or [_python(), "-I", os.path.abspath(__file__), "--worker"]
        s.n_workers, s.n_slots = workers, slots
        s.helpers, s.T, s.shape, s.n = [], None, None, 0
        s.graph_shm, s.graph_of, s.graph_ver = {}, {}, {}     # kind -> [SharedMemory]; graph object; version
        s.slot_shm, s.slot_view, s.slot_used, s.slot_owner = [], [], [], []
        s.inflight = {}                                       # (cache id, ckey) -> (helper, jid)
        s.pending = []                                        # [(t, cache, ckey, kind, start, limit, goal)]
        s.done_ids, s.view_slot = {}, {}                      # jid -> result; id(view) -> slot
        s.near_index = {}                                     # (cache id, ckey prefix) -> {ckey: goal}
        s.pinned, s.pin_want, s.pin_dirty = {}, {}, False   # (cache id, ckey) -> field kept all match; -> its ask
        s.jid, s.gen = 0, None
        s.broken = None
        s.stats = dict(jobs=0, used=0, near=0, waited=0, dropped=0, stale=0)

    # --- setting up
    @_locked
    def bind(s, T):
        """Use the pool for T: its result slots sized to T's nodes, its graphs published (again when T changed)."""
        if s.broken:
            return False
        try:
            from multiprocessing import shared_memory
            import numpy as np
            shape = (T.L, T.nh, T.nw)
            if s.T is not T or s.shape != shape:
                s._drop_all()
                s.T, s.shape, s.n = T, shape, T.L * T.nh * T.nw
                for _ in range(s.n_slots):
                    m = shared_memory.SharedMemory(create=True, size=max(8, s.n * 8))
                    s.slot_shm.append(m)
                    s.slot_view.append(np.ndarray(shape, dtype=np.float64, buffer=m.buf))
                    s.slot_used.append(0.0)
                    s.slot_owner.append(None)
                while len(s.helpers) < s.n_workers:
                    s.helpers.append(_Helper(s.cmd))
                for h in s.helpers:
                    h.send(dict(op="slots", names=[m.name for m in s.slot_shm], shape=list(shape)))
            s._sync_graphs()
            return True
        except Exception as e:
            s._break(e)
            return False

    def _graphs(s):
        T = s.T
        return {"walk": getattr(T, "graph_to", None), "jump": getattr(T, "graph_jump_to", None),
                "h": getattr(T, "graph_h_to", None)}

    def _sync_graphs(s):
        """Publish each graph again when it is a new object or T's weights changed (FieldCache.gen) since."""
        from multiprocessing import shared_memory
        import numpy as np
        gen = getattr(getattr(s.T, "_fields", None), "gen", 0)
        for kind, g in s._graphs().items():
            if g is None:
                continue
            same = s.graph_of.get(kind) is g and s.graph_shm.get(kind) is not None
            if same and s.gen == gen:
                continue
            arrs = (np.ascontiguousarray(g.indptr), np.ascontiguousarray(g.indices),
                    np.ascontiguousarray(g.data, dtype=np.float64))
            old = s.graph_shm.get(kind)
            if same and old is not None and all(m.size >= a.nbytes for m, a in zip(old, arrs)):
                shms = old                              # (only the weights changed: written over in place)
            else:
                shms = [shared_memory.SharedMemory(create=True, size=max(8, a.nbytes)) for a in arrs]
            for m, a in zip(shms, arrs):
                np.ndarray(a.shape, dtype=a.dtype, buffer=m.buf)[:] = a
            ver = s.graph_ver.get(kind, 0) + 1
            s.graph_ver[kind], s.graph_of[kind] = ver, g
            msg = dict(op="graph", kind=kind, ver=ver, n=g.shape[0],
                       parts=[[m.name, list(a.shape), a.dtype.str] for m, a in zip(shms, arrs)])
            for h in s.helpers:
                h.send(msg)
            s.pin_dirty = True                          # (the kept fields are of the old graph: worked out again)
            if old is not None and shms is not old:
                for m in old:
                    _close(m)
            s.graph_shm[kind] = shms
        s.gen = gen

    # --- asking
    @_locked
    def submit(s, cache, ckey, kind, start, limit, goal, now=None, pin=False):
        """Ask for the field to node start on graph kind (Terrain._field's ckey into cache), unless it is cached, in
        flight or waiting already. pin: kept all match (pinned), never dropped as old."""
        if s.broken or s.T is None or (ckey in cache and not pin):
            return
        k = (id(cache), ckey)
        if k in s.inflight or any(p[1] is cache and p[2] == ckey for p in s.pending):
            return
        s.pending.append((now if now is not None else time.perf_counter(), cache, ckey, kind, start, limit, goal, pin))
        if len(s.pending) > PENDING_MAX:
            drop = next((i for i, p in enumerate(s.pending) if not p[7]), 0)
            s.pending.pop(drop)
            s.stats["dropped"] += 1
        s._dispatch()

    @_locked
    def pin(s, cache, ckey, kind, start, limit, goal):
        """A fixed target's field (Terrain.pin_targets): worked out once and kept all match (PIN_BYTES in all)."""
        k = (id(cache), ckey)
        if s.broken or s.T is None or k in s.pin_want or (len(s.pin_want) + 1) * s.n * 8 > PIN_BYTES:
            return
        s.pin_want[k] = (cache, ckey, kind, start, goal)
        s.submit(cache, ckey, kind, start, None, goal, pin=True)

    def _free_slot(s, now):
        best = None
        for i, used in enumerate(s.slot_used):
            if now - used < SLOT_HOLD_S or any(h.job is not None and h.job[3] == i for h in s.helpers):
                continue
            if best is None or used < s.slot_used[best]:
                best = i
        return best

    def _dispatch(s):
        now = time.perf_counter()
        s.pending = [p for p in s.pending if p[7] or now - p[0] < JOB_OLD_S]
        try:
            s._sync_graphs()
        except Exception as e:
            s._break(e)
            return
        if s.pin_dirty:                                 # (a graph published again: its kept fields worked out anew)
            s.pin_dirty = False
            s.pinned.clear()
            asked = {(id(p[1]), p[2]) for p in s.pending}
            for k, (cache, ckey, kind, start, goal) in s.pin_want.items():
                if k not in asked and k not in s.inflight:
                    s.pending.append((now, cache, ckey, kind, start, None, goal, True))
        for h in s.helpers:
            if not s.pending:
                return
            if h.job is not None:
                continue
            slot = s._free_slot(now)
            if slot is None:
                return
            t, cache, ckey, kind, start, limit, goal, pin = s.pending.pop(0)
            if ckey in cache and not pin:
                continue
            s._release(slot)
            s.jid += 1
            h.job = (s.jid, cache, ckey, slot, kind, s.graph_ver.get(kind), goal, pin)
            s.slot_used[slot] = now            # (taken: not handed out again until read and SLOT_HOLD_S old)
            s.inflight[(id(cache), ckey)] = (h, s.jid)
            try:
                h.send(dict(op="job", id=s.jid, kind=kind, ver=s.graph_ver.get(kind), start=int(start),
                            limit=None if limit is None else float(limit), slot=slot))
                s.stats["jobs"] += 1
            except Exception as e:
                s._break(e)
                return

    def _release(s, slot):
        """The slot's old field out of its cache (only if the cache still holds that very array)."""
        own = s.slot_owner[slot]
        s.slot_owner[slot] = None
        if own is not None:
            cache, ckey = own
            if cache.get(ckey) is s.slot_view[slot]:
                cache.pop(ckey, None)

    @_locked
    def drain(s, keep):
        """Take the helpers' finished fields into their caches (keep: brain/terrain.py keep_field)."""
        if s.broken:
            return
        for h in s.helpers:
            while True:
                try:
                    line = h.replies.get_nowait()
                except queue.Empty:
                    break
                if line is None:
                    s._break(RuntimeError("a helper stopped"))
                    return
                s._finish(h, json.loads(line), keep)
        if s.pending:
            s._dispatch()

    def _finish(s, h, r, keep):
        job, h.job = h.job, None
        if job is None or r.get("id") != job[0]:
            return
        jid, cache, ckey, slot, kind, ver, goal, pin = job
        s.inflight.pop((id(cache), ckey), None)
        if not r.get("ok") or ver != s.graph_ver.get(kind) or s.graph_of.get(kind) is not s._graphs().get(kind):
            s.stats["stale"] += 1
            if pin and (id(cache), ckey) in s.pin_want:       # (asked again on the new graph)
                s.pin_dirty = True
            return
        view = s.slot_view[slot]
        if pin:                                          # (a kept field: copied out, its slot free at once)
            import numpy as np
            s.pinned[(id(cache), ckey)] = np.array(view)
            s.slot_used[slot] = 0.0
            s.stats["pinned"] = len(s.pinned)
            return
        s.slot_owner[slot] = (cache, ckey)
        s.slot_used[slot] = time.perf_counter()
        s.view_slot[id(view)] = slot
        keep(cache, ckey, view)
        s.note(cache, ckey, goal)

    @_locked
    def wait(s, cache, ckey, keep, timeout=WAIT_S):
        """The field a helper is working on, waited for up to timeout; None."""
        k = (id(cache), ckey)
        fl = s.inflight.get(k)
        if fl is None:
            return None
        h = fl[0]
        end = time.perf_counter() + timeout
        while k in s.inflight:
            left = end - time.perf_counter()
            if left <= 0:
                return None
            try:
                line = h.replies.get(timeout=left)
            except queue.Empty:
                return None
            if line is None:
                s._break(RuntimeError("a helper stopped"))
                return None
            s._finish(h, json.loads(line), keep)
        s.stats["waited"] += 1
        return cache.get(ckey)

    # --- what the cache holds
    @_locked
    def touch(s, f):
        """A field read now: its slot (if one) not used again for SLOT_HOLD_S."""
        slot = s.view_slot.get(id(f))
        if slot is not None and s.slot_view[slot] is f:
            s.slot_used[slot] = time.perf_counter()

    @_locked
    def note(s, cache, ckey, goal):
        """A field now in cache for goal: a stand-in for goals NEAR_R from it (near)."""
        if goal is None or not isinstance(ckey, tuple) or len(ckey) < 3:
            return
        idx = s.near_index.setdefault((id(cache), ckey[:-3]), {})
        idx.pop(ckey, None)
        idx[ckey] = goal
        while len(idx) > 64:
            idx.pop(next(iter(idx)))

    @_locked
    def near(s, cache, ckey, goal):
        """The cached field of the same search (all but its goal node in ckey) whose goal is nearest goal within NEAR_R
        flat and NEAR_DZ up or down; None."""
        if goal is None or not isinstance(ckey, tuple) or len(ckey) < 3:
            return None
        best = None
        for k, g in list(s.near_index.get((id(cache), ckey[:-3]), {}).items()):
            d = math.hypot(g.x - goal.x, g.y - goal.y)
            if d <= NEAR_R and abs(g.z - goal.z) <= NEAR_DZ and k in cache and (best is None or d < best[0]):
                best = (d, k)
        return cache.get(best[1]) if best else None

    @_locked
    def lookup(s, cache, ckey, kind, start, limit, goal, keep):
        """For Terrain._field, a field it does not have cached: the helpers' if done (or nearly: WAIT_S), else a stand-in
        near it while a helper works it out; None: search it here."""
        if s.broken or s.T is None:
            return None
        s.drain(keep)
        f = cache.get(ckey)
        if f is not None:
            s.stats["used"] += 1
            return f
        stand = s.near(cache, ckey, goal)
        if stand is not None:
            s.submit(cache, ckey, kind, start, limit, goal)
            s.stats["near"] += 1
            return stand
        if (id(cache), ckey) in s.inflight and not s.no_wait:
            f = s.wait(cache, ckey, keep)
            if f is not None:
                s.stats["used"] += 1
                return f
        return None

    # --- the end
    def _break(s, e):
        if s.broken is None:
            print(f"route-search helpers off: {type(e).__name__}: {e}; searches in the brain as before", flush=True)
        s.broken = e
        s.close()

    def _drop_all(s):
        for cache_ckey in [o for o in s.slot_owner if o is not None]:
            cache, ckey = cache_ckey
            cache.pop(ckey, None)
        for m in s.slot_shm:
            _close(m)
        for shms in s.graph_shm.values():
            for m in shms:
                _close(m)
        s.slot_shm, s.slot_view, s.slot_used, s.slot_owner = [], [], [], []
        s.graph_shm, s.graph_of, s.graph_ver = {}, {}, {}
        s.inflight, s.pending, s.view_slot, s.near_index = {}, [], {}, {}
        s.pinned, s.pin_want, s.pin_dirty = {}, {}, False
        for h in s.helpers:
            h.job = None
        s.gen = None

    @_locked
    def close(s):
        for h in s.helpers:
            h.stop()
        s.helpers = []
        s._drop_all()
        s.T = None


def _close(m):
    try:
        m.close()
        m.unlink()
    except Exception:
        pass


def worker():
    """A helper: graphs and result slots from shared memory, a Dijkstra a request."""
    from multiprocessing import resource_tracker, shared_memory
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra

    def attach(name):
        m = shared_memory.SharedMemory(name=name)
        try:                                   # (the brain owns it: this process never unlinks it)
            resource_tracker.unregister(m._name, "shared_memory")
        except Exception:
            pass
        return m

    out = sys.stdout.buffer
    graphs, slots, held = {}, [], []
    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        try:
            q = json.loads(line)
            op = q.get("op")
            if op == "slots":
                held = [m for m in held if m not in slots]
                slots = [attach(n) for n in q["names"]]
                shape = tuple(q["shape"])
                views = [np.ndarray(shape, dtype=np.float64, buffer=m.buf) for m in slots]
                continue
            if op == "graph":
                ms = [attach(p[0]) for p in q["parts"]]
                ip, ix, dt = (np.ndarray(tuple(p[1]), dtype=np.dtype(p[2]), buffer=m.buf) for p, m in zip(q["parts"], ms))
                g = csr_matrix((dt, ix, ip), shape=(q["n"], q["n"]), copy=False)
                graphs[q["kind"]] = (q["ver"], g, ms)
                continue
            if op == "job":
                ver, g, _ = graphs.get(q["kind"], (None, None, None))
                if g is None or ver != q["ver"]:
                    r = dict(id=q["id"], ok=False, error="graph version")
                else:
                    t0 = time.perf_counter()
                    cost = dijkstra(g, directed=True, indices=q["start"],
                                    limit=math.inf if q["limit"] is None else q["limit"])
                    views[q["slot"]].reshape(-1)[:] = cost
                    r = dict(id=q["id"], ok=True, ms=round((time.perf_counter() - t0) * 1000.0, 2))
                out.write((json.dumps(r) + "\n").encode("utf-8"))
                out.flush()
        except Exception as e:
            try:
                qid = json.loads(line).get("id")
            except Exception:
                qid = None
            out.write((json.dumps(dict(id=qid, ok=False, error=f"{type(e).__name__}: {e}")) + "\n").encode("utf-8"))
            out.flush()


if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker()
