-- =============================================================================
--  conf/windowrules.lua — per-application window behaviour
-- =============================================================================
--  Helper: float + center + size for a class regex. Add a line per app.
-- =============================================================================

local function floating(name, class, size)
    hl.window_rule({ name = name, match = { class = class }, float = true, center = true, size = size })
end

-- Floating utilities ------------------------------------------------------------
floating("floating-tui",     "^(floating-tui)$",                  "900 620")  -- nmtui, bluetui… (TERMINAL_FLOAT)
floating("pavucontrol",      ".*org.pulseaudio.pavucontrol.*",    "760 600")
floating("blueman",          "^(blueman-manager)$",               "800 600")
floating("nm-editor",        "^(nm-connection-editor)$",          "800 700")
floating("nwg-look",         "^(nwg-look)$",                      "800 600")
floating("nwg-displays",     "^(nwg-displays)$",                  "1000 650")
floating("calculator",       "^(org.gnome.Calculator)$",          "420 640")
floating("missioncenter",    "^(io.missioncenter.MissionCenter)$", "1000 650")
floating("satty",            "^(com.gabm.satty)$",                "1200 800")
floating("share-picker",     "^(hyprland-share-picker)$",         "600 400")
floating("hypr-settings",    "^(dev.inkpaw.Settings)$",      "1060 720")  -- settings window
floating("hypr-welcome",     "^(dev.inkpaw.Welcome)$",       "1100 720")  -- first-boot welcome

-- File / folder pickers ----------------------------------------------------------
hl.window_rule({
    name  = "portal-gtk",
    match = { class = "^(xdg-desktop-portal-gtk)$" },
    float = true,
    size  = "900 620",
})

-- Picture-in-Picture: floating, pinned, never steals focus -------------------------
hl.window_rule({
    name  = "pip",
    match = { title = [[^([Pp]icture[-\s]?[Ii]n[-\s]?[Pp]icture)(.*)$]] },
    float = true,
    pin   = true,
    focus_on_activate = false,
    no_initial_focus  = true,
    suppress_event    = "activate",
})

-- Ignore maximize requests from apps (kitty re-opening maximized…) -------------------
hl.window_rule({
    name  = "suppress-maximize",
    match = { class = ".*" },
    suppress_event = "maximize",
})

-- Fix XWayland drag & drop ghosts ---------------------------------------------------
hl.window_rule({
    name  = "fix-xwayland-drags",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})

-- AI assistant: a tall window docked on one side (AI_SIDE, AI_WIDTH). aichat.py
-- re-sends this rule at each opening with the exact geometry of the tiled
-- area (hyprctl eval) and widens the outer gap of the workspace, so tiled
-- windows move aside; the values below are only the first-guess fallback. ----
do
    local S   = require("lib.settings")
    local gap = S.num("GAPS_OUT", 12)
    local bar = S.num("BAR_MARGIN", 6) + 41 + gap          -- the bar + its margin + a gap
    local top, bottom = bar, gap
    if S.str("BAR_POSITION", "top") == "bottom" then top, bottom = gap, bar end
    local x = S.str("AI_SIDE", "right") == "left" and tostring(gap)
              or string.format("(monitor_w-window_w-%d)", gap)
    hl.window_rule({
        name  = "aichat",
        match = { class = "^(dev.inkpaw.AIChat)$" },
        float = true,
        size  = string.format("%d (monitor_h-%d)", S.num("AI_WIDTH", 420), top + bottom),
        move  = string.format("%s %d", x, top),
        opacity = "1.0 override 1.0 override",
    })
end

-- Settings window: always fully opaque (readability over the blur) -------------------
hl.window_rule({
    name  = "hypr-settings-opaque",
    match = { class = "^(dev.inkpaw.(Settings|Welcome))$" },
    opacity = "1.0 override 1.0 override",
})
