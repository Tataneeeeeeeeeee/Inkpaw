# Installation

- [One-line install](#one-line-install)
- [Manual install](#manual-install)
- [Dependencies](#dependencies)
- [How the login session works](#how-the-login-session-works)
- [The SDDM login theme](#the-sddm-login-theme)
- [Updating](#updating)
- [Uninstalling](#uninstalling)
- [Troubleshooting](#troubleshooting)

Inkpaw targets **Arch Linux** (and Arch-based distributions) with
**Hyprland 0.56 or newer** (the Lua configuration). It never writes to
`~/.config`: it runs as a separate login session next to your usual one.

## One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/Tataneeeeeeeeeee/Inkpaw/main/install.sh | bash
```

`install.sh` asks before every step that installs something or needs `sudo`:

| Step | What happens |
|---|---|
| Files | clones the repo into `~/.local/share/inkpaw/repo` (or updates it with `git pull --ff-only`). Run from a clone, it uses that clone. |
| Packages | `./test.sh deps --list` gives the missing packages, installed with `yay` or `paru` (some, like Walker and Elephant, are in the AUR). Without an AUR helper it prints what to install. |
| Keyboard | if your system layout (`localectl`) differs from the default of `hypr/settings.conf` (`fr`), it is saved as your setting. |
| Wallpapers | `hyprtheme/generate-wallpapers.sh` draws 15 wallpapers into `~/Pictures/wallpapers` (about a minute; existing files are kept). |
| Login session | `sudo session/install.sh` adds **Hyprland — Inkpaw** to the session menu of the login screen. |

Options, passed after `bash -s --` when piped:

| Option | |
|---|---|
| `--yes` | answer yes to every question |
| `--sddm-theme` | also install the “encre” SDDM login theme |
| `--no-deps` | do not install packages |
| `--no-wallpapers` | do not draw the wallpapers |
| `--no-session` | do not add the login session (no `sudo` at all) |
| `--dir DIR` | clone somewhere else |
| `--branch NAME` | another branch |

```bash
curl -fsSL https://raw.githubusercontent.com/Tataneeeeeeeeeee/Inkpaw/main/install.sh | bash -s -- --yes --sddm-theme
```

Then **log out**, choose **Hyprland — Inkpaw** in the session menu of the
login screen (bottom-left on SDDM) and log in. The login screen remembers the
last session you picked.

## Manual install

```bash
git clone https://github.com/Tataneeeeeeeeeee/Inkpaw.git ~/Inkpaw
cd ~/Inkpaw
./test.sh deps                          # what is missing + the yay command
./test.sh verify                        # checks the whole config in a temp copy
hyprtheme/generate-wallpapers.sh        # optional: the wallpapers
sudo ./session/install.sh               # add the login session (--sddm-theme for the login screen)
```

You can keep the clone anywhere: the session entry points to the folder you
ran `session/install.sh` from. Run it again if you move the folder.

## Dependencies

`./test.sh deps` checks everything below and prints one `yay -S --needed …`
command for what is missing.

| Group | Packages |
|---|---|
| Hyprland | `hyprland` `hyprlock` `hypridle` `hyprsunset` |
| Desktop | `waybar` `rofi` `walker` `elephant` (+ `elephant-desktopapplications` `-files` `-calc` `-websearch` `-clipboard` `-runner` `-symbols` `-providerlist` `-menus`) `swaync` `swayosd` `wlogout` |
| Theming | `matugen` `awww` (or `swww`) `jq` `imagemagick` |
| System | `networkmanager` `bluez-utils` `blueman` `wireplumber` `pavucontrol` `brightnessctl` `playerctl` `libnotify` `dbus` |
| Screenshots | `hyprshot` `satty` `grim` `slurp` `wl-clipboard` |
| Apps | `kitty` `python-gobject` `python-cairo` `gtk4` `libadwaita` `gtk4-layer-shell` |
| Fonts | `ttf-jetbrains-mono-nerd` `ttf-cascadia-code-nerd` |
| Optional | `python-markdown-it-py` (Markdown in the AI chat), `python-anthropic` (Claude), `tesseract-data-eng`/`-fra` (OCR screenshots), `nwg-displays`, `ddcutil` (external screen brightness), `power-profiles-daemon`, `pywalfox`, `shellcheck` |

The default text font is *Google Sans Flex* (`FONT_FAMILY`): when it is not
installed the default sans font is used. Change it in Settings → Appearance.

Without Walker / Elephant the launcher falls back to `rofi -show drun`; without
swayosd the volume and brightness keys still work, with a plain notification.

## How the login session works

`session/install.sh` writes `/usr/share/wayland-sessions/inkpaw.desktop`,
which runs `session/start.sh`. At every login, `start.sh`:

1. rebuilds `~/.local/share/inkpaw/session-root`, a “merged” config folder:
   - **symlinks to this repo** for Inkpaw's folders (`hypr`, `hyprtheme`,
     `waybar`, `swaync`, …) — so your edits are live (`SUPER+CTRL+R`);
   - **symlinks to your real `~/.config/*`** for everything else (browser,
     editor, chat apps keep their settings);
   - real `gtk-3.0`, `gtk-4.0` and `kitty` folders whose files point to yours,
     except the files Inkpaw generates (`gtk.css`, the kitty theme), so your
     own files are never overwritten;
2. sets `XDG_CONFIG_HOME` to it (also for systemd / D-Bus activated services);
3. starts Hyprland with `hypr/hyprland.lua`.

Good to know:

- It is a real session: idle, lock, portals and polkit are active.
- The palette is rendered into the repo's own files (`waybar/style/colors.css`,
  `hypr/themes/current.lua`…). They are listed in `.gitignore`.
- A folder an app creates in `~/.config` during the session is moved to your
  real `~/.config` at the next login.
- When Hyprland exits, `XDG_CONFIG_HOME` is removed from the systemd
  environment, so your other session never inherits it.
- Log: `~/.local/share/inkpaw/session.log`.

Inkpaw's own state lives in `~/.local/state/inkpaw` (your settings, last
theme, conversations, notification history) and `~/.cache/inkpaw`.

## The SDDM login theme

```bash
sudo ./session/install.sh --sddm-theme      # undo: sudo ./session/uninstall.sh --sddm-theme
sddm-greeter-qt6 --test-mode --theme /usr/share/sddm/themes/inkpaw-encre   # preview
```

The “encre” login screen (clock, user card with a cat, session chooser, power
buttons) is copied to `/usr/share/sddm/themes/inkpaw-encre` with its fonts and
images — SDDM cannot read your home folder — and selected in
`/etc/sddm.conf.d/zz-inkpaw-theme.conf`. Its background is drawn during the
install. Colors and texts can be changed in `theme.conf.user` next to it.

## Updating

```bash
cd ~/.local/share/inkpaw/repo && git pull     # or run the one-line installer again
```

Then `SUPER+CTRL+R` (reload) or log out and in. Your settings are in
`~/.local/state/inkpaw/toggles.conf`, outside the repo, and survive updates.

## Uninstalling

```bash
sudo ~/.local/share/inkpaw/repo/session/uninstall.sh --sddm-theme
rm -rf ~/.local/share/inkpaw ~/.local/state/inkpaw ~/.cache/inkpaw
```

Your `~/.config` was never modified. The wallpapers in `~/Pictures/wallpapers`
are yours to keep or delete.

## Troubleshooting

| Problem | Fix |
|---|---|
| The session does not start | Pick your usual session, read `~/.local/share/inkpaw/session.log`, run `./test.sh verify`. |
| Something is missing | `./test.sh deps` |
| Clicking a workspace number does nothing | The bar must run through `hypr/scripts/waybar.sh` (it starts the IPC relay `waybar/ipc-proxy.py`). `SUPER+SHIFT+B` restarts it. |
| Notifications do not follow the theme | Another daemon (mako, dunst) took the notification name: `hypr/scripts/notifications.sh restart`. |
| An app opened from the bar closes on a theme change | Rebuild the bar (`SUPER+SHIFT+B`): bar commands are detached with `setsid`. |
| Wrong keyboard layout | Settings → Displays → Keyboard & mouse, or `KB_LAYOUT` in `hypr/settings.conf`. |
| Wrong monitor setup | `SUPER+SHIFT+M` (monitor profiles), or `MONITOR_*` in `hypr/settings.conf`. |
