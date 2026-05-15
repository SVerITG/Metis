#!/bin/bash
# run-demo.sh — Start Metis dashboard with demo/screenshot data.
#
# Creates a temporary demo database seeded with fictional researcher data
# (Dr. Amélie Fontaine, Senior Epidemiologist, IMT Lyon) suitable for
# screenshots, demos, and documentation without exposing personal data.
#
# Usage:
#   bash system/app-py/run-demo.sh
#   # Dashboard opens at http://127.0.0.1:8081
#
# Note: runs on port 8081 so it doesn't conflict with your real Metis (8080).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
METIS_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APP_DIR="$SCRIPT_DIR"
VENV_DIR="$HOME/.local/share/metis-mcp/.venv"
MCP_SRC="$METIS_ROOT/system/mcp-server/src"
SEED_SCRIPT="$METIS_ROOT/system/install/seed_mockup_demo.py"
DEMO_DB="$METIS_ROOT/system/app/data/demo.sqlite"

if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Metis venv not found at $VENV_DIR"
    echo "Run the installer first: bash '$METIS_ROOT/system/mcp-server/setup-mcp.sh'"
    exit 1
fi

PYTHON="$VENV_DIR/bin/python3"
PY_VER=$("$PYTHON" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null)
SITE_PKG="$VENV_DIR/lib/python${PY_VER}/site-packages"

# --- Create or refresh demo database ---
echo "Setting up demo database..."

# Create empty demo.sqlite by running migrations against it
DEMO_DB_DIR="$(dirname "$DEMO_DB")"
mkdir -p "$DEMO_DB_DIR"

if [ ! -f "$DEMO_DB" ]; then
    echo "Creating fresh demo database at $DEMO_DB"
    # Copy the live DB structure (tables only, no user data) using sqlite3
    if command -v sqlite3 &>/dev/null; then
        sqlite3 "$DEMO_DB" ""
    else
        # Fallback: start dashboard briefly to create the DB via migrations, then seed
        METIS_DB="$DEMO_DB" METIS_RC_ROOT="$METIS_ROOT" PYTHONPATH="$SITE_PKG:$MCP_SRC:$APP_DIR" \
            "$PYTHON" -c "
import os, sys
sys.path.insert(0, '$SITE_PKG')
sys.path.insert(0, '$MCP_SRC')
sys.path.insert(0, '$APP_DIR')
os.environ['METIS_RC_ROOT'] = '$METIS_ROOT'
os.environ['METIS_DB'] = '$DEMO_DB'
from db import run_migrations
run_migrations()
print('Demo DB initialized')
"
    fi
fi

# Seed with demo data (always refresh so screenshots are consistent)
echo "Seeding demo data..."
METIS_RC_ROOT="$METIS_ROOT" PYTHONPATH="$SITE_PKG:$MCP_SRC:$APP_DIR" \
    "$PYTHON" "$SEED_SCRIPT" --db "$DEMO_DB" --reset

echo ""
echo "Demo database ready: $DEMO_DB"
echo "Starting Metis demo dashboard on port 8081..."
echo "Open: http://127.0.0.1:8081"
echo ""
echo "Press Ctrl+C to stop."

export METIS_RC_ROOT="$METIS_ROOT"
export METIS_DB="$DEMO_DB"
export PYTHONPATH="$SITE_PKG:$MCP_SRC:$APP_DIR"
export PATH="$HOME/.local/bin:$PATH"

pkill -f "uvicorn main:app.*8081" 2>/dev/null || true
sleep 0.3

cd "$APP_DIR"
exec "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port 8081
