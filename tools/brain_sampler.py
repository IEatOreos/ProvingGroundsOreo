"""(custom, Nov 23) Where the brain's time goes in a live match: a sampling profiler.

The owner, on an 8v8 CTF on Forge World (20261123-182210) whose brain passes took 194 ms (median; 15-35 ms in the day's
other matches): "Yes, profile first". A thread looks at the brain's main thread every SAMPLE_S and counts the function it
is in (self) and every function on its stack (total), for all of the match and for the slow passes alone (a pass that has
run SLOW_MS already when the sample is taken). Far cheaper than cProfile (which runs every call 1.5-2x slower: a match
already behind would fall further behind); the counts are shares of time, not exact timings.

The report, logs/brain_profile_<map>_<stamp>.txt, is written every WRITE_S and when the brain stops: the top functions by
total and by self time, and the commonest stacks (the brain's own frames, innermost last).

usage (tools/live_bots.py): s = Sampler(path); s.start(); each pass: s.tick = time.time(); at the end: s.stop()
"""
import collections
import os
import sys
import threading
import time

SAMPLE_S = 0.01        # s between samples (100 a second)
SLOW_MS = 100.0        # a pass this long so far is a slow one
WRITE_S = 60.0         # s between reports
TOP = 40               # functions listed
STACK_TOP = 25         # stacks listed
STACK_DEPTH = 8        # frames of a stack kept (the innermost)
OURS = ("brain", "tools")   # the folders whose frames make a stack's key


def frame_key(code):
    """(file, function, first line) of a code object, the file as its last two path parts."""
    parts = code.co_filename.replace("\\", "/").split("/")
    return ("/".join(parts[-2:]), code.co_name, code.co_firstlineno)


def fmt(key):
    f, name, line = key
    return f"{f}:{line} {name}"


class Sampler(threading.Thread):
    def __init__(s, path, thread_id=None, sample_s=SAMPLE_S, write_s=WRITE_S):
        super().__init__(daemon=True, name="brain sampler")
        s.path, s.sample_s, s.write_s = path, sample_s, write_s
        s.target = thread_id if thread_id is not None else threading.main_thread().ident
        s.tick = None                     # the current pass's start (time.time()), set by the brain's loop
        s.n = {"all": 0, "slow": 0}
        s.self_ = {"all": collections.Counter(), "slow": collections.Counter()}
        s.total = {"all": collections.Counter(), "slow": collections.Counter()}
        s.stacks = {"all": collections.Counter(), "slow": collections.Counter()}
        s.t0 = time.time()
        s._halt = threading.Event()
        s._lock = threading.Lock()

    def sample(s):
        """One look at the target thread: counted under "all", and "slow" too while its pass has run SLOW_MS."""
        f = sys._current_frames().get(s.target)
        if f is None:
            return
        keys = []
        while f is not None:
            keys.append(frame_key(f.f_code))
            f = f.f_back
        if not keys:
            return
        tick = s.tick
        slow = tick is not None and (time.time() - tick) * 1000.0 >= SLOW_MS
        ours = [k for k in keys if k[0].split("/")[0] in OURS][:STACK_DEPTH]
        stack = tuple(reversed(ours))
        with s._lock:
            for kind in (("all", "slow") if slow else ("all",)):
                s.n[kind] += 1
                s.self_[kind][keys[0]] += 1
                s.total[kind].update(set(keys))
                if stack:
                    s.stacks[kind][stack] += 1

    def run(s):
        last = time.time()
        while not s._halt.is_set():
            # (time.sleep, not Event.wait: on Windows a wait's timeout wakes on the 15.6 ms system tick, the sleep on a
            # high-resolution timer; a test asking 2 ms got one sample in 23 ms)
            time.sleep(s.sample_s)
            if s._halt.is_set():
                break
            try:
                s.sample()
            except Exception:             # (never stops the brain)
                pass
            if time.time() - last >= s.write_s:
                last = time.time()
                s.write()

    def stop(s):
        s._halt.set()
        s.write()

    def report(s):
        with s._lock:
            n = dict(s.n)
            out = [f"brain profile: {n['all']} samples over {time.time() - s.t0:.0f} s ({s.sample_s * 1000:.0f} ms apart), "
                   f"{n['slow']} of them in passes past {SLOW_MS:.0f} ms ({n['slow'] / max(1, n['all']):.0%})", ""]
            for kind in ("slow", "all"):
                m = max(1, n[kind])
                title = "slow passes" if kind == "slow" else "the whole match"
                out.append(f"== {title}: by total time (the function and what it calls)")
                out += [f"{c / m:6.1%}  {fmt(k)}" for k, c in s.total[kind].most_common(TOP)]
                out.append("")
                out.append(f"== {title}: by self time (in the function itself)")
                out += [f"{c / m:6.1%}  {fmt(k)}" for k, c in s.self_[kind].most_common(TOP)]
                out.append("")
                out.append(f"== {title}: commonest stacks (brain and tools frames, innermost last)")
                for st, c in s.stacks[kind].most_common(STACK_TOP):
                    out.append(f"{c / m:6.1%}  " + " > ".join(f"{k[1]}" for k in st))
                    out.append("        " + fmt(st[-1]))
                out.append("")
        return "\n".join(out) + "\n"

    def write(s):
        try:
            text = s.report()
            tmp = s.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, s.path)
        except Exception as e:            # (never stops the brain)
            print(f"brain profile not written: {type(e).__name__}: {e}", flush=True)
