#!/usr/bin/env bash
# =============================================================================
#  hooks/60-walker.sh — restart the Walker service so it loads the new theme CSS
# =============================================================================
#  Run by theme.sh after the templates are rendered. Delete / chmod -x to skip.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

if pgrep -f "walker --gapplication-service" >/dev/null; then
    pkill -f "walker --gapplication-service"; sleep 0.3
    setsid -f walker --gapplication-service >/dev/null 2>&1
fi
