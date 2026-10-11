-- =============================================================================
--  conf/keybinds/apps.lua — launch applications
-- =============================================================================
--  Apps are defined in settings.conf. Every bind has a description: it shows
--  up in the cheat sheet (SUPER+CTRL+K).
-- =============================================================================
local S   = require("lib.settings")
local MOD = S.str("MOD", "SUPER")
local exec = hl.dsp.exec_cmd

hl.bind(MOD .. " + RETURN", exec(S.str("TERMINAL", "kitty")),            { description = "Terminal" })
hl.bind(MOD .. " + B",      exec(S.str("BROWSER", "firefox")),           { description = "Browser" })
hl.bind(MOD .. " + E",      exec(S.str("FILEMANAGER", "nautilus")),      { description = "File manager" })
hl.bind(MOD .. " + C",      exec(S.str("CALCULATOR", "gnome-calculator")), { description = "Calculator" })

-- Personal apps (from your custom.lua)
hl.bind(MOD .. " + D", exec(S.str("APP_CHAT", "discord")),          { description = "Discord" })
hl.bind(MOD .. " + P", exec(S.str("APP_MUSIC", "spotify-launcher")), { description = "Spotify" })
hl.bind(MOD .. " + O", exec(S.str("APP_TEAMS", "teams-for-linux")),  { description = "Microsoft Teams" })
