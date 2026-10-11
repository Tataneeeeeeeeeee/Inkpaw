-- =============================================================================
--  monitors/extended.lua — laptop + external side by side
-- =============================================================================
--  Side is MONITOR_EXTERNAL_SIDE in settings.conf (left/right/above/below).
-- =============================================================================
local m = require("monitors.common")
local side = ({ right = "auto-right", left = "auto-left", above = "auto-up", below = "auto-down" })[m.side] or "auto-right"

hl.monitor({ output = m.laptop,   mode = "preferred", position = "0x0", scale = 1 })
hl.monitor({ output = m.external, mode = "preferred", position = side,  scale = 1 })
m.fallback()
