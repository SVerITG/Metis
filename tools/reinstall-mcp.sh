#!/bin/bash
# reinstall-mcp.sh — Reinstall the Metis MCP server package from current source.
#
# WHY THIS EXISTS:
#   The MCP server runs an INSTALLED COPY of the package (in the venv site-packages),
#   not the source tree. So edits to system/mcp-server/src/ do NOT take effect until
#   the package is reinstalled AND the server reconnects. Skipping this is the single
#   most common "my change didn't work / the server is broken" failure.
#
# USAGE:   bash tools/reinstall-mcp.sh
# AFTER:   reconnect the MCP server (Claude Code: /mcp → reconnect metis-rc;
#          Claude Desktop: quit & reopen).
#
# Works on WSL, Linux, and macOS. Uses uv if available, else the venv's pip.

set -uo pipefail

# ── Locate repo root (this script lives in tools/) ───────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$REPO_ROOT/system/mcp-server"
if [ ! -f "$SRC/pyproject.toml" ]; then
  echo "ERROR: cannot find system/mcp-server/pyproject.toml under $REPO_ROOT"
  exit 1
fi

VENV="$HOME/.local/share/metis-mcp/.venv"
PY="$VENV/bin/python3"
LOCAL_SRC="$HOME/.local/share/metis-mcp/src-install"

if [ ! -x "$PY" ]; then
  echo "ERROR: venv python not found at $PY"
  echo "Run the installer first: bash system/mcp-server/setup-mcp.sh"
  exit 1
fi

echo "── Reinstalling Metis MCP server from source ──"
echo "  source:  $SRC"
echo "  venv:    $VENV"

# ── Copy source to a local (non-NTFS) dir so setuptools can write temp files ──
rm -rf "$LOCAL_SRC"
mkdir -p "$LOCAL_SRC"
cp -r "$SRC/src" "$LOCAL_SRC/"
cp "$SRC/pyproject.toml" "$LOCAL_SRC/"
[ -f "$SRC/requirements.txt" ] && cp "$SRC/requirements.txt" "$LOCAL_SRC/"

# ── Reinstall (no deps = fast; deps unchanged on a code-only edit) ───────────
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
if [ -x "$UV" ]; then
  echo "  using uv"
  "$UV" pip install --python "$PY" --no-deps --reinstall "$LOCAL_SRC" || {
    echo "  uv failed — falling back to pip"; "$PY" -m pip install --no-deps --force-reinstall "$LOCAL_SRC"; }
else
  echo "  using pip"
  "$PY" -m pip install --no-deps --force-reinstall "$LOCAL_SRC"
fi

# ── Verify the installed package imports and registers tools ─────────────────
echo "── Verifying ──"
COUNT="$("$PY" - <<'PYEOF'
try:
    import metis_mcp.server as s
    from metis_mcp.app_instance import app
    n = len(app._tool_manager._tools) if hasattr(app, "_tool_manager") else 0
    failed = getattr(s, "FAILED_MODULES", {})
    print(f"OK {n} {len(failed)}")
    if failed:
        for k, v in failed.items():
            print(f"FAILMOD {k}: {v}")
except Exception as e:
    print(f"IMPORTFAIL {type(e).__name__}: {e}")
PYEOF
)"
# Check the FAILURE case outside any pipeline. `exit 1` inside `echo … | while`
# runs in a SUBSHELL and only exits that subshell — so the script sailed on and
# printed "Reinstall complete." with status 0 even when the package did not import.
# metis-preflight.sh gates on this exit code and would then log "running current
# code" over a broken install. Same false-success class as register-autostart.ps1.
if printf '%s\n' "$COUNT" | grep -q '^IMPORTFAIL'; then
  printf '%s\n' "$COUNT" | sed -n 's/^IMPORTFAIL /  ✗ /p'
  echo ""
  echo "  The installed package does NOT import — the server would start on broken code."
  echo "  Nothing was verified. Fix the error above and re-run."
  exit 1
fi

printf '%s\n' "$COUNT" | while read -r line; do
  case "$line" in
    OK*)      set -- $line; echo "  ✓ imports OK — $2 tools registered, $3 module(s) skipped" ;;
    FAILMOD*) echo "  ⚠ ${line#FAILMOD }" ;;
  esac
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Reinstall complete."
echo "  NOW RECONNECT THE SERVER so it loads the new code:"
echo "    • Claude Code:    run  /mcp  → reconnect 'metis-rc'  (or restart)"
echo "    • Claude Desktop: quit and reopen the app"
echo "════════════════════════════════════════════════════════════════════"
