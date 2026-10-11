-- =============================================================================
--  conf/keybinds/screenshots.lua — capture (hyprshot), annotate (satty), OCR
-- =============================================================================
local S   = require("lib.settings")
local MOD = S.str("MOD", "SUPER")
local shot = S.script("screenshot.sh")
local exec = hl.dsp.exec_cmd

hl.bind("PRINT",               exec(shot .. " area-edit"),   { description = "Screenshot area → annotate" })
hl.bind(MOD .. " + PRINT",     exec(shot .. " menu"),        { description = "Screenshot menu" })
-- Same two without a Print key (many laptops have none)
hl.bind(MOD .. " + ALT + E",   exec(shot .. " area-edit"),   { description = "Screenshot area → annotate" })
hl.bind(MOD .. " + ALT + C",   exec(shot .. " menu"),        { description = "Screenshot menu" })
hl.bind(MOD .. " + ALT + S",   exec(shot .. " area"),        { description = "Instant area screenshot" })
hl.bind(MOD .. " + ALT + F",   exec(shot .. " screen"),      { description = "Instant full-screen screenshot" })
hl.bind(MOD .. " + ALT + A",   exec(shot .. " ocr"),         { description = "Extract text from an area (OCR)" })
