-- =============================================================================
--  conf/monitors.lua — loads the active monitor profile
-- =============================================================================
--  The profile name comes from MONITOR_PROFILE (settings.conf), overridden by
--  the monitor menu (SUPER+SHIFT+M), which saves it in the state toggles file.
--  Profiles live in hypr/monitors/<name>.lua.
-- =============================================================================
local S = require("lib.settings")

local profile = S.str("MONITOR_PROFILE", "auto")

-- In the nested test session the real outputs don't exist: always use "auto".
if S.test_mode then profile = "auto" end

local ok, err = pcall(require, "monitors." .. profile)
if not ok then
    print("[monitors] profile '" .. profile .. "' failed (" .. tostring(err) .. "), using auto")
    require("monitors.auto")
end
