#!/usr/bin/env python3
# =============================================================================
#  hyprtheme/lib/accents.py — 6 harmonious accent colors ("wallbash"-style)
# =============================================================================
#  Usage: accents.py <primary-hex> <dark|light> [explicit,hexes] [wallbash|rainbow]
#  wallbash (default): tone-on-tone around the wallpaper hue (HyDE look)
#  rainbow: 6 hues around the color wheel (explicit static accents used here)
#  Prints {"accent": {"a1": "#rrggbb", "a1_hex": "rrggbb", ...}} for matugen
#  (--import-json-string). Templates use {{accent.a1}} … {{accent.a6}}.
#
#  Without explicit colors, the primary hue is rotated around the color wheel
#  with a vivid saturation, so every module gets its own color that still
#  belongs to the wallpaper's palette. Static themes may pass their own list.
# =============================================================================
import colorsys, json, sys

primary, mode = sys.argv[1].lstrip("#"), sys.argv[2]
explicit = [c.strip().lstrip("#") for c in sys.argv[3].split(",")] if len(sys.argv) > 3 and sys.argv[3] else []

def to_hex(r, g, b):
    return "".join(f"{round(max(0, min(1, v)) * 255):02x}" for v in (r, g, b))

style = sys.argv[4] if len(sys.argv) > 4 else "wallbash"

if len(explicit) >= 6 and style == "rainbow":
    colors = explicit[:6]
else:
    r, g, b = (int(primary[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    dark = mode == "dark"
    if style == "rainbow":
        # 6 hues around the wheel, vivid
        sat = min(0.9, max(0.62, s * 1.15))
        light = 0.72 if dark else 0.44
        steps = [(o, light, sat) for o in (0, 45, 100, 165, 235, 300)]
    else:
        # "wallbash" (HyDE): tone-on-tone pastels close to the wallpaper hue,
        # varied in lightness, one soft complementary accent for contrast
        sat = min(0.62, max(0.38, s))
        L = (lambda x: x) if dark else (lambda x: 1.15 - x)
        steps = [(0, L(0.78), sat), (16, L(0.70), sat), (-16, L(0.84), sat * 0.9),
                 (32, L(0.64), sat), (-32, L(0.74), sat * 0.85), (180, L(0.76), sat * 0.7)]
    colors = [to_hex(*colorsys.hls_to_rgb((h + o / 360) % 1, li, sa)) for o, li, sa in steps]

out = {}
for i, c in enumerate(colors, 1):
    out[f"a{i}"] = "#" + c
    out[f"a{i}_hex"] = c
print(json.dumps({"accent": out}))
