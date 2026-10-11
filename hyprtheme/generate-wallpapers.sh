#!/usr/bin/env bash
# =============================================================================
#  hyprtheme/generate-wallpapers.sh — procedural wallpapers (ImageMagick only)
# =============================================================================
#  Usage: generate-wallpapers.sh [output-dir] [WIDTHxHEIGHT]
#         default dir  = WALLPAPER_DIR from hypr/settings.conf
#         default size = 3840x2160 (covers 1920x1200 and 3440x1440 when cropped)
#  Existing files are never overwritten (delete one to regenerate it).
#  ONLY="14-ink-hills 15-ink-hills-night" generates just those names.
#
#  Styles: blobs (mesh gradient), aurora, waves, sunset (mountains + sun),
#  plasma. Every image gets a fine film grain so gradients never band.
#  Rendering is done at 1/4 size then upscaled with heavy blur where possible,
#  so the whole set takes about a minute.
# =============================================================================
set -euo pipefail
# shellcheck disable=SC1091
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh" 2>/dev/null || true

OUT="${1:-${WALLPAPER_DIR:-$HOME/Pictures/wallpapers}}"
SIZE="${2:-3840x2160}"
W="${SIZE%x*}"; H="${SIZE#*x}"
w=$((W / 4)); h=$((H / 4))               # working resolution
mkdir -p "$OUT"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

have_magick() { command -v magick >/dev/null || { echo "ImageMagick (magick) is required" >&2; exit 1; }; }
have_magick

# Deterministic pseudo-random numbers: rnd <seed> <n> <max>
rnd() { awk -v s="$1" -v n="$2" -v m="$3" 'BEGIN { srand(s); for (i = 0; i < n; i++) printf "%d ", rand() * m }'; }

# Final step: upscale, grain, save
finish() {   # <small.png> <name>
    # +noise on the image itself keeps the mean brightness (a softlight overlay
    # in ImageMagick brightens everything)
    magick "$1" -resize "${W}x${H}!" -attenuate 0.35 +noise Gaussian -quality 92 "$OUT/$2.jpg"
    echo "  ✔ $2.jpg"
}

skip() {
    if [ -n "${ONLY:-}" ] && [[ " $ONLY " != *" $1 "* ]]; then return 0; fi
    [ -f "$OUT/$1.jpg" ] && { echo "  · $1.jpg (exists)"; return 0; }; return 1
}

# --- blobs: large blurred color spots on a dark base -----------------------------
blobs() {   # <name> <seed> <bg> <colors...>
    local name="$1" seed="$2" bg="$3"; shift 3
    skip "$name" && return
    local args=() i=0 c x y r
    local -a xs ys rs
    read -ra xs <<<"$(rnd "$seed" 8 "$w")"
    read -ra ys <<<"$(rnd $((seed + 1)) 8 "$h")"
    read -ra rs <<<"$(rnd $((seed + 2)) 8 $((h / 5)))"
    for c in "$@" "$@"; do
        [ $i -ge 6 ] && break
        x=${xs[$i]}; y=${ys[$i]}; r=$(( ${rs[$i]} + h / 7 ))
        [[ "$name" == *light* ]] && r=$(( ${rs[$i]} * 2 + h / 4 ))   # light: big soft fields
        args+=( -fill "${c}e6" -draw "circle $x,$y $((x + r)),$y" )   # e6 = ~90 % opaque
        i=$((i + 1))
    done
    if [[ "$name" == *light* ]]; then   # light variant: opaque spots, no brightening
        args=("${args[@]//e6/}")
        magick -size "${w}x${h}" "xc:$bg" "${args[@]}" -blur 0x$((h / 8)) -modulate 100,120 "$TMP/$name.png"
    else
        magick -size "${w}x${h}" "xc:$bg" "${args[@]}" -blur 0x$((h / 7)) -modulate 125,165 \
            \( -size "${w}x${h}" "radial-gradient:none-${bg}aa" \) -compose over -composite "$TMP/$name.png"
    fi
    finish "$TMP/$name.png" "$name"
}

# --- aurora: thin curtains of light along a wave, over a night gradient ---------
aurora() {   # <name> <seed> <top> <bottom> <c1> <c2> <c3>
    local name="$1" seed="$2" top="$3" bottom="$4"; skip "$name" && return
    local cols=("$5" "$6" "$7") args=()
    while read -r x y len ci; do
        args+=( -fill "${cols[$ci]}" -draw "rectangle $x,$y $((x + w / 90)),$((y + len))" )
    done < <(awk -v w="$w" -v h="$h" -v s="$seed" 'BEGIN { srand(s)
        for (x = 0; x < w; x += w / 160) {
            y = h * (0.22 + 0.10 * sin(x / w * 6.28 * 1.3 + s) + 0.04 * sin(x / w * 6.28 * 4.1))
            printf "%d %d %d %d\n", x, y, h * (0.12 + rand() * 0.22), int((x / w) * 3 + rand() * 0.9) % 3 } }')
    magick -size "${w}x${h}" "gradient:$top-$bottom" \
        \( -size "${w}x${h}" xc:none "${args[@]}" -motion-blur 0x$((h / 8))+90 -blur 0x$((h / 60)) \
           -channel A -evaluate multiply 0.9 +channel \) -compose screen -composite \
        \( -size "${w}x${h}" xc:none "${args[@]}" -blur 0x$((h / 10)) -channel A -evaluate multiply 0.5 +channel \) -compose screen -composite \
        "$TMP/$name.png"
    finish "$TMP/$name.png" "$name"
}

# --- waves: layered sine bands with gradient fills ----------------------------------
waves() {   # <name> <seed> <bg> <colors... (4)>
    local name="$1" seed="$2" bg="$3"; shift 3
    skip "$name" && return
    local args=() layer=0 c pts
    for c in "$@"; do
        pts=$(awk -v w="$w" -v h="$h" -v L="$layer" -v s="$seed" 'BEGIN {
            srand(s + L); a = h * (0.05 + rand() * 0.06); f = 1.2 + rand() * 1.6; p = rand() * 6.28
            base = h * (0.38 + L * 0.15)
            printf "0,%d ", h
            for (x = 0; x <= w; x += w / 120) printf "%d,%d ", x, base + a * sin(x / w * 6.28 * f + p)
            printf "%d,%d", w, h }')
        args+=( -fill "$c" -draw "polygon $pts" )
        layer=$((layer + 1))
    done
    magick -size "${w}x${h}" "xc:$bg" "${args[@]}" -blur 0x2 \
        \( -size "${w}x${h}" "radial-gradient:none-#00000066" \) -compose over -composite "$TMP/$name.png"
    finish "$TMP/$name.png" "$name"
}

# --- sunset: gradient sky, glowing sun, layered mountain ridges ----------------------
sunset() {  # <name> <seed> <sky-top> <sky-bottom> <sun> <ridge1> <ridge2> <ridge3>
    local name="$1" seed="$2"; skip "$name" && return
    local sky1="$3" sky2="$4" sun="$5"; shift 5
    local args=() L=0 c pts
    for c in "$@"; do
        pts=$(awk -v w="$w" -v h="$h" -v L="$L" -v s="$seed" 'BEGIN {
            srand(s * 7 + L); base = h * (0.55 + L * 0.12); y = base
            printf "0,%d ", h
            for (x = 0; x <= w; x += w / 60) { y += (rand() - 0.5) * h * 0.06; if (y < base - h*0.12) y = base - h*0.12; if (y > base + h*0.08) y = base + h*0.08; printf "%d,%d ", x, y }
            printf "%d,%d", w, h }')
        args+=( -fill "$c" -draw "polygon $pts" )
        L=$((L + 1))
    done
    local cx=$((w / 2)) cy=$((h * 52 / 100)) r=$((h / 6))
    magick -size "${w}x${h}" "gradient:$sky1-$sky2" \
        \( -size "${w}x${h}" xc:none -fill "$sun" -draw "circle $cx,$cy $((cx + r * 2)),$cy" -blur 0x$((h / 8)) \) -compose screen -composite \
        -fill "$sun" -draw "circle $cx,$cy $((cx + r)),$cy" \
        "${args[@]}" "$TMP/$name.png"
    finish "$TMP/$name.png" "$name"
}

# --- plasma: fractal noise mapped onto a color ramp ------------------------------
plasma() {  # <name> <seed> <c1> <c2> <c3> <c4>
    local name="$1" seed="$2"; skip "$name" && return
    magick -size 1x256 "gradient:$3-$4" "gradient:$4-$5" "gradient:$5-$6" -append -resize 1x256! "$TMP/ramp.png"
    magick -seed "$seed" -size "${w}x${h}" plasma:fractal -blur 0x$((h / 30)) -colorspace gray -auto-level -evaluate pow 1.5 \
        "$TMP/ramp.png" -clut "$TMP/plasma-$name.png"
    finish "$TMP/plasma-$name.png" "$name"
}

echo "Generating wallpapers in $OUT ($SIZE)"
blobs  01-synthwave-glow   11 "#1a1426" "#ff7edb" "#36f9f6" "#b893ce" "#fede5d"
blobs  02-catppuccin-mist  23 "#1e1e2e" "#cba6f7" "#f5c2e7" "#89b4fa" "#94e2d5"
blobs  03-rose-pine-dusk   37 "#191724" "#ebbcba" "#c4a7e7" "#31748f" "#f6c177"
blobs  04-tokyo-neon       41 "#16161e" "#7aa2f7" "#bb9af7" "#7dcfff" "#f7768e"
aurora 05-aurora-north     53 "#050816" "#0b1026" "#00ffa3" "#00b3ff" "#7a00ff"
aurora 06-aurora-pink      67 "#0d0518" "#1a0b2e" "#ff6ec7" "#8a5cff" "#00e5ff"
waves  07-ocean-waves      71 "#0f2027" "#1c4e80" "#2b7bba" "#4fb3d9" "#a8e6ff"
waves  08-candy-waves      83 "#2d1b4e" "#7b2ff7" "#c86dd7" "#ff8fab" "#ffd6a5"
sunset 09-synthwave-sunset 97 "#120c2b" "#ff4f9a" "#ffd36e" "#3a1c5c" "#24123f" "#140a26"
sunset 10-forest-dawn      101 "#1f3b5c" "#f6b37f" "#fff1c1" "#2e4a3f" "#1d3329" "#0f1f19"
plasma 11-plasma-ember     113 "#1a0a0a" "#ff512f" "#f09819" "#ffe29f"
plasma 12-plasma-lagoon    127 "#03111f" "#0f4c75" "#00b4d8" "#90e0ef"
blobs  13-lavender-light   131 "#d9cffc" "#a77bff" "#5fb8ff" "#ff7ab8" "#6fe0c0"
# the "encre" themes: ink hills on parchment under an ochre sun / a pale moon at night
sunset 14-ink-hills        139 "#f4ead2" "#e3cf9e" "#d9a12e" "#a8977a" "#6b5a47" "#2a2420"
sunset 15-ink-hills-night  149 "#121014" "#2a2420" "#e9dcb8" "#3d342c" "#2a221c" "#141110"
echo "Done. Pick one with SUPER+CTRL+W (or: hyprtheme/theme.sh random)."
