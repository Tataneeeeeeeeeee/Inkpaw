#!/usr/bin/env bash
# =============================================================================
#  osd.sh — volume / brightness with an on-screen display
# =============================================================================
#  Usage: osd.sh volume up|down|mute   osd.sh mic mute   osd.sh brightness up|down
#         osd.sh server [restart]   (autostart + theme hook: start swayosd-server)
#  Uses swayosd-client when installed (themed popup), otherwise plain
#  wpctl / brightnessctl. STEP: 5 %.
#  server: swayosd-server with swayosd/config.toml and swayosd/style.css, or
#  swayosd/skins/$UI_SKIN.css (rendered by hyprtheme from
#  templates/swayosd-$UI_SKIN.css) when UI_SKIN is not "default".
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

STEP=5
osd() { have swayosd-client && pgrep -x swayosd-server >/dev/null; }

server() {
    have swayosd-server || return 0
    if [ "${1:-}" = "restart" ]; then
        pkill -x swayosd-server
        local i; for i in $(seq 20); do pgrep -x swayosd-server >/dev/null || break; sleep 0.1; done
    fi
    pgrep -x swayosd-server >/dev/null && return 0
    local style="$CFG/swayosd/style.css" skin="${UI_SKIN:-default}"
    [ "$skin" != "default" ] && [ -f "$CFG/swayosd/skins/$skin.css" ] && style="$CFG/swayosd/skins/$skin.css"
    setsid -f swayosd-server --config "$CFG/swayosd/config.toml" -s "$style" >/dev/null 2>&1
}

[ "${1:-}" = "server" ] && { server "${2:-}"; exit 0; }

case "$1 $2" in
    "volume up")
        osd && exec swayosd-client --output-volume "+$STEP" --max-volume 100
        wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ "$STEP%+" ;;
    "volume down")
        osd && exec swayosd-client --output-volume "-$STEP"
        wpctl set-volume @DEFAULT_AUDIO_SINK@ "$STEP%-" ;;
    "volume mute")
        osd && exec swayosd-client --output-volume mute-toggle
        wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle ;;
    "mic mute")
        osd && exec swayosd-client --input-volume mute-toggle
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle ;;
    "brightness up")
        osd && exec swayosd-client --brightness "+$STEP"
        brightnessctl -e4 -n2 set "$STEP%+" ;;
    "brightness down")
        osd && exec swayosd-client --brightness "-$STEP"
        brightnessctl -e4 -n2 set "$STEP%-" ;;
    *) echo "usage: $0 volume up|down|mute | mic mute | brightness up|down | server [restart]" >&2; exit 1 ;;
esac
