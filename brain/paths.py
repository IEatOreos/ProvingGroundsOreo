"""Where things are installed on this PC: Steam's libraries, The Master Chief Collection, Halo's official mod kits, the
Visual Studio C++ build tools and the map tools. Nothing is assumed about drive letters: Steam's own registry key and
its library list (steamapps/libraryfolders.vdf) are read, and an environment variable overrides each answer:

    HB_STEAM_COMMON   a steamapps/common folder to look in first
    HB_MCC            The Master Chief Collection's folder
    HB_KIT_<NAME>     a mod kit's folder, e.g. HB_KIT_H3EK
    HB_VCVARS         vcvars64.bat of a Visual Studio C++ install
    HB_MAP_TOOLS      the folder with bsp2obj.exe and model2obj.exe (the separate map tools project)

MCC's folder, in order: HB_MCC, else the folder the player chose in the launcher (user/mcc_folder.txt, kept by updates
and Repair), else the copy Steam has installed, else another MCC folder in a Steam library.

    python -I brain/paths.py      prints what it finds
"""
import functools
import glob
import os
import re

MCC_NAME = "Halo The Master Chief Collection"
MCC_APPID = "976730"
GAME_EXE = os.path.join("MCC", "Binaries", "Win64", "MCC-Win64-Shipping.exe")    # in MCC's folder
CHOICE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user", "mcc_folder.txt")
# Halo's official mod kits (free on Steam), by their install folder names
KITS = ("HCEEK", "H2EK", "H2AMPEK", "H3EK", "H3ODSTEK", "HREK", "H4EK")


def _steam_roots():
    """Steam's own folders: its registry keys (the user's, the machine's), then the default install folder."""
    out = []
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for key, name in ((r"Software\Valve\Steam", "SteamPath"), (r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                              (r"SOFTWARE\Valve\Steam", "InstallPath")):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        out.append(winreg.QueryValueEx(k, name)[0])
                except OSError:
                    continue
    except ImportError:
        pass
    out.append(os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Steam"))
    return [os.path.normpath(p) for p in out if p and os.path.isdir(p)]


def library_paths(vdf_text):
    """The library folders listed in libraryfolders.vdf's text: "path" entries (any case), and the numbered entries of
    the file's older format ("1" "D:\\\\Games"); VDF escapes (doubled backslashes, \\") undone."""
    out = []
    for key, val in re.findall(r'^[ \t]*"(path|\d+)"[ \t]+"((?:[^"\\\n]|\\.)*)"', vdf_text, re.I | re.M):
        if key.lower() == "path" or not val.isdigit():           # (not an "apps" entry: app id and size)
            out.append(os.path.normpath(re.sub(r"\\(.)", r"\1", val)))
    return out


@functools.lru_cache(maxsize=None)
def steam_commons():
    """Every steamapps/common folder on this PC, the override first."""
    out = []
    if os.environ.get("HB_STEAM_COMMON"):
        out.append(os.environ["HB_STEAM_COMMON"])
    for root in _steam_roots():
        libs = [root]
        for vdf in (os.path.join(root, "steamapps", "libraryfolders.vdf"), os.path.join(root, "config", "libraryfolders.vdf")):
            try:
                libs += library_paths(open(vdf, encoding="utf-8", errors="replace").read())
            except OSError:
                pass
        out += [os.path.join(lib, "steamapps", "common") for lib in libs]
    seen, uniq = set(), []
    for p in out:
        key = os.path.normcase(os.path.normpath(p))
        if key not in seen and os.path.isdir(p):
            seen.add(key)
            uniq.append(os.path.normpath(p))
    return tuple(uniq)


def installed_in(common, name):
    """Whether Steam's own record of an app (steamapps/appmanifest_<id>.acf beside this common folder) puts the app
    with this install folder name here."""
    rx = re.compile(r'"installdir"\s+"%s"' % re.escape(name), re.I)
    for acf in glob.glob(os.path.join(os.path.dirname(common), "appmanifest_*.acf")):
        try:
            if rx.search(open(acf, encoding="utf-8", errors="replace").read()):
                return True
        except OSError:
            continue
    return False


def app(name, env=None):
    """An installed Steam app's folder by its install folder name (the env override first), or None. A folder of that
    name can be left behind in another library (a game moved or uninstalled): the library Steam says has it comes
    first."""
    if env and os.environ.get(env):
        return os.environ[env]
    found = [os.path.join(c, name) for c in steam_commons() if os.path.isdir(os.path.join(c, name))]
    return next((p for p in found if installed_in(os.path.dirname(p), name)), found[0] if found else None)


def steam_mcc():
    """The MCC folders Steam has installed (its appmanifest_976730.acf in that library names the folder): the copies
    Steam starts."""
    out = []
    for c in steam_commons():
        try:
            acf = open(os.path.join(os.path.dirname(c), f"appmanifest_{MCC_APPID}.acf"), encoding="utf-8",
                       errors="replace").read()
        except OSError:
            continue
        m = re.search(r'"installdir"\s+"([^"]+)"', acf, re.I)
        if m and os.path.isdir(os.path.join(c, m.group(1))):
            out.append(os.path.join(c, m.group(1)))
    return out


def installs():
    """Every MCC folder found in the Steam libraries, Steam's own copies first, then other usable ones (a copy left
    behind or set aside in a library), then folders of its name that are not (yet) usable."""
    seen, out = set(), []
    for p in steam_mcc() + [os.path.join(c, MCC_NAME) for c in steam_commons()]:
        key = os.path.normcase(os.path.normpath(p))
        if key not in seen and os.path.isdir(p):
            seen.add(key)
            out.append(os.path.normpath(p))
    steam = {os.path.normcase(p) for p in steam_mcc()}
    return sorted(out, key=lambda p: (os.path.normcase(p) not in steam, check(p) is not None))


def check(path):
    """Why this folder is not an MCC copy the mod can use, or None when it is."""
    if not path or not os.path.isdir(path):
        return "That folder does not exist."
    if not os.path.isfile(os.path.join(path, GAME_EXE)):
        return "That is not an MCC folder: MCC\\Binaries\\Win64\\MCC-Win64-Shipping.exe is not in it."
    if not games(path):
        return "MCC is there, but none of its games are installed (no map files)."
    return None


def find_root(path):
    """The MCC folder for a folder the player picked: that folder, one around it (MCC\\Binaries\\Win64 or MCC picked),
    or one in it (a steamapps\\common folder or a Steam library picked); else the folder itself."""
    path = os.path.normpath(path or "")
    near = [path, *(os.path.normpath(os.path.join(path, *[".."] * n)) for n in (1, 2, 3))]
    near += [os.path.join(path, *sub, MCC_NAME) for sub in ((), ("common",), ("steamapps", "common"))]
    return next((p for p in near if os.path.isfile(os.path.join(p, GAME_EXE))), path)


def chosen():
    """The MCC folder the player chose in the launcher, or None (automatic)."""
    try:
        return open(CHOICE, encoding="utf-8").read().strip() or None
    except OSError:
        return None


def choose(path):
    """Saves the player's MCC folder (None: back to automatic). (ok, the folder saved or why it was not)."""
    if path is None:
        if os.path.exists(CHOICE):
            os.remove(CHOICE)
        return True, None
    root = find_root(path)
    why = check(root)
    if why:
        return False, why
    os.makedirs(os.path.dirname(CHOICE), exist_ok=True)
    with open(CHOICE, "w", encoding="utf-8") as f:
        f.write(root + "\n")
    return True, root


def mcc():
    """The Master Chief Collection's folder, or None when it is not found (or the chosen folder is gone)."""
    if os.environ.get("HB_MCC"):
        return os.environ["HB_MCC"]
    c = chosen()
    if c:
        return c if os.path.isdir(c) else None
    found = installs()
    return found[0] if found else None


def is_steam_copy(path):
    """Whether this MCC folder is the one Steam starts (steam://rungameid), not a copy of its own."""
    return bool(path) and os.path.normcase(os.path.normpath(path)) in {os.path.normcase(p) for p in steam_mcc()}


def wine():
    """Whether this runs under Wine / Proton (Linux, Steam Deck): the Linux scripts set PPG_LINUX, and Wine's ntdll
    has wine_get_version."""
    if os.environ.get("PPG_LINUX"):
        return True
    try:
        import ctypes
        return hasattr(ctypes.windll.ntdll, "wine_get_version")
    except (ImportError, AttributeError, OSError):
        return False


def kit(name):
    """A Halo mod kit's folder (KITS), or None when it is not installed."""
    return app(name, "HB_KIT_" + name)


def steam_common():
    """The steamapps/common folder Steam's MCC is in (else the first one found), or None."""
    m = (steam_mcc() or installs() or [None])[0]
    if m:
        return os.path.dirname(m)
    commons = steam_commons()
    return commons[0] if commons else None


# MCC's games: their map folders (Steam installs each game on its own, so some may be missing), and their names
GAME_MAPS = {"ce": r"halo1\maps", "h2": r"halo2\h2_maps_win64_dx11", "h2a": r"groundhog\maps", "h3": r"halo3\maps",
             "odst": r"halo3odst\maps", "reach": r"haloreach\maps", "h4": r"halo4\maps"}
GAME_NAMES = {"ce": "Halo: CE", "h2": "Halo 2", "h2a": "Halo 2 Anniversary", "h3": "Halo 3", "odst": "Halo 3: ODST",
              "reach": "Halo: Reach", "h4": "Halo 4"}


def games(mcc_dir=None):
    """The MCC games installed (their maps are there), in GAME_MAPS order."""
    mcc_dir = mcc_dir or mcc()
    return [g for g, d in GAME_MAPS.items()
            if mcc_dir and glob.glob(os.path.join(mcc_dir, *d.split("\\"), "*.map"))]


def map_tool(name):
    """bsp2obj.exe / model2obj.exe of the separate map tools project (GPL-3.0, run as their own programs), or None:
    the HB_MAP_TOOLS folder, else tools/map_tools (where the installer puts them), else a proving-grounds-map-tools
    checkout beside this project (its bin folder, as its build.bat writes it)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for d in (os.environ.get("HB_MAP_TOOLS"), os.path.join(root, "tools", "map_tools"),
              os.path.join(os.path.dirname(root), "proving-grounds-map-tools", "bin")):
        if d and os.path.exists(os.path.join(d, name + ".exe")):
            return os.path.join(d, name + ".exe")
    return None


def need(path, what):
    """path, or a clear stop when it was not found (for the tools that cannot run without it)."""
    if not path:
        raise SystemExit(f"{what} was not found: install it through Steam, or set its environment variable "
                         f"(python -I brain/paths.py lists them)")
    return path


@functools.lru_cache(maxsize=None)
def vcvars():
    """vcvars64.bat of the newest Visual Studio with the C++ tools (vswhere), or None."""
    if os.environ.get("HB_VCVARS"):
        return os.environ["HB_VCVARS"]
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = os.path.join(pf86, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if os.path.exists(vswhere):
        import subprocess
        try:
            out = subprocess.run([vswhere, "-latest", "-products", "*", "-requires",
                                  "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                                 capture_output=True, text=True, timeout=20).stdout.strip()
            bat = os.path.join(out, "VC", "Auxiliary", "Build", "vcvars64.bat") if out else None
            if bat and os.path.exists(bat):
                return bat
        except (OSError, subprocess.SubprocessError):
            pass
    for bat in sorted(glob.glob(os.path.join(pf86, "Microsoft Visual Studio", "*", "*", "VC", "Auxiliary", "Build",
                                             "vcvars64.bat")), reverse=True):
        return bat
    return None


if __name__ == "__main__":
    assert library_paths('"0"\n{\n\t"path"\t\t"D:\\\\Games\\\\Steam"\n}') == [os.path.normpath("D:\\Games\\Steam")]
    import tempfile                                  # a folder left behind in one library, the install in another
    with tempfile.TemporaryDirectory() as tmp:
        old, new = (os.path.join(tmp, lib, "steamapps", "common") for lib in ("old", "new"))
        for c in (old, new):
            os.makedirs(os.path.join(c, MCC_NAME))
        open(os.path.join(new, "..", "appmanifest_976730.acf"), "w").write(f'"AppState"\n{{\n\t"installdir"\t\t"{MCC_NAME}"\n}}')
        assert installed_in(new, MCC_NAME) and not installed_in(old, MCC_NAME)
        os.makedirs(os.path.join(new, MCC_NAME, "halo3", "maps"))
        open(os.path.join(new, MCC_NAME, "halo3", "maps", "construct.map"), "w").close()
        assert games(os.path.join(new, MCC_NAME)) == ["h3"] and games(os.path.join(old, MCC_NAME)) == []
    print("steam libraries:", ", ".join(steam_commons()) or "none found")
    print("MCC:", mcc() or "not found (choose its folder in the launcher, or set HB_MCC)", "| games:",
          ", ".join(games()) or "none", "| chosen:", chosen() or "no (automatic)")
    print("MCC copies found:", ", ".join(installs()) or "none")
    for k in KITS:
        print(f"{k}:", kit(k) or "not installed")
    print("vcvars64.bat:", vcvars() or "not found (set HB_VCVARS)")
    for t in ("bsp2obj", "model2obj"):
        print(f"{t}:", map_tool(t) or "not found (the installer puts it in tools/map_tools; or set HB_MAP_TOOLS)")
