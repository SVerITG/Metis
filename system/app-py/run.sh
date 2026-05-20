#!/bin/bash
# Metis dashboard launcher — paths derived at runtime, no hardcoded user paths.
# run.sh lives at: system/app-py/run.sh
# METIS_ROOT is two levels up: app-py/ -> system/ -> metis/

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

export METIS_RC_ROOT="$METIS_ROOT"
export PYTHONPATH="$SITE_PKG:$MCP_SRC:$APP_DIR"
export PATH="$HOME/.local/bin:$PATH"

# AI features — inherit from Windows environment automatically (no manual config needed).
# If ANTHROPIC_API_KEY is already set in this shell, it is used as-is.
# Otherwise, try to read it from the Windows user environment via PowerShell.
if [ -z "${ANTHROPIC_API_KEY}" ]; then
    _win_key=$(powershell.exe -NoProfile -NonInteractive -Command \
        "[Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','User')" 2>/dev/null | tr -d '\r\n')
    [ -n "$_win_key" ] && export ANTHROPIC_API_KEY="$_win_key"
    unset _win_key
fi
# To set the key permanently in Windows: Start → "Edit the system environment variables"
# → Environment Variables → User variables → New → ANTHROPIC_API_KEY = sk-ant-...

cd "$APP_DIR"

# Kill any previous Metis instance (on any port)
pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 0.5

# Auto-pick first free port in range 8080–8090
PORT=$("$PYTHON" - <<'PYEOF'
import socket
for p in range(8080, 8091):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', p))
        s.close()
        print(p)
        break
    except OSError:
        continue
else:
    print(8080)
PYEOF
)

export METIS_PORT="$PORT"
echo "Starting Metis dashboard on http://localhost:${PORT}"

# Write selected port to a file so the desktop shortcut can open the correct URL
echo "$PORT" > "$APP_DIR/.metis-port"

exec "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "$PORT"
