#!/usr/bin/env bash
# =============================================================================
#  menus/edit-config.sh — pick a config file and open it in EDITOR_GUI
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/../lib.sh"

# Files offered (relative to $CFG). Globs are expanded.
cd "$CFG" || exit 1
mapfile -t files < <(ls -1 \
    hypr/settings.conf hypr/settings.schema hypr/hyprland.lua hypr/conf/*.lua hypr/conf/keybinds/*.lua \
    hypr/monitors/*.lua hypr/hyprlock.conf hypr/idle/hypridle.conf.tpl \
    waybar/catalog.tsv waybar/modules/*.jsonc waybar/style/*.css waybar/style/presets/*.css waybar/style/modules/*.css \
    spotlight/config.toml spotlight/style.css \
    walker/config.toml elephant/*.toml swaync/config.json wlogout/layout \
    hyprtheme/static/*.json hyprtheme/templates/* 2>/dev/null)

choice=$(printf '%s\n' "${files[@]}" | rofi_menu "Edit")
[ -n "$choice" ] && setsid -f ${EDITOR_GUI:-xdg-open} "$CFG/$choice" >/dev/null 2>&1
