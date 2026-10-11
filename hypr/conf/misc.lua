-- =============================================================================
--  conf/misc.lua — miscellaneous behaviour
-- =============================================================================
hl.config({
    misc = {
        disable_hyprland_logo      = true,
        disable_splash_rendering   = true,
        force_default_wallpaper    = 0,
        initial_workspace_tracking = 1,
        -- 2 = a window opened over a fullscreen one un-fullscreens it and tiles
        -- next to it (from your custom.lua)
        on_focus_under_fullscreen  = 2,
        allow_session_lock_restore = true,
    },
})
