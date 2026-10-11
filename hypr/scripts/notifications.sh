#!/usr/bin/env bash
# =============================================================================
#  notifications.sh — start / restart swaync with THIS config (explicit paths)
# =============================================================================
#  Usage: notifications.sh start|restart|reload   (reload = new theme CSS, or a
#         fresh start when another daemon such as mako took the notifications)
#  swaync is also D-Bus-activatable; started that way it would read the default
#  ~/.config/swaync. Starting it here with -c/-s guarantees our config.
#  Skins: when UI_SKIN is not "default" and swaync/skins/$UI_SKIN.css exists
#  (rendered by hyprtheme from templates/swaync-$UI_SKIN.css), it replaces
#  style.css. An optional swaync/skins/$UI_SKIN.json is a config OVERLAY merged
#  over config.json with jq (objects merge, arrays are replaced) into
#  ~/.cache/inkpaw/swaync-$UI_SKIN.json.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

# Pick config + style for the current skin -> $conf $style
pick() {
    conf="$CFG/swaync/config.json"; style="$CFG/swaync/style.css"
    local skin="${UI_SKIN:-default}"
    [ "$skin" = "default" ] && return 0
    [ -f "$CFG/swaync/skins/$skin.css" ] && style="$CFG/swaync/skins/$skin.css"
    if [ -f "$CFG/swaync/skins/$skin.json" ] && have jq; then
        jq -s '.[0] * .[1]' "$conf" "$CFG/swaync/skins/$skin.json" \
            >"$CACHE/swaync-$skin.json" 2>/dev/null && conf="$CACHE/swaync-$skin.json"
    fi
}

# true if the running swaync was started with our -s style
ours() {
    local pid
    for pid in $(pgrep -x swaync); do
        tr '\0' '\n' <"/proc/$pid/cmdline" 2>/dev/null | grep -qxF -- "$style" && return 0
    done
    return 1
}

# Does someone own swaync's bus name? (NameHasOwner never D-Bus-activates)
owned() {
    busctl --user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus \
        NameHasOwner s org.erikreider.swaync.cc 2>/dev/null | grep -q true
}

# PID owning the notification name org.freedesktop.Notifications (empty if none).
# Other daemons (mako, dunst, plasma) are D-Bus-activatable for that name too:
# a notification sent while swaync is down starts one of them, which then
# keeps the name — swaync can't get it ("Could not acquire notification name")
# and notifications stop following the theme.
notif_owner() {
    busctl --user call org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus \
        GetConnectionUnixProcessID s org.freedesktop.Notifications 2>/dev/null | awk '{print $2}'
}

# Stop whatever other daemon holds the notification name (by PID, never pkill -f)
free_name() {
    local pid i
    pid="$(notif_owner)"
    [ -n "$pid" ] || return 0
    [ "$(cat "/proc/$pid/comm" 2>/dev/null)" = "swaync" ] && return 0
    kill "$pid" 2>/dev/null
    for i in $(seq 20); do [ -d "/proc/$pid" ] || break; sleep 0.05; done
}

# true when our swaync runs AND is the one showing notifications
healthy() {
    pick
    local pid; pid="$(notif_owner)"
    ours && [ -n "$pid" ] && [ "$(cat "/proc/$pid/comm" 2>/dev/null)" = "swaync" ]
}

# swaync is D-Bus-activatable through systemd (swaync.service, no -c/-s): any
# swaync-client call (Waybar polls one) respawns it within milliseconds of a
# kill, with the default style. So while we swap instances, the unit is masked
# for this boot only (--runtime, under $XDG_RUNTIME_DIR) and unmasked right
# after (trap), then ours owns the name and no activation happens any more.
start() {
    healthy && return 0
    local i; MASKED=0
    if have systemctl && systemctl --user cat swaync.service >/dev/null 2>&1; then
        systemctl --user mask --runtime --quiet swaync.service 2>/dev/null && MASKED=1
        trap '[ "$MASKED" = 1 ] && systemctl --user unmask --runtime --quiet swaync.service' EXIT
        systemctl --user stop swaync.service 2>/dev/null
    fi
    pkill -x swaync
    for i in $(seq 20); do pgrep -x swaync >/dev/null || break; sleep 0.1; done
    # another daemon may grab the name again (D-Bus activation) between the
    # kill and swaync's start: retry a few times
    local try
    for try in 1 2 3; do
        free_name
        setsid -f swaync -c "$conf" -s "$style" >"$CACHE/swaync.log" 2>&1
        for i in $(seq 30); do healthy && return 0; sleep 0.1; done
        pkill -x swaync
    done
    healthy
}

case "${1:-start}" in
    start)   start ;;
    restart) pkill -x swaync; start ;;
    reload)  if healthy; then swaync-client -rs >/dev/null 2>&1; else start; fi ;;   # new theme CSS
    *) echo "usage: $0 start|restart|reload" >&2; exit 1 ;;
esac
