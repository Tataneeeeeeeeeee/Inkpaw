# =============================================================================
#  pylib/hyprapp.py — resident full-screen overlay menus (GTK 4 layer-shell)
# =============================================================================
#  Shared by powermenu/, keysheet/, themepicker/, wallpicker/. Each menu is a
#  RESIDENT app: started hidden at login (`<app>.py --daemon`), it maps itself
#  once invisibly (so the first opening skips the ~1 s first-map cost) and then
#  only hides / shows its window. Opening = a D-Bus call to its "toggle"
#  action (hypr/scripts/resident.sh, ~10 ms) instead of starting Python + GTK.
#
#  At every opening the subclass rebuilds its content (fresh binds, themes,
#  wallpapers…) and its CSS from the CURRENT palette, so theme changes need no
#  restart.
#
#  Subclass API:
#      NAMESPACE        layer-shell namespace (layer rules, debugging)
#      css()            -> CSS text for this opening
#      build()          -> the window's child widget (called at each opening)
#      on_key(name, keyval, state) -> True when handled (Esc closes by default)
#      inside(widget)   -> True when a click on `widget` must NOT close the menu
#      hide()           close the menu (the process stays)
#
#  Must be imported AFTER the module re-exec'd itself with LD_PRELOAD of
#  gtk4-layer-shell (see the apps' headers).
# =============================================================================
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

WARM_MS = 500          # how long the invisible first map lasts at --daemon


class ResidentOverlay(Gtk.Application):
    NAMESPACE = "overlay"

    def __init__(self, app_id):
        super().__init__(application_id=app_id, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.win = None
        self.provider = None

    # --- life cycle ---
    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()                                   # stays alive with its window hidden
        act = Gio.SimpleAction.new("toggle", None)
        act.connect("activate", lambda *_: self.toggle())
        self.add_action(act)

    def do_command_line(self, cmd):
        args = cmd.get_arguments()[1:]
        if args and args[0] == "--daemon":
            if self.win is None:
                self.warm()
        else:
            self.toggle()
        return 0

    def window(self):
        if self.win is not None:
            return self.win
        win = self.win = Gtk.ApplicationWindow(application=self)
        win.add_css_class(self.NAMESPACE)
        LayerShell.init_for_window(win)
        LayerShell.set_namespace(win, self.NAMESPACE)
        LayerShell.set_layer(win, LayerShell.Layer.OVERLAY)
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(win, edge, True)
        LayerShell.set_exclusive_zone(win, -1)
        LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.NONE)
        click = Gtk.GestureClick()
        click.connect("released", self._on_click)
        win.add_controller(click)
        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key)
        win.add_controller(keys)
        win.connect("close-request", lambda *_: (self.hide(), True)[1])
        return win

    def refresh(self):
        """New CSS from the current palette + freshly built content."""
        display = Gdk.Display.get_default()
        if self.provider is not None:
            Gtk.StyleContext.remove_provider_for_display(display, self.provider)
        self.provider = Gtk.CssProvider()
        self.provider.load_from_string(self.css())
        Gtk.StyleContext.add_provider_for_display(display, self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window().set_child(self.build())

    def warm(self):
        """Map once, invisible and without the keyboard, then hide."""
        win = self.window()
        self.refresh()
        win.set_opacity(0)
        win.present()
        GLib.timeout_add(WARM_MS, lambda: (win.set_visible(False), win.set_opacity(1), False)[2])

    def toggle(self):
        if self.win is not None and self.win.get_visible() and self.win.get_opacity() > 0:
            self.hide()
        else:
            self.open()

    def open(self):
        win = self.window()
        self.refresh()
        win.set_opacity(1)
        LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.EXCLUSIVE)
        win.present()
        self.opened()

    def opened(self):
        """Hook: after the window is shown (focus a field, select a card…)."""

    def hide(self):
        if self.win is not None:
            LayerShell.set_keyboard_mode(self.win, LayerShell.KeyboardMode.NONE)
            self.win.set_visible(False)

    # --- input ---
    def _on_key(self, _ctl, keyval, _code, state):
        name = Gdk.keyval_name(keyval) or ""
        if self.on_key(name, keyval, state):
            return True
        if name == "Escape":
            self.hide()
            return True
        return False

    def on_key(self, name, keyval, state):
        return False

    def _on_click(self, _g, _n, x, y):
        w = self.win.pick(x, y, Gtk.PickFlags.DEFAULT)
        while w is not None:
            if self.inside(w):
                return
            w = w.get_parent()
        self.hide()

    def inside(self, widget):
        return False
