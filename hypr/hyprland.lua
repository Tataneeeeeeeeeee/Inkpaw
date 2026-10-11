-- =============================================================================
--  hyprland.lua — entry point. ONLY require() lines live here.
--  Comment a line to disable a module. Values live in settings.conf.
-- =============================================================================

-- Core -----------------------------------------------------------------------
require("conf.env")             -- environment variables
require("conf.monitors")        -- monitor profile (monitors/*.lua)
require("conf.input")           -- keyboard, mouse, touchpad
require("conf.gestures")        -- touchpad gestures

-- Appearance -----------------------------------------------------------------
require("conf.look-and-feel")   -- gaps, borders, rounding, blur, shadows
require("conf.animations")      -- animation preset (conf/animations/*.lua)
require("conf.layouts")         -- dwindle / master options
require("conf.misc")            -- misc behaviour

-- Rules ----------------------------------------------------------------------
require("conf.windowrules")     -- floating apps, PiP, dialogs
require("conf.layerrules")      -- blur behind bar / launcher / panels
require("conf.workspaces")      -- workspace rules & scratchpad

-- Keybindings ----------------------------------------------------------------
require("conf.keybinds.apps")        -- launch applications
require("conf.keybinds.windows")     -- focus, move, resize, float, group
require("conf.keybinds.workspaces")  -- switch / move to workspaces, scratchpad
require("conf.keybinds.system")      -- launcher, menus, theme, bar, lock, reload
require("conf.keybinds.screenshots") -- capture, annotate, OCR
require("conf.keybinds.media")       -- volume, brightness, players (with OSD)
require("conf.keybinds.switches")    -- laptop lid

-- Session --------------------------------------------------------------------
require("conf.autostart")       -- daemons started once at login

-- Personal overrides (optional, loaded last, not tracked) ---------------------
require("conf.custom")
