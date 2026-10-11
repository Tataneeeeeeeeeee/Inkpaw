#!/usr/bin/env bash
# =============================================================================
#  notif-log.sh — keep a history of notifications (for the quick panel)
# =============================================================================
#  Run by swaync for every notification received ("scripts" → "history" in
#  swaync/config.json). swaync passes the notification as SWAYNC_* variables.
#  History: ~/.local/state/inkpaw/notifications.jsonl (last 200).
#  Usage: notif-log.sh            (called by swaync)
#         notif-log.sh clear      empty the history
#         notif-log.sh remove ID  forget one notification
# =============================================================================
. "$(dirname "$(readlink -f "$0")")/lib.sh"

LOG="$STATE/notifications.jsonl"

case "${1:-}" in
    clear)  : >"$LOG"; exit 0 ;;
    remove) [ -f "$LOG" ] && jq -c --arg id "$2" 'select(.id != $id)' "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"; exit 0 ;;
esac

# Debug aid: NOTIF_LOG_DEBUG=1 dumps the environment swaync gave us
[ -n "${NOTIF_LOG_DEBUG:-}" ] && env | grep '^SWAYNC_' >"$CACHE/notif-env.txt"

jq -cn \
    --arg id "${SWAYNC_ID:-$(date +%s%N)}" \
    --arg app "${SWAYNC_APP_NAME:-}" \
    --arg summary "${SWAYNC_SUMMARY:-}" \
    --arg body "${SWAYNC_BODY:-}" \
    --arg urgency "${SWAYNC_URGENCY:-Normal}" \
    --arg entry "${SWAYNC_DESKTOP_ENTRY:-}" \
    --arg time "$(date +%s)" \
    '{id: $id, app: $app, summary: $summary, body: $body, urgency: $urgency, entry: $entry, time: ($time | tonumber)}' \
    >>"$LOG"

# keep the file small
if [ "$(wc -l <"$LOG")" -gt 200 ]; then
    tail -n 200 "$LOG" >"$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
