#!/usr/bin/env python3
# =============================================================================
#  settings-app/settings_app.py — "Hyprland settings" window (GTK 4 + libadwaita)
# =============================================================================
#  A GNOME/Ubuntu-Settings-like window: sidebar of pages on the left, grouped
#  rows on the right (switches, drop-downs, spin buttons, text fields with
#  suggestions, ordered module lists, action buttons).
#
#  Everything comes from hypr/settings.schema ("Page/Group | KEY | type |
#  choices | label | apply"): add a line there and it appears here.
#  Values: hypr/settings.conf (defaults) + ~/.local/state/inkpaw/
#  toggles.conf (your changes). Changes are applied through
#  hypr/scripts/menus/settings.sh set KEY VALUE (same logic as the rofi menu),
#  immediately for switches / drop-downs, after a short pause for numbers/text.
#
#  Launch: SUPER+CTRL+S, the 󰒓 bar button, or hypr/scripts/settings-ui.sh
#
#  Skins: with UI_SKIN set (e.g. "encre", hyprtheme/skin.sh), the generated
#  settings-app/skins/<skin>.css (template hyprtheme/templates/settings-<skin>.css)
#  is loaded over APP_CSS; "encre" also adds brush-pen page titles and a cat
#  peeking at the bottom of the sidebar. Read at start: reopen the window
#  after switching skin. UI_SKIN="default" = plain libadwaita look.
# =============================================================================
import os
import queue
import re
import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

HOME = os.path.expanduser("~")
CFG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
SETTINGS = os.path.join(CFG, "hypr", "settings.conf")
TOGGLES = os.path.join(STATE, "toggles.conf")
SCHEMA = os.path.join(CFG, "hypr", "settings.schema")
CATALOG = os.path.join(CFG, "waybar", "catalog.tsv")
SETTER = os.path.join(CFG, "hypr", "scripts", "menus", "settings.sh")
ENV = dict(os.environ, SCRIPTS=os.path.join(CFG, "hypr", "scripts"), THEME_DIR=os.path.join(CFG, "hyprtheme"), CFG=CFG)

PAGE_ICONS = {
    "Bar": ["view-continuous-symbolic", "view-list-symbolic"],
    "Appearance": ["preferences-desktop-appearance-symbolic", "applications-graphics-symbolic"],
    "Windows": ["preferences-system-windows-symbolic", "window-new-symbolic", "focus-windows-symbolic"],
    "Displays": ["video-display-symbolic", "preferences-desktop-display-symbolic"],
    "System": ["preferences-system-symbolic", "emblem-system-symbolic"],
    "Applications": ["application-x-executable-symbolic", "view-app-grid-symbolic", "applications-system-symbolic"],
    "AI assistant": ["chat-bubble-text-symbolic", "user-available-symbolic", "dialog-information-symbolic"],
}
CAPSULE_LABELS = {"session": "Session (launcher, workspaces…)", "time": "Time (clock)",
                  "status": "Status (sound, network…)", "system": "System (notifications, power…)"}


def esc(text):
    """libadwaita titles are Pango markup: escape "&", "<"…"""
    return GLib.markup_escape_text(text or "")


# --- data ------------------------------------------------------------------------------
def read_conf(path, into=None):
    into = {} if into is None else into
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


def load_values():
    defaults = read_conf(SETTINGS)
    overrides = read_conf(TOGGLES)
    return dict(defaults, **overrides), overrides


def skin_of(values):
    """Active interface skin ("default" = plain libadwaita look)."""
    return values.get("UI_SKIN") or "default"


def skin_css(skin):
    """Generated stylesheet of a skin, or None (default skin / not rendered yet)."""
    path = os.path.join(CFG, "settings-app", "skins", f"{skin}.css")
    return path if skin != "default" and os.path.isfile(path) else None


def load_schema():
    """[(page, group, [option dicts])] in file order."""
    pages = {}
    order = []
    with open(SCHEMA) as f:
        for line in f:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = [x.strip() for x in line.split("|")]
            if len(fields) != 6:
                continue
            section, key, typ, choices, label, apply = fields
            page, _, group = section.partition("/")
            if page not in pages:
                pages[page] = {}
                order.append(page)
            pages[page].setdefault(group or page, []).append(
                {"key": key, "type": typ, "choices": choices, "label": label, "apply": apply})
    return [(p, list(pages[p].items())) for p in order]


def catalog():
    items = []
    try:
        with open(CATALOG) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                name, _wid, label = line.rstrip("\n").split("\t")
                items.append((name, label))
    except OSError:
        pass
    return items


# --- applying (serialised in a worker thread) -------------------------------------
class Applier:
    def __init__(self, on_done):
        self.q = queue.Queue()
        self.on_done = on_done
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while True:
            argv, msg = self.q.get()
            ok = subprocess.run(argv, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            GLib.idle_add(self.on_done, msg, ok)

    def set(self, key, value, label):
        self.q.put(([SETTER, "set", key, value], f"{label}: {value or 'default'}"))

    def reset(self, page):
        self.q.put(([SETTER, "reset", page], f"{page} reset to defaults"))

    def reset_key(self, key, label):
        self.q.put(([SETTER, "unset", key], f"{label} reset"))


# --- window ------------------------------------------------------------------------------
class SettingsWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Hyprland settings", default_width=1060, default_height=720)
        self.values, self.overrides = load_values()
        self.schema = load_schema()
        self.catalog = catalog()
        self.timers = {}
        self.applier = Applier(self.on_applied)
        # skin decorations (titles, cat) only when its stylesheet is there too
        self.encre = skin_of(self.values) == "encre" and skin_css("encre") is not None

        self.split = Adw.NavigationSplitView(min_sidebar_width=220, max_sidebar_width=260)
        self.set_content(self.split)

        # Sidebar
        side_tb = Adw.ToolbarView()
        side_head = Adw.HeaderBar()
        side_head.set_title_widget(Adw.WindowTitle(title="Settings", subtitle="inkpaw"))
        mark = os.path.join(CFG, "hyprtheme", "skins", "encre", "logo", "inkpaw-mark-64.png")
        if os.path.isfile(mark):                    # the Inkpaw mark left of the title
            logo = Gtk.Image.new_from_file(mark)
            logo.set_pixel_size(26)
            side_head.pack_start(logo)
        side_tb.add_top_bar(side_head)
        self.sidebar = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.sidebar.add_css_class("navigation-sidebar")
        self.sidebar.connect("row-selected", self.on_page_selected)
        side_scroll = Gtk.ScrolledWindow(child=self.sidebar, vexpand=True)
        cat = self.skin_picture("peek-biscotte", 112, 121) if self.encre else None
        if cat is not None:                      # encre: the horned cream cat peeks at the bottom
            overlay = Gtk.Overlay(child=side_scroll)
            cat.set_halign(Gtk.Align.CENTER)
            cat.set_valign(Gtk.Align.END)
            cat.set_can_target(False)            # clicks go through to the page list
            cat.add_css_class("encre-sidebar-cat")
            overlay.add_overlay(cat)
            side_tb.set_content(overlay)
        else:
            side_tb.set_content(side_scroll)
        self.split.set_sidebar(Adw.NavigationPage(title="Settings", child=side_tb))

        # Content
        content_tb = Adw.ToolbarView()
        self.content_head = Adw.HeaderBar()
        content_tb.add_top_bar(self.content_head)
        if self.encre:                           # the page title is drawn big in the page itself
            self.content_head.set_show_title(False)
        self.toasts = Adw.ToastOverlay()
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=150)
        self.toasts.set_child(self.stack)
        content_tb.set_content(self.toasts)
        self.content_page = Adw.NavigationPage(title="", child=content_tb)
        self.split.set_content(self.content_page)

        self.build_pages()
        self.sidebar.select_row(self.sidebar.get_row_at_index(0))

    # pages -----------------------------------------------------------------------------
    def build_pages(self):
        for child in list(self.stack):
            self.stack.remove(child)
        self.sidebar.remove_all()
        for page, groups in self.schema:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=12, margin_top=8, margin_bottom=8, margin_start=6)
            box.append(Gtk.Image.new_from_icon_name(self.icon_for(page)))
            box.append(Gtk.Label(label=page, xalign=0))
            row.set_child(box)
            row.page_name = page
            self.sidebar.append(row)
            self.stack.add_named(self.build_page(page, groups), page)

    def skin_picture(self, name, width, height):
        """Picture of a cat of the skin (hyprtheme/skins/encre/cats/<name>.svg|png), or None."""
        base = os.path.join(CFG, "hyprtheme", "skins", "encre", "cats", name)
        for path in (base + ".svg", base + ".png"):
            if os.path.isfile(path):
                pic = Gtk.Picture.new_for_filename(path)
                pic.set_content_fit(Gtk.ContentFit.CONTAIN)
                pic.set_can_shrink(True)
                pic.set_size_request(width, height)
                return pic
        return None

    def icon_for(self, page):
        theme = Gtk.IconTheme.get_for_display(self.get_display())
        for name in PAGE_ICONS.get(page, []) + ["preferences-system-symbolic"]:
            if theme.has_icon(name):
                return name
        return "preferences-system-symbolic"

    def build_page(self, page, groups):
        pref = Adw.PreferencesPage(title=page, icon_name=self.icon_for(page))
        if self.encre:                           # big brush-pen title on top of the page
            head = Adw.PreferencesGroup()
            title = Gtk.Label(label=page, xalign=0)
            title.add_css_class("encre-page-title")
            head.add(title)
            pref.add(head)
        for title, options in groups:
            group = Adw.PreferencesGroup(title=esc(title) if title != page else "")
            for opt in options:
                row = self.build_row(opt)
                if row is not None:
                    group.add(row)
            pref.add(group)
        tail = Adw.PreferencesGroup()
        reset = Adw.ButtonRow(title=esc(f"Reset {page} to defaults"), start_icon_name="edit-undo-symbolic")
        reset.add_css_class("destructive-action")
        reset.connect("activated", lambda *_: self.confirm_reset(page))
        tail.add(reset)
        pref.add(tail)
        return pref

    def open_page(self, name):
        for i, (p, _g) in enumerate(self.schema):
            if p.lower() == name.lower():
                self.sidebar.select_row(self.sidebar.get_row_at_index(i))

    def on_page_selected(self, _list, row):
        if row is None:
            return
        self.stack.set_visible_child_name(row.page_name)
        self.content_page.set_title(row.page_name)
        self.split.set_show_content(True)

    # rows -------------------------------------------------------------------------------
    def build_row(self, opt):
        key, typ, label = opt["key"], opt["type"], opt["label"]
        value = self.values.get(key, "")
        builder = {"bool": self.row_bool, "choice": self.row_choice, "number": self.row_number, "app": self.row_app,
                   "secret": self.row_secret,
                   "text": self.row_text, "modules": self.row_list, "capsules": self.row_list,
                   "action": self.row_action}.get(typ)
        if builder is None:
            return None
        row = builder(opt, value)
        if typ not in ("action", "secret"):
            self.add_revert(row, key, label)
        return row

    def add_revert(self, row, key, label):
        """Small 'back to default' button, shown when the value was changed."""
        btn = Gtk.Button(icon_name="edit-undo-symbolic", valign=Gtk.Align.CENTER,
                         tooltip_text="Back to the value of settings.conf")
        btn.add_css_class("flat")
        btn.set_visible(key in self.overrides)
        btn.connect("clicked", lambda *_: self.revert_key(key, label))
        if hasattr(row, "add_suffix"):
            row.add_suffix(btn)
        row.revert_button = btn

    def row_bool(self, opt, value):
        row = Adw.SwitchRow(title=esc(opt["label"]), active=value.lower() in ("1", "true", "yes", "on"))
        row.connect("notify::active", lambda r, _p: self.change(opt, "true" if r.get_active() else "false", r))
        return row

    def row_choice(self, opt, value):
        choices = [c for c in opt["choices"].split(",") if c]
        if value and value not in choices:
            choices.insert(0, value)
        row = Adw.ComboRow(title=esc(opt["label"]), model=Gtk.StringList.new(choices))
        row.set_selected(choices.index(value) if value in choices else 0)
        row.connect("notify::selected", lambda r, _p: self.change(opt, choices[r.get_selected()], r))
        return row

    def row_number(self, opt, value):
        sugg = []
        for c in opt["choices"].split(","):
            try:
                sugg.append(float(c))
            except ValueError:
                pass
        try:
            cur = float(value)
        except ValueError:
            cur = sugg[0] if sugg else 0.0
        is_float = any(not v.is_integer() for v in sugg + [cur]) or opt["key"].endswith("OPACITY")
        lo = min(sugg + [cur, 0.0])
        hi = max(sugg + [cur]) if sugg else 100.0
        if is_float:
            lo, hi, step, digits = (min(lo, -1.0) if lo < 0 else 0.0), max(1.0, hi), 0.01, 2
        else:
            lo, hi, step, digits = lo, max(hi * 3, hi + 10), 1, 0
        row = Adw.SpinRow.new_with_range(lo, hi, step)
        row.set_title(esc(opt["label"]))
        row.set_digits(digits)
        row.set_value(cur)
        fmt = (lambda v: f"{v:.2f}".rstrip("0").rstrip(".") if is_float else str(int(round(v))))
        row.connect("notify::value", lambda r, _p: self.change(opt, fmt(r.get_value()), r, delay=600))
        return row

    def row_app(self, opt, value):
        """Drop-down of the INSTALLED suggestions (+ current value) and "Other…"."""
        import shutil
        apps = [c for c in opt["choices"].split(",") if c and shutil.which(c.split()[0])]
        if value and value not in apps:
            apps.insert(0, value)
        items = apps + ["Other…"]
        row = Adw.ComboRow(title=esc(opt["label"]), model=Gtk.StringList.new(items))
        row.set_subtitle(esc("" if value in apps else "not installed"))
        row.set_selected(apps.index(value) if value in apps else 0)
        state = {"last": row.get_selected()}

        def on_sel(r, _p):
            i = r.get_selected()
            if i == len(items) - 1:                      # "Other…": ask for a command
                self.ask_command(opt, r, lambda: r.set_selected(state["last"]))
                return
            state["last"] = i
            self.change(opt, items[i], r)
        row.connect("notify::selected", on_sel)
        return row

    def ask_command(self, opt, row, on_cancel):
        dlg = Adw.AlertDialog(heading=esc(opt["label"]), body="Command to launch")
        entry = Gtk.Entry(text=self.values.get(opt["key"], ""), activates_default=True)
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Use")
        dlg.set_default_response("ok")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)

        def done(_d, resp):
            cmd = entry.get_text().strip()
            if resp == "ok" and cmd:
                self.change(opt, cmd, row)
                self.toasts.add_toast(Adw.Toast(title=esc(f"{opt['label']}: {cmd}"), timeout=2))
            else:
                on_cancel()
        dlg.connect("response", done)
        dlg.present(self)

    def row_secret(self, opt, _value):
        """API key: typed in a password field, stored apart, never shown back."""
        saved = bool(read_conf(os.path.join(STATE, "secrets.conf")).get(opt["key"]))
        base = esc(opt["label"])
        row = Adw.PasswordEntryRow(title=f"{base} — saved" if saved else base, show_apply_button=True)
        trash = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, tooltip_text="Remove the key")
        trash.add_css_class("flat")
        trash.set_visible(saved)

        def store(value):
            self.applier.q.put(([SETTER, "secret", opt["key"], value],
                                f"{opt['label']} {'saved' if value else 'removed'}"))
            row.set_text("")
            row.set_title(f"{base} — saved" if value else base)
            trash.set_visible(bool(value))
        row.connect("apply", lambda r: r.get_text() and store(r.get_text()))
        trash.connect("clicked", lambda *_: store(""))
        row.add_suffix(trash)
        return row

    def row_text(self, opt, value):
        row = Adw.EntryRow(title=esc(opt["label"]), text=value, show_apply_button=True)
        row.connect("apply", lambda r: self.change(opt, r.get_text(), r))
        sugg = [s for s in opt["choices"].split(";") if s]
        if sugg:
            box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
            box.add_css_class("boxed-list")
            pop = Gtk.Popover(child=box)
            for s in sugg:
                item = Adw.ActionRow(title=esc(s), activatable=True)
                item.connect("activated", lambda _i, s=s: (pop.popdown(), row.set_text(s), self.change(opt, s, row)))
                box.append(item)
            menu = Gtk.MenuButton(icon_name="view-more-symbolic", popover=pop, valign=Gtk.Align.CENTER,
                                  tooltip_text="Suggestions")
            menu.add_css_class("flat")
            row.add_suffix(menu)
        return row

    def row_action(self, opt, _value):
        row = Adw.ActionRow(title=esc(opt["label"]), activatable=True)
        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        row.connect("activated", lambda *_: subprocess.Popen(["bash", "-c", opt["key"]], env=ENV,
                                                             start_new_session=True))
        return row

    # ordered module / capsule lists inside an expander -----------------------------
    def row_list(self, opt, value):
        exp = Adw.ExpanderRow(title=esc(opt["label"]))
        exp.items = value.split()
        exp.children = []
        self.fill_list(exp, opt)
        return exp

    def list_universe(self, opt):
        if opt["type"] == "capsules":
            return [(n, CAPSULE_LABELS[n]) for n in ("session", "time", "status", "system")]
        items = self.catalog
        if opt["key"] == "BAR_EXTRAS":
            items = [i for i in items if i[0] != "extras"]
        return items

    def fill_list(self, exp, opt):
        for child in exp.children:
            exp.remove(child)
        exp.children = []
        labels = dict(self.list_universe(opt))
        exp.set_subtitle(esc(", ".join(labels.get(n, n) for n in exp.items) or "(empty)"))

        def add(name, label, enabled, index):
            r = Adw.ActionRow(title=esc(label), subtitle=esc(name))
            check = Gtk.CheckButton(active=enabled, valign=Gtk.Align.CENTER)
            check.connect("toggled", lambda c: self.list_toggle(exp, opt, name, c.get_active()))
            r.add_prefix(check)
            r.set_activatable_widget(check)
            if enabled:
                for icon, delta, tip in (("go-up-symbolic", -1, "Earlier"), ("go-down-symbolic", 1, "Later")):
                    b = Gtk.Button(icon_name=icon, valign=Gtk.Align.CENTER, tooltip_text=tip)
                    b.add_css_class("flat")
                    b.set_sensitive(0 <= index + delta < len(exp.items))
                    b.connect("clicked", lambda _b, d=delta: self.list_move(exp, opt, name, d))
                    r.add_suffix(b)
            exp.add_row(r)
            exp.children.append(r)

        for i, n in enumerate(exp.items):
            add(n, labels.get(n, n), True, i)
        for n, label in self.list_universe(opt):
            if n not in exp.items:
                add(n, label, False, -1)

    def list_toggle(self, exp, opt, name, on):
        if on and name not in exp.items:
            exp.items.append(name)
        elif not on and name in exp.items:
            exp.items.remove(name)
        self.list_commit(exp, opt)

    def list_move(self, exp, opt, name, delta):
        i = exp.items.index(name)
        j = i + delta
        if 0 <= j < len(exp.items):
            exp.items[i], exp.items[j] = exp.items[j], exp.items[i]
            self.list_commit(exp, opt)

    def list_commit(self, exp, opt):
        GLib.idle_add(lambda: (self.fill_list(exp, opt), False)[1])
        self.change(opt, " ".join(exp.items), exp, delay=400)

    # changes -----------------------------------------------------------------------------
    def change(self, opt, value, row, delay=0):
        key = opt["key"]
        self.values[key] = value
        self.overrides[key] = value
        if getattr(row, "revert_button", None):
            row.revert_button.set_visible(True)
        if key in self.timers:
            GLib.source_remove(self.timers.pop(key))

        def fire():
            self.timers.pop(key, None)
            self.applier.set(key, value, opt["label"])
            return False
        if delay:
            self.timers[key] = GLib.timeout_add(delay, fire)
        else:
            fire()

    def revert_key(self, key, label):
        self.applier.reset_key(key, label)

    def confirm_reset(self, page):
        dlg = Adw.AlertDialog(heading=f"Reset {page}?",
                              body="Every value of this page goes back to hypr/settings.conf.")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("reset", "Reset")
        dlg.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", lambda _d, r: r == "reset" and self.applier.reset(page))
        dlg.present(self)

    def on_applied(self, msg, ok):
        self.toasts.add_toast(Adw.Toast(title=esc(msg if ok else f"Failed: {msg}"), timeout=2))
        if "reset" in msg:                       # values changed on disk: rebuild the pages
            current = self.sidebar.get_selected_row()
            name = getattr(current, "page_name", None)
            self.values, self.overrides = load_values()
            self.build_pages()
            for i, (p, _g) in enumerate(self.schema):
                if p == name:
                    self.sidebar.select_row(self.sidebar.get_row_at_index(i))
        return False


APP_CSS = """
/* opaque sidebar + content (the window sits over a blurred, translucent desktop) */
.sidebar-pane, .sidebar-pane .navigation-sidebar { background-color: @sidebar_bg_color; }
.content-pane { background-color: @window_bg_color; }
"""


class App(Adw.Application):
    def __init__(self, page=None):
        super().__init__(application_id="dev.inkpaw.Settings", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.page = page

    def do_startup(self):
        Adw.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_string(APP_CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        skin = skin_css(skin_of(load_values()[0]))
        if skin:                                 # UI_SKIN != default: its stylesheet over APP_CSS
            skin_provider = Gtk.CssProvider()
            skin_provider.load_from_path(skin)
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), skin_provider,
                                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)

    def do_activate(self):
        win = self.get_active_window() or SettingsWindow(self)
        if self.page:
            win.open_page(self.page)
        win.present()


if __name__ == "__main__":
    import sys
    App(sys.argv[1] if len(sys.argv) > 1 else None).run([])
