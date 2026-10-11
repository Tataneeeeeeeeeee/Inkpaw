#!/usr/bin/env bash
# =============================================================================
#  scripts/lib.sh — shared helpers, sourced by every script
# =============================================================================
#  Provides:
#    $CFG        config root ($XDG_CONFIG_HOME or ~/.config)
#    $HYPR_DIR   $CFG/hypr          $SCRIPTS  $CFG/hypr/scripts
#    $THEME_DIR  $CFG/hyprtheme     $STATE    ~/.local/state/inkpaw
#    $CACHE      ~/.cache/inkpaw
#    every KEY from hypr/settings.conf (+ runtime toggles)
#    have <cmd>               -> true if the command exists
#    notify <title> [body]    -> desktop notification (silent if unavailable)
#    state_set KEY VALUE      -> persist a runtime toggle (overrides settings.conf)
#    rofi_menu <prompt> [..]  -> themed rofi dmenu (skin-aware, see rofi-theme.sh), stdin entries
#    is_test                  -> true inside the ./test.sh nested session
# =============================================================================

CFG="${XDG_CONFIG_HOME:-$HOME/.config}"
HYPR_DIR="$CFG/hypr"
SCRIPTS="$HYPR_DIR/scripts"
THEME_DIR="$CFG/hyprtheme"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/inkpaw"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/inkpaw"
TOGGLES="$STATE/toggles.conf"
mkdir -p "$STATE" "$CACHE"

# shellcheck disable=SC1091
[ -f "$HYPR_DIR/settings.conf" ] && . "$HYPR_DIR/settings.conf"
# shellcheck disable=SC1090
[ -f "$TOGGLES" ] && . "$TOGGLES"

# Bundled fonts (hyprtheme/fonts) for every app a script starts — Hyprland
# exports the same FONTCONFIG_FILE for what it launches itself (conf/env.lua)
[ -f "$THEME_DIR/fonts/fonts.conf" ] && export FONTCONFIG_FILE="$THEME_DIR/fonts/fonts.conf"

have() { command -v "$1" >/dev/null 2>&1; }

is_test() { [ -n "${INKPAW_TEST:-}" ]; }

notify() {
    have notify-send || return 0
    notify-send -a "inkpaw" -i "$THEME_DIR/skins/encre/logo/inkpaw-mark-128.png" "$1" "${2:-}" >/dev/null 2>&1 &
}

# Persist KEY=VALUE into the toggles file (replaces an existing key)
state_set() {
    local key="$1" val="$2"
    touch "$TOGGLES"
    sed -i "/^${key}=/d" "$TOGGLES"
    printf '%s="%s"\n' "$key" "$val" >>"$TOGGLES"
}

# Read a bool KEY (settings + toggles already sourced); default $2
is_true() {
    local v="${!1:-$2}"
    [[ "$v" == "true" || "$v" == "1" || "$v" == "yes" || "$v" == "on" ]]
}

# Themed rofi dmenu. Usage: printf 'a\nb' | rofi_menu "Prompt" [extra rofi args]
# Theme: ROFI_THEME (default "menu"), skinned version first (rofi-theme.sh):
# rofi/skins/$UI_SKIN/<name>.rasi, else rofi/themes/<name>.rasi
rofi_menu() {
    local prompt="$1" theme="$CFG/rofi/themes/menu.rasi" t=""; shift
    declare -F rofi_theme >/dev/null || . "$SCRIPTS/rofi-theme.sh" 2>/dev/null
    t=$(rofi_theme "${ROFI_THEME:-menu}" 2>/dev/null); [ -f "$t" ] && theme="$t"
    rofi -dmenu -i -p "$prompt" -theme "$theme" "$@"
}

# Run a command in a floating terminal (window rule: class floating-tui)
float_term() {
    # shellcheck disable=SC2086
    setsid -f ${TERMINAL_FLOAT:-kitty --class floating-tui -e} "$@" >/dev/null 2>&1
}
