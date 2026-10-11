# Apps

- [Spotlight](#spotlight)
- [Walker and Elephant](#walker-and-elephant)
- [Quick panel](#quick-panel)
- [Notifications](#notifications)
- [AI assistant](#ai-assistant)
- [Menus](#menus)
- [Screenshots](#screenshots)
- [Welcome window and desktop cat](#welcome-window-and-desktop-cat)

## Spotlight

`SUPER+SPACE` (also `SUPER+A`). `spotlight/spotlight.py` is a GTK 4 +
layer-shell launcher showing **one list with a titled separator between each
kind of result**: calculator, applications, desktop actions, files and
folders, emoji, clipboard, web and maps, command. Search is done by Elephant
(the Walker backend, ~15–30 ms per provider).

- Prefixes for one section only: `=` calc, `/` files, `.` emoji, `:` clipboard,
  `@` web, `>` run. `:` alone lists the last 15 clipboard entries.
- Keys: ↑/↓ move, Enter opens, Shift+Enter is the alternative (open the folder
  of a file, run a command in a terminal, copy an emoji without typing it),
  Tab / Ctrl+↓ next section, Esc closes.
- Web rows: `elephant/websearch.toml` (`map …`, `yt …`, `wiki …`, `aw` Arch Wiki,
  `aur`, `gh`…). Desktop actions: `elephant/menus/inkpaw.toml`.
- Look and section order: `spotlight/config.toml` (`style = "hyde"` with a
  slanted picture of the wallpaper, or `"classic"`).
- `LAUNCHER="walker"` in `settings.conf` uses Walker instead.

## Walker and Elephant

`SUPER+V` opens the clipboard history (with images) and `SUPER+CTRL+E` the
emoji grid in Walker. Providers and prefixes: `walker/config.toml`; look:
`walker/themes/inkpaw/`. Walker covers apps, files, calculator, web, clipboard,
runner, emoji and custom menus natively, each source being an Elephant
provider package. Rofi is kept for the menus.

## Quick panel

`quickpanel/quickpanel.py`: a drop-down under the bar that shows **only the
section of the icon you clicked**. It stays in memory, so it opens at once.

| Section | Opened by | Contents |
|---|---|---|
| Wi-Fi | network icon | status · IP · scan · switch, networks (connect, disconnect, forget, password dialog) |
| Bluetooth | bluetooth icon | your devices (connect, battery, remove), scan, nearby devices (pair + trust + connect) |
| Sound | sound icon | output and microphone volume + device, one slider per app playing sound |
| Brightness | brightness icon (drawer) | laptop panel, external screens over DDC/CI (`ddcutil`), keyboard backlight, night light + temperature |
| Battery | battery icon | level, time left, power draw, health, power mode (power-profiles-daemon), devices' batteries |
| Notifications | bell icon, `SUPER+N` | history (today / earlier), dismiss, open the sender, do not disturb, clear all |
| Calendar | clock | month view with week numbers, back to today |
| Media | now-playing module | cover, title, seek bar, previous / play / next, player chooser |

Clicking the same icon again, Esc or a click outside closes it. Without GTK 4
layer-shell, `hypr/scripts/quickpanel.sh` falls back to the rofi menus.

## Notifications

swaync (`swaync/config.json`): popups, a control center with quick toggles
(Wi-Fi, Bluetooth, wallpaper, settings, screenshot, light/dark, lock, power),
do not disturb, volume and media. Every notification is also logged to
`~/.local/state/inkpaw/notifications.jsonl` (last 200) for the quick panel.
`hypr/scripts/notifications.sh start|restart|reload` makes sure *this* swaync
owns the notifications, even if another daemon (mako, dunst) was started.

## AI assistant

`SUPER+I` or the 󰚩 button. `aichat/aichat.py` is a chat window that docks on
the right (or left, `AI_SIDE`, `AI_WIDTH`): while it is open your tiled
windows make room for it, and closing it gives the space back.

- Enter sends, Shift+Enter adds a line, Esc closes. Answers stream in with
  full Markdown (code blocks with a Copy button, tables, lists…) and a Copy
  button under each answer.
- **Conversations** are kept in `~/.local/state/inkpaw/aichat-chats.json`:
  `Ctrl+O` lists them (search, rename, delete), `Ctrl+N` starts a new one.
- **Claude** (default): the Anthropic Python SDK (`python-anthropic`), model
  `AI_MODEL`, effort `AI_EFFORT`. Without a key in Settings it uses
  `ANTHROPIC_API_KEY`.
- **Other providers**: `openai`, `ollama` (local), `openrouter`, or `custom`
  (any OpenAI-compatible endpoint, `AI_BASE_URL`).
- Settings → **AI assistant**: provider, model, effort, endpoint, API keys
  (stored in `~/.local/state/inkpaw/secrets.conf`, mode 600, never in the repo),
  side, width, custom instructions.

## Menus

| | |
|---|---|
| `SUPER+CTRL+P` | power menu (lock, log out, suspend, reboot, shut down) |
| `SUPER+CTRL+K` | cheat sheet of every shortcut, by category, with a filter |
| `SUPER+CTRL+W` / `CTRL+ALT+T` | wallpaper / theme selectors |
| `SUPER+SHIFT+M` | monitor profiles |
| Wi-Fi, Bluetooth, settings, screenshot | rofi menus (`hypr/scripts/menus/`) |

With the “encre” style the power menu, cheat sheet and both selectors are GTK 4
full-screen apps (`powermenu/`, `keysheet/`, `themepicker/`, `wallpicker/`);
otherwise wlogout and rofi are used.

## Screenshots

| | |
|---|---|
| `PRINT` or `SUPER+ALT+E` | select an area, then annotate it (satty) |
| `SUPER+PRINT` or `SUPER+ALT+C` | screenshot menu |
| `SUPER+ALT+S` / `SUPER+ALT+F` | area / full screen, saved and copied at once |
| `SUPER+ALT+A` | area → text in the clipboard (OCR, `tesseract`) |

Files go to `SCREENSHOT_DIR` (`~/Pictures/Screenshots`).

## Welcome window and desktop cat

- `welcome/welcome.py`: four steps at the first login (wallpaper, bar,
  default apps, shortcuts). Reopen it from Settings → System → Tools.
- `deskpet/deskpet.py`: a cat peeking from the bottom of the screen
  (`DESKTOP_PET`, `DESKTOP_PET_CAT`); click it.
