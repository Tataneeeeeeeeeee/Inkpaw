#!/usr/bin/env bash
# =============================================================================
#  deskpet.sh — the cat peeking from the bottom of the screen (deskpet/)
# =============================================================================
#  Usage: deskpet.sh start     show it if DESKTOP_PET=true (else make sure it is gone)
#         deskpet.sh stop      remove it
#         deskpet.sh restart   re-read the settings (cat, on/off) and start again
#         deskpet.sh toggle    show / hide it now, whatever DESKTOP_PET says
#         deskpet.sh status    "running <pid>" or "stopped"
#  Called at login (conf/autostart.lua), by skin.sh after a skin change and by
#  the settings (apply "pet"). Single instance: pid file ~/.cache/inkpaw/
#  deskpet.pid, checked against /proc (never pkill -f).
#  The app is found next to this script's real location (project/deskpet/),
#  so it works even before the session root links the deskpet/ folder.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

PROJECT="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
APP="$PROJECT/deskpet/deskpet.py"
[ -f "$APP" ] || APP="$CFG/deskpet/deskpet.py"
PIDFILE="$CACHE/deskpet.pid"
LOCK="$CACHE/deskpet.lock"

running_pid() {   # prints the pid of our live instance, if any
    local pid
    pid=$(cat "$PIDFILE" 2>/dev/null) || return 1
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    tr '\0' ' ' 2>/dev/null <"/proc/$pid/cmdline" | grep -q "deskpet/deskpet.py" || return 1
    echo "$pid"
}

do_start() {
    running_pid >/dev/null && return 0
    [ -f "$APP" ] || { echo "deskpet: $APP not found" >&2; return 1; }
    if ! python3 -c 'import gi, cairo; gi.require_version("Gtk", "4.0"); gi.require_version("Gtk4LayerShell", "1.0")' 2>/dev/null; then
        notify "Desktop cat" "needs GTK 4 layer-shell (gtk4-layer-shell, python-gobject, python-cairo)"
        return 1
    fi
    # the app re-execs itself with LD_PRELOAD (same pid) and clears it afterwards
    setsid python3 -I "$APP" >/dev/null 2>&1 </dev/null 9>&- &
    echo $! >"$PIDFILE"
}

do_stop() {
    local pid i
    pid=$(running_pid) || { rm -f "$PIDFILE"; return 0; }
    kill "$pid" 2>/dev/null
    for i in $(seq 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.05; done
    rm -f "$PIDFILE"
}

# one deskpet.sh at a time (login + skin change may race)
exec 9>"$LOCK"
flock -w 5 9 || exit 1

case "${1:-start}" in
    start)   if is_true DESKTOP_PET false; then do_start; else do_stop; fi ;;
    stop)    do_stop ;;
    restart) do_stop; is_true DESKTOP_PET false && do_start ;;
    toggle)  if running_pid >/dev/null; then do_stop; else do_start; fi ;;
    status)  if pid=$(running_pid); then echo "running $pid"; else echo "stopped"; fi ;;
    *)       echo "usage: deskpet.sh start|stop|restart|toggle|status" >&2; exit 2 ;;
esac
exit 0
