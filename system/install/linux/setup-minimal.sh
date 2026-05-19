#!/usr/bin/env bash
# Metis Research Cortex — Linux/WSL Minimal Install
# Installs: core only (MCP server + agents, no dashboard)
# Fastest option — integrates with Claude Desktop via MCP
#
# Usage:  bash setup-minimal.sh [--install-dir DIR] [--api-key sk-ant-...]

set -euo pipefail

INSTALL_TYPE="minimal"
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
echo "║  Metis Research Cortex — Minimal Install             ║"
echo "║  Core (MCP server + agents only)                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

source "$(dirname "${BASH_SOURCE[0]}")/lib/_common.sh"

check_python
create_install_dir "$INSTALL_DIR"
copy_core_files "$REPO_ROOT" "$INSTALL_DIR"
create_venv "$INSTALL_DIR"
init_database "$INSTALL_DIR"
configure_mcp "$INSTALL_DIR" "$API_KEY"
write_env_file "$INSTALL_DIR" "$API_KEY"

echo ""
echo "✓ Metis (Minimal) installed to: $INSTALL_DIR"
echo ""
echo "  MCP tools: configured for Claude Desktop"
echo "  Restart Claude Desktop to activate."
echo ""
