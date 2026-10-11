-- =============================================================================
--  conf/env.lua — environment variables
-- =============================================================================
local S = require("lib.settings")
local HOME = S.paths.home

-- PATH: user binaries ---------------------------------------------------------
hl.env("PATH", HOME .. "/.local/bin:" .. HOME .. "/.cargo/bin:" .. (os.getenv("PATH") or ""))

-- Wayland session -------------------------------------------------------------
hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
hl.env("XDG_SESSION_TYPE", "wayland")
hl.env("XDG_SESSION_DESKTOP", "Hyprland")
hl.env("DESKTOP_SESSION", "Hyprland")

-- Toolkits --------------------------------------------------------------------
hl.env("GDK_BACKEND", "wayland,x11,*")
hl.env("GDK_SCALE", "1")
hl.env("QT_QPA_PLATFORM", "wayland;xcb")
hl.env("QT_QPA_PLATFORMTHEME", "qt6ct")
hl.env("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")
hl.env("CLUTTER_BACKEND", "wayland")
hl.env("SDL_VIDEODRIVER", "wayland")

-- Electron / browsers -----------------------------------------------------------
hl.env("OZONE_PLATFORM", "wayland")
hl.env("ELECTRON_OZONE_PLATFORM_HINT", "wayland")
hl.env("MOZ_ENABLE_WAYLAND", "1")

-- Fonts: the system config + hyprtheme/fonts (bundled OFL fonts of the skins)
hl.env("FONTCONFIG_FILE", S.paths.theme .. "/fonts/fonts.conf")

-- Cursor ----------------------------------------------------------------------
hl.env("XCURSOR_THEME", S.str("CURSOR_THEME", "Adwaita"))
hl.env("XCURSOR_SIZE", S.str("CURSOR_SIZE", "24"))
hl.env("HYPRCURSOR_SIZE", S.str("CURSOR_SIZE", "24"))

-- XWayland: no blurry scaling
hl.config({ xwayland = { force_zero_scaling = true } })
