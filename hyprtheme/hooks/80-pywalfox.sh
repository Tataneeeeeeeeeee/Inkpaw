#!/usr/bin/env bash
# =============================================================================
#  hooks/80-pywalfox.sh — recolor Firefox (pywalfox) with the new palette
# =============================================================================
#  The palette is written to ~/.cache/wal/colors.json by templates/pywal.json.
#  Needs the pywalfox native host ("pywalfox install") and the Pywalfox Firefox
#  extension; silently does nothing otherwise. Delete / chmod -x to skip.
# =============================================================================
. "${XDG_CONFIG_HOME:-$HOME/.config}/hypr/scripts/lib.sh"

have pywalfox || exit 0
pywalfox update
