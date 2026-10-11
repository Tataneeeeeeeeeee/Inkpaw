#!/usr/bin/env python3
# =============================================================================
#  wallpicker/wallpicker.py — wallpaper selector of the "encre" skin (mockup Mew-Wallpapers)
# =============================================================================
#  A full-screen GTK 4 layer-shell overlay: a torn parchment band across the
#  screen, the title "Choisis un fond", a dashed filter and a counter, then a
#  row of photos taped on the band (tilted cards, the name in brush pen under
#  each one). The selected photo is ochre-framed and raised, and the black cat
#  naps on it.
#
#  Images: every jpg / jpeg / png / webp / gif of WALLPAPER_DIR (2 levels),
#  sorted. Thumbnails are cached in ~/.cache/inkpaw/thumbs-encre (rebuilt
#  when an image changes). Choosing one runs hyprtheme/theme.sh wallpaper
#  <image> (transition + new palette everywhere).
#  ONE selection for keyboard and mouse (hover selects; the row scrolls to keep
#  it in view): ← → move, Enter / click apply, type to filter, Esc clears the
#  filter then closes, a click outside the band closes.
#  Resident (pylib/hyprapp.py, thumbnails kept in memory): opened / closed by
#  hyprtheme/wallpaper-picker.sh under UI_SKIN=encre (SUPER+CTRL+W) through
#  hypr/scripts/resident.sh.
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

import hashlib
import json
import math
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

HOME = os.path.expanduser("~")
PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "inkpaw")
THUMBS = os.path.join(CACHE, "thumbs-encre")
THEME_SH = os.path.join(PROJECT, "hyprtheme", "theme.sh")
CATS = os.path.join(PROJECT, "hyprtheme", "skins", "encre", "cats")

TITLE = "Choisis un fond"
EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
PHOTO_W, PHOTO_H = 170, 240      # photo size inside a card
CAT_ROOM = 64                    # room above the cards for the napping cat
BAND_H = 600
TILTS = (-3, 2, -1.5, 2.5, -2, 1.5)
TAPES = (-5, 4)


# --- settings, palette, images ----------------------------------------------------------------
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
                into[m.group(1)] = v.replace("$HOME", HOME).replace("${HOME}", HOME)
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


def images(folder):
    out = []
    for root, dirs, files in os.walk(folder, followlinks=True):
        if os.path.relpath(root, folder).count(os.sep) >= 1 and root != folder:
            dirs[:] = []
        for f in files:
            if f.lower().endswith(EXTS):
                out.append(os.path.join(root, f))
    return sorted(out)


def label_of(path):
    """"09-synthwave-sunset.jpg" -> "synthwave sunset"."""
    name = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r"^\d+[-_ ]", "", name)
    return re.sub(r"[-_]+", " ", name)


def thumbnail(path):
    """Cached pixbuf PHOTO_W*2 wide (rebuilt when the image changes), or None."""
    os.makedirs(THUMBS, exist_ok=True)
    key = hashlib.md5(path.encode()).hexdigest()[:16]
    out = os.path.join(THUMBS, key + ".png")
    try:
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(path):
            return GdkPixbuf.Pixbuf.new_from_file(out)
        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, PHOTO_W * 3, PHOTO_H * 3, True)
        pb.savev(out, "png", [], [])
        return pb
    except (GLib.Error, OSError):
        return None


def rgb(hexcol, alpha=1.0):
    h = hexcol.lstrip("#")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, alpha


def draw_cover(cr, w, h, pb, ink):
    if pb is None:
        cr.set_source_rgba(*rgb(ink, 0.15))
        cr.paint()
        return
    k = max(w / pb.get_width(), h / pb.get_height())
    cr.translate((w - pb.get_width() * k) / 2, (h - pb.get_height() * k) / 2)
    cr.scale(k, k)
    Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
    cr.paint()


def draw_band(cr, w, h, paper, ink):
    """Parchment band with torn top and bottom edges (the mockup's wavy path)."""
    amp, step = 9, 70
    cr.move_to(0, amp * 1.5)
    x = 0
    i = 0
    while x < w:
        nx = min(w, x + step)
        cy = amp * (0.4 if i % 2 else 2.2)
        cr.curve_to(x + step * 0.35, cy, x + step * 0.65, amp * (2.2 if i % 2 else 0.4), nx, amp * 1.5)
        x, i = nx, i + 1
    cr.line_to(w, h - amp * 1.5)
    x, i = w, 0
    while x > 0:
        nx = max(0, x - step)
        cy = h - amp * (2.2 if i % 2 else 0.4)
        cr.curve_to(x - step * 0.35, cy, x - step * 0.65, h - amp * (0.4 if i % 2 else 2.2), nx, h - amp * 1.5)
        x, i = nx, i + 1
    cr.close_path()
    cr.set_source_rgba(*rgb(paper))
    cr.fill_preserve()
    cr.set_line_width(4)
    cr.set_line_join(1)
    cr.set_source_rgba(*rgb(ink))
    cr.stroke()


def css(p, s):
    font = s.get("FONT_FAMILY") or "Shantell Sans"
    display = s.get("DISPLAY_FONT") or font
    mono = s.get("MONO_FONT") or "monospace"
    ink = p["on_surface"]
    tilts = "\n".join(
        f".card.t{i} {{ transform: rotate({t}deg); }}\n"
        f".card.t{i}.selected {{ transform: translateY(-10px) rotate({t}deg); }}"
        for i, t in enumerate(TILTS))
    tapes = "\n".join(f".tape.t{i} {{ transform: rotate({t}deg); }}" for i, t in enumerate(TAPES))
    return f"""
window.wallpicker {{ background: alpha({p['shadow']}, 0.35); font-family: "{font}", sans-serif; color: {ink}; }}
.title {{ font-family: "{display}", cursive; font-size: 40px; transform: rotate(-2deg); }}
.filter {{
    background: transparent; color: {ink};
    border: 2.5px dashed {ink}; border-radius: 14px 10px 16px 12px;
    padding: 3px 8px; min-width: 300px; font-size: 14px;
}}
.count {{ font-family: "{mono}", monospace; font-weight: 700; font-size: 14px; }}
.card {{
    background: {p['surface_container_lowest']}; color: {ink};
    border: 3px solid {ink}; border-radius: 10px 14px 9px 13px;
    box-shadow: 4px 4px 0 {ink};
    padding: 10px 10px 8px 10px;
    transition: transform 120ms ease-out, background-color 120ms ease-out;
}}
.card.selected {{ background: {p['primary_container']}; color: {p['on_primary_container']};
                  box-shadow: 6px 6px 0 {ink}; }}
.card:focus-visible {{ outline: none; }}
.photo {{ border: 2.5px solid {ink}; border-radius: 6px 9px 5px 8px; }}
.name {{ font-family: "{display}", cursive; font-size: 21px; }}
.tape {{
    background: alpha({p['primary_container']}, 0.55);
    border: 2px solid alpha({ink}, 0.5);
    min-width: 70px; min-height: 22px;
}}
.empty {{ font-size: 15px; color: {p['on_surface_variant']}; }}
scrollbar {{ opacity: 0; }}
{tilts}
{tapes}
"""


# --- the picker --------------------------------------------------------------------------------
class WallPicker(ResidentOverlay):
    NAMESPACE = "wallpicker"

    def __init__(self):
        super().__init__("dev.inkpaw.WallPicker")
        self.cards, self.cats, self.cells, self.files, self.visible = [], [], [], [], []
        self.sel = 0
        self.ink = "#2a2420"
        self.pixbufs = {}      # (path, mtime) -> thumbnail, kept between openings

    def css(self):
        p = palette()
        self.ink, self.paper = p["on_surface"], p["surface"]
        return css(p, settings())

    def thumb(self, path):
        try:
            key = (path, os.path.getmtime(path))
        except OSError:
            return None
        if key not in self.pixbufs:
            self.pixbufs[key] = thumbnail(path)
        return self.pixbufs[key]

    def build(self):
        """Rebuilt at each opening: the folder's images and the current wallpaper."""
        s = settings()
        self.cards, self.cats, self.cells = [], [], []
        folder = s.get("WALLPAPER_DIR") or os.path.join(HOME, "Pictures", "wallpapers")
        self.files = images(folder)
        current = read_conf(os.path.join(STATE, "theme.conf"), {}).get("THEME_WALLPAPER", "")

        # band = torn paper drawn under the content
        band = self.band = Gtk.Overlay(valign=Gtk.Align.CENTER, height_request=BAND_H)
        paper = Gtk.DrawingArea(hexpand=True, vexpand=True)
        paper.set_draw_func(lambda _a, cr, w, h: draw_band(cr, w, h, self.paper, self.ink))
        band.set_child(paper)

        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, valign=Gtk.Align.CENTER)
        head = Gtk.Box(spacing=16, halign=Gtk.Align.CENTER)
        head.append(Gtk.Label(label=TITLE, css_classes=["title"]))
        self.filter = Gtk.SearchEntry(placeholder_text="Filtrer…", css_classes=["filter"], valign=Gtk.Align.CENTER)
        self.filter.connect("search-changed", lambda *_: self.apply_filter())
        head.append(self.filter)
        self.count = Gtk.Label(css_classes=["count"], valign=Gtk.Align.CENTER)
        head.append(self.count)
        col.append(head)

        self.row = Gtk.Box(spacing=26, margin_start=60, margin_end=60, margin_bottom=14)
        for i, path in enumerate(self.files):
            self.row.append(self.cell(i, path))
        if not self.files:
            self.row.append(Gtk.Label(label=f"Aucune image dans {folder}", css_classes=["empty"], hexpand=True))
        self.scroll = Gtk.ScrolledWindow(child=self.row, vscrollbar_policy=Gtk.PolicyType.NEVER,
                                         hscrollbar_policy=Gtk.PolicyType.EXTERNAL)
        self.scroll.set_size_request(-1, PHOTO_H + CAT_ROOM + 110)
        wheel = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.BOTH_AXES)
        wheel.connect("scroll", self.on_wheel)
        self.scroll.add_controller(wheel)
        col.append(self.scroll)
        band.add_overlay(col)

        self.visible = list(range(len(self.files)))
        self.start = self.files.index(current) if current in self.files else 0
        if self.files:
            self.select(self.start, scroll=False)
        self.update_count()
        return band

    def opened(self):
        self.filter.grab_focus()
        if self.files:
            GLib.timeout_add(120, lambda: self.scroll_to(self.sel) or False)   # once laid out: center it

    def cell(self, i, path):
        """Room for the cat + the taped card; returns the cell widget."""
        over = Gtk.Overlay()
        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_top=CAT_ROOM)
        btn = Gtk.Button(css_classes=["card", f"t{i % len(TILTS)}"])
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame = Gtk.Box(css_classes=["photo"], overflow=Gtk.Overflow.HIDDEN)
        area = Gtk.DrawingArea(content_width=PHOTO_W, content_height=PHOTO_H)
        pb = self.thumb(path)
        area.set_draw_func(lambda _a, cr, w, h, pb=pb: draw_cover(cr, w, h, pb, self.ink))
        frame.append(area)
        box.append(frame)
        box.append(Gtk.Label(label=label_of(path), css_classes=["name"], ellipsize=3, max_width_chars=14))
        btn.set_child(box)
        btn.connect("clicked", lambda _b, n=i: self.apply(n))
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_a, n=i: self.select(n, scroll=False))
        btn.add_controller(motion)
        holder.append(btn)
        over.set_child(holder)
        # a strip of tape over the card's top edge
        tape = Gtk.Box(css_classes=["tape", f"t{i % len(TAPES)}"], halign=Gtk.Align.CENTER,
                       valign=Gtk.Align.START, margin_top=CAT_ROOM - 12, can_target=False)
        over.add_overlay(tape)
        # the napping cat, shown on the selected card only
        cat = os.path.join(CATS, "sleep-clafoutis.svg")
        pic = None
        if os.path.exists(cat):
            pic = Gtk.Picture.new_for_filename(cat)
            pic.set_size_request(150, 81)
            pic.set_halign(Gtk.Align.CENTER)
            pic.set_valign(Gtk.Align.START)
            pic.set_margin_top(CAT_ROOM - 66)
            pic.set_can_target(False)
            pic.set_visible(False)
            over.add_overlay(pic)
        self.cards.append(btn)
        self.cats.append(pic)
        self.cells.append(over)
        return over

    # --- selection / filter ---
    def select(self, n, scroll=True):
        if not self.visible:
            return
        if n not in self.visible:
            n = self.visible[0]
        self.sel = n
        for i, c in enumerate(self.cards):
            on = i == n
            (c.add_css_class if on else c.remove_css_class)("selected")
            if self.cats[i] is not None:
                self.cats[i].set_visible(on)
        if scroll:
            self.scroll_to(n)
        self.update_count()

    def scroll_to(self, n):
        cell = self.cells[n]
        ok, bounds = cell.compute_bounds(self.row)
        if not ok:
            return
        adj = self.scroll.get_hadjustment()
        x, w = bounds.get_x(), bounds.get_width()
        page = adj.get_page_size()
        adj.set_value(max(0, min(adj.get_upper() - page, x + w / 2 - page / 2)))

    def move(self, step):
        if not self.visible:
            return
        k = self.visible.index(self.sel) if self.sel in self.visible else 0
        self.select(self.visible[(k + step) % len(self.visible)])

    def apply_filter(self):
        q = self.filter.get_text().strip().lower()
        self.visible = [i for i, f in enumerate(self.files) if not q or q in label_of(f).lower()]
        for i, cell in enumerate(self.cells):
            cell.set_visible(i in self.visible)
        if self.visible and self.sel not in self.visible:
            self.select(self.visible[0])
        self.update_count()

    def update_count(self):
        if not self.visible:
            self.count.set_label("0 / 0")
            return
        k = self.visible.index(self.sel) + 1 if self.sel in self.visible else 1
        self.count.set_label(f"{k} / {len(self.visible)}")

    # --- input ---
    def on_key(self, name, keyval, state):
        if name == "Escape":
            if not self.filter.get_text():
                return False                       # the base class closes
            self.filter.set_text("")
        elif name in ("Right", "Down", "Tab"):
            self.move(1)
        elif name in ("Left", "Up", "ISO_Left_Tab"):
            self.move(-1)
        elif name in ("Return", "KP_Enter"):
            if self.visible:
                self.apply(self.sel)
        else:
            return False
        return True

    def on_wheel(self, _ctl, dx, dy):
        adj = self.scroll.get_hadjustment()
        adj.set_value(adj.get_value() + (dx + dy) * 60)
        return True

    def inside(self, widget):
        return widget is self.band

    def apply(self, n):
        self.hide()
        subprocess.Popen([THEME_SH, "wallpaper", self.files[n]], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.exit(WallPicker().run(sys.argv))
