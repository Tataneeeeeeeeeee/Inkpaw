# Development

- [Project layout](#project-layout)
- [Conventions](#conventions)
- [Testing](#testing)
- [Recipes](#recipes)

## Project layout

Each top-level folder has the name of its `~/.config/<app>` directory; the
login session links them into its config root (see
[installation](installation.md#how-the-login-session-works)).

```
.
├── install.sh                  # one-command installer (curl | bash)
├── test.sh                     # deps · verify · nested session · previews
├── hypr/
│   ├── hyprland.lua            # entry point: only require() lines
│   ├── settings.conf           # ★ every user value (shell syntax, read by Lua and scripts)
│   ├── settings.schema         # what Settings shows: Page/Group | key | type | choices | label | apply
│   ├── lib/                    # settings.lua (settings.conf + toggles), colors.lua
│   ├── conf/                   # one concern per file: env, monitors, input, look-and-feel,
│   │   │                       #   animations, layouts, rules, workspaces, autostart, custom
│   │   └── keybinds/           # apps, windows, workspaces, system, screenshots, media, switches
│   ├── monitors/               # monitor profiles (auto, extended, laptop-only, external-only, mirror)
│   ├── themes/default.lua      # fallback palette (current.lua is generated next to it)
│   ├── hyprlock.conf  idle/    # lock screen, idle template
│   └── scripts/                # lib.sh + one script per job; menus/ = rofi menus
├── hyprtheme/                  # theming engine
│   ├── theme.sh                # wallpaper | random | static | mode | scheme | restore | current
│   ├── templates/              # one matugen template per themed app ("@output: <path>")
│   ├── static/                 # static themes (JSON)
│   ├── hooks/                  # NN-app.sh live reloads, run after each theme change
│   ├── skin.sh  skins/encre/   # the "encre" style: skin.conf, design README, cats/
│   ├── fonts/                  # bundled OFL fonts + fonts.conf (FONTCONFIG_FILE)
│   ├── lib/accents.py          # the six accent colors
│   └── generate-wallpapers.sh  # procedural wallpapers (ImageMagick)
├── waybar/                     # build.py (generates the bar), catalog.tsv, modules/, style/, ipc-proxy.py
├── settings-app/               # Settings (GTK 4 + libadwaita), generated from the schema
├── quickpanel/                 # drop-down panel (Wi-Fi, Bluetooth, sound, brightness, battery…)
├── spotlight/                  # sectioned launcher (GTK 4 + layer-shell, Elephant backend)
├── aichat/                     # AI assistant window
├── powermenu/ keysheet/ themepicker/ wallpicker/   # full-screen GTK 4 menus of the encre style
├── pylib/hyprapp.py            # shared base of those resident menus
├── welcome/  deskpet/          # welcome window, desktop cat
├── walker/  elephant/          # launcher config and backend menus
├── swaync/  swayosd/  wlogout/  rofi/  kitty/
├── session/                    # login session: start.sh, install.sh, uninstall.sh, sddm/encre/
├── logo/                       # the logo (build.py → SVG + PNG)
└── site/                       # the website: content/{en,fr}.json → build.py → en/ fr/
```

## Conventions

- **One concern per file**, every file starts with a header explaining what it
  does, how it is used and what it depends on.
- **Every value lives in `hypr/settings.conf`** (and, when it is user-facing,
  one line in `settings.schema`). No hard-coded path or color in a module.
- **Generated files are never committed.** Theme outputs (`@output:` of the
  templates) are in `.gitignore`; the bar config is built into
  `~/.cache/inkpaw`.
- **Never write to `~/.config`.** State goes to `~/.local/state/inkpaw`, caches
  to `~/.cache/inkpaw`.
- Scripts are bash (`set -u`, `lib.sh` helpers: `have`, `notify`, `state_set`);
  processes are stopped by PID, never with `pkill -f`.
- GTK apps are Python 3 + PyGObject (GTK 4, libadwaita, gtk4-layer-shell). The
  layer-shell library must be preloaded: the apps re-exec themselves with
  `LD_PRELOAD` using `os.path.realpath(__file__)`.

## Testing

Every command copies the repo into a throw-away `$TMPDIR/inkpaw.XXXXXX`, points
`XDG_CONFIG_HOME`, `XDG_STATE_HOME` and `XDG_CACHE_HOME` at it, and deletes it
on exit. Nothing in your home folder is written.

```bash
./test.sh --help
./test.sh deps [--list]           # missing packages (+ the yay command)
./test.sh verify                  # Hyprland --verify-config on every monitor profile and mode,
                                  # JSON/JSONC/TOML/rofi/shell/Python syntax, renders every theme
./test.sh nested                  # the whole desktop in a nested Hyprland window (MOD = ALT)
./test.sh waybar                  # just the bar, in your current session
./test.sh launcher [clipboard|files|symbols]
./test.sh notifications           # private swaync + sample notifications
./test.sh menu settings|wifi|bluetooth|power|monitors|keybindings|screenshot|wallpaper|static
./test.sh theme ~/Pictures/x.jpg [--preview]  |  ./test.sh theme static:nord
./test.sh lock                    # locks your session with the local look (asks first)
./test.sh clean                   # removes temp dirs left by a killed run
```

The nested session runs `dbus-run-session -- Hyprland -c <temp>/hypr/hyprland.lua`
(private D-Bus, so its swaync and OSD do not clash with yours). Services that
would touch the host session are skipped (`host = true` in
`conf/autostart.lua`). For a full test, use the real login session.

`./test.sh verify` must pass before every commit.

## Recipes

| To add… | Do |
|---|---|
| a setting | a `KEY="value"` line (commented) in `settings.conf`, one line in `settings.schema` |
| a themed app | a template in `hyprtheme/templates/` (+ a hook, + its output in `.gitignore`) — see [theming](theming.md#adding-a-themed-app) |
| a static theme | a JSON file in `hyprtheme/static/` |
| a bar module / style | see [bar](bar.md#extending) |
| a monitor profile | a file in `hypr/monitors/` |
| a keybind | a line in `hypr/conf/keybinds/*.lua` with a `description` (shown in the cheat sheet) |
| an autostart service | a line in `hypr/conf/autostart.lua` |
| a Spotlight action | `elephant/menus/inkpaw.toml` |

The logo, the cats and the wallpapers are drawn by code:
`python3 logo/build.py`, `python3 hyprtheme/skins/encre/cats/build.py`,
`hyprtheme/generate-wallpapers.sh`.
