"""Start MCC (anti-cheat off) and load botcore, so the BOTS tile shows in the custom game lobbies. Run by the launcher's
Play button (and "Play Halo with Bots.bat" in the project folder).

Which MCC: brain/paths.mcc() (HB_MCC, else the folder chosen in the launcher, else Steam's). Steam's own copy starts
through Steam (steam://rungameid/976730). A copy of the player's own (a second MCC folder, say one kept away from
updates) is not one Steam can start: its program is started directly, with steam_appid.txt (976730) beside it so it
starts as itself with anti-cheat off instead of handing over to Steam's copy. Steam must be running and signed in.

Linux / Steam Deck: Steam's launch option (installer/linux/ppg-run.sh %command%) runs this inside MCC's own Proton
session with --exe <MCC's program> [-- <its arguments>]: it starts the game itself, loads the bots, and stays until
the game closes.

usage: python -I launch.py [--exe <MCC-Win64-Shipping.exe> [-- <arguments>]]
"""
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
MCC = "MCC-Win64-Shipping.exe"
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import conflicts  # noqa: E402
from brain import paths  # noqa: E402


def running(name):
    return conflicts.process_running(name)


def start_copy(mcc):
    """Starts a copy of MCC that Steam does not start, directly; its process, or None when it cannot."""
    exe = os.path.join(mcc, paths.GAME_EXE)
    if not running("steam.exe"):
        print(f"Start Steam and sign in first, then press Play again: your MCC copy ({mcc}) needs Steam running.")
        return None
    for d in (mcc, os.path.dirname(exe)):            # (MCC's folder and the program's: where Steam's library looks)
        f = os.path.join(d, "steam_appid.txt")
        try:
            if not os.path.exists(f):
                with open(f, "w") as out:
                    out.write(paths.MCC_APPID)
        except OSError as e:
            print(f"could not write {f} ({e}): MCC may start Steam's copy instead")
    print(f"starting your MCC copy ({mcc}) with anti-cheat off")
    return subprocess.Popen([exe], cwd=os.path.dirname(exe))


def main():
    from brain import looks
    looks.profiles()             # this install's 15 bots, drawn on the first run and kept (brain/looks.py)
    exe = sys.argv[sys.argv.index("--exe") + 1] if "--exe" in sys.argv else None
    game = None
    if exe:                                          # (Linux: Steam's launch option, in MCC's Proton session)
        extra = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
        print(f"starting MCC with the bots: {exe}", flush=True)
        game = subprocess.Popen([exe, *extra], cwd=os.path.dirname(exe))
    elif paths.wine():
        print("On Linux and Steam Deck, start MCC from Steam and choose the anti-cheat off option: the launch option "
              "loads the bots (see the README, Linux and Steam Deck).")
        return
    elif not running(MCC):
        mcc = paths.mcc()
        if mcc and not paths.is_steam_copy(mcc):
            game = start_copy(mcc)
            if game is None:
                sys.exit(1)
        else:
            print("starting MCC from Steam (choose the anti-cheat OFF option if Steam asks)")
            os.startfile("steam://rungameid/976730")
    elif paths.chosen():
        where = conflicts.process_path(MCC)
        if where and not os.path.normcase(where).startswith(os.path.normcase(os.path.join(paths.chosen(), ""))):
            print(f"MCC is already running from {where}, not from your chosen folder ({paths.chosen()}): the bots load "
                  "into the running one. To play the other copy, quit MCC and press Play again.")
    for _ in range(180):
        if running(MCC):
            break
        if game and game.poll() is not None:
            sys.exit(f"MCC closed as it started (exit code {game.returncode})")
        time.sleep(1)
    else:
        sys.exit("MCC did not start")
    if any(running(n) for n in ("EasyAntiCheat.exe", "EasyAntiCheat_EOS.exe")):
        sys.exit("MCC is running with anti-cheat ON. Quit it and start it with anti-cheat off.")
    time.sleep(15)                                   # let MCC open its window and renderer
    dll = max(glob.glob(os.path.join(ROOT, "native", "bin", "botcore*.dll")), key=os.path.getmtime)
    import botctl
    inj = botctl.injector()                          # (put back if Windows Defender deleted it)
    if inj is None:
        sys.exit(1)
    r = subprocess.run([inj, os.path.abspath(dll)], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    print("Bots are ready: open Multiplayer > Custom Multiplayer > Halo: CE, Halo 2, Halo 2 Anniversary, Halo 3, Halo: Reach or Halo 4; the BOTS tile is next to"
          " START (or press B).", flush=True)
    if exe:                                          # (Steam counts the game as running while this does)
        sys.exit(game.wait())


if __name__ == "__main__":
    main()
