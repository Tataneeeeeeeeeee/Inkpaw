#!/usr/bin/env python3
# =============================================================================
#  logo/build.py — draws the Inkpaw logo (SVG + PNG renders)
# =============================================================================
#  The mark: the ochre cat of the encre skin
#  (flat head between pointed ears, ink outline) curled up asleep, its tail
#  wrapped around it, two little "z" above. The signature puts
#  the sleeping cat above "Inkpaw" in Caveat Brush, underlined in ochre.
#
#  Writes next to this script:
#    inkpaw-mark.svg            parchment tile (app icon, avatar)   + .png 512 / 256 / 128 / 64 / 32
#    inkpaw-mark-dark.svg       ink tile, cream lines               + .png 512 / 128
#    inkpaw-mark-flat.svg       the cat alone on transparency       + .png 512 / 256 / 128 / 64
#    inkpaw-mark-flat-dark.svg  same, cream lines (dark backgrounds) + .png 512 / 256
#    inkpaw-mark-mono.svg       one ink color, stencil cut (stamps, favicons)
#    inkpaw-logo.svg            cat + wordmark, horizontal          + .png 1100 wide (+ -dark)
#    inkpaw-signature.svg       cat above the name                  + .png 600 / 300 wide (+ -dark)
#  Run again after a change: python3 build.py
#  The wordmark is SVG text: renders need the Caveat Brush font
#  (hyprtheme/fonts, used through FONTCONFIG_FILE below). The UI uses the PNGs.
# =============================================================================
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "hyprtheme", "fonts", "fonts.conf")

INK = "#2a2420"
PAPER = "#f1e7cf"
OCHRE = "#d9a12e"

# The cat is drawn in a 200 x 200 box; its bounding box (with the "z") is
# x 28..172, y 40..174 → CAT_BOX is used to fit it anywhere.
CAT_BOX = (28, 40, 144, 134)


def head(cx, cy, line, s=1.0):
    """The encre cat's head (flat top between pointed ears), eyes shut; cy = eye line."""
    def p(v):
        return round(v * s, 2)
    b = cy + p(12)
    d = (f"M{cx - p(38)} {b} L{cx - p(32)} {b - p(40)} L{cx - p(10)} {b - p(22)} "
         f"Q{cx} {b - p(25)} {cx + p(10)} {b - p(22)} L{cx + p(32)} {b - p(40)} L{cx + p(38)} {b} "
         f"Q{cx} {b + p(14)} {cx - p(38)} {b} Z")
    return (f'<path d="{d}" fill="{OCHRE}" stroke="{line}" stroke-width="{p(5)}" stroke-linejoin="round"/>'
            f'<path d="M{cx - p(18)} {cy} Q{cx - p(12)} {cy + p(5)} {cx - p(6)} {cy} M{cx + p(6)} {cy} '
            f'Q{cx + p(12)} {cy + p(5)} {cx + p(18)} {cy}" stroke="{line}" stroke-width="{p(4)}" stroke-linecap="round"/>')


def cat(line=INK, zz=True, zz_color=None):
    """The sleeping cat in its 200 box: body, tail wrapped around, head, two z."""
    tail = "M160 150 C150 168 110 170 86 162"
    out = (f'<path d="M40 160 C30 124 56 100 100 100 C144 100 172 124 162 160 Z" fill="{OCHRE}" '
           f'stroke="{line}" stroke-width="5" stroke-linejoin="round"/>'
           f'<path d="{tail}" stroke="{line}" stroke-width="17" stroke-linecap="round" fill="none"/>'
           f'<path d="{tail}" stroke="{OCHRE}" stroke-width="8" stroke-linecap="round" fill="none"/>'
           + head(70, 132, line, s=0.95))
    if zz:
        out += (f'<path d="M132 60 h12 l-12 12 h12 M154 42 h9 l-9 9 h9" stroke="{zz_color or line}" stroke-width="4" '
                f'stroke-linecap="round" stroke-linejoin="round" fill="none" opacity="0.75"/>')
    return out


def place(body, x, y, w):
    """Fit the cat box into width w with its top-left corner at x, y."""
    bx, by, bw, _ = CAT_BOX
    k = w / bw
    return f'<g transform="translate({round(x - bx * k, 2)} {round(y - by * k, 2)}) scale({round(k, 4)})">{body}</g>'


def tile(fill=PAPER, line=INK):
    """512 tile, 14 px outline, the skin's uneven corners, hard shadow."""
    corners = (82, 110, 70, 100)        # tl, tr, br, bl radii
    w = h = 476
    tl, tr, br, bl = corners
    ox = oy = 8
    d = (f"M{ox + tl} {oy} H{ox + w - tr} Q{ox + w} {oy} {ox + w} {oy + tr} "
         f"V{oy + h - br} Q{ox + w} {oy + h} {ox + w - br} {oy + h} "
         f"H{ox + bl} Q{ox} {oy + h} {ox} {oy + h - bl} V{oy + tl} Q{ox} {oy} {ox + tl} {oy} Z")
    shadow = INK if fill == PAPER else "#0f0c0a"
    return (f'<path d="{d}" fill="{shadow}" transform="translate(20 20)"/>'
            f'<path d="{d}" fill="{fill}" stroke="{line}" stroke-width="14" stroke-linejoin="round"/>')


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'fill="none">\n{body}\n</svg>\n')


def mark(dark=False):
    line = PAPER if dark else INK
    return svg(512, 512, tile(INK if dark else PAPER, line) + place(cat(line), 60, 70, 384))


def flat(dark=False):
    return svg(512, 512, place(cat(PAPER if dark else INK), 16, 40, 480))


def mono():
    """One ink color: the lines become cuts in the shape (a stencil)."""
    stencil = cat(line="black").replace(f'fill="{OCHRE}"', 'fill="white"').replace(f'stroke="{OCHRE}"', 'stroke="white"')
    stencil = stencil.replace('opacity="0.75"', '').replace('stroke="black" stroke-width="4" stroke-linecap="round" '
                                                              'stroke-linejoin="round"', 'stroke="white" stroke-width="5" '
                                                              'stroke-linecap="round" stroke-linejoin="round"')
    return svg(512, 512, '<mask id="m">' + place(stencil, 16, 40, 480) + '</mask>'
               f'<rect width="512" height="512" fill="{INK}" mask="url(#m)"/>')


def word(x, y, size, color, anchor="start"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Caveat Brush, cursive" '
            f'font-size="{size}" fill="{color}">Inkpaw</text>')


def logo(dark=False):
    line = PAPER if dark else INK
    return svg(1100, 400, place(cat(line), 30, 70, 300)
               + word(380, 262, 220, line)
               + f'<path d="M390 300 C560 282 780 314 1000 290" stroke="{OCHRE}" stroke-width="16" stroke-linecap="round"/>')


def signature(dark=False):
    """Concept 90: the sleeping cat above the name."""
    line = PAPER if dark else INK
    return svg(600, 520, place(cat(line), 165, 20, 270)
               + word(300, 400, 170, line, anchor="middle")
               + f'<path d="M110 440 C230 418 370 458 490 430" stroke="{OCHRE}" stroke-width="14" stroke-linecap="round"/>')


def main():
    out = {"inkpaw-mark.svg": mark(), "inkpaw-mark-dark.svg": mark(True),
           "inkpaw-mark-flat.svg": flat(), "inkpaw-mark-flat-dark.svg": flat(True),
           "inkpaw-mark-mono.svg": mono(),
           "inkpaw-logo.svg": logo(), "inkpaw-logo-dark.svg": logo(True),
           "inkpaw-signature.svg": signature(), "inkpaw-signature-dark.svg": signature(True)}
    for name, text in out.items():
        with open(os.path.join(HERE, name), "w") as f:
            f.write(text)
    rsvg = shutil.which("rsvg-convert")
    if not rsvg:
        print("SVG written (no rsvg-convert: no PNG)")
        return
    env = dict(os.environ, FONTCONFIG_FILE=FONTS)
    renders = [("inkpaw-mark.svg", s, f"inkpaw-mark-{s}.png") for s in (512, 256, 128, 64, 32)]
    renders += [("inkpaw-mark-dark.svg", s, f"inkpaw-mark-dark-{s}.png") for s in (512, 128)]
    renders += [("inkpaw-mark-flat.svg", s, f"inkpaw-mark-flat-{s}.png") for s in (512, 256, 128, 64)]
    renders += [("inkpaw-mark-flat-dark.svg", s, f"inkpaw-mark-flat-dark-{s}.png") for s in (512, 256)]
    renders += [("inkpaw-mark-mono.svg", 512, "inkpaw-mark-mono-512.png")]
    renders += [("inkpaw-logo.svg", 1100, "inkpaw-logo.png"), ("inkpaw-logo-dark.svg", 1100, "inkpaw-logo-dark.png")]
    renders += [(f"inkpaw-signature{d}.svg", w, f"inkpaw-signature{d}-{w}.png") for d in ("", "-dark") for w in (600, 300)]
    for src, w, dst in renders:
        subprocess.run([rsvg, "-w", str(w), "-o", os.path.join(HERE, dst), os.path.join(HERE, src)], env=env, check=False)
    print(f"logo written in {HERE}")


if __name__ == "__main__":
    main()
