#!/bin/bash
# Removes Project Proving Grounds from Linux / Steam Deck: the mod's folder (asks whether to keep your LiDAR scans,
# learned map data and recorded matches), its Wine prefix and its menu entries. MCC itself is not changed.
#   ./uninstall.sh [--yes]      (--yes: no questions, keeps your data)
set -euo pipefail

HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
for c in "$HERE/common.sh" "$HERE/payload/installer/linux/common.sh"; do
    # shellcheck source=common.sh
    if [ -f "$c" ]; then . "$c"; break; fi
done
declare -F ppg_data_dir >/dev/null || { echo "common.sh was not found beside this script" >&2; exit 1; }
DATA="$(ppg_data_dir)"
APP="$DATA/app"
[ -d "$DATA" ] || { echo "Project Proving Grounds is not installed ($DATA)"; exit 0; }
ppg_mcc_running && ppg_die "Close Halo: The Master Chief Collection first (the bots are loaded into it)."

keep=y
if [ "${1:-}" != "--yes" ]; then
    read -r -p "Keep your LiDAR scans, what the bots learned on each map and your recorded matches? [Y/n] " keep
fi
if [ "${keep,,}" = n ]; then
    rm -rf "$APP"
else
    find "$APP" -mindepth 1 -maxdepth 1 ! -name maps ! -name logs ! -name user -exec rm -rf {} +
    echo "kept: $APP/maps, $APP/logs and $APP/user"
fi
rm -rf "$DATA/prefix"
# Steam's launch option still points here: a stand-in that starts the game as Steam asks, so MCC keeps starting
mkdir -p "$APP/installer/linux"
printf '#!/bin/bash\nexec "$@"\n' >"$APP/installer/linux/ppg-run.sh"
chmod +x "$APP/installer/linux/ppg-run.sh"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/project-proving-grounds.desktop"
desktop="$(xdg-user-dir DESKTOP 2>/dev/null || printf '%s' "$HOME/Desktop")"
rm -f "$desktop/project-proving-grounds.desktop"
cat <<EOF
Project Proving Grounds is removed.
Last step in Steam: Halo: The Master Chief Collection > Properties > General > Launch Options: clear the line.
(Until then MCC still starts normally, through a small stand-in left at $APP/installer/linux/ppg-run.sh.)
EOF
