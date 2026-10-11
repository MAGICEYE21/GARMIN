#!/bin/bash
# ./install.sh           create .venv and install dependencies
# ./install.sh launchd   install/reload the 07:00 + 21:00 sync job and the dashboard
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")" && pwd)"
LOGS="$HOME/Library/Logs/garmin-health"
AGENTS="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"

install_venv() {
    PY=""
    for c in python3.13 python3.12 python3; do
        if command -v "$c" >/dev/null 2>&1 &&
            "$c" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then
            PY="$(command -v "$c")"; break
        fi
    done
    if [ -z "$PY" ]; then
        echo "Python 3.12+ is required (python-garminconnect needs it): brew install python@3.13" >&2
        exit 1
    fi
    echo "Using $PY"
    "$PY" -m venv "$PROJECT/.venv"
    "$PROJECT/.venv/bin/pip" install --quiet --upgrade pip
    "$PROJECT/.venv/bin/pip" install --quiet -r "$PROJECT/requirements.txt"
    echo
    echo "Installed. Next: bin/garmin-health login"
}

install_launchd() {
    [ -x "$PROJECT/.venv/bin/python" ] || { echo "Run ./install.sh first." >&2; exit 1; }
    mkdir -p "$LOGS" "$AGENTS"
    chmod 700 "$LOGS"
    for name in sync web; do
        label="com.garmin-health.$name"
        dest="$AGENTS/$label.plist"
        sed -e "s|__PROJECT__|$PROJECT|g" -e "s|__LOGS__|$LOGS|g" \
            "$PROJECT/launchd/$label.plist" > "$dest"
        plutil -lint "$dest" >/dev/null
        launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
        launchctl bootstrap "$DOMAIN" "$dest"
        echo "Loaded $label"
    done
    echo
    echo "Sync runs at 07:00 and 21:00. Logs: $LOGS"
    echo "Dashboard: http://127.0.0.1:8765/"
    echo "Run a sync now with: launchctl kickstart $DOMAIN/com.garmin-health.sync"
}

case "${1:-}" in
    "") install_venv ;;
    launchd) install_launchd ;;
    *) echo "usage: $0 [launchd]" >&2; exit 2 ;;
esac
