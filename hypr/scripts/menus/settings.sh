#!/usr/bin/env bash
# =============================================================================
#  menus/settings.sh — settings menu (SUPER+CTRL+S, Waybar 󰒓 button)
# =============================================================================
#  Entirely driven by hypr/settings.schema: sections, options, value types and
#  what to re-apply after a change. Nothing is hard-coded here: add a line to
#  the schema to expose a new option.
#
#  Usage: settings.sh              main menu
#         settings.sh <Section>    open a section directly (e.g. "Bar")
#         settings.sh set KEY VAL  set + apply one value (scriptable)
#         settings.sh unset KEY    back to the settings.conf value
#         settings.sh reset PAGE   reset a whole page (Bar, Windows…)
#
#  Changed values go to ~/.local/state/inkpaw/toggles.conf (overriding
#  hypr/settings.conf); "Reset section" deletes them again.
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/../lib.sh"

SCHEMA="$HYPR_DIR/settings.schema"
CATALOG="$CFG/waybar/catalog.tsv"
export SCRIPTS THEME_DIR CFG

# --- schema ------------------------------------------------------------------------
# rows: section, key, type, choices, label, apply — separated by \x1f (unit
# separator: unlike TAB it is not whitespace, so empty fields are kept by read)
schema() {
    sed -e '/^[[:space:]]*#/d' -e '/^[[:space:]]*$/d' "$SCHEMA" |
    awk -F'|' '{ for (i = 1; i <= NF; i++) { gsub(/^[ \t]+|[ \t]+$/, "", $i) }
                 sub(/\/.*/, "", $1)        # "Bar/Layout" -> page "Bar" (groups are for the app)
                 print $1 "\037" $2 "\037" $3 "\037" $4 "\037" $5 "\037" $6 }'
}

reload_values() {   # re-read settings + overrides after a change
    # shellcheck disable=SC1091
    . "$HYPR_DIR/settings.conf"
    # shellcheck disable=SC1090
    [ -f "$TOGGLES" ] && . "$TOGGLES"
}

# Module / capsule labels
label_of() {   # <kind> <name>
    if [ "$1" = capsules ]; then
        case "$2" in session) echo "Session (launcher, workspaces…)";; time) echo "Time (clock)";;
                     status) echo "Status (sound, network…)";; system) echo "System (notifications, power…)";; *) echo "$2";; esac
    else
        awk -F'\t' -v n="$2" '$1 == n { print $3; exit }' "$CATALOG"
    fi
}
all_items() {  # <kind>
    if [ "$1" = capsules ]; then printf '%s\n' session time status system
    else awk -F'\t' '!/^#/ && NF == 3 { print $1 }' "$CATALOG"; fi
}

# Human readable value
show_value() {   # <type> <value>
    case "$1" in
        bool) is_true_value "$2" && echo "on" || echo "off" ;;
        action) echo "" ;;
        secret) echo "••••" ;;
        modules|capsules)
            [ -z "$2" ] && { echo "(empty)"; return; }
            local out="" n; for n in $2; do out+="${out:+, }$n"; done; echo "$out" ;;
        *) [ -z "$2" ] && echo "(default)" || echo "$2" ;;
    esac
}
is_true_value() { [[ "$1" == true || "$1" == 1 || "$1" == yes || "$1" == on ]]; }

# --- apply -------------------------------------------------------------------------
apply() {   # <apply> <key> <value>
    case "$1" in
        hypr)   hyprctl reload >/dev/null ;;
        bar)    "$SCRIPTS/waybar.sh" restart ;;
        theme)  THEME_NO_WALLPAPER=1 "$THEME_DIR/theme.sh" restore ;;
        mode)   "$THEME_DIR/theme.sh" mode "$3" ;;
        scheme) "$THEME_DIR/theme.sh" scheme "$3" ;;
        apps)   "$SCRIPTS/apps-config.sh" "$2" ;;
        skin)   "$THEME_DIR/skin.sh" apply "$3" ;;
        pet)    "$SCRIPTS/deskpet.sh" restart ;;
        *) ;;
    esac
}

set_value() {   # <key> <value> <apply>
    state_set "$1" "$2"
    reload_values
    apply "$3" "$1" "$2" >/dev/null 2>&1
}

reset_section() {   # <section>
    local keys k
    keys=$(schema | awk -F'\037' -v s="$1" '$1 == s && $3 != "action" { print $2 }')
    for k in $keys; do sed -i "/^${k}=/d" "$TOGGLES" 2>/dev/null; done
    reload_values
    # re-apply everything the section touches
    schema | awk -F'\037' -v s="$1" '$1 == s { print $6 }' | sort -u | while read -r a; do
        apply "$a" "" "" >/dev/null 2>&1
    done
    notify "Settings" "$1 reset to defaults"
}

# --- editors -----------------------------------------------------------------------
edit_choice() {   # <key> <choices> <label> <apply>
    local cur="${!1}" pick
    pick=$(tr ',' '\n' <<<"$2" | awk -v c="$cur" '{ print ($0 == c) ? $0 " ✓" : $0 }' |
           rofi_menu "$3" -no-custom)
    pick="${pick% ✓}"
    [ -n "$pick" ] && set_value "$1" "$pick" "$4"
}

edit_free() {   # <key> <type> <suggestions> <label> <apply>
    local cur="${!1}" sep="," pick
    [ "$2" = text ] && sep=";"
    if [ "$2" = app ]; then   # only suggest installed commands
        sug=$(tr ',' '\n' <<<"$3" | while read -r x; do command -v "${x%% *}" >/dev/null && echo "$x"; done | paste -sd,)
        set -- "$1" app "$sug" "$4" "$5"
    fi
    pick=$( { [ -n "$cur" ] && echo "$cur"; tr "$sep" '\n' <<<"$3"; } | awk 'NF && !seen[$0]++' |
            rofi_menu "$4 (type a value)" -mesg "Current: ${cur:-default}")
    [ -z "$pick" ] && return
    if [ "$2" = number ] && ! [[ "$pick" =~ ^-?[0-9]+([.][0-9]+)?$ ]]; then
        notify "Settings" "'$pick' is not a number"; return
    fi
    set_value "$1" "$pick" "$5"
}

edit_list() {   # <key> <kind> <label> <apply>
    local key="$1" kind="$2" label="$3" ap="$4"
    while true; do
        local -a cur=(${!key}) rows=() names=()
        local n
        rows+=("↩  Done"); names+=("@done")
        rows+=("⇡  Move an item earlier"); names+=("@up")
        rows+=("⇣  Move an item later"); names+=("@down")
        for n in "${cur[@]}"; do rows+=("✓  $(label_of "$kind" "$n")"); names+=("$n"); done
        while read -r n; do
            [[ " ${cur[*]} " == *" $n "* ]] && continue
            [ "$key" = BAR_EXTRAS ] && [ "$n" = extras ] && continue
            rows+=("     $(label_of "$kind" "$n")"); names+=("$n")
        done < <(all_items "$kind")

        local idx
        idx=$(printf '%s\n' "${rows[@]}" | rofi_menu "$label" -no-custom -format i \
              -mesg "✓ = shown, in this order · select to add / remove")
        [ -z "$idx" ] && return
        local pick="${names[$idx]}"
        case "$pick" in
            @done) return ;;
            @up|@down)
                [ ${#cur[@]} -lt 2 ] && continue
                local -a lbl=(); for n in "${cur[@]}"; do lbl+=("$(label_of "$kind" "$n")"); done
                local i; i=$(printf '%s\n' "${lbl[@]}" | rofi_menu "Move which?" -no-custom -format i)
                [ -z "$i" ] && continue
                local j; [ "$pick" = "@up" ] && j=$((i - 1)) || j=$((i + 1))
                if [ $j -ge 0 ] && [ $j -lt ${#cur[@]} ]; then
                    local t="${cur[$i]}"; cur[$i]="${cur[$j]}"; cur[$j]="$t"
                fi ;;
            *)
                if [[ " ${cur[*]} " == *" $pick "* ]]; then
                    local -a nxt=(); for n in "${cur[@]}"; do [ "$n" != "$pick" ] && nxt+=("$n"); done; cur=("${nxt[@]}")
                else
                    cur+=("$pick")
                fi ;;
        esac
        set_value "$key" "${cur[*]}" "$ap"
    done
}

# --- menus -------------------------------------------------------------------------
section_icon() {
    case "$1" in
        Bar) echo "󰍜" ;; Appearance) echo "󰏘" ;; Windows) echo "󰖯" ;;
        Displays) echo "󰍹" ;; System) echo "󰒓" ;; *) echo "•" ;;
    esac
}

section_menu() {   # <section>
    local sec="$1"
    while true; do
        reload_values
        local -a rows=() keys=() types=() choices=() labels=() applies=()
        rows+=("←  Back"); keys+=("@back"); types+=(""); choices+=(""); labels+=(""); applies+=("")
        local s k t c l a v
        while IFS=$'\037' read -r s k t c l a; do
            [ "$s" = "$sec" ] || continue
            if [ "$t" = action ]; then
                rows+=("$(printf '󰐊  %s' "$l")")
            else
                v="${!k-}"
                # pad by characters, not bytes (printf %-34s miscounts "·", "é"…)
                local pad=$(( 34 - ${#l} )); [ $pad -lt 1 ] && pad=1
                rows+=("$l$(printf '%*s' "$pad" '')$(show_value "$t" "$v")")
            fi
            keys+=("$k"); types+=("$t"); choices+=("$c"); labels+=("$l"); applies+=("$a")
        done < <(schema)
        rows+=("󰑓  Reset section to defaults"); keys+=("@reset"); types+=(""); choices+=(""); labels+=(""); applies+=("")

        local idx
        idx=$(printf '%s\n' "${rows[@]}" | rofi_menu "$sec" -no-custom -format i \
              -theme-str 'element-text { font: "monospace 11"; } window { width: 980px; }')
        [ -z "$idx" ] && exit 0
        k="${keys[$idx]}"; t="${types[$idx]}"; c="${choices[$idx]}"; l="${labels[$idx]}"; a="${applies[$idx]}"
        case "$k" in
            @back)  return ;;
            @reset) reset_section "$sec" ;;
            *)
                case "$t" in
                    action)   setsid -f bash -c "$k" >/dev/null 2>&1; exit 0 ;;
                    bool)     is_true_value "${!k-}" && set_value "$k" false "$a" || set_value "$k" true "$a" ;;
                    choice)   edit_choice "$k" "$c" "$l" "$a" ;;
                    number|text) edit_free "$k" "$t" "$c" "$l" "$a" ;;
                    app)      edit_free "$k" app "$c" "$l" "$a" ;;
                    secret)   v=$(rofi_menu "$l" -password -lines 0 -mesg "Saved apart (mode 600). Empty = remove." </dev/null)
                              set_secret "$k" "$v"; notify "Settings" "$l ${v:+saved}${v:-removed}" ;;
                    modules|capsules) edit_list "$k" "$t" "$l" "$a" ;;
                esac ;;
        esac
    done
}

main_menu() {
    while true; do
        local -a secs=() rows=()
        local s
        while read -r s; do secs+=("$s"); rows+=("$(section_icon "$s")  $s"); done \
            < <(schema | cut -d$'\037' -f1 | awk '!seen[$0]++')
        rows+=("󰑓  Reset ALL customizations")
        local idx
        idx=$(printf '%s\n' "${rows[@]}" | rofi_menu "Settings" -no-custom -format i)
        [ -z "$idx" ] && exit 0
        if [ "$idx" -ge "${#secs[@]}" ]; then
            : >"$TOGGLES"; reload_values
            hyprctl reload >/dev/null; "$SCRIPTS/waybar.sh" restart; THEME_NO_WALLPAPER=1 "$THEME_DIR/theme.sh" restore
            notify "Settings" "All customizations removed"
        else
            section_menu "${secs[$idx]}"
        fi
    done
}

SECRETS="$STATE/secrets.conf"
set_secret() {   # <key> <value>  (empty value = remove)
    umask 077; touch "$SECRETS"; chmod 600 "$SECRETS"
    sed -i "/^${1}=/d" "$SECRETS"
    [ -n "$2" ] && printf '%s="%s"\n' "$1" "${2//\"/}" >>"$SECRETS"
}

apply_of() { schema | awk -F'\037' -v k="$1" '$2 == k { print $6; exit }'; }

case "${1:-}" in
    set)   set_value "$2" "$3" "$(apply_of "$2")" ;;
    unset) sed -i "/^${2}=/d" "$TOGGLES" 2>/dev/null; reload_values; apply "$(apply_of "$2")" "$2" "${!2-}" >/dev/null 2>&1 ;;
    reset) reset_section "$2" ;;
    secret) set_secret "$2" "${3:-}" ;;
    "")  main_menu ;;
    *)   section_menu "$1" ;;
esac
