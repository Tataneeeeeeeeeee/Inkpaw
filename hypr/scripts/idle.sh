#!/usr/bin/env bash
# =============================================================================
#  idle.sh — hypridle with different timeouts on AC and on battery
# =============================================================================
#  Usage: idle.sh watch     render + (re)start hypridle whenever the power
#                           source changes (polls every 20 s, very cheap)
#         idle.sh render    print the rendered config for the current source
#  Template: hypr/idle/hypridle.conf.tpl — timeouts in settings.conf
#  (IDLE_AC_* / IDLE_BAT_*). Caffeine: Waybar's idle_inhibitor module.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

tpl="$HYPR_DIR/idle/hypridle.conf.tpl"
out="$CACHE/hypridle.conf"

# "ac" or "bat" (desktops without a battery are always "ac")
source_now() {
    local s
    for s in /sys/class/power_supply/*/; do
        [ "$(cat "$s/type" 2>/dev/null)" = "Mains" ] || continue
        [ "$(cat "$s/online" 2>/dev/null)" = "1" ] && { echo ac; return; }
        echo bat; return
    done
    echo ac
}

# Render the template; a timeout of 0 removes its listener block
render() {
    local p; p=$(echo "$1" | tr '[:lower:]' '[:upper:]')
    local dim lock dpms susp
    eval "dim=\${IDLE_${p}_DIM:-0} lock=\${IDLE_${p}_LOCK:-0} dpms=\${IDLE_${p}_DPMS:-0} susp=\${IDLE_${p}_SUSPEND:-0}"
    sed -e "s|@LOCK_CMD@|$SCRIPTS/lock.sh|g" \
        -e "s|@DIM@|$dim|; s|@LOCK@|$lock|; s|@DPMS@|$dpms|; s|@SUSPEND@|$susp|" "$tpl" |
    awk 'BEGIN{RS="";ORS="\n\n"} !/timeout = 0[^0-9]/'
}

case "${1:-watch}" in
    render) render "$(source_now)" ;;
    watch)
        last=""
        while true; do
            now=$(source_now)
            if [ "$now" != "$last" ]; then
                render "$now" >"$out"
                pkill -x hypridle; sleep 0.3
                setsid -f hypridle -c "$out" >/dev/null 2>&1
                last="$now"
            fi
            sleep 20
        done ;;
esac
