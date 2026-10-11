#!/usr/bin/env python3
# =============================================================================
#  waybar/build.py — generate the Waybar config + stylesheet from the settings
# =============================================================================
#  Inputs
#    hypr/settings.conf                         BAR_* defaults
#    ~/.local/state/inkpaw/toggles.conf   values changed from the menu
#    waybar/catalog.tsv                         module names -> waybar ids
#    waybar/modules/*.jsonc                     module definitions
#    waybar/style/{colors,base}.css, style/presets/<BAR_STYLE>.css, style/modules/*.css
#  Outputs (never edit, rebuilt on every start)
#    ~/.cache/inkpaw/waybar/config.json
#    ~/.cache/inkpaw/waybar/style.css
#
#  Usage: build.py            build and print the two output paths
#         build.py --check    build into a temp dir and validate only
# =============================================================================
import json
import os
import re
import shlex
import sys
import tempfile

HOME = os.path.expanduser("~")
CFG = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local/state"), "inkpaw")
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.join(HOME, ".cache"), "inkpaw")
WB = os.path.join(CFG, "waybar")

CAPSULES = ("session", "time", "status", "system")       # capsule names (CSS ids)
STYLES = ("capsules", "floating", "solid", "minimal", "hyde", "encre")


# --- settings --------------------------------------------------------------------
def read_conf(path, into):
    try:
        with open(path) as f:
            for line in f:
                m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
                if not m or line.lstrip().startswith("#"):
                    continue
                val = re.sub(r'\s+#.*$', "", m.group(2))
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1]
                into[m.group(1)] = val.replace("${HOME}", HOME).replace("$HOME", HOME)
    except OSError:
        pass
    return into


S = read_conf(os.path.join(STATE, "toggles.conf"), read_conf(os.path.join(CFG, "hypr", "settings.conf"), {}))


def get(key, default=""):
    return S.get(key, default)


def num(key, default):
    try:
        return float(S.get(key, default))
    except ValueError:
        return float(default)


def flag(key, default=True):
    return S.get(key, "true" if default else "false").lower() in ("1", "true", "yes", "on")


def words(key, default=""):
    return get(key, default).split()


# --- modules ---------------------------------------------------------------------
def load_jsonc(path):
    with open(path) as f:
        text = "\n".join(l for l in f.read().splitlines() if not l.strip().startswith("//"))
    return json.loads(text)


def catalog():
    out = {}
    with open(os.path.join(WB, "catalog.tsv")) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            name, wid, label = line.rstrip("\n").split("\t")
            out[name] = (wid, label)
    return out


def module_definitions():
    defs = {}
    d = os.path.join(WB, "modules")
    for name in sorted(os.listdir(d)):
        if name.endswith(".jsonc"):
            defs.update(load_jsonc(os.path.join(d, name)))
    return defs


def apply_options(defs):
    """BAR_* options that change module definitions."""
    pct = flag("BAR_SHOW_PERCENT")
    ws = defs.setdefault("hyprland/workspaces", {})
    ws["persistent-workspaces"] = {"*": int(num("BAR_WORKSPACES_COUNT", 5))}
    if get("BAR_WORKSPACES_STYLE", "dots") == "numbers":
        ws["format"] = "{name}"
    clock = defs.setdefault("clock", {})
    clock["format"] = "{:L" + get("BAR_CLOCK_FORMAT", "%a %d %b   %H:%M") + "}"
    if not pct:
        defs.get("pulseaudio", {}).update({"format": "{icon}", "format-bluetooth": "󰂰"})
        defs.get("battery", {}).update({"format": "{icon}", "format-charging": "󰂄", "format-plugged": "󰚥"})
    return defs


def ids(names, cat, where):
    out = []
    for n in names:
        if n in cat:
            out.append(cat[n][0])
        else:
            print(f"build.py: unknown module '{n}' in {where} (see waybar/catalog.tsv)", file=sys.stderr)
    return out


# --- config ----------------------------------------------------------------------
def build_config():
    cat = catalog()
    defs = apply_options(module_definitions())
    position = get("BAR_POSITION", "top")
    margin = int(num("BAR_MARGIN", 6))

    conf = {
        "layer": "top",
        "position": position,
        "exclusive": True,
        "passthrough": False,
        "spacing": 0,
        "reload_style_on_change": True,
        "margin-left": margin + 4,
        "margin-right": margin + 4,
        ("margin-top" if position == "top" else "margin-bottom"): margin,
    }
    if get("BAR_STYLE") in ("solid", "hyde"):            # edge to edge
        conf.update({"margin-left": 0, "margin-right": 0, ("margin-top" if position == "top" else "margin-bottom"): 0})
    outputs = words("BAR_OUTPUTS", "*")
    if outputs and outputs != ["*"]:
        conf["output"] = outputs
    if num("BAR_HEIGHT", 0) > 0:
        conf["height"] = int(num("BAR_HEIGHT", 0))

    # Capsules = groups
    contents = {
        "session": words("BAR_SESSION", "launcher workspaces taskbar"),
        "time": words("BAR_TIME", "clock"),
        "status": words("BAR_STATUS", "extras media sound network bluetooth battery"),
        "system": words("BAR_SYSTEM", "ai notifications settings power"),
    }
    for cap, names in contents.items():
        mods = ids(names, cat, f"BAR_{cap.upper()}")
        if mods:
            conf[f"group/{cap}"] = {"orientation": "inherit", "modules": mods}
    extras = ids(words("BAR_EXTRAS", "tray caffeine wallpaper brightness"), cat, "BAR_EXTRAS")
    conf["group/extras"] = {
        "orientation": "inherit",
        "drawer": {"transition-duration": 450, "children-class": "extra", "click-to-reveal": False,
                   "transition-left-to-right": False},
        "modules": ["custom/chevron"] + extras,
    }

    # Placement
    layout = get("BAR_LAYOUT", "center")
    presets = {
        "center": ([], list(CAPSULES), []),
        "split": (["session"], ["time"], ["status", "system"]),
        "left": (list(CAPSULES), [], []),
        "right": ([], [], list(CAPSULES)),
        "custom": (words("BAR_LEFT"), words("BAR_CENTER"), words("BAR_RIGHT")),
    }
    left, center, right = presets.get(layout, presets["center"])
    used = lambda caps: [f"group/{c}" for c in caps if f"group/{c}" in conf]
    conf["modules-left"], conf["modules-center"], conf["modules-right"] = used(left), used(center), used(right)

    # BAR_SINGLE_CAPSULE: the modules of every capsule go FLAT into the
    # "session" group (its #session styling is reused), with a thin
    # custom/sep#N between the former capsules.
    if flag("BAR_SINGLE_CAPSULE", False):
        flat, n = [], 0
        for g in conf["modules-left"] + conf["modules-center"] + conf["modules-right"]:
            if flat:
                n += 1
                flat.append(f"custom/sep#{n}")
                defs[f"custom/sep#{n}"] = defs.get("custom/sep", {"format": " ", "tooltip": False})
            flat += conf[g]["modules"]
        for cap in CAPSULES:
            conf.pop(f"group/{cap}", None)
        conf["group/session"] = {"orientation": "inherit", "modules": flat}
        side = {"left": "modules-left", "right": "modules-right"}.get(layout, "modules-center")
        for key in ("modules-left", "modules-center", "modules-right"):
            conf[key] = ["group/session"] if key == side else []

    # Module definitions (only those referenced, keeps the file readable)
    referenced = set()
    def walk(group):
        for m in conf[group]["modules"]:
            referenced.add(m)
            if m.startswith("group/") and m in conf and m != group:
                walk(m)
    for key in ("modules-left", "modules-center", "modules-right"):
        for g in conf[key]:
            walk(g)
    referenced.update(conf["group/extras"]["modules"])
    for wid in sorted(referenced):
        if wid in defs:
            conf[wid] = detach_actions(defs[wid])
    return conf


# Waybar runs on-click / on-scroll commands with PR_SET_PDEATHSIG: an app opened
# from the bar (Settings, pavucontrol…) was killed as soon as Waybar reloaded,
# and changing the theme reloads it. "setsid -f" forks once more (the death
# signal is not inherited across fork) and leaves Waybar's session.
BUILTIN_ACTIONS = {"activate", "close", "minimize", "minimize-raise", "maximize", "fullscreen",
                   "mode", "tz_up", "tz_down", "shift_up", "shift_down", "shift_reset", "none"}


def detach_actions(module):
    if not isinstance(module, dict):
        return module
    out = dict(module)
    for key, cmd in module.items():
        if key.startswith("on-") and isinstance(cmd, str) and cmd.strip() and cmd not in BUILTIN_ACTIONS \
                and not cmd.startswith("setsid "):
            out[key] = "setsid -f sh -c " + shlex.quote(cmd)
    return out


# --- style -----------------------------------------------------------------------
def encre_style(conf):
    """BAR_STYLE="encre" (skin "encre"): the rules that depend on the settings.
    The look itself is in style/presets/encre.css (+ encre-numbers.css)."""
    font = int(num("BAR_FONT_SIZE", 12))
    pad = int(num("BAR_MODULE_PADDING", 8))
    lines = []
    if get("BAR_WORKSPACES_STYLE", "dots") == "numbers":
        display = get("DISPLAY_FONT", "Caveat Brush").replace('"', "")
        lines += ["/* encre: workspace numbers in the brush font (DISPLAY_FONT) */",
                  f'#workspaces button label {{ font-family: "{display}", sans-serif; font-size: {round(font * 1.75)}px;'
                  " font-weight: 400; }"]
    if flag("BAR_SINGLE_CAPSULE", False):
        lines += ["/* encre + BAR_SINGLE_CAPSULE: one plate, dashed ink lines between the former capsules */",
                  f"window#waybar #custom-sep {{ min-width: 0; padding: 0; margin: 9px {max(4, pad - 4)}px; font-size: 1px;"
                  " background: transparent; border: none; border-left: 2px dashed alpha(@on_surface, 0.5);"
                  " border-radius: 0; }",
                  "window#waybar #custom-sep:hover { background: transparent; border-color: transparent;"
                  " border-left-color: alpha(@on_surface, 0.5); }"]
    else:
        # Capsules side by side in one section = ONE plate (the mockup has three
        # plates: left, center, right): flatten the inner sides of the joint.
        for key in ("modules-left", "modules-center", "modules-right"):
            caps = [g.split("/", 1)[1] for g in (conf or {}).get(key, [])]
            if len(caps) < 2:
                continue
            lines.append(f"/* encre: {' + '.join(caps)} joined into one plate ({key}) */")
            for i, cap in enumerate(caps):
                rules = []
                if i < len(caps) - 1:
                    rules.append("margin-right: 0; border-right-width: 0; border-top-right-radius: 0;"
                                 " border-bottom-right-radius: 0;")
                if i > 0:
                    # the previous capsule's shadow is clipped at its edge (no right margin
                    # left): a 2nd, unshifted shadow fills the 4 px notch under the joint
                    rules.append("margin-left: 0; border-left-width: 0; border-top-left-radius: 0;"
                                 " border-bottom-left-radius: 0;"
                                 " box-shadow: 4px 4px 0 @encre_shadow, 0 4px 0 @encre_shadow;")
                lines.append(f"#{cap} {{ {' '.join(rules)} }}")
    return lines


def build_style(conf=None):
    style = get("BAR_STYLE", "capsules")
    if style not in STYLES:
        style = "capsules"
    op = max(0.0, min(1.0, num("BAR_OPACITY", 0.82)))
    radius = int(num("BAR_RADIUS", 9))
    font = int(num("BAR_FONT_SIZE", 12))
    css_dir = os.path.join(WB, "style")
    imports = [os.path.join(css_dir, "colors.css"), os.path.join(css_dir, "base.css"),
               os.path.join(css_dir, "presets", f"{style}.css")]
    mod_dir = os.path.join(css_dir, "modules")
    imports += [os.path.join(mod_dir, f) for f in sorted(os.listdir(mod_dir)) if f.endswith(".css")]
    if style == "encre":                                  # a skin: its preset overrides the module colors
        imports.remove(os.path.join(css_dir, "presets", "encre.css"))
        imports.append(os.path.join(css_dir, "presets", "encre.css"))
        if get("BAR_WORKSPACES_STYLE", "dots") == "numbers":
            imports.append(os.path.join(css_dir, "presets", "encre-numbers.css"))

    caps = "#session, #time, #status, #system"
    lines = [f'/* GENERATED by waybar/build.py — style "{style}" (edit the settings, not this file) */']
    lines += [f'@import url("file://{p}");' for p in imports]
    pad = int(num("BAR_MODULE_PADDING", 8))
    lines += ["", "/* numbers from settings.conf (BAR_FONT_SIZE, BAR_MODULE_PADDING, BAR_RADIUS, BAR_OPACITY) */",
              f"* {{ font-size: {font}px; }}",
              f"#session > widget > *, #time > widget > *, #status > widget > *, #system > widget > *, .extra"
              f" {{ padding: 0 {pad}px; }}",
              f"#session, #time, #status, #system {{ padding: 0 {max(4, pad // 2)}px; }}"]
    if style == "capsules":
        lines += [f"{caps} {{ border-radius: {radius}px; background-color: alpha(@surface, {op}); }}"]
    elif style == "floating":
        lines += [f"window#waybar > box {{ border-radius: {radius + 3}px; background-color: alpha(@surface, {op}); }}"]
    elif style == "solid":
        lines += [f"window#waybar > box {{ background-color: alpha(@surface, {op}); }}"]
    elif style == "hyde":
        lines += [f"window#waybar > box {{ background-color: alpha(@surface, {op}); }}",
                  f"{caps} {{ border-radius: {radius}px; }}"]
    if style == "encre":                                  # opaque plates, BAR_OPACITY / BAR_RADIUS unused
        return "\n".join(lines + encre_style(conf)) + "\n"
    if flag("BAR_SINGLE_CAPSULE", False):
        lines += ["/* BAR_SINGLE_CAPSULE: everything in #session, thin separators (.sep) */",
                  f"#custom-sep {{ min-width: 1px; padding: 0; margin: 9px {max(6, pad - 2)}px; border-radius: 0;"
                  " background-color: alpha(@on_surface, 0.16); font-size: 1px; }",
                  "#session > widget > #custom-sep:hover { background-color: alpha(@on_surface, 0.16); }"]
    if not flag("BAR_COLORED_ICONS"):
        lines += ["/* BAR_COLORED_ICONS=false: monochrome */",
                  "#pulseaudio, #network, #bluetooth, #battery, #cpu, #memory, #mpris, #language, "
                  "#custom-settings, #custom-power, #custom-notifications, #custom-wallpaper, #backlight, "
                  "#idle_inhibitor, #custom-launcher, #custom-chevron { color: @on_surface; }"]
    if get("BAR_WORKSPACES_STYLE", "dots") == "numbers":
        lines += ["/* numbered workspaces */",
                  "#workspaces button, #workspaces button.empty { min-width: 20px; min-height: 0; margin: 4px 1px;"
                  " padding: 0 4px; background: transparent; border-radius: 6px; }",
                  "#workspaces button.empty label { color: alpha(@on_surface, 0.3); }",
                  f"#workspaces button label {{ font-size: {font}px; color: alpha(@on_surface, 0.6); }}",
                  "#workspaces button.active { min-width: 20px; background-image: linear-gradient(90deg, @a1, @a3); }",
                  "#workspaces button.active label { color: @surface; font-weight: 800; }"]
    return "\n".join(lines) + "\n"


def main():
    check = "--check" in sys.argv
    out_dir = tempfile.mkdtemp() if check else os.path.join(CACHE, "waybar")
    os.makedirs(out_dir, exist_ok=True)
    conf = build_config()
    css = build_style(conf)
    cpath, spath = os.path.join(out_dir, "config.json"), os.path.join(out_dir, "style.css")
    with open(cpath, "w") as f:
        json.dump(conf, f, indent=2, ensure_ascii=False)
    with open(spath, "w") as f:
        f.write(css)
    if check:
        json.load(open(cpath))
        body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)     # ignore comments
        if body.count("{") != body.count("}"):
            sys.exit(f"build.py: generated style.css has unbalanced braces ({body.count('{')} vs {body.count('}')})")
        print(f"ok: {len(conf['modules-left']) + len(conf['modules-center']) + len(conf['modules-right'])} capsules, "
              f"style {get('BAR_STYLE', 'capsules')}, layout {get('BAR_LAYOUT', 'center')}, position {get('BAR_POSITION', 'top')}")
    else:
        print(cpath)
        print(spath)


if __name__ == "__main__":
    main()
