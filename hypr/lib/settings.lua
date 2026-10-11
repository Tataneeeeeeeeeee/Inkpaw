-- =============================================================================
--  lib/settings.lua — loads hypr/settings.conf (+ runtime toggles) into Lua
-- =============================================================================
--  Usage in any module:
--      local S = require("lib.settings")
--      S.str("TERMINAL")          --> "kitty"
--      S.num("GAPS_IN")           --> 10
--      S.bool("BLUR")             --> true
--      S.paths.scripts            --> ".../hypr/scripts"
--
--  Values come from (later wins):
--      1. hypr/settings.conf                       (your defaults)
--      2. $XDG_STATE_HOME/inkpaw/toggles.conf (written by toggle scripts)
-- =============================================================================

local HOME   = os.getenv("HOME")
local CONFIG = os.getenv("XDG_CONFIG_HOME") or (HOME .. "/.config")
local STATE  = (os.getenv("XDG_STATE_HOME") or (HOME .. "/.local/state")) .. "/inkpaw"

local M = {
    values = {},
    -- True when launched by ./test.sh (nested session): host-affecting
    -- services (portals, polkit, idle, gsettings…) are skipped.
    test_mode = (os.getenv("INKPAW_TEST") or "") ~= "",
    paths = {
        home    = HOME,
        config  = CONFIG,
        hypr    = CONFIG .. "/hypr",
        scripts = CONFIG .. "/hypr/scripts",
        theme   = CONFIG .. "/hyprtheme",
        state   = STATE,
    },
}

-- Expand $HOME / ${HOME} in a value
local function expand(v)
    v = v:gsub("%${HOME}", HOME)
    v = v:gsub("%$HOME", HOME)
    return v
end

-- Parse a KEY="value" file into M.values (missing file = no-op)
local function load(path)
    local f = io.open(path, "r")
    if not f then return end
    for line in f:lines() do
        local key, val = line:match('^%s*([%w_]+)%s*=%s*(.-)%s*$')
        if key and not line:match("^%s*#") then
            val = val:gsub("%s+#.*$", "")          -- trailing comment
            val = val:match('^"(.*)"$') or val:match("^'(.*)'$") or val
            M.values[key] = expand(val)
        end
    end
    f:close()
end

load(CONFIG .. "/hypr/settings.conf")
load(STATE .. "/toggles.conf")

-- Typed accessors ------------------------------------------------------------
function M.str(key, default)
    local v = M.values[key]
    if v == nil or v == "" then return default end
    return v
end

function M.num(key, default)
    return tonumber(M.values[key]) or default
end

function M.bool(key, default)
    local v = M.values[key]
    if v == nil then return default end
    return v == "true" or v == "1" or v == "yes" or v == "on"
end

-- Helper: absolute path of a script in hypr/scripts
function M.script(name)
    return M.paths.scripts .. "/" .. name
end

return M
