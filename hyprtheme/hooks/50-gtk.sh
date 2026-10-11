#!/usr/bin/env bash
# =============================================================================
#  hooks/50-gtk.sh — tell GTK / libadwaita apps about light vs dark
# =============================================================================
#  Run by theme.sh after the templates are rendered. Delete / chmod -x to skip.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

# Writes your real dconf, so it is skipped inside the ./test.sh session.
is_test && exit 0
have gsettings || exit 0
mode=$(sed -n 's/.*mode *= *"\([a-z]*\)".*/\1/p' "$HYPR_DIR/themes/current.lua" | head -1)
if [ "$mode" = "light" ]; then
    gsettings set org.gnome.desktop.interface color-scheme prefer-light
else
    gsettings set org.gnome.desktop.interface color-scheme prefer-dark
fi
