-- =============================================================================
--  conf/animations.lua — loads an animation preset from conf/animations/
-- =============================================================================
--  ANIMATION_PRESET (settings.conf) picks the file. ANIMATIONS=false or
--  GAMEMODE=true disable animations entirely (toggle: SUPER+SHIFT+A).
-- =============================================================================
local S = require("lib.settings")

local enabled = S.bool("ANIMATIONS", true) and not S.bool("GAMEMODE", false)
hl.config({ animations = { enabled = enabled } })

if enabled then
    local preset = S.str("ANIMATION_PRESET", "md3")
    local ok, err = pcall(require, "conf.animations." .. preset)
    if not ok then
        print("[animations] preset '" .. preset .. "' failed: " .. tostring(err))
        require("conf.animations.md3")
    end
end
