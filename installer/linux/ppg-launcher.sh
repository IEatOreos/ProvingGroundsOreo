#!/bin/bash
# Opens Project Proving Grounds' launcher on Linux and Steam Deck (the desktop entry runs this): the launcher runs in
# the mod's own Wine prefix with MCC's Proton and shows in the system's browser (there is no WebView2 under Wine).
# The first start of the prefix takes a minute. Output: logs/launcher/linux.txt in the mod's folder.

APP="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
# shellcheck source=common.sh
. "$APP/installer/linux/common.sh"
URL="http://127.0.0.1:8793/"

open_page() { xdg-open "$1" >/dev/null 2>&1 || ppg_say "Open $1 in your browser."; }

if ppg_port_open 8793; then                          # it runs already: show its page again
    open_page "$URL"
    exit 0
fi
ppg_find
mkdir -p "$APP/logs/launcher"
( ppg_wine "$APP/python/python.exe" -I "$(ppg_winpath "$APP/tools/launcher.py")" --no-window \
      >"$APP/logs/launcher/linux.txt" 2>&1 & )
for _ in $(seq 1 180); do
    if ppg_port_open 8793; then
        open_page "$URL${1:+?setup=1}"
        exit 0
    fi
    sleep 1
done
ppg_die "the launcher did not start: see $APP/logs/launcher/linux.txt"
