"""The launcher's update check: it looks for new versions on GitHub and says so, with when it last looked, and leaves the
choice to the player (updating automatically only when they turn that on). Updates are never forced.

GitHub's latest release of the public repository is read at most every CHECK_EVERY (or when asked); the result and the
player's choice are kept in user/update.json (kept by updates and Repair). An update is the release's Windows Setup,
downloaded to user/updates and run silently over this folder (/UPDATE=1: the installer opens the launcher again after).
Automatic updates are off unless the player turns them on; nothing is ever installed without that or the Update button.

usage: python -I updater.py            prints what it finds     python -I updater.py --selftest
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# (custom, Nov 12) this custom build's own releases: upstream's would offer its newer version as an update, and its
# Setup would replace the custom bots
RELEASES = "https://github.com/IEatOreos/ProvingGroundsOreo/releases"
REPO = RELEASES.split("github.com/")[1].rsplit("/releases", 1)[0]
API = f"https://api.github.com/repos/{REPO}/releases/latest"
CHECK_EVERY = 6 * 3600          # seconds between automatic checks
STATE = os.path.join(ROOT, "user", "update.json")
DOWNLOADS = os.path.join(ROOT, "user", "updates")
# a release updated in place (same-day fixes) keeps its version: each build has a stamp (BUILD beside VERSION), the
# release's notes carry it (<!-- build: ... -->, tools/release_notes.py), and a newer stamp of the same version is an
# update too. What is new comes from that release's own docs/UPDATES.md, all of it since the player's copy: every version
# newer than ours, and of ours every stamped batch newer than our build
NOTES = f"https://api.github.com/repos/{REPO}/contents/docs/UPDATES.md?ref={{tag}}"   # (not raw.githubusercontent.com:
#   it keeps a moved tag's old file for 5 minutes)
BUILD_MARK = re.compile(r"<!--\s*build:\s*(\d{8}-\d{4})\s*-->")
SECTION = re.compile(r"<summary><b>(.*?)</b>(.*?)</summary>(.*?)</details>", re.S)
_lock = threading.Lock()
_job = dict(state="idle", done=0, total=0, error="")   # the download: idle, downloading, installing, failed


_CURRENT = dict(at=-1e9, v=None)     # (custom, Nov 24) the scheme's answer, kept a minute: the page asks every 2-3 s
CURRENT_KEEP = 60.0


def current():
    """This copy's version. (custom, Nov 24) Project Noble's X.Y.Z (tools/noble_version.py: the NOBLE_VERSION an
    installer stamped, else a Git checkout's commits on GitHub's main and its release tags), else CUSTOM_VERSION
    ("0.2.2-custom.14", the releases before the scheme: an older install), else upstream's VERSION."""
    if time.time() - _CURRENT["at"] > CURRENT_KEEP:
        try:
            if HERE not in sys.path:                 # (python -I, or imported as tools.updater)
                sys.path.insert(0, HERE)
            import noble_version
            v = noble_version.current(ROOT)
        except Exception:
            v = None
        _CURRENT.update(at=time.time(), v=v)
    if _CURRENT["v"]:
        return _CURRENT["v"]
    for name in ("CUSTOM_VERSION", "VERSION"):
        try:
            with open(os.path.join(ROOT, name), encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            continue
    return "dev"


def build():
    """This copy's build stamp (BUILD, "20261106-2245"); "" for one built before stamps (older than any stamped)."""
    try:
        return open(os.path.join(ROOT, "BUILD"), encoding="utf-8").read().strip()
    except OSError:
        return ""


def parse_updates(md):
    """docs/UPDATES.md as [dict(name, key, title, batches=[(build stamp or "", text)])], newest first: each version's
    <details> section, split at its <!-- build: ... --> marks (the text before the first: its first build, unstamped)."""
    out = []
    for name, title, body in SECTION.findall(md or ""):
        parts = BUILD_MARK.split(body)            # [text, stamp, text, stamp, text ...]
        batches = [("", parts[0])] + [(parts[k], parts[k + 1]) for k in range(1, len(parts) - 1, 2)]
        batches = [(b, t.strip()) for b, t in batches if t.strip()]
        out.append(dict(name=name.strip(), key=version_key(name), title=title.strip(" :\n"), batches=batches))
    return out


def news(md, cur, cur_build):
    """What is new for a copy of version cur and build cur_build: [dict(title, text)], newest first: every version
    newer than cur, whole; of cur itself, the stamped batches newer than cur_build (all of them for an unstamped copy)."""
    ck = version_key(cur)
    out = []
    for sec in parse_updates(md):
        if not ck or not sec["key"]:
            continue
        if sec["key"] > ck:
            out.append(dict(title=f"{sec['name']}{(' ' + sec['title']) if sec['title'] else ''}",
                            text="\n\n".join(t for _, t in sec["batches"])))
        elif sec["key"] == ck:
            newer = [t for b, t in sec["batches"] if b and b > (cur_build or "")]
            if newer:
                out.append(dict(title=f"{sec['name']}: updated since your copy", text="\n\n".join(newer)))
    return out


def version_key(v):
    """(scheme, major, minor, patch, build) from "0.2.2-s165", "v0.2.2 s165", "0.2.1" (build 0); None for "dev" or junk.

    (custom, Nov 24) scheme 1: Project Noble's own X.Y.Z (tools/noble_version.py), a plain three-part number with X >= 1,
    or X = 0 and Y = 0 (a copy before the scheme's first release); scheme 0: everything before it (upstream's
    "0.2.2-s181", its plain 0.1.0 to 0.3.0, our "0.2.2-custom.14"), so every new-scheme version is newer than every old
    one: a dev copy at 0.0.325 is not offered the old 0.2.2-custom.14 release, and an install at 0.2.2-custom.14 is
    offered 1.0.x. (A copy at 0.Y.Z with Y >= 1, past 1000 commits before the first release, would read as old.)"""
    s = str(v or "").strip()
    m = re.fullmatch(r"[vV]?(\d+)\.(\d+)\.(\d+)", s)
    if m:
        x, y, z = map(int, m.groups())
        if x >= 1 or y == 0:
            return (1, x, y, z, 0)
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?(?:\D+s?(\d+))?", s)
    if not m:
        return None
    return (0, *(int(x or 0) for x in m.groups()))


def load():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, STATE)


def check(force=False):
    """Reads GitHub's latest release (unless checked within CHECK_EVERY and not forced); returns info()."""
    st = load()
    if not force and time.time() - st.get("checked", 0) < CHECK_EVERY:
        return info()
    try:
        req = urllib.request.Request(API, headers={"User-Agent": "ProjectProvingGrounds-launcher",
                                                   "Accept": "application/vnd.github+json"})
        rel = json.load(urllib.request.urlopen(req, timeout=8))
        setup = next((a for a in rel.get("assets", []) if a.get("name", "").lower().endswith(".exe")
                      and "setup" in a["name"].lower()), None)
        body = rel.get("body") or ""
        st.update(checked=time.time(), latest=rel.get("tag_name", ""), title=rel.get("name", ""),
                  url=rel.get("html_url", RELEASES), setup_url=setup["browser_download_url"] if setup else "",
                  setup_name=setup["name"] if setup else "", setup_bytes=setup.get("size", 0) if setup else 0, error="",
                  latest_build=max(BUILD_MARK.findall(body), default=""), body=body)
        try:                                        # what is new: that release's own notes (news); its body if not
            req = urllib.request.Request(NOTES.format(tag=st["latest"]), headers={"User-Agent": "ProjectProvingGrounds-launcher",
                                                                                  "Accept": "application/vnd.github.raw"})
            st["notes_md"] = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", "replace")
        except Exception:
            st["notes_md"] = ""
    except Exception as e:                          # offline, GitHub down, rate limited: say so, keep the last answer
        st.update(checked_try=time.time(), error=f"Could not reach GitHub ({type(e).__name__}).")
    save(st)
    return info()


def is_newer(cur, cur_build, latest, latest_build):
    """A newer version, or the same version built later (a release updated in place: its notes' newest build stamp)."""
    ck, lk = version_key(cur), version_key(latest)
    if not (ck and lk):
        return False
    return lk > ck or (lk == ck and bool(latest_build) and latest_build > (cur_build or ""))


def info():
    st = load()
    cur, latest, mine, theirs = current(), st.get("latest", ""), build(), st.get("latest_build", "")
    available = is_newer(cur, mine, latest, theirs)
    same = available and version_key(cur) == version_key(latest)
    md = st.get("notes_md", "")
    if theirs and theirs not in md:                  # (its UPDATES.md not read, or an older copy of it)
        md = ""
    new = news(md, cur, mine) if available else []
    if available and not new and st.get("body"):     # then the release's own text; of our version, the updates after ours
        parts = BUILD_MARK.split(st["body"])          # [head, stamp, text, stamp, text ...]
        newer = [parts[k + 1].strip() for k in range(1, len(parts) - 1, 2) if parts[k] > mine] if same else []
        new = [dict(title=st.get("title") or latest, text="\n\n".join(newer) or BUILD_MARK.sub("", st["body"]).strip())]
    return dict(current=cur, latest=latest, title=st.get("title", ""), url=st.get("url", RELEASES),
                available=available, same_version=same, build=mine, latest_build=theirs, news=new,
                checked=st.get("checked", 0), error=st.get("error", ""),
                auto=bool(st.get("auto", False)), can_install=bool(st.get("setup_url")),
                job=dict(_job))


def set_auto(on):
    st = load()
    st["auto"] = bool(on)
    save(st)
    return info()


def download(url, name):
    """The Setup into user/updates (a .part file renamed when whole); its path, or raises."""
    os.makedirs(DOWNLOADS, exist_ok=True)
    path = os.path.join(DOWNLOADS, os.path.basename(name))
    req = urllib.request.Request(url, headers={"User-Agent": "ProjectProvingGrounds-launcher"})
    with urllib.request.urlopen(req, timeout=30) as r, open(path + ".part", "wb") as f:
        _job["total"] = int(r.headers.get("Content-Length") or 0)
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            _job["done"] += len(chunk)
    if _job["total"] and _job["done"] != _job["total"]:
        raise IOError("the download stopped early")
    os.replace(path + ".part", path)
    return path


def install(on_start=None):
    """Downloads the latest Setup and runs it over this folder, silently (the player asked: the Update button, or
    automatic updates on). on_start(): called once the installer runs (the launcher closes everything of the mod)."""
    with _lock:
        if _job["state"] in ("downloading", "installing"):
            return False
        _job.update(state="downloading", done=0, total=0, error="")
    st = load()

    def run():
        try:
            setup = download(st["setup_url"], st["setup_name"])
            _job["state"] = "installing"
            subprocess.Popen([setup, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/UPDATE=1", f"/DIR={ROOT}", "/TASKS="],
                             cwd=os.path.dirname(ROOT), creationflags=0x00000008)      # DETACHED_PROCESS
            if on_start:
                on_start()
        except Exception as e:
            _job.update(state="failed", error=f"The update could not be downloaded ({type(e).__name__}). "
                                              "Try again, or download it from the releases page.")
    threading.Thread(target=run, daemon=True).start()
    return True


def selftest():
    # (custom, Nov 24) every key starts with its scheme: 0 before Project Noble's X.Y.Z
    assert version_key("0.2.2-s165") == (0, 0, 2, 2, 165) and version_key("v0.2.2 s165") == (0, 0, 2, 2, 165)
    assert version_key("0.2.1") == (0, 0, 2, 1, 0) and version_key("dev") is None
    assert version_key("v0.2.2-s166") > version_key("0.2.2-s165") > version_key("0.2.1")
    assert version_key("v0.3.0") > version_key("0.2.9-s999")
    # (custom) the custom releases' tags
    assert version_key("v0.2.2-custom.12") > version_key("0.2.2-custom.11") == (0, 0, 2, 2, 11)
    # (custom, Nov 24) Project Noble's X.Y.Z is newer than every older version, either way round
    assert version_key("0.0.325") > version_key("v0.2.2-custom.14") and version_key("v1.0.340") > version_key("0.0.999")
    assert not is_newer("0.0.325", "", "v0.2.2-custom.14", "") and is_newer("0.2.2-custom.14", "", "v1.0.340", "")
    print("updater OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(json.dumps(check(force=True), indent=1))
