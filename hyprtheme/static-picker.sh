#!/usr/bin/env bash
# =============================================================================
#  hyprtheme/static-picker.sh — pick a predefined theme from a row of cards
# =============================================================================
#  Each card = the theme's wallpaper ("wallpaper" in static/<name>.json) on the
#  left, its name and 6 accent dots on the right (HyDE-style). Cards are cached
#  in ~/.cache/inkpaw/theme-cards and rebuilt when the JSON changes.
#  Choosing a card applies the palette AND its wallpaper.
#  UI_SKIN=encre with GTK 4 layer-shell: themepicker/themepicker.py instead.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"
. "$SCRIPTS/rofi-theme.sh"   # rofi_theme: skinned theme (rofi/skins/$UI_SKIN) first

# encre: the GTK 4 sheet of the mockup (themepicker/: mini desktops in each
# theme's colors), resident and opened / closed instantly; exit 3 = no layer-shell
if [ "${UI_SKIN:-default}" = "encre" ]; then
    "$SCRIPTS/resident.sh" themepicker && exit 0
fi

cards="$CACHE/theme-cards"; mkdir -p "$cards"
wdir="${WALLPAPER_DIR:-$HOME/Pictures/wallpapers}"
# ImageMagick needs a font FILE, not a family name
font=$(fc-match -f "%{file}" "${FONT_FAMILY:-sans-serif}:weight=bold" 2>/dev/null)

mapfile -t themes < <(find "$THEME_DIR/static" -name '*.json' -printf '%f\n' | sed 's/\.json$//' | sort)

card() {   # <name> -> path of the card png
    local n="$1" json="$THEME_DIR/static/$1.json" out="$cards/$1.png"
    [ -f "$out" ] && [ "$out" -nt "$json" ] && { echo "$out"; return; }
    local title bg fg wp dots=() i c
    title=$(jq -r .name "$json")
    [ ${#title} -gt 11 ] && title="${title/ /$'\n'}"   # long names on two lines
    bg=$(jq -r '.colors.surface_container_low // .colors.surface' "$json")
    fg=$(jq -r .colors.on_surface "$json"); wp="$wdir/$(jq -r '.wallpaper // ""' "$json")"
    i=0; for c in $(jq -r '(.accents // [])[]' "$json"); do
        dots+=( -fill "$c" -draw "circle $((232 + i * 30)),178 $((232 + i * 30 + 10)),178" ); i=$((i + 1))
    done
    {
        if [ -f "$wp" ]; then magick "${wp}[0]" -resize 220x300^ -gravity center -extent 220x300 "$cards/.img.png"
        else magick -size 220x300 "gradient:$(jq -r .colors.primary "$json")-$bg" "$cards/.img.png"; fi
        magick -size 420x300 "xc:$bg" "$cards/.img.png" -gravity west -composite \
            -gravity northwest ${font:+-font "$font"} -pointsize 24 -fill "$fg" -annotate +232+96 "$title" \
            -pointsize 14 -fill "${fg}99" -annotate +232+214 "$(jq -r .mode "$json") theme" \
            "${dots[@]}" \
            \( +clone -alpha extract -fill black -colorize 100 -fill white -draw "roundrectangle 0,0 419,299 24,24" \) \
            -alpha off -compose copyopacity -composite "$out"
    } 2>/dev/null
    echo "$out"
}

idx=$(for n in "${themes[@]}"; do printf '%s\0icon\x1f%s\n' "$(jq -r .name "$THEME_DIR/static/$n.json")" "$(card "$n")"; done |
      rofi -dmenu -i -show-icons -format i -p "Theme" -theme "$(rofi_theme wallpaper-strip)" \
           -theme-str 'listview { columns: 4; } element { children: [ element-icon ]; } element-icon { size: 400px; }')
[ -n "$idx" ] && exec "$THEME_DIR/theme.sh" static "${themes[$idx]}"
