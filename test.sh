#!/usr/bin/env bash
# =============================================================================
#  test.sh — try this Hyprland setup WITHOUT touching ~/.config
# =============================================================================
#  Every test copies this folder into a throw-away directory
#  ($TMPDIR/inkpaw.XXXXXX) and points XDG_CONFIG_HOME / XDG_STATE_HOME /
#  XDG_CACHE_HOME at it. The directory is deleted on exit (even on Ctrl+C).
#  Nothing is installed, linked or copied into your home directory.
#
#  Run ./test.sh --help for the list of commands.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
COMPONENTS=(hypr hyprtheme waybar walker elephant swaync rofi wlogout swayosd spotlight settings-app quickpanel aichat deskpet welcome powermenu keysheet themepicker wallpicker pylib kitty)

# --- pretty output -----------------------------------------------------------
if [ -t 1 ]; then B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; D=$'\e[2m'; N=$'\e[0m'
else B=""; G=""; Y=""; R=""; D=""; N=""; fi
ok()   { printf '  %s✔%s %s\n' "$G" "$N" "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
err()  { printf '  %s✘%s %s\n' "$R" "$N" "$*"; }
title(){ printf '\n%s%s%s\n' "$B" "$*" "$N"; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
    cat <<EOF
${B}Usage:${N} ./test.sh <command> [options]

${B}Checks${N}
  deps [--list]            List missing dependencies + the yay command to install them
                           (--list: only the missing package names)
  verify                   Validate everything: Hyprland Lua (all monitor profiles),
                           JSON/JSONC, TOML, rofi themes, shell syntax, theme rendering

${B}Full session${N}
  nested [options]         Launch the whole setup as a nested Hyprland window
      --wallpapers <dir>   Use this wallpaper folder (default: WALLPAPER_DIR)
      --keep-mod           Keep SUPER as modifier (default in nested: ALT, because
                           your host Hyprland grabs SUPER shortcuts first)
      --keep               Keep the temp directory after exit (prints its path)

      ${D}Nested sessions share keyboard/D-Bus quirks with your host. For a clean,
      full test, log in to the "inkpaw" SDDM session (see session/).${N}

${B}Components${N} (run inside your current session, with the local files)
  waybar                   Launch Waybar with the local config (Ctrl+C to quit)
  launcher [provider]      Open the sectioned Spotlight (or Walker for a provider,
                           e.g. clipboard) with the local config
  notifications            Private swaync + 3 sample notifications + control center
  menu <name>              Open a rofi menu: settings | wifi | bluetooth | power |
                           keybindings | monitors | screenshot | wallpaper | static
  theme <image|static:NAME> [--preview]
                           Generate a palette into the temp dir, print the swatches
                           and generated files; --preview also opens Waybar with it
  lock                     Lock YOUR session with the local hyprlock look (asks first)

${B}Misc${N}
  clean                    Remove leftover temp directories from killed runs
  -h, --help               This help

${D}Nothing in ~/.config is ever modified. Menu actions (Wi-Fi, Bluetooth,
power…) act on the real system, exactly as they would after installation.${N}
EOF
}

# =============================================================================
#  Temp root
# =============================================================================
ROOT=""; KEEP=0
cleanup() {
    [ -n "${WAYBAR_PID:-}" ] && kill "$WAYBAR_PID" 2>/dev/null
    if [ -n "$ROOT" ] && [ -d "$ROOT" ]; then
        if [ "$KEEP" = 1 ]; then echo "${D}temp dir kept: $ROOT${N}"
        else rm -rf "$ROOT"; fi
    fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# Build $ROOT/{config,state,cache} from this folder and export the XDG vars
make_root() {
    ROOT="$(mktemp -d -t inkpaw.XXXXXX)"
    mkdir -p "$ROOT/config" "$ROOT/state" "$ROOT/cache"
    local c
    for c in "${COMPONENTS[@]}"; do cp -r "$HERE/$c" "$ROOT/config/"; done

    # kitty: keep your own kitty.conf (read-only include) + the generated theme
    {
        echo "# test.sh: your kitty.conf (read-only include) + generated theme"
        [ -f "$HOME/.config/kitty/kitty.conf" ] && echo "include $HOME/.config/kitty/kitty.conf"
        echo "include inkpaw-theme.conf"
    } >"$ROOT/config/kitty/kitty.conf"
    # GTK: copy (never link) your GTK settings so apps keep their icon theme
    local g
    for g in gtk-3.0 gtk-4.0; do
        [ -f "$HOME/.config/$g/settings.ini" ] && mkdir -p "$ROOT/config/$g" && cp "$HOME/.config/$g/settings.ini" "$ROOT/config/$g/"
    done

    export XDG_CONFIG_HOME="$ROOT/config" XDG_STATE_HOME="$ROOT/state" XDG_CACHE_HOME="$ROOT/cache"
    export INKPAW_TEST=1
}

# Change KEY="value" in the temp copy of settings.conf
set_setting() {
    sed -i "s|^$1=.*|$1=\"$2\"|" "$ROOT/config/hypr/settings.conf"
}

# =============================================================================
#  deps
# =============================================================================
# "command:package" — package names for Arch (repo or AUR, installed with yay)
REQUIRED=(
    "Hyprland:hyprland" "hyprlock:hyprlock" "hypridle:hypridle" "hyprsunset:hyprsunset"
    "waybar:waybar" "rofi:rofi" "walker:walker" "elephant:elephant"
    "swaync:swaync" "swayosd-server:swayosd" "wlogout:wlogout"
    "matugen:matugen" "awww:awww" "jq:jq" "magick:imagemagick"
    "nmcli:networkmanager" "bluetoothctl:bluez-utils" "blueman-manager:blueman"
    "wpctl:wireplumber" "pavucontrol:pavucontrol" "brightnessctl:brightnessctl" "playerctl:playerctl"
    "hyprshot:hyprshot" "satty:satty" "grim:grim" "slurp:slurp" "wl-copy:wl-clipboard"
    "notify-send:libnotify" "kitty:kitty" "dbus-run-session:dbus"
)
# libraries of the GTK 4 apps (settings, menus, quick panel, AI chat…): checked with pacman -Q
LIBS=(python-gobject python-cairo gtk4 libadwaita gtk4-layer-shell)
# fonts of the default look: "family:package" (the encre skin bundles its own)
FONTS=("JetBrainsMono Nerd Font:ttf-jetbrains-mono-nerd" "CaskaydiaCove Nerd Font:ttf-cascadia-code-nerd")
# optional libraries: full Markdown in the AI chat, the Claude provider
OPT_LIBS=(python-markdown-it-py python-anthropic)
OPTIONAL=( "tesseract:tesseract-data-fra (OCR)" "nwg-displays:nwg-displays (monitor GUI)" "shellcheck:shellcheck (verify)" )
ELEPHANT_PROVIDERS=(desktopapplications files calc websearch clipboard runner symbols providerlist menus)

# deps [--list]: --list prints only the missing package names (used by install.sh)
cmd_deps() {
    local list=0; [ "${1:-}" = "--list" ] && list=1
    if [ "$list" = 1 ]; then cmd_deps >/dev/null 2>&1; echo "${DEPS_MISSING:-}"; return 0; fi
    title "Required commands"
    local missing=() e c p
    for e in "${REQUIRED[@]}"; do
        c="${e%%:*}"; p="${e#*:}"
        if [ "$c" = "awww" ] && ! have awww && have swww; then ok "swww (legacy, used instead of awww)"; continue; fi
        if have "$c"; then ok "$c"; else err "$c  ${D}($p)${N}"; missing+=("$p"); fi
    done

    title "Walker / Elephant providers"
    if have pacman; then
        for p in "${ELEPHANT_PROVIDERS[@]}"; do
            if pacman -Q "elephant-$p" >/dev/null 2>&1; then ok "elephant-$p"
            else err "elephant-$p"; missing+=("elephant-$p"); fi
        done
    else warn "pacman not found: cannot check elephant-* provider packages"; fi

    title "Libraries (GTK 4 apps)"
    if have pacman; then
        for p in "${LIBS[@]}"; do
            if pacman -Q "$p" >/dev/null 2>&1; then ok "$p"; else err "$p"; missing+=("$p"); fi
        done
        for p in "${OPT_LIBS[@]}"; do
            if pacman -Q "$p" >/dev/null 2>&1; then ok "$p"; else warn "$p  ${D}(optional)${N}"; fi
        done
    else warn "pacman not found: cannot check the GTK 4 / Python libraries"; fi

    title "Optional"
    for e in "${OPTIONAL[@]}"; do
        c="${e%%:*}"; p="${e#*:}"
        if have "$c"; then ok "$c"; else warn "$c  ${D}— $p${N}"; fi
    done

    title "Fonts"
    local fam families
    families="$(fc-list : family 2>/dev/null)"    # read once (grep -q + pipefail = SIGPIPE)
    for e in "${FONTS[@]}"; do
        fam="${e%%:*}"; p="${e#*:}"
        if grep -qiF -- "$fam" <<<"$families"; then ok "$fam"
        else err "$fam  ${D}($p)${N}"; missing+=("$p"); fi
    done
    local font; font=$(sed -n 's/^FONT_FAMILY="\(.*\)"/\1/p' "$HERE/hypr/settings.conf")
    if grep -qiF -- "$font" <<<"$families"; then ok "$font (FONT_FAMILY)"
    else warn "$font (FONT_FAMILY) not installed: the default sans font is used — set FONT_FAMILY in hypr/settings.conf or Settings"; fi

    DEPS_MISSING="${missing[*]}"
    echo
    if [ ${#missing[@]} -eq 0 ]; then
        printf '%sAll required dependencies are installed.%s\n' "$G" "$N"
    else
        printf '%sMissing:%s %s\n\n' "$Y" "$N" "${missing[*]}"
        echo "Install with (not run by this script):"
        printf '  %syay -S --needed %s%s\n' "$B" "${missing[*]}" "$N"
        return 1
    fi
}

# =============================================================================
#  verify
# =============================================================================
cmd_verify() {
    local fail=0 f out p
    make_root

    title "Hyprland Lua config (Hyprland --verify-config)"
    if have Hyprland; then
        mkdir -p "$ROOT/state/inkpaw"
        for p in auto extended laptop-only external-only mirror; do
            printf 'MONITOR_PROFILE="%s"\n' "$p" >"$ROOT/state/inkpaw/toggles.conf"
            # test mode forces the "auto" profile, so unset it for this check
            out=$(env -u INKPAW_TEST timeout 30 Hyprland --verify-config -c "$ROOT/config/hypr/hyprland.lua" 2>&1 | grep -v DEBUG | sed -n '/parsing result/,$p' | tail -n +2 | sed '/^$/d')
            if [ "$out" = "config ok" ]; then ok "profile $p"; else err "profile $p:"; echo "$out" | sed 's/^/      /'; fail=1; fi
        done
        printf 'GAMEMODE="true"\nANIMATIONS="false"\n' >"$ROOT/state/inkpaw/toggles.conf"
        out=$(timeout 30 Hyprland --verify-config -c "$ROOT/config/hypr/hyprland.lua" 2>&1 | grep -v DEBUG | tail -1)
        [ "$out" = "config ok" ] && ok "gamemode + test mode" || { err "gamemode: $out"; fail=1; }
        rm -f "$ROOT/state/inkpaw/toggles.conf"
    else warn "Hyprland not installed: skipped"; fi

    title "JSON / JSONC"
    while IFS= read -r f; do
        if sed -E 's#^\s*//.*##' "$f" | jq empty 2>/dev/null; then ok "${f#"$HERE"/}"; else err "${f#"$HERE"/}"; fail=1; fi
    done < <(find "$HERE/waybar" "$HERE/swaync" "$HERE/hyprtheme/static" -name '*.json*' | sort)
    while IFS= read -r line; do
        echo "$line" | jq empty 2>/dev/null || { err "wlogout/layout: $line"; fail=1; }
    done <"$HERE/wlogout/layout"; ok "wlogout/layout"

    title "TOML"
    if have python3; then
        while IFS= read -r f; do
            if python3 -c 'import sys,tomllib; tomllib.load(open(sys.argv[1],"rb"))' "$f" 2>/dev/null; then ok "${f#"$HERE"/}"
            else err "${f#"$HERE"/}"; fail=1; fi
        done < <(find "$HERE/walker" "$HERE/elephant" "$HERE/swayosd" -name '*.toml' | sort)
    else warn "python3 missing: skipped"; fi

    title "rofi themes"
    if have rofi; then
        for f in "$HERE"/rofi/themes/*.rasi "$HERE"/rofi/skins/*/*.rasi; do
            [ -f "$f" ] || continue
            # -dump-theme misses some errors: also parse it for real (needs a display)
            if ! rofi -dump-theme -theme "$f" >/dev/null 2>&1; then err "${f#"$HERE"/}"; fail=1
            elif [ -n "${WAYLAND_DISPLAY:-}" ] && printf 'x\n' | timeout 1 rofi -dmenu -theme "$f" 2>&1 >/dev/null | grep -qE 'Failed|failed to resolve'; then
                err "${f#"$HERE"/} (runtime parse)"; fail=1
            else ok "${f#"$HERE"/}"; fi
        done
    else warn "rofi missing: skipped"; fi

    title "rofi nested-comment lint"
    # rofi nests /* */ comments: a "/*" inside a comment (e.g. a glob) swallows the file
    out=$(grep -nE '^[[:space:]]*[^[:space:]/].*/\*|[^[:space:]].*/\*.*' "$HERE"/rofi/*.rasi "$HERE"/rofi/themes/*.rasi "$HERE"/rofi/skins/*/*.rasi "$HERE"/hyprtheme/templates/rofi*.rasi 2>/dev/null | grep -vE ':[0-9]+:[[:space:]]*/\*' )
    [ -z "$out" ] && ok "no stray /* in .rasi files" || { err "stray /* in:"; echo "$out" | sed 's/^/      /'; fail=1; }
    # rofi reads a binding string up to the end of the line: one string per line
    out=$(grep -nE '"[^"]*"[^"]*;[^"]*"[^"]*"' "$HERE"/rofi/themes/*.rasi "$HERE"/rofi/skins/*/*.rasi 2>/dev/null | grep -E 'me-|kb-' )
    [ -z "$out" ] && ok "one binding string per line" || { err "several binding strings on one line:"; echo "$out" | sed 's/^/      /'; fail=1; }

    title "Shell scripts (bash -n${D}, shellcheck if installed${N}${B})"
    while IFS= read -r f; do
        if bash -n "$f" 2>/dev/null; then ok "${f#"$HERE"/}"; else err "${f#"$HERE"/}"; bash -n "$f"; fail=1; fi
    done < <({ find "$HERE" -name '*.sh' -not -path '*/.*'; echo "$HERE/hypr/scripts/skin-bin/slurp"; } | sort)
    if have shellcheck; then
        out=$(find "$HERE" -name '*.sh' -not -path '*/.*' -exec shellcheck -S error {} + 2>&1)
        [ -z "$out" ] && ok "shellcheck: no errors" || { warn "shellcheck:"; echo "$out" | head -30; }
    fi

    title "Bar builder (waybar/build.py, every style × layout × position)"
    local st la po
    mkdir -p "$ROOT/state/inkpaw"
    for st in capsules floating solid minimal hyde encre; do for la in center split left right custom; do for po in top bottom; do
        printf 'BAR_STYLE="%s"\nBAR_LAYOUT="%s"\nBAR_POSITION="%s"\n' "$st" "$la" "$po" >"$ROOT/state/inkpaw/toggles.conf"
        python3 -I "$ROOT/config/waybar/build.py" --check >/dev/null 2>"$ROOT/cache/build.err" || { err "build $st/$la/$po: $(cat "$ROOT/cache/build.err")"; fail=1; }
    done; done; done
    for st in capsules floating solid minimal hyde encre; do
        printf 'BAR_STYLE="%s"\nBAR_SINGLE_CAPSULE="true"\n' "$st" >"$ROOT/state/inkpaw/toggles.conf"
        python3 -I "$ROOT/config/waybar/build.py" --check >/dev/null 2>"$ROOT/cache/build.err" || { err "build single/$st: $(cat "$ROOT/cache/build.err")"; fail=1; }
    done
    rm -f "$ROOT/state/inkpaw/toggles.conf"
    [ $fail = 0 ] && ok "66 combinations build valid JSON (incl. single capsule)"
    if grep -vE '^\s*(#|$)' "$HERE/hypr/settings.schema" | awk -F'|' 'NF != 6 { bad = 1 } END { exit bad }'; then ok "settings.schema: every line has 6 fields"
    else err "settings.schema: malformed line(s)"; fail=1; fi

    title "Python syntax"
    for f in "$HERE"/spotlight/*.py "$HERE"/hyprtheme/lib/*.py "$HERE"/waybar/build.py "$HERE"/waybar/ipc-proxy.py "$HERE"/settings-app/*.py "$HERE"/quickpanel/*.py "$HERE"/aichat/*.py \
             "$HERE"/deskpet/*.py "$HERE"/welcome/*.py "$HERE"/powermenu/*.py "$HERE"/keysheet/*.py "$HERE"/themepicker/*.py "$HERE"/wallpicker/*.py "$HERE"/pylib/*.py "$HERE"/hyprtheme/skins/*/cats/build.py; do
        if python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' "$f" 2>/dev/null; then ok "${f#"$HERE"/}"
        else err "${f#"$HERE"/}"; fail=1; fi
    done
    # the Waybar IPC relay rewrites the legacy workspace dispatch into Lua
    if HYPRLAND_INSTANCE_SIGNATURE=x python3 -I - "$HERE/waybar/ipc-proxy.py" <<'PYEOF' 2>/dev/null
import importlib.util, sys
spec = importlib.util.spec_from_file_location("p", sys.argv[1]); p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
assert p.translate("dispatch workspace 3") == 'dispatch hl.dsp.focus({ workspace = "3" })'
assert p.translate("[[BATCH]]dispatch workspace name:a;j/clients").startswith('[[BATCH]]dispatch hl.dsp.focus({ workspace = "name:a" });j/clients')
assert p.translate("dispatch togglespecialworkspace") == "dispatch hl.dsp.workspace.toggle_special()"
assert p.translate("j/workspaces") == "j/workspaces"
PYEOF
    then ok "waybar/ipc-proxy.py: workspace clicks translated to Lua"
    else err "waybar/ipc-proxy.py: translation"; fail=1; fi

    title "Theme engine (matugen rendering into the temp dir)"
    if have matugen && have jq; then
        local t
        for t in "$HERE"/hyprtheme/static/*.json; do
            t=$(basename "$t" .json)
            if THEME_NO_RELOAD=1 THEME_NO_WALLPAPER=1 "$ROOT/config/hyprtheme/theme.sh" static "$t" >/dev/null 2>&1; then ok "static: $t"
            else err "static: $t"; fail=1; fi
        done
        if have magick; then
            magick -size 320x200 gradient:'#2e7d32'-'#ff8f00' "$ROOT/cache/test.png"
            if THEME_NO_RELOAD=1 THEME_NO_WALLPAPER=1 "$ROOT/config/hyprtheme/theme.sh" wallpaper "$ROOT/cache/test.png" >/dev/null 2>&1; then ok "wallpaper palette (generated test image)"
            else err "wallpaper palette"; fail=1; fi
            if have Hyprland; then
                out=$(timeout 30 Hyprland --verify-config -c "$ROOT/config/hypr/hyprland.lua" 2>&1 | tail -1)
                [ "$out" = "config ok" ] && ok "Hyprland accepts generated themes/current.lua" || { err "generated colors: $out"; fail=1; }
            fi
        fi
    else warn "matugen/jq missing: skipped"; fi

    title "Skins (hyprtheme/skin.sh, in the temp dir)"
    out=$(FONTCONFIG_FILE="$HERE/hyprtheme/fonts/fonts.conf" fc-list : family 2>/dev/null)
    if [[ "$out" == *"Caveat Brush"* && "$out" == *"Shantell Sans"* && "$out" == *"Courier Prime"* ]]; then ok "bundled fonts visible through hyprtheme/fonts/fonts.conf"
    else err "bundled fonts not found by fontconfig"; fail=1; fi
    local sk conf missing
    for conf in "$HERE"/hyprtheme/skins/*/skin.conf; do
        sk=$(basename "$(dirname "$conf")")
        mkdir -p "$ROOT/state/inkpaw"; rm -f "$ROOT/state/inkpaw/toggles.conf" "$ROOT/state/inkpaw/theme.conf"
        printf 'GAPS_IN="3"\n' >"$ROOT/state/inkpaw/toggles.conf"
        if SKIN_NO_RELOAD=1 "$ROOT/config/hyprtheme/skin.sh" apply "$sk" >/dev/null 2>&1 &&
           grep -q "^UI_SKIN=\"$sk\"" "$ROOT/state/inkpaw/toggles.conf"; then ok "skin $sk: applied"
        else err "skin $sk: apply failed"; fail=1; continue; fi
        if have Hyprland; then
            out=$(timeout 30 Hyprland --verify-config -c "$ROOT/config/hypr/hyprland.lua" 2>&1 | tail -1)
            [ "$out" = "config ok" ] && ok "skin $sk: Hyprland config ok" || { err "skin $sk: $out"; fail=1; }
        fi
        python3 -I "$ROOT/config/waybar/build.py" --check >/dev/null 2>"$ROOT/cache/build.err" && ok "skin $sk: bar builds" || { err "skin $sk bar: $(cat "$ROOT/cache/build.err")"; fail=1; }
        # every skinned file the templates render must exist after the theme pass
        missing=""
        for f in $(grep -ho '@output:[[:space:]]*[^[:space:]*]*' "$HERE"/hyprtheme/templates/*-"$sk".* 2>/dev/null | sed 's/@output:[[:space:]]*//'); do
            [ -s "$ROOT/config/$f" ] || missing+=" $f"
        done
        [ -z "$missing" ] && ok "skin $sk: skinned files rendered" || { err "skin $sk: missing$missing"; fail=1; }
        SKIN_NO_RELOAD=1 "$ROOT/config/hyprtheme/skin.sh" apply default >/dev/null 2>&1
        if grep -q '^GAPS_IN="3"' "$ROOT/state/inkpaw/toggles.conf" && ! grep -q '^BAR_STYLE=' "$ROOT/state/inkpaw/toggles.conf"; then ok "skin $sk: 'apply default' restores your toggles"
        else err "skin $sk: default not restored"; fail=1; fi
    done
    rm -f "$ROOT/state/inkpaw/toggles.conf"
    if python3 -I "$ROOT/config/hyprtheme/skins/encre/cats/build.py" >/dev/null 2>&1; then ok "cats/build.py draws the cats"
    else err "cats/build.py"; fail=1; fi

    echo
    if [ $fail = 0 ]; then printf '%sAll checks passed.%s\n' "$G" "$N"; else printf '%sSome checks failed.%s\n' "$R" "$N"; fi
    return $fail
}

# =============================================================================
#  nested
# =============================================================================
cmd_nested() {
    local wallpapers="" keep_mod=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --wallpapers) wallpapers="$(readlink -f "${2:?}")"; shift 2 ;;
            --keep-mod)   keep_mod=1; shift ;;
            --keep)       KEEP=1; shift ;;
            *) err "unknown option $1"; exit 1 ;;
        esac
    done
    [ -n "${WAYLAND_DISPLAY:-}" ] || { err "Run this from a graphical Wayland session."; exit 1; }
    have Hyprland || { err "Hyprland is not installed"; exit 1; }

    make_root
    [ -n "$wallpapers" ] && set_setting WALLPAPER_DIR "$wallpapers"
    [ "$keep_mod" = 0 ] && set_setting MOD "ALT"

    title "Nested Hyprland session"
    echo "  config root : $ROOT/config"
    echo "  modifier    : $([ "$keep_mod" = 0 ] && echo "ALT  (e.g. ALT+SPACE = Spotlight, ALT+RETURN = terminal)" || echo SUPER)"
    echo "  skipped     : portals, polkit, systemd env, idle/suspend, lid switch, gsettings"
    echo "  isolation   : private D-Bus session (own swaync/OSD), temp XDG dirs"
    echo "  quit        : close the window, or run the power menu → Logout"
    echo

    dbus-run-session -- Hyprland -c "$ROOT/config/hypr/hyprland.lua"
}

# =============================================================================
#  components
# =============================================================================
cmd_waybar() {
    have waybar || { err "waybar is not installed"; exit 1; }
    make_root
    title "Waybar with local config (Ctrl+C to stop)"
    python3 -I "$ROOT/config/waybar/build.py" >/dev/null || exit 1
    waybar -c "$ROOT/cache/inkpaw/waybar/config.json" -s "$ROOT/cache/inkpaw/waybar/style.css" -l warning
}

cmd_launcher() {
    make_root
    # Sectioned Spotlight (default) unless a Walker provider was requested
    if [ -z "${1:-}" ] && python3 -c 'import gi; gi.require_version("Gtk4LayerShell", "1.0")' 2>/dev/null; then
        pgrep -x elephant >/dev/null || { elephant >"$ROOT/cache/elephant.log" 2>&1 & sleep 0.5; }
        title "Spotlight with local config — Esc to close"
        python3 -I "$ROOT/config/spotlight/spotlight.py"
        return
    fi
    if have walker; then
        if pgrep -x elephant >/dev/null; then
            warn "An Elephant instance is already running: Walker will use ITS providers/config."
        else
            elephant >"$ROOT/cache/elephant.log" 2>&1 & local ELE=$!
            sleep 0.5
        fi
        title "Walker with local config — Esc to close"
        if [ -n "${1:-}" ]; then walker -m "$1"; else walker; fi
        [ -n "${ELE:-}" ] && kill "$ELE" 2>/dev/null
    else
        warn "walker not installed — showing the rofi fallback"
        rofi -show drun -theme "$ROOT/config/rofi/themes/launcher.rasi"
    fi
}

cmd_notifications() {
    have swaync || { err "swaync is not installed"; exit 1; }
    make_root
    title "Private swaync instance (its own D-Bus session) — closes after the control center"
    dbus-run-session -- bash -c '
        swaync -c "$XDG_CONFIG_HOME/swaync/config.json" -s "$XDG_CONFIG_HOME/swaync/style.css" & pid=$!
        sleep 1
        notify-send -a "test.sh" "Hello from inkpaw" "This popup uses the generated palette."
        notify-send -a "test.sh" -u critical "Critical notification" "Red border = urgency critical."
        notify-send -a "test.sh" "Third one" "Open the control center to see history + quick toggles."
        sleep 3
        swaync-client -t -sw
        echo "Control center open. Press Enter here to quit."; read -r _
        kill $pid'
}

cmd_menu() {
    local name="${1:-settings}" s
    make_root
    # Menus must not reload your host Hyprland: hide its socket from them
    unset HYPRLAND_INSTANCE_SIGNATURE
    s="$ROOT/config/hypr/scripts"
    case "$name" in
        settings|wifi|bluetooth|power|monitors|keybindings) "$s/menus/$name.sh" ;;
        screenshot) "$s/screenshot.sh" menu ;;
        wallpaper)  THEME_NO_WALLPAPER=1 THEME_NO_RELOAD=1 "$ROOT/config/hyprtheme/wallpaper-picker.sh" ;;
        static)     THEME_NO_RELOAD=1 "$ROOT/config/hyprtheme/static-picker.sh" ;;
        *) err "unknown menu '$name'"; exit 1 ;;
    esac
    [ "$name" = keybindings ] && warn "Outside the nested session, keybindings shows your HOST binds (hyprctl was hidden, so probably nothing)."
}

swatch() {   # $1 = hex without '#'
    local h="$1" r g b
    r=$((16#${h:0:2})); g=$((16#${h:2:2})); b=$((16#${h:4:2}))
    printf '\e[48;2;%d;%d;%dm      \e[0m' "$r" "$g" "$b"
}

cmd_theme() {
    local src="${1:-}" preview=0
    [ "${2:-}" = "--preview" ] && preview=1
    [ -n "$src" ] || { err "usage: ./test.sh theme <image|static:NAME> [--preview]"; exit 1; }
    make_root
    export THEME_NO_RELOAD=1 THEME_NO_WALLPAPER=1
    title "Generating palette"
    if [[ "$src" == static:* ]]; then
        "$ROOT/config/hyprtheme/theme.sh" static "${src#static:}" || exit 1
    else
        "$ROOT/config/hyprtheme/theme.sh" wallpaper "$(readlink -f "$src")" || exit 1
    fi

    title "Palette"
    local k v
    while IFS='=' read -r k v; do
        k=$(echo "$k" | tr -d ' '); v=$(echo "$v" | tr -d ' ",')
        [[ "$v" =~ ^[0-9a-fA-F]{6}$ ]] || continue
        printf '  %s %-24s #%s\n' "$(swatch "$v")" "$k" "$v"
    done < <(grep '= "' "$ROOT/config/hypr/themes/current.lua")

    title "Generated files (in the temp dir)"
    grep -h "output_path" "$ROOT/cache/inkpaw/matugen.toml" | sed "s|.*'$ROOT/config/|  |; s|'$||"

    if [ "$preview" = 1 ]; then
        title "Waybar preview with this palette (Ctrl+C to stop)"
        python3 -I "$ROOT/config/waybar/build.py" >/dev/null || exit 1
        waybar -c "$ROOT/cache/inkpaw/waybar/config.json" -s "$ROOT/cache/inkpaw/waybar/style.css" -l warning
    fi
}

cmd_lock() {
    have hyprlock || { err "hyprlock is not installed"; exit 1; }
    make_root
    printf 'This locks your REAL session with the local hyprlock look. Continue? [y/N] '
    read -r a; [[ "$a" =~ ^[yY]$ ]] || exit 0
    "$ROOT/config/hypr/scripts/lock.sh"
}

cmd_clean() {
    local d n=0
    for d in "${TMPDIR:-/tmp}"/inkpaw.*; do
        [ -d "$d" ] || continue
        rm -rf "$d"; n=$((n + 1))
    done
    ok "removed $n leftover temp dir(s)"
}

# =============================================================================
case "${1:-}" in
    deps)          cmd_deps "${2:-}" ;;
    verify)        cmd_verify ;;
    nested)        shift; cmd_nested "$@" ;;
    waybar)        cmd_waybar ;;
    launcher)      shift; cmd_launcher "$@" ;;
    notifications) cmd_notifications ;;
    menu)          shift; cmd_menu "$@" ;;
    theme)         shift; cmd_theme "$@" ;;
    lock)          cmd_lock ;;
    clean)         cmd_clean ;;
    -h|--help|help|"") usage ;;
    *) err "unknown command: $1"; usage; exit 1 ;;
esac
