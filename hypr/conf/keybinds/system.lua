-- =============================================================================
--  conf/keybinds/system.lua — launcher, menus, theming, bar, session
-- =============================================================================
local S   = require("lib.settings")
local MOD = S.str("MOD", "SUPER")
local exec = hl.dsp.exec_cmd
local sc  = S.script

-- Spotlight launcher (Walker) -----------------------------------------------------
hl.bind(MOD .. " + SPACE",          exec(sc("launcher.sh")),              { description = "Spotlight search" })
hl.bind(MOD .. " + A",              exec(sc("launcher.sh")),              { description = "Spotlight search" })
hl.bind(MOD .. " + CTRL + RETURN",  exec(sc("launcher.sh")),              { description = "Spotlight search" })
hl.bind(MOD .. " + V",              exec(sc("launcher.sh") .. " clipboard"), { description = "Clipboard history" })
hl.bind(MOD .. " + CTRL + E",       exec(sc("launcher.sh") .. " symbols"),   { description = "Emoji & symbol picker" })

-- AI chat side panel ---------------------------------------------------------------
hl.bind(MOD .. " + I",         exec(sc("aichat.sh")),             { description = "AI assistant (chat panel)" })

-- Menus ----------------------------------------------------------------------------
hl.bind(MOD .. " + CTRL + S",  exec(sc("settings-ui.sh")),         { description = "Settings" })
hl.bind(MOD .. " + CTRL + K",  exec(sc("menus/keybindings.sh")),  { description = "Keybindings cheat sheet" })
hl.bind(MOD .. " + SHIFT + M", exec(sc("menus/monitors.sh")),     { description = "Monitor profiles" })
hl.bind(MOD .. " + CTRL + P",  exec(sc("menus/power.sh")),        { description = "Power menu" })

-- Notifications ---------------------------------------------------------------------
hl.bind(MOD .. " + N",         exec(sc("quickpanel.sh") .. " notifications"), { description = "Notifications" })
hl.bind(MOD .. " + SHIFT + N", exec("swaync-client -d -sw"), { description = "Toggle Do Not Disturb" })

-- Wallpaper & theme -----------------------------------------------------------------
local theme = S.paths.theme .. "/theme.sh"
hl.bind(MOD .. " + CTRL + W",  exec(S.paths.theme .. "/wallpaper-picker.sh"), { description = "Wallpaper selector" })
hl.bind(MOD .. " + SHIFT + W", exec(theme .. " random"),                      { description = "Random wallpaper" })
hl.bind(MOD .. " + CTRL + T",  exec(theme .. " mode toggle"),                 { description = "Toggle light / dark mode" })
hl.bind("CTRL + ALT + T",      exec(S.paths.theme .. "/static-picker.sh"),    { description = "Static theme selector" })

-- Waybar ----------------------------------------------------------------------------
hl.bind(MOD .. " + CTRL + B",  exec(sc("waybar.sh") .. " toggle"), { description = "Toggle status bar" })
hl.bind(MOD .. " + SHIFT + B", exec(sc("waybar.sh") .. " restart"), { description = "Restart status bar" })

-- Toggles ---------------------------------------------------------------------------
hl.bind(MOD .. " + SHIFT + A", exec(sc("toggle.sh") .. " ANIMATIONS"), { description = "Toggle animations" })
hl.bind(MOD .. " + ALT + G",   exec(sc("toggle.sh") .. " GAMEMODE"),   { description = "Toggle game mode" })
hl.bind(MOD .. " + SHIFT + H", exec(sc("nightlight.sh")),              { description = "Toggle night light (hyprsunset)" })

-- Session ---------------------------------------------------------------------------
hl.bind(MOD .. " + L",         exec(sc("lock.sh")), { description = "Lock screen" })
hl.bind(MOD .. " + CTRL + L",  exec(sc("lock.sh")), { description = "Lock screen" })
hl.bind(MOD .. " + CTRL + R",  exec("hyprctl reload"), { description = "Reload Hyprland config" })
hl.bind(MOD .. " + SHIFT + R", exec("hyprctl reload"), { description = "Reload Hyprland config" })
