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

# Embedding model is cached locally under FASTEMBED_CACHE_PATH after first run.
# Force fully-offline loading so startup NEVER depends on a network round-trip to
# HuggingFace — behind the ITG proxy those HEAD/GET calls stall or fail and hang
# the whole boot. If the cache is ever missing, unset these and launch once online.
export FASTEMBED_CACHE_PATH="${FASTEMBED_CACHE_PATH:-$HOME/.cache/fastembed}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Corporate proxy SSL fix: Python's httpx/requests use certifi's CA bundle by
# default, which doesn't include the ITG root CA. Point them at the system
# bundle which has itg-root-ca.pem, so HuggingFace model downloads and any
# other HTTPS calls through the proxy succeed.
_SYS_CA="/etc/ssl/certs/ca-certificates.crt"
if [ -f "$_SYS_CA" ]; then
    export SSL_CERT_FILE="$_SYS_CA"
    export REQUESTS_CA_BUNDLE="$_SYS_CA"
fi

# AI features — set ANTHROPIC_API_KEY in system/.env (next to this file's parent folder).
# WSL interop is disabled on this machine so Windows environment variables are not
# visible to WSL processes. The key must be in system/.env or exported before launch.
# Load the key from system/.env unless a REAL one (sk-ant-…) is already exported.
# A leaked/placeholder ANTHROPIC_API_KEY — e.g. a stray Windows env var passed in
# through WSL interop — used to win over .env and silently break every API call
# (no brief, "running without a key" banner). So .env now also overrides any value
# that doesn't look like a real key. Also strips CR (Windows line endings) + quotes.
case "${ANTHROPIC_API_KEY}" in
    sk-ant-*) : ;;   # already a valid key — keep it
    *)
        _env_file="$METIS_ROOT/system/.env"
        if [ -f "$_env_file" ]; then
            _file_key=$(grep -m1 '^ANTHROPIC_API_KEY=' "$_env_file" | cut -d= -f2- | tr -d '\r' | sed 's/^"//; s/"$//')
            [ -n "$_file_key" ] && export ANTHROPIC_API_KEY="$_file_key"
            unset _file_key
        fi
        unset _env_file
        ;;
esac
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

# ── Statistics course server setup (Express/Node on port 3000) ────────────────
# Defined early so both the adopt path and the cold-start path can call it.
# The course app runs from the Linux filesystem to avoid OneDrive EIO errors.
# Source files live on OneDrive and evolve there; rsync keeps ~/mlm-app current.
#
# Port strategy (all apps on this machine):
#   Metis Dashboard  → 8080 (fallback 8081-8090)  Python/uvicorn  auto-start
#   Statistics Course → 3000 (fixed)               Node.js/Express auto-start
#   HAT Dashboard    → 4321 (fixed, on-demand)     R/Shiny         manual click
MLM_APP_DIR="$HOME/mlm-app"
MLM_LOG="$LOG_DIR/course-server.log"
# Derive the OneDrive source from METIS_ROOT (both under the same Documents tree)
_docs_parent="${METIS_ROOT%/*}"
_docs_root="${_docs_parent%/*}"
MLM_ONEDRIVE_SRC="$_docs_root/9. Education/1. Multilevel Analysis/mlm-app"

_start_course_server() {
    # Find node: prefer system-wide install, fall back to nvm
    local node_exe=""
    if command -v node >/dev/null 2>&1; then
        node_exe="$(command -v node)"
    else
        local nv
        nv=$(ls "$HOME/.nvm/versions/node" 2>/dev/null | sort -V | tail -1)
        if [ -n "$nv" ]; then
            node_exe="$HOME/.nvm/versions/node/$nv/bin/node"
        fi
    fi
    if [ -z "$node_exe" ]; then
        log "node not found — Statistics course server skipped"
        return
    fi

    # Sync source files from OneDrive → Linux FS (skip node_modules, DB, backups)
    if [ -d "$MLM_ONEDRIVE_SRC" ]; then
        rsync -a --exclude='node_modules' --exclude='.git' \
              --exclude='*.db' --exclude='*.db-shm' --exclude='*.db-wal' \
              --exclude='backups' --exclude='launcher.log' \
              "$MLM_ONEDRIVE_SRC/" "$MLM_APP_DIR/" 2>/dev/null \
            && log "course files synced from OneDrive" \
            || log "course file sync failed (non-fatal)"
    fi

    log "starting Statistics course server (node on :3000)"
    nohup "$node_exe" "$MLM_APP_DIR/server.js" >> "$MLM_LOG" 2>&1 &
}

# Helper: ensure the course server is running (used in both adopt and cold-start)
_ensure_course_server() {
    if [ -f "$MLM_APP_DIR/server.js" ] && ! pgrep -f "node.*server\.js" >/dev/null 2>&1; then
        _start_course_server
    fi
}

# ── Singleton / adopt-don't-kill (R4) ─────────────────────────────────────────
# If a HEALTHY dashboard is already serving, adopt it — never kill a working server
# (killing one mid-write is what corrupted the DB on 2026-06-19). Only a wedged /
# unresponsive instance gets cleared below.
for p in 8080 $(cat "$PORT_FILE" 2>/dev/null); do
    if curl -sf -m 2 "http://127.0.0.1:$p/health" >/dev/null 2>&1; then
        log "adopt: healthy dashboard already on :$p — not restarting"
        echo "$p" > "$PORT_FILE"
        echo "Metis already running on http://localhost:$p"
        _ensure_course_server
        # Under systemd (INVOCATION_ID set): monitor the adopted server so
        # systemd restarts us (→ cold start) when it dies. Without this,
        # exit 0 + Restart=on-failure means systemd stops, and the next crash
        # has no supervisor to bring the dashboard back.
        if [ -n "${INVOCATION_ID:-}" ]; then
            log "adopt: systemd mode — monitoring adopted server on :$p"
            while curl -sf -m 5 "http://127.0.0.1:$p/health" >/dev/null 2>&1; do
                sleep 30
            done
            log "adopt: adopted server on :$p is gone — exiting 1 for systemd restart"
            exit 1
        fi
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
            # Under systemd: monitor the winner's server (same as adopt path)
            if [ -n "${INVOCATION_ID:-}" ]; then
                log "flock-loser: systemd mode — monitoring on :8080"
                while curl -sf -m 5 "http://127.0.0.1:8080/health" >/dev/null 2>&1; do
                    sleep 30
                done
                log "flock-loser: server on :8080 is gone — exiting 1 for systemd restart"
                exit 1
            fi
            exit 0
        fi
        sleep 1
    done
    log "gave up waiting for the other launch"
    exit 1
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

# ── Ensure the course server is running (cold-start path) ─────────────────────
_ensure_course_server

# Background watchdog: restart Node if it crashes while Metis stays up.
# Checks every 60s. Exits when .metis-stop is touched.
(
    while [ ! -f "$STOP_FILE" ]; do
        sleep 60
        if [ -f "$MLM_APP_DIR/server.js" ] && ! pgrep -f "node.*server\.js" >/dev/null 2>&1; then
            log "course watchdog: Node died — restarting"
            _start_course_server
        fi
    done
) &

# ── Supervisor (R3): restart on crash with backoff; clean stop via .metis-stop ─
# To stop Metis deliberately:  touch "$STOP_FILE" && pkill -f 'uvicorn main:app'
# R6: bind 127.0.0.1 only (not 0.0.0.0) — single-user desktop app, no LAN exposure.
# R8: port cleanup before each restart — prevents "address already in use" crash loops
#     after SIGKILL (exit 137) leaves the socket in TIME_WAIT.
attempt=0
while [ ! -f "$STOP_FILE" ]; do
    started=$(date +%s)
    "$PYTHON" -m uvicorn main:app --host 127.0.0.1 --port "$PORT" >>"$LOG_FILE" 2>&1
    ec=$?
    [ -f "$STOP_FILE" ] && { log "stop requested — supervisor exiting"; break; }
    ran=$(( $(date +%s) - started ))
    if [ "$ran" -ge 30 ]; then attempt=0; fi   # stable run → reset backoff
    attempt=$((attempt + 1))
    if [ "$attempt" -gt 8 ]; then
        log "uvicorn exited (code $ec) after ${ran}s — 8 rapid restarts, giving up"
        rm -f "$STOP_FILE" 2>/dev/null
        log "supervisor stopped (give-up)"
        exit 1
    fi
    # Clean up stale processes and free the port before retrying (R8).
    # Without this, a SIGKILL'd uvicorn leaves the socket in TIME_WAIT and every
    # restart attempt fails with exit 1 ("address already in use") until the kernel
    # releases it (~60s). This was the primary cause of the "5 rapid restarts, giving
    # up" crash loop observed on 2026-06-29.
    pkill -f "uvicorn main:app" 2>/dev/null || true
    command -v fuser >/dev/null 2>&1 && fuser -k "$PORT"/tcp 2>/dev/null || true
    backoff=$(( attempt * 5 )); [ "$backoff" -gt 60 ] && backoff=60
    log "uvicorn exited (code $ec) after ${ran}s — restart #$attempt in ${backoff}s"
    sleep "$backoff"
done
rm -f "$STOP_FILE" 2>/dev/null
log "supervisor stopped"
