#!/usr/bin/env bash
# run_tests.sh — One-command test runner for the full Metis evaluation suite.
#
# Usage:
#   bash run_tests.sh              # default: unit + integration + audit (skips e2e)
#   bash run_tests.sh --fast       # unit only (< 5s)
#   bash run_tests.sh --full       # everything including e2e and known-gap docs
#   bash run_tests.sh --audit      # only the audit/ tests (wizard + UX + personas)
#   bash run_tests.sh --persona    # only persona regression tests
#   bash run_tests.sh --security   # only security / personal-data tests
#   bash run_tests.sh --html       # generate HTML report in tests/report.html
#
# Prerequisites:
#   pip install pytest pytest-html httpx fastapi pyyaml markdown
#   (all already installed in the MCP server venv)
#
# Run from any directory — this script finds the correct test root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Primary: the globally-installed Metis MCP venv (always present on a working install)
VENV_PYTHON="/home/$(whoami)/.local/share/metis-mcp/.venv/bin/python3"

# Fallback 1: local mcp-server venv (Docker/CI)
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="${SCRIPT_DIR}/../mcp-server/.venv/bin/python3"
fi

# Fallback 2: system python3
if [ ! -f "$VENV_PYTHON" ]; then
    VENV_PYTHON="$(which python3 2>/dev/null || echo python3)"
fi

# Always add MCP source to PYTHONPATH so metis_mcp imports resolve
export PYTHONPATH="${SCRIPT_DIR}/../../mcp-server/src${PYTHONPATH:+:$PYTHONPATH}"

MODE="default"
HTML_REPORT=0

for arg in "$@"; do
    case "$arg" in
        --fast)     MODE="fast" ;;
        --full)     MODE="full" ;;
        --audit)    MODE="audit" ;;
        --persona)  MODE="persona" ;;
        --security) MODE="security" ;;
        --html)     HTML_REPORT=1 ;;
    esac
done

HTML_ARGS=""
if [ "$HTML_REPORT" -eq 1 ]; then
    HTML_ARGS="--html=${SCRIPT_DIR}/report.html --self-contained-html"
fi

cd "$SCRIPT_DIR"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Metis Evaluation Suite — mode: ${MODE}"
echo "  Python: ${VENV_PYTHON}"
echo "  Date:   $(date '+%Y-%m-%d %H:%M')"
echo "═══════════════════════════════════════════════════════"
echo ""

case "$MODE" in
    fast)
        "$VENV_PYTHON" -m pytest unit/ -v --tb=short $HTML_ARGS
        ;;
    full)
        "$VENV_PYTHON" -m pytest . -v --tb=short \
            -m "unit or integration or wizard or ux or persona or e2e or known_gap" \
            $HTML_ARGS
        ;;
    audit)
        "$VENV_PYTHON" -m pytest audit/ personas/ -v --tb=short $HTML_ARGS
        ;;
    persona)
        "$VENV_PYTHON" -m pytest personas/ -v --tb=short $HTML_ARGS
        ;;
    security)
        "$VENV_PYTHON" -m pytest unit/test_personal_data_scrub.py \
            unit/test_guardrails.py -v --tb=short $HTML_ARGS
        ;;
    default)
        "$VENV_PYTHON" -m pytest . -v --tb=short \
            -m "not e2e and not known_gap" \
            $HTML_ARGS
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Done. See intentions_vs_implementation.md for the"
echo "  full gap analysis and feature status report."
echo "═══════════════════════════════════════════════════════"
