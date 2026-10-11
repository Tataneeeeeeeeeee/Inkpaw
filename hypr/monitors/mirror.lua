-- =============================================================================
--  monitors/mirror.lua — external screen mirrors the laptop (presentations)
-- =============================================================================
local m = require("monitors.common")

hl.monitor({ output = m.laptop,   mode = "preferred", position = "0x0", scale = 1 })
hl.monitor({ output = m.external, mode = "preferred", position = "auto", scale = 1, mirror = m.laptop })
m.fallback()
