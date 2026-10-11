-- =============================================================================
--  conf/animations/smooth.lua — soft, physical animations (springs)
-- =============================================================================
--  Springs instead of fixed-duration curves: windows settle naturally, fast
--  interactions never feel laggy. Tweak `stiffness` (speed) and `dampening`
--  (bounce: lower = more bounce).
-- =============================================================================

-- Springs ---------------------------------------------------------------------
hl.curve("soft",  { type = "spring", mass = 1, stiffness = 180, dampening = 22 })   -- windows
hl.curve("snap",  { type = "spring", mass = 1, stiffness = 300, dampening = 30 })   -- layers / menus
hl.curve("glide", { type = "spring", mass = 1, stiffness = 140, dampening = 24 })   -- workspaces

-- Beziers (fades & borders) -----------------------------------------------------
hl.curve("easeOutQuint", { type = "bezier", points = { {0.23, 1}, {0.32, 1} } })
hl.curve("easeInOut",    { type = "bezier", points = { {0.65, 0.05}, {0.36, 1} } })
hl.curve("linear",       { type = "bezier", points = { {0, 0}, {1, 1} } })

-- Rules ---------------------------------------------------------------------------
hl.animation({ leaf = "global",           enabled = true, speed = 8,   bezier = "easeOutQuint" })
hl.animation({ leaf = "windows",          enabled = true, speed = 5,   spring = "soft" })
hl.animation({ leaf = "windowsIn",        enabled = true, speed = 4.5, spring = "soft",  style = "popin 92%" })
hl.animation({ leaf = "windowsOut",       enabled = true, speed = 2,   bezier = "easeInOut", style = "popin 92%" })
hl.animation({ leaf = "windowsMove",      enabled = true, speed = 5,   spring = "soft" })
hl.animation({ leaf = "border",           enabled = true, speed = 6,   bezier = "easeOutQuint" })

-- Rotating gradient border (HyDE-style). Costs a redraw per frame of the
-- focused window's border: set BORDER_ANIMATE="false" on battery if you prefer.
if require("lib.settings").bool("BORDER_ANIMATE", true) then
    hl.animation({ leaf = "borderangle", enabled = true, speed = 80, bezier = "linear", style = "loop" })
end
hl.animation({ leaf = "fade",             enabled = true, speed = 3,   bezier = "easeOutQuint" })
hl.animation({ leaf = "fadeOut",          enabled = true, speed = 2,   bezier = "easeInOut" })
hl.animation({ leaf = "layersIn",         enabled = true, speed = 4,   spring = "snap",  style = "popin 94%" })
hl.animation({ leaf = "layersOut",        enabled = true, speed = 2,   bezier = "easeInOut", style = "fade" })
hl.animation({ leaf = "fadeLayersIn",     enabled = true, speed = 2.5, bezier = "easeOutQuint" })
hl.animation({ leaf = "fadeLayersOut",    enabled = true, speed = 2,   bezier = "easeInOut" })
hl.animation({ leaf = "workspaces",       enabled = true, speed = 5,   spring = "glide", style = "slidefade 12%" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 5,   spring = "glide", style = "slidefadevert 20%" })
