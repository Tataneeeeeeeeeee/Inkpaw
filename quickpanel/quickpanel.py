#!/usr/bin/env python3
# =============================================================================
#  quickpanel/quickpanel.py — Wi-Fi, Bluetooth & Sound panel (drop-down under the bar)
# =============================================================================
#  A minimal libadwaita panel that drops down under the bar (layer-shell) and
#  shows ONE section: the one of the bar button you clicked.
#    Wi-Fi      switch, networks (connected one first: disconnect / forget;
#               click another = connect, password asked when needed), ⟳ scan,
#               ⚙ NetworkManager editor
#    Bluetooth  switch, your devices (click = connect / disconnect, battery,
#               remove), nearby devices after 󰍉 scan (click = pair + connect),
#               ⚙ Blueman
#    Sound      output volume + device, microphone volume + device, one slider
#               per application playing sound, ⚙ pavucontrol
#    Brightness laptop screen (brightnessctl), external screens over DDC/CI
#               (ddcutil, detected once and cached), keyboard backlight, night
#               light switch + color temperature (hyprsunset)
#    Battery    level, state, time left, power draw, health & cycles, power
#               mode (power-profiles-daemon), batteries of mouse / headset…
#    Notifications  history (logged by swaync → hypr/scripts/notif-log.sh),
#               today / earlier, dismiss, clear all, do-not-disturb, click =
#               open the app, ⚙ swaync control center
#    Calendar   month view with week numbers, selected day, ⌂ back to today
#    Media      cover, title, artist, progress (seek), previous / play-pause /
#               next, player chooser when several (playerctl / MPRIS)
#  Uses nmcli, bluetoothctl, pactl, brightnessctl, ddcutil, upower and
#  powerprofilesctl (all optional: missing tools just hide their rows). Refresh: 3 s
#  (sound: 2 s, a slider being moved is never overwritten).
#
#  Skins: UI_SKIN≠default loads quickpanel/skins/<skin>.css (rendered by hyprtheme
#  from templates/quickpanel-<skin>.css) over the base CSS, and adds the skin's
#  cats (encre: a cat sniffing under the Bluetooth panel, a cat as "no cover").
#
#  Usage: quickpanel.py wifi|bluetooth|sound|brightness|battery|notifications|calendar|media
#         Same section again = close, another one = replaces it.
#         Esc or a click outside closes.
#  Waybar: left click on the network / bluetooth / volume icons (modules/*.jsonc).
# =============================================================================
import os
import sys

# gtk4-layer-shell must be loaded before libwayland: re-exec with LD_PRELOAD,
# then drop it from the environment so the commands we run don't inherit it.
_LS = "/usr/lib/libgtk4-layer-shell.so"
if os.path.exists(_LS) and _LS not in os.environ.get("LD_PRELOAD", ""):
    os.environ["LD_PRELOAD"] = (_LS + " " + os.environ.get("LD_PRELOAD", "")).strip()
    os.execv(sys.executable, [sys.executable, "-I", os.path.abspath(__file__)] + sys.argv[1:])
_pre = [p for p in os.environ.get("LD_PRELOAD", "").split() if p != _LS]
if _pre:
    os.environ["LD_PRELOAD"] = " ".join(_pre)
else:
    os.environ.pop("LD_PRELOAD", None)

import re
import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TERMINAL_FLOAT = os.environ.get("TERMINAL_FLOAT", "kitty --class floating-tui -e")


# --- Skin (UI_SKIN) ------------------------------------------------------------------------
#  UI_SKIN comes from the environment when set, else from hypr/settings.conf
#  then the runtime toggles (later wins), like hypr/lib/settings.lua.
#  A skin = an extra stylesheet quickpanel/skins/<skin>.css (rendered by
#  hyprtheme from templates/quickpanel-<skin>.css), loaded after the base CSS,
#  plus the skin's cats (hyprtheme/skins/<skin>/cats/). "default" = base look only.
def read_setting(key, default=""):
    if os.environ.get(key):
        return os.environ[key]
    cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    state = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"), "inkpaw")
    value = default
    for path in (os.path.join(cfg, "hypr", "settings.conf"), os.path.join(state, "toggles.conf")):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$', line)
                    if m and m.group(1) == key and not line.lstrip().startswith("#"):
                        v = re.sub(r"\s+#.*$", "", m.group(2))          # trailing comment
                        value = v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" else v
        except OSError:
            pass
    return value


SKIN = read_setting("UI_SKIN", "default") or "default"
SKIN_CSS = os.path.join(HERE, "skins", SKIN + ".css")
SKIN_CATS = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                         "hyprtheme", "skins", SKIN, "cats")


def skin_cat(name):
    """Path of a cat picture of the active skin (PNG), or None (default skin / missing)."""
    path = os.path.join(SKIN_CATS, name + ".png")
    return path if SKIN != "default" and os.path.isfile(path) else None


def esc(text):
    return GLib.markup_escape_text(text or "")


def run(*argv, timeout=20):
    """Run a command, return (ok, stdout)."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, p.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False, ""


def background(fn, done=None):
    """Run fn() in a thread, then done(result) on the GTK thread."""
    def work():
        res = fn()
        if done:
            GLib.idle_add(lambda: (done(res), False)[1])
    threading.Thread(target=work, daemon=True).start()


# --- Wi-Fi (nmcli) -------------------------------------------------------------------
def nm_split(line):
    """nmcli -t escapes ':' as '\\:' inside fields."""
    return [f.replace("\\:", ":") for f in re.split(r"(?<!\\):", line)]


def wifi_state():
    ok, radio = run("nmcli", "-t", "radio", "wifi")
    enabled = radio.strip() == "enabled"
    iface, conn = None, None
    _, devs = run("nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev")
    for line in devs.splitlines():
        d = nm_split(line)
        if len(d) >= 4 and d[1] == "wifi":
            iface = d[0]
            if d[2] == "connected":
                conn = d[3]
    ip = ""
    if iface and conn:
        _, show = run("nmcli", "-t", "-f", "IP4.ADDRESS", "dev", "show", iface)
        m = re.search(r"IP4\.ADDRESS\[1\]:(\S+)", show)
        ip = m.group(1) if m else ""
    _, saved_out = run("nmcli", "-t", "-f", "NAME,TYPE", "con", "show")
    saved = {nm_split(l)[0] for l in saved_out.splitlines() if l.endswith(":802-11-wireless")}
    nets = {}
    if enabled:
        _, out = run("nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "no")
        for line in out.splitlines():
            f = nm_split(line)
            if len(f) < 4 or not f[1]:
                continue
            ssid, sig = f[1], int(f[2] or 0)
            cur = nets.get(ssid)
            if cur is None or sig > cur["signal"] or f[0] == "*":
                nets[ssid] = {"ssid": ssid, "signal": max(sig, cur["signal"] if cur else 0),
                              "secure": f[3] not in ("", "--"), "active": f[0] == "*" or (cur or {}).get("active", False),
                              "saved": ssid in saved, "security": f[3]}
    ordered = sorted(nets.values(), key=lambda n: (not n["active"], not n["saved"], -n["signal"]))
    return {"enabled": enabled, "iface": iface, "conn": conn, "ip": ip, "networks": ordered}


def signal_icon(sig):
    for limit, name in ((75, "excellent"), (50, "good"), (25, "ok"), (0, "weak")):
        if sig >= limit:
            return f"network-wireless-signal-{name}-symbolic"
    return "network-wireless-signal-none-symbolic"


# --- Bluetooth (bluetoothctl) -----------------------------------------------------------
def bt_state():
    _, show = run("bluetoothctl", "show")
    powered = "Powered: yes" in show
    devices = []
    if powered:
        _, out = run("bluetoothctl", "devices")
        for line in out.splitlines():
            parts = line.split(" ", 2)
            if len(parts) < 3 or parts[0] != "Device":
                continue
            mac, name = parts[1], parts[2]
            _, info = run("bluetoothctl", "info", mac, timeout=5)
            batt = re.search(r"Battery Percentage: \S+ \((\d+)\)", info)
            icon = re.search(r"Icon: (\S+)", info)
            devices.append({"mac": mac, "name": name,
                            "paired": "Paired: yes" in info, "connected": "Connected: yes" in info,
                            "battery": int(batt.group(1)) if batt else None,
                            "icon": icon.group(1) if icon else "bluetooth"})
    devices.sort(key=lambda d: (not d["connected"], d["name"].lower()))
    return {"powered": powered, "devices": devices}


def bt_icon(kind):
    return {"audio-headset": "audio-headset-symbolic", "audio-headphones": "audio-headphones-symbolic",
            "audio-card": "audio-speakers-symbolic", "input-mouse": "input-mouse-symbolic",
            "input-keyboard": "input-keyboard-symbolic", "input-gaming": "input-gaming-symbolic",
            "phone": "phone-symbolic", "computer": "computer-symbolic"}.get(kind, "bluetooth-active-symbolic")


# --- Sound (pactl, PipeWire / PulseAudio) ---------------------------------------------
import json as _json  # noqa: E402
import time  # noqa: E402


def _pactl_json(what):
    ok, out = run("pactl", "-f", "json", "list", what, timeout=5)
    try:
        return _json.loads(out) if ok else []
    except ValueError:
        return []


def _name(obj):
    """pactl JSON sometimes gives "(null)" when the description has accents."""
    d = obj.get("description") or ""
    props = obj.get("properties") or {}
    if not d or d == "(null)":
        d = props.get("device.description") or props.get("node.nick") or obj.get("name", "?")
    return d


def _volume(obj):
    try:
        return int(next(iter(obj["volume"].values()))["value_percent"].rstrip("%"))
    except (KeyError, StopIteration, ValueError, AttributeError):
        return 0


def sound_state():
    _, info = run("pactl", "info", timeout=5)
    m_sink = re.search(r"Default Sink: (\S+)", info)
    m_src = re.search(r"Default Source: (\S+)", info)
    sinks = [{"name": x["name"], "label": _name(x), "volume": _volume(x), "mute": x.get("mute", False)}
             for x in _pactl_json("sinks")]
    sources = [{"name": x["name"], "label": _name(x), "volume": _volume(x), "mute": x.get("mute", False)}
               for x in _pactl_json("sources") if not x.get("monitor_source") and ".monitor" not in x["name"]]
    streams = []
    for x in _pactl_json("sink-inputs"):
        props = x.get("properties") or {}
        streams.append({"id": str(x["index"]), "app": props.get("application.name") or "Application",
                        "media": props.get("media.name") or "",
                        "icon": props.get("application.icon_name") or (props.get("application.process.binary") or ""),
                        "volume": _volume(x), "mute": x.get("mute", False)})
    return {"sink": m_sink.group(1) if m_sink else "", "source": m_src.group(1) if m_src else "",
            "sinks": sinks, "sources": sources, "streams": streams}


def vol_icon(v, mute):
    if mute or v == 0:
        return "audio-volume-muted-symbolic"
    return "audio-volume-low-symbolic" if v < 34 else "audio-volume-medium-symbolic" if v < 67 else "audio-volume-high-symbolic"


# --- Brightness (brightnessctl, ddcutil, hyprsunset) ------------------------------------
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "inkpaw")


def ddc_displays():
    """External monitors that answer DDC/CI (cached for a day: detection is slow)."""
    path = os.path.join(CACHE, "ddc-displays.json")
    try:
        if time.time() - os.path.getmtime(path) < 86400:
            with open(path) as f:
                return _json.load(f)
    except (OSError, ValueError):
        pass
    found = []
    _, out = run("ddcutil", "detect", "--brief", timeout=20)
    for block in out.split("\n\n"):
        if not block.startswith("Display"):
            continue                          # "Invalid display" = laptop panel etc.
        bus = re.search(r"/dev/i2c-(\d+)", block)
        mon = re.search(r"Monitor:\s+\w*:([^:\n]+)", block)
        conn = re.search(r"DRM connector:\s+\S+?-(\S+)", block)
        if bus:
            found.append({"bus": bus.group(1), "name": (mon.group(1) if mon else "External screen").strip(),
                          "connector": conn.group(1) if conn else ""})
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w") as f:
        _json.dump(found, f)
    return found


def brightness_state():
    screens = []
    _, out = run("brightnessctl", "-l", "-m", "-c", "backlight", timeout=5)
    for line in out.splitlines():
        f = line.split(",")
        if len(f) >= 5:
            screens.append({"key": "bl:" + f[0], "name": "Laptop screen", "kind": "backlight", "dev": f[0],
                            "value": int(f[3].rstrip("%") or 0)})
    _, kbd = run("brightnessctl", "-l", "-m", "-c", "leds", timeout=5)
    for line in kbd.splitlines():
        f = line.split(",")
        if len(f) >= 5 and "kbd_backlight" in f[0]:
            screens.append({"key": "kb:" + f[0], "name": "Keyboard backlight", "kind": "backlight", "dev": f[0],
                            "value": int(f[3].rstrip("%") or 0)})
    for d in ddc_displays():
        ok, v = run("ddcutil", "--bus", d["bus"], "getvcp", "10", "--brief", timeout=8)
        m = re.search(r"VCP 10 C (\d+) (\d+)", v)
        if ok and m:
            screens.append({"key": "ddc:" + d["bus"], "name": d["name"], "kind": "ddc", "dev": d["bus"],
                            "value": round(int(m.group(1)) * 100 / max(1, int(m.group(2))))})
    night = subprocess.run(["pgrep", "-x", "hyprsunset"], capture_output=True).returncode == 0
    temp = int(os.environ.get("NIGHTLIGHT_TEMP", "4500"))
    return {"screens": screens, "night": night, "temp": temp}


def set_brightness(screen, value):
    if screen["kind"] == "ddc":
        run("ddcutil", "--bus", screen["dev"], "setvcp", "10", str(value), "--noverify", timeout=10)
    else:
        run("brightnessctl", "-d", screen["dev"], "set", f"{max(1, value)}%", timeout=5)


# --- Battery & power (upower, powerprofilesctl) -------------------------------------------
def _upower_fields(path):
    _, out = run("upower", "-i", path, timeout=5)
    fields = {}
    for line in out.splitlines():
        m = re.match(r"\s+([a-z0-9 -]+):\s+(.+)$", line)
        if m:
            fields.setdefault(m.group(1).strip(), m.group(2).strip())
    return fields


def battery_state():
    _, paths = run("upower", "-e", timeout=5)
    main, others = None, []
    for path in paths.split():
        base = path.rsplit("/", 1)[-1]
        if base.startswith(("line_power", "DisplayDevice")):
            continue
        f = _upower_fields(path)
        if "percentage" not in f:
            continue
        dev = {"kind": base.split("_")[0], "model": f.get("model", "") or base,
               "percent": int(float(f["percentage"].rstrip("%").replace(",", "."))),
               "state": f.get("state", ""), "icon": f.get("icon-name", "").strip("'"),
               "time": f.get("time to empty") or f.get("time to full") or "",
               "rate": f.get("energy-rate", ""), "capacity": f.get("capacity", ""),
               "cycles": f.get("charge-cycles", "")}
        if dev["kind"] == "battery" and main is None:
            main = dev
        else:
            others.append(dev)
    ok, prof = run("powerprofilesctl", "get", timeout=5)
    return {"main": main, "others": others, "profile": prof.strip() if ok else ""}


# --- Notifications (swaync + history logged by hypr/scripts/notif-log.sh) -------------
STATE_DIR = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"), "inkpaw")
NOTIF_LOG = os.path.join(STATE_DIR, "notifications.jsonl")


def notifications_state():
    items = []
    try:
        with open(NOTIF_LOG) as f:
            for line in f:
                try:
                    items.append(_json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    _, dnd = run("swaync-client", "-D", timeout=3)
    return {"items": list(reversed(items))[:60], "dnd": dnd.strip() == "true"}


def ago(ts):
    s = int(time.time() - ts)
    for unit, size in (("d", 86400), ("h", 3600), ("min", 60)):
        if s >= size:
            return f"{s // size} {unit}"
    return "now"


# --- Media (playerctl / MPRIS) ---------------------------------------------------------
import hashlib  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402

ART_DIR = os.path.join(CACHE, "media-art")


def media_state(preferred=None):
    _, out = run("playerctl", "-l", timeout=3)
    players = [p for p in out.split() if p]
    if not players:
        return {"players": [], "player": None}
    info = {}
    for p in players:
        ok, meta = run("playerctl", "-p", p, "metadata", "--format",
                       "{{status}}\t{{artist}}\t{{title}}\t{{album}}\t{{mpris:artUrl}}\t{{position}}\t{{mpris:length}}",
                       timeout=3)
        f = (meta.rstrip("\n").split("\t") + [""] * 7)[:7] if ok else [""] * 7
        info[p] = {"name": p.split(".")[0], "status": f[0], "artist": f[1], "title": f[2], "album": f[3],
                   "art": f[4], "position": int(f[5] or 0) // 1_000_000, "length": int(f[6] or 0) // 1_000_000}
    current = preferred if preferred in info else next((p for p in players if info[p]["status"] == "Playing"), players[0])
    cur = dict(info[current], id=current)
    cur["art_file"] = art_file(cur["art"])
    return {"players": [(p, info[p]["name"]) for p in players], "player": cur}


def art_file(url):
    """Local path for an MPRIS art URL (file:// as is, http(s) downloaded once)."""
    if not url:
        return ""
    if url.startswith("file://"):
        return urllib.parse.unquote(url[7:])
    if url.startswith(("http://", "https://")):
        os.makedirs(ART_DIR, exist_ok=True)
        path = os.path.join(ART_DIR, hashlib.md5(url.encode()).hexdigest() + ".img")
        if not os.path.exists(path):
            try:
                with urllib.request.urlopen(url, timeout=5) as r, open(path, "wb") as f:
                    f.write(r.read())
            except OSError:
                return ""
        return path
    return ""


def mmss(sec):
    return f"{sec // 60}:{sec % 60:02d}"


# --- UI ----------------------------------------------------------------------------------
#  Minimal drop-down: ONE section at a time (the button you clicked), a one-line
#  header (title · status · small icon buttons · switch) and compact lists.
CSS = """
window.quickpanel-backdrop { background: transparent; }
.qp {
    background-color: @window_bg_color;
    border: 1px solid alpha(@accent_bg_color, 0.55);
    border-radius: 16px;
    box-shadow: 0 14px 40px alpha(black, 0.40);
    padding: 10px 8px 8px 8px;
}
.qp-head { padding: 2px 6px 8px 8px; }
.qp-title { font-weight: 800; font-size: 15px; }
.qp-status { font-size: 11px; opacity: 0.6; }
.qp-head button { min-width: 28px; min-height: 28px; padding: 0; }
.qp-list { background: transparent; }
.qp-list row { padding: 6px 8px; border-radius: 10px; background: transparent; min-height: 0; }
.qp-list row:hover { background: alpha(currentColor, 0.07); }
.qp-list row.qp-active { background: alpha(@accent_bg_color, 0.18); }
.qp-name { font-size: 13px; }
.qp-hint { font-size: 11px; opacity: 0.55; }
.qp-label { font-size: 10px; font-weight: 800; letter-spacing: 1px; opacity: 0.45; margin: 10px 8px 2px 8px; }
.qp-empty { font-size: 12px; opacity: 0.5; margin: 10px 8px; }
.qp-device { font-size: 11px; padding: 0 6px; min-height: 22px; opacity: 0.75; }
.qp-pct { font-size: 11px; opacity: 0.6; min-width: 34px; }
.qp-calendar { margin: 2px 6px 6px 6px; background: transparent; }
.qp-calendar > header { background: transparent; }
.qp-art { border-radius: 14px; }
.qp-art-fallback { border-radius: 14px; background: alpha(@accent_bg_color, 0.18); }
.qp-track { font-weight: 800; font-size: 15px; }
.qp-artist { font-size: 12px; opacity: 0.7; }
.qp-play { min-width: 46px; min-height: 46px; }
.qp-time { font-size: 10px; opacity: 0.55; }
"""

SECTIONS = ("wifi", "bluetooth", "sound", "brightness", "battery", "notifications", "calendar", "media")


def icon_button(icon, tip, cb, danger=False):
    """Small round flat icon button; danger=True marks a destructive one (forget,
    remove…: class qp-danger, only styled by skins)."""
    b = Gtk.Button(icon_name=icon, tooltip_text=tip, valign=Gtk.Align.CENTER)
    b.add_css_class("flat")
    b.add_css_class("circular")
    if danger:
        b.add_css_class("qp-danger")
    b.connect("clicked", lambda *_: cb())
    return b


def row(icon, name, hint="", suffix=(), active=False, on_click=None):
    """Compact list row: icon · name / hint · suffix widgets."""
    r = Gtk.ListBoxRow(activatable=on_click is not None)
    if active:
        r.add_css_class("qp-active")
    box = Gtk.Box(spacing=10)
    img = Gtk.Image(icon_name=icon, valign=Gtk.Align.CENTER)   # centered: skins draw a bubble
    box.append(img)
    texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
    n = Gtk.Label(label=name, xalign=0, ellipsize=3)
    n.add_css_class("qp-name")
    texts.append(n)
    if hint:
        h = Gtk.Label(label=hint, xalign=0, ellipsize=3)
        h.add_css_class("qp-hint")
        texts.append(h)
    box.append(texts)
    for w in suffix:
        box.append(w)
    r.set_child(box)
    r.on_click = on_click
    return r


def listbox():
    lb = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    lb.add_css_class("qp-list")
    lb.connect("row-activated", lambda _l, r: r.on_click and r.on_click())
    return lb


def clear(box):
    while (c := box.get_first_child()) is not None:
        box.remove(c)


def small_label(text, css):
    l = Gtk.Label(label=text, xalign=0)
    l.add_css_class(css)
    return l


class Panel(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.inkpaw.QuickPanel",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.win = None
        self.busy = False
        self.touched = {}
        self.sound_rows = {}

    # Resident: the app stays alive with its window hidden (started at login with
    # --daemon), so opening a section is instant. quickpanel.sh talks to it over
    # D-Bus (action "show", parameter "<tab> <edge> <offset> <side>"); a second
    # process with a tab argument does the same through the command line.
    # Same button again = hide, other button = show that section.
    def do_command_line(self, cmd):
        args = cmd.get_arguments()[1:]
        if args and args[0] == "--daemon":
            if self.win is None:              # build it now (hidden): the first opening is instant too
                self.build("wifi", present=False)
            return 0
        tab = args[0] if args and args[0] in SECTIONS else "wifi"
        self.show_from(tab, os.environ.get("QUICKPANEL_EDGE", "top"),
                       int(os.environ.get("QUICKPANEL_OFFSET", "56")), int(os.environ.get("QUICKPANEL_SIDE", "12")))
        return 0

    def on_show_action(self, _action, param):
        parts = (param.get_string() if param else "").split()
        tab = parts[0] if parts and parts[0] in SECTIONS else "wifi"
        try:
            edge, offset, side = parts[1], int(parts[2]), int(parts[3])
        except (IndexError, ValueError):
            edge, offset, side = "top", 56, 12
        self.show_from(tab, edge, offset, side)

    def show_from(self, tab, edge, offset, side):
        os.environ["QUICKPANEL_EDGE"], os.environ["QUICKPANEL_OFFSET"] = edge, str(offset)
        os.environ["QUICKPANEL_SIDE"] = str(side)
        if self.win is None:
            self.build(tab)
            return
        if self.win.get_visible() and self.stack.get_visible_child_name() == tab:
            self.hide_panel()
            return
        self.place_at(edge, offset, side)
        self.show(tab)
        self.win.present()

    def place_at(self, edge, offset, side):
        bottom = edge == "bottom"
        self.place.set_valign(Gtk.Align.END if bottom else Gtk.Align.START)
        self.place.set_margin_top(0 if bottom else offset)
        self.place.set_margin_bottom(offset if bottom else 0)
        self.place.set_margin_start(side)
        self.place.set_margin_end(side)

    def hide_panel(self):
        """Close = hide (the process stays for the next opening)."""
        if self.win is not None:
            self.win.set_visible(False)

    def visible(self):
        return self.win is not None and self.win.get_visible()

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.hold()                                   # stay alive with no window (resident)
        act = Gio.SimpleAction.new("show", GLib.VariantType.new("s"))
        act.connect("activate", self.on_show_action)
        self.add_action(act)
        css = Gtk.CssProvider()
        css.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        # skin stylesheet on top of the base one (missing file = base look)
        if SKIN != "default" and os.path.isfile(SKIN_CSS):
            skin = Gtk.CssProvider()
            skin.load_from_path(SKIN_CSS)
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), skin,
                                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)

    def build(self, tab, present=True):
        win = self.win = Adw.ApplicationWindow(application=self)
        win.add_css_class("quickpanel-backdrop")
        LayerShell.init_for_window(win)
        LayerShell.set_layer(win, LayerShell.Layer.TOP)
        LayerShell.set_namespace(win, "quickpanel")
        LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.ON_DEMAND)
        LayerShell.set_exclusive_zone(win, -1)
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM, LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(win, edge, True)

        overlay = Gtk.Overlay()
        backdrop = Gtk.Box(hexpand=True, vexpand=True)
        click = Gtk.GestureClick()
        click.connect("pressed", lambda *_: self.hide_panel())
        backdrop.add_controller(click)
        overlay.set_child(backdrop)

        # Drops down under the bar (or up above it when BAR_POSITION=bottom)
        offset = int(os.environ.get("QUICKPANEL_OFFSET", "56"))
        bottom = os.environ.get("QUICKPANEL_EDGE", "top") == "bottom"
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER,
                        valign=Gtk.Align.END if bottom else Gtk.Align.START, width_request=360)
        panel.set_margin_bottom(offset) if bottom else panel.set_margin_top(offset)
        panel.add_css_class("qp")
        self.sniff_cat = None
        cat = skin_cat("head-pate") if not bottom else None
        self.place = self.cat_holder(panel, cat) if cat else panel     # the widget that is positioned
        side = int(os.environ.get("QUICKPANEL_SIDE", "12"))
        self.place.set_margin_start(side)
        self.place.set_margin_end(side)
        overlay.add_overlay(self.place)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=120,
                               vhomogeneous=False, interpolate_size=True)
        self.toasts = Adw.ToastOverlay(child=self.stack)
        panel.append(self.toasts)
        self.stack.add_named(self.build_wifi(), "wifi")
        self.stack.add_named(self.build_bluetooth(), "bluetooth")
        self.stack.add_named(self.build_sound(), "sound")
        self.stack.add_named(self.build_brightness(), "brightness")
        self.stack.add_named(self.build_battery(), "battery")
        self.stack.add_named(self.build_notifications(), "notifications")
        self.stack.add_named(self.build_calendar(), "calendar")
        self.stack.add_named(self.build_media(), "media")

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", lambda _c, k, *_: (self.hide_panel(), True)[1] if k == Gdk.KEY_Escape else False)
        win.add_controller(keys)
        win.connect("close-request", lambda *_: (self.hide_panel(), True)[1])   # never destroyed
        win.set_content(overlay)
        if present:
            self.show(tab)
            win.present()
        else:
            # resident start: map it once, invisible, then hide it, so even the first
            # opening skips the first-map cost (~1 s)
            self.stack.set_visible_child_name(tab)
            win.set_opacity(0)
            win.present()
            GLib.timeout_add(500, lambda: (win.set_visible(False), win.set_opacity(1), False)[2])
        GLib.timeout_add_seconds(3, self.tick)
        GLib.timeout_add_seconds(2, self.tick_sound)
        GLib.timeout_add_seconds(1, self.tick_media)

    def cat_holder(self, panel, cat):
        """Skin only: wrap the panel so a cat can sniff under its bottom edge (Bluetooth
        section, as in the mockup). The holder takes the panel's place / margins; the
        cat is an overlay child over the panel's bottom-right corner + a strip under it."""
        holder = Gtk.Overlay(halign=panel.get_halign(), valign=panel.get_valign())
        holder.set_margin_top(panel.get_margin_top())
        panel.set_margin_top(0)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        col.append(panel)
        self.sniff_space = Gtk.Box(height_request=36, visible=False)    # strip the cat stands in
        click = Gtk.GestureClick()
        click.connect("pressed", lambda *_: self.hide_panel())           # still "outside the panel"
        self.sniff_space.add_controller(click)
        col.append(self.sniff_space)
        holder.set_child(col)
        img = Gtk.Image.new_from_file(cat)
        img.set_pixel_size(64)
        img.set_halign(Gtk.Align.END)
        img.set_valign(Gtk.Align.END)
        img.set_margin_end(26)
        img.set_can_target(False)                                        # clicks go to the strip
        img.set_visible(False)
        img.add_css_class("qp-sniff-cat")
        holder.add_overlay(img)
        self.sniff_cat = img
        return holder

    # Calendar under the clock on the LEFT, every other section on the RIGHT
    # (under the status / system buttons of the bar)
    LEFT_TABS = ("calendar",)

    def show(self, tab):
        self.place.set_halign(Gtk.Align.START if tab in self.LEFT_TABS else Gtk.Align.END)
        self.stack.set_visible_child_name(tab)
        if self.sniff_cat is not None:                                   # skin cat: Bluetooth only
            self.sniff_cat.set_visible(tab == "bluetooth")
            self.sniff_space.set_visible(tab == "bluetooth")
        self.refresh(tab)

    # --- common pieces ---
    def section(self, title, buttons=(), switch=None, min_height=0, max_height=440):
        """Section page = header + scrollable body; returns (page, status label, body box).
        min_height / max_height: size of the scrollable list (px)."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        head = Gtk.Box(spacing=4)
        head.add_css_class("qp-head")
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        titles.append(small_label(title, "qp-title"))
        status = small_label("", "qp-status")
        status.set_ellipsize(3)
        titles.append(status)
        head.append(titles)
        for b in buttons:
            head.append(b)
        if switch is not None:
            switch.set_valign(Gtk.Align.CENTER)
            switch.set_margin_start(6)
            head.append(switch)
        page.append(head)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll = Gtk.ScrolledWindow(child=body, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                    propagate_natural_height=True, max_content_height=max_height,
                                    min_content_height=min_height)
        page.append(scroll)
        return page, status, body

    def tick(self):
        if not self.visible():
            return True
        tab = self.stack.get_visible_child_name()
        if not self.busy and tab not in ("sound", "brightness", "media", "calendar"):   # own timers / static
            self.refresh(tab)
        return True

    def tick_media(self):
        if self.visible() and self.stack.get_visible_child_name() == "media" and not self.busy:
            self.refresh("media")
        return True

    def tick_sound(self):
        if self.visible() and self.stack.get_visible_child_name() == "sound":
            background(sound_state, self.render_sound)
        return True

    def refresh(self, tab=None):
        tab = tab or self.stack.get_visible_child_name()
        fn, cb = {"wifi": (wifi_state, self.render_wifi), "bluetooth": (bt_state, self.render_bt),
                  "sound": (sound_state, self.render_sound), "brightness": (brightness_state, self.render_brightness),
                  "battery": (battery_state, self.render_battery),
                  "notifications": (notifications_state, self.render_notifications),
                  "calendar": (lambda: None, self.render_calendar),
                  "media": (lambda: media_state(getattr(self, "media_player", None)), self.render_media)}[tab]
        background(fn, cb)

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=esc(text), timeout=2))

    def act(self, argv, ok_msg, fail_msg, timeout=30):
        self.busy = True

        def done(res):
            self.busy = False
            self.toast(ok_msg if res[0] else fail_msg)
            self.refresh()
        background(lambda: run(*argv, timeout=timeout), done)

    def launch(self, argv):
        subprocess.Popen(argv, start_new_session=True)
        self.hide_panel()

    # --- Wi-Fi ---
    def build_wifi(self):
        self.wifi_switch = Gtk.Switch()
        self.wifi_handler = self.wifi_switch.connect("notify::active", lambda sw, _p: self.act(
            ["nmcli", "radio", "wifi", "on" if sw.get_active() else "off"],
            f"Wi-Fi {'on' if sw.get_active() else 'off'}", "Failed"))
        page, self.wifi_status, self.wifi_body = self.section("Wi-Fi", (
            icon_button("view-refresh-symbolic", "Scan again",
                        lambda: self.act(["nmcli", "dev", "wifi", "rescan"], "Scanning…", "Scan failed")),
            icon_button("emblem-system-symbolic", "All connections (NetworkManager)",
                        lambda: self.launch(["nm-connection-editor"])),
        ), self.wifi_switch)
        return page

    def render_wifi(self, st):
        self.wifi_switch.handler_block(self.wifi_handler)
        self.wifi_switch.set_active(st["enabled"])
        self.wifi_switch.handler_unblock(self.wifi_handler)
        self.wifi_status.set_label(" · ".join(x for x in (st["conn"] or ("Not connected" if st["enabled"] else "Off"),
                                                         st["ip"].split("/")[0] if st["ip"] else "") if x))
        clear(self.wifi_body)
        if not st["enabled"]:
            return
        lb = listbox()
        for n in st["networks"]:
            if n["active"]:
                suffix = [icon_button("network-offline-symbolic", "Disconnect",
                                      lambda: self.act(["nmcli", "con", "down", "id", st["conn"]], "Disconnected", "Failed")),
                          icon_button("user-trash-symbolic", "Forget",
                                      lambda: self.act(["nmcli", "con", "delete", "id", st["conn"]], "Forgotten", "Failed"),
                                      danger=True)]
                lb.append(row(signal_icon(n["signal"]), n["ssid"], "Connected", suffix, active=True))
            else:
                suffix = [Gtk.Image.new_from_icon_name("channel-secure-symbolic")] if n["secure"] else []
                lb.append(row(signal_icon(n["signal"]), n["ssid"], "Saved" if n["saved"] else "",
                              suffix, on_click=lambda n=n: self.connect_wifi(n)))
        self.wifi_body.append(lb)
        if not st["networks"]:
            self.wifi_body.append(small_label("No network found", "qp-empty"))

    def connect_wifi(self, n):
        if n["saved"]:
            self.act(["nmcli", "con", "up", "id", n["ssid"]], f"Connected to {n['ssid']}", "Could not connect")
            return
        if not n["secure"]:
            self.act(["nmcli", "dev", "wifi", "connect", n["ssid"]], f"Connected to {n['ssid']}", "Connection failed")
            return
        dlg = Adw.AlertDialog(heading=esc(n["ssid"]), body="Password")
        entry = Gtk.PasswordEntry(show_peek_icon=True, activates_default=True)
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("connect", "Connect")
        dlg.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("connect")
        dlg.connect("response", lambda _d, r: r == "connect" and entry.get_text() and self.act(
            ["nmcli", "dev", "wifi", "connect", n["ssid"], "password", entry.get_text()],
            f"Connected to {n['ssid']}", "Wrong password or connection failed", timeout=45))
        dlg.present(self.win)
        entry.grab_focus()

    # --- Bluetooth ---
    def build_bluetooth(self):
        self.bt_switch = Gtk.Switch()
        self.bt_switch.add_css_class("qp-bt")             # skins tint the Bluetooth switch
        self.bt_handler = self.bt_switch.connect("notify::active", lambda sw, _p: self.act(
            ["bluetoothctl", "power", "on" if sw.get_active() else "off"],
            f"Bluetooth {'on' if sw.get_active() else 'off'}", "Failed"))
        self.scan_btn = icon_button("system-search-symbolic", "Look for new devices (12 s)", self.bt_scan)
        page, self.bt_status, self.bt_body = self.section("Bluetooth", (
            self.scan_btn,
            icon_button("emblem-system-symbolic", "Bluetooth manager (Blueman)", lambda: self.launch(["blueman-manager"])),
        ), self.bt_switch)
        return page

    def bt_scan(self):
        self.scan_btn.set_sensitive(False)
        self.bt_status.set_label("Scanning…")

        def done(_r):
            self.scan_btn.set_sensitive(True)
            self.refresh("bluetooth")
        background(lambda: run("bluetoothctl", "--timeout", "12", "scan", "on", timeout=20), done)
        GLib.timeout_add_seconds(3, lambda: (self.refresh("bluetooth"), False)[1])

    def render_bt(self, st):
        self.bt_switch.handler_block(self.bt_handler)
        self.bt_switch.set_active(st["powered"])
        self.bt_switch.handler_unblock(self.bt_handler)
        connected = [d["name"] for d in st["devices"] if d["connected"]]
        if self.scan_btn.get_sensitive():
            self.bt_status.set_label(", ".join(connected) if connected else ("On" if st["powered"] else "Off"))
        clear(self.bt_body)
        if not st["powered"]:
            return
        paired = [d for d in st["devices"] if d["paired"]]
        nearby = [d for d in st["devices"] if not d["paired"]]
        if paired:
            lb = listbox()
            for d in paired:
                hint = "Connected" if d["connected"] else ""
                if d["battery"] is not None:
                    hint = f"{hint} · {d['battery']}%" if hint else f"{d['battery']}%"
                verb = "disconnect" if d["connected"] else "connect"
                rm = icon_button("user-trash-symbolic", "Remove",
                                 lambda d=d: self.act(["bluetoothctl", "remove", d["mac"]], f"{d['name']} removed", "Failed"),
                                 danger=True)
                lb.append(row(bt_icon(d["icon"]), d["name"], hint, [rm], active=d["connected"],
                              on_click=lambda d=d, v=verb: self.act(["bluetoothctl", v, d["mac"]],
                                                                    f"{d['name']}: {v}ed", f"Could not {v}")))
            self.bt_body.append(lb)
        else:
            self.bt_body.append(small_label("No paired device · 󰍉 to look for one", "qp-empty"))
        if nearby:
            self.bt_body.append(small_label("NEARBY", "qp-label"))
            lb = listbox()
            for d in nearby:
                lb.append(row(bt_icon(d["icon"]), d["name"], "Click to pair",
                              on_click=lambda d=d: self.act(
                                  ["sh", "-c", f"bluetoothctl pair {d['mac']} && bluetoothctl trust {d['mac']} "
                                               f"&& bluetoothctl connect {d['mac']}"],
                                  f"{d['name']} connected", "Pairing failed", timeout=45)))
            self.bt_body.append(lb)

    # --- Sound ---
    def build_sound(self):
        page, self.sound_status, body = self.section("Sound", (
            icon_button("emblem-system-symbolic", "Advanced mixer (pavucontrol)", lambda: self.launch(["pavucontrol"])),
        ))
        self.out_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.in_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.apps_label = small_label("APPS", "qp-label")
        self.apps_list = listbox()
        for w in (self.out_box, self.in_box, self.apps_label, self.apps_list):
            body.append(w)
        self.sinks, self.sources = [], []
        return page

    def device_button(self, kind):
        """Small flat button showing the device name; popover lists the devices."""
        btn = Gtk.MenuButton(halign=Gtk.Align.START)
        btn.add_css_class("flat")
        btn.add_css_class("qp-device")
        lb = listbox()
        pop = Gtk.Popover(child=lb)
        btn.set_popover(pop)
        btn.devlist = lb
        btn.kind = kind
        return btn

    def fill_devices(self, btn, items, current):
        clear(btn.devlist)
        for it in items:
            setter = "set-default-sink" if btn.kind == "out" else "set-default-source"
            btn.devlist.append(row("object-select-symbolic" if it["name"] == current else "", it["label"],
                                   on_click=lambda it=it: (btn.get_popover().popdown(),
                                                           self.act(["pactl", setter, it["name"]], "Device changed", "Failed"))))
        cur = next((i["label"] for i in items if i["name"] == current), "")
        btn.set_label(cur)                       # the MenuButton draws its own arrow
        btn.set_sensitive(len(items) > 1)        # nothing to choose with one device

    def volume_row(self, key, icon, set_vol, toggle_mute):
        r = Gtk.ListBoxRow(activatable=False)
        box = Gtk.Box(spacing=8)
        mute = Gtk.Button(icon_name=icon, valign=Gtk.Align.CENTER, tooltip_text="Mute / unmute")
        mute.add_css_class("flat")
        mute.add_css_class("circular")
        mute.connect("clicked", lambda *_: background(toggle_mute, lambda _r: background(sound_state, self.render_sound)))
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_hexpand(True)
        scale.set_draw_value(False)
        pct = small_label("", "qp-pct")
        pct.set_xalign(1)

        def moved(sc):
            v = int(sc.get_value())
            pct.set_label(f"{v}%")
            if getattr(sc, "_quiet", False):     # set by a refresh, not by the user
                return
            self.touched[key] = time.monotonic()
            if getattr(sc, "_pending", None):
                GLib.source_remove(sc._pending)

            def fire():
                sc._pending = None
                background(lambda: set_vol(v))
                return False
            sc._pending = GLib.timeout_add(60, fire)
        scale.connect("value-changed", moved)
        for w in (mute, scale, pct):
            box.append(w)
        r.set_child(box)
        self.sound_rows[key] = (r, scale, mute, pct)
        return r

    def update_volume(self, key, volume, muted, icon=None):
        _r, scale, mute, pct = self.sound_rows[key]
        mute.set_icon_name(icon or vol_icon(volume, muted))
        if time.monotonic() - self.touched.get(key, 0) > 1.5:
            scale._quiet = True
            scale.set_value(volume)
            pct.set_label(f"{volume}%")
            scale._quiet = False

    def render_sound(self, st):
        sink = next((x for x in st["sinks"] if x["name"] == st["sink"]), None)
        src = next((x for x in st["sources"] if x["name"] == st["source"]), None)
        self.sound_status.set_label(sink["label"] if sink else "No output")

        # output: device button + volume row (created once)
        if "out" not in self.sound_rows:
            self.out_dev = self.device_button("out")
            lb = listbox()
            lb.append(self.volume_row("out", "audio-volume-high-symbolic",
                                      lambda v: run("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{v}%"),
                                      lambda: run("pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle")))
            self.out_box.append(lb)
            self.out_box.append(self.out_dev)
        sig = ([x["name"] for x in st["sinks"]], st["sink"])
        if sig != self.sinks:                    # only when devices / default changed
            self.fill_devices(self.out_dev, st["sinks"], st["sink"])
            self.sinks = sig
        if sink:
            self.update_volume("out", sink["volume"], sink["mute"])

        # input
        self.in_box.set_visible(bool(src))
        if src:
            if "in" not in self.sound_rows:
                self.in_dev = self.device_button("in")
                self.in_box.append(small_label("MICROPHONE", "qp-label"))
                lb = listbox()
                lb.append(self.volume_row("in", "microphone-sensitivity-high-symbolic",
                                          lambda v: run("pactl", "set-source-volume", "@DEFAULT_SOURCE@", f"{v}%"),
                                          lambda: run("pactl", "set-source-mute", "@DEFAULT_SOURCE@", "toggle")))
                self.in_box.append(lb)
                self.in_box.append(self.in_dev)
            sig = ([x["name"] for x in st["sources"]], st["source"])
            if sig != self.sources:
                self.fill_devices(self.in_dev, st["sources"], st["source"])
                self.sources = sig
            self.update_volume("in", src["volume"], src["mute"],
                               "microphone-disabled-symbolic" if src["mute"] else "microphone-sensitivity-high-symbolic")

        # applications: one compact row each (name above the slider)
        live = set()
        for x in st["streams"]:
            key = "app:" + x["id"]
            live.add(key)
            if key not in self.sound_rows:
                sid = x["id"]
                r = self.volume_row(key, "audio-volume-high-symbolic",
                                    lambda v, i=sid: run("pactl", "set-sink-input-volume", i, f"{v}%"),
                                    lambda i=sid: run("pactl", "set-sink-input-mute", i, "toggle"))
                box = r.get_child()
                name = small_label(x["app"], "qp-hint")
                name.set_width_chars(9)
                name.set_max_width_chars(9)
                name.set_ellipsize(3)
                box.insert_child_after(name, box.get_first_child())
                self.apps_list.append(r)
            self.update_volume(key, x["volume"], x["mute"])
        for key in [k for k in self.sound_rows if k.startswith("app:") and k not in live]:
            self.apps_list.remove(self.sound_rows.pop(key)[0])
        self.apps_label.set_visible(bool(live))
        self.apps_list.set_visible(bool(live))

    # --- Brightness ---
    def level_row(self, key, icon, title, lo, hi, setter, unit="%"):
        """Row: icon · title above a slider · value. Updated in place."""
        r = Gtk.ListBoxRow(activatable=False)
        box = Gtk.Box(spacing=10)
        box.append(Gtk.Image(icon_name=icon, valign=Gtk.Align.CENTER))
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        col.append(small_label(title, "qp-hint"))
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, 1)
        scale.set_draw_value(False)
        col.append(scale)
        box.append(col)
        val = small_label("", "qp-pct")
        val.set_xalign(1)
        val.set_valign(Gtk.Align.END)
        box.append(val)

        def moved(sc):
            v = int(sc.get_value())
            val.set_label(f"{v}{unit}")
            if getattr(sc, "_quiet", False):
                return
            self.touched[key] = time.monotonic()
            if getattr(sc, "_pending", None):
                GLib.source_remove(sc._pending)

            def fire():
                sc._pending = None
                background(lambda: setter(v))
                return False
            sc._pending = GLib.timeout_add(250, fire)      # DDC is slow: coalesce moves
        scale.connect("value-changed", moved)
        r.set_child(box)
        self.sound_rows[key] = (r, scale, None, val)
        return r

    def set_level(self, key, value, unit="%"):
        _r, scale, _m, val = self.sound_rows[key]
        if time.monotonic() - self.touched.get(key, 0) > 2:
            scale._quiet = True
            scale.set_value(value)
            val.set_label(f"{value}{unit}")
            scale._quiet = False

    def build_brightness(self):
        page, self.bri_status, body = self.section("Brightness", (
            icon_button("view-refresh-symbolic", "Detect screens again", self.redetect_screens),
        ))
        self.bri_list = listbox()
        body.append(self.bri_list)
        body.append(small_label("NIGHT LIGHT", "qp-label"))
        self.night_list = listbox()
        self.night_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.night_handler = self.night_switch.connect("notify::active", self.on_night_toggle)
        self.night_list.append(row("weather-clear-night-symbolic", "Night light", "Warmer colors, easier on the eyes",
                                   [self.night_switch]))
        self.night_list.append(self.level_row("temp", "color-select-symbolic", "Temperature", 2500, 6500,
                                              self.set_night_temp, unit=" K"))
        body.append(self.night_list)
        return page

    def redetect_screens(self):
        try:
            os.remove(os.path.join(CACHE, "ddc-displays.json"))
        except OSError:
            pass
        self.bri_status.set_label("Detecting screens…")
        self.refresh("brightness")

    def render_brightness(self, st):
        for scr in st["screens"]:
            if scr["key"] not in self.sound_rows:
                icon = "keyboard-brightness-symbolic" if scr["key"].startswith("kb:") else "display-brightness-symbolic"
                self.bri_list.append(self.level_row(scr["key"], icon, scr["name"], 0, 100,
                                                    lambda v, scr=scr: set_brightness(scr, v)))
            self.set_level(scr["key"], scr["value"])
        self.bri_status.set_label(" · ".join(f"{s['name'].split()[0]} {s['value']}%" for s in st["screens"]
                                             if not s["key"].startswith("kb:")) or "No adjustable screen")
        self.night_switch.handler_block(self.night_handler)
        self.night_switch.set_active(st["night"])
        self.night_switch.handler_unblock(self.night_handler)
        self.set_level("temp", st["temp"], unit=" K")
        self.sound_rows["temp"][0].set_sensitive(st["night"])

    def on_night_toggle(self, sw, _p):
        scripts = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "hypr", "scripts")
        self.act([os.path.join(scripts, "nightlight.sh")], "Night light " + ("on" if sw.get_active() else "off"), "Failed")

    def set_night_temp(self, value):
        os.environ["NIGHTLIGHT_TEMP"] = str(value)
        cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        run(os.path.join(cfg, "hypr", "scripts", "menus", "settings.sh"), "set", "NIGHTLIGHT_TEMP", str(value))
        if not run("hyprctl", "hyprsunset", "temperature", str(value), timeout=5)[0]:
            # no IPC: restart hyprsunset with the new temperature
            run("pkill", "-x", "hyprsunset")
            subprocess.Popen(["hyprsunset", "-t", str(value)], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # --- Battery ---
    def build_battery(self):
        cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        page, self.bat_status, body = self.section("Battery", (
            icon_button("system-shutdown-symbolic", "Power menu",
                        lambda: self.launch([os.path.join(cfg, "hypr", "scripts", "menus", "power.sh")])),
        ))
        self.bat_main = listbox()
        body.append(self.bat_main)
        body.append(small_label("POWER MODE", "qp-label"))
        self.profiles = Adw.ToggleGroup(margin_start=6, margin_end=6, margin_top=2, margin_bottom=4)
        for name, label, icon in (("power-saver", "Saver", "power-profile-power-saver-symbolic"),
                                  ("balanced", "Balanced", "power-profile-balanced-symbolic"),
                                  ("performance", "Performance", "power-profile-performance-symbolic")):
            t = Adw.Toggle(name=name, label=label, tooltip=label)
            self.profiles.add(t)
        self.profile_handler = self.profiles.connect("notify::active-name", self.on_profile)
        body.append(self.profiles)
        self.dev_label = small_label("DEVICES", "qp-label")
        self.dev_list = listbox()
        body.append(self.dev_label)
        body.append(self.dev_list)
        return page

    def render_battery(self, st):
        b = st["main"]
        clear(self.bat_main)
        if b:
            state = {"charging": "Charging", "discharging": "On battery", "fully-charged": "Fully charged",
                     "pending-charge": "Not charging", "empty": "Empty"}.get(b["state"], b["state"])
            self.bat_status.set_label(f"{b['percent']}% · {state}")
            when = (f"{b['time']} left" if b["state"] == "discharging" else f"full in {b['time']}") if b["time"] else ""
            rate = b["rate"] if b["rate"] and not b["rate"].startswith("0 ") else ""
            self.bat_main.append(row(b["icon"] or "battery-symbolic", f"{b['percent']}%  ·  {state}",
                                     " · ".join(x for x in (when, rate) if x)))
            health = " · ".join(x for x in (f"health {b['capacity']}" if b["capacity"] else "",
                                            f"{b['cycles']} cycles" if b["cycles"] else "", b["model"]) if x)
            if health:
                self.bat_main.append(row("emblem-ok-symbolic", "Battery health", health))
        else:
            self.bat_status.set_label("No battery (desktop)")
        self.profiles.set_visible(bool(st["profile"]))
        if st["profile"]:
            self.profiles.handler_block(self.profile_handler)
            self.profiles.set_active_name(st["profile"])
            self.profiles.handler_unblock(self.profile_handler)
        clear(self.dev_list)
        for d in st["others"]:
            icon = {"mouse": "input-mouse-symbolic", "keyboard": "input-keyboard-symbolic",
                    "headset": "audio-headset-symbolic", "headphones": "audio-headphones-symbolic",
                    "gaming": "input-gaming-symbolic", "phone": "phone-symbolic"}.get(d["kind"], d["icon"] or "battery-symbolic")
            low = " · low!" if d["percent"] <= 15 and d["state"] != "charging" else ""
            self.dev_list.append(row(icon, d["model"], f"{d['percent']}%{low}"))
        self.dev_label.set_visible(bool(st["others"]))

    def on_profile(self, group, _p):
        name = group.get_active_name()
        if name:
            self.act(["powerprofilesctl", "set", name], f"Power mode: {name}", "Failed")

    # --- Notifications ---
    def build_notifications(self):
        self.dnd_btn = Gtk.ToggleButton(icon_name="notifications-disabled-symbolic", valign=Gtk.Align.CENTER,
                                        tooltip_text="Do not disturb")
        self.dnd_btn.add_css_class("flat")
        self.dnd_btn.add_css_class("circular")
        self.dnd_handler = self.dnd_btn.connect("toggled", lambda b: self.act(
            ["swaync-client", "-d", "-sw"], "Do not disturb " + ("on" if b.get_active() else "off"), "Failed"))
        page, self.notif_status, self.notif_body = self.section("Notifications", (
            self.dnd_btn,
            icon_button("edit-clear-all-symbolic", "Clear all", self.clear_notifications),
            icon_button("emblem-system-symbolic", "Notification center (swaync)",
                        lambda: (subprocess.Popen(["swaync-client", "-t", "-sw"], start_new_session=True), self.hide_panel())),
        ))
        return page

    def clear_notifications(self):
        scripts = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "hypr", "scripts")
        self.act(["sh", "-c", f"{scripts}/notif-log.sh clear; swaync-client -C"], "Cleared", "Failed")

    def notif_icon(self, n):
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        for name in (n.get("entry"), (n.get("app") or "").lower().replace(" ", "-"), (n.get("app") or "").lower()):
            if name and theme.has_icon(name):
                return name
        return "dialog-warning-symbolic" if n.get("urgency") == "Critical" else "preferences-system-notifications-symbolic"

    def render_notifications(self, st):
        self.dnd_btn.handler_block(self.dnd_handler)
        self.dnd_btn.set_active(st["dnd"])
        self.dnd_btn.handler_unblock(self.dnd_handler)
        n = len(st["items"])
        self.notif_status.set_label(" · ".join(x for x in (f"{n} notification{'s' if n != 1 else ''}" if n else "Nothing new",
                                                           "do not disturb" if st["dnd"] else "") if x))
        clear(self.notif_body)
        if not st["items"]:
            self.notif_body.append(small_label("You're all caught up", "qp-empty"))
            return
        scripts = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "hypr", "scripts")
        today = time.strftime("%Y-%m-%d")
        groups = {}
        for it in st["items"]:
            day = "TODAY" if time.strftime("%Y-%m-%d", time.localtime(it.get("time", 0))) == today else "EARLIER"
            groups.setdefault(day, []).append(it)
        for day in ("TODAY", "EARLIER"):
            if day not in groups:
                continue
            if len(groups) > 1:
                self.notif_body.append(small_label(day, "qp-label"))
            lb = listbox()
            for it in groups[day]:
                body = " ".join((it.get("body") or "").split())
                hint = " · ".join(x for x in (it.get("app"), ago(it.get("time", 0)), body[:60]) if x)
                rm = icon_button("window-close-symbolic", "Dismiss",
                                 lambda i=it: self.act([f"{scripts}/notif-log.sh", "remove", i["id"]], "Dismissed", "Failed"))
                entry = it.get("entry")
                lb.append(row(self.notif_icon(it), it.get("summary") or it.get("app") or "Notification", hint, [rm],
                              active=it.get("urgency") == "Critical",
                              on_click=(lambda e=entry: self.launch(["gtk-launch", e])) if entry else None))
            self.notif_body.append(lb)

    # --- Calendar ---
    def build_calendar(self):
        page, self.cal_status, body = self.section("Calendar", (
            icon_button("go-home-symbolic", "Today", self.calendar_today),
        ), max_height=520)
        self.calendar = Gtk.Calendar(show_week_numbers=True)
        self.calendar.add_css_class("qp-calendar")
        self.calendar.connect("day-selected", lambda c: self.render_calendar(None))
        body.append(self.calendar)
        return page

    def calendar_today(self):
        self.calendar.select_day(GLib.DateTime.new_now_local())
        self.render_calendar(None)

    def render_calendar(self, _st):
        now = GLib.DateTime.new_now_local()
        sel = self.calendar.get_date()
        txt = sel.format("%A %d %B %Y")
        if sel.get_ymd() == now.get_ymd():
            txt = now.format("%A %d %B · %H:%M")
        else:
            days = int((sel.to_unix() - now.to_unix()) // 86400 + (1 if sel.to_unix() > now.to_unix() else 0))
            txt += f" · {'in ' if days > 0 else ''}{abs(days)} day{'s' if abs(days) != 1 else ''}{' ago' if days < 0 else ''}"
        self.cal_status.set_label(txt.capitalize())

    # --- Media ---
    def build_media(self):
        self.player_btn = Gtk.MenuButton(icon_name="view-more-symbolic", tooltip_text="Choose the player",
                                         valign=Gtk.Align.CENTER)
        self.player_btn.add_css_class("flat")
        self.player_btn.add_css_class("circular")
        self.player_list = listbox()
        self.player_btn.set_popover(Gtk.Popover(child=self.player_list))
        page, self.media_status, body = self.section("Media", (self.player_btn,))
        self.media_body = body
        self.media_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_start=6, margin_end=6)
        top = Gtk.Box(spacing=12)
        self.art = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, width_request=96, height_request=96)
        self.art.add_css_class("qp-art")
        self.art.set_overflow(Gtk.Overflow.HIDDEN)
        self.art_fallback = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        self.art_fallback.set_pixel_size(40)
        self.art_fallback.set_size_request(96, 96)
        self.art_fallback.add_css_class("qp-art-fallback")
        if cover_cat := skin_cat("head-moumoute"):        # skin: a cat as the "no cover" picture
            self.art_fallback.set_from_file(cover_cat)
            self.art_fallback.set_pixel_size(72)
        art_stack = Gtk.Stack()
        art_stack.add_named(self.art, "art")
        art_stack.add_named(self.art_fallback, "none")
        self.art_stack = art_stack
        top.append(art_stack)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        self.track = small_label("", "qp-track")
        self.track.set_ellipsize(3)
        self.track.set_wrap(False)
        self.artist = small_label("", "qp-artist")
        self.artist.set_ellipsize(3)
        texts.append(self.track)
        texts.append(self.artist)
        top.append(texts)
        self.media_box.append(top)

        prog = Gtk.Box(spacing=8)
        self.pos_lbl = small_label("0:00", "qp-time")
        self.len_lbl = small_label("", "qp-time")
        self.seek = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.seek.set_hexpand(True)
        self.seek.set_draw_value(False)
        self.seek.connect("change-value", self.on_seek)
        for w in (self.pos_lbl, self.seek, self.len_lbl):
            prog.append(w)
        self.prog_box = prog
        self.media_box.append(prog)

        ctl = Gtk.Box(spacing=18, halign=Gtk.Align.CENTER, margin_bottom=4)
        self.prev_btn = icon_button("media-skip-backward-symbolic", "Previous", lambda: self.media_cmd("previous"))
        self.play_btn = icon_button("media-playback-start-symbolic", "Play / pause", lambda: self.media_cmd("play-pause"))
        self.play_btn.remove_css_class("flat")
        self.play_btn.add_css_class("suggested-action")
        self.play_btn.add_css_class("qp-play")
        self.next_btn = icon_button("media-skip-forward-symbolic", "Next", lambda: self.media_cmd("next"))
        for w in (self.prev_btn, self.play_btn, self.next_btn):
            ctl.append(w)
        self.media_box.append(ctl)
        body.append(self.media_box)
        self.media_empty = small_label("Nothing is playing", "qp-empty")
        body.append(self.media_empty)
        self.media_players = []
        self.media_art_path = None
        return page

    def media_cmd(self, cmd, *args):
        pid = getattr(self, "media_id", None)
        argv = ["playerctl"] + (["-p", pid] if pid else []) + [cmd] + list(args)
        background(lambda: run(*argv, timeout=5), lambda _r: self.refresh("media"))

    def on_seek(self, _scale, _scroll, value):
        self.touched["seek"] = time.monotonic()
        self.media_cmd("position", str(int(value)))
        return False

    def render_media(self, st):
        p = st["player"]
        self.media_box.set_visible(p is not None)
        self.media_empty.set_visible(p is None)
        self.player_btn.set_visible(len(st["players"]) > 1)
        if [x[0] for x in st["players"]] != self.media_players:
            clear(self.player_list)
            for pid, name in st["players"]:
                self.player_list.append(row("multimedia-player-symbolic", name.capitalize(),
                                            on_click=lambda pid=pid: (self.player_btn.get_popover().popdown(),
                                                                      setattr(self, "media_player", pid),
                                                                      self.refresh("media"))))
            self.media_players = [x[0] for x in st["players"]]
        if not p:
            self.media_status.set_label("No player")
            return
        self.media_id = p["id"]
        self.media_status.set_label(f"{p['name'].capitalize()} · {p['status'].lower() or 'stopped'}")
        self.track.set_label(p["title"] or "Unknown title")
        self.artist.set_label(" · ".join(x for x in (p["artist"], p["album"]) if x))
        self.play_btn.set_icon_name("media-playback-pause-symbolic" if p["status"] == "Playing"
                                    else "media-playback-start-symbolic")
        if p["art_file"] and os.path.exists(p["art_file"]):
            if p["art_file"] != self.media_art_path:
                self.art.set_filename(p["art_file"])
                self.media_art_path = p["art_file"]
            self.art_stack.set_visible_child_name("art")
        else:
            self.art_stack.set_visible_child_name("none")
        has_len = p["length"] > 0
        self.prog_box.set_visible(has_len)
        if has_len and time.monotonic() - self.touched.get("seek", 0) > 1.5:
            self.seek.set_range(0, p["length"])
            self.seek.set_value(p["position"])
            self.pos_lbl.set_label(mmss(p["position"]))
            self.len_lbl.set_label(mmss(p["length"]))


if __name__ == "__main__":
    sys.exit(Panel().run(sys.argv))
