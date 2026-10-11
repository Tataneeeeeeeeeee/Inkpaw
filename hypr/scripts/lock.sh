#!/usr/bin/env bash
# =============================================================================
#  lock.sh — lock the session with hyprlock (single instance)
# =============================================================================
#  Default skin: hyprlock.conf + the generated hyprlock-colors.conf are merged
#  into one file in the cache, so no path inside hyprlock.conf depends on
#  where the config is installed.
#  UI_SKIN=encre: the self-contained hypr/skins/hyprlock-encre.conf (GENERATED
#  by hyprtheme from templates/hyprlock-encre.conf) is used as is; if it has
#  not been generated yet, the default lock screen is used.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

pidof hyprlock >/dev/null && exit 0

skinned="$HYPR_DIR/skins/hyprlock-${UI_SKIN:-default}.conf"
if [ "${UI_SKIN:-default}" != "default" ] && [ -f "$skinned" ]; then
    exec hyprlock -c "$skinned"
fi

conf="$CACHE/hyprlock.conf"
{
    cat "$HYPR_DIR/hyprlock-colors.conf" 2>/dev/null
    grep -v '^source *=' "$HYPR_DIR/hyprlock.conf"
} >"$conf"

exec hyprlock -c "$conf"
