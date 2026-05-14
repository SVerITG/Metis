#!/usr/bin/env bash
# Metis Research Cortex — Linux/WSL Full Install
# Installs: core (MCP server + agents) + dashboard + biostatistics course
#
# Usage:  bash setup-full.sh [--install-dir DIR] [--api-key sk-ant-...]
# Prereq: Python 3.10+, git, curl

set -euo pipefail

INSTALL_TYPE="full"
INSTALL_DIR="${HOME}/Documents/Metis"
API_KEY=""
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"

# ── Argument parsing ──────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --api-key)     API_KEY="$2";     shift 2 ;;
    *)             echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "╔══════════════════════════════════════════════════════╗"
echo "║  Metis Research Cortex — Full Install                ║"
echo "║  Core + Dashboard + Biostatistics course             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Install directory: $INSTALL_DIR"
echo ""

source "$(dirname "${BASH_SOURCE[0]}")/lib/_common.sh"

check_python
create_install_dir "$INSTALL_DIR"
copy_core_files "$REPO_ROOT" "$INSTALL_DIR"
copy_dashboard "$REPO_ROOT" "$INSTALL_DIR"
copy_courses "$REPO_ROOT" "$INSTALL_DIR"
create_venv "$INSTALL_DIR"
init_database "$INSTALL_DIR"
seed_epi_base "$INSTALL_DIR"
configure_mcp "$INSTALL_DIR" "$API_KEY"
write_env_file "$INSTALL_DIR" "$API_KEY"
write_launcher "$INSTALL_DIR" "full"

echo ""
echo "✓ Metis (Full) installed to: $INSTALL_DIR"
echo ""
echo "  Start dashboard:  $INSTALL_DIR/start.sh"
echo "  Open browser:     http://localhost:8080"
echo "  MCP tools:        configured for Claude Desktop"
echo ""
