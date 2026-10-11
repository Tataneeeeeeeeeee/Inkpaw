#!/usr/bin/env bash
# =============================================================================
#  menus/power.sh — power menu (wlogout, themed). Falls back to rofi.
# =============================================================================
#  UI_SKIN=encre: powermenu/powermenu.py (GTK 4 layer-shell: title, hint, key
#  chips, one selection shared by keyboard and mouse — mockup Mew-Power);
#  when GTK 4 layer-shell is missing, wlogout/skins/encre/layout (plain JSON — wlogout rejects
#  comments; same actions/keybinds as wlogout/layout, French labels, key hint
#  after "·") + wlogout/skins/encre/style.css (GENERATED from
#  hyprtheme/templates/wlogout-encre.css): five 200x260 cat cards in one row,
#  the margins are computed from the focused monitor so the cards keep that
#  size on any screen. Other skins: wlogout/layout + wlogout/style.css.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/../lib.sh"

pgrep -x wlogout >/dev/null && { pkill -x wlogout; exit 0; }

# encre: our own menu (resident, opened / closed instantly over D-Bus);
# exit 3 = GTK 4 layer-shell missing -> wlogout below
if [ "${UI_SKIN:-default}" = "encre" ]; then
    "$SCRIPTS/resident.sh" powermenu && exit 0
fi

# Margins (-T -B -L -R) that leave a centered 5-card row of cell W x H px
encre_margins() {
    local w=232 h=300 mw mh   # card 200x260 + 3 px borders + CSS margins (13 px sides, 26+8 px)
    read -r mw mh < <(hyprctl monitors -j 2>/dev/null |
        jq -r '[.[] | select(.focused)][0] // .[0] | "\((.width / .scale | floor)) \((.height / .scale | floor))"' 2>/dev/null)
    [[ "$mw" =~ ^[0-9]+$ && "$mh" =~ ^[0-9]+$ ]] || { mw=1920; mh=1080; }
    local lr=$(( (mw - 5 * w) / 2 )) tb=$(( (mh - h) / 2 ))
    (( lr < 0 )) && lr=0; (( tb < 0 )) && tb=0
    echo "-T $tb -B $tb -L $lr -R $lr"
}

skin_dir="$CFG/wlogout/skins/${UI_SKIN:-default}"
if have wlogout && [ "${UI_SKIN:-default}" != "default" ] && [ -f "$skin_dir/layout" ] && [ -f "$skin_dir/style.css" ]; then
    # shellcheck disable=SC2046
    exec wlogout -l "$skin_dir/layout" -C "$skin_dir/style.css" -b 5 $(encre_margins) -c 0 -r 0 -p layer-shell
fi

if have wlogout; then
    exec wlogout -l "$CFG/wlogout/layout" -C "$CFG/wlogout/style.css" -b 5 -T 380 -B 380 -c 0 -r 0 -p layer-shell
fi

choice=$(printf '%s\n' "󰌾  Lock" "󰍃  Logout" "󰒲  Suspend" "󰜉  Reboot" "󰐥  Shutdown" | rofi_menu "Power")
case "$choice" in
    *Lock*)     "$SCRIPTS/lock.sh" ;;
    *Logout*)   hyprctl dispatch 'hl.dsp.exit()' ;;
    *Suspend*)  systemctl suspend ;;
    *Reboot*)   systemctl reboot ;;
    *Shutdown*) systemctl poweroff ;;
esac
