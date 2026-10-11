#!/usr/bin/env bash
# =============================================================================
#  resident.sh — open / close / start a resident overlay menu (pylib/hyprapp.py)
# =============================================================================
#  Usage: resident.sh <name> [toggle|--daemon|--restart]
#    <name> = powermenu | keysheet | themepicker | wallpicker
#             (app = <project>/<name>/<name>.py, D-Bus id dev.inkpaw.<Id>)
#    toggle    (default) open it, or close it when open — a ~10 ms D-Bus call
#              when it is already running, else it is started and opened
#    --daemon  start it hidden (login), nothing shown — only with UI_SKIN=encre,
#              the skin that uses these menus
#    --restart stop it and start it hidden again (skin / theme change)
#    --stop    stop it
#  <name> = all: the same mode for the four menus.
#  Exit 3 = GTK 4 layer-shell missing (the caller falls back to rofi / wlogout).
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

name="${1:?usage: resident.sh <name> [toggle|--daemon|--restart|--stop]}"
mode="${2:-toggle}"
if [ "$name" = all ]; then
    for m in powermenu keysheet themepicker wallpicker; do "$0" "$m" "$mode"; done
    exit 0
fi
PROJECT="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
APP="$PROJECT/$name/$name.py"
case "$name" in
    powermenu)   id=PowerMenu ;;
    keysheet)    id=KeySheet ;;
    themepicker) id=ThemePicker ;;
    wallpicker)  id=WallPicker ;;
    *) echo "resident.sh: unknown menu '$name'" >&2; exit 2 ;;
esac
DEST="dev.inkpaw.$id"
OBJ="/dev/inkpaw/$id"

running() {
    gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
        --method org.freedesktop.DBus.NameHasOwner "$DEST" 2>/dev/null | grep -q true
}
usable() {
    [ -f "$APP" ] && python3 -c 'import gi; gi.require_version("Gtk", "4.0"); gi.require_version("Gtk4LayerShell", "1.0")' 2>/dev/null
}
start() {   # [arg]  (the app re-execs itself with gtk4-layer-shell preloaded)
    setsid -f python3 -I "$APP" "${1:---daemon}" >/dev/null 2>&1 </dev/null
}
stop() {
    local p i
    for p in $(pgrep -x python3); do
        tr '\0' ' ' 2>/dev/null <"/proc/$p/cmdline" | grep -q "$name/$name.py" && kill "$p"
    done
    # wait until the D-Bus name is free, else a new instance would just hand its
    # command line to the dying one and exit
    for i in $(seq 40); do running || return 0; sleep 0.05; done
}

case "$mode" in
    --daemon)  [ "${UI_SKIN:-default}" = encre ] || exit 0
               running && exit 0; usable || exit 3; start --daemon ;;
    --restart) stop
               [ "${UI_SKIN:-default}" = encre ] || exit 0
               usable || exit 3; start --daemon ;;
    --stop)    stop ;;
    toggle)
        if running; then
            exec gdbus call --session --dest "$DEST" --object-path "$OBJ" \
                --method org.gtk.Actions.Activate toggle "[]" "{}" >/dev/null
        fi
        usable || exit 3
        start toggle ;;                       # first time: start it, opened (then resident)
    *) echo "resident.sh: unknown mode '$mode'" >&2; exit 2 ;;
esac
