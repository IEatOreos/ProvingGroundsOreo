#!/bin/bash
# Steam launch option for Halo: The Master Chief Collection on Linux and Steam Deck:
#
#     "<this file>" %command%
#
# Steam runs MCC's command through this. When it is the anti-cheat off one (MCC-Win64-Shipping.exe), the game's
# program is swapped for the mod's Windows Python running tools/launch.py, in the very same Proton command, so it runs
# in MCC's own Proton session: launch.py starts MCC, loads the bots (inject.exe), and stays until MCC closes. The
# anti-cheat on choice (mcclauncher.exe), or a missing mod, runs the game exactly as Steam asked: bots never load into
# an anti-cheat session. Output: logs/linux_play.txt in the mod's folder.

APP="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
# shellcheck source=common.sh
. "$APP/installer/linux/common.sh"

args=("$@")
at=-1
for i in "${!args[@]}"; do
    case "${args[$i],,}" in
        *mcc-win64-shipping.exe) at=$i ;;
    esac
done
if [ "$at" -lt 0 ] || [ ! -f "$APP/python/python.exe" ] || [ ! -f "$APP/tools/launch.py" ]; then
    exec "$@"
fi

exe="${args[$at]}"
mcc="$(dirname "$(dirname "$(dirname "$(dirname "$exe")")")")"     # MCC/Binaries/Win64/<exe> -> MCC's folder
export PPG_LINUX=1
HB_MCC="$(ppg_winpath "$mcc")"
export HB_MCC
mkdir -p "$APP/logs"
exec "${args[@]:0:$at}" "$APP/python/python.exe" -u -I "$(ppg_winpath "$APP/tools/launch.py")" \
    --exe "$(ppg_winpath "$exe")" -- "${args[@]:$((at + 1))}" >>"$APP/logs/linux_play.txt" 2>&1
