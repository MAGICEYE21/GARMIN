#!/bin/bash
# ./uninstall.sh          stop and remove the launchd jobs (keeps your data)
# ./uninstall.sh --purge  also delete the database, tokens, logs, Keychain login and .venv
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")" && pwd)"
DOMAIN="gui/$(id -u)"

for label in com.garmin-health.sync com.garmin-health.web; do
    launchctl bootout "$DOMAIN/$label" 2>/dev/null && echo "Stopped $label" || true
    rm -f "$HOME/Library/LaunchAgents/$label.plist"
done

if [ "${1:-}" = "--purge" ]; then
    DATA="${GARMIN_HEALTH_HOME:-$HOME/Library/Application Support/garmin-health}"
    LOGS="$HOME/Library/Logs/garmin-health"
    echo "This permanently deletes:"
    echo "  $DATA   (health database, session tokens)"
    echo "  $LOGS"
    echo "  the 'garmin-health' Keychain items"
    echo "  $PROJECT/.venv"
    read -r -p "Type 'delete' to continue: " answer
    [ "$answer" = "delete" ] || { echo "Aborted."; exit 1; }
    if [ -x "$PROJECT/.venv/bin/python" ]; then
        (cd "$PROJECT" && .venv/bin/python -m garmin_health logout --forget) || true
    fi
    while security delete-generic-password -s garmin-health >/dev/null 2>&1; do :; done
    rm -rf "$DATA" "$LOGS" "$PROJECT/.venv"
    echo "Purged. You can now delete $PROJECT."
else
    echo "Jobs removed. Data kept; run '$0 --purge' to delete it too."
fi
