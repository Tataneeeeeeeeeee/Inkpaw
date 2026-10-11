#!/usr/bin/env bash
# =============================================================================
#  hyprtheme/wallpaper-picker.sh — preview grid of WALLPAPER_DIR (rofi)
# =============================================================================
#  Portrait thumbnails with rounded corners are generated once (ImageMagick)
#  into ~/.cache/inkpaw/thumbs-portrait
#  and refreshed when the source image changes. Selecting an image runs
#  `theme.sh wallpaper <image>` → wallpaper transition + new palette everywhere.
#  Look: rofi/themes/wallpaper-strip.rasi (full-width band of cards, HyDE-style),
#  or rofi/skins/$UI_SKIN/wallpaper-strip.rasi when the active skin has one.
#  UI_SKIN=encre with GTK 4 layer-shell: wallpicker/wallpicker.py instead.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"
. "$SCRIPTS/rofi-theme.sh"   # rofi_theme: skinned theme (rofi/skins/$UI_SKIN) first

# encre: the GTK 4 band of the mockup (wallpicker/: torn parchment, taped
# photos, the cat on the selection), resident and opened / closed instantly;
# exit 3 = no layer-shell -> rofi below
if [ "${UI_SKIN:-default}" = "encre" ]; then
    "$SCRIPTS/resident.sh" wallpicker && exit 0
fi

dir="${WALLPAPER_DIR:-$HOME/Pictures/wallpapers}"
thumbs="$CACHE/thumbs-portrait"
mkdir -p "$thumbs"
[ -d "$dir" ] || { notify "Wallpaper" "Folder not found: $dir"; exit 1; }

magick_bin=""; have magick && magick_bin="magick"; [ -z "$magick_bin" ] && have convert && magick_bin="convert"

# rofi entries: "<label>\0icon\x1f<thumbnail>" (same order as the file list below)
list() {
    find -L "$dir" -maxdepth 2 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.gif' \) | sort |
    while read -r img; do
        rel="${img#"$dir"/}"
        label="${rel%.*}"; label="${label#[0-9][0-9]-}"; label="${label//-/ }"
        thumb="$thumbs/$(printf '%s' "$img" | md5sum | cut -c1-16).png"
        if [ -n "$magick_bin" ] && { [ ! -f "$thumb" ] || [ "$img" -nt "$thumb" ]; }; then
            # portrait card, rounded corners (HyDE-style strip)
            "$magick_bin" "${img}[0]" -strip -thumbnail 360x500^ -gravity center -extent 360x500 \
                \( +clone -alpha extract -fill black -colorize 100 -fill white \
                   -draw "roundrectangle 0,0 359,499 26,26" \) -alpha off -compose copyopacity -composite "$thumb" 2>/dev/null
        fi
        [ -f "$thumb" ] || thumb="$img"
        # card label = clean name ("09-synthwave-sunset.jpg" -> "synthwave sunset")
        printf '%s\0icon\x1f%s\n' "$label" "$thumb"
    done
}

# -format i returns the index of the chosen card; map it back to the file
mapfile -t files < <(find -L "$dir" -maxdepth 2 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' -o -iname '*.gif' \) | sort)
idx=$(list | rofi -dmenu -i -show-icons -format i -p "Wallpaper" -theme "$(rofi_theme wallpaper-strip)")
[ -n "$idx" ] && exec "$THEME_DIR/theme.sh" wallpaper "${files[$idx]}"
