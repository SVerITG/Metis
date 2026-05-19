#!/usr/bin/env bash
# =============================================================================
# Metis MCP Server — Local Setup Script
# Run once per computer (in WSL) to install the MCP server locally.
# The venv is created in ~/.local/share/metis-mcp/ so it is NOT synced
# by OneDrive and won't be deleted or corrupted by cross-computer sync.
# =============================================================================

set -e

VENV_DIR="$HOME/.local/share/metis-mcp/.venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Metis MCP Server Setup ==="
echo "Script dir: $SCRIPT_DIR"
echo "Venv dir:   $VENV_DIR"
echo ""

# 1. Create venv
echo "[1/4] Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

# 2. Upgrade pip + setuptools
echo "[2/4] Upgrading pip and setuptools..."
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel --quiet

# 3. Install dependencies directly (bypass broken editable install on WSL)
echo "[3/4] Installing dependencies..."
"$VENV_DIR/bin/pip" install "mcp>=1.0.0" pyyaml requests --quiet

# 4. Create .pth file so metis_mcp package is importable
SITE_PACKAGES=$("$VENV_DIR/bin/python3" -c "import site; print(site.getsitepackages()[0])")
echo "$SCRIPT_DIR/src" > "$SITE_PACKAGES/metis_mcp.pth"
echo "Linked: $SCRIPT_DIR/src -> $SITE_PACKAGES/metis_mcp.pth"

# 5. Create console script
cat > "$VENV_DIR/bin/metis-mcp" << 'SCRIPT'
#!/bin/sh
'''exec' "$(dirname "$0")/python3" "$0" "$@"
' '''
import re
import sys
from metis_mcp.server import run
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(run())
SCRIPT
chmod +x "$VENV_DIR/bin/metis-mcp"

# 6. Update Claude Code settings.json
SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
    python3 - << PYEOF
import json, sys

settings_path = "$SETTINGS"
with open(settings_path) as f:
    s = json.load(f)

s.setdefault("mcpServers", {})["metis-pkm"] = {
    "command": "$VENV_DIR/bin/metis-mcp",
    "env": {
        "METIS_PKM_ROOT": "$SCRIPT_DIR/../../../.."
    }
}

with open(settings_path, "w") as f:
    json.dump(s, f, indent=2)
print("Updated ~/.claude/settings.json")
PYEOF
else
    echo "No ~/.claude/settings.json found — create it manually (see SETUP.md)"
fi

# 6. Create Claude Desktop wrapper script
cat > "$HOME/.local/share/metis-mcp/run.sh" << WRAPPER
#!/bin/bash
export METIS_PKM_ROOT="$SCRIPT_DIR/../../../.."
exec "$VENV_DIR/bin/metis-mcp"
WRAPPER
chmod +x "$HOME/.local/share/metis-mcp/run.sh"
echo "Created wrapper: $HOME/.local/share/metis-mcp/run.sh"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Verify with:"
echo "  $VENV_DIR/bin/python3 -c 'from metis_mcp.server import app; print(app.name)'"
echo ""
echo "Restart Claude Code for the MCP server to take effect."
