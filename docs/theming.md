# Theming

- [Wallpapers and palettes](#wallpapers-and-palettes)
- [Static themes](#static-themes)
- [Accent colors](#accent-colors)
- [The “encre” style](#the-encre-style)
- [Adding a themed app](#adding-a-themed-app)
- [Firefox (pywalfox)](#firefox-pywalfox)

## Wallpapers and palettes

`SUPER+CTRL+W` opens the wallpaper selector. The new image fades in (awww),
then **matugen** computes a Material palette from it and the theme engine
(`hyprtheme/theme.sh`) renders it into every app: Hyprland borders, Waybar,
Spotlight / Walker, rofi menus, swaync, wlogout, swayosd, hyprlock, kitty and
GTK 3/4 (plus the libadwaita light / dark preference).

| | |
|---|---|
| `SUPER+CTRL+W` / `SUPER+SHIFT+W` | wallpaper selector / random wallpaper |
| `CTRL+ALT+T` | static theme selector |
| `SUPER+CTRL+T` | light ↔ dark (static themes switch to their `pair`) |
| Settings → Appearance → *Palette style* | matugen scheme: tonal-spot, vibrant (default), expressive… |

```bash
hyprtheme/theme.sh wallpaper ~/Pictures/x.jpg
hyprtheme/theme.sh random | static nord | mode dark | scheme scheme-expressive | current
```

**Wallpapers**: `hyprtheme/generate-wallpapers.sh [dir] [WxH]` draws 15
procedural 4K wallpapers with ImageMagick (gradients, aurora, waves, sunsets,
plasma, ink hills) into `WALLPAPER_DIR` (`~/Pictures/wallpapers`). Existing
files are kept; delete one to redraw it. Your own images go in the same folder.

## Static themes

`hyprtheme/static/*.json`: Catppuccin Mocha / Latte, Tokyo Night, Rosé Pine,
Nord, Gruvbox Dark, Synthwave '84, Encre parchemin / nuit. Each one can bundle
a wallpaper (`"wallpaper"`, a file in `WALLPAPER_DIR`) applied with it.

To add one, copy a file and set `seed` (fills every role you leave out),
`mode`, an optional `pair` (its light / dark sibling), the `colors` roles and
optionally `accents`.

## Accent colors

On top of the Material palette the engine computes **six accents**
(`hyprtheme/lib/accents.py`): `ACCENT_STYLE="wallbash"` (default) gives
tone-on-tone pastels of the wallpaper's hue, `"rainbow"` six different hues.
Static themes bring their own. Templates use them as `{{accent.a1}}` …
`{{accent.a6}}`; they become `@a1`…`@a6` in CSS and rofi and `C.a1` in Lua.

They color the bar modules, the active workspace pill, the selection in menus
and launcher, the swaync toggles, the power menu buttons, the OSD and lock
screen gradients and the focused window border (`BORDER_ANIMATE` rotates it).

## The “encre” style

Settings → Appearance → **Interface style** → *encre* (or
`hyprtheme/skin.sh apply encre`, back with `skin.sh apply default`).

A hand-drawn look for the **fonts, the apps and menus, and the top bar**:
opaque parchment panels outlined in ink, uneven corners, hard shadows, brush
titles and six original cats (drawn by `hyprtheme/skins/encre/cats/build.py`).
Your colors, wallpaper and window settings stay yours — the style follows the
current palette. The matching themes *Encre parchemin* / *Encre nuit* are in
the theme selector.

- Bundled fonts (Shantell Sans, Caveat Brush, Courier Prime — OFL) in
  `hyprtheme/fonts/`, loaded with `FONTCONFIG_FILE`: nothing is installed.
- Skinned when `UI_SKIN=encre`: the Waybar preset, Spotlight, quick panel,
  notifications, OSD, AI chat, Settings, lock screen, power menu, rofi menus,
  cheat sheet, theme and wallpaper selectors, screenshot selection, kitty font.
- The four full-screen menus (power, cheat sheet, themes, wallpapers) and the
  quick panel stay in memory, hidden, so they open in ~50 ms
  (`hypr/scripts/resident.sh`, `pylib/hyprapp.py`).
- Extras: the desktop cat (`DESKTOP_PET`, click it), the welcome window,
  the SDDM login theme (see [installation](installation.md#the-sddm-login-theme)).
- The mockups' ink border and hard window shadow are window settings:
  `BORDER_STYLE=ink`, `SHADOW_STYLE=hard`.
- Design spec and screen → file map: `hyprtheme/skins/encre/README.md`.

## Adding a themed app

Adding a themed app is **adding one file** to `hyprtheme/templates/`. Its first
lines contain `@output: <path relative to the config root>` (or
`@output: cache:<path>`). Use `{{colors.<role>.default.hex}}`
(`.hex_stripped`), `{{base16.base0X.default.hex}}`, `{{mode}}`, `{{accent.aN}}`
and `{{ui.font}}`, `{{ui.radius}}`, `{{ui.opacity}}`, `{{ui.opacity_hex}}`,
`{{ui.display_font}}`, `{{ui.skin_dir}}`.

Add `hyprtheme/hooks/NN-app.sh` to live-reload the app after a theme change.
Move a template to `templates/disabled/` to switch it off. Add its output to
`.gitignore`: generated files contain machine-specific paths.

## Firefox (pywalfox)

The palette is also written in pywal format to `~/.cache/wal/colors.json`, and
`hooks/80-pywalfox.sh` runs `pywalfox update` after every theme change.
One-time setup:

```bash
pywalfox install
# then install the "Pywalfox" Firefox extension, open it, click "Fetch Pywal colors"
```
