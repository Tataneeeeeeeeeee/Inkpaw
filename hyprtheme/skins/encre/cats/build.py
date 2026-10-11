#!/usr/bin/env python3
# =============================================================================
#  hyprtheme/skins/encre/cats/build.py — draws every cat of the "encre" skin
# =============================================================================
#  Writes the SVG files next to this script (and a 2x PNG of each one when
#  rsvg-convert is installed, for apps that cannot read SVG such as hyprlock).
#  Run it again after changing a cat:   python3 build.py
#
#  The cats are original drawings (thick ink outline, lumpy head, odd eyes,
#  small mutations), made for this project — not assets taken from any game.
#
#  Files
#    head-<cat>.svg        face, 120x120          (icons, avatars, mascots)
#    peek-<cat>.svg        face + two paws        (peeking over a panel edge)
#    sit-<cat>.svg         sitting cat            (sitting on a field / card)
#    sleep-<cat>.svg       lying cat with "z z"   (napping on a card)
#    paw-<cat>.svg         one paw                (dragging a corner, hovering)
#    power-<action>.svg    faces for the power menu: lock logout suspend reboot shutdown
#    gamer.svg             headband + headset     (game mode notification)
#    basket.svg            three cats in a basket (welcome window)
# =============================================================================
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
INK = "#2a2420"
EAR = "#e7a196"
NOSE = "#c9675e"
TONGUE = "#e07a8a"
CREAM = "#fffaf0"

# name: fur, patch color (or None), left/right eye radius, pupil shift, eye color, mutations
CATS = {
    "moumoute":  dict(fur="#e9a14a", spot="#b86a2a", eyes=(11, 15), dx=3,  eye=CREAM,     traits=()),
    "gribouille": dict(fur="#5c5a57", spot=None,      eyes=(13, 13), dx=0,  eye="#e8d36a", traits=("third",)),
    "biscotte":  dict(fur="#f3ead6", spot="#c9a77a", eyes=(12, 9),  dx=-2, eye=CREAM,     traits=("horn",)),
    "pate":      dict(fur="#8a6a4a", spot=None,      eyes=(10, 14), dx=2,  eye=CREAM,     traits=("tongue",)),
    "clafoutis": dict(fur="#3b3734", spot=None,      eyes=(12, 12), dx=1,  eye="#c9e06a", traits=("stitch",)),
    "croquette": dict(fur="#c9c3b5", spot="#e9a14a", eyes=(14, 10), dx=-3, eye=CREAM,     traits=("tongue", "calico")),
}

HEAD = ("M26 54 C21 41 20 26 23 12 C33 18 41 25 47 32 C55 29 66 29 74 32 C80 25 89 18 98 12 "
        "C101 27 100 41 95 54 C104 66 102 85 90 96 C76 108 44 108 30 96 C18 85 16 66 26 54 Z")


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'fill="none" stroke="{INK}" stroke-linejoin="round" stroke-linecap="round">\n{body}\n</svg>\n')


def face(c, eyes_open=True, eyes_path=None, mouth=True, whiskers=True):
    """Head in a 120x120 box. eyes_path replaces the round eyes (power faces)."""
    l, r = c["eyes"]
    p = [f'<path d="{HEAD}" fill="{c["fur"]}" stroke-width="5"/>']
    if c["spot"]:
        p.append(f'<path d="M71 37 C82 36 91 44 92 56 C83 57 75 50 71 37 Z" fill="{c["spot"]}" stroke="none"/>')
    if "calico" in c["traits"]:
        p.append('<path d="M30 40 C36 34 46 34 48 42 C40 46 34 46 30 40 Z" fill="#3b3734" stroke="none"/>')
    p.append(f'<path d="M29 22 L31 38 L42 33 Z" fill="{EAR}" stroke-width="3"/>')
    p.append(f'<path d="M92 22 L79 33 L90 38 Z" fill="{EAR}" stroke-width="3"/>')
    if "horn" in c["traits"]:
        p.append('<path d="M53 31 C49 21 52 12 59 8 C59 17 62 24 63 30" fill="#efe3c4" stroke-width="4"/>')
    if eyes_path:
        p.append(f'<path d="{eyes_path}" stroke-width="4.5"/>')
    elif eyes_open:
        dx = c["dx"]
        p.append(f'<circle cx="45" cy="64" r="{l}" fill="{c["eye"]}" stroke-width="4"/>')
        p.append(f'<circle cx="{45 + dx}" cy="65" r="{round(l * 0.45)}" fill="{INK}" stroke="none"/>')
        p.append(f'<circle cx="77" cy="62" r="{r}" fill="{c["eye"]}" stroke-width="4"/>')
        p.append(f'<circle cx="{77 - dx}" cy="61" r="{round(r * 0.4)}" fill="{INK}" stroke="none"/>')
        if "third" in c["traits"]:
            p.append(f'<circle cx="61" cy="45" r="7" fill="{c["eye"]}" stroke-width="3.5"/>')
            p.append(f'<circle cx="61" cy="46" r="3" fill="{INK}" stroke="none"/>')
    p.append(f'<path d="M57 78 L66 78 L61.5 83 Z" fill="{NOSE}" stroke-width="3"/>')
    if mouth is True:
        p.append('<path d="M51 86 C55 91 60 89 61.5 84 C63 89 68 91 72 86" stroke-width="3.5"/>')
    elif mouth:
        p.append(f'<path d="{mouth}" stroke-width="3.5"/>')
    if "tongue" in c["traits"] and mouth is True:
        p.append(f'<path d="M58 88 C58 97 65 97 65 88" fill="{TONGUE}" stroke-width="3"/>')
    if "stitch" in c["traits"]:
        p.append('<path d="M30 46 L44 40 M33 40 L35 47 M39 38 L41 45" stroke-width="3"/>')
    if whiskers:
        p.append('<path d="M28 79 L10 75 M29 86 L11 90 M94 79 L111 75 M93 86 L110 90" stroke-width="3"/>')
    return "\n".join(p)


def paws(fur, y, xs=(22, 88)):
    out = []
    for x in xs:
        out.append(f'<ellipse cx="{x}" cy="{y}" rx="18" ry="11" fill="{fur}" stroke-width="3.5"/>')
        out.append(f'<path d="M{x - 6} {y + 7}v-6M{x + 2} {y + 7}v-6" stroke-width="3"/>')
    return "\n".join(out)


def sit(c):
    """Sitting cat, 120x110: body behind, head on top (lock screen, cards)."""
    l, r = c["eyes"]
    third = ""
    if "third" in c["traits"]:
        third = (f'<circle cx="60" cy="38" r="5.5" fill="{c["eye"]}" stroke-width="2.5"/>'
                 f'<circle cx="60" cy="40" r="2.5" fill="{INK}" stroke="none"/>')
    spot = (f'<path d="M66 30 C76 30 84 36 86 46 C78 46 70 40 66 30 Z" fill="{c["spot"]}" stroke="none"/>'
            if c["spot"] else "")
    return "\n".join([
        f'<path d="M22 108 C14 80 22 56 42 50 L78 50 C98 56 106 80 98 108 Z" fill="{c["fur"]}" stroke-width="4"/>',
        f'<path d="M98 100 C116 96 118 74 108 66" stroke-width="6"/>',
        f'<path d="M30 46 C26 36 26 22 30 10 C38 16 44 22 48 28 C54 26 66 26 72 28 C76 22 82 16 90 10 '
        f'C94 22 94 36 90 46 C96 58 90 72 76 76 C62 80 48 80 38 74 C26 68 24 56 30 46 Z" fill="{c["fur"]}" stroke-width="4"/>',
        spot,
        f'<path d="M33 18 L35 32 L44 28 Z" fill="{EAR}" stroke-width="2.5"/>',
        f'<path d="M87 18 L76 28 L85 32 Z" fill="{EAR}" stroke-width="2.5"/>',
        f'<circle cx="47" cy="54" r="{max(7, l - 3)}" fill="{c["eye"]}" stroke-width="3"/>',
        f'<circle cx="{47 + c["dx"]}" cy="56" r="3.5" fill="{INK}" stroke="none"/>',
        f'<circle cx="73" cy="54" r="{max(7, r - 3)}" fill="{c["eye"]}" stroke-width="3"/>',
        f'<circle cx="{73 - c["dx"]}" cy="56" r="3.5" fill="{INK}" stroke="none"/>',
        third,
        f'<path d="M57 64 L63 64 L60 68 Z" fill="{NOSE}" stroke-width="2"/>',
    ])


def sleep(c):
    """Lying cat with closed eyes, 170x92 (naps on a selected card)."""
    return "\n".join([
        f'<path d="M20 84 C8 60 22 30 60 26 C92 22 128 26 146 44 C160 58 158 80 150 86 Z" fill="{c["fur"]}" stroke-width="4"/>',
        f'<path d="M150 86 C166 78 170 60 160 50" stroke-width="7"/>',
        f'<path d="M150 86 C166 78 170 60 160 50" stroke="{c["fur"]}" stroke-width="2"/>',
        f'<path d="M26 46 C22 36 22 24 26 14 C34 20 40 26 44 32 C50 30 58 30 64 32 C68 26 74 20 82 16 '
        f'C85 26 84 38 80 48 C86 60 80 76 66 80 C52 84 34 82 26 74 C18 66 20 54 26 46 Z" fill="{c["fur"]}" stroke-width="4"/>',
        f'<path d="M29 22 L31 34 L40 30 Z" fill="{EAR}" stroke-width="2.5"/>',
        f'<path d="M78 24 L68 30 L76 35 Z" fill="{EAR}" stroke-width="2.5"/>',
        f'<path d="M34 56 C38 60 44 60 48 56 M58 55 C62 59 68 59 72 55" stroke="{CREAM if c["fur"] in ("#3b3734", "#5c5a57") else INK}" stroke-width="3"/>',
        f'<path d="M50 66 L56 66 L53 70 Z" fill="{NOSE}" stroke-width="2"/>',
        '<path d="M100 18 l8 -6 M104 6 h8 l-8 8 h8" stroke-width="2.5"/>',
    ])


def paw(c):
    """One paw reaching from the bottom right, 120x120."""
    return "\n".join([
        f'<path d="M14 30 C10 14 26 4 40 12 L112 70 L84 110 Z" fill="{c["fur"]}" stroke-width="4"/>',
        f'<ellipse cx="26" cy="24" rx="18" ry="15" fill="{c["fur"]}" stroke-width="4"/>',
        f'<ellipse cx="25" cy="27" rx="7" ry="6" fill="{EAR}" stroke-width="2.5"/>',
        f'<circle cx="13" cy="15" r="4" fill="{EAR}" stroke-width="2"/>',
        f'<circle cx="22" cy="10" r="4" fill="{EAR}" stroke-width="2"/>',
        f'<circle cx="33" cy="11" r="4" fill="{EAR}" stroke-width="2"/>',
    ])


SMILE = "M51 86 C55 91 60 89 61.5 84 C63 89 68 91 72 86"
POWER = {   # action: (cat, eyes path or None for open eyes, mouth, extra path)
    "lock":     ("gribouille", None, SMILE, ""),
    "logout":   ("pate", "M36 58 L48 64 L36 70 M86 58 L74 64 L86 70", SMILE, ""),
    "suspend":  ("moumoute", "M34 62 C38 68 50 68 54 62 M68 60 C72 66 84 66 88 60",
                 "M55 88 C58 90 64 90 67 88", "M96 14 h12 l-12 12 h12 M84 2 h8 l-8 8 h8"),
    "reboot":   ("biscotte", "M45 64 m-2 0 a2 2 0 1 1 4 0 a5 5 0 1 1 -9 -1 a9 9 0 1 1 15 4 "
                 "M77 62 m-2 0 a2 2 0 1 1 4 0 a5 5 0 1 1 -9 -1 a9 9 0 1 1 15 4",
                 "M53 89 C57 86 61 92 65 88 C67 86 69 89 71 88", ""),
    "shutdown": ("clafoutis", "M34 64 H54 M68 62 H88", "M54 88 H69", ""),
}


def power_face(action):
    name, eyes, mouth, extra = POWER[action]
    c = dict(CATS[name])
    c["traits"] = tuple(t for t in c["traits"] if t not in ("tongue",))
    body = face(c, eyes_open=eyes is None, eyes_path=eyes, mouth=mouth)
    if extra:
        body += f'\n<path d="{extra}" stroke-width="3.5"/>'
    return svg(120, 120, body)


def gamer():
    c = CATS["clafoutis"]
    body = "\n".join([
        f'<path d="{HEAD}" fill="{c["fur"]}" stroke-width="5"/>',
        '<path d="M24 40 C40 30 80 30 98 40" stroke="#c4573e" stroke-width="9"/>',
        '<path d="M14 70 C8 56 10 46 20 44 M106 68 C112 54 110 44 100 42" stroke-width="5"/>',
        '<rect x="6" y="62" width="14" height="22" rx="5" fill="#d9a12e" stroke-width="4"/>',
        '<rect x="100" y="60" width="14" height="22" rx="5" fill="#d9a12e" stroke-width="4"/>',
        '<path d="M34 62 L54 66 M68 64 L88 60" stroke="#c9e06a" stroke-width="6"/>',
        f'<path d="M57 78 L66 78 L61.5 83 Z" fill="{NOSE}" stroke-width="3"/>',
        '<path d="M52 88 C58 92 66 92 72 88" stroke="#f1e7cf" stroke-width="3"/>',
    ])
    return svg(120, 120, body)


def basket():
    def head_at(name, tx, ty, s):
        return f'<g transform="translate({tx} {ty}) scale({s})">\n{face(CATS[name], whiskers=False)}\n</g>'
    body = "\n".join([
        head_at("gribouille", 26, 40, 0.95),
        head_at("moumoute", 110, 10, 1.05),
        head_at("biscotte", 206, 44, 0.92),
        '<path d="M20 160 H320 L296 284 H44 Z" fill="#b88a4e" stroke-width="5"/>',
        '<path d="M30 196 H312 M36 232 H304 M42 264 H298" stroke-width="3"/>',
        '<path d="M80 162 L70 282 M140 162 L134 282 M200 162 L204 282 M260 162 L268 282" stroke-width="3"/>',
        '<path d="M14 152 C14 144 20 140 28 140 H312 C320 140 326 144 326 152 V164 H14 Z" fill="#c99a5c" stroke-width="5"/>',
    ])
    return svg(340, 300, body)


def write(name, text):
    path = os.path.join(HERE, name)
    with open(path, "w") as f:
        f.write(text)
    return path


def main():
    files = []
    for name, c in CATS.items():
        files.append(write(f"head-{name}.svg", svg(120, 120, face(c))))
        files.append(write(f"peek-{name}.svg", svg(120, 130, face(c) + "\n" + paws(c["fur"], 117))))
        files.append(write(f"sit-{name}.svg", svg(120, 110, sit(c))))
        files.append(write(f"sleep-{name}.svg", svg(170, 92, sleep(c))))
        files.append(write(f"paw-{name}.svg", svg(120, 120, paw(c))))
    for action in POWER:
        files.append(write(f"power-{action}.svg", power_face(action)))
    files.append(write("gamer.svg", gamer()))
    files.append(write("basket.svg", basket()))

    rsvg = shutil.which("rsvg-convert")
    for f in files:
        if rsvg:
            subprocess.run([rsvg, "-z", "2", "-o", f[:-4] + ".png", f], check=False)
    print(f"{len(files)} cats drawn in {HERE}" + ("" if rsvg else " (no rsvg-convert: SVG only)"))


if __name__ == "__main__":
    main()
