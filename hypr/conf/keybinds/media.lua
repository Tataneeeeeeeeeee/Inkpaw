-- =============================================================================
--  conf/keybinds/media.lua — volume, brightness, players (with OSD)
-- =============================================================================
--  osd.sh uses swayosd-client when available, falls back to wpctl/brightnessctl.
-- =============================================================================
local S   = require("lib.settings")
local osd = S.script("osd.sh")
local exec = hl.dsp.exec_cmd
local hw  = { locked = true, repeating = true }

local function key(k, cmd, desc)
    hl.bind(k, exec(cmd), { locked = hw.locked, repeating = hw.repeating, description = desc })
end

key("XF86AudioRaiseVolume",  osd .. " volume up",       "Raise volume")
key("XF86AudioLowerVolume",  osd .. " volume down",     "Lower volume")
key("XF86AudioMute",         osd .. " volume mute",     "Mute audio")
key("XF86AudioMicMute",      osd .. " mic mute",        "Mute microphone")
key("XF86MonBrightnessUp",   osd .. " brightness up",   "Increase brightness")
key("XF86MonBrightnessDown", osd .. " brightness down", "Decrease brightness")

-- Players (playerctl)
hl.bind("XF86AudioNext",  exec("playerctl next"),       { locked = true, description = "Next track" })
hl.bind("XF86AudioPrev",  exec("playerctl previous"),   { locked = true, description = "Previous track" })
hl.bind("XF86AudioPlay",  exec("playerctl play-pause"), { locked = true, description = "Play / pause" })
hl.bind("XF86AudioPause", exec("playerctl play-pause"), { locked = true, description = "Play / pause" })
