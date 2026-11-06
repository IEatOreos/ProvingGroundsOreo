"""Project Proving Grounds' launcher: the window the Start Menu shortcut opens. It shows what is ready (the game, the
first-time setup, the map tools, mapped maps, mods that can clash), lets the player choose which MCC folder the mod uses
(Windows' folder picker or a pasted path, saved in user/mcc_folder.txt; or automatic), starts MCC with the bots, runs the first-time setup
(Repair: all of it again), opens the tools (Observer, LiDAR Simulator, LiDAR Viewer, nav painter), each in its own app
window (tools/appwindow.py), and uninstalls (the installer's own uninstaller, once everything of the mod is closed).

A small local server (127.0.0.1 only) serves tools/launcher.html (its picture: docs/banner.jpg) and runs the tasks as their own processes, with
this Python. It stops a while after its window closes, unless a task it started is still running. Starting it again
while it runs just opens its window again.

usage: python -I launcher.py [--port 8793] [--no-window] [--setup]   (--setup: runs the first-time setup if needed)
"""
import glob
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import appwindow  # noqa: E402
import conflicts  # noqa: E402
import setup  # noqa: E402
import updater  # noqa: E402
from brain import paths  # noqa: E402

PORT = 8793
# the console Python for the tasks, run with CREATE_NO_WINDOW: the launcher itself runs under pythonw.exe (no console
# window), and a task under pythonw has no console, so every console program it starts (model2obj.exe for each 3D
# model, inject.exe) would open a console window of its own; under python.exe with a hidden console they inherit it
PY = os.path.join(os.path.dirname(sys.executable), "python.exe") \
    if os.path.basename(sys.executable).lower() == "pythonw.exe" else sys.executable
IDLE_STOP = 20.0          # seconds without a ping from the window before the server stops (no task running)
LOGS = os.path.join(ROOT, "logs", "launcher")
# task: (script and its arguments, keeps running on its own after it opened its window, its window's port)
TASKS = {
    "play": (["launch.py"], False, None),
    "setup": (["setup.py"], False, None),
    "setup_force": (["setup.py", "--force"], False, None),
    "observer": (["observer.py", "serve", "--open"], True, 8799),
    "lidar_sim": (["lidar_sim.py", "--open"], True, 8798),     # (its own port: the Viewer and a LiDAR match use 8797)
    "lidar_view": (["lidar.py", "--view", "--open"], True, 8797),
    "paint": (["paint.py", "--open"], True, 8796),
}
procs = {}                # task: Popen
last_ping = [time.time()]


def version():
    try:
        return open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()
    except OSError:
        return "dev"


def lidar_counts():
    """(maps with a LiDAR scan, maps the mod knows)."""
    maps = os.path.join(ROOT, "maps")
    known = [d for d in os.listdir(maps) if not d.startswith("_") and os.path.isdir(os.path.join(maps, d))]
    return sum(os.path.exists(os.path.join(maps, d, "lidar.json")) for d in known), len(known)


def uninstaller():
    """The installer's uninstaller (unins000.exe in the install folder), or None in a copy not installed with it."""
    found = sorted(glob.glob(os.path.join(ROOT, "unins*.exe")))
    return found[-1] if found else None


def uninstall(srv):
    """Closes everything of the mod (the tools it started, their windows, this one), then opens the uninstaller: the
    same one Windows' Settings > Apps runs, which asks before it removes anything."""
    exe = uninstaller()
    time.sleep(0.8)                                  # (the page's answer reaches it first)
    conflicts.stop_inside(ROOT, keep={os.getpid()})
    subprocess.Popen([exe], cwd=os.path.dirname(ROOT), creationflags=0x00000008)   # DETACHED_PROCESS
    srv.shutdown()


def close_for_update(srv):
    """The update's installer runs: everything of the mod closes (the tools, their windows, this launcher) so it can
    replace the files; it opens the launcher again when done (installer: LauncherUpdate)."""
    time.sleep(1.5)                                  # (the page shows "Installing" first)
    conflicts.stop_inside(ROOT, keep={os.getpid()})
    srv.shutdown()


def auto_update(srv):
    """At the launcher's start: the update check (at most every 6 hours); with automatic updates on (the player's
    choice, off by default) a newer version is downloaded and installed, never while MCC runs."""
    try:
        got = updater.check()
        if got["auto"] and got["available"] and got["can_install"] and not paths.wine() and not conflicts.mcc_running():
            updater.install(on_start=lambda: close_for_update(srv))
    except Exception:
        pass                                         # (offline: the page says when it last checked)


def pick_folder(start=None):
    """Windows' own folder picker (IFileOpenDialog, folders only) over the launcher's window; the folder picked, or
    None (cancelled, or no picker: the page also takes a pasted path)."""
    import ctypes
    from ctypes import wintypes as wt
    ole = ctypes.oledll.ole32

    def guid(s):
        g = (ctypes.c_ubyte * 16)()
        ole.CLSIDFromString(s, ctypes.byref(g))
        return g

    def call(obj, index, *args):                     # a COM method by its vtable slot (shobjidl.h order)
        fn = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0][index]
        types = [ctypes.c_void_p if type(a).__name__ == "CArgObject" else type(a) for a in args]   # (byref: a pointer)
        return ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *types)(fn)(obj, *args)

    try:
        ole.CoInitializeEx(None, 2)                  # COINIT_APARTMENTTHREADED (this request's own thread)
    except OSError:
        pass
    dlg, item = ctypes.c_void_p(), ctypes.c_void_p()
    try:
        ole.CoCreateInstance(guid("{DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7}"), None, 1,       # FileOpenDialog
                             guid("{D57C7288-D4AD-4768-BE02-9D969532D960}"), ctypes.byref(dlg))  # IFileOpenDialog
        opts = wt.DWORD()
        call(dlg, 10, ctypes.byref(opts))                                                   # GetOptions
        call(dlg, 9, wt.DWORD(opts.value | 0x20 | 0x40 | 0x800))     # SetOptions: PICKFOLDERS FORCEFILESYSTEM PATHMUSTEXIST
        call(dlg, 17, wt.LPCWSTR("Choose the Halo: The Master Chief Collection folder"))      # SetTitle
        if start and os.path.isdir(start):
            folder = ctypes.c_void_p()
            try:
                ctypes.oledll.shell32.SHCreateItemFromParsingName(
                    wt.LPCWSTR(start), None, guid("{43826D1E-E718-42EE-BC55-A1E261C37BFE}"), ctypes.byref(folder))
                call(dlg, 12, folder)                                                       # SetFolder
                call(folder, 2)                                                             # Release
            except OSError:
                pass
        owner = ctypes.windll.user32.FindWindowW(None, appwindow.TITLES["8793"])          # the launcher's window
        call(dlg, 3, wt.HWND(owner or None))                                                 # Show (cancel raises)
        call(dlg, 20, ctypes.byref(item))                                                   # GetResult
        name = ctypes.c_void_p()
        call(item, 5, ctypes.c_int(0x80058000 - (1 << 32)), ctypes.byref(name))            # GetDisplayName FILESYSPATH
        path = ctypes.wstring_at(name.value)
        ole.CoTaskMemFree(name)
        return path
    except OSError:
        return None
    finally:
        for o in (item, dlg):
            if o.value:
                call(o, 2)


def choose_mcc(body):
    """The launcher's MCC folder choice: {"path": ...} (picked or pasted), {"browse": true} (the folder picker first),
    {"auto": true} (back to automatic). (ok, message)."""
    if body.get("auto"):
        paths.choose(None)
        return True, "automatic"
    path = pick_folder(paths.mcc()) if body.get("browse") else (body.get("path") or "").strip().strip('"')
    if not path:
        return False, "" if body.get("browse") else "Type or paste a folder first."
    if paths.wine() and path.startswith("/"):        # (a Linux path: Wine's drive Z: is the Linux root)
        path = "Z:" + path.replace("/", "\\")
    ok, said = paths.choose(path)
    return ok, said


def status():
    found = conflicts.scan()
    mapped, total = lidar_counts()
    mcc = paths.mcc()
    shown = os.path.realpath(mcc) if mcc else mcc    # (as the folder is really spelled: Steam's file is lowercase)
    return dict(version=version(), mcc=shown, mcc_running=conflicts.mcc_running(), installed=bool(uninstaller()),
                mcc_choice=paths.chosen(), mcc_env=bool(os.environ.get("HB_MCC")), mcc_steam=paths.is_steam_copy(mcc),
                mcc_found=paths.installs(), wine=paths.wine(),
                missing_games=[paths.GAME_NAMES[g] for g in paths.GAME_MAPS if g not in paths.games(mcc)] if mcc else [],
                setup=setup.status()[1:], map_tools=bool(paths.map_tool("model2obj")),
                lidar=dict(mapped=mapped, total=total), workshop=conflicts.workshop_count(),
                conflicts=[dict(file=os.path.relpath(p, paths.mcc()), why=w) for p, w in found],
                running={t: p.poll() is None for t, p in procs.items()})


def start(task, clean=False):
    """Starts a task; (ok, message)."""
    if task not in TASKS:
        return False, "unknown task"
    if task in procs and procs[task].poll() is None:
        port = TASKS[task][2]
        if port:                                     # a tool keeps serving after its window closes: open it again
            appwindow.open_window(f"http://127.0.0.1:{port}/")
        return True, "already running"
    if task == "play" and clean:
        moved = conflicts.turn_off()
        if moved:                                    # put back once MCC has come and gone (its own process)
            subprocess.Popen([PY, "-I", os.path.join(HERE, "conflicts.py"), "--restore-after-mcc"],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), cwd=ROOT)
    args = TASKS[task][0]
    os.makedirs(LOGS, exist_ok=True)
    log = open(os.path.join(LOGS, task + ".txt"), "w", encoding="utf-8")
    procs[task] = subprocess.Popen([PY, "-u", "-I", os.path.join(HERE, args[0]), *args[1:]], cwd=ROOT,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return True, "started"


def log_lines(task, skip=0):
    if task not in TASKS:                            # (a known task's log only: the name goes into a path)
        return dict(lines=[], next=0, running=False, code=None)
    try:
        lines = open(os.path.join(LOGS, task + ".txt"), encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        lines = []
    p = procs.get(task)
    return dict(lines=lines[skip:], next=len(lines), running=bool(p and p.poll() is None),
                code=None if not p or p.poll() is None else p.returncode)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", code=200):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/":
            self.send(open(os.path.join(HERE, "launcher.html"), "rb").read(), "text/html; charset=utf-8")
        elif path == "/art.jpg":                     # the page's hero: the README's banner (docs/banner.jpg ships)
            try:
                self.send(open(os.path.join(ROOT, "docs", "banner.jpg"), "rb").read(), "image/jpeg")
            except OSError:
                self.send({"error": "not found"}, code=404)
        elif path == "/guide":                       # the player's guide, in the launcher's look (Read the guide)
            self.send(open(os.path.join(HERE, "guide.html"), "rb").read(), "text/html; charset=utf-8")
        elif path == "/update":                      # the update check's last answer (tools/updater.py)
            self.send(dict(updater.info(), wine=paths.wine()))
        elif path == "/status":
            self.send(status())
        elif path.startswith("/log/"):
            skip = int(query.split("=")[1]) if query.startswith("from=") and query[5:].isdigit() else 0
            self.send(log_lines(path[5:], skip))
        else:
            self.send({"error": "not found"}, code=404)

    def do_POST(self):
        if self.headers.get("X-Launcher") != "1":    # only the launcher's own page (a plain form post cannot set it)
            return self.send({"error": "refused"}, code=403)
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        if self.path == "/ping":
            last_ping[0] = time.time()
            self.send({"ok": True})
        elif self.path.startswith("/run/"):
            ok, msg = start(self.path[5:], bool(body.get("clean")))
            port = TASKS.get(self.path[5:], (0, 0, None))[2]
            self.send({"ok": ok, "message": msg, "port": port}, code=200 if ok else 400)
        elif self.path == "/mcc":
            ok, msg = choose_mcc(body)
            self.send({"ok": ok, "message": msg})
        elif self.path == "/folder":
            os.startfile(ROOT)
            self.send({"ok": True})
        elif self.path == "/docs":                   # the guide in the mod's own window (it opened README.md as raw text)
            url = f"http://127.0.0.1:{self.server.server_address[1]}/guide"
            if paths.wine():                         # (no app window under Wine: the page opens it in the browser)
                return self.send({"ok": True, "url": "/guide", "opened": False})
            appwindow.open_window(url, (1180, 820), "Guide - Project Proving Grounds")
            self.send({"ok": True, "opened": True})
        elif self.path == "/update/check":
            self.send(dict(updater.check(force=True), wine=paths.wine()))
        elif self.path == "/update/auto":
            self.send(updater.set_auto(bool(body.get("on"))))
        elif self.path == "/update/install":         # the player pressed Update (never on its own: automatic is opt-in)
            if conflicts.mcc_running():
                return self.send({"ok": False, "message": "Close MCC first: the bots are loaded into it."}, code=400)
            if paths.wine() or not updater.info()["can_install"]:
                return self.send({"ok": False, "message": "Download the new version from the releases page."}, code=400)
            self.send({"ok": updater.install(on_start=lambda: close_for_update(self.server))})
        elif self.path == "/open":                   # a link out of the guide, in the default browser: web pages only
            url = str(body.get("url", ""))
            if not url.startswith("https://github.com/AyoItzKye/"):
                return self.send({"ok": False}, code=400)
            webbrowser.open(url)
            self.send({"ok": True})
        elif self.path == "/uninstall":
            if not uninstaller():
                return self.send({"ok": False, "message": "This copy was not installed with the installer: to remove "
                                  "it, delete its folder."}, code=400)
            if conflicts.mcc_running():
                return self.send({"ok": False, "message": "Close MCC first: the bots are loaded into it."}, code=400)
            self.send({"ok": True})
            threading.Thread(target=uninstall, args=(self.server,), daemon=True).start()
        else:
            self.send({"error": "not found"}, code=404)


class Server(ThreadingHTTPServer):
    # no address reuse: on Windows it let a second launcher serve the same port as the first, and the new window
    # talked to the old launcher (whose tools said "already running" and never opened)
    allow_reuse_address = False


def watch_idle(srv):
    """Stops the server once the window has been closed a while and no task of its own is still working."""
    while True:
        time.sleep(2)
        busy = any(p.poll() is None and not TASKS[t][1] for t, p in procs.items())
        if not busy and time.time() - last_ping[0] > IDLE_STOP:
            srv.shutdown()
            return


def main():
    if os.path.basename(sys.executable).lower() == "pythonw.exe":
        # started by the shortcut under pythonw (no console window): start again under python.exe with a hidden
        # console (CREATE_NO_WINDOW), which every program the launcher starts inherits, so none can flash a window
        subprocess.Popen([PY, "-I", os.path.abspath(__file__), *sys.argv[1:]], cwd=ROOT,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else PORT
    url = f"http://127.0.0.1:{port}/" + ("?setup=1" if "--setup" in sys.argv else "")
    conflicts.restore()                              # (files a clean launch moved aside, if the PC went off since)
    appwindow.remove_old_edge_profile()              # (0.1.0's Edge profile, signed into the user's account by Windows)
    try:
        srv = Server(("127.0.0.1", port), Handler)
    except OSError:                                  # it runs already: show its window again
        if "--no-window" not in sys.argv:
            appwindow.open_window(url, (1040, 700))
        return
    threading.Thread(target=watch_idle, args=(srv,), daemon=True).start()
    threading.Thread(target=auto_update, args=(srv,), daemon=True).start()   # (the update check, tools/updater.py)
    if "--no-window" not in sys.argv:
        appwindow.open_window(url, (1040, 700))
    srv.serve_forever()


if __name__ == "__main__":
    main()
