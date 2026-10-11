#!/usr/bin/env bash
# =============================================================================
#  hooks/20-waybar.sh — rebuild + reload Waybar with the new colors
# =============================================================================
#  Run by theme.sh after the templates are rendered. Delete / chmod -x to skip.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

"$SCRIPTS/waybar.sh" reload
