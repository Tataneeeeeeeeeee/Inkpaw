# Configuration

- [Where values live](#where-values-live)
- [The Settings app](#the-settings-app)
- [The settings system](#the-settings-system)
- [Default applications and terminal](#default-applications-and-terminal)
- [Hyprland modules](#hyprland-modules)
- [Monitors](#monitors)
- [Battery alerts](#battery-alerts)

## Where values live

| What | File |
|---|---|
| **Every user value**: apps, keyboard, monitors, gaps, borders, blur, fonts, radius, opacity, bar, wallpaper folder, idle timeouts, screenshot folder, AI provider… | `hypr/settings.conf` (the defaults, commented) |
| What you changed in Settings | `~/.local/state/inkpaw/toggles.conf` — overrides `settings.conf`, outside the repo |
| Last theme (wallpaper or static theme), restored at login | `~/.local/state/inkpaw/theme.conf` |
| API keys of the AI assistant | `~/.local/state/inkpaw/secrets.conf` (mode 600) |
| Keybindings | `hypr/conf/keybinds/*.lua` (modifier = `MOD` in `settings.conf`) |
| Personal Hyprland tweaks | `hypr/conf/custom.lua`, loaded last |

`settings.conf` uses shell syntax, so the Lua config and every script read the
same file. Fonts, radius and opacity are injected into every theme template as
`{{ui.font}}`, `{{ui.radius}}`… so one change restyles the bar, the menus, the
notifications, the OSD and the lock screen.

## The Settings app

`SUPER+CTRL+S` (or the 󰒓 button of the bar) opens `settings-app/settings_app.py`,
a GTK 4 + libadwaita window:

- a sidebar of pages — **Bar, Applications, AI assistant, Appearance, Windows,
  Displays, System** — split into groups;
- switches, drop-down lists, − / + number fields and text fields with a ⋮
  menu of suggestions;
- ordered lists for the bar capsules: tick the modules to show, ↑ / ↓ to reorder;
- action buttons (wallpaper selector, monitor profiles, Wi-Fi…);
- a ↺ button on every changed row and **Reset <page>** at the bottom.

Changes apply live (numbers and text after a short pause).
`hypr/scripts/settings-ui.sh [Page]` opens it on a page. `SETTINGS_UI="rofi"`
uses the rofi menu instead; a middle click on 󰒓 always opens the rofi menu.

## The settings system

The window and the rofi menu are both generated from **`hypr/settings.schema`**,
one line per option:

```
Page/Group | KEY | type | choices | label | apply
```

- Types: `bool`, `choice`, `number`, `text` (free value + suggestions),
  `modules` / `capsules` (ordered lists), `action`.
- `apply` says what to reload: `hypr` (Hyprland), `bar`, `theme` (re-render
  the colors), `mode`, `scheme`, `skin`, `apps`, `pet`…
- A change is written to `toggles.conf`; *Reset* deletes it again. Your
  `settings.conf` is never rewritten.
- Scriptable: `hypr/scripts/menus/settings.sh set BAR_POSITION bottom`,
  `settings.sh unset KEY`, `settings.sh Bar` opens a section.
- To expose any other `settings.conf` key, add one line to the schema.

## Default applications and terminal

Settings → **Applications**:

- **Default applications**: terminal, browser, file manager, text editor,
  calculator, audio mixer, Bluetooth manager, and three personal shortcuts
  (`SUPER+D` / `P` / `O`, Discord / Spotify / Teams by default). Each is a
  drop-down of the apps installed on your system, plus *Other…*. Changing the
  browser or file manager also makes it the system default (`xdg-settings`,
  `xdg-mime`).
- **Terminal (kitty)**: font, size, background opacity, padding, cursor.
  Written to `kitty/inkpaw-settings.conf`, included after your own
  `kitty.conf`; kitty reloads at once.
- **File manager**: hidden files, list or grid view.

## Hyprland modules

`hypr/hyprland.lua` only contains `require()` lines — one per concern in
`hypr/conf/` (env, monitors, input, gestures, look and feel, animations,
layouts, window rules, layer rules, workspaces, autostart, keybinds, custom).

- **Turn a module off**: comment its `require(...)` line.
- **Change a value**: edit `hypr/settings.conf` (or use Settings), then `SUPER+CTRL+R`.
- **Window rule**: one `floating("name", "class-regex", "W H")` line in `conf/windowrules.lua`.
- **Animation preset**: a new file in `conf/animations/`, then `ANIMATION_PRESET`.
- **Autostart service**: one line in `conf/autostart.lua` (`enabled = false` to skip it).
- **Personal tweaks**: `conf/custom.lua`.

## Monitors

`SUPER+SHIFT+M` opens the monitor profiles: `auto`, `extended`, `laptop-only`,
`external-only`, `mirror` (`hypr/monitors/*.lua`). The names of your screens
are `MONITOR_LAPTOP` / `MONITOR_EXTERNAL` in `settings.conf` (`hyprctl monitors`
lists them), with `MONITOR_EXTERNAL_SIDE`. A new profile is a new file in
`hypr/monitors/`: it shows up in the menu by itself. Closing the lid turns the
laptop panel off when an external screen is connected.

## Battery alerts

`hypr/scripts/battery-alert.sh` checks `upower` every minute and sends one
notification each time a level is crossed: the laptop battery at
`BATTERY_ALERT_LEVELS` (20 / 10 / 5 %, the lowest is critical) and mouse,
headset or keyboard at `DEVICE_ALERT_LEVEL` (15 %). Charging re-arms them.
Both are in Settings → System → Battery alerts.
