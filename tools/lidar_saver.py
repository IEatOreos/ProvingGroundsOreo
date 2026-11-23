"""(custom, Nov 22) The people's LiDAR save's merge and write (maps/<map>/lidar.json), and a helper process that does it
for live_bots. Live Asylum: the merge of a 3 MB lidar.json (about 100,000 walked cells read, merged, sorted and
written) took 420-445 ms once a minute. On a thread it still held Python's lock (one thread runs at a time), so the
bot thinking then waited: every bot stood for 260-670 ms each minute. In its own process (Saver) the bots never wait:
they hand it only what is new (Recorder.save_payload), and it merges it into the file.

Only the standard library here: the helper starts quickly and loads nothing of the brain.
usage (Saver starts it): python -I lidar_saver.py --worker     (one JSON payload a line in, {"ok": ...} a line out)"""
import json
import os
import queue
import subprocess
import sys
import threading

REPLY_S = 60.0          # s: no reply from the helper in this long: it is stopped and the save done in this process


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def merge_save(p):
    """Merge one save's payload (lidar.Recorder.save_payload) into its lidar.json (atomic). Returns what was written.
    The same merge Recorder.save did in place before."""
    old = _load(p["path"])
    walk = {}
    for w in old.get("walk", []):
        if len(w) == 4:
            w.insert(3, p["kind_bot"])
        walk[tuple(w[:4])] = w[4]
    for r in p["new_walk"]:                  # only what is new since the last save
        k = tuple(r[:4])
        walk[k] = walk.get(k, 0) + r[4]
    out = dict(cell=p["cell"], zstep=p["zstep"],
               runs=old.get("runs", 0) + (1 if p["run"] else 0),
               bot_minutes=round(old.get("bot_minutes", 0) + p["bot_seconds"] / 60, 1),
               human_minutes=round(old.get("human_minutes", 0) + p["human_seconds"] / 60, 1),
               walk=[[*k, n] for k, n in sorted(walk.items())],
               deaths=(old.get("deaths", []) + p["deaths"])[-3000:],
               jumps=(old.get("jumps", []) + p["jumps"])[-2000:],
               links=p["links"], weapons=p["weapons"], cover=p["cover"])
    objectives = p["objectives"] if p["has_objectives"] else old.get("objectives")
    if objectives:                           # every gametype objective place, reached or not (lidar.Objectives)
        out["objectives"] = objectives
    if p.get("coverage") is not None:        # this run's coverage, what is left
        out["coverage"] = p["coverage"]
    os.makedirs(os.path.dirname(p["path"]), exist_ok=True)
    tmp = p["path"] + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f)
    os.replace(tmp, p["path"])
    return out


def _python():
    """This Python, the console one (pythonw has no pipes to talk on)."""
    exe = sys.executable
    head, tail = os.path.split(exe)
    if tail.lower() == "pythonw.exe" and os.path.exists(os.path.join(head, "python.exe")):
        return os.path.join(head, "python.exe")
    return exe


class Saver:
    """The helper process, started at the first save and kept for the match. save(payload) waits for its reply (the
    wait gives up Python's lock: the bots go on thinking). Any failure (no start, a crash, no reply in REPLY_S): the
    helper is stopped and this save is merged here as before, the next save starts a new one."""

    def __init__(s, cmd=None):
        s.cmd = cmd or [_python(), "-I", os.path.abspath(__file__), "--worker"]
        s.proc, s.replies = None, None
        s.lock = threading.Lock()
        s.fallbacks = 0

    def _start(s):
        flags = 0
        if os.name == "nt":
            flags = 0x08000000 | 0x00004000          # CREATE_NO_WINDOW, BELOW_NORMAL_PRIORITY_CLASS (the game first)
        s.proc = subprocess.Popen(s.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  creationflags=flags)
        s.replies = queue.Queue()
        out, q = s.proc.stdout, s.replies

        def read():
            try:
                for line in out:
                    q.put(line)
            except (OSError, ValueError):      # (closed by _stop)
                pass
            q.put(None)
        threading.Thread(target=read, daemon=True).start()

    def save(s, payload):
        with s.lock:
            try:
                if s.proc is None or s.proc.poll() is not None:
                    s._start()
                s.proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
                s.proc.stdin.flush()
                line = s.replies.get(timeout=REPLY_S)
                if line is None:
                    raise RuntimeError("the helper stopped")
                r = json.loads(line)
                if not r.get("ok"):
                    raise RuntimeError(r.get("error", "no reason given"))
                return True
            except Exception as e:
                print(f"LiDAR save helper: {type(e).__name__}: {e}; saved in the bots' process", flush=True)
                s._stop()
                s.fallbacks += 1
                merge_save(payload)
                return True

    def _stop(s):
        p, s.proc = s.proc, None
        if p is None:
            return
        try:
            p.stdin.close()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
        try:
            p.stdout.close()
        except Exception:
            pass

    def close(s):
        """At the match's end, after its last save: the helper exits."""
        with s.lock:
            s._stop()


def worker():
    out = sys.stdout.buffer
    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        try:
            merge_save(json.loads(line))
            r = {"ok": True}
        except Exception as e:
            r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        out.write((json.dumps(r) + "\n").encode("utf-8"))
        out.flush()


if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker()
