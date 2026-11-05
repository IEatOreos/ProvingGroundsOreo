#!/bin/bash
# Project Proving Grounds on Linux and Steam Deck: what the other scripts share (sourced, not run).
#
# MCC runs through Proton (Wine). The mod's Windows parts (its bundled Windows Python, inject.exe, botcore.dll) run
# through the same Proton:
#   - in the game: Steam's launch option ("<app>/installer/linux/ppg-run.sh" %command%) starts tools/launch.py in
#     MCC's own Proton session (same prefix, same wineserver), which starts the game and loads the bots; botcore then
#     starts the brain inside the game's session.
#   - outside the game (the launcher, the first-time setup, the tools): a Wine prefix of the mod's own, run with MCC's
#     Proton, so MCC's prefix (compatdata/976730) is never changed and the launcher never holds it open.
# Nothing is installed into MCC's prefix: the mod lives in its own folder, which Wine reaches as drive Z:.
#
# Overrides: PPG_STEAM (Steam's folder), PPG_MCC (MCC's folder), PPG_PROTON (a Proton folder with its proton script).

PPG_APPID=976730

ppg_say() { printf '%s\n' "$*"; }
ppg_die() { printf 'Project Proving Grounds: %s\n' "$*" >&2; exit 1; }

# Steam's folders: native (~/.steam/steam, ~/.local/share/Steam) and Flatpak; one line each, no repeats
ppg_steam_roots() {
    local d
    for d in "${PPG_STEAM:-}" "$HOME/.steam/steam" "$HOME/.steam/root" "$HOME/.local/share/Steam" \
             "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam" \
             "$HOME/.var/app/com.valvesoftware.Steam/data/Steam"; do
        if [ -n "$d" ] && [ -d "$d/steamapps" ]; then readlink -f "$d"; fi
    done | awk '!seen[$0]++'
}

# every Steam library folder (libraryfolders.vdf "path" entries, any case; SD cards included), one line each
ppg_libraries() {
    local root
    while IFS= read -r root; do
        printf '%s\n' "$root"
        if [ -f "$root/steamapps/libraryfolders.vdf" ]; then
            sed -n 's/^[[:space:]]*"[Pp][Aa][Tt][Hh]"[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' \
                "$root/steamapps/libraryfolders.vdf" | sed 's/\\\\/\\/g'
        fi
    done < <(ppg_steam_roots)
    return 0
}

# Linux path -> the Windows path Wine sees (drive Z: is /)
ppg_winpath() { local p="$1"; printf 'Z:%s' "${p//\//\\}"; }

# finds Steam, MCC, its library and compatdata, and the Proton to use; sets PPG_STEAM_ROOT PPG_MCC_DIR PPG_LIB
# PPG_COMPAT PPG_PROTON_DIR PPG_SLR (the Steam Linux Runtime entry point, may be empty)
ppg_find() {
    PPG_STEAM_ROOT="$(ppg_steam_roots | head -n 1)"
    [ -n "$PPG_STEAM_ROOT" ] || ppg_die "Steam was not found (set PPG_STEAM to its folder, e.g. ~/.local/share/Steam)."
    PPG_MCC_DIR="" PPG_LIB=""
    if [ -n "${PPG_MCC:-}" ]; then
        PPG_MCC_DIR="$(readlink -f "$PPG_MCC")"
        PPG_LIB="$(dirname "$(dirname "$(dirname "$PPG_MCC_DIR")")")"
    else
        local lib dir
        while IFS= read -r lib; do
            [ -f "$lib/steamapps/appmanifest_$PPG_APPID.acf" ] || continue
            dir="$(sed -n 's/^[[:space:]]*"[Ii][Nn][Ss][Tt][Aa][Ll][Ll][Dd][Ii][Rr]"[[:space:]]*"\(.*\)".*$/\1/p' \
                   "$lib/steamapps/appmanifest_$PPG_APPID.acf" | head -n 1)"
            if [ -n "$dir" ] && [ -d "$lib/steamapps/common/$dir" ]; then
                PPG_MCC_DIR="$lib/steamapps/common/$dir" PPG_LIB="$lib"
                break
            fi
        done < <(ppg_libraries | awk '!seen[$0]++')
    fi
    [ -n "$PPG_MCC_DIR" ] && [ -f "$PPG_MCC_DIR/MCC/Binaries/Win64/MCC-Win64-Shipping.exe" ] ||
        ppg_die "Halo: The Master Chief Collection was not found in your Steam libraries (install it, or set PPG_MCC to its folder)."
    PPG_COMPAT="$PPG_LIB/steamapps/compatdata/$PPG_APPID"
    # Proton: the one MCC last ran with (compatdata/976730/config_info, line 3 is its lib folder), else the newest
    PPG_PROTON_DIR="${PPG_PROTON:-}"
    if [ -z "$PPG_PROTON_DIR" ] && [ -f "$PPG_COMPAT/config_info" ]; then
        local d
        d="$(sed -n 3p "$PPG_COMPAT/config_info")"
        while [ -n "$d" ] && [ "$d" != "/" ] && [ ! -f "$d/proton" ]; do d="$(dirname "$d")"; done
        if [ -f "$d/proton" ]; then PPG_PROTON_DIR="$d"; fi
    fi
    if [ -z "$PPG_PROTON_DIR" ]; then
        PPG_PROTON_DIR="$( { ppg_libraries | while IFS= read -r lib; do
                                 for d in "$lib"/steamapps/common/Proton*/; do printf '%s\n' "$d"; done; done
                             for d in "$PPG_STEAM_ROOT"/compatibilitytools.d/*/; do printf '%s\n' "$d"; done; } |
                           while IFS= read -r d; do if [ -f "$d/proton" ]; then printf '%s\n' "${d%/}"; fi; done |
                           sort -V | tail -n 1 || true)"
    fi
    [ -n "$PPG_PROTON_DIR" ] && [ -f "$PPG_PROTON_DIR/proton" ] ||
        ppg_die "No Proton was found. Start MCC once from Steam (it installs Proton), or set PPG_PROTON to a Proton folder."
    # the Steam Linux Runtime the Proton asks for (toolmanifest.vdf: 1628350 sniper, 1391110 soldier)
    PPG_SLR=""
    local want=""
    grep -q '1628350' "$PPG_PROTON_DIR/toolmanifest.vdf" 2>/dev/null && want=SteamLinuxRuntime_sniper
    grep -q '1391110' "$PPG_PROTON_DIR/toolmanifest.vdf" 2>/dev/null && want=SteamLinuxRuntime_soldier
    if [ -n "$want" ]; then
        local lib
        while IFS= read -r lib; do
            if [ -x "$lib/steamapps/common/$want/_v2-entry-point" ]; then
                PPG_SLR="$lib/steamapps/common/$want/_v2-entry-point"
                break
            fi
        done < <(ppg_libraries)
    fi
}

# where the mod lives: ~/.local/share/project-proving-grounds (Flatpak Steam: inside its own data folder, the only
# place its launch option can reach)
ppg_data_dir() {
    case "$(ppg_steam_roots | head -n 1)" in
        "$HOME/.var/app/com.valvesoftware.Steam/"*) printf '%s\n' "$HOME/.var/app/com.valvesoftware.Steam/data/project-proving-grounds" ;;
        *) printf '%s\n' "${XDG_DATA_HOME:-$HOME/.local/share}/project-proving-grounds" ;;
    esac
}

# runs a Windows program of the mod in the mod's own prefix (<data>/prefix), with MCC's Proton; waits for it
ppg_wine() {
    local data
    data="$(ppg_data_dir)"
    mkdir -p "$data/prefix"
    export STEAM_COMPAT_CLIENT_INSTALL_PATH="$PPG_STEAM_ROOT" STEAM_COMPAT_DATA_PATH="$data/prefix"
    export STEAM_COMPAT_APP_ID=0 SteamAppId=0 SteamGameId=0 PPG_LINUX=1
    export HB_STEAM_COMMON
    HB_STEAM_COMMON="$(ppg_winpath "$(dirname "$PPG_MCC_DIR")")"     # (the folder MCC is in)
    if [ -n "$PPG_SLR" ]; then
        "$PPG_SLR" --verb=waitforexitandrun -- "$PPG_PROTON_DIR/proton" waitforexitandrun "$@"
    else
        "$PPG_PROTON_DIR/proton" waitforexitandrun "$@"
    fi
}

ppg_port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

ppg_mcc_running() { pgrep -f 'MCC-Win64-Shipping\.exe' >/dev/null 2>&1; }
