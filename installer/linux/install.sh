#!/bin/bash
# Installs Project Proving Grounds on Linux and Steam Deck (SteamOS), for MCC on Steam through Proton.
#
#   ./install.sh                 from the unpacked ProjectProvingGrounds-Linux-<version>.tar.gz (its payload folder)
#   ./install.sh --download      downloads the newest Linux release from GitHub first
#   ./install.sh --payload DIR   installs the files of DIR (an unpacked payload, or a Windows install folder)
#   --no-setup                   skips the first-time setup (run it later from the launcher)
#
# What it does: copies the mod to ~/.local/share/project-proving-grounds/app (an update keeps your LiDAR scans,
# learned map data, recordings and settings), runs the first-time setup in the mod's own Wine prefix with MCC's Proton,
# adds "Project Proving Grounds" to the application menu, and prints the Steam launch option that loads the bots.
# MCC's own files and its Proton prefix are not changed. No root rights needed.
set -euo pipefail

HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO="AyoItzKye/project-proving-grounds"
PAYLOAD="" DOWNLOAD=0 SETUP=1
while [ $# -gt 0 ]; do
    case "$1" in
        --payload) PAYLOAD="$2"; shift ;;
        --download) DOWNLOAD=1 ;;
        --no-setup) SETUP=0 ;;
        -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
        *) printf 'unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done

if [ -z "$PAYLOAD" ] && [ "$DOWNLOAD" = 0 ]; then
    for d in "$HERE/payload" "$HERE/../.."; do        # beside this script (the release), or the install it is in
        if [ -f "$d/tools/launcher.py" ] && [ -f "$d/python/python.exe" ]; then PAYLOAD="$d"; break; fi
    done
    [ -n "$PAYLOAD" ] || DOWNLOAD=1
fi
if [ "$DOWNLOAD" = 1 ]; then
    command -v curl >/dev/null || { echo "curl is needed to download the release" >&2; exit 1; }
    url="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" |
           grep -o '"browser_download_url": *"[^"]*-Linux-[^"]*\.tar\.gz"' | head -n 1 | sed 's/.*"\(https[^"]*\)"/\1/')"
    [ -n "$url" ] || { echo "no Linux download was found on the newest GitHub release of $REPO" >&2; exit 1; }
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    echo "downloading $url"
    curl -fL --progress-bar "$url" | tar -xz -C "$tmp"
    PAYLOAD="$(find "$tmp" -mindepth 2 -maxdepth 2 -type d -name payload | head -n 1)"
fi
PAYLOAD="$(cd "$PAYLOAD" && pwd)"
[ -f "$PAYLOAD/installer/linux/common.sh" ] || { echo "$PAYLOAD is not a Project Proving Grounds payload" >&2; exit 1; }
# shellcheck source=common.sh
. "$PAYLOAD/installer/linux/common.sh"

ppg_find
ppg_say "Steam:  $PPG_STEAM_ROOT"
ppg_say "MCC:    $PPG_MCC_DIR"
ppg_say "Proton: $PPG_PROTON_DIR${PPG_SLR:+ (in $(basename "$(dirname "$PPG_SLR")"))}"
ppg_mcc_running && ppg_die "Close Halo: The Master Chief Collection first (the bots may be loaded into it), then run this again."

DATA="$(ppg_data_dir)"
APP="$DATA/app"
mkdir -p "$APP"
if [ "$PAYLOAD" != "$(cd "$APP" && pwd)" ]; then
    ppg_say "installing to $APP"
    # an update first clears the previous version's code and documents (as the Windows installer does); the player's
    # logs, maps, LiDAR scans, settings (user/) and the art the setup built stay
    rm -rf "$APP/docs" "$APP/ghidra" "$APP/native/tests" "$APP/tools/menu_titles" "$APP/tools/__pycache__" \
           "$APP/brain/__pycache__"
    rm -f "$APP"/tools/*.py "$APP"/tools/*.html "$APP"/tools/*.ps1 "$APP"/brain/*.py "$APP"/native/*.cpp \
          "$APP"/native/*.h "$APP"/native/*.bat
    cp -a "$PAYLOAD/." "$APP/"
fi
chmod +x "$APP"/installer/linux/*.sh
mkdir -p "$APP/logs"

if [ "$SETUP" = 1 ]; then
    ppg_say "first-time setup (a few minutes; the first start of the mod's Wine prefix adds a minute) ..."
    ppg_wine "$APP/python/python.exe" -u -I "$(ppg_winpath "$APP/tools/setup.py")" | tee "$APP/logs/linux_setup.txt" ||
        ppg_say "the setup did not finish: run it again from the launcher (Run setup), see $APP/logs/linux_setup.txt"
fi

# the application menu entry (and one on the desktop, when there is a Desktop folder)
icons="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$icons"
entry="$icons/project-proving-grounds.desktop"
cat >"$entry" <<EOF
[Desktop Entry]
Type=Application
Name=Project Proving Grounds
Comment=PvP bots for Halo: The Master Chief Collection
Exec="$APP/installer/linux/ppg-launcher.sh"
Icon=$APP/installer/linux/icon.png
Terminal=false
Categories=Game;
EOF
chmod +x "$entry"
desktop="$(xdg-user-dir DESKTOP 2>/dev/null || printf '%s' "$HOME/Desktop")"
if [ -d "$desktop" ]; then
    cp "$entry" "$desktop/" && chmod +x "$desktop/project-proving-grounds.desktop"
fi
command -v update-desktop-database >/dev/null && update-desktop-database "$icons" >/dev/null 2>&1 || true

option="\"$APP/installer/linux/ppg-run.sh\" %command%"
copied=""
if command -v wl-copy >/dev/null && printf '%s' "$option" | wl-copy 2>/dev/null; then copied=" (copied to the clipboard)"
elif command -v xclip >/dev/null && printf '%s' "$option" | xclip -selection clipboard 2>/dev/null; then copied=" (copied to the clipboard)"
fi
cat <<EOF

Project Proving Grounds is installed.

One step in Steam (once): Halo: The Master Chief Collection > Properties > General > Launch Options, paste$copied:

    $option

Then press Play in Steam and choose the anti-cheat off option. The bots load as MCC starts; in MCC open
Multiplayer > Custom Multiplayer, the BOTS tile is next to START (or press B).

The launcher (setup, Repair, Observer, LiDAR tools): "Project Proving Grounds" in the application menu.
To uninstall: $APP/installer/linux/uninstall.sh
EOF
