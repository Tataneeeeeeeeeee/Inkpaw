#!/usr/bin/env bash
# =============================================================================
#  menus/bluetooth.sh — rofi Bluetooth manager (bluetoothctl)
# =============================================================================
#  Power on/off, scan, connect / disconnect paired devices, pair new ones,
#  or open blueman for everything else.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/../lib.sh"

powered() { bluetoothctl show | grep -q "Powered: yes"; }
connected() { bluetoothctl info "$1" | grep -q "Connected: yes"; }

if ! powered; then
    choice=$(printf '%s\n' "󰂯  Turn Bluetooth on" "󰒓  Open Blueman" | rofi_menu "Bluetooth (off)")
    case "$choice" in
        *on*)     bluetoothctl power on >/dev/null && notify "Bluetooth" "on"; exec "$0" ;;
        *Blueman*) setsid -f "${BLUETOOTH_MANAGER:-blueman-manager}" >/dev/null 2>&1 ;;
    esac
    exit 0
fi

# "MAC|label" lines for every known device
devices=$(bluetoothctl devices | while read -r _ mac name; do
    if connected "$mac"; then echo "$mac|󰂱  $name  (connected)"; else echo "$mac|󰂯  $name"; fi
done)

choice=$( { printf '%s\n' "󰂲  Turn Bluetooth off" "󰂰  Scan for new devices (10 s)" "󰒓  Open Blueman";
            echo "$devices" | cut -d'|' -f2; } | sed '/^$/d' | rofi_menu "Bluetooth")
[ -z "$choice" ] && exit 0

case "$choice" in
    *"Turn Bluetooth off"*) bluetoothctl power off >/dev/null; notify "Bluetooth" "off" ;;
    *Scan*)
        notify "Bluetooth" "Scanning for 10 s…"
        bluetoothctl --timeout 10 scan on >/dev/null; exec "$0" ;;
    *Blueman*) setsid -f "${BLUETOOTH_MANAGER:-blueman-manager}" >/dev/null 2>&1 ;;
    *)
        mac=$(echo "$devices" | grep -F "|$choice" | head -1 | cut -d'|' -f1)
        [ -z "$mac" ] && exit 1
        if connected "$mac"; then
            bluetoothctl disconnect "$mac" >/dev/null && notify "Bluetooth" "Disconnected"
        else
            bluetoothctl info "$mac" | grep -q "Paired: yes" || bluetoothctl pair "$mac" >/dev/null
            bluetoothctl trust "$mac" >/dev/null
            if bluetoothctl connect "$mac" >/dev/null; then notify "Bluetooth" "Connected"
            else notify "Bluetooth" "Connection failed"; fi
        fi ;;
esac
