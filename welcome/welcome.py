#!/usr/bin/env python3
# =============================================================================
#  welcome/welcome.py — first-boot welcome window (GTK 4 + libadwaita)
# =============================================================================
#  Four steps to get going ("Mew-Welcome" mockup):
#    1  choose a wallpaper          -> hyprtheme/wallpaper-picker.sh
#    2  place the bar               -> menus/settings.sh set BAR_POSITION top|bottom
#                                      menus/settings.sh set BAR_SINGLE_CAPSULE true|false
#    3  default applications        -> settings-ui.sh Applications (settings window)
#    4  three shortcuts to remember (SUPER+SPACE, SUPER+CTRL+S, SUPER+CTRL+K)
#  Click a step card to jump to it; Next / Skip / Esc.
#  Usage: welcome.py [--step 1..4]   (open on that step)
#  WELCOME_SKIN=default|encre overrides UI_SKIN (to preview the other look).
#
#  "Don't show at startup" (checked by default) writes the flag
#  ~/.local/state/inkpaw/welcome-done when the window closes (unchecked
#  removes it). hypr/scripts/welcome.sh --first opens the window only while
#  that flag does not exist.
#
#  Look: UI_SKIN=encre -> parchment / ink / ochre CSS embedded below, colors
#  read from the current palette (~/.cache/inkpaw/palette.json, written
#  by hyprtheme/theme.sh), fonts Shantell Sans / Caveat Brush / Courier Prime;
#  any other skin -> plain libadwaita. Texts in French when LANG is fr_*,
#  English otherwise. Window class: dev.inkpaw.Welcome.
# =============================================================================
import json
import os
import re
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

HOME = os.path.expanduser("~")
PROJECT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "inkpaw")
FLAG = os.path.join(STATE, "welcome-done")
SCRIPTS = os.path.join(PROJECT, "hypr", "scripts")
CATS = os.path.join(PROJECT, "hyprtheme", "skins", "encre", "cats")
ENV = {k: v for k, v in os.environ.items() if k != "LD_PRELOAD"}

FR = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "").startswith("fr")
T = {
    "title":    ("Bienvenue dans Inkpaw", "Welcome to Inkpaw"),
    "litter":   ("La portée te salue.", "The litter says hi."),
    "step":     ("Étape {} sur 4", "Step {} of 4"),
    "intro":    ("Quatre petites choses et c’est prêt.", "Four little things and you are set."),
    "intro2":   ("Tout reste modifiable ensuite dans Réglages (", "Everything can be changed later in Settings ("),
    "s1":       ("Choisis un fond d’écran", "Choose a wallpaper"),
    "s1d":      ("Les couleurs de tout le bureau en découlent", "The colors of the whole desktop follow it"),
    "s2":       ("Place la barre", "Place the bar"),
    "s2d":      ("En haut ou en bas, 3 groupes ou une seule capsule", "Top or bottom, 3 groups or a single capsule"),
    "s3":       ("Applications par défaut", "Default applications"),
    "s3d":      ("Terminal, navigateur, fichiers", "Terminal, browser, files"),
    "s4":       ("Retiens trois raccourcis", "Remember three shortcuts"),
    "s4d":      ("Recherche, réglages, pense-bête", "Search, settings, cheat sheet"),
    "done":     ("fait ✓", "done ✓"),
    "current":  ("en cours", "now"),
    "pick":     ("Choisir un fond d’écran…", "Choose a wallpaper…"),
    "top":      ("En haut", "Top"),
    "bottom":   ("En bas", "Bottom"),
    "groups":   ("3 groupes", "3 groups"),
    "capsule":  ("Une seule capsule", "One capsule"),
    "apps":     ("Ouvrir les réglages", "Open the settings"),
    "apps_now": ("Actuellement : {}", "Currently: {}"),
    "k_search": ("Recherche (applis, fichiers, calculs…)", "Search (apps, files, maths…)"),
    "k_set":    ("Réglages", "Settings"),
    "k_keys":   ("Pense-bête de tous les raccourcis", "Cheat sheet of every shortcut"),
    "dont":     ("Ne plus afficher au démarrage", "Don’t show at startup"),
    "skip":     ("Passer", "Skip"),
    "next":     ("Suivant", "Next"),
    "finish":   ("C’est parti !", "Let’s go!"),
}


def _(key):
    return T[key][0 if FR else 1]


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


def is_true(v):
    return str(v).lower() in ("true", "1", "yes", "on")


def run(argv):
    """Start a helper detached from us (it outlives the window)."""
    try:
        subprocess.Popen(argv, env=ENV, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def set_setting(key, value):
    """menus/settings.sh set KEY VALUE (writes the toggle + restarts the bar) off the UI thread."""
    def work():
        subprocess.run([os.path.join(SCRIPTS, "menus", "settings.sh"), "set", key, value],
                       env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    threading.Thread(target=work, daemon=True).start()


# --- encre skin CSS (Material roles from the current palette) ----------------------------
def palette():
    roles = {"surface": "#f1e7cf", "surface_container_high": "#e2d3b0", "surface_container_lowest": "#fffaf0",
             "on_surface": "#2a2420", "on_surface_variant": "#4a4038", "primary": "#8a5d10",
             "primary_container": "#d9a12e", "on_primary_container": "#2a2420",
             "secondary_container": "#8fa34b", "on_secondary_container": "#2a2420"}
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


def encre_css(p, conf):
    font = conf.get("FONT_FAMILY") or "Shantell Sans"
    display = conf.get("DISPLAY_FONT") or "Caveat Brush"
    mono = conf.get("MONO_FONT") or "Courier Prime"
    return f"""
@define-color ink {p['on_surface']};
@define-color paper {p['surface']};
@define-color card {p['surface_container_lowest']};
@define-color ochre {p['primary_container']};
@define-color on_ochre {p['on_primary_container']};
@define-color moss {p['secondary_container']};
window.welcome {{ background: @paper; color: @ink; font-family: "{font}", sans-serif; }}
window.welcome label {{ font-family: "{font}", sans-serif; }}
.side {{ background: @ochre; color: @on_ochre; border-right: 3px solid @ink; }}
.display, window.welcome label.display {{ font-family: "{display}", cursive; }}
.litter {{ font-size: 30px; transform: rotate(-2deg); }}
.stepnum {{ font-size: 14px; font-weight: 700; color: {p['primary']}; }}
.bigtitle {{ font-size: 50px; }}
.intro {{ font-size: 16px; color: {p['on_surface_variant']}; }}
.keycap, window.welcome label.keycap {{
    font-family: "{mono}", monospace; font-size: 13px; font-weight: 700;
    background: @card; color: @ink; padding: 0 7px;
    border: 2.5px solid @ink; border-bottom-width: 4px; border-radius: 7px 9px 6px 8px;
}}
.keycap.big {{ font-size: 16px; padding: 2px 10px; }}
.stepcard {{
    padding: 10px 14px; background: @card; border: 3px solid alpha(@ink, 0.35);
    border-radius: 14px 10px 16px 12px;
}}
.stepcard.current {{ background: @ochre; color: @on_ochre; border-color: @ink; transform: rotate(-0.8deg); }}
.stepcard .num {{
    min-width: 36px; min-height: 36px; font-family: "{display}", cursive; font-size: 24px;
    background: @card; color: @ink; border: 2.5px solid @ink; border-radius: 18px 16px 19px 17px;
}}
.stepcard.done .num {{ background: @moss; }}
.stepcard .ctitle {{ font-size: 16px; font-weight: 700; }}
.stepcard .cdesc {{ font-size: 13px; color: {p['on_surface_variant']}; }}
.stepcard.current .cdesc {{ color: alpha(@on_ochre, 0.8); }}
.stepcard .cstate {{ font-size: 13px; font-weight: 700; }}
.stepcard .hint {{ font-size: 13px; }}
window.welcome button {{
    font-family: "{font}", sans-serif; font-weight: 700; color: @ink; background: @card;
    border: 3px solid @ink; border-radius: 14px 10px 16px 12px; padding: 7px 18px; box-shadow: none;
}}
window.welcome button:hover {{ background: mix(@card, @ochre, 0.3); }}
window.welcome button.chip {{ border-width: 2.5px; border-radius: 10px 14px 9px 13px; padding: 4px 14px; }}
window.welcome button.chip:checked {{ background: @ink; color: @card; box-shadow: 3px 3px 0 alpha(@ink, 0.35); }}
window.welcome button.next {{ background: @moss; box-shadow: 4px 4px 0 @ink; padding: 9px 22px; font-size: 16px; }}
window.welcome button.skip {{ padding: 9px 22px; font-size: 16px; }}
window.welcome checkbutton {{ font-weight: 600; font-size: 14px; }}
window.welcome checkbutton check {{
    background: @card; border: 2.5px solid @ink; border-radius: 4px 6px 5px 4px; color: @ink;
    min-width: 16px; min-height: 16px; box-shadow: none;
}}
window.welcome checkbutton check:checked {{ background: @ink; color: @card; }}
"""


PLAIN_CSS = """
.side { background: alpha(@accent_bg_color, 0.18); }
.litter { font-size: 22px; font-weight: 700; }
.stepnum { font-weight: 700; color: @accent_color; }
.bigtitle { font-size: 36px; font-weight: 800; }
.keycap { font-family: monospace; font-weight: 700; padding: 0 6px; border-radius: 6px;
          border: 1px solid alpha(currentColor, 0.3); border-bottom-width: 3px; background: alpha(currentColor, 0.06); }
.keycap.big { padding: 2px 9px; }
.stepcard { padding: 10px 14px; border-radius: 12px; background: alpha(currentColor, 0.04);
            border: 1px solid alpha(currentColor, 0.12); }
.stepcard.current { background: alpha(@accent_bg_color, 0.2); border-color: @accent_bg_color; }
.stepcard .num { min-width: 34px; min-height: 34px; border-radius: 17px; font-weight: 800;
                 background: alpha(currentColor, 0.08); }
.stepcard.done .num { background: @success_color; color: white; }
.stepcard .ctitle { font-weight: 700; }
.stepcard .cdesc { opacity: 0.7; font-size: 0.9em; }
.stepcard .cstate { font-weight: 700; font-size: 0.9em; }
"""


def keycap(text, big=False):
    lb = Gtk.Label(label=text, valign=Gtk.Align.CENTER)
    lb.add_css_class("keycap")
    if big:
        lb.add_css_class("big")
    return lb


def keys_row(keys, big=False):
    box = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
    for i, k in enumerate(keys):
        if i:
            box.append(Gtk.Label(label="+"))
        box.append(keycap(k, big))
    return box


# --- the window ------------------------------------------------------------------------------
class Welcome(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.inkpaw.Welcome")
        self.conf = settings()
        self.step = 0
        if "--step" in sys.argv[1:-1]:
            try:
                self.step = max(0, min(3, int(sys.argv[sys.argv.index("--step") + 1]) - 1))
            except ValueError:
                pass
        self.done = set()
        self.win = None

    def do_activate(self):
        if self.win:
            self.win.present()
            return
        encre = (os.environ.get("WELCOME_SKIN") or self.conf.get("UI_SKIN")) == "encre"
        prov = Gtk.CssProvider()
        prov.load_from_string(encre_css(palette(), self.conf) if encre else PLAIN_CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        win = Adw.ApplicationWindow(application=self, title=_("title"), default_width=1100, default_height=720)
        win.add_css_class("welcome")
        self.win = win

        main = Gtk.Box()
        main.append(self.build_side())
        main.append(self.build_steps())
        if encre:
            win.set_content(Gtk.WindowHandle(child=main))
        else:
            tv = Adw.ToolbarView()
            tv.add_top_bar(Adw.HeaderBar(show_title=False))
            tv.set_content(main)
            win.set_content(tv)

        esc = Gtk.ShortcutController()
        esc.add_shortcut(Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string("Escape"),
                                      action=Gtk.CallbackAction.new(lambda *_: win.close() or True)))
        win.add_controller(esc)
        win.connect("close-request", self.on_close)
        self.refresh()
        win.present()

    # left: the basket of cats
    def build_side(self):
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, valign=Gtk.Align.FILL)
        side.add_css_class("side")
        side.set_size_request(420, -1)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, vexpand=True, valign=Gtk.Align.CENTER)
        for name in ("basket.png", "basket.svg"):
            path = os.path.join(CATS, name)
            if os.path.exists(path):
                pic = Gtk.Picture.new_for_filename(path)
                pic.set_can_shrink(True)
                pic.set_content_fit(Gtk.ContentFit.CONTAIN)
                pic.set_size_request(340, 300)
                # the clamp caps the natural width (the 2x PNG is 680 px wide)
                inner.append(Adw.Clamp(child=pic, maximum_size=340, tightening_threshold=340))
                break
        lb = Gtk.Label(label=_("litter"))
        lb.add_css_class("display")
        lb.add_css_class("litter")
        inner.append(lb)
        side.append(inner)
        return side

    # right: title, the four step cards, footer
    def build_steps(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, hexpand=True)
        box.set_margin_top(34)
        box.set_margin_bottom(30)
        box.set_margin_start(40)
        box.set_margin_end(40)

        # the Inkpaw logo (cat + name), cream version on a dark theme
        dark = Adw.StyleManager.get_default().get_dark()
        logo = os.path.join(PROJECT, "logo", "inkpaw-logo-dark.png" if dark else "inkpaw-logo.png")
        if os.path.isfile(logo):
            pic = Gtk.Picture.new_for_filename(logo)
            pic.set_content_fit(Gtk.ContentFit.CONTAIN)
            pic.set_can_shrink(True)
            pic.set_size_request(220, 80)
            pic.set_halign(Gtk.Align.START)
            box.append(pic)

        self.steplabel = Gtk.Label(xalign=0)
        self.steplabel.add_css_class("stepnum")
        box.append(self.steplabel)
        title = Gtk.Label(label=_("title"), xalign=0, wrap=True)
        title.add_css_class("display")
        title.add_css_class("bigtitle")
        box.append(title)

        intro = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        intro.add_css_class("intro")
        intro.append(Gtk.Label(label=_("intro"), xalign=0, wrap=True))
        row = Gtk.Box(spacing=4)
        row.append(Gtk.Label(label=_("intro2")))
        row.append(keys_row(["SUPER", "CTRL", "S"]))
        row.append(Gtk.Label(label=")."))
        intro.append(row)
        box.append(intro)

        cards = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        cards.set_margin_top(4)
        self.cards = []
        bodies = [self.body_wallpaper(), self.body_bar(), self.body_apps(), self.body_keys()]
        for i, (t, d) in enumerate((("s1", "s1d"), ("s2", "s2d"), ("s3", "s3d"), ("s4", "s4d"))):
            cards.append(self.build_card(i, _(t), _(d), bodies[i]))
        box.append(cards)

        foot = Gtk.Box(spacing=12, vexpand=True, valign=Gtk.Align.END)
        self.dont = Gtk.CheckButton(label=_("dont"), active=True)
        foot.append(self.dont)
        foot.append(Gtk.Box(hexpand=True))
        skip = Gtk.Button(label=_("skip"))
        skip.add_css_class("skip")
        skip.connect("clicked", lambda *_: self.win.close())
        foot.append(skip)
        self.nextbtn = Gtk.Button()
        self.nextbtn.add_css_class("next")
        self.nextbtn.add_css_class("suggested-action")
        self.nextbtn.connect("clicked", self.on_next)
        foot.append(self.nextbtn)
        box.append(foot)
        return box

    def build_card(self, i, title, desc, body):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("stepcard")
        head = Gtk.Box(spacing=14)
        num = Gtk.Label(label=str(i + 1), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        num.add_css_class("num")
        head.append(num)
        txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        t = Gtk.Label(label=title, xalign=0)
        t.add_css_class("ctitle")
        d = Gtk.Label(label=desc, xalign=0)
        d.add_css_class("cdesc")
        txt.append(t)
        txt.append(d)
        head.append(txt)
        state = Gtk.Label(hexpand=True, xalign=1)
        state.add_css_class("cstate")
        head.append(state)
        click = Gtk.GestureClick()
        click.connect("released", lambda *_: self.go(i))
        head.add_controller(click)
        head.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        card.append(head)
        rev = Gtk.Revealer(child=body, transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN)
        body.set_margin_start(50)
        card.append(rev)
        self.cards.append((card, state, rev))
        return card

    # step bodies ---------------------------------------------------------------------------
    def body_wallpaper(self):
        box = Gtk.Box(spacing=10)
        b = Gtk.Button(label=_("pick"))
        b.add_css_class("chip")
        b.connect("clicked", lambda *_: (run([os.path.join(PROJECT, "hyprtheme", "wallpaper-picker.sh")]),
                                         self.done.add(0), self.refresh()))
        box.append(b)
        return box

    def chip_group(self, box, options, current, on_pick):
        first = None
        for value, label in options:
            b = Gtk.ToggleButton(label=label, active=(value == current))
            b.add_css_class("chip")
            if first:
                b.set_group(first)
            else:
                first = b
            b.connect("toggled", lambda btn, v=value: btn.get_active() and on_pick(v))
            box.append(b)

    def body_bar(self):
        box = Gtk.Box(spacing=8)
        self.chip_group(box, [("top", _("top")), ("bottom", _("bottom"))],
                        self.conf.get("BAR_POSITION", "top"),
                        lambda v: (set_setting("BAR_POSITION", v), self.mark(1)))
        box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL, margin_start=6, margin_end=6))
        single = "true" if is_true(self.conf.get("BAR_SINGLE_CAPSULE", "false")) else "false"
        self.chip_group(box, [("false", _("groups")), ("true", _("capsule"))], single,
                        lambda v: (set_setting("BAR_SINGLE_CAPSULE", v), self.mark(1)))
        return box

    def body_apps(self):
        box = Gtk.Box(spacing=12)
        b = Gtk.Button(label=_("apps"))
        b.add_css_class("chip")
        b.connect("clicked", lambda *_: (run([os.path.join(SCRIPTS, "settings-ui.sh"), "Applications"]), self.mark(2)))
        box.append(b)
        apps = [self.conf.get(k, "").split()[0] for k in ("TERMINAL", "BROWSER", "FILEMANAGER") if self.conf.get(k)]
        if apps:
            hint = Gtk.Label(label=_("apps_now").format(" · ".join(apps)), xalign=0)
            hint.add_css_class("hint")
            box.append(hint)
        return box

    def body_keys(self):
        grid = Gtk.Grid(column_spacing=14, row_spacing=6)
        for r, (keys, what) in enumerate(((["SUPER", "SPACE"], "k_search"),
                                          (["SUPER", "CTRL", "S"], "k_set"),
                                          (["SUPER", "CTRL", "K"], "k_keys"))):
            row = keys_row(keys, big=True)
            row.set_halign(Gtk.Align.START)
            grid.attach(row, 0, r, 1, 1)
            lb = Gtk.Label(label=what and _(what), xalign=0)
            lb.add_css_class("hint")
            grid.attach(lb, 1, r, 1, 1)
        return grid

    # navigation --------------------------------------------------------------------------
    def mark(self, i):
        self.done.add(i)
        self.refresh()

    def go(self, i):
        self.step = i
        self.refresh()

    def on_next(self, *_a):
        self.done.add(self.step)
        if self.step >= 3:
            self.win.close()
            return
        self.step += 1
        self.refresh()

    def refresh(self):
        self.steplabel.set_label(_("step").format(self.step + 1))
        self.nextbtn.set_label(_("finish") if self.step >= 3 else _("next"))
        for i, (card, state, rev) in enumerate(self.cards):
            cur = i == self.step
            (card.add_css_class if cur else card.remove_css_class)("current")
            (card.add_css_class if i in self.done else card.remove_css_class)("done")
            state.set_label(_("current") if cur else (_("done") if i in self.done else ""))
            rev.set_reveal_child(cur)

    def on_close(self, *_a):
        try:
            if self.dont.get_active():
                os.makedirs(STATE, exist_ok=True)
                with open(FLAG, "w") as f:
                    f.write("# inkpaw welcome window: do not show at startup (delete to see it again)\n")
            elif os.path.exists(FLAG):
                os.remove(FLAG)
        except OSError:
            pass
        return False


if __name__ == "__main__":
    Welcome().run([])
