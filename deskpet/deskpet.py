#!/usr/bin/env python3
# =============================================================================
#  deskpet/deskpet.py — the cat peeking up from the bottom of the screen
# =============================================================================
#  A tiny GTK 4 layer-shell surface anchored bottom-right: the head of
#  DESKTOP_PET_CAT (hyprtheme/skins/encre/cats/head-<cat>.svg) cut by the
#  screen edge, as in the "Mew-Main" mockup. Click it: a speech bubble
#  ("Mrrp ?", "Miaou."…) pops up for ~2.5 s (parchment card, ink border,
#  Caveat Brush).
#
#  Layer: BOTTOM — above the wallpaper, under every window. The cat lives on
#  the desktop: it shows on empty / roomy workspaces and never covers the
#  bottom-right corner of your windows (terminal prompt, scrollbars, buttons)
#  nor steals their clicks. `--layer top` puts it above windows instead.
#  Exclusive zone 0: it sits above a bottom bar instead of under it.
#  Keyboard mode NONE (never takes the focus); the input region is only the
#  visible part of the cat, the rest of the surface lets clicks through.
#
#  Started / stopped by hypr/scripts/deskpet.sh (single instance, pid file),
#  only when DESKTOP_PET=true. Colors come from the current palette
#  (~/.cache/inkpaw/palette.json, written by hyprtheme/theme.sh).
#  Usage: deskpet.py [--layer bottom|top] [--cat <name>] [--say]   (--say: bubble at start, for tests)
# =============================================================================
import os
import sys

# gtk4-layer-shell must be loaded before libwayland: re-exec with LD_PRELOAD,
# then drop it so nothing started later inherits it.
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
import random
import re

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk4LayerShell", "1.0")
gi.require_foreign("cairo")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

HOME = os.path.expanduser("~")
PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "inkpaw")
CATS = os.path.join(PROJECT, "hyprtheme", "skins", "encre", "cats")

SIZE = 240          # drawn size of the head (the mockup's big cat)
VISIBLE = 166       # part above the screen edge: ears, three eyes, nose
BUBBLE_H = 92       # room above the head for the speech bubble
WIDTH = SIZE + 40   # a little room on the right for the tilted bubble
MARGIN_RIGHT = 110  # distance from the right edge of the screen
SAYINGS = ["Mrrp ?", "Miaou.", "…", "Prrrt.", "Mrraow !", "Miaou ?", "…prrr…", "Nya."]
SHOW_MS = 2600


# --- settings (hypr/settings.conf, then the runtime toggles) --------------------------
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
    """Material roles of the current theme (fallback: the parchment skin)."""
    roles = {"surface_container_lowest": "#fffaf0", "on_surface": "#2a2420"}
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


def css(p):
    return f"""
window.deskpet, window.deskpet > * {{ background: transparent; box-shadow: none; }}
.bubble {{
    background: {p['surface_container_lowest']};
    color: {p['on_surface']};
    border: 3px solid {p['on_surface']};
    border-radius: 20px 16px 22px 6px;
    padding: 4px 16px 6px 16px;
    font-family: "Caveat Brush", cursive;
    font-size: 26px;
    transform: rotate(-4deg);
}}
"""


def arg(name, default):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


# --- the pet --------------------------------------------------------------------------------
class Pet(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=None)
        self.conf = settings()
        self.hide_id = 0
        self.last = ""

    def cat_texture(self, scale):
        cat = arg("--cat", self.conf.get("DESKTOP_PET_CAT") or "gribouille")
        for name in (f"head-{cat}.svg", f"head-{cat}.png", "head-gribouille.svg", "head-gribouille.png"):
            path = os.path.join(CATS, name)
            if os.path.exists(path):
                px = SIZE * scale
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, px, px, True)
                h = min(pb.get_height(), VISIBLE * scale)
                ok, data = pb.new_subpixbuf(0, 0, pb.get_width(), h).save_to_bufferv("png", [], [])
                return Gdk.Texture.new_from_bytes(GLib.Bytes.new(data)) if ok else None
        return None

    def do_activate(self):
        prov = Gtk.CssProvider()
        prov.load_from_string(css(palette()))
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)

        win = Gtk.ApplicationWindow(application=self)
        win.add_css_class("deskpet")
        win.set_decorated(False)
        LayerShell.init_for_window(win)
        top = arg("--layer", "bottom") == "top"
        LayerShell.set_layer(win, LayerShell.Layer.TOP if top else LayerShell.Layer.BOTTOM)
        LayerShell.set_namespace(win, "deskpet")
        LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.NONE)
        LayerShell.set_exclusive_zone(win, 0)
        LayerShell.set_anchor(win, LayerShell.Edge.BOTTOM, True)
        LayerShell.set_anchor(win, LayerShell.Edge.RIGHT, True)
        LayerShell.set_margin(win, LayerShell.Edge.RIGHT, MARGIN_RIGHT)
        LayerShell.set_margin(win, LayerShell.Edge.BOTTOM, 0)
        self.win = win

        # Fixed-size surface: bubble zone on top, the cat's visible part at the bottom
        root = Gtk.Overlay()
        root.set_size_request(WIDTH, BUBBLE_H + VISIBLE)

        scale = 2 if any(m.get_scale_factor() > 1 for m in Gdk.Display.get_default().get_monitors()) else 1
        self.cat = Gtk.Picture()
        tex = self.cat_texture(scale)
        if tex:
            self.cat.set_paintable(tex)
        self.cat.set_content_fit(Gtk.ContentFit.FILL)
        self.cat.set_can_shrink(True)
        self.cat.set_size_request(SIZE, VISIBLE)
        self.cat.set_halign(Gtk.Align.START)
        self.cat.set_valign(Gtk.Align.END)
        self.cat.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        root.set_child(self.cat)

        self.label = Gtk.Label()
        self.bubble = Gtk.Box()
        self.bubble.add_css_class("bubble")
        self.bubble.append(self.label)
        self.bubble.set_halign(Gtk.Align.END)
        self.bubble.set_valign(Gtk.Align.START)
        self.bubble.set_margin_top(14)
        self.bubble.set_margin_end(4)
        self.bubble.set_visible(False)
        self.bubble.set_can_target(False)
        root.add_overlay(self.bubble)

        click = Gtk.GestureClick()
        click.connect("pressed", self.on_click)
        self.cat.add_controller(click)

        win.set_child(root)
        win.connect("map", lambda *_: GLib.idle_add(self.set_input_region))
        win.present()
        if "--say" in sys.argv:
            GLib.timeout_add(300, lambda: self.on_click() or False)

    def set_input_region(self):
        """Only the visible part of the cat takes clicks."""
        surf = self.win.get_surface()
        if surf is not None:
            # small inset: the transparent corners around the ears let clicks through
            r = cairo.RectangleInt(14, BUBBLE_H + 18, SIZE - 28, VISIBLE - 18)
            surf.set_input_region(cairo.Region(r))
        return False

    def on_click(self, *_):
        choices = [s for s in SAYINGS if s != self.last] or SAYINGS
        self.last = random.choice(choices)
        self.label.set_text(self.last)
        self.bubble.set_visible(True)
        if self.hide_id:
            GLib.source_remove(self.hide_id)
        self.hide_id = GLib.timeout_add(SHOW_MS + random.randint(-400, 400), self.hide_bubble)

    def hide_bubble(self):
        self.bubble.set_visible(False)
        self.hide_id = 0
        return False


if __name__ == "__main__":
    Pet().run([])
