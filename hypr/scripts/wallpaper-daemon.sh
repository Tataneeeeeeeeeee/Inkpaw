#!/usr/bin/env bash
# =============================================================================
#  wallpaper-daemon.sh — start awww (or legacy swww) daemon
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

if have awww-daemon; then
    awww query >/dev/null 2>&1 || exec awww-daemon
elif have swww-daemon; then
    swww query >/dev/null 2>&1 || exec swww-daemon
else
    notify "Wallpaper" "Neither awww nor swww is installed"
fi
