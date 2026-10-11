#!/usr/bin/env bash
# =============================================================================
#  quickpanel.sh — open the Wi-Fi / Bluetooth panel (quickpanel/quickpanel.py)
# =============================================================================
#  Usage: quickpanel.sh wifi|bluetooth|sound|brightness|battery|notifications|calendar|media
#         quickpanel.sh --daemon    start the resident panel (login), no window
#         quickpanel.sh --restart   restart it (theme / skin changed: new colors)
#  Same tab again = close, other tab = switch. Falls back to the rofi menus
#  when GTK 4 layer-shell / libadwaita are not available.
#  The panel opens under the bar (or above it with BAR_POSITION=bottom): on the
#  RIGHT for every section, on the LEFT for the calendar (under the clock).
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

tab="${1:-wifi}"
APP_ID="dev.inkpaw.QuickPanel"
APP="$(readlink -f "$CFG/quickpanel/quickpanel.py")"

# the panel is resident (started at login with --daemon): talk to it over D-Bus,
# a ~10 ms call, instead of starting Python + GTK each time
running() {
    gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
        --method org.freedesktop.DBus.NameHasOwner "$APP_ID" 2>/dev/null | grep -q true
}
geometry() {
    # bar height (~41 px) + its margin + a gap; distance from the screen side
    local off=$(( ${BAR_HEIGHT:-0} > 0 ? ${BAR_HEIGHT:-0} + ${BAR_MARGIN:-6} + 36 : 41 + ${BAR_MARGIN:-6} + 36 ))
    echo "${BAR_POSITION:-top} $off $(( ${BAR_MARGIN:-6} + 4 ))"
}
start_daemon() {   # [tab]
    export TERMINAL_FLOAT NIGHTLIGHT_TEMP="${NIGHTLIGHT_TEMP:-4500}"
    read -r QUICKPANEL_EDGE QUICKPANEL_OFFSET QUICKPANEL_SIDE < <(geometry)
    export QUICKPANEL_EDGE QUICKPANEL_OFFSET QUICKPANEL_SIDE
    setsid -f python3 -I "$APP" "${1:---daemon}" >/dev/null 2>&1 </dev/null
}
stop_daemon() {
    local p
    for p in $(pgrep -x python3); do
        tr '\0' ' ' 2>/dev/null <"/proc/$p/cmdline" | grep -q 'quickpanel/quickpanel.py' && kill "$p"
    done
}

case "$tab" in
    --daemon)  running || start_daemon; exit 0 ;;
    --restart) stop_daemon; for i in $(seq 40); do running || break; sleep 0.05; done
               start_daemon; exit 0 ;;   # after a theme / skin change
esac

if running; then
    exec gdbus call --session --dest "$APP_ID" --object-path /dev/inkpaw/QuickPanel \
        --method org.gtk.Actions.Activate show "[<'$tab $(geometry)'>]" "{}" >/dev/null
fi
if [ -f "$APP" ] && python3 -c 'import gi; gi.require_version("Adw", "1"); gi.require_version("Gtk4LayerShell", "1.0")' 2>/dev/null; then
    start_daemon "$tab"          # first opening: start it (it then stays resident)
    exit 0
fi
case "$tab" in
    sound)      exec "${AUDIO_MIXER:-pavucontrol}" ;;
    notifications) exec swaync-client -t -sw ;;
    media)         exec playerctl play-pause ;;
    calendar)      exit 0 ;;
    brightness|battery) notify "Panel" "needs GTK 4 layer-shell + libadwaita (python-gobject)"; exit 1 ;;
    bluetooth) exec "$SCRIPTS/menus/bluetooth.sh" ;;
    *)         exec "$SCRIPTS/menus/wifi.sh" ;;
esac
