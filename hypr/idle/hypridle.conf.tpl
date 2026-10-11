# =============================================================================
#  hypridle.conf.tpl — rendered by scripts/idle.sh (do not point hypridle here)
# =============================================================================
#  @PLACEHOLDERS@ are replaced with IDLE_AC_* or IDLE_BAT_* from settings.conf.
#  A listener whose timeout is 0 is dropped.
# =============================================================================

general {
    lock_cmd = @LOCK_CMD@                        # single-instance hyprlock
    before_sleep_cmd = loginctl lock-session     # lock before suspend
    after_sleep_cmd = hyprctl dispatch 'hl.dsp.dpms({ action = "enable" })'
}

# Dim the backlight
listener {
    timeout = @DIM@
    on-timeout = brightnessctl -s set 10
    on-resume = brightnessctl -r
}

# Lock the session
listener {
    timeout = @LOCK@
    on-timeout = loginctl lock-session
}

# Screens off
listener {
    timeout = @DPMS@
    on-timeout = hyprctl dispatch 'hl.dsp.dpms({ action = "disable" })'
    on-resume = hyprctl dispatch 'hl.dsp.dpms({ action = "enable" })' && brightnessctl -r
}

# Suspend
listener {
    timeout = @SUSPEND@
    on-timeout = systemctl suspend
}
