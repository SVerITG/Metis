#!/usr/bin/env bash
# Regenerate system/mcp-server/requirements.txt — the version lock both installers
# use as a constraint file.
#
# One resolution covers the MCP server (with the extras the installers add by
# default) AND the dashboard, so a shared package cannot be pinned two ways.
# Versions already in the lock are kept unless a change forces a new one, which
# keeps a regeneration from quietly upgrading everything at once.
#
# Usage:  bash tools/lock-requirements.sh            # keep current versions where possible
#         bash tools/lock-requirements.sh --upgrade  # move everything to the newest allowed
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOCK=system/mcp-server/requirements.txt
UV=$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")
[ -x "$UV" ] || { echo "uv is required: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

# The extras every installer adds by default. voice is opt-in (it compiles C).
EXTRAS=(--extra embedding --extra library --extra ocr)

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
# Seed with the current lock (minus the header) so uv prefers those versions.
[ "${1:-}" = "--upgrade" ] || grep -v '^#' "$LOCK" > "$TMP" || true

"$UV" pip compile system/mcp-server/pyproject.toml system/app-py/requirements.txt \
  "${EXTRAS[@]}" --universal --python-version 3.11 --no-header -q -o "$TMP"

{
  cat <<'EOF'
# Version lock for the MCP server AND the dashboard — one resolution, so the two
# can never ask for incompatible versions of a shared package.
#
# The installers use it as a CONSTRAINT file (pip/uv `-c`), not a package list:
# pyproject.toml and app-py/requirements.txt say WHAT is installed, this file
# says WHICH version. A hand-pinned list here once asked for two versions that
# cannot coexist, and every fresh install failed for three months.
#
# Generated — do not edit. Regenerate with:  bash tools/lock-requirements.sh
EOF
  cat "$TMP"
} > "$LOCK"
echo "wrote $LOCK ($(grep -c '==' "$LOCK") pinned packages)"
