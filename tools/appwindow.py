"""Opens one of the project's pages (the launcher, the Observer, the LiDAR view, the nav painter) in its own app
window: native/bin/ppg_window.exe, a small Windows program that shows the page through the WebView2 web view built into
Windows 10 and 11. It is not a browser: no profile, no account sign-in, no sync, no extensions, no address bar; links to
other sites open in the default browser. A developer copy without the built window opens the page in the default
browser instead.

usage: python -I appwindow.py <url> [width height]
"""
import os
import shutil
import subprocess
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
WINDOW = os.path.join(ROOT, "native", "bin", "ppg_window.exe")
ICON = os.path.join(ROOT, "installer", "icon.ico")
TITLES = {"8793": "Project Proving Grounds", "8799": "Observer - Project Proving Grounds",
          "8797": "LiDAR Viewer - Project Proving Grounds", "8798": "LiDAR Simulator - Project Proving Grounds",
          "8796": "Paint the nav - Project Proving Grounds"}


def command(url, size=(1400, 900), title=None):
    """The command line that opens url in the app window, or None without the built window."""
    if not os.path.exists(WINDOW):
        return None
    port = url.split(":")[2].split("/")[0] if url.count(":") >= 2 else ""
    cmd = [WINDOW, "--url", url, "--title", title or TITLES.get(port, "Project Proving Grounds"),
           "--width", str(size[0]), "--height", str(size[1])]
    return cmd + (["--icon", ICON] if os.path.exists(ICON) else [])


def open_window(url, size=(1400, 900), title=None):
    """Opens url in the app window (the default browser without it). Returns at once. Under Wine (Linux, Steam Deck)
    there is no WebView2: the Linux launcher script and the launcher's page open the pages in the system's browser."""
    sys.path.insert(0, ROOT)
    from brain import paths
    if paths.wine():
        print(f"open {url} in your browser", flush=True)
        return
    cmd = command(url, size, title)
    if cmd:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(url)


def remove_old_edge_profile():
    """Version 0.1.0 opened its pages in Edge with a profile of its own (%LOCALAPPDATA%\\ProjectProvingGrounds\\window),
    which Windows signed into the user's Microsoft account and synced into: deleted (best effort; Edge may hold it)."""
    old = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ProjectProvingGrounds", "window")
    if os.environ.get("LOCALAPPDATA") and os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    open_window(a[0], (int(a[1]), int(a[2])) if len(a) >= 3 else (1400, 900))
