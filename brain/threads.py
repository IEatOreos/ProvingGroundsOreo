"""(custom, Nov 23) The bots' thinking on several cores: every bot's Bot.think of a pass on a pool of threads.

Adapted from the upstream author's brain/threads.py (Project Proving Grounds 0.3.0, build 20261123-003719; PolyForm
Noncommercial, see LICENSE.md / NOTICE.md), for this brain. The owner: "Yes, start the port". It needs the free-threaded
Python (3.14t: no lock, so threads run at once; with the lock they only slow the brain, upstream's study and ours).

Bots think in parallel on what the pass started with. Whatever one bot's think would change for the others in the same
pass is held back and applied after the pass, in the players' order, so the result does not depend on which thread ran
first (Pass(workers=1) runs the same held-back pass on one thread: the reference a threaded pass must match,
tools/test_threads.py):
- the Terrain's learning (learn_stuck, learn_blocked, learn_shot_through), as upstream's;
- the team tables bots post to and read (brain/bot.py TEAM_SIGHTINGS, TEAM_EYES, TEAM_FACING, TEAM_TARGETS,
  TEAM_CRACKED, TEAM_ATTACKERS, TEAM_SPACE; BOT_PROFILES, DEAD_SPOTS) and the map's vehicle duds (Bot.duds): a bot reads
  the pass's start plus its own writes (one more than upstream's: "I claimed this spot" holds within its think), the
  others' only after the pass;
- what the bots learn as they play: Noble's hit book (brain/noble.py Book.add), Noble's habits (brain/noble_habits.py
  add_sight, add_escape, add_dodge), the map's lore of jumps (brain/lore.py Lore.add_jump).
Shared caches are made safe where they live: the route-field caches (brain/terrain.py cached_field / keep_field, a
lock), a route with one-off costs (Terrain._field: a copy of the graph while THREADS is on), the per-think search budget
(terrain.opt_state: per thread), the route-search helpers (tools/field_pool.py: a lock, no waiting).
"""
import threading
from concurrent.futures import ThreadPoolExecutor

from . import bot as botmod
from . import terrain as termod

LEARNS = ("learn_stuck", "learn_blocked", "learn_shot_through")
NESTED = ("TEAM_SIGHTINGS", "TEAM_EYES", "TEAM_FACING", "TEAM_TARGETS", "TEAM_CRACKED", "TEAM_ATTACKERS", "TEAM_SPACE")
FLAT = ("BOT_PROFILES", "DEAD_SPOTS")
_who = threading.local()          # the player's place in the pass on this thread: the order held-back writes go in
_GONE = object()


def who():
    return getattr(_who, "k", -1)


class PassDict(dict):
    """A table during a pass: reads see the pass's start (this dict) plus this thread's own writes; every write is held
    for after the pass (target(): the real dict then)."""

    def __init__(s, start, held, target):
        super().__init__(start)
        s.held, s.target, s.own = held, target, {}
        s._lock = threading.Lock()

    def _mine(s):
        k = who()
        with s._lock:
            return s.own.setdefault(k, {})

    def _hold(s, op, *a):
        s.held.append((who(), len(s.held), lambda: getattr(s.target(), op)(*a), (), {}))

    def _view(s):
        out = dict(super().items())
        for k, v in s._mine().items():
            if v is _GONE:
                out.pop(k, None)
            else:
                out[k] = v
        return out

    # reads
    def __getitem__(s, k):
        m = s._mine()
        if k in m:
            if m[k] is _GONE:
                raise KeyError(k)
            return m[k]
        return super().__getitem__(k)

    def get(s, k, default=None):
        try:
            return s[k]
        except KeyError:
            return default

    def __contains__(s, k):
        m = s._mine()
        if k in m:
            return m[k] is not _GONE
        return super().__contains__(k)

    def __iter__(s):
        return iter(list(s._view()))

    def __len__(s):
        return len(s._view())

    def keys(s):
        return s._view().keys()

    def values(s):
        return s._view().values()

    def items(s):
        return s._view().items()

    def copy(s):
        return s._view()

    # writes
    def __setitem__(s, k, v):
        s._mine()[k] = v
        s._hold("__setitem__", k, v)

    def __delitem__(s, k):
        if k not in s:
            raise KeyError(k)
        s._mine()[k] = _GONE
        s._hold("pop", k, None)

    def pop(s, k, *default):
        if k in s:
            v = s[k]
            s._mine()[k] = _GONE
            s._hold("pop", k, None)
            return v
        if default:
            return default[0]
        raise KeyError(k)

    def setdefault(s, k, default=None):
        if k in s:
            return s[k]
        s[k] = default
        return default

    def update(s, *a, **kw):
        for k, v in dict(*a, **kw).items():
            s[k] = v

    def clear(s):
        for k in list(s):
            del s[k]


class PassTable(dict):
    """A team table ({key: {...}}) during a pass: each key's inner dict a PassDict over its start."""

    def __init__(s, real, held):
        super().__init__()
        s.real, s.held = real, held
        s._lock = threading.Lock()

    def _inner(s, key, create):
        with s._lock:
            v = dict.get(s, key)
            if v is None and (create or key in s.real):
                start = s.real.get(key, {})
                v = PassDict(start, s.held, lambda: s.real.setdefault(key, {}))
                dict.__setitem__(s, key, v)
            return v

    def setdefault(s, key, default=None):
        return s._inner(key, True)

    def get(s, key, default=None):
        v = s._inner(key, False)
        return default if v is None else v

    def __getitem__(s, key):
        v = s._inner(key, False)
        if v is None:
            raise KeyError(key)
        return v

    def __contains__(s, key):
        return key in s.real or dict.__contains__(s, key)

    def keys(s):
        return list(set(s.real) | set(dict.keys(s)))

    def __iter__(s):
        return iter(s.keys())

    def __len__(s):
        return len(s.keys())

    def items(s):
        return [(k, s[k]) for k in s.keys()]

    def values(s):
        return [s[k] for k in s.keys()]


class Pass:
    """Runs a pass's thinks on `workers` threads (1: the same held-back pass on this thread)."""

    def __init__(s, workers):
        s.workers = max(1, int(workers))
        s.pool = ThreadPoolExecutor(s.workers, thread_name_prefix="think") if s.workers > 1 else None
        s.held = []
        termod.THREADS = True

    def _defer(s, fn):
        return lambda *a, **k: s.held.append((who(), len(s.held), fn, a, k))

    def _run(s, k, fn, args):
        _who.k = k
        termod.set_pass_who(k)
        try:
            return fn(*args)
        finally:
            _who.k = -1
            termod.set_pass_who(-1)

    def run(s, jobs, T=None, mapdata=None):
        """jobs: [(think, args)] in the players' order; their results in the same order (an exception raised as it would
        serially, after every job ended), the held-back writes done. T: the terrain the bots walk (its learning held);
        mapdata: the map dict they share (its vehicle duds held)."""
        from . import lore, noble, noble_habits
        s.held = held = []
        termod._PASS["seq"] += 1             # (the fields kept this pass: terrain.fresh_to_me)
        tables = {n: getattr(botmod, n) for n in NESTED + FLAT}
        for n in NESTED:
            setattr(botmod, n, PassTable(tables[n], held))
        for n in FLAT:
            real = tables[n]
            setattr(botmod, n, PassDict(real, held, (lambda r: lambda: r)(real)))
        patches = [(noble.Book, "add"), (lore.Lore, "add_jump")]
        saved = [(o, n, o.__dict__[n]) for o, n in patches]
        for o, n, fn in saved:
            setattr(o, n, (lambda f: lambda self, *a, **k: held.append((who(), len(held), f, (self,) + a, k)))(fn))
        funcs = [(noble_habits, n, getattr(noble_habits, n)) for n in ("add_sight", "add_escape", "add_dodge")]
        for mod, n, fn in funcs:
            setattr(mod, n, s._defer(fn))
        if T is not None:
            for n in LEARNS:
                setattr(T, n, s._defer(getattr(T, n)))
        duds = None
        if mapdata is not None:
            duds = mapdata.setdefault("_vehicle_duds", {})
            mapdata["_vehicle_duds"] = PassDict(duds, held, lambda: duds)
        try:
            if s.pool is None:
                futs = None
                out = []
                for k, (fn, a) in enumerate(jobs):
                    out.append(s._run(k, fn, a))
            else:
                futs = [s.pool.submit(s._run, k, fn, a) for k, (fn, a) in enumerate(jobs)]
                out, err = [], None
                for f in futs:                       # (every think ended before the tables go back: the first error
                    try:                             # raised after, as serially)
                        out.append(f.result())
                    except BaseException as e:
                        out.append(None)
                        err = err or e
                if err is not None:
                    raise err
        finally:
            for n, real in tables.items():
                setattr(botmod, n, real)
            for o, n, fn in saved:
                setattr(o, n, fn)
            for mod, n, fn in funcs:
                setattr(mod, n, fn)
            if T is not None:
                for n in LEARNS:
                    T.__dict__.pop(n, None)
            if mapdata is not None:
                mapdata["_vehicle_duds"] = duds
        for _, _, fn, a, k in sorted(held, key=lambda h: h[:2]):
            fn(*a, **k)
        return out

    def close(s):
        if s.pool is not None:
            s.pool.shutdown(wait=True)
            s.pool = None
        termod.THREADS = False
