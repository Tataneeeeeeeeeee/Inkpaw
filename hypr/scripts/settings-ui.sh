#!/usr/bin/env bash
# =============================================================================
#  settings-ui.sh — open the settings
# =============================================================================
#  The "Hyprland settings" window (settings-app/, GTK 4 + libadwaita) when
#  available, otherwise the rofi menu. SETTINGS_UI="rofi" forces the menu.
#  Usage: settings-ui.sh [Page]     open on a page: Bar, Appearance, Windows…
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

# Already open (maybe on another workspace)? Jump to it instead of doing nothing.
if [ "${SETTINGS_UI:-app}" != "rofi" ] && [ $# -eq 0 ] && have hyprctl; then
    addr=$(hyprctl clients -j 2>/dev/null | jq -r '.[] | select(.class == "dev.inkpaw.Settings") | .address' | head -1)
    if [ -n "$addr" ]; then
        hyprctl dispatch "hl.dsp.focus({ window = \"address:$addr\" })" >/dev/null
        exit 0
    fi
fi

if [ "${SETTINGS_UI:-app}" != "rofi" ] && [ -f "$CFG/settings-app/settings_app.py" ] \
   && python3 -c 'import gi; gi.require_version("Adw", "1")' 2>/dev/null; then
    exec python3 -I "$CFG/settings-app/settings_app.py" "$@"
fi
exec "$SCRIPTS/menus/settings.sh" "$@"
