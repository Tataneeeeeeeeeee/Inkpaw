-- =============================================================================
--  conf/look-and-feel.lua — gaps, borders, rounding, opacity, blur, shadows
-- =============================================================================
--  Numbers come from settings.conf; colors from the generated theme.
--  GAMEMODE (toggled with SUPER+ALT+G) strips every effect for performance.
-- =============================================================================
local S = require("lib.settings")
local C = require("lib.colors")

local game = S.bool("GAMEMODE", false)
-- "ink" border / "hard" shadow: the hand-drawn look of the encre skin
local ink  = S.str("BORDER_STYLE", "gradient") == "ink"
local hard = S.str("SHADOW_STYLE", "soft") == "hard"

local active_border = ink and C.rgba("on_surface", "ff") or
    -- 3-accent gradient on the focused window (rotates if BORDER_ANIMATE)
    { colors = { C.rgba("a1", "ff"), C.rgba("a3", "ff"), C.rgba("a5", "ff") },
      angle = S.num("BORDER_ANGLE", 45) }

hl.config({
    general = {
        gaps_in     = game and 0 or S.num("GAPS_IN", 10),
        gaps_out    = game and 0 or S.num("GAPS_OUT", 20),
        border_size = game and 1 or S.num("BORDER_SIZE", 2),
        col = {
            active_border   = active_border,
            inactive_border = ink and C.rgba("on_surface", "99") or C.rgba("outline_variant", "40"),
        },
        resize_on_border = true,
        allow_tearing    = false,
        layout           = S.str("LAYOUT", "dwindle"),
    },

    decoration = {
        rounding           = game and 0 or S.num("ROUNDING", 10),
        rounding_power     = 2,
        active_opacity     = game and 1.0 or S.num("ACTIVE_OPACITY", 1.0),
        inactive_opacity   = game and 1.0 or S.num("INACTIVE_OPACITY", 0.9),
        fullscreen_opacity = 1.0,

        -- soft = blurred drop shadow; hard = solid ink block offset down-right
        shadow = {
            enabled        = (not game) and S.bool("SHADOW", true),
            sharp          = hard,
            range          = hard and 1 or 28,
            render_power   = hard and 1 or 3,
            offset         = hard and "5 5" or "0 6",
            color          = hard and C.rgba("shadow", "ff") or C.rgba("shadow", "45"),
            color_inactive = hard and C.rgba("shadow", "99") or C.rgba("shadow", "20"),
        },

        blur = {
            enabled           = (not game) and S.bool("BLUR", true),
            size              = S.num("BLUR_SIZE", 4),
            passes            = S.num("BLUR_PASSES", 4),
            new_optimizations = true,
            ignore_opacity    = true,
            xray              = false,
            noise             = 0.012,
            contrast          = 0.9,
            brightness        = 0.85,
            vibrancy          = 0.18,
        },
    },

    misc = {
        background_color = C.rgba("surface", "ff"),
    },
})
