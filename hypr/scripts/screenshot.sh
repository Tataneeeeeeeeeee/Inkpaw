#!/usr/bin/env bash
# =============================================================================
#  screenshot.sh — hyprshot capture, satty annotation, tesseract OCR
# =============================================================================
#  Usage: screenshot.sh area | window | screen      save + copy instantly
#         screenshot.sh area-edit | screen-edit     capture then annotate (satty)
#         screenshot.sh ocr                         area → text in clipboard
#         screenshot.sh menu                        rofi menu with all actions
#  Folder: SCREENSHOT_DIR (settings.conf)
#  Skin: when rofi/skins/$UI_SKIN/tokens.rasi exists (skin "encre"), the
#  selection is drawn in the skin colors (mockup Mew-Screenshot: outside
#  dimmed with ink, 3px ink outline, clear inside, mono-font dimensions):
#  scripts/skin-bin/ goes first in PATH so hyprshot's own slurp calls get
#  them too (see skin-bin/slurp). Colors come from the generated palette.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"
. "$SCRIPTS/rofi-theme.sh"

skin_slurp() {
    local tokens="$CFG/rofi/skins/${UI_SKIN:-default}/tokens.rasi" ink shadow ochre font
    [ -f "$tokens" ] && [ -x "$SCRIPTS/skin-bin/slurp" ] || return 0
    ink=$(rofi_token ink '#2a2420'); shadow=$(rofi_token ink-shadow "$ink")
    ochre=$(rofi_token ochre '#d9a12e'); font=$(rofi_token mono-family 'monospace')
    # 8c = 55 % (dimmed outside), 00 = clear selection, 40 = window boxes (-r)
    SLURP_SKIN_ARGS=$(printf '%s\n' -b "${shadow:0:7}8c" -c "${ink:0:7}ff" -s "#00000000" \
                                    -B "${ochre:0:7}40" -w 3 -F "$font")
    export SLURP_SKIN_ARGS PATH="$SCRIPTS/skin-bin:$PATH"
}
skin_slurp

dir="${SCREENSHOT_DIR:-$HOME/Pictures/Screenshots}"
mkdir -p "$dir"
name="screenshot_$(date +%Y-%m-%d_%H-%M-%S).png"

capture() {   # $1 = hyprshot mode (region|window|output)
    hyprshot -m "$1" -o "$dir" -f "$name"
}

edit() {      # $1 = hyprshot mode; pipes the raw image into satty
    hyprshot -m "$1" --raw | satty --filename - \
        --output-filename "$dir/$name" --early-exit --copy-command wl-copy
}

ocr() {
    have tesseract || { notify "OCR" "tesseract is not installed"; exit 1; }
    local text
    text=$(grim -g "$(slurp)" - | tesseract - - -l "${OCR_LANG:-eng}" 2>/dev/null)
    [ -n "$text" ] && printf '%s' "$text" | wl-copy && notify "OCR" "Text copied to clipboard"
}

menu() {
    local choice
    choice=$(printf '%s\n' \
        "󰩭  Area" "󰖯  Window" "󰍹  Screen" \
        "󰏫  Area → annotate" "󰏫  Screen → annotate" "󰊄  Area → text (OCR)" \
        "󰉋  Open screenshot folder" | rofi_menu "Screenshot")
    sleep 0.2   # let rofi close before capturing
    case "$choice" in
        *"Area → annotate"*)   edit region ;;
        *"Screen → annotate"*) edit output ;;
        *"OCR"*)               ocr ;;
        *Area*)                capture region ;;
        *Window*)              capture window ;;
        *Screen*)              capture output ;;
        *folder*)              xdg-open "$dir" ;;
    esac
}

case "${1:-menu}" in
    area)        capture region ;;
    window)      capture window ;;
    screen)      capture output ;;
    area-edit)   edit region ;;
    screen-edit) edit output ;;
    ocr)         ocr ;;
    menu)        menu ;;
    *) echo "usage: $0 area|window|screen|area-edit|screen-edit|ocr|menu" >&2; exit 1 ;;
esac
