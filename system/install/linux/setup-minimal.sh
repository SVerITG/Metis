#!/usr/bin/env bash
# Linux "minimal" install — forwards to the one real installer, setup-mcp.sh, with
# METIS_PROFILE=light.
#
# These scripts used to be a second installer of their own. It drifted: it
# reported the database as created without creating it, and served the dashboard
# on every network interface. One installer cannot disagree with itself.
#
# Usage:  bash setup-minimal.sh [--api-key sk-ant-...] [--with-voice]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-key)     export ANTHROPIC_API_KEY="$2"; shift 2 ;;
    --install-dir) echo "Note: --install-dir is ignored; Metis installs where this folder is."; shift 2 ;;
    *)             ARGS+=("$1"); shift ;;
  esac
done

METIS_PROFILE=light exec bash "$ROOT/system/mcp-server/setup-mcp.sh" ${ARGS[@]+"${ARGS[@]}"}
