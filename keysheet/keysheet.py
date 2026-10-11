#!/usr/bin/env python3
# =============================================================================
#  keysheet/keysheet.py — keybind cheat sheet of the "encre" skin (mockup Mew-Keys)
# =============================================================================
#  A full-screen GTK 4 layer-shell overlay: a big parchment sheet titled
#  "Pense-bête des raccourcis", a filter field, and one card per category
#  (Lancer · Fenêtres · Espaces · Captures & médias · Système) with a colored,
#  tilted title chip and one row per action: the action in French + its keys
#  drawn as keycaps. A cat naps on the top edge of the sheet.
#
#  The binds are read live from `hyprctl binds -j` (every bind of
#  hypr/conf/keybinds/*.lua has a description). CATEGORY below files each
#  description in a card and translates it; families are folded into one row
#  ("Focus workspace 1…10" → "Aller à l'espace 1…0", "Focus left/right…" →
#  "Focus ← → ↑ ↓"). An unknown description lands in "Système" as is.
#
#  Keys: type to filter · Esc or a click outside the sheet closes.
#  Colors: current palette (~/.cache/inkpaw/palette.json); fonts:
#  FONT_FAMILY / DISPLAY_FONT / MONO_FONT. Resident (pylib/hyprapp.py): opened /
#  closed by hypr/scripts/menus/keybindings.sh through hypr/scripts/resident.sh.
# =============================================================================
import os
import sys

# gtk4-layer-shell must be loaded before libwayland: re-exec with LD_PRELOAD,
# then drop it from the environment.
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
from gi.repository import Gtk  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "pylib"))
from hyprapp import ResidentOverlay  # noqa: E402

HOME = os.path.expanduser("~")
PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "inkpaw")
CATS = os.path.join(PROJECT, "hyprtheme", "skins", "encre", "cats")

TITLE = "Pense-bête des raccourcis"
HINT_KEYS = ["SUPER", "CTRL", "K"]

# Cards, left to right: (id, title, fill color role or fixed color)
CARDS = [
    ("launch",  "Lancer",            "primary_container"),
    ("windows", "Fenêtres",          "secondary_container"),
    ("spaces",  "Espaces",           "tertiary_container"),
    ("media",   "Captures & médias", "#e8a0b4"),
    ("system",  "Système",           "error"),
]

# description (exact, or a family pattern) -> (card, French label)
CATEGORY = {
    "Terminal": ("launch", "Terminal"),
    "Browser": ("launch", "Navigateur"),
    "File manager": ("launch", "Fichiers"),
    "Calculator": ("launch", "Calculatrice"),
    "Discord": ("launch", "Discord"),
    "Spotify": ("launch", "Spotify"),
    "Microsoft Teams": ("launch", "Teams"),
    "Spotlight search": ("launch", "Recherche"),
    "Clipboard history": ("launch", "Presse-papiers"),
    "Emoji & symbol picker": ("launch", "Émojis et symboles"),
    "AI assistant (chat panel)": ("launch", "Assistant IA"),
    "Settings": ("launch", "Réglages"),
    "Notifications": ("launch", "Notifications"),

    "Close active window": ("windows", "Fermer"),
    "Kill active window process": ("windows", "Tuer le processus"),
    "Toggle fullscreen": ("windows", "Plein écran"),
    "Toggle maximize": ("windows", "Agrandir"),
    "Toggle floating": ("windows", "Flottante"),
    "Toggle floating for all windows of workspace": ("windows", "Tout flottant (espace)"),
    "Toggle floating + pinned": ("windows", "Flottante + épinglée"),
    "Toggle split": ("windows", "Changer la division"),
    "Swap split": ("windows", "Inverser la division"),
    "Toggle window group": ("windows", "Grouper"),
    "Focus *dir": ("windows", "Focus"),
    "Swap window *dir": ("windows", "Échanger"),
    "Grow width": ("windows", "Élargir"),
    "Shrink width": ("windows", "Rétrécir"),
    "Grow height": ("windows", "Allonger"),
    "Shrink height": ("windows", "Raccourcir"),
    "Move window (drag)": ("windows", "Déplacer (glisser)"),
    "Resize window (drag)": ("windows", "Redimensionner (glisser)"),

    "Focus workspace *n": ("spaces", "Aller à l'espace"),
    "Move window to workspace *n": ("spaces", "Envoyer vers l'espace"),
    "Next workspace": ("spaces", "Espace suivant"),
    "Previous workspace": ("spaces", "Espace précédent"),
    "Toggle scratchpad": ("spaces", "Bloc-notes caché"),
    "Send window to scratchpad": ("spaces", "Envoyer au bloc-notes"),

    "Screenshot area → annotate": ("media", "Capture de zone + annotation"),
    "Screenshot menu": ("media", "Menu capture"),
    "Instant area screenshot": ("media", "Capture de zone"),
    "Instant full-screen screenshot": ("media", "Capture de l'écran"),
    "Extract text from an area (OCR)": ("media", "Texte d'une zone (OCR)"),
    "Raise volume": ("media", "Volume +"),
    "Lower volume": ("media", "Volume −"),
    "Mute audio": ("media", "Couper le son"),
    "Mute microphone": ("media", "Couper le micro"),
    "Increase brightness": ("media", "Luminosité +"),
    "Decrease brightness": ("media", "Luminosité −"),
    "Play / pause": ("media", "Lecture / pause"),
    "Next track": ("media", "Piste suivante"),
    "Previous track": ("media", "Piste précédente"),

    "Lock screen": ("system", "Verrouiller"),
    "Power menu": ("system", "Alimentation"),
    "Reload Hyprland config": ("system", "Recharger Hyprland"),
    "Keybindings cheat sheet": ("system", "Ce pense-bête"),
    "Monitor profiles": ("system", "Profils d'écrans"),
    "Toggle Do Not Disturb": ("system", "Ne pas déranger"),
    "Wallpaper selector": ("system", "Fond d'écran"),
    "Random wallpaper": ("system", "Fond au hasard"),
    "Toggle light / dark mode": ("system", "Clair / sombre"),
    "Static theme selector": ("system", "Thèmes"),
    "Toggle status bar": ("system", "Barre on / off"),
    "Restart status bar": ("system", "Redémarrer la barre"),
    "Toggle animations": ("system", "Animations on / off"),
    "Toggle game mode": ("system", "Mode jeu"),
    "Toggle night light (hyprsunset)": ("system", "Veilleuse"),
}
HIDDEN = {"Lid closed", "Lid opened"}

# AZERTY digit row: keysym -> digit; other keys -> short labels
DIGITS = {"ampersand": "1", "eacute": "2", "quotedbl": "3", "apostrophe": "4", "parenleft": "5",
          "minus": "6", "egrave": "7", "underscore": "8", "ccedilla": "9", "agrave": "0"}
KEYS = {"RETURN": "Entrée", "SPACE": "Espace", "PRINT": "Impr", "ESCAPE": "Échap", "TAB": "Tab",
        "LEFT": "←", "RIGHT": "→", "UP": "↑", "DOWN": "↓",
        "MOUSE:272": "clic gauche", "MOUSE:273": "clic droit",
        "MOUSE_DOWN": "molette ↓", "MOUSE_UP": "molette ↑",
        "XF86AUDIORAISEVOLUME": "Vol +", "XF86AUDIOLOWERVOLUME": "Vol −", "XF86AUDIOMUTE": "Muet",
        "XF86AUDIOMICMUTE": "Micro", "XF86MONBRIGHTNESSUP": "Lum +", "XF86MONBRIGHTNESSDOWN": "Lum −",
        "XF86AUDIOPLAY": "▶❚❚", "XF86AUDIOPAUSE": "▶❚❚", "XF86AUDIONEXT": "⏭", "XF86AUDIOPREV": "⏮"}
DIRS = {"left": "←", "right": "→", "up": "↑", "down": "↓"}


# --- settings + palette ------------------------------------------------------------------
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
             "primary_container": "#d9a12e", "secondary_container": "#8fa34b",
             "tertiary_container": "#7e9cc0", "error": "#c4573e", "on_primary_container": "#2a2420"}
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


# --- binds -> rows ---------------------------------------------------------------------------
def mods(mask):
    names = [(64, "SUPER"), (4, "CTRL"), (8, "ALT"), (1, "SHIFT")]
    return [n for bit, n in names if mask & bit]


def key_name(key):
    if key in DIGITS:
        return DIGITS[key]
    up = key.upper()
    return KEYS.get(up, up if len(up) > 1 else up)


def load_rows():
    """{card: [(label, [combo, …]), …]} from the live binds, families folded."""
    try:
        binds = json.loads(subprocess.run(["hyprctl", "binds", "-j"], capture_output=True,
                                          text=True, timeout=3).stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        binds = []
    rows, order = {}, []          # (card, label) -> list of combos
    for b in binds:
        desc = (b.get("description") or "").strip()
        if not desc or desc in HIDDEN:
            continue
        key = b.get("key", "")
        combo = mods(b.get("modmask", 0))
        m_num = re.match(r"^(.*) (\d+)$", desc)
        m_dir = re.match(r"^(.*) (left|right|up|down)$", desc)
        if m_num and f"{m_num.group(1)} *n" in CATEGORY:
            card, label = CATEGORY[f"{m_num.group(1)} *n"]
            combo = combo + ["1…0"]                    # one row for the whole digit row
        elif m_dir and f"{m_dir.group(1)} *dir" in CATEGORY:
            card, label = CATEGORY[f"{m_dir.group(1)} *dir"]
            combo = combo + ["← → ↑ ↓"]
        else:
            card, label = CATEGORY.get(desc, ("system", desc))
            combo = combo + [key_name(key)]
        k = (card, label)
        if k not in rows:
            rows[k] = []
            order.append(k)
        if combo not in rows[k]:
            rows[k].append(combo)
    out = {c[0]: [] for c in CARDS}
    for card, label in order:
        out.setdefault(card, []).append((label, rows[(card, label)][:2]))
    return out


def css(p, s):
    font = s.get("FONT_FAMILY") or "Shantell Sans"
    display = s.get("DISPLAY_FONT") or font
    mono = s.get("MONO_FONT") or "monospace"
    ink = p["on_surface"]
    chips = "\n".join(f".chip.{cid} {{ background: {p.get(col, col)}; }}" for cid, _t, col in CARDS)
    tilts = "\n".join(f".card.c{i} {{ transform: rotate({t}deg); }}"
                      for i, t in enumerate((-0.6, 0.5, -0.4, 0.6, -0.5)))
    return f"""
window.keysheet {{ background: alpha({p['shadow']}, 0.45); }}
.sheet {{
    background: {p['surface']}; color: {ink};
    border: 3px solid {ink}; border-radius: 16px 22px 14px 20px;
    box-shadow: 7px 7px 0 {ink};
    padding: 26px 34px 30px 34px;
    font-family: "{font}", sans-serif;
}}
.title {{ font-family: "{display}", cursive; font-size: 54px; transform: rotate(-1.5deg); }}
.hint {{ font-size: 14px; font-weight: 600; color: {p['on_surface_variant']}; }}
.key {{
    /* the mono font has no arrows / media glyphs: fall back to the UI font, then DejaVu */
    font-family: "{mono}", "{font}", "DejaVu Sans Mono", monospace; font-size: 13px; font-weight: 700;
    padding: 1px 7px; min-width: 14px;
    background: {p['surface_container_lowest']}; color: {ink};
    border: 2.5px solid {ink}; border-bottom-width: 4px; border-radius: 7px 9px 6px 8px;
}}
.plus {{ font-size: 11px; font-weight: 700; color: {p['on_surface_variant']}; }}
.or {{ font-size: 11px; font-weight: 600; color: {p['on_surface_variant']}; margin: 0 2px; }}
.filter {{
    background: transparent; color: {ink};
    border: 2.5px dashed {ink}; border-radius: 12px 9px 14px 10px;
    padding: 4px 8px; min-width: 260px; font-size: 14px;
}}
.card {{
    background: {p['surface_container_lowest']};
    border: 3px solid {ink}; border-radius: 14px 18px 12px 16px;
    padding: 14px;
}}
.chip {{
    font-family: "{display}", cursive; font-size: 28px; color: {ink};
    padding: 0 10px; border: 2.5px solid {ink}; border-radius: 10px 13px 9px 12px;
    transform: rotate(-2deg);
}}
.row {{ padding: 4px 0; border-bottom: 2px dashed alpha({ink}, 0.2); }}
.act {{ font-size: 13.5px; font-weight: 600; color: {ink}; }}
.empty {{ font-size: 13px; color: {p['on_surface_variant']}; }}
{chips}
{tilts}
"""


# --- the sheet ------------------------------------------------------------------------------
class KeySheet(ResidentOverlay):
    NAMESPACE = "keysheet"

    def __init__(self):
        super().__init__("dev.inkpaw.KeySheet")
        self.rows = []         # (row widget, card id, lowercase search text)
        self.cards = {}

    def css(self):
        return css(palette(), settings())

    def build(self):
        """Rebuilt at each opening: the binds are read live."""
        self.rows, self.cards = [], {}
        sheet = self.sheet = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, css_classes=["sheet"],
                                     margin_top=96, margin_bottom=56, margin_start=70, margin_end=70)
        head = Gtk.Box(spacing=18)
        head.append(Gtk.Label(label=TITLE, css_classes=["title"]))
        hint = Gtk.Box(spacing=5, valign=Gtk.Align.CENTER)
        hint.append(Gtk.Label(label="ouvert avec", css_classes=["hint"]))
        hint.append(self.combo(HINT_KEYS))
        head.append(hint)
        head.append(Gtk.Box(hexpand=True))
        self.filter = Gtk.SearchEntry(placeholder_text="Filtrer…", css_classes=["filter"], valign=Gtk.Align.CENTER)
        self.filter.connect("search-changed", lambda *_: self.apply_filter())
        head.append(self.filter)
        sheet.append(head)

        grid = Gtk.Box(spacing=20, homogeneous=True, vexpand=True)
        data = load_rows()
        for i, (cid, title, _col) in enumerate(CARDS):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["card", f"c{i}"])
            card.append(Gtk.Label(label=title, css_classes=["chip", cid], halign=Gtk.Align.START))
            body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            for label, combos in data.get(cid, []):
                row = self.row(label, combos)
                body.append(row)
                text = (label + " " + " ".join(" ".join(c) for c in combos)).lower()
                self.rows.append((row, cid, text))
            card.append(Gtk.ScrolledWindow(child=body, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER))
            self.cards[cid] = card
            grid.append(card)
        sheet.append(grid)

        # a cat napping on the top edge of the sheet
        over = Gtk.Overlay(child=sheet)
        cat = os.path.join(CATS, "sleep-moumoute.svg")
        if os.path.exists(cat):
            pic = Gtk.Picture.new_for_filename(cat)
            pic.set_can_shrink(False)
            pic.set_halign(Gtk.Align.END)
            pic.set_valign(Gtk.Align.START)
            pic.set_margin_end(170)
            pic.set_margin_top(96 - 86)            # its belly on the sheet's top border
            pic.set_can_target(False)
            over.add_overlay(pic)
        return over

    def opened(self):
        self.filter.grab_focus()

    def combo(self, keys):
        box = Gtk.Box(spacing=3, valign=Gtk.Align.CENTER)
        for i, k in enumerate(keys):
            if i:
                box.append(Gtk.Label(label="+", css_classes=["plus"]))
            box.append(Gtk.Label(label=k, css_classes=["key"]))
        return box

    def row(self, label, combos):
        row = Gtk.Box(spacing=8, css_classes=["row"])
        row.append(Gtk.Label(label=label, xalign=0, hexpand=True, wrap=True, css_classes=["act"]))
        keys = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, halign=Gtk.Align.END)
        for i, c in enumerate(combos):
            line = Gtk.Box(spacing=3, halign=Gtk.Align.END)
            if i:
                line.append(Gtk.Label(label="ou", css_classes=["or"]))
            line.append(self.combo(c))
            keys.append(line)
        row.append(keys)
        return row

    def apply_filter(self):
        q = self.filter.get_text().strip().lower()
        shown = {cid: 0 for cid in self.cards}
        for row, cid, text in self.rows:
            ok = not q or q in text
            row.set_visible(ok)
            shown[cid] += ok
        for cid, card in self.cards.items():
            card.set_visible(shown[cid] > 0)

    def on_key(self, name, keyval, state):
        if name == "Escape" and self.filter.get_text():      # Esc: clear the filter first
            self.filter.set_text("")
            return True
        return False

    def inside(self, widget):
        return widget is self.sheet


if __name__ == "__main__":
    sys.exit(KeySheet().run(sys.argv))
