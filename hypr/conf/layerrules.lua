-- =============================================================================
--  conf/layerrules.lua — blur & animation tweaks for layer-shell surfaces
-- =============================================================================
--  ignore_alpha keeps blur off fully transparent pixels (rounded corners).
-- =============================================================================

local function blurred(name, namespace)
    hl.layer_rule({ name = name, match = { namespace = namespace }, blur = true, ignore_alpha = 0.3 })
end

blurred("waybar",        "^(waybar)$")
blurred("walker",        "^(walker)$")
blurred("spotlight",     "^(spotlight)$")
blurred("quickpanel",    "^(quickpanel)$")
blurred("rofi",          "^(rofi)$")
blurred("swaync-center", "^(swaync-control-center)$")
blurred("swaync-popups", "^(swaync-notification-window)$")
blurred("wlogout",       "^(logout_dialog)$")
blurred("swayosd",       "^(swayosd)$")
