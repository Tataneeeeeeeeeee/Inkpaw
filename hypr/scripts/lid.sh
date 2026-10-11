#!/usr/bin/env bash
# =============================================================================
#  lid.sh — react to the laptop lid (bound in conf/keybinds/switches.lua)
# =============================================================================
#  close: if an external screen is connected, disable the laptop panel;
#         otherwise do nothing (logind / hypridle handle suspend & lock).
#  open:  reload Hyprland so the saved monitor profile is re-applied.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

laptop="${MONITOR_LAPTOP:-eDP-1}"

case "$1" in
    close)
        others=$(hyprctl monitors -j | jq --arg l "$laptop" '[.[] | select(.name != $l)] | length')
        if [ "${others:-0}" -gt 0 ]; then
            hyprctl eval "hl.monitor({ output = \"$laptop\", disabled = true })" >/dev/null
        fi ;;
    open)
        hyprctl reload >/dev/null ;;
esac
