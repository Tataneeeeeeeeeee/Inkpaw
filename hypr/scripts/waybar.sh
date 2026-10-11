#!/usr/bin/env bash
# =============================================================================
#  waybar.sh — build + start / restart / reload / toggle Waybar
# =============================================================================
#  Usage: waybar.sh start|restart|reload|toggle|build
#  The config is GENERATED from the BAR_* settings by waybar/build.py into
#  ~/.cache/inkpaw/waybar/{config.json,style.css} before each (re)start.
#  reload = rebuild + SIGUSR2 (Waybar re-reads config and style in place).
#  toggle = SIGUSR1 (hide / show).
#  Waybar talks to Hyprland through waybar/ipc-proxy.py, which rewrites the
#  legacy "dispatch workspace N" sent by a click on a workspace number into
#  Lua (Hyprland 0.56 Lua configs reject the old syntax). If the relay cannot
#  start, Waybar uses the real socket (the numbers then just don't switch).
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

# Module commands use $XDG_CONFIG_HOME (on-click…): make sure it is set
export XDG_CONFIG_HOME="$CFG"

out="$CACHE/waybar"
conf="$out/config.json"
style="$out/style.css"

build() { python3 -I "$CFG/waybar/build.py" >/dev/null || { notify "Waybar" "config build failed (see waybar/build.py)"; return 1; }; }

# PID of *our* waybar (matched by config path, so a host bar is never touched)
our_pid() { pgrep -f "waybar -c $conf" ; }

# Start (or reuse) the IPC relay; prints the HYPRLAND_INSTANCE_SIGNATURE to use
ipc_proxy() {
    [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ] || return 1
    python3 -I "$CFG/waybar/ipc-proxy.py" "$CACHE/hipc" 2>>"$CACHE/waybar.log"
}

start() {
    our_pid >/dev/null && return 0
    build || return 1
    local his
    his="$(ipc_proxy)" || his="${HYPRLAND_INSTANCE_SIGNATURE:-}"
    HYPRLAND_INSTANCE_SIGNATURE="$his" setsid -f waybar -c "$conf" -s "$style" >"$CACHE/waybar.log" 2>&1
}

case "${1:-start}" in
    start)   start ;;
    restart) our_pid | xargs -r kill; sleep 0.4; start ;;
    reload)  build && our_pid | xargs -r kill -SIGUSR2 ;;
    toggle)  our_pid | xargs -r kill -SIGUSR1 ;;
    build)   build && echo "$conf" ;;
    *) echo "usage: $0 start|restart|reload|toggle|build" >&2; exit 1 ;;
esac
