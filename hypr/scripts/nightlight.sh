#!/usr/bin/env bash
# =============================================================================
#  nightlight.sh — toggle hyprsunset (warm screen)
# =============================================================================
#  Temperature: NIGHTLIGHT_TEMP env or 4500 K.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

if pgrep -x hyprsunset >/dev/null; then
    pkill -x hyprsunset && notify "Night light" "off"
else
    setsid -f hyprsunset -t "${NIGHTLIGHT_TEMP:-4500}" >/dev/null 2>&1
    notify "Night light" "on (${NIGHTLIGHT_TEMP:-4500} K)"
fi
