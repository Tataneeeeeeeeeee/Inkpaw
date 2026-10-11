-- =============================================================================
--  monitors/common.lua — shared helpers for monitor profiles
-- =============================================================================
local S = require("lib.settings")

local M = {
    laptop   = S.str("MONITOR_LAPTOP", "eDP-1"),
    external = S.str("MONITOR_EXTERNAL", "HDMI-A-1"),
    side     = S.str("MONITOR_EXTERNAL_SIDE", "right"),
}

-- Catch-all rule: any other screen that gets plugged in uses its preferred mode
function M.fallback()
    hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })
end

return M
