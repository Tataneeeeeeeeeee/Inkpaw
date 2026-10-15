#!/usr/bin/env bash
# =============================================================================
#  updates.sh — pending system updates: bar module + update terminal
# =============================================================================
#  Usage: updates.sh [check]   JSON for the Waybar module custom/updates
#         updates.sh run       open a floating terminal that runs the update
#         updates.sh upgrade   the update itself (what "run" starts in the terminal)
#         updates.sh refresh   forget the last check and ask the bar to check again
#
#  Counted: official repos with checkupdates (pacman-contrib: a copy of the
#  sync database, so the system's own database is never touched), the AUR
#  through yay / paru, and Flatpak apps when flatpak is installed.
#  The result is cached a minute: with the bar on several monitors, every
#  Waybar runs the check at the same time — only the first one really does.
#  Settings: UPDATES_SHOW_ZERO (show the icon when up to date),
#            UPDATES_INTERVAL (minutes between checks, read by waybar/build.py).
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

cache="$CACHE/updates.json"
SIGNAL=8                          # "signal" of custom/updates (waybar/modules/updates.jsonc)

aur_helper() { for h in yay paru; do have "$h" && { echo "$h"; return; }; done; }

# Ask our Waybar (matched by its config path) to run the check again
poke_bar() { pkill -RTMIN+$SIGNAL -f "waybar -c $CACHE/waybar/config.json" 2>/dev/null || true; }

json_escape() { python3 -Ic 'import json, sys; print(json.dumps(sys.stdin.read().rstrip("\n")))'; }

# One "name old -> new" line per update, prefixed with its source
list_updates() {
    local helper; helper="$(aur_helper)"
    if have checkupdates; then
        timeout 60 checkupdates 2>/dev/null
        # 0 = updates, 2 = none, anything else = no network / mirror down
        case $? in 0|2) ;; *) return 1 ;; esac
    else
        pacman -Qu 2>/dev/null       # stale database, but needs no root
    fi
    [ -n "$helper" ] && timeout 60 "$helper" -Qua 2>/dev/null | sed 's/^/aur  /'
    have flatpak && timeout 60 flatpak remote-ls --updates --columns=application 2>/dev/null | sed 's/^/flatpak  /'
    return 0
}

check() {
    local list n class text tooltip
    if ! list="$(list_updates)"; then
        # Offline: keep the last result rather than flashing "up to date"
        [ -s "$cache" ] && { cat "$cache"; return; }
        printf '{"text": "", "class": "error", "tooltip": "Could not check for updates"}\n'
        return
    fi
    n=$(printf '%s' "$list" | grep -c .)
    if [ "$n" -eq 0 ]; then
        class="none"; tooltip="System up to date"
        text=""; is_true UPDATES_SHOW_ZERO false && text="󰗠"
    else
        class="pending"; [ "$n" -ge 50 ] && class="many"
        text="󰏗  $n"
        tooltip="$n update(s) — click to install, right click to check again"$'\n\n'"$(printf '%s\n' "$list" | head -20)"
        [ "$n" -gt 20 ] && tooltip+=$'\n'"… and $((n - 20)) more"
    fi
    printf '{"text": "%s", "alt": "%s", "class": "%s", "tooltip": %s}\n' \
        "$text" "$class" "$class" "$(printf '%s' "$tooltip" | json_escape)"
}

# Cached check (one per minute), serialized between the bars of every monitor
cached_check() {
    exec 9>"$CACHE/updates.lock"
    flock 9
    if [ -s "$cache" ] && [ -z "$(find "$cache" -mmin +1 2>/dev/null)" ]; then
        cat "$cache"
    else
        check | tee "$cache.tmp" && mv -f "$cache.tmp" "$cache"
    fi
}

upgrade() {
    local helper; helper="$(aur_helper)"
    printf '\n  \e[1mSystem update\e[0m\n\n'
    if [ -n "$helper" ]; then
        printf '  → %s -Syu (official repos + AUR)\n\n' "$helper"
        "$helper" -Syu
    else
        printf '  → sudo pacman -Syu\n\n'
        sudo pacman -Syu
    fi
    if have flatpak; then
        printf '\n  → flatpak update\n\n'
        flatpak update
    fi
    rm -f "$cache"
    poke_bar
    printf '\n  Done. Press Enter to close.'
    read -r _
}

case "${1:-check}" in
    check)   cached_check ;;
    run)     float_term "$SCRIPTS/updates.sh" upgrade ;;
    upgrade) upgrade ;;
    refresh) rm -f "$cache"; poke_bar ;;
    *) echo "usage: $0 check|run|upgrade|refresh" >&2; exit 1 ;;
esac
