#!/usr/bin/env bash
# =============================================================================
#  toggle-allfloat.sh — toggle floating for every window of the active workspace
# =============================================================================
ws=$(hyprctl activeworkspace -j | jq -r '.id')
hyprctl clients -j | jq -r --argjson ws "$ws" '.[] | select(.workspace.id == $ws) | .address' |
while read -r addr; do
    hyprctl dispatch "hl.dsp.window.float({ action = \"toggle\", window = \"address:$addr\" })" >/dev/null
done
