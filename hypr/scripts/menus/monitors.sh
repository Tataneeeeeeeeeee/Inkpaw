#!/usr/bin/env bash
# =============================================================================
#  menus/monitors.sh — pick a monitor profile (hypr/monitors/*.lua)
# =============================================================================
#  The choice is persisted (MONITOR_PROFILE in toggles.conf) and Hyprland
#  is reloaded. New profile = new file in hypr/monitors/.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/../lib.sh"

current="${MONITOR_PROFILE:-auto}"
profiles=$(find "$HYPR_DIR/monitors" -name '*.lua' ! -name 'common.lua' -printf '%f\n' | sed 's/\.lua$//' | sort)

choice=$(echo "$profiles" | sed "s/^$current\$/$current  (active)/" | rofi_menu "Monitors")
choice="${choice%%  (active)}"
[ -z "$choice" ] && exit 0

state_set MONITOR_PROFILE "$choice"
hyprctl reload >/dev/null
notify "Monitors" "Profile: $choice"
