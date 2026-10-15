# The bar

The bar is **generated**: `waybar/build.py` turns the `BAR_*` settings into
`~/.cache/inkpaw/waybar/{config.json,style.css}` every time Waybar starts or
reloads. You never edit Waybar JSON by hand — use Settings → Bar or
`hypr/settings.conf`.

## Settings

| Setting | What it does |
|---|---|
| `BAR_POSITION` | `top` / `bottom` |
| `BAR_OUTPUTS` | `*` or monitor names (`eDP-1 HDMI-A-1`) |
| `BAR_LAYOUT` | `center` (all capsules in the middle), `split` (session · time · status+system), `left`, `right`, `custom` (`BAR_LEFT` / `BAR_CENTER` / `BAR_RIGHT` list the capsules) |
| `BAR_SINGLE_CAPSULE` | `true` = every capsule inside one pill, with thin separators |
| `BAR_STYLE` | `capsules`, `floating`, `solid`, `minimal`, `hyde`, `encre` (`waybar/style/presets/`) |
| `BAR_SESSION` `BAR_TIME` `BAR_STATUS` `BAR_SYSTEM` | the ordered modules of the four capsules |
| `BAR_EXTRAS` | modules hidden in the hover drawer |
| `BAR_WORKSPACES_STYLE` / `BAR_WORKSPACES_COUNT` | `dots` or `numbers`, how many are always shown |
| `BAR_CLOCK_FORMAT` | strftime format |
| `BAR_SHOW_PERCENT`, `BAR_COLORED_ICONS` | numbers next to icons; one accent per module or monochrome |
| `BAR_HEIGHT` (0 = auto), `BAR_MARGIN`, `BAR_FONT_SIZE`, `BAR_MODULE_PADDING`, `BAR_RADIUS`, `BAR_OPACITY` | sizes |
| `UPDATES_INTERVAL`, `UPDATES_SHOW_ZERO` | minutes between two update checks; keep the updates button when the system is up to date |

Modules (`waybar/catalog.tsv`): launcher, workspaces, taskbar, window, clock,
media, extras (drawer), tray, caffeine, wallpaper, brightness, keyboard, cpu,
memory, sound, network, bluetooth, battery, updates, notifications, ai, settings, power.

## Clicks

| Module | Left click | Right click | Other |
|---|---|---|---|
| launcher | Spotlight | file search | |
| workspaces | go to the workspace | | scroll = previous / next |
| taskbar | focus the window | | middle click = close |
| clock | calendar panel | long date | |
| chevron (hover) | reveals tray · caffeine · wallpaper · brightness | | |
| caffeine | toggle idle inhibit | | |
| wallpaper | wallpaper selector | random wallpaper | middle click = light / dark |
| brightness | brightness panel | | scroll = brightness |
| battery | battery & power panel | | |
| sound | sound panel | pavucontrol | middle = mute, scroll = volume |
| network | Wi-Fi panel | nmtui | middle = rofi menu |
| bluetooth | Bluetooth panel | Blueman | middle = rofi menu |
| updates | update in a floating terminal | check again | |
| notifications | notifications panel | do not disturb | middle = swaync center |
| ai | AI assistant | its settings page | |
| settings | Settings | keybindings sheet | middle = rofi settings menu |
| power | power menu | lock | |

## Commands

```bash
hypr/scripts/waybar.sh start|restart|reload|toggle|build
```

`SUPER+CTRL+B` hides / shows the bar, `SUPER+SHIFT+B` restarts it. Always
start it through `waybar.sh`: it exports `XDG_CONFIG_HOME` for the module
commands and starts the IPC relay below.

## System updates

The `updates` module shows how many packages can be updated — official
repositories (`checkupdates`, from `pacman-contrib`: it works on a copy of the
database, so the system's own is never touched), the AUR (`yay` / `paru`) and
Flatpak apps. It is hidden when everything is up to date (`UPDATES_SHOW_ZERO`)
and turns to the warning color from 50 updates; the tooltip lists them.

A click opens a floating terminal running `yay -Syu` (or `paru`, or
`sudo pacman -Syu`) then `flatpak update`; the count refreshes when it ends.
Same thing from Settings → System → Update the system, or:

```bash
hypr/scripts/updates.sh run       # the update terminal
hypr/scripts/updates.sh refresh   # check again now
```

## Under the hood

- **Workspace clicks** — Waybar switches workspace with the legacy command
  `dispatch workspace N`, which a Lua Hyprland config rejects.
  `waybar/ipc-proxy.py` sits between Waybar and Hyprland's socket and rewrites
  those dispatches into Lua (`hl.dsp.focus({ workspace = "N" })`); everything
  else is forwarded unchanged.
- **Detached commands** — Waybar kills the programs it started when it
  reloads (and a theme change reloads it). `build.py` prefixes every click /
  scroll command with `setsid -f`, so an app opened from the bar survives.

## Extending

- **New module**: `waybar/modules/foo.jsonc` (definition), one line in
  `catalog.tsv`, optionally `style/modules/foo.css`. It then shows up in Settings.
- **New style**: `waybar/style/presets/<name>.css` and its name in the
  `BAR_STYLE` choices of `hypr/settings.schema`.
