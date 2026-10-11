#!/usr/bin/env python3
# =============================================================================
#  powermenu/powermenu.py — power menu of the "encre" skin (mockup Mew-Power)
# =============================================================================
#  A full-screen GTK 4 layer-shell overlay: dark ink veil, the title
#  "On fait quoi ?" in Caveat Brush, five tilted parchment cards (one cat face
#  per action, hyprtheme/skins/encre/cats/power-*.svg), each with its label and
#  a key chip, and the hint "Échap pour annuler · …" under the row.
#
#  ONE selection, shared by the keyboard and the mouse: hovering a card
#  selects it (the keyboard then continues from there) and the arrow keys /
#  Tab move it; the selected card is ochre, raised and has a bigger shadow.
#  (wlogout could not do that: its :hover and :focus are two different cards.)
#
#  Keys: ← → / Tab / Shift+Tab move · Enter or Space run the selected action ·
#        L E U R S run an action directly · Esc or a click on the veil closes.
#  Colors: current palette (~/.cache/inkpaw/palette.json, written by
#  hyprtheme/theme.sh); fonts: FONT_FAMILY / DISPLAY_FONT / MONO_FONT settings.
#  Resident (pylib/hyprapp.py): started hidden at login, opened / closed by
#  hypr/scripts/menus/power.sh through hypr/scripts/resident.sh (D-Bus, instant).
# =============================================================================
import os
import sys

# gtk4-layer-shell must be loaded before libwayland: re-exec with LD_PRELOAD,
# then drop it so the actions started from here don't inherit it.
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
import re
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "pylib"))
from hyprapp import ResidentOverlay  # noqa: E402

HOME = os.path.expanduser("~")
PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
CFG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "inkpaw")
CATS = os.path.join(PROJECT, "hyprtheme", "skins", "encre", "cats")
LOCK = os.path.join(PROJECT, "hypr", "scripts", "lock.sh")

TITLE = "On fait quoi ?"
HINT = "Échap pour annuler · le chat roux dort déjà"
# id, label, Nerd Font glyph, key, command, card tilt (deg) — same actions as wlogout/layout
ACTIONS = [
    ("lock",     "Verrouiller", "󰌾", "L", [LOCK],                                -2.0),
    ("logout",   "Déconnexion", "󰍃", "E", ["hyprctl", "dispatch", "hl.dsp.exit()"], 1.5),
    ("suspend",  "Veille",      "󰒲", "U", ["systemctl", "suspend"],                -3.0),
    ("reboot",   "Redémarrer",  "󰜉", "R", ["systemctl", "reboot"],                  2.0),
    ("shutdown", "Éteindre",    "󰐥", "S", ["systemctl", "poweroff"],               -1.0),
]
CARD_W, CARD_H, CAT = 220, 300, 160


# --- settings + palette -------------------------------------------------------------------
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
    """Material roles of the current theme (fallback: the parchment colors)."""
    roles = {"surface": "#f1e7cf", "surface_container_lowest": "#fffaf0", "on_surface": "#2a2420",
             "shadow": "#2a2420", "primary_container": "#d9a12e", "on_primary_container": "#2a2420"}
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


def css(p, s):
    font = s.get("FONT_FAMILY") or "Shantell Sans"
    display = s.get("DISPLAY_FONT") or font
    mono = s.get("MONO_FONT") or "monospace"
    tilts = "\n".join(
        f".card.c{i} {{ transform: rotate({t}deg); }}\n"
        f".card.c{i}.selected {{ transform: translateY(-18px) rotate({t}deg); }}"
        for i, (*_, t) in enumerate(ACTIONS))
    return f"""
window.powermenu {{ background: alpha({p['shadow']}, 0.55); }}
.title {{
    font-family: "{display}", cursive; font-size: 72px; color: {p['surface']};
    text-shadow: 4px 4px 0 {p['on_surface']}; transform: rotate(-2deg);
}}
.hint {{ font-family: "{font}", sans-serif; font-size: 16px; font-weight: 600; color: {p['surface']}; }}
.card {{
    background: {p['surface']}; color: {p['on_surface']};
    border: 3px solid {p['on_surface']};
    border-radius: 16px 22px 14px 20px;
    box-shadow: 4px 4px 0 {p['on_surface']};
    padding: 26px 16px 20px 16px;
    transition: background-color 120ms ease-out, box-shadow 120ms ease-out, transform 120ms ease-out;
}}
.card.selected {{ background: {p['primary_container']}; color: {p['on_primary_container']};
                  box-shadow: 7px 7px 0 {p['on_surface']}; }}
.card:focus-visible {{ outline: none; }}
.name {{ font-family: "{font}", sans-serif; font-size: 19px; font-weight: 700; }}
.glyph {{ font-size: 22px; }}
.key {{
    font-family: "{mono}", monospace; font-size: 14px; font-weight: 700;
    padding: 1px 10px; background: {p['surface_container_lowest']}; color: {p['on_surface']};
    border: 2.5px solid {p['on_surface']}; border-radius: 8px 10px 7px 9px;
}}
{tilts}
"""


# --- the menu (resident, see pylib/hyprapp.py) ------------------------------------------------
class PowerMenu(ResidentOverlay):
    NAMESPACE = "powermenu"

    def __init__(self):
        super().__init__("dev.inkpaw.PowerMenu")
        self.cards = []
        self.sel = 0

    def css(self):
        return css(palette(), settings())

    def build(self):
        self.cards = []
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=64,
                      halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        col.append(Gtk.Label(label=TITLE, css_classes=["title"]))
        row = Gtk.Box(spacing=34, halign=Gtk.Align.CENTER, valign=Gtk.Align.END)
        for i, (aid, name, glyph, key, cmd, _t) in enumerate(ACTIONS):
            row.append(self.card(i, aid, name, glyph, key))
        col.append(row)
        col.append(Gtk.Label(label=HINT, css_classes=["hint"]))
        self.select(0)
        return col

    def opened(self):
        self.select(0)

    def card(self, i, aid, name, glyph, key):
        btn = Gtk.Button(css_classes=["card", f"c{i}"], width_request=CARD_W, height_request=CARD_H)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        pic = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=False,
                          width_request=CAT, height_request=CAT, halign=Gtk.Align.CENTER, vexpand=True)
        for ext in ("svg", "png"):
            path = os.path.join(CATS, f"power-{aid}.{ext}")
            if os.path.exists(path):
                pic.set_filename(path)
                break
        box.append(pic)
        lab = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        lab.append(Gtk.Label(label=glyph, css_classes=["glyph"]))
        lab.append(Gtk.Label(label=name, css_classes=["name"]))
        box.append(lab)
        box.append(Gtk.Label(label=key, css_classes=["key"], halign=Gtk.Align.CENTER))
        btn.set_child(box)
        btn.connect("clicked", lambda _b, n=i: self.launch(n))
        # the mouse moves the same selection as the keyboard
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_a, n=i: self.select(n))
        btn.add_controller(motion)
        self.cards.append(btn)
        return btn

    def select(self, n):
        self.sel = n % len(self.cards)
        for i, c in enumerate(self.cards):
            (c.add_css_class if i == self.sel else c.remove_css_class)("selected")
        if self.cards[self.sel].get_root() is not None:
            self.cards[self.sel].grab_focus()

    def on_key(self, name, keyval, state):
        if name in ("Right", "Down") or (name == "Tab" and not state & Gdk.ModifierType.SHIFT_MASK):
            self.select(self.sel + 1)
        elif name in ("Left", "Up", "ISO_Left_Tab") or name == "Tab":
            self.select(self.sel - 1)
        elif name in ("Return", "KP_Enter", "space"):
            self.launch(self.sel)
        else:
            for i, (*_x, key, _cmd, _t) in enumerate(ACTIONS):
                if name.upper() == key:
                    self.select(i)
                    self.launch(i)
                    return True
            return False
        return True

    def inside(self, widget):
        return widget in self.cards

    def launch(self, n):
        cmd = ACTIONS[n][4]
        self.hide()
        # let the overlay disappear before locking / suspending
        GLib.timeout_add(120, lambda: subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL,
                                                       stderr=subprocess.DEVNULL) and False)


if __name__ == "__main__":
    sys.exit(PowerMenu().run(sys.argv))
