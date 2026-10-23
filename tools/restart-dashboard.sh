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
# The dashboard is whatever owns port 8080, not the first uvicorn found: a
# preview instance on another port was being killed while the real one ran on.
_port_pid() { ss -ltnpH "sport = :8080" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1; }
OLD=$(_port_pid)
[ -n "$OLD" ] && kill "$OLD" 2>/dev/null
for _ in $(seq 1 90); do
    NEW=$(_port_pid)
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
