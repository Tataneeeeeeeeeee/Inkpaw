#!/usr/bin/env bash
# =============================================================================
#  toggle.sh — flip a boolean setting at runtime and persist it
# =============================================================================
#  Usage: toggle.sh ANIMATIONS | BLUR | SHADOW | GAMEMODE | GAPS
#  The value is saved in ~/.local/state/inkpaw/toggles.conf (overrides
#  settings.conf) and Hyprland is reloaded so every module re-reads it.
#  GAPS is special: it switches between your gaps and 0.
#  Skin "encre": GAMEMODE sends the game-mode toast of the mockup Mew-GameMode
#  (French text + the gamer cat, hyprtheme/skins/encre/cats/gamer.png) instead
#  of the plain "GAMEMODE turned on/off".
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

key="${1:?usage: toggle.sh KEY}"

if [ "$key" = "GAPS" ]; then
    if [ "${GAPS_OUT:-0}" != "0" ]; then
        state_set GAPS_IN 0; state_set GAPS_OUT 0; state="off"
    else
        sed -i '/^GAPS_IN=/d;/^GAPS_OUT=/d' "$TOGGLES"; state="on"
    fi
else
    default="true"; [ "$key" = "GAMEMODE" ] && default="false"
    if is_true "$key" "$default"; then state_set "$key" false; state="off"
    else state_set "$key" true; state="on"; fi
fi

hyprctl reload >/dev/null

if [ "$key" = "GAMEMODE" ] && [ "${UI_SKIN:-default}" = "encre" ] && have notify-send; then
    icon="$THEME_DIR/skins/encre/cats/gamer.png"   # body: no-break spaces keep the shortcut on one line
    if [ "$state" = "on" ]; then
        title="Mode jeu activé"
        body="Animations, flou, ombres, marges et coins arrondis coupés. Retour : SUPER + ALT + G"
    else
        title="Mode jeu désactivé"
        body="Animations, flou, ombres, marges et coins arrondis rétablis. Mode jeu : SUPER + ALT + G"
    fi
    notify-send -a "inkpaw" -i "$icon" "$title" "$body" >/dev/null 2>&1 &
else
    notify "$key" "turned $state"
fi
