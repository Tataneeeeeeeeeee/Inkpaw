#!/usr/bin/env bash
# =============================================================================
#  menus/keybindings.sh — cheat sheet generated from live binds
# =============================================================================
#  Reads `hyprctl binds -j` and shows every bind that has a description
#  (all binds in conf/keybinds/*.lua have one). Searchable.
#  Skinned (rofi/skins/$UI_SKIN/keys.rasi exists, e.g. "encre"): the rows are
#  pango markup — keys drawn as caps (mono font on the darker paper, colors
#  from the skin's generated tokens.rasi), key names prettified (RETURN ->
#  ENTER, AZERTY digits -> their glyph…; no arrows: the mono font has none and
#  the padding that lines the actions up counts characters), then the action.
#  Otherwise: plain aligned columns.
#  UI_SKIN=encre with GTK 4 layer-shell: keysheet/keysheet.py instead (cards).
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/../lib.sh"
. "$SCRIPTS/rofi-theme.sh"

# encre: the GTK 4 sheet of the mockup (keysheet/: category cards, filter,
# keycaps), resident and opened / closed instantly; exit 3 = no layer-shell -> rofi
if [ "${UI_SKIN:-default}" = "encre" ]; then
    "$SCRIPTS/resident.sh" keysheet && exit 0
fi

# "<key> <key>…<TAB><description>" (keys separated by \x1f), deduplicated
binds() {
    hyprctl binds -j | jq -r '
      def mods($m):
        [ (if ($m / 64 | floor) % 2 == 1 then "SUPER" else empty end),
          (if ($m / 4  | floor) % 2 == 1 then "CTRL"  else empty end),
          (if ($m / 8  | floor) % 2 == 1 then "ALT"   else empty end),
          (if ($m      | floor) % 2 == 1 then "SHIFT" else empty end) ] ;
      .[] | select((.description // "") != "")
          | (mods(.modmask) + [ (.key | ascii_upcase) ] | map(select(. != "")) | join("\u001f")) as $combo
          | "\($combo)\t\(.description)"' | awk '!seen[$0]++'
}

if ! rofi_skinned keys; then
    # Default look: aligned plain text
    binds | awk -F'\t' '{ gsub(/\x1f/, " + ", $1); printf "%-32s  %s\n", $1, $2 }' |
      rofi_menu "Keybindings" -no-custom -theme-str 'window { width: 1180px; } element-text { font: "monospace 11"; }' >/dev/null
    exit 0
fi

# Skinned look: keycaps in pango markup, padded so the actions line up
card=$(rofi_token paper-dark '#e2d3b0'); ink=$(rofi_token ink '#2a2420')
mono=$(rofi_token font-mono 'monospace Bold 11'); mono="${mono% *} 11"
binds | LC_ALL=C.UTF-8 awk -F'\t' -v card="$card" -v ink="$ink" -v mono="$mono" '
  function pretty(k) {
    if (k == "RETURN") return "ENTER"
    if (k == "AMPERSAND") return "&";  if (k == "EACUTE") return "é";
    if (k == "QUOTEDBL") return "\""; if (k == "APOSTROPHE") return "'\''";
    if (k == "PARENLEFT") return "(";  if (k == "MINUS") return "-";
    if (k == "EGRAVE") return "è";     if (k == "UNDERSCORE") return "_";
    if (k == "CCEDILLA") return "ç";   if (k == "AGRAVE") return "à";
    if (k == "MOUSE:272") return "CLICK"; if (k == "MOUSE:273") return "R-CLICK";
    if (k == "MOUSE_DOWN") return "WHEEL-DN"; if (k == "MOUSE_UP") return "WHEEL-UP";
    if (k ~ /^SWITCH:/) return "LID";
    sub(/^XF86AUDIO/, "", k); sub(/^XF86MONBRIGHTNESS/, "BRIGHT ", k); sub(/^XF86/, "", k)
    if (k == "RAISEVOLUME") return "VOL+"; if (k == "LOWERVOLUME") return "VOL-"
    if (k == "MICMUTE") return "MIC";      if (k == "BRIGHT UP") return "BRIGHT+"
    if (k == "BRIGHT DOWN") return "BRIGHT-"
    return k
  }
  function esc(s) { gsub(/&/, "\\&amp;", s); gsub(/</, "\\&lt;", s); gsub(/>/, "\\&gt;", s); return s }
  {
    n = split($1, keys, "\x1f"); caps = ""; len = 0
    for (i = 1; i <= n; i++) {
      k = pretty(keys[i])
      caps = caps (i > 1 ? " " : "") "<span background=\"" card "\" foreground=\"" ink "\"> " esc(k) " </span>"
      len += length(k) + 2 + (i > 1)
    }
    row[NR] = caps; width[NR] = len; desc[NR] = esc($2)
    if (len > max) max = len
  }
  END {
    for (r = 1; r <= NR; r++) {
      pad = sprintf("%" (max - width[r] + 2) "s", "")
      printf "<span font=\"%s\">%s%s</span>%s\n", mono, row[r], pad, desc[r]
    }
  }' |
  ROFI_THEME=keys rofi_menu "Keybindings" -no-custom -markup-rows >/dev/null
