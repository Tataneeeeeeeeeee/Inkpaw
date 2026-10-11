-- =============================================================================
--  conf/keybinds/workspaces.lua — workspaces & scratchpad
-- =============================================================================
--  With an AZERTY layout (KB_LAYOUT="fr") the number row keys are used
--  unshifted: & é " ' ( - è _ ç à
-- =============================================================================
local S   = require("lib.settings")
local MOD = S.str("MOD", "SUPER")

local azerty = S.str("KB_LAYOUT", "us"):match("^fr") ~= nil and S.str("KB_VARIANT", "") ~= "us"
local fr_keys = { "ampersand", "eacute", "quotedbl", "apostrophe", "parenleft",
                  "minus", "egrave", "underscore", "ccedilla", "agrave" }

for i = 1, 10 do
    local key = azerty and fr_keys[i] or tostring(i % 10)
    hl.bind(MOD .. " + " .. key,         hl.dsp.focus({ workspace = i }),       { description = "Focus workspace " .. i })
    hl.bind(MOD .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }), { description = "Move window to workspace " .. i })
end

-- Cycle through existing workspaces with the mouse wheel
hl.bind(MOD .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }), { description = "Next workspace" })
hl.bind(MOD .. " + mouse_up",   hl.dsp.focus({ workspace = "e-1" }), { description = "Previous workspace" })

-- Scratchpad -------------------------------------------------------------------
hl.bind(MOD .. " + S", hl.dsp.workspace.toggle_special("scratchpad"), { description = "Toggle scratchpad" })
hl.bind(MOD .. " + SHIFT + S", function()
    hl.dispatch(hl.dsp.window.float({ action = "toggle" }))
    hl.dispatch(hl.dsp.window.move({ workspace = "special:scratchpad" }))
end, { description = "Send window to scratchpad" })
