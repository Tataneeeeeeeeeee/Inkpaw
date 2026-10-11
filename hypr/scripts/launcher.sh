#!/usr/bin/env bash
# =============================================================================
#  launcher.sh — open the Spotlight launcher (Walker)
# =============================================================================
#  Usage: launcher.sh                 all default providers (apps, calc, web…)
#         launcher.sh clipboard       clipboard history only
#         launcher.sh symbols         emoji / symbols only
#         launcher.sh files           file search only
#  Falls back to rofi if Walker is not installed.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

provider="${1:-}"

# Sectioned Spotlight (spotlight/spotlight.py) for the main search, unless
# LAUNCHER="walker" in settings.conf. Clipboard / symbols modes use Walker.
if [ -z "$provider" ] && [ "${LAUNCHER:-spotlight}" != "walker" ] && [ -f "$CFG/spotlight/spotlight.py" ] \
   && python3 -c 'import gi; gi.require_version("Gtk4LayerShell", "1.0")' 2>/dev/null; then
    pgrep -x elephant >/dev/null || { setsid -f elephant >/dev/null 2>&1; sleep 0.3; }
    exec python3 -I "$CFG/spotlight/spotlight.py"
fi

if have walker; then
    # Elephant (the backend) must be running; start it lazily if needed.
    pgrep -x elephant >/dev/null || { setsid -f elephant >/dev/null 2>&1; sleep 0.3; }
    if [ -n "$provider" ]; then
        exec walker -m "$provider"
    fi
    exec walker
fi

# Fallback: rofi drun
exec rofi -show drun -theme "$CFG/rofi/themes/launcher.rasi"
