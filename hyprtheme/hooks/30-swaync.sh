#!/usr/bin/env bash
# =============================================================================
#  hooks/30-swaync.sh — reload swaync CSS
# =============================================================================
#  Run by theme.sh after the templates are rendered. Delete / chmod -x to skip.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

"$SCRIPTS/notifications.sh" reload    # reload the CSS, or (re)start swaync if another daemon took over
