#!/bin/bash
# open-dashboard.sh — what the Metis app-menu shortcut runs on desktop Linux.
#
# Starts the dashboard in the background if nothing is serving, waits until it
# answers, then opens it in the browser. Safe to click twice: run-dashboard.sh is
# a singleton, and a dashboard that is already up is simply opened.
#
# ENV  METIS_PORT  dashboard port (default 8080)

set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${METIS_PORT:-8080}"
URL="http://127.0.0.1:$PORT/"
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/metis/dashboard.log"

healthy() { curl -sf -m 3 "${URL}health" >/dev/null 2>&1; }

open_url() {
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$URL" >/dev/null 2>&1 &
    else
        echo "Metis is running: $URL"
    fi
}

tell() {
    # A shortcut has no terminal: say it where the user will see it.
    command -v notify-send >/dev/null 2>&1 && notify-send "Metis" "$1"
    echo "$1"
}

if healthy; then
    open_url
    exit 0
fi

mkdir -p "$(dirname "$LOG")"
# The launcher supervises uvicorn and must outlive this script and its terminal.
setsid nohup bash "$APP_DIR/run-dashboard.sh" </dev/null >>"$LOG" 2>&1 &
tell "Starting Metis — the dashboard opens in a moment."

for _ in $(seq 1 60); do
    if healthy; then
        open_url
        exit 0
    fi
    sleep 1
done

tell "Metis did not start within a minute. Details: $LOG"
exit 1
