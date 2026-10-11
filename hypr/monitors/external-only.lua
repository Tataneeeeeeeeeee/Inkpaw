-- =============================================================================
--  monitors/external-only.lua — laptop panel disabled (clamshell / docked)
-- =============================================================================
local m = require("monitors.common")

hl.monitor({ output = m.external, mode = "preferred", position = "0x0", scale = 1 })
hl.monitor({ output = m.laptop,   disabled = true })
m.fallback()
