#!/bin/bash
# test-entrypoint.sh — Start Metis in a clean container for installer testing.
#
# Code:  /opt/metis        (read-only bind mount — your repo)
# Data:  /opt/metis-data   (writable named volume — zero personal data)
# Venv:  /root/.local/share/metis-mcp  (named volume — cached between runs)
#
# Profiles:
#   METIS_PROFILE=standard  → installs MCP + dashboard, starts dashboard on 8080
#   METIS_PROFILE=light     → installs MCP only, runs MCP server (no dashboard)
#
# Reset to a completely fresh state:
#   docker compose -f docker-compose.test.yml down -v

set -euo pipefail

CODE=/opt/metis
DATA=/opt/metis-data
VENV_DIR="$HOME/.local/share/metis-mcp/.venv"
PROFILE="${METIS_PROFILE:-standard}"

# ── Install packages if venv doesn't exist (first run only) ──────────────────
if [ ! -f "$VENV_DIR/bin/python3" ]; then
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "  First run — installing Metis packages (profile: $PROFILE)"
    echo "══════════════════════════════════════════════════════════"
    cd "$CODE"
    METIS_PROFILE="$PROFILE" bash system/mcp-server/setup-mcp.sh
fi

# ── Prepare fresh data directory (idempotent) ────────────────────────────────
mkdir -p \
    "$DATA/system/config" \
    "$DATA/system/app-py/data" \
    "$DATA/system/app-py" \
    "$DATA/projects/active" \
    "$DATA/inputs/meetings" \
    "$DATA/inputs/literature" \
    "$DATA/journal" \
    "$DATA/inbox" \
    "$DATA/outputs/reviews"

# Always reset to first-run state so wizard appears fresh
touch "$DATA/system/config/.first-run"
rm -f "$DATA/system/config/user-config.yaml"
rm -f "$DATA/system/config/metis-persona.md"

export METIS_RC_ROOT="$DATA"
cd "$CODE"

# ── Start appropriate service based on profile ────────────────────────────────
if [ "$PROFILE" = "light" ]; then
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "  Metis test — MCP server only (light profile)"
    echo "  Check logs: docker logs <container-name>"
    echo "══════════════════════════════════════════════════════════"
    echo ""

    # Verify MCP server imports, report tool + prompt counts, then run as server
    "$VENV_DIR/bin/python3" -c "
import asyncio
import metis_mcp.server
from metis_mcp.app_instance import app
tools = list(app._tool_manager._tools.keys()) if hasattr(app, '_tool_manager') else []
prompts = asyncio.run(app.list_prompts())
pnames = {p.name for p in prompts}
assert 'search_pdf_knowledge' in tools, 'knowledge layer tool missing — subset too narrow'
assert 'metis' in pnames, 'metis router prompt missing — Desktop routing broken'
print(f'  MCP server OK — {len(tools)} tools, {len(prompts)} prompts registered')
"
    echo "  ✓ MCP server verified"
    echo "  Starting MCP server process..."
    exec "$VENV_DIR/bin/python3" -m metis_mcp.server
else
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "  Metis test environment (profile: $PROFILE)"
    echo "  Code:  $CODE  (read-only)"
    echo "  Data:  $DATA  (fresh — no personal data)"
    echo ""
    echo "  Dashboard:    http://localhost:8080"
    echo "  Setup wizard: http://localhost:8080/setup"
    echo ""
    echo "  Reset: docker compose -f docker-compose.test.yml down -v"
    echo "══════════════════════════════════════════════════════════"
    echo ""
    exec bash system/app-py/run.sh
fi
