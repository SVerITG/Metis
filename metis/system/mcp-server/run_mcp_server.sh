#!/bin/bash
# run_mcp_server.sh
# Wrapper to launch the Metis MCP server from Claude Desktop (Windows + WSL).
#
# Root cause context: the .venv lives on OneDrive (NTFS mount), which does not
# support symlinks. Python's venv therefore cannot create the python/python3
# symlinks in .venv/bin/, so the metis-mcp entry-point script fails.
# Fix: call the system Python directly with the venv site-packages on PYTHONPATH.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_SITE="$SCRIPT_DIR/.venv/lib/python3.12/site-packages"
SRC_DIR="$SCRIPT_DIR/src"

export PYTHONPATH="$VENV_SITE:$SRC_DIR${PYTHONPATH:+:$PYTHONPATH}"
export METIS_RC_ROOT="${METIS_RC_ROOT:-/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis}"

exec /usr/bin/python3.12 -m metis_mcp.server
