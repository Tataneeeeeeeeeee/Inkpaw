#!/usr/bin/env bash
# =============================================================================
#  hyprtheme/skin.sh — switch the whole interface style ("skin")
# =============================================================================
#  Usage:
#    skin.sh apply <name>    apply hyprtheme/skins/<name>/skin.conf
#    skin.sh apply default   back to the toggles + theme you had before
#    skin.sh current         print the active skin
#    skin.sh list            list the skins (name<TAB>description)
#
#  A skin = a bundle of settings (fonts, app panels, bar preset…) written
#  to the runtime toggles, plus optionally a static theme (THEME= in
#  skin.conf; "encre" has none: it keeps your colors). Each
#  component then reads UI_SKIN to load its own skinned style file
#  (e.g. swaync/skins/encre.css). Applying a skin from "default" first saves
#  toggles.conf + theme.conf in ~/.local/state/inkpaw/skin-backup/.
#
#  Env: SKIN_NO_RELOAD=1  write the settings only, restart nothing (tests)
# =============================================================================
set -uo pipefail
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

SKINS="$THEME_DIR/skins"
BACKUP="$STATE/skin-backup"

die() { echo "skin.sh: $*" >&2; notify "Skin" "$*"; exit 1; }

# KEY="VALUE" lines of a skin.conf (comments and THEME= left out)
skin_keys() { grep -E '^[A-Z_][A-Z0-9_]*=' "$1" | grep -v '^THEME='; }

reload_all() {
    [ "${SKIN_NO_RELOAD:-0}" = "1" ] && return 0
    hyprctl reload >/dev/null 2>&1
    "$SCRIPTS/waybar.sh" restart >/dev/null 2>&1
    "$SCRIPTS/notifications.sh" restart >/dev/null 2>&1
    "$SCRIPTS/apps-config.sh" KITTY_FONT >/dev/null 2>&1
    "$SCRIPTS/quickpanel.sh" --restart >/dev/null 2>&1          # resident panel: new skin CSS
    "$SCRIPTS/resident.sh" all --restart >/dev/null 2>&1         # encre menus (stopped on other skins)
    [ -x "$SCRIPTS/deskpet.sh" ] && "$SCRIPTS/deskpet.sh" restart >/dev/null 2>&1
    return 0
}

apply_skin() {
    local name="$1" conf="$SKINS/$1/skin.conf" theme line key val
    [ -f "$conf" ] || die "unknown skin '$name'"
    # Save what you had, only when leaving the default look (re-applying a
    # skin must not overwrite the backup with skinned values)
    if [ "${UI_SKIN:-default}" = "default" ]; then
        mkdir -p "$BACKUP"
        cp -f "$TOGGLES" "$BACKUP/toggles.conf" 2>/dev/null || : >"$BACKUP/toggles.conf"
        cp -f "$STATE/theme.conf" "$BACKUP/theme.conf" 2>/dev/null || true
    fi
    while IFS= read -r line; do
        key="${line%%=*}"; val="${line#*=}"; val="${val%\"}"; val="${val#\"}"
        state_set "$key" "$val"
    done < <(skin_keys "$conf")
    theme=$(sed -n 's/^THEME="\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' "$conf" | head -1)
    # Re-read the toggles so the theme engine sees the new fonts / radius
    # shellcheck disable=SC1090
    . "$TOGGLES"
    if [ -n "$theme" ]; then
        local opt=(); [ "${SKIN_NO_RELOAD:-0}" = "1" ] && opt=(env THEME_NO_RELOAD=1 THEME_NO_WALLPAPER=1)
        "${opt[@]}" "$THEME_DIR/theme.sh" static "$theme" >/dev/null 2>&1
    fi
    reload_all
    notify "Skin" "$name applied (back: skin.sh apply default)"
}

restore_default() {
    if [ -f "$BACKUP/toggles.conf" ]; then
        cp -f "$BACKUP/toggles.conf" "$TOGGLES"
        [ -f "$BACKUP/theme.conf" ] && cp -f "$BACKUP/theme.conf" "$STATE/theme.conf"
        rm -rf "$BACKUP"
    else
        # No backup: drop every key any skin sets
        local conf key
        for conf in "$SKINS"/*/skin.conf; do
            [ -f "$conf" ] || continue
            for key in $(skin_keys "$conf" | cut -d= -f1); do sed -i "/^${key}=/d" "$TOGGLES" 2>/dev/null; done
        done
    fi
    state_set UI_SKIN default
    if [ "${SKIN_NO_RELOAD:-0}" != "1" ]; then
        "$THEME_DIR/theme.sh" restore >/dev/null 2>&1
    fi
    reload_all
    notify "Skin" "default style restored"
}

case "${1:-}" in
    apply)
        case "${2:?skin name required}" in
            default) restore_default ;;
            *)       apply_skin "$2" ;;
        esac ;;
    current) echo "${UI_SKIN:-default}" ;;
    list)
        printf 'default\tthe default look (your settings)\n'
        for d in "$SKINS"/*/; do
            [ -f "$d/skin.conf" ] || continue
            printf '%s\t%s\n' "$(basename "$d")" "$(sed -n '2s/^#  [^—]*— *//p' "$d/skin.conf")"
        done ;;
    *) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
