#!/bin/bash
# metis-boot.sh — make Metis CORRECT on this computer. Idempotent. Cheap. Safe to
# run every 5 minutes forever.
#
# WHY THIS EXISTS
#   The dashboard "kept crashing". It wasn't crashing — nothing was restarting it.
#   The supervision chain had a hole at every level:
#     · The systemd USER service (metis-dashboard.service) is enabled into
#       user@1000.service — which on this WSL box FAILS to start
#       ("Failed to spawn executor: Device or resource busy"). An enabled service
#       inside a dead manager never runs. Lingering was on; it made no difference.
#     · The Windows Startup shortcut fires ONCE at logon. When WSL restarts
#       mid-session (Docker, `wsl --shutdown`, Claude Desktop relaunching it),
#       nothing fires again.
#     · register-autostart.ps1 was written to add a 5-minute recovery heartbeat —
#       and was never actually registered. That was the missing safety net.
#
#   So supervision must live OUTSIDE WSL, in Windows Task Scheduler, because WSL
#   itself does not run when the computer starts and cannot resurrect itself.
#   This script is what that heartbeat calls.
#
# WHAT IT GUARANTEES, every 5 minutes and at every logon:
#   1. the CODE is current           (git fast-forward)
#   2. the MCP SERVER runs current code (reinstall if the venv copy is stale)
#   3. the DASHBOARD is actually SERVING (HTTP 200, not merely "a process exists")
#
# It never kills a healthy server — system/app-py/run.sh is a singleton that
# adopts one. The happy path is a ~50ms curl and then exit.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$HOME/.local/share/metis-mcp"
STATUS="$STATE_DIR/last-boot.txt"
LOG="/tmp/metis-dashboard.log"
PORT=8080
mkdir -p "$STATE_DIR"

say() { echo "[metis-boot] $*"; }

# One heartbeat at a time. A cold start takes ~50s (embedding model); the Task
# Scheduler heartbeat fires every 5 min, so overlap is unlikely but not impossible
# (e.g. logon trigger + heartbeat together). Everything downstream is idempotent,
# so a second run is harmless — it is just wasted work. Skip it.
exec 8>"$STATE_DIR/.boot.lock"
if command -v flock >/dev/null 2>&1 && ! flock -n 8; then
    echo "[metis-boot] another boot check is already running — skipping"
    exit 0
fi

{
    echo "── metis-boot $(date '+%Y-%m-%d %H:%M:%S') ──"

    # ── 1. Is the CODE current, and does the MCP server run the current code? ──
    # Handles: git fast-forward from the other computer + reinstalling the venv
    # copy the MCP server actually loads. Throttled internally; safe every 5 min.
    if [ -x "$ROOT/tools/metis-preflight.sh" ]; then
        bash "$ROOT/tools/metis-preflight.sh" 2>&1 | sed 's/^/  /'
    fi

    # ── 2. Is the DASHBOARD serving? ──────────────────────────────────────────
    # Health = HTTP 200 on /health. A listening socket is NOT health: a wedged
    # uvicorn still holds the port. This is the check that actually matters.
    if curl -sf -m 5 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
        say "dashboard healthy on :$PORT — nothing to do"
        echo "dashboard: OK (:$PORT)"
    else
        say "dashboard NOT serving on :$PORT — starting it"
        # Detached: run.sh cold-starts uvicorn in the foreground, so it must not
        # hold the heartbeat open. run.sh's own lock stops a double-launch race.
        #
        # 8>&- is load-bearing: run.sh is long-lived and would otherwise INHERIT
        # our boot-lock fd and hold it for its entire life — permanently blocking
        # every future heartbeat. That is precisely the fd-inheritance bug that
        # wedged the dashboard (the node course server holding run.sh's fd 9).
        # Do not remove it.
        setsid nohup bash "$ROOT/system/app-py/run.sh" </dev/null >"$LOG" 2>&1 8>&- &
        disown 2>/dev/null || true

        # Wait for it to actually come up. Must be MORE patient than run.sh's
        # worst case (up to 120s waiting out a stale lock holder + ~60s cold start
        # loading the embedding model) — otherwise we declare FAILED while run.sh
        # is still legitimately recovering. Still well inside the 5-min heartbeat.
        for _ in $(seq 1 60); do
            sleep 3
            if curl -sf -m 5 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
                say "dashboard is up and serving on :$PORT"
                echo "dashboard: STARTED (:$PORT)"
                break
            fi
        done
        if ! curl -sf -m 5 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
            say "dashboard FAILED to come up — see $LOG"
            echo "dashboard: FAILED (see $LOG)"
            tail -5 "$LOG" 2>/dev/null | sed 's/^/    /'
        fi
    fi
} > "$STATUS" 2>&1

# Echo the result so a human running this by hand sees it too.
cat "$STATUS"
exit 0
