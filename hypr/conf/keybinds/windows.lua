-- =============================================================================
--  conf/keybinds/windows.lua — focus, move, resize, float, fullscreen, groups
-- =============================================================================
local S   = require("lib.settings")
local MOD = S.str("MOD", "SUPER")
local exec = hl.dsp.exec_cmd

-- Close ------------------------------------------------------------------------
hl.bind(MOD .. " + Q",         hl.dsp.window.close(), { description = "Close active window" })
hl.bind(MOD .. " + SHIFT + Q", exec("hyprctl activewindow -j | jq -r .pid | xargs -r kill"),
        { description = "Kill active window process" })

-- State ------------------------------------------------------------------------
hl.bind(MOD .. " + F", hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }), { description = "Toggle fullscreen" })
hl.bind(MOD .. " + M", hl.dsp.window.fullscreen({ mode = "maximized",  action = "toggle" }), { description = "Toggle maximize" })
hl.bind(MOD .. " + T", hl.dsp.window.float({ action = "toggle" }), { description = "Toggle floating" })
hl.bind(MOD .. " + SHIFT + T", exec(S.script("toggle-allfloat.sh")), { description = "Toggle floating for all windows of workspace" })
hl.bind(MOD .. " + ALT + T", function()
    hl.dispatch(hl.dsp.window.float({ action = "toggle" }))
    hl.dispatch(hl.dsp.window.pin())
end, { description = "Toggle floating + pinned" })

-- Layout -----------------------------------------------------------------------
hl.bind(MOD .. " + J", hl.dsp.layout("togglesplit"), { description = "Toggle split" })
hl.bind(MOD .. " + K", hl.dsp.layout("swapsplit"),   { description = "Swap split" })
hl.bind(MOD .. " + G", hl.dsp.group.toggle(),        { description = "Toggle window group" })

-- Focus (arrows) ---------------------------------------------------------------
for _, dir in ipairs({ "left", "right", "up", "down" }) do
    hl.bind(MOD .. " + " .. dir,         hl.dsp.focus({ direction = dir }),       { description = "Focus " .. dir })
    hl.bind(MOD .. " + ALT + " .. dir,   hl.dsp.window.swap({ direction = dir }), { description = "Swap window " .. dir })
end

-- Resize (SHIFT + arrows) --------------------------------------------------------
local STEP = 100
hl.bind(MOD .. " + SHIFT + right", hl.dsp.window.resize({ x =  STEP, y = 0, relative = true }), { repeating = true, description = "Grow width" })
hl.bind(MOD .. " + SHIFT + left",  hl.dsp.window.resize({ x = -STEP, y = 0, relative = true }), { repeating = true, description = "Shrink width" })
hl.bind(MOD .. " + SHIFT + down",  hl.dsp.window.resize({ x = 0, y =  STEP, relative = true }), { repeating = true, description = "Grow height" })
hl.bind(MOD .. " + SHIFT + up",    hl.dsp.window.resize({ x = 0, y = -STEP, relative = true }), { repeating = true, description = "Shrink height" })

-- Mouse --------------------------------------------------------------------------
hl.bind(MOD .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true, description = "Move window (drag)" })
hl.bind(MOD .. " + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Resize window (drag)" })
