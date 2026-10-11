#!/usr/bin/env bash
# =============================================================================
#  aichat.sh — open / close the AI chat window (aichat/aichat.py)
# =============================================================================
#  Bar button 󰚩 and SUPER+I. Running it again closes the panel.
#  Settings: Settings window → AI assistant (provider, model, key, side…).
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

if [ -f "$CFG/aichat/aichat.py" ] && python3 -c 'import gi; gi.require_version("Adw", "1")' 2>/dev/null; then
    exec python3 -I "$CFG/aichat/aichat.py"
fi
notify "AI chat" "needs GTK 4 + libadwaita (python-gobject)"
exit 1
