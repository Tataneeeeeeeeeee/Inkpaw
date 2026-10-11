#!/usr/bin/env bash
# =============================================================================
#  radio.sh — state / toggle helpers for swaync quick-toggle buttons
# =============================================================================
#  Usage: radio.sh wifi|bluetooth state    -> prints true / false
#         radio.sh wifi|bluetooth set       -> applies $SWAYNC_TOGGLE_STATE
# =============================================================================
case "$1 $2" in
    "wifi state")      [ "$(nmcli -t radio wifi)" = "enabled" ] && echo true || echo false ;;
    "wifi set")        [ "$SWAYNC_TOGGLE_STATE" = "true" ] && nmcli radio wifi on || nmcli radio wifi off; : ;;
    "bluetooth state") bluetoothctl show | grep -q "Powered: yes" && echo true || echo false ;;
    "bluetooth set")   [ "$SWAYNC_TOGGLE_STATE" = "true" ] && bluetoothctl power on >/dev/null || bluetoothctl power off >/dev/null; : ;;
    *) echo "usage: $0 wifi|bluetooth state|set" >&2; exit 1 ;;
esac 2>/dev/null
