#!/usr/bin/env bash
# =============================================================================
#  welcome.sh — open the welcome window (welcome/welcome.py, 4 first steps)
# =============================================================================
#  Usage: welcome.sh [--step N] open it (or bring it to the front), on step N
#         welcome.sh --first   open it only while ~/.local/state/inkpaw/
#                              welcome-done does not exist (for the autostart)
#  The window writes that flag itself when "Don't show at startup" is ticked.
#  The app is found next to this script's real location (project/welcome/),
#  so it works even before the session root links the welcome/ folder.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

PROJECT="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
APP="$PROJECT/welcome/welcome.py"
[ -f "$APP" ] || APP="$CFG/welcome/welcome.py"

if [ "${1:-}" = "--first" ] && [ -e "$STATE/welcome-done" ]; then
    exit 0
fi

if [ -f "$APP" ] && python3 -c 'import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Adw", "1")' 2>/dev/null; then
    [ "${1:-}" = "--first" ] && shift
    exec python3 -I "$APP" "$@"
fi
notify "Welcome" "needs GTK 4 + libadwaita (python-gobject)"
exit 1
