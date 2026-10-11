-- =============================================================================
--  monitors/laptop-only.lua — external screen disabled
-- =============================================================================
local m = require("monitors.common")

hl.monitor({ output = m.laptop,   mode = "preferred", position = "0x0", scale = 1 })
hl.monitor({ output = m.external, disabled = true })
m.fallback()
