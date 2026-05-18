#!/usr/bin/env bash
# Metis Research Cortex — Linux/WSL Standard Install
# Installs: core (MCP server + agents) + dashboard (no extra courses)
#
# Usage:  bash setup-standard.sh [--install-dir DIR] [--api-key sk-ant-...]

set -euo pipefail

INSTALL_TYPE="standard"
INSTALL_DIR="${HOME}/Documents/Metis"
API_KEY=""
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --api-key)     API_KEY="$2";     shift 2 ;;
    *)             echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Metis Research Cortex — Standard Install            ║"
echo "║  Core + Dashboard                                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

source "$(dirname "${BASH_SOURCE[0]}")/lib/_common.sh"

check_python
create_install_dir "$INSTALL_DIR"
copy_core_files "$REPO_ROOT" "$INSTALL_DIR"
copy_dashboard "$REPO_ROOT" "$INSTALL_DIR"
create_venv "$INSTALL_DIR"
init_database "$INSTALL_DIR"
configure_mcp "$INSTALL_DIR" "$API_KEY"
write_env_file "$INSTALL_DIR" "$API_KEY"
write_launcher "$INSTALL_DIR" "standard"

echo ""
echo "✓ Metis (Standard) installed to: $INSTALL_DIR"
echo ""
echo "  Start dashboard:  $INSTALL_DIR/start.sh"
echo "  Open browser:     http://localhost:8080"
echo ""
