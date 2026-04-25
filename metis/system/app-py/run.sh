#!/bin/bash
# Metis Python Dashboard — launcher (matches MCP server pattern for NTFS/WSL compatibility)

APP_DIR="/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis/system/app-py"
SITE_PKG="/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis/system/mcp-server/.venv/lib/python3.12/site-packages"
HOME_SITE_PKG="/home/sverschaeve/.local/share/metis-mcp/.venv/lib/python3.12/site-packages"
MCP_SRC="/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis/system/mcp-server/src"

export METIS_RC_ROOT="/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis"
export PYTHONPATH="$HOME_SITE_PKG:$SITE_PKG:$MCP_SRC:$APP_DIR"

cd "$APP_DIR"
exec /usr/bin/python3.12 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
