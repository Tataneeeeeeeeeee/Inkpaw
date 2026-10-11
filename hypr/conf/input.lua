-- =============================================================================
--  conf/input.lua — keyboard, mouse and touchpad
-- =============================================================================
local S = require("lib.settings")

hl.config({
    input = {
        kb_layout    = S.str("KB_LAYOUT", "us"),
        kb_variant   = S.str("KB_VARIANT", ""),
        kb_model     = "",
        kb_options   = S.str("KB_OPTIONS", ""),
        kb_rules     = "",
        follow_mouse = 1,
        sensitivity  = S.num("MOUSE_SENSITIVITY", 0),   -- -1.0 .. 1.0
        touchpad     = {
            natural_scroll = S.bool("NATURAL_SCROLL", true),
        },
    },
})
