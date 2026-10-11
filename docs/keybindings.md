# Keybindings

`MOD` is `SUPER` (`MOD` in `hypr/settings.conf`; `ALT` inside
`./test.sh nested`). The live, searchable list is **`SUPER+CTRL+K`**: it is
generated from the `description` of every bind in `hypr/conf/keybinds/*.lua`,
so a bind you add shows up there by itself.

With an AZERTY layout (`KB_LAYOUT="fr"`) the workspace keys are the unshifted
number row (`& é " ' ( - è _ ç à`); with other layouts, `1`…`0`.

| Keys | Action |
|---|---|
| **Apps** | |
| `SUPER+RETURN` | terminal |
| `SUPER+B` / `E` / `C` | browser / file manager / calculator |
| `SUPER+D` / `P` / `O` | personal shortcuts (Discord / Spotify / Teams by default, Settings → Applications) |
| **Search** | |
| `SUPER+SPACE`, `SUPER+A`, `SUPER+CTRL+RETURN` | Spotlight |
| `SUPER+V` | clipboard history |
| `SUPER+CTRL+E` | emoji & symbols |
| **Windows** | |
| `SUPER+Q` | close · `SUPER+SHIFT+Q` kill the process |
| `SUPER+F` / `SUPER+M` | fullscreen / maximize |
| `SUPER+T` | float · `SUPER+SHIFT+T` float every window of the workspace · `SUPER+ALT+T` float + pin |
| `SUPER+J` / `K` / `G` | toggle split / swap split / group |
| `SUPER+arrows` | focus · `SUPER+ALT+arrows` swap · `SUPER+SHIFT+arrows` resize |
| `SUPER` + left / right mouse drag | move / resize |
| **Workspaces** | |
| `SUPER+1…0` | go to workspace 1–10 · `SUPER+SHIFT+1…0` move the window there |
| `SUPER+mouse wheel` | previous / next workspace |
| `SUPER+S` / `SUPER+SHIFT+S` | scratchpad: show / send the window |
| **Menus & system** | |
| `SUPER+CTRL+S` | Settings |
| `SUPER+I` | AI assistant |
| `SUPER+CTRL+K` | cheat sheet |
| `SUPER+SHIFT+M` | monitor profiles |
| `SUPER+CTRL+P` | power menu |
| `SUPER+N` / `SUPER+SHIFT+N` | notifications / do not disturb |
| `SUPER+CTRL+W` / `SUPER+SHIFT+W` | wallpaper selector / random wallpaper |
| `SUPER+CTRL+T` / `CTRL+ALT+T` | light ↔ dark / theme selector |
| `SUPER+CTRL+B` / `SUPER+SHIFT+B` | hide-show / restart the bar |
| `SUPER+SHIFT+A` / `SUPER+ALT+G` / `SUPER+SHIFT+H` | animations / game mode / night light |
| `SUPER+L`, `SUPER+CTRL+L` | lock |
| `SUPER+CTRL+R`, `SUPER+SHIFT+R` | reload Hyprland |
| **Screenshots** | |
| `PRINT` or `SUPER+ALT+E` | area → annotate (satty) |
| `SUPER+PRINT` or `SUPER+ALT+C` | screenshot menu |
| `SUPER+ALT+S` / `SUPER+ALT+F` | instant area / full screen |
| `SUPER+ALT+A` | area → text in the clipboard (OCR) |
| **Hardware** | volume, microphone and brightness keys (with OSD), media keys (playerctl); closing the lid turns the laptop panel off when an external screen is connected |
