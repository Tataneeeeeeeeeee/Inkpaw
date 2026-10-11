#!/usr/bin/env bash
# =============================================================================
#  hooks/90-quickpanel.sh — new theme: restart the resident quick panel
# =============================================================================
#  The panel (quickpanel/quickpanel.py) stays in memory between openings and
#  reads its stylesheets once, so it is restarted to pick up the new colors.
#  Nothing happens when it is not running.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"
gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
    --method org.freedesktop.DBus.NameHasOwner dev.inkpaw.QuickPanel 2>/dev/null | grep -q true || exit 0
exec "$SCRIPTS/quickpanel.sh" --restart
