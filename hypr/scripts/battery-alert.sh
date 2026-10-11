#!/usr/bin/env bash
# =============================================================================
#  battery-alert.sh — low-battery notifications (laptop + mouse, headset…)
# =============================================================================
#  Started once by conf/autostart.lua ("battery-alert"). Every minute it reads
#  upower and sends ONE notification each time a level is crossed downwards:
#    laptop battery : BATTERY_ALERT_LEVELS   (settings.conf, e.g. "20 10 5")
#    other devices  : DEVICE_ALERT_LEVEL     (e.g. "15")
#  The lowest laptop level is "critical" (stays on screen). Plugging the
#  charger / charging the device re-arms the alerts.
#  Usage: battery-alert.sh watch | check
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

LEVELS="${BATTERY_ALERT_LEVELS:-20 10 5}"
DEV_LEVEL="${DEVICE_ALERT_LEVEL:-15}"
MEM="$CACHE/battery-alert"      # last level we warned about, per device
mkdir -p "$MEM"

check() {
    local path info pct state name kind key last lowest crossed l urg
    lowest=$(tr ' ' '\n' <<<"$LEVELS" | sort -n | head -1)
    while read -r path; do
        case "$path" in *line_power*|*DisplayDevice*) continue ;; esac
        info=$(upower -i "$path" 2>/dev/null)
        pct=$(awk '/percentage:/ { gsub(/[%,]/, "", $2); print int($2); exit }' <<<"$info")
        [ -z "$pct" ] && continue
        state=$(awk '/state:/ { print $2; exit }' <<<"$info")
        name=$(awk -F': +' '/model:/ { print $2; exit }' <<<"$info")
        kind=$(basename "$path" | cut -d_ -f1)
        key=$(basename "$path")
        last=$(cat "$MEM/$key" 2>/dev/null || echo 101)

        if [ "$state" = "charging" ] || [ "$state" = "fully-charged" ]; then
            echo 101 >"$MEM/$key"; continue                    # re-arm
        fi
        if [ "$kind" = "battery" ]; then
            crossed=""
            for l in $LEVELS; do
                if [ "$pct" -le "$l" ] && [ "$last" -gt "$l" ] && { [ -z "$crossed" ] || [ "$l" -lt "$crossed" ]; }; then
                    crossed=$l
                fi
            done
            if [ -n "$crossed" ]; then
                urg=normal; [ "$crossed" -le "$lowest" ] && urg=critical
                notify-send -a "Battery" -u "$urg" -i battery-caution-symbolic \
                    "Battery low: ${pct}%" "Plug in the charger soon." >/dev/null 2>&1
                echo "$crossed" >"$MEM/$key"
            fi
        elif [ "$pct" -le "$DEV_LEVEL" ] && [ "$last" -gt "$DEV_LEVEL" ]; then
            notify-send -a "Battery" -i battery-caution-symbolic \
                "${name:-$kind}: ${pct}%" "Its battery is almost empty." >/dev/null 2>&1
            echo "$DEV_LEVEL" >"$MEM/$key"
        fi
    done < <(upower -e 2>/dev/null)
}

case "${1:-watch}" in
    check) check ;;
    watch) while true; do check; sleep 60; done ;;
esac
