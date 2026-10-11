#!/usr/bin/env bash
# =============================================================================
#  scripts/rofi-theme.sh — pick the rofi theme of the active skin (UI_SKIN)
# =============================================================================
#  Sourced (by lib.sh's rofi_menu, the wallpaper / theme pickers…) it defines:
#    rofi_theme <name>   -> rofi/skins/$UI_SKIN/<name>.rasi if it exists,
#                           else rofi/themes/<name>.rasi, else rofi/themes/menu.rasi
#    rofi_skinned <name> -> true when the active skin has its own <name>.rasi
#    rofi_token <name> [fallback]
#                        -> a value of rofi/skins/$UI_SKIN/tokens.rasi (generated
#                           by hyprtheme/templates/rofi-<skin>.rasi), e.g.
#                           `rofi_token ink '#2a2420'` -> "#2a2420"
#  Run directly: rofi-theme.sh <name> prints the path (sources lib.sh first).
#  Needs $CFG and $UI_SKIN (both set by lib.sh).
# =============================================================================

rofi_skinned() {
    [ -f "${CFG:-$HOME/.config}/rofi/skins/${UI_SKIN:-default}/$1.rasi" ]
}

rofi_theme() {
    local name="${1:-menu}" root="${CFG:-$HOME/.config}/rofi"
    if   [ -f "$root/skins/${UI_SKIN:-default}/$name.rasi" ]; then echo "$root/skins/${UI_SKIN:-default}/$name.rasi"
    elif [ -f "$root/themes/$name.rasi" ]; then echo "$root/themes/$name.rasi"
    else echo "$root/themes/menu.rasi"; fi
}

rofi_token() {
    local f="${CFG:-$HOME/.config}/rofi/skins/${UI_SKIN:-default}/tokens.rasi" v=""
    [ -f "$f" ] && v=$(sed -n "s/^[[:space:]]*$1:[[:space:]]*\([^;]*\);.*/\1/p" "$f" | head -1)
    v="${v//\"/}"
    echo "${v:-$2}"
}

# Executed (not sourced): print the theme path
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    . "$(dirname "$(readlink -f "$0")")/lib.sh"
    rofi_theme "${1:-menu}"
fi
