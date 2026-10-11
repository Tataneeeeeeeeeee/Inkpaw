-- =============================================================================
--  conf/gestures.lua — touchpad gestures
-- =============================================================================

-- 3 fingers vertical: switch workspace
hl.gesture({ fingers = 3, direction = "vertical", action = "workspace" })

-- 3 fingers horizontal: scroll-move (scrolling layout)
hl.gesture({ fingers = 3, direction = "horizontal", action = "scroll_move", scale = 0.9 })

-- 4 fingers pinch out / in: fullscreen on / off
hl.gesture({ fingers = 4, direction = "pinchout", action = function()
    hl.dispatch(hl.dsp.window.fullscreen({ action = "set" }))
end })
hl.gesture({ fingers = 4, direction = "pinchin", action = function()
    hl.dispatch(hl.dsp.window.fullscreen({ action = "unset" }))
end })
