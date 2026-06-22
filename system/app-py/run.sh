#!/bin/bash
# Metis dashboard launcher — paths derived at runtime, no hardcoded user paths.
# run.sh lives at: system/app-py/run.sh
# METIS_ROOT is two levels up: app-py/ -> system/ -> repo root

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
METIS_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_DIR="$SCRIPT_DIR"
VENV_DIR="$HOME/.local/share/metis-mcp/.venv"
MCP_SRC="$METIS_ROOT/system/mcp-server/src"

if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Metis venv not found at $VENV_DIR"
    echo "Run the installer: bash '$METIS_ROOT/system/mcp-server/setup-mcp.sh'"
    exit 1
fi

PYTHON="$VENV_DIR/bin/python3"
PY_VER=$("$PYTHON" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null)
SITE_PKG="$VENV_DIR/lib/python${PY_VER}/site-packages"

export METIS_RC_ROOT="${METIS_RC_ROOT:-$METIS_ROOT}"
export PYTHONPATH="$SITE_PKG:$MCP_SRC:$APP_DIR"
export PATH="$HOME/.local/bin:$PATH"

# AI features — set ANTHROPIC_API_KEY in system/.env (next to this file's parent folder).
# WSL interop is disabled on this machine so Windows environment variables are not
# visible to WSL processes. The key must be in system/.env or exported before launch.
if [ -z "${ANTHROPIC_API_KEY}" ]; then
    _env_file="$METIS_ROOT/system/.env"
    if [ -f "$_env_file" ]; then
        _file_key=$(grep -m1 '^ANTHROPIC_API_KEY=' "$_env_file" | cut -d= -f2-)
        [ -n "$_file_key" ] && export ANTHROPIC_API_KEY="$_file_key"
        unset _file_key
    fi
    unset _env_file
fi
# To set the key: add ANTHROPIC_API_KEY=sk-ant-... to system/.env (one line, no quotes).

cd "$APP_DIR"

# ── Persistent, rotating logs (R7) ────────────────────────────────────────────
# Off ephemeral /tmp; survives reboots; rotate at ~2 MB keeping 3 generations so a
# crash is always diagnosable.
LOG_DIR="${METIS_RC_ROOT}/system/config/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/dashboard.log"
if [ -f "$LOG_FILE" ] && [ "$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)" -gt 2097152 ]; then
    mv -f "$LOG_DIR/dashboard.log.2" "$LOG_DIR/dashboard.log.3" 2>/dev/null || true
    mv -f "$LOG_DIR/dashboard.log.1" "$LOG_DIR/dashboard.log.2" 2>/dev/null || true
    mv -f "$LOG_FILE"                "$LOG_DIR/dashboard.log.1" 2>/dev/null || true
fi
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG_FILE"; }

PORT_FILE="${METIS_RC_ROOT}/system/app-py/.metis-port"
STOP_FILE="${APP_DIR}/.metis-stop"
rm -f "$STOP_FILE" 2>/dev/null   # a fresh launch clears any prior stop request

# ── Singleton / adopt-don't-kill (R4) ─────────────────────────────────────────
# If a HEALTHY dashboard is already serving, adopt it — never kill a working server
# (killing one mid-write is what corrupted the DB on 2026-06-19). Only a wedged /
# unresponsive instance gets cleared below.
for p in 8080 $(cat "$PORT_FILE" 2>/dev/null); do
    if curl -sf -m 2 "http://127.0.0.1:$p/health" >/dev/null 2>&1; then
        log "adopt: healthy dashboard already on :$p — not restarting"
        echo "$p" > "$PORT_FILE"
        echo "Metis already running on http://localhost:$p"
        exit 0
    fi
done

# Launch lock: only one supervisor may cold-start at a time (closes the race where
# the logon autostart and a desktop double-click fire simultaneously). The winning
# supervisor holds fd 9 for its whole life — a true singleton. Losers wait for the
# winner to come up, then adopt it.
exec 9>"${APP_DIR}/.metis-launch.lock"
if command -v flock >/dev/null 2>&1 && ! flock -n 9; then
    log "another launch in progress — waiting to adopt"
    for _ in $(seq 1 30); do
        if curl -sf -m 2 "http://127.0.0.1:8080/health" >/dev/null 2>&1; then
            echo "Metis already running on http://localhost:8080"
            exit 0
        fi
        sleep 1
    done
    log "gave up waiting for the other launch"
    exit 0
fi

# No healthy instance → clear any stale/wedged one and free the preferred port.
rm -f "$PORT_FILE" 2>/dev/null
pkill -f "uvicorn main:app" 2>/dev/null || true
command -v fuser >/dev/null 2>&1 && fuser -k 8080/tcp 2>/dev/null || true

PORT=$("$PYTHON" - <<'PYEOF'
import socket, time
def free(p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(('', p)); return True
    except OSError:
        return False
    finally:
        s.close()
# Wait up to ~8s for the preferred port 8080 to free after killing the old server.
for _ in range(40):
    if free(8080):
        print(8080); break
    time.sleep(0.2)
else:
    # 8080 genuinely occupied by something else — fall back to the next free port.
    for p in range(8081, 8091):
        if free(p):
            print(p); break
    else:
        print(8080)
PYEOF
)

export METIS_PORT="$PORT"
mkdir -p "$(dirname "$PORT_FILE")"
echo "$PORT" > "$PORT_FILE"
echo "Starting Metis dashboard on http://localhost:${PORT}"
log "supervisor start — 127.0.0.1:${PORT}"

# ── Supervisor (R3): restart on crash with backoff; clean stop via .metis-stop ─
# To stop Metis deliberately:  touch "$STOP_FILE" && pkill -f 'uvicorn main:app'
# R6: bind 127.0.0.1 only (not 0.0.0.0) — single-user desktop app, no LAN exposure.
attempt=0
while [ ! -f "$STOP_FILE" ]; do
    started=$(date +%s)
    "$PYTHON" -m uvicorn main:app --host 127.0.0.1 --port "$PORT" >>"$LOG_FILE" 2>&1
    ec=$?
    [ -f "$STOP_FILE" ] && { log "stop requested — supervisor exiting"; break; }
    ran=$(( $(date +%s) - started ))
    if [ "$ran" -ge 30 ]; then attempt=0; fi   # stable run → reset backoff
    attempt=$((attempt + 1))
    if [ "$attempt" -gt 5 ]; then
        log "uvicorn exited (code $ec) after ${ran}s — 5 rapid restarts, giving up"
        break
    fi
    backoff=$(( attempt * 3 )); [ "$backoff" -gt 30 ] && backoff=30
    log "uvicorn exited (code $ec) after ${ran}s — restart #$attempt in ${backoff}s"
    sleep "$backoff"
done
rm -f "$STOP_FILE" 2>/dev/null
log "supervisor stopped"
