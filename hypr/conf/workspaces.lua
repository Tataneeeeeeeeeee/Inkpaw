-- =============================================================================
--  conf/workspaces.lua — workspace rules
-- =============================================================================

-- Scratchpad (SUPER+S): bigger outer gaps so it looks like a floating sheet
hl.workspace_rule({ workspace = "special:scratchpad", gaps_out = 60 })

-- Examples (uncomment to pin workspaces to screens):
-- local S = require("lib.settings")
-- for i = 1, 5  do hl.workspace_rule({ workspace = tostring(i), monitor = S.str("MONITOR_EXTERNAL") }) end
-- for i = 6, 10 do hl.workspace_rule({ workspace = tostring(i), monitor = S.str("MONITOR_LAPTOP") }) end
