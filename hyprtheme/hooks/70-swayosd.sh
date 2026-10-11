#!/usr/bin/env bash
# =============================================================================
#  hooks/70-swayosd.sh — restart swayosd-server (CSS is read at start)
# =============================================================================
#  Run by theme.sh after the templates are rendered. Delete / chmod -x to skip.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

# osd.sh server picks swayosd/style.css or the skin's swayosd/skins/<skin>.css
if pgrep -x swayosd-server >/dev/null; then
    "$SCRIPTS/osd.sh" server restart
fi
