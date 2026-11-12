"""Builds the Windows installer for a GitHub release of this custom build: ProjectProvingGrounds-Setup-<CUSTOM_VERSION>.exe,
everything a player needs in one file, so nobody has to install Python, build tools or anything else.

(custom, Nov 12) Adapted from upstream's tools/build_installer.py (AyoItzKye/project-proving-grounds, main), which needs
its tools/make_release.py, not in this install. Here:
  - the public copy is the committed tree (git archive HEAD: only what is on GitHub), less DEV_ONLY; nothing is built
    while tracked files have uncommitted changes, or while the regression tests fail on that committed copy
  - the map pack (maps/*/heightmap.npz, topdown.png, glass.json, maps/_shapes: derived from each map's level mesh, the
    optional map pack of NOTICE.md) comes from this folder and is merged into the payload, as upstream's
  - the mod (botcore.dll, inject.exe, ppg_window.exe) is built from that committed copy (native/build.bat and
    build_window.bat in a worktree), so this folder's own native/bin, and the newest DLL MCC loads here, are untouched
  - Python is this install's bundled one (python/, its numpy, scipy and Pillow), copied, not downloaded
  - the map tools are this install's tools/map_tools (the separate proving-grounds-map-tools project, GPL-3.0)
  - a privacy scan: no text file of the payload may hold this PC's user name or profile path, or a term listed in
    .private_terms (one per line, not in Git)
then Inno Setup compiles installer/ProjectProvingGrounds.iss over it. No Linux tar.gz or separate map pack zip.

Needs: Visual Studio's C++ build tools, Inno Setup 6 (winget install JRSoftware.InnoSetup), git.

usage: python -I build_installer.py [--git <git.exe>] [--skip-tests]
"""
import fnmatch
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
BUILD = os.path.join(os.path.dirname(ROOT), "installer_build")
PAYLOAD = os.path.join(BUILD, "payload")
SRC = os.path.join(BUILD, "src")                     # the committed copy (a worktree of HEAD): tests and the native build

# in the source repository for developers, not in a player's install (upstream's list, and this build's handoff notes)
DEV_ONLY = ("tools/test_*.py", "tools/run_tests.py", "tools/testdata.py", "tools/build_installer.py", "tools/make_release.py",
            "tools/human_data.py", "tools/baseline_compare.py", "tools/clean_bin.py", "tools/zoom_match.py",
            "brain/sim.py", "brain/sim_modes.py", "brain/simgear.py", "native/panel_preview.cpp", "native/build_preview.bat",
            "native/test_zoom.cpp", "native/tests/*", "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "SECURITY.md",
            "requirements.txt", "requirements-dev.txt", ".gitignore", ".github/*", "lidar-maps/*",
            "AGENTS.md", "DEVELOPER_HANDOFF_*.md", "docs/AI_REVIEW_HANDOFF_*.md", "native/pool_test.cpp",
            "native/build_pool_test.bat")
MAP_PACK = ("maps/*/heightmap.npz", "maps/*/topdown.png", "maps/*/glass.json", "maps/_shapes/*")
TEXT = (".py", ".md", ".json", ".txt", ".ini", ".cpp", ".h", ".bat", ".sh", ".iss", ".html", ".js", ".css", ".toml", "")


def step(msg):
    print(f"== {msg}", flush=True)


def git_exe():
    if "--git" in sys.argv:
        return sys.argv[sys.argv.index("--git") + 1]
    return shutil.which("git") or sys.exit("git was not found (pass --git <git.exe>)")


GIT = git_exe()


def git(*a, cwd=ROOT, out=True):
    r = subprocess.run([GIT, "-C", cwd, *a], capture_output=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(a)} failed:\n{r.stderr.decode(errors='replace')}")
    return r.stdout if out else None


def custom_version():
    return open(os.path.join(ROOT, "CUSTOM_VERSION"), encoding="utf-8").read().strip()


def match(rel, pats):
    return any(fnmatch.fnmatch(rel, p) for p in pats)


def iscc():
    """Inno Setup's compiler, or None (upstream's search)."""
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        for p in (os.path.join(base or "", "Programs", "Inno Setup 6", "ISCC.exe"),
                  os.path.join(base or "", "Inno Setup 6", "ISCC.exe")):
            if base and os.path.exists(p):
                return p
    return shutil.which("ISCC")


def committed_copy():
    """A clean worktree of HEAD at SRC; refuses while tracked files have changes not committed."""
    step("the committed copy (HEAD)")
    if git("status", "--porcelain", "--untracked-files=no").strip():
        raise SystemExit("tracked files have uncommitted changes: commit them first (the release is HEAD)")
    if os.path.exists(SRC):
        git("worktree", "remove", "--force", SRC, out=False)
    git("worktree", "prune", out=False)
    git("worktree", "add", "--detach", SRC, "HEAD", out=False)
    print(f"   HEAD {git('rev-parse', '--short', 'HEAD').decode().strip()}", flush=True)


def regress_gate():
    step("regression tests on the committed copy")
    py = os.path.join(ROOT, "python", "python.exe")
    r = subprocess.run([py, "-I", "-W", "ignore", "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"],
                       cwd=SRC, capture_output=True, text=True, errors="replace")
    tail = (r.stderr or "").strip().splitlines()[-3:]
    print("   " + " | ".join(tail), flush=True)
    if r.returncode:
        raise SystemExit("the regression tests fail: not building\n" + r.stderr[-3000:])


def stage_project():
    step("the public copy (git archive HEAD, less DEV_ONLY) and the map pack")
    data = git("archive", "--format=tar", "HEAD")
    n = 0
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for m in tar.getmembers():
            if not m.isfile() or match(m.name, DEV_ONLY):
                continue
            dst = os.path.join(PAYLOAD, *m.name.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with tar.extractfile(m) as f, open(dst, "wb") as g:
                g.write(f.read())
            n += 1
    pack = 0
    for dp, _, fs in os.walk(os.path.join(ROOT, "maps")):
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), ROOT).replace("\\", "/")
            if match(rel, MAP_PACK):
                dst = os.path.join(PAYLOAD, *rel.split("/"))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(os.path.join(dp, f), dst)
                pack += 1
    print(f"   {n} files of the project, {pack} of the map pack", flush=True)


def stage_native():
    step("the mod: botcore.dll, inject.exe and the app window (ppg_window.exe), built from the committed copy")
    nb = os.path.join(SRC, "native", "bin")
    for marker in ("models/h3_spartan.mdl", "art/fx_fire.rgba"):     # (build.bat's game-art steps: made by each install's
        p = os.path.join(nb, *marker.split("/"))                       #  own first-time setup, never shipped)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "a").close()
    for bat in ("build.bat", "build_window.bat"):
        r = subprocess.run(["cmd", "/c", os.path.join(SRC, "native", bat)], cwd=os.path.join(SRC, "native"),
                           capture_output=True, text=True, errors="replace")
        if "BUILD OK" not in r.stdout:
            raise SystemExit(f"native build ({bat}) failed:\n" + r.stdout[-3000:])
    dst = os.path.join(PAYLOAD, "native", "bin")
    os.makedirs(dst, exist_ok=True)
    for f in ("botcore.dll", "inject.exe", "ppg_window.exe"):
        shutil.copy2(os.path.join(nb, f), os.path.join(dst, f))
        print(f"   {f} {os.path.getsize(os.path.join(dst, f)):,} bytes", flush=True)


def stage_map_tools():
    step("the map tools (bsp2obj, model2obj)")
    src = os.path.join(ROOT, "tools", "map_tools")
    if not os.path.exists(os.path.join(src, "model2obj.exe")):
        raise SystemExit("tools/map_tools has no model2obj.exe: not building")
    shutil.copytree(src, os.path.join(PAYLOAD, "tools", "map_tools"), dirs_exist_ok=True)


def stage_python():
    step("Python (this install's bundled one) with numpy, scipy, Pillow")
    shutil.copytree(os.path.join(ROOT, "python"), os.path.join(PAYLOAD, "python"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    r = subprocess.run([os.path.join(PAYLOAD, "python", "python.exe"), "-I", "-c",
                        "import numpy, scipy.sparse.csgraph, PIL, ctypes, winreg, sqlite3; print('python ok')"],
                       capture_output=True, text=True)
    if "python ok" not in r.stdout:
        raise SystemExit("the bundled Python does not import the packages:\n" + r.stderr[-1500:])
    r = subprocess.run([os.path.join(PAYLOAD, "python", "python.exe"), "-I", "-c",
                        "import sys; sys.path.insert(0, '.'); import brain.bot, brain.director, tools.updater as u; "
                        "u.selftest(); print('brain ok', u.current())"],
                       cwd=PAYLOAD, capture_output=True, text=True)
    print("   " + (r.stdout.strip().replace("\n", " | ") or r.stderr[-800:]), flush=True)
    if "brain ok" not in r.stdout:
        raise SystemExit("the payload's brain does not import")


def privacy_scan():
    step("privacy scan")
    terms = {os.environ.get("USERNAME", ""), os.environ.get("USERPROFILE", "")}
    try:
        terms |= {t.strip() for t in open(os.path.join(ROOT, ".private_terms"), encoding="utf-8") if t.strip()}
    except OSError:
        pass
    terms = sorted({t.lower() for t in terms if len(t) >= 4})
    hits = []
    for dp, _, fs in os.walk(PAYLOAD):
        if os.path.relpath(dp, PAYLOAD).split(os.sep)[0] in ("python", "map_tools") or "map_tools" in dp:
            continue                                  # (third-party runtimes, copied as they are)
        for f in fs:
            if os.path.splitext(f)[1].lower() not in TEXT:
                continue
            p = os.path.join(dp, f)
            text = open(p, "rb").read().decode("utf-8", "replace").lower()
            for t in terms:
                if t in text:
                    hits.append((os.path.relpath(p, PAYLOAD), t))
    for p, t in hits[:20]:
        print(f"   {p}: holds '{t}'", flush=True)
    if hits:
        raise SystemExit(f"the privacy scan found {len(hits)} hit(s): not building")
    print(f"   {len(terms)} terms, no hit", flush=True)


def stage_texts():
    """Plain-text copies of the license and notices for the installer's license page."""
    with open(os.path.join(BUILD, "license.txt"), "w", encoding="utf-8") as f:
        f.write(open(os.path.join(ROOT, "NOTICE.md"), encoding="utf-8").read() + "\n\n")
        f.write(open(os.path.join(ROOT, "LICENSE.md"), encoding="utf-8").read())


def compile_setup():
    step("Setup.exe (Inno Setup)")
    exe = iscc() or sys.exit("Inno Setup 6 was not found (winget install JRSoftware.InnoSetup)")
    ver = custom_version()
    r = subprocess.run([exe, f"/DAppVersion={ver}", f"/DPayload={PAYLOAD}", f"/DBuildDir={BUILD}",
                        os.path.join(ROOT, "installer", "ProjectProvingGrounds.iss")], capture_output=True, text=True,
                       errors="replace")
    if r.returncode:
        raise SystemExit("Inno Setup failed:\n" + r.stdout[-3000:] + r.stderr[-1000:])
    out = os.path.join(BUILD, f"ProjectProvingGrounds-Setup-{ver}.exe")
    h = hashlib.sha256()
    with open(out, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    print(f"   {out}: {os.path.getsize(out) / 1048576:.0f} MB, sha256 {h.hexdigest()}", flush=True)
    return out


def main():
    committed_copy()
    try:
        if "--skip-tests" not in sys.argv:
            regress_gate()
        if os.path.exists(PAYLOAD):
            shutil.rmtree(PAYLOAD)
        os.makedirs(PAYLOAD)
        stage_project()
        stage_native()
        stage_map_tools()
        stage_python()
        privacy_scan()
        stage_texts()
        compile_setup()
    finally:
        git("worktree", "remove", "--force", SRC, out=False)
        git("worktree", "prune", out=False)


if __name__ == "__main__":
    main()
