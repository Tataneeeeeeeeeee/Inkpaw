-- =============================================================================
--  conf/autostart.lua — services started once when Hyprland starts
-- =============================================================================
--  One entry per service. Set `enabled = false` (or delete the line) to skip
--  one. `host = true` marks services that touch the host session (systemd env,
--  portals, polkit, idle/suspend): they are skipped in the ./test.sh nested
--  session so the test never interferes with your real desktop.
-- =============================================================================
local S  = require("lib.settings")
local sc = S.script

local services = {
    -- Session plumbing ----------------------------------------------------------
    -- XDG_CONFIG_HOME is exported too when set (SDDM "inkpaw" session), so
    -- D-Bus-activated apps (swaync, portals…) read the same config as the session.
    { name = "systemd-env", host = true,
      cmd = "dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP HYPRLAND_INSTANCE_SIGNATURE"
            .. (os.getenv("XDG_CONFIG_HOME") and " XDG_CONFIG_HOME" or "") },
    { name = "portals",     host = true,
      cmd = "systemctl --user restart xdg-desktop-portal-hyprland xdg-desktop-portal" },
    { name = "polkit",      host = true, cmd = "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1" },
    { name = "cursor",      cmd = "hyprctl setcursor " .. S.str("CURSOR_THEME", "Adwaita") .. " " .. S.str("CURSOR_SIZE", "24") },

    -- Desktop ---------------------------------------------------------------------
    { name = "wallpaper-daemon", cmd = sc("wallpaper-daemon.sh") },
    { name = "theme-restore",    cmd = S.paths.theme .. "/theme.sh restore" },   -- wallpaper + palette
    { name = "apps-config",      cmd = sc("apps-config.sh") },                    -- kitty settings file
    { name = "waybar",           cmd = sc("waybar.sh") .. " start" },
    -- explicit paths: if swaync were D-Bus-activated it would read ~/.config instead
    { name = "notifications",    cmd = sc("notifications.sh") .. " start" },
    { name = "osd",              cmd = sc("osd.sh") .. " server" },               -- picks the skin style
    -- the cat peeking from the bottom of the screen (only when DESKTOP_PET=true)
    { name = "deskpet",          cmd = sc("deskpet.sh") .. " start" },
    -- quick panel kept in memory (hidden) so the bar buttons open it instantly
    { name = "quickpanel",       cmd = sc("quickpanel.sh") .. " --daemon" },
    -- encre menus kept in memory too (power, cheat sheet, themes, wallpapers)
    { name = "resident-menus",   cmd = sc("resident.sh") .. " all --daemon" },
    -- 4-step welcome window, shown once (until "Ne plus afficher" is ticked)
    { name = "welcome",          cmd = sc("welcome.sh") .. " --first" },

    -- Launcher backend (Elephant) + Walker service for instant opening -------------
    { name = "elephant",         cmd = "elephant" },
    { name = "walker-service",   cmd = "walker --gapplication-service" },

    -- Idle management (switches AC / battery timeouts automatically) ----------------
    { name = "idle",             host = true, cmd = sc("idle.sh") .. " watch" },

    -- Low-battery notifications (laptop + mouse / headset…)
    { name = "battery-alert",    cmd = sc("battery-alert.sh") .. " watch" },
}

-- On exit, drop XDG_CONFIG_HOME from the systemd/D-Bus activation env so a
-- following non-Inkpaw session never inherits it.
hl.on("hyprland.shutdown", function()
    if os.getenv("XDG_CONFIG_HOME") and not S.test_mode then
        os.execute("systemctl --user unset-environment XDG_CONFIG_HOME")
    end
end)

hl.on("hyprland.start", function()
    for _, s in ipairs(services) do
        if s.enabled ~= false and not (S.test_mode and s.host) then
            hl.exec_cmd(s.cmd)
        end
    end
end)
