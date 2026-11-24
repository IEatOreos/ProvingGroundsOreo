"""(custom, Nov 24) Whether a match with the bots is running: user/match.running, written by tools/live_bots.py while it
runs (its process id and map) and removed when it ends. Nothing else in the mod knew it reliably (MCC open is not a
match; the launcher only knows its own Play task).

A LiDAR import (tools/lidar_share.py) is refused while it is held: the match's own LiDAR save rewrites lidar.json
from what it recorded, once a minute and at the end, and an import in between would be lost or mixed. A file left by a
match that crashed counts only while its process is still alive.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "user", "match.running")


def _alive(pid):
    """Whether a process with this id runs now (Windows: OpenProcess / GetExitCodeProcess; never a kill)."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform == "win32":
        import ctypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = ctypes.c_void_p
        h = k32.OpenProcess(0x1000, False, pid)         # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ctypes.get_last_error() == 5         # (access denied: it exists)
        try:
            code = ctypes.c_ulong()
            ok = k32.GetExitCodeProcess(ctypes.c_void_p(h), ctypes.byref(code))
            return bool(ok) and code.value == 259       # STILL_ACTIVE
        finally:
            k32.CloseHandle(ctypes.c_void_p(h))
    try:
        os.kill(pid, 0)                                 # (POSIX: signal 0 only checks)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def hold(map_name="", path=None):
    """This process holds the lock (a match runs) until release() or its exit."""
    import atexit
    path = path or PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dict(pid=os.getpid(), map=str(map_name), t=round(time.time())), f)
    os.replace(tmp, path)
    atexit.register(release, path)


def release(path=None):
    """The lock removed, if this process holds it."""
    path = path or PATH
    try:
        with open(path, encoding="utf-8") as f:
            pid = json.load(f).get("pid")
    except (OSError, ValueError, AttributeError):
        return
    if pid == os.getpid():
        try:
            os.remove(path)
        except OSError:
            pass


def running(path=None):
    """The running match's {pid, map, t}, or None (no lock, or its process has ended)."""
    path = path or PATH
    try:
        with open(path, encoding="utf-8") as f:
            got = json.load(f)
    except (OSError, ValueError):
        return None
    return got if isinstance(got, dict) and _alive(got.get("pid")) else None
