-- =============================================================================
--  conf/animations/fast.lua — short, snappy animations
-- =============================================================================
hl.curve("snap", { type = "bezier", points = { {0.2, 0.9}, {0.1, 1} } })

hl.animation({ leaf = "global",           enabled = true, speed = 4, bezier = "snap" })
hl.animation({ leaf = "windows",          enabled = true, speed = 2, bezier = "snap", style = "popin 85%" })
hl.animation({ leaf = "layers",           enabled = true, speed = 2, bezier = "snap", style = "fade" })
hl.animation({ leaf = "workspaces",       enabled = true, speed = 3, bezier = "snap", style = "slide" })
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 2, bezier = "snap", style = "slidevert" })
