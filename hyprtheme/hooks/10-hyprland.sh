#!/usr/bin/env bash
# =============================================================================
#  hooks/10-hyprland.sh — reload Hyprland (border colors from hypr/themes/current.lua)
# =============================================================================
#  Run by theme.sh after the templates are rendered. Delete / chmod -x to skip.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ] && hyprctl reload >/dev/null
