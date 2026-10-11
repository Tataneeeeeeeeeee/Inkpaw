#!/usr/bin/env bash
# =============================================================================
#  hooks/40-kitty.sh — kitty re-reads its config (picks up inkpaw-theme.conf)
# =============================================================================
#  Run by theme.sh after the templates are rendered. Delete / chmod -x to skip.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

pkill -USR1 -x kitty || true
