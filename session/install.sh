#!/usr/bin/env bash
# =============================================================================
#  session/install.sh — add the "Hyprland — Inkpaw" session to the login menu
# =============================================================================
#  Run with:  sudo ./session/install.sh
#  Installs /usr/share/wayland-sessions/inkpaw.desktop ("Hyprland — Inkpaw"),
#  which runs session/start.sh from THIS folder. Your usual Hyprland session
#  (the package's hyprland.desktop) and ~/.config are left untouched: pick
#  either one in the session menu of your display manager. SDDM remembers the
#  last session you picked. Undo: sudo ./session/uninstall.sh
#
#  Optional:  sudo ./session/install.sh --sddm-theme
#    also installs the "encre" login screen (session/sddm/encre) as
#    /usr/share/sddm/themes/inkpaw-encre and selects it in
#    /etc/sddm.conf.d/zz-inkpaw-theme.conf ([Theme] Current=...).
#    "zz-" makes it load after any other file there (later files win).
#    Its background is drawn on the fly (hyprtheme/generate-wallpapers.sh,
#    "14-ink-hills", needs ImageMagick). Undo: sudo ./session/uninstall.sh --sddm-theme
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

HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PROJECT="$(dirname "$HERE")"
DEST=/usr/share/wayland-sessions

chmod +x "$HERE/start.sh"
install -d -m755 "$DEST"
sed "s|@PROJECT@|$PROJECT|g" "$HERE/inkpaw.desktop.in" > "$DEST/inkpaw.desktop"
chmod 644 "$DEST/inkpaw.desktop"

echo "Installed:"
echo "  $DEST/inkpaw.desktop  (Exec=$PROJECT/session/start.sh)"
echo "Log out, then choose \"Hyprland — Inkpaw\" in the session menu of the login screen."

# --- optional: SDDM theme "inkpaw-encre" ---------------------------------
# SDDM runs as its own user: the theme folder is COPIED (fonts, cats, logo
# and the background are inside it), nothing in it points back to /home.
if [ "$SDDM_THEME" = 1 ]; then
  THEME_SRC="$HERE/sddm/encre"
  THEME_DEST=/usr/share/sddm/themes/inkpaw-encre
  THEME_CONF=/etc/sddm.conf.d/zz-inkpaw-theme.conf
  [ -f "$THEME_SRC/Main.qml" ] || { echo "Missing $THEME_SRC/Main.qml" >&2; exit 1; }
  rm -rf "$THEME_DEST"
  install -d -m755 "$THEME_DEST"
  cp -rL --no-preserve=ownership "$THEME_SRC/." "$THEME_DEST/"
  # background: the parchment ink-hills wallpaper, drawn at 1920x1080
  if command -v magick >/dev/null; then
    tmp="$(mktemp -d)"
    XDG_CONFIG_HOME=/nonexistent ONLY="14-ink-hills" \
      bash "$PROJECT/hyprtheme/generate-wallpapers.sh" "$tmp" 1920x1080 >/dev/null
    install -m644 "$tmp/14-ink-hills.jpg" "$THEME_DEST/background.jpg"
    rm -rf "$tmp"
  else
    echo "  (ImageMagick missing: the login screen gets a plain ink background)"
  fi
  chmod -R u=rwX,go=rX "$THEME_DEST"
  install -d -m755 /etc/sddm.conf.d
  printf '%s\n' \
    "# Written by inkpaw session/install.sh --sddm-theme" \
    "# Remove with: sudo session/uninstall.sh --sddm-theme" \
    "[Theme]" "Current=inkpaw-encre" > "$THEME_CONF"
  chmod 644 "$THEME_CONF"
  echo "  $THEME_DEST  (SDDM theme)"
  echo "  $THEME_CONF  ([Theme] Current=inkpaw-encre)"
  echo "Preview: sddm-greeter-qt6 --test-mode --theme $THEME_DEST"
fi
