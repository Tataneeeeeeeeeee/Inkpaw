-- =============================================================================
--  conf/keybinds/switches.lua — hardware switches (laptop lid)
-- =============================================================================
--  Closing the lid with an external screen connected disables the laptop panel;
--  opening it restores the saved monitor profile. LID_SWITCH_HANDLING=false
--  disables this file's effect.
-- =============================================================================
local S = require("lib.settings")

if S.bool("LID_SWITCH_HANDLING", true) and not S.test_mode then
    local lid = S.script("lid.sh")
    hl.bind("switch:on:Lid Switch",  hl.dsp.exec_cmd(lid .. " close"), { locked = true, description = "Lid closed" })
    hl.bind("switch:off:Lid Switch", hl.dsp.exec_cmd(lid .. " open"),  { locked = true, description = "Lid opened" })
end
