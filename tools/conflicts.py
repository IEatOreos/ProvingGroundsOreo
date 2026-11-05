"""Other mods that can clash with Project Proving Grounds, found in the MCC folder, and a clean launch without them.

What can clash: a DLL another mod drops beside MCC's program so Windows loads it into the game (a "proxy" DLL named
like a system one: dxgi.dll, d3d11.dll, dinput8.dll, version.dll ... ReShade, Special K, ASI loaders, other injectors
and overlays), and ASI plugin files. They hook the same game and the same drawing as this mod. MCC's own DLLs are
known and never reported. Steam Workshop mods are only counted: MCC loads them only when started with mods, and they
change maps and game files, not the game's code.

A clean launch moves the clashing files aside (renamed <file>.ppg-off) for one session; restore() puts them back,
and the launcher does so when MCC has closed (and at its next start, if the PC was turned off in between).

usage: python -I conflicts.py              the report
       python -I conflicts.py --off         move them aside (before starting MCC)
       python -I conflicts.py --restore     put them back
       python -I conflicts.py --restore-after-mcc   put them back once MCC has started and closed again
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from brain import paths  # noqa: E402  (where MCC is)

OFF = ".ppg-off"
# names Windows would load from the program's folder in place of a system DLL: the usual proxy loaders
PROXY = {"dxgi.dll", "d3d11.dll", "d3d12.dll", "d3d9.dll", "d3d10.dll", "dinput8.dll", "version.dll", "winmm.dll",
         "xinput1_3.dll", "xinput1_4.dll", "xinput9_1_0.dll", "dsound.dll", "opengl32.dll", "winhttp.dll", "wininet.dll",
         "msimg32.dll", "dbghelp.dll", "uxtheme.dll", "bink2w64_.dll"}
# the folders Windows loads them from: the launcher's and the game's
FOLDERS = ("", os.path.join("MCC", "Binaries", "Win64"))


def scan(mcc=None):
    """[(path, why)] of the files that can clash, in MCC's launcher and game folders."""
    mcc = mcc or paths.mcc()
    if not mcc:
        return []
    out = []
    for sub in FOLDERS:
        d = os.path.join(mcc, sub)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            low = f.lower()
            if low in PROXY:
                out.append((os.path.join(d, f), "a DLL other mods put beside the game so it loads into it"))
            elif low.endswith(".asi"):
                out.append((os.path.join(d, f), "an ASI plugin (loaded into the game by an ASI loader)"))
    return out


def workshop_count():
    """How many Steam Workshop items for MCC are subscribed (MCC loads them only when started with mods)."""
    for common in paths.steam_commons():
        d = os.path.join(os.path.dirname(common), "workshop", "content", "976730")
        if os.path.isdir(d):
            return len(os.listdir(d))
    return 0


def turn_off(found=None):
    """Moves every clashing file aside for one session; returns the files moved."""
    moved = []
    for p, _ in (found if found is not None else scan()):
        os.replace(p, p + OFF)
        moved.append(p)
    return moved


def restore(mcc=None):
    """Puts back every file a clean launch moved aside; returns how many."""
    mcc = mcc or paths.mcc()
    n = 0
    for sub in FOLDERS if mcc else ():
        for p in glob.glob(os.path.join(mcc, sub, "*" + OFF)):
            orig = p[:-len(OFF)]
            if not os.path.exists(orig):
                os.replace(p, orig)
                n += 1
    return n


def report():
    found = scan()
    lines = [f"{len(found)} file(s) in the MCC folder can clash with the bots"]
    lines += [f"  {os.path.relpath(p, paths.mcc())}: {why}" for p, why in found]
    w = workshop_count()
    if w:
        lines.append(f"{w} Steam Workshop item(s) subscribed for MCC (only loaded when MCC starts with mods)")
    return "\n".join(lines)


def processes():
    """[(pid, file name)] of every process, asked of Windows directly (a process snapshot): no child program, so
    nothing opens a console window."""
    import ctypes
    import ctypes.wintypes as wt

    class ENTRY(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]
    k = ctypes.windll.kernel32
    k.CreateToolhelp32Snapshot.restype = wt.HANDLE
    snap = k.CreateToolhelp32Snapshot(0x2, 0)                  # TH32CS_SNAPPROCESS
    if not snap or snap == wt.HANDLE(-1).value:
        return []
    out = []
    try:
        e = ENTRY()
        e.dwSize = ctypes.sizeof(ENTRY)
        ok = k.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            out.append((e.th32ProcessID, e.szExeFile))
            ok = k.Process32NextW(snap, ctypes.byref(e))
        return out
    finally:
        k.CloseHandle(snap)


def process_running(name):
    """Whether a process with this file name runs."""
    return any(n.lower() == name.lower() for _, n in processes())


def stop_inside(folder, keep=()):
    """Ends every process whose program file is inside folder (the mod's Python, its app windows, the injector) but
    the pids in keep; returns how many. For the uninstaller: no file of the mod may be in use."""
    import ctypes
    import ctypes.wintypes as wt
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wt.HANDLE
    root = os.path.normcase(os.path.abspath(folder)) + os.sep
    n = 0
    for pid, _ in processes():
        if pid in keep or not pid:
            continue
        h = k.OpenProcess(0x1000 | 0x0001, False, pid)          # QUERY_LIMITED_INFORMATION | TERMINATE
        if not h:
            continue
        try:
            buf, size = ctypes.create_unicode_buffer(1024), wt.DWORD(1024)
            if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)) and \
                    os.path.normcase(buf.value).startswith(root) and k.TerminateProcess(h, 0):
                n += 1
        finally:
            k.CloseHandle(h)
    return n


def process_path(name):
    """The program file of the first running process with this file name, or None."""
    import ctypes
    import ctypes.wintypes as wt
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wt.HANDLE
    for pid, n in processes():
        if n.lower() != name.lower():
            continue
        h = k.OpenProcess(0x1000, False, pid)                    # QUERY_LIMITED_INFORMATION
        if h:
            try:
                buf, size = ctypes.create_unicode_buffer(1024), wt.DWORD(1024)
                if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                    return buf.value
            finally:
                k.CloseHandle(h)
    return None


def mcc_running():
    return process_running("MCC-Win64-Shipping.exe")


def restore_after_mcc(start_wait=180):
    """Waits for MCC to start (up to start_wait s) and then to close, then puts the moved files back."""
    import time
    for _ in range(start_wait):
        if mcc_running():
            break
        time.sleep(1)
    while mcc_running():
        time.sleep(5)
    return restore()


if __name__ == "__main__":
    if "--off" in sys.argv:
        print(f"moved aside: {len(turn_off())}")
    elif "--restore-after-mcc" in sys.argv:
        print(f"put back: {restore_after_mcc()}")
    elif "--restore" in sys.argv:
        print(f"put back: {restore()}")
    else:
        print(report())
