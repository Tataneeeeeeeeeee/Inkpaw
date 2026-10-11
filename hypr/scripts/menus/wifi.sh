#!/usr/bin/env bash
# =============================================================================
#  menus/wifi.sh — rofi Wi-Fi manager (NetworkManager / nmcli)
# =============================================================================
#  Lists networks (signal, security), connects (asks for a password when the
#  network is new), toggles the radio, and opens nmtui for anything advanced.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/../lib.sh"

radio=$(nmcli -t radio wifi)
current=$(nmcli -t -f active,ssid dev wifi 2>/dev/null | awk -F: '$1=="yes"{print $2; exit}')

header=()
if [ "$radio" = "enabled" ]; then
    header+=("󰖪  Turn Wi-Fi off")
    [ -n "$current" ] && header+=("󰅙  Disconnect from $current")
    header+=("󰑓  Rescan")
else
    header+=("󰖩  Turn Wi-Fi on")
fi
header+=("󰆍  Advanced (nmtui)" "󰒓  Connection editor")

networks=""
if [ "$radio" = "enabled" ]; then
    networks=$(nmcli -t -f in-use,signal,security,ssid dev wifi list --rescan no 2>/dev/null |
        awk -F: '$4 != "" && !seen[$4]++ {
            bars = ($2 >= 75) ? "󰤨" : ($2 >= 50) ? "󰤥" : ($2 >= 25) ? "󰤢" : "󰤟";
            lock = ($3 == "" || $3 == "--") ? "󰌿" : "󰌾";
            mark = ($1 == "*") ? "  (connected)" : "";
            printf "%s %s  %s%s\n", bars, lock, $4, mark }')
fi

choice=$( { printf '%s\n' "${header[@]}"; [ -n "$networks" ] && echo "$networks"; } |
          rofi_menu "Wi-Fi${current:+ · $current}")
[ -z "$choice" ] && exit 0

case "$choice" in
    *"Turn Wi-Fi off"*) nmcli radio wifi off; notify "Wi-Fi" "off" ;;
    *"Turn Wi-Fi on"*)  nmcli radio wifi on;  notify "Wi-Fi" "on" ;;
    *Disconnect*)       nmcli con down id "$current" && notify "Wi-Fi" "Disconnected" ;;
    *Rescan*)           nmcli dev wifi rescan; exec "$0" ;;
    *nmtui*)            float_term nmtui ;;
    *"Connection editor"*) setsid -f nm-connection-editor >/dev/null 2>&1 ;;
    *)
        ssid=$(echo "$choice" | sed -E 's/^[^ ]+ [^ ]+  //; s/  \(connected\)$//')
        if nmcli -t -f name con show | grep -Fxq "$ssid"; then
            nmcli con up id "$ssid" && notify "Wi-Fi" "Connected to $ssid"
        else
            pass=""
            if echo "$choice" | grep -q "󰌾"; then
                pass=$(rofi_menu "Password for $ssid" -password -lines 0 </dev/null)
                [ -z "$pass" ] && exit 0
            fi
            if nmcli dev wifi connect "$ssid" ${pass:+password "$pass"}; then
                notify "Wi-Fi" "Connected to $ssid"
            else
                notify "Wi-Fi" "Failed to connect to $ssid"
            fi
        fi ;;
esac
