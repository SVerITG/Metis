#!/bin/bash
# restart-dashboard.sh — restart uvicorn and WAIT FOR THE NEW PROCESS.
#
# Waiting on /health after a kill is wrong and cost three false diagnoses on
# 2026-08-24: the dying process keeps answering /health for a moment, so the wait
# returns immediately, the next request lands in the supervisor's 5-second restart
# backoff, and curl reports 000 or a stale 302. Every one of those looked like a
# bug in the code just written.
#
# So: record the old PID, kill it, wait for a DIFFERENT pid to appear, and only
# then wait for health.
set -uo pipefail
OLD=$(pgrep -f "uvicorn main:app" | head -1)
[ -n "$OLD" ] && kill "$OLD" 2>/dev/null
for _ in $(seq 1 90); do
    NEW=$(pgrep -f "uvicorn main:app" | head -1)
    [ -n "$NEW" ] && [ "$NEW" != "$OLD" ] && break
    sleep 1
done
[ -z "${NEW:-}" ] && { echo "no uvicorn appeared"; exit 1; }
for _ in $(seq 1 90); do
    curl -sf -m 3 http://127.0.0.1:8080/health >/dev/null 2>&1 && {
        echo "dashboard up (pid $OLD -> $NEW)"; exit 0; }
    sleep 1
done
echo "pid $NEW started but never became healthy"; exit 1
