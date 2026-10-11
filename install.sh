#!/usr/bin/env bash
# =============================================================================
#  install.sh — install Inkpaw in one command
# =============================================================================
#    curl -fsSL https://raw.githubusercontent.com/Tataneeeeeeeeeee/Inkpaw/main/install.sh | bash
#  or, from a clone:  ./install.sh
#
#  What it does (asks before every step that needs sudo or installs packages):
#    1. clones (or updates) the repo into $INKPAW_DIR
#       (default ~/.local/share/inkpaw/repo; a local clone is used as is)
#    2. installs the missing packages (Arch Linux: pacman + yay/paru for AUR)
#       — the list comes from ./test.sh deps --list
#    3. keyboard: uses your system layout (localectl) if it differs from the
#       default of hypr/settings.conf (written as a setting, changeable later)
#    4. draws the procedural wallpapers into ~/Pictures/wallpapers
#       (existing files are kept)
#    5. adds the "Hyprland — Inkpaw" session to the login screen
#       (sudo session/install.sh, optionally with the "encre" SDDM theme)
#  Nothing is written to ~/.config: Inkpaw runs as its own session, your
#  usual Hyprland session stays as it is.
#
#  Options (after "| bash -s --" when piped):
#    --yes          answer yes to every question
#    --no-deps      skip the package installation
#    --no-wallpapers
#    --sddm-theme   also install the "encre" login screen theme
#    --no-session   do not touch the login screen (no sudo at all)
#    --dir DIR      where to clone (default ~/.local/share/inkpaw/repo)
#    --branch NAME  git branch (default main)
#  Example: curl -fsSL …/install.sh | bash -s -- --yes --sddm-theme
#
#  Uninstall: sudo <repo>/session/uninstall.sh [--sddm-theme], then delete
#  the repo folder and ~/.local/share/inkpaw, ~/.local/state/inkpaw, ~/.cache/inkpaw.
# =============================================================================
set -euo pipefail

REPO_URL="${INKPAW_REPO:-https://github.com/Tataneeeeeeeeeee/Inkpaw.git}"
BRANCH="main"
DIR="${INKPAW_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/inkpaw/repo}"
YES=0 DEPS=1 WALLS=1 SESSION=1 SDDM=0

while [ $# -gt 0 ]; do
    case "$1" in
        --yes|-y)        YES=1 ;;
        --no-deps)       DEPS=0 ;;
        --no-wallpapers) WALLS=0 ;;
        --sddm-theme)    SDDM=1 ;;
        --no-session)    SESSION=0 ;;
        --dir)           DIR="${2:?--dir needs a path}"; shift ;;
        --branch)        BRANCH="${2:?--branch needs a name}"; shift ;;
        -h|--help)       sed -n '2,32p' "${BASH_SOURCE[0]:-/dev/null}" 2>/dev/null | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $1 (see --help)" >&2; exit 2 ;;
    esac
    shift
done

# --- output helpers ----------------------------------------------------------
if [ -t 1 ]; then B=$'\e[1m' G=$'\e[32m' Y=$'\e[33m' R=$'\e[31m' D=$'\e[2m' N=$'\e[0m'; else B="" G="" Y="" R="" D="" N=""; fi
step() { printf '\n%s==> %s%s\n' "$B" "$1" "$N"; }
info() { printf '    %s\n' "$1"; }
warn() { printf '    %s!%s %s\n' "$Y" "$N" "$1"; }
die()  { printf '%serror:%s %s\n' "$R" "$N" "$1" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# Questions read the terminal even when the script itself comes from a pipe
ask() {   # ask "question" → 0 for yes
    [ "$YES" = 1 ] && return 0
    local a=""
    if [ -r /dev/tty ]; then printf '    %s %s[Y/n]%s ' "$1" "$D" "$N" >/dev/tty; read -r a </dev/tty || a=n
    else return 1; fi
    case "$a" in ""|y|Y|o|O|yes|oui) return 0 ;; *) return 1 ;; esac
}

[ "$(id -u)" != 0 ] || die "run this as your user, not root (sudo is asked when needed)"

printf '%s\n' "${B}🐾 Inkpaw installer${N}"

# --- 1. the repo ----------------------------------------------------------------
step "Inkpaw files"
here="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd || true)"
if [ -n "$here" ] && [ -f "$here/session/start.sh" ] && [ -f "$here/hypr/hyprland.lua" ]; then
    DIR="$here"                                   # run from a clone: use it
    info "using this clone: $DIR"
else
    have git || die "git is required (sudo pacman -S git)"
    if [ -d "$DIR/.git" ]; then
        info "updating $DIR"
        git -C "$DIR" pull --ff-only --quiet || warn "could not update (local changes?); keeping the current version"
    else
        info "cloning into $DIR"
        mkdir -p "$(dirname "$DIR")"
        git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$DIR"
    fi
fi
cd "$DIR"
chmod +x install.sh test.sh session/*.sh hypr/scripts/*.sh hypr/scripts/*/*.sh hyprtheme/*.sh hyprtheme/hooks/*.sh 2>/dev/null || true

# --- 2. packages ------------------------------------------------------------------
if [ "$DEPS" = 1 ]; then
    step "Packages"
    if ! have pacman; then
        warn "not an Arch-based system: install the packages listed by ./test.sh deps by hand"
    else
        missing="$(./test.sh deps --list)"
        if [ -z "$missing" ]; then
            info "${G}everything is already installed${N}"
        else
            info "missing: $missing"
            helper=""
            for h in yay paru; do have "$h" && { helper="$h"; break; }; done
            if [ -z "$helper" ]; then
                warn "no AUR helper (yay or paru) found: some packages (walker, elephant…) are in the AUR"
                info "install yay (https://github.com/Jguer/yay), then run this installer again,"
                info "or install them by hand: sudo pacman -S --needed <repo packages>"
            elif ask "Install them now with $helper?"; then
                # shellcheck disable=SC2086
                "$helper" -S --needed $missing </dev/tty || warn "some packages failed to install: see above"
            else
                info "skipped. Later: $helper -S --needed $missing"
            fi
        fi
    fi
fi

# --- 3. keyboard layout --------------------------------------------------------------
step "Keyboard"
default_kb="$(sed -n 's/^KB_LAYOUT="\(.*\)"/\1/p' hypr/settings.conf)"
sys_kb="$(localectl status 2>/dev/null | sed -n 's/.*X11 Layout: *//p' | head -1)"
toggles="${XDG_STATE_HOME:-$HOME/.local/state}/inkpaw/toggles.conf"
if [ -n "$sys_kb" ] && [ "$sys_kb" != "$default_kb" ] && ! grep -q '^KB_LAYOUT=' "$toggles" 2>/dev/null; then
    if ask "Your keyboard layout is \"$sys_kb\" (Inkpaw's default is \"$default_kb\"). Use \"$sys_kb\"?"; then
        mkdir -p "$(dirname "$toggles")"
        printf 'KB_LAYOUT="%s"\n' "$sys_kb" >>"$toggles"
        info "set (Settings → Displays → Keyboard & mouse to change it)"
    fi
else
    info "layout: ${sys_kb:-$default_kb}"
fi

# --- 4. wallpapers -----------------------------------------------------------------
if [ "$WALLS" = 1 ]; then
    step "Wallpapers"
    walls="$HOME/Pictures/wallpapers"
    if ! have magick; then
        warn "ImageMagick missing: skipped (later: hyprtheme/generate-wallpapers.sh)"
    elif ask "Draw the Inkpaw wallpapers into $walls (about a minute)?"; then
        XDG_CONFIG_HOME=/nonexistent bash hyprtheme/generate-wallpapers.sh "$walls" | sed 's/^/    /'
    else
        info "skipped. Later: $DIR/hyprtheme/generate-wallpapers.sh"
    fi
fi

# --- 5. login session ----------------------------------------------------------------
if [ "$SESSION" = 1 ]; then
    step "Login session"
    if ask "Add \"Hyprland — Inkpaw\" to the login screen (needs sudo)?"; then
        opt=()
        if [ "$SDDM" = 1 ]; then opt=(--sddm-theme)
        elif [ -d /usr/share/sddm ] && [ "$YES" = 0 ] && ask "Also install the \"encre\" SDDM login theme?"; then opt=(--sddm-theme); fi
        sudo ./session/install.sh "${opt[@]}" | sed 's/^/    /'
    else
        info "skipped. Later: sudo $DIR/session/install.sh [--sddm-theme]"
    fi
fi

# --- done ------------------------------------------------------------------------------
step "Done"
info "Inkpaw is in ${B}$DIR${N}"
info "Log out, pick ${B}Hyprland — Inkpaw${N} in the session menu of the login screen, log in."
info "A welcome window opens at the first login. Then: ${B}SUPER+SPACE${N} search, ${B}SUPER+CTRL+S${N} settings, ${B}SUPER+CTRL+K${N} all the shortcuts."
info "Check the setup any time with: ${D}$DIR/test.sh deps${N} and ${D}$DIR/test.sh verify${N}"
