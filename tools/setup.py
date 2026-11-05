"""First-time setup: builds everything that comes from the player's own copy of MCC (none of it ships with the mod),
step by step, skipping what is already there:

  1 game        finds The Master Chief Collection
  2 bots        this install's 15 bots (names, looks, clan tags), drawn once and kept
  3 recording   matches are recorded for the Observer (logs/trace_on; delete it to stop)
  4 map art     MCC's menu pictures and map names for the LiDAR view's map list (tools/map_art.py)
  5 logos       the game logos for the BOTS panel's profile view (tools/panel_art.py)
  6 3D bots     the profile view's 3D bots and the emblem art, from MCC's map files with the map tools
                (tools/make_models.py; a few minutes, about 470 MB)
  7 effects     the armor effect sprites (tools/fx_art.py, the map tools)
  8 looks       each bot's armor and emblem as rolled (tools/looks_export.py)

Each step prints one line, "STEP <n>/<total> <name>: done | already there | skipped (<why>) | failed: <why>", which
the launcher shows. A failed step does not stop the ones after it that do not need it. Steam installs MCC's games one
by one: what needs a game that is not installed is skipped (3D bots of that game, the effects without Halo: Reach),
and a copy of MCC with its menu art missing gets plain logos and the maps' own top-down pictures.

usage: python -I setup.py [--force]      (--force rebuilds every step)
       python -I setup.py --status       what is there, one line a step, nothing built
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
from brain import paths  # noqa: E402  (where MCC and the map tools are)

BIN = os.path.join(ROOT, "native", "bin")


def tool(name, *args):
    """Runs tools/<name> with this Python; (ok, the last line it printed)."""
    r = subprocess.run([sys.executable, "-I", os.path.join(HERE, name), *args], capture_output=True, text=True,
                       errors="replace", cwd=ROOT)
    lines = (r.stdout + r.stderr).strip().splitlines()
    return r.returncode == 0, (lines[-1] if lines else "")


def has(*rel):
    return all(os.path.exists(os.path.join(ROOT, *r.split("/"))) for r in rel)


def _bots():
    from brain import looks
    looks.profiles()
    return True, f"{len(looks.profiles())} bots"


def _recording():
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    open(os.path.join(ROOT, "logs", "trace_on"), "a").close()     # (tools/play.py records a match while it exists)
    return True, "matches are recorded for the Observer"


def _map_art():
    return tool("map_art.py")


def _logos():
    return tool("panel_art.py")


def _models():
    if not paths.map_tool("model2obj"):
        return False, "the map tools are missing (tools/map_tools: reinstall, or see docs/BUILDING.md)"
    return tool("make_models.py", "--clean-exports")


def _effects():
    if not paths.map_tool("model2obj"):
        return False, "the map tools are missing (tools/map_tools)"
    return tool("fx_art.py")


def _looks():
    return tool("looks_export.py")


def _no_reach():
    """Why the effects step does not apply (None: it does): they come from a Halo: Reach map."""
    return None if not paths.mcc() or "reach" in paths.games() else "Halo: Reach is not installed"


# (name, what shows it is done, builder, needs the game, why it does not apply on this PC (None: it does))
STEPS = (
    ("bots", lambda: has("native/bin/bot_profiles.ini"), _bots, False, None),
    ("recording", lambda: has("logs/trace_on"), _recording, False, None),
    ("map art", lambda: len(glob.glob(os.path.join(HERE, "view_art", "maps", "*.jpg"))) >= 100, _map_art, True, None),
    ("logos", lambda: has("native/bin/art/ce.rgba", "native/bin/art/h4.rgba"), _logos, True, None),
    ("3D bots", lambda: has("native/bin/models/made.txt") or has("native/bin/models/h3_spartan.mdl",
                                                                 "maps/_models/emblems_mcc"), _models, True, None),
    ("effects", lambda: has("native/bin/art/fx_fire.rgba"), _effects, True, _no_reach),
    ("looks", lambda: has("native/bin/bot_looks.ini"), _looks, False, None),
)
TOTAL = len(STEPS) + 1


def status():
    """[(name, done, note)] for the game and every step; a step that does not apply on this PC counts as done, its
    note says why ("" otherwise)."""
    out = [("game", bool(paths.mcc()), "")]
    for name, done, _, _, skip in STEPS:
        why = "" if done() else (skip() if skip else None) or ""
        out.append((name, bool(done() or why), why))
    return out


def game_line(mcc):
    """Step 1's line: where MCC is and which of its games are installed."""
    if not mcc:
        if paths.chosen():
            return f"failed: the MCC folder you chose is not there any more ({paths.chosen()}): choose it again in the launcher"
        return ("failed: The Master Chief Collection was not found (choose its folder in the launcher, Game folder; or "
                "install it through Steam)")
    have = paths.games(mcc)
    if not have:
        return f"failed: {mcc} has none of MCC's games installed (Steam: MCC > Properties > DLC)"
    missing = [paths.GAME_NAMES[g] for g in paths.GAME_MAPS if g not in have]
    return f"done ({mcc}" + (f"; not installed: {', '.join(missing)}" if missing else "") + ")"


def run(force=False):
    """Every step in order; returns the number that failed."""
    os.makedirs(BIN, exist_ok=True)
    mcc = paths.mcc()
    line = game_line(mcc)
    print(f"STEP 1/{TOTAL} game: {line}", flush=True)
    mcc = None if line.startswith("failed") else mcc
    failed = 0 if mcc else 1
    for n, (name, done, build, needs_game, skip) in enumerate(STEPS, 2):
        if done() and not force:
            print(f"STEP {n}/{TOTAL} {name}: already there", flush=True)
            continue
        if needs_game and not mcc:
            print(f"STEP {n}/{TOTAL} {name}: failed: needs the game", flush=True)
            failed += 1
            continue
        why = skip() if skip else None
        if why:
            print(f"STEP {n}/{TOTAL} {name}: skipped ({why})", flush=True)
            continue
        print(f"STEP {n}/{TOTAL} {name}: working ...", flush=True)
        try:
            ok, said = build()
        except Exception as e:                       # one step failing must not stop the others
            ok, said = False, f"{type(e).__name__}: {e}"
        failed += not ok
        print(f"STEP {n}/{TOTAL} {name}: " + ("done" + (f" ({said})" if said else "") if ok else f"failed: {said}"),
              flush=True)
    print("SETUP " + ("COMPLETE" if not failed else f"FINISHED WITH {failed} FAILED STEP(S)"), flush=True)
    return failed


if __name__ == "__main__":
    if "--status" in sys.argv:
        for name, done, why in status():
            print(f"{name}: {why or ('ready' if done else 'not yet')}")
    else:
        raise SystemExit(1 if run("--force" in sys.argv) else 0)
