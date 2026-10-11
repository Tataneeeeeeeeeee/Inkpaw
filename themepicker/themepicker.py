#!/usr/bin/env python3
# =============================================================================
#  themepicker/themepicker.py — theme selector of the "encre" skin (mockup Mew-Themes)
# =============================================================================
#  A full-screen GTK 4 layer-shell overlay: a parchment sheet titled "Thèmes",
#  a grid of tilted cards. Each card shows a mini desktop drawn in the theme's
#  own colors (bar pills, a window, a card), its name in brush pen, a mode chip
#  (dynamique / clair / sombre) and five swatches. The first card is the
#  dynamic theme: the palette of your current wallpaper (its preview is the
#  wallpaper itself). The sitting cat follows the selected card; the selection
#  starts on the theme in use.
#
#  Themes: hyprtheme/static/*.json (colors, mode, name). Choosing one runs
#  hyprtheme/theme.sh static <name> (palette + its wallpaper); the dynamic card
#  runs theme.sh wallpaper <current wallpaper>.
#  ONE selection shared by keyboard and mouse (hover selects): arrows move,
#  Enter / click apply, Esc or a click outside the sheet closes.
#  Resident (pylib/hyprapp.py): opened / closed by hyprtheme/static-picker.sh
#  under UI_SKIN=encre (CTRL+ALT+T) through hypr/scripts/resident.sh.
# =============================================================================
import os
import sys

# gtk4-layer-shell must be loaded before libwayland: re-exec with LD_PRELOAD,
# then drop it so theme.sh (started from here) does not inherit it.
_LS = "/usr/lib/libgtk4-layer-shell.so"
if os.path.exists(_LS) and _LS not in os.environ.get("LD_PRELOAD", ""):
    os.environ["LD_PRELOAD"] = (_LS + " " + os.environ.get("LD_PRELOAD", "")).strip()
    os.execv(sys.executable, [sys.executable, "-I", os.path.realpath(__file__)] + sys.argv[1:])
_pre = [p for p in os.environ.get("LD_PRELOAD", "").split() if p != _LS]
if _pre:
    os.environ["LD_PRELOAD"] = " ".join(_pre)
else:
    os.environ.pop("LD_PRELOAD", None)

import json
import math
import warnings
import re
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk4LayerShell", "1.0")
gi.require_foreign("cairo")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "pylib"))
from hyprapp import ResidentOverlay  # noqa: E402

warnings.filterwarnings("ignore", category=DeprecationWarning)   # Texture.new_for_pixbuf (still the simplest)

HOME = os.path.expanduser("~")
PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "inkpaw")
STATIC = os.path.join(PROJECT, "hyprtheme", "static")
THEME_SH = os.path.join(PROJECT, "hyprtheme", "theme.sh")
CATS = os.path.join(PROJECT, "hyprtheme", "skins", "encre", "cats")

TITLE = "Thèmes"
HINT = "le thème dynamique suit le fond d'écran, les autres sont fixes"
COLS = 5
PREVIEW_W, PREVIEW_H = 250, 150
CAT_ROOM = 70             # room above each card (the cat of the theme in use sits there)
TILTS = (-1.2, 0.8, -0.5, 1.0, 0.6, -0.9, 1.1, -0.4, 0.7, -1.0)
MODE_FR = {"dark": "sombre", "light": "clair"}


# --- settings, palette, themes -----------------------------------------------------------
def read_conf(path, into):
    try:
        with open(path) as f:
            for line in f:
                m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
                if not m or line.lstrip().startswith("#"):
                    continue
                v = re.sub(r'\s+#.*$', "", m.group(2))
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                into[m.group(1)] = v
    except OSError:
        pass
    return into


def settings():
    s = read_conf(os.path.join(PROJECT, "hypr", "settings.conf"), {})
    return read_conf(os.path.join(STATE, "toggles.conf"), s)


def palette():
    roles = {"surface": "#f1e7cf", "surface_container_high": "#e2d3b0", "surface_container_lowest": "#fffaf0",
             "on_surface": "#2a2420", "on_surface_variant": "#4a4038", "shadow": "#2a2420",
             "primary_container": "#d9a12e", "on_primary_container": "#2a2420"}
    try:
        with open(os.path.join(CACHE, "palette.json")) as f:
            colors = json.load(f).get("colors", {})
        for k in roles:
            c = colors.get(k, {}).get("default", {}).get("color")
            if c:
                roles[k] = c
    except (OSError, ValueError, AttributeError):
        pass
    return roles


def themes():
    """[{id, name, mode, colors…}] — the dynamic entry first, then static/*.json by name."""
    state = read_conf(os.path.join(STATE, "theme.conf"), {})
    out = [{"id": "@wallpaper", "name": "Depuis le fond", "mode": "dynamique",
            "wallpaper": state.get("THEME_WALLPAPER", ""),
            "current": state.get("THEME_SOURCE") == "wallpaper"}]
    items = []
    for f in sorted(os.listdir(STATIC)):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(STATIC, f)) as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        c = d.get("colors", {})
        tid = f[:-5]
        items.append({
            "id": tid, "name": d.get("name", tid), "mode": MODE_FR.get(d.get("mode"), d.get("mode", "")),
            "bg": c.get("surface", "#222222"), "surface2": c.get("surface_container_high", c.get("surface", "#333333")),
            "primary": c.get("primary", "#888888"), "secondary": c.get("secondary", "#999999"),
            "tertiary": c.get("tertiary", "#aaaaaa"), "fg": c.get("on_surface", "#eeeeee"),
            "current": state.get("THEME_SOURCE") == "static" and state.get("THEME_STATIC") == tid,
        })
    return out + sorted(items, key=lambda t: t["name"].lower())


def rgb(hexcol, alpha=1.0):
    h = hexcol.lstrip("#")
    if len(h) >= 6:
        return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, alpha
    return 0.5, 0.5, 0.5, alpha


def rounded(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def draw_mini(cr, w, h, t):
    """Mini desktop in the theme's colors (mockup Mew-Themes)."""
    cr.set_source_rgba(*rgb(t["bg"]))
    cr.paint()
    s2, fg, pr, se, te = t["surface2"], t["fg"], t["primary"], t["secondary"], t["tertiary"]
    pad = 10
    # bar: three pills, the middle one with the active workspace
    for x, bw in ((pad, 46), (w - pad - 62, 62)):
        rounded(cr, x, pad, bw, 13, 6.5)
        cr.set_source_rgba(*rgb(s2))
        cr.fill()
    mx = w / 2 - 26
    rounded(cr, mx, pad, 52, 13, 6.5)
    cr.set_source_rgba(*rgb(s2))
    cr.fill()
    rounded(cr, mx + 4, pad + 3, 16, 7, 3.5)
    cr.set_source_rgba(*rgb(pr))
    cr.fill()
    for i in range(2):
        rounded(cr, mx + 24 + i * 12, pad + 3, 8, 7, 3.5)
        cr.set_source_rgba(*rgb(fg, 0.4))
        cr.fill()
    # focused window (primary border, text lines) + two smaller windows
    top = pad + 13 + 8
    ww = (w - 3 * pad) * 0.56
    hh = h - top - pad
    rounded(cr, pad, top, ww, hh, 7)
    cr.set_source_rgba(*rgb(s2))
    cr.fill_preserve()
    cr.set_line_width(2)
    cr.set_source_rgba(*rgb(pr))
    cr.stroke()
    for i, (frac, col, a) in enumerate(((0.7, pr, 1), (0.9, fg, 0.5), (0.55, se, 1), (0.8, fg, 0.5))):
        rounded(cr, pad + 8, top + 10 + i * 13, (ww - 16) * frac, 6, 3)
        cr.set_source_rgba(*rgb(col, a))
        cr.fill()
    rx = pad * 2 + ww
    rw = w - rx - pad
    half = (hh - pad / 2) / 2
    rounded(cr, rx, top, rw, half, 7)
    cr.set_source_rgba(*rgb(s2))
    cr.fill()
    rounded(cr, rx, top + half + pad / 2, rw, half, 7)
    cr.set_source_rgba(*rgb(s2))
    cr.fill()
    cr.arc(rx + rw / 2, top + half + pad / 2 + half / 2, min(rw, half) / 4, 0, 2 * math.pi)
    cr.set_source_rgba(*rgb(te))
    cr.fill()


def draw_cover(cr, w, h, pb, ink):
    """Wallpaper scaled to cover the preview (or plain ink when there is none)."""
    if pb is None:
        cr.set_source_rgba(*rgb(ink, 0.15))
        cr.paint()
        return
    k = max(w / pb.get_width(), h / pb.get_height())
    cr.translate((w - pb.get_width() * k) / 2, (h - pb.get_height() * k) / 2)
    cr.scale(k, k)
    Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
    cr.paint()


def draw_swatches(cr, w, h, t, ink):
    """Five ink-outlined swatches: background, primary, secondary, tertiary, text."""
    cols = (t["bg"], t["primary"], t["secondary"], t["tertiary"], t["fg"])
    gap = 5
    sw = (w - gap * (len(cols) - 1)) / len(cols)
    for i, c in enumerate(cols):
        x = i * (sw + gap)
        rounded(cr, x + 1, 1, sw - 2, h - 2, 5)
        cr.set_source_rgba(*rgb(c))
        cr.fill_preserve()
        cr.set_line_width(2)
        cr.set_source_rgba(*rgb(ink))
        cr.stroke()


def css(p, s):
    font = s.get("FONT_FAMILY") or "Shantell Sans"
    display = s.get("DISPLAY_FONT") or font
    ink = p["on_surface"]
    tilts = "\n".join(f".card.c{i} {{ transform: rotate({t}deg); }}" for i, t in enumerate(TILTS))
    return f"""
window.themepicker {{ background: alpha({p['shadow']}, 0.45); }}
.sheet {{
    background: {p['surface']}; color: {ink};
    border: 3px solid {ink}; border-radius: 16px 22px 14px 20px;
    box-shadow: 7px 7px 0 {ink};
    padding: 26px 32px 32px 32px;
    font-family: "{font}", sans-serif;
}}
.title {{ font-family: "{display}", cursive; font-size: 54px; transform: rotate(-1.5deg); }}
.hint {{ font-size: 14px; font-weight: 600; color: {p['on_surface_variant']}; }}
.card {{
    background: {p['surface_container_lowest']}; color: {ink};
    border: 3px solid {ink}; border-radius: 14px 18px 12px 16px;
    box-shadow: 3px 3px 0 {ink};
    padding: 10px;
}}
.card.selected {{ background: {p['primary_container']}; color: {p['on_primary_container']};
                  box-shadow: 6px 6px 0 {ink}; }}
.card:focus-visible {{ outline: none; }}
.preview {{ border: 2.5px solid {ink}; border-radius: 9px 12px 8px 11px; }}
.name {{ font-family: "{display}", cursive; font-size: 24px; }}
.mode {{
    font-size: 11px; font-weight: 700; padding: 1px 8px;
    background: {p['surface_container_lowest']}; color: {ink};
    border: 2px solid {ink}; border-radius: 8px 10px 7px 9px;
}}
{tilts}
"""


# --- the picker -------------------------------------------------------------------------------
class ThemePicker(ResidentOverlay):
    NAMESPACE = "themepicker"

    def __init__(self):
        super().__init__("dev.inkpaw.ThemePicker")
        self.cards, self.items, self.sel = [], [], 0
        self.cats = []         # one sitting cat per card, only the selected one visible
        self.ink = "#2a2420"

    def css(self):
        p = palette()
        self.ink = p["on_surface"]
        return css(p, settings())

    def build(self):
        """Rebuilt at each opening: current theme / wallpaper, theme files."""
        self.cards, self.cats = [], []
        self.items = themes()
        sheet = self.sheet = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22, css_classes=["sheet"],
                                     halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        head = Gtk.Box(spacing=16)
        head.append(Gtk.Label(label=TITLE, css_classes=["title"]))
        head.append(Gtk.Label(label="CTRL + ALT + T · " + HINT, css_classes=["hint"], valign=Gtk.Align.CENTER))
        sheet.append(head)
        grid = Gtk.Grid(row_spacing=0, column_spacing=22, column_homogeneous=True)
        for i, t in enumerate(self.items):
            grid.attach(self.cell(self.card(i, t), t.get("current")), i % COLS, i // COLS, 1, 1)
        sheet.append(grid)
        self.select(next((i for i, t in enumerate(self.items) if t.get("current")), 0))
        return sheet

    def opened(self):
        self.select(self.sel)

    def card(self, i, t):
        btn = Gtk.Button(css_classes=["card", f"c{i % len(TILTS)}"])
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        frame = Gtk.Box(css_classes=["preview"], overflow=Gtk.Overflow.HIDDEN, hexpand=True)
        area = Gtk.DrawingArea(content_width=PREVIEW_W, content_height=PREVIEW_H, hexpand=True)
        if t["id"] == "@wallpaper":
            try:          # the wallpaper itself, cover-cropped (cairo: fixed natural size)
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(t["wallpaper"], PREVIEW_W * 2, -1, True)
            except (GLib.Error, TypeError):
                pb = None
            area.set_draw_func(lambda _a, cr, w, h, pb=pb: draw_cover(cr, w, h, pb, self.ink))
        else:
            area.set_draw_func(lambda _a, cr, w, h, t=t: draw_mini(cr, w, h, t))
        frame.append(area)
        box.append(frame)
        line = Gtk.Box(spacing=8)
        line.append(Gtk.Label(label=t["name"], css_classes=["name"], xalign=0, hexpand=True, ellipsize=3))
        line.append(Gtk.Label(label=t["mode"], css_classes=["mode"], valign=Gtk.Align.CENTER))
        box.append(line)
        if t["id"] != "@wallpaper":
            sw = Gtk.DrawingArea(content_width=PREVIEW_W, content_height=18, hexpand=True)
            sw.set_draw_func(lambda _a, cr, w, h, t=t: draw_swatches(cr, w, h, t, self.ink))
            box.append(sw)
        btn.set_child(box)
        btn.connect("clicked", lambda _b, n=i: self.apply(n))
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_a, n=i: self.select(n))
        btn.add_controller(motion)
        self.cards.append(btn)
        return btn

    def cell(self, card, current):
        """Grid cell: room above every card for the sitting cat, which follows the
        selected card (shown by select())."""
        over = Gtk.Overlay()
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_top=CAT_ROOM)
        col.append(card)
        over.set_child(col)
        path = os.path.join(CATS, "sit-moumoute.svg")
        if os.path.exists(path):
            pic = Gtk.Picture.new_for_filename(path)
            pic.set_content_fit(Gtk.ContentFit.CONTAIN)
            pic.set_size_request(96, 88)
            pic.set_halign(Gtk.Align.CENTER)
            pic.set_valign(Gtk.Align.START)
            pic.set_can_target(False)
            pic.set_visible(False)
            over.add_overlay(pic)
            self.cats.append(pic)
        else:
            self.cats.append(None)
        return over

    def select(self, n):
        self.sel = n % len(self.cards)
        for i, c in enumerate(self.cards):
            (c.add_css_class if i == self.sel else c.remove_css_class)("selected")
            if i < len(self.cats) and self.cats[i] is not None:
                self.cats[i].set_visible(i == self.sel)      # the cat sits on the selection
        if self.cards[self.sel].get_root() is not None:
            self.cards[self.sel].grab_focus()

    def on_key(self, name, keyval, state):
        n = len(self.cards)
        if name in ("Right", "Tab"):
            self.select(self.sel + 1)
        elif name in ("Left", "ISO_Left_Tab"):
            self.select(self.sel - 1)
        elif name == "Down":
            self.select(min(self.sel + COLS, n - 1))
        elif name == "Up":
            self.select(max(self.sel - COLS, 0))
        elif name in ("Return", "KP_Enter", "space"):
            self.apply(self.sel)
        else:
            return False
        return True

    def inside(self, widget):
        return widget is self.sheet

    def apply(self, n):
        t = self.items[n]
        self.hide()
        if t["id"] == "@wallpaper":
            if not t.get("wallpaper"):
                return
            cmd = [THEME_SH, "wallpaper", t["wallpaper"]]
        else:
            cmd = [THEME_SH, "static", t["id"]]
        subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.exit(ThemePicker().run(sys.argv))
