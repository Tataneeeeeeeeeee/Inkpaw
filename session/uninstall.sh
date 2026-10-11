#!/usr/bin/env bash
# =============================================================================
#  session/uninstall.sh — remove the session entry added by install.sh
# =============================================================================
#  Run with: sudo ./session/uninstall.sh
#  Add --sddm-theme to also remove the "encre" login theme installed by
#  install.sh --sddm-theme (theme folder + /etc/sddm.conf.d entry); SDDM then
#  falls back to the theme it used before.
#  (~/.local/share/inkpaw/session-root can be deleted by hand.)
# =============================================================================
set -euo pipefail
SDDM_THEME=0
for a in "$@"; do
  case "$a" in
    --sddm-theme) SDDM_THEME=1 ;;
    *) echo "Unknown option: $a (only --sddm-theme)" >&2; exit 2 ;;
  esac
done
[ "$(id -u)" = 0 ] || { echo "Run with sudo: sudo $0 $*" >&2; exit 1; }
rm -fv /usr/share/wayland-sessions/inkpaw.desktop
# --- optional: SDDM theme "inkpaw-encre" ---------------------------------
if [ "$SDDM_THEME" = 1 ]; then
  rm -fv /etc/sddm.conf.d/zz-inkpaw-theme.conf
  rm -rf /usr/share/sddm/themes/inkpaw-encre && echo "removed the inkpaw-encre theme"
fi
