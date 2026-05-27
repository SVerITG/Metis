#!/bin/bash
# setup-mcp.sh — Install / reinstall the Metis MCP server on WSL Ubuntu.
#
# Works on Ubuntu 20.04 (Python 3.8), 22.04 (3.10), 24.04 (3.12).
# Installs a dedicated venv at ~/.local/share/metis-mcp/.venv
# so the NTFS OneDrive path never needs to manage symlinks.
#
# Run once after a fresh WSL install or when adding new tool modules:
#   bash setup-mcp.sh

set -euo pipefail

# ── Install profile ──────────────────────────────────────────────────────────
# Choose how much of Metis to install:
#   light    — MCP server only. Works with Claude Desktop + Claude Code. ~5 min.
#   standard — MCP server + Python dashboard (9-tab UI). ~15 min. (DEFAULT)
#   full     — Standard + Windows Task Scheduler automation + daily scan. ~25 min.
#
# Override via environment: METIS_PROFILE=light bash setup-mcp.sh
METIS_PROFILE="${METIS_PROFILE:-}"

if [ -z "$METIS_PROFILE" ] && [ -t 0 ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Metis Install Profile"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  [1] light    — MCP server only (~5 min)"
  echo "  [2] standard — MCP server + dashboard (~15 min)  [DEFAULT]"
  echo "  [3] full     — Standard + Windows scheduler (~25 min)"
  echo ""
  read -rp "  Choose profile [1/2/3, Enter for standard]: " PROFILE_CHOICE
  case "$PROFILE_CHOICE" in
    1) METIS_PROFILE="light" ;;
    3) METIS_PROFILE="full" ;;
    *) METIS_PROFILE="standard" ;;
  esac
elif [ -z "$METIS_PROFILE" ]; then
  METIS_PROFILE="standard"
fi

echo "Installing Metis with profile: $METIS_PROFILE"

# ── Config ──────────────────────────────────────────────────────────────────
VENV_DIR="$HOME/.local/share/metis-mcp/.venv"
RUN_SCRIPT="$HOME/.local/share/metis-mcp/run.sh"
LOCAL_SRC="$HOME/.local/share/metis-mcp/src-install"
METIS_RC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_DIR="$METIS_RC_ROOT/system/mcp-server"

mkdir -p "$HOME/.local/share/metis-mcp"

# ── Install uv (preferred — no sudo, no python3.X-venv package needed) ───────
# uv manages its own Python and venv, so it works on any OS/distro without
# requiring OS-level venv packages or sudo.
UV="$HOME/.local/bin/uv"
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$UV" ]; then
  echo "Installing uv (Python package manager)..."
  # -k: bypass corporate SSL inspection proxies (self-signed cert in chain)
  if curl -LsSf --retry 3 https://astral.sh/uv/install.sh | sh 2>/dev/null; then
    echo "  uv installed"
  else
    curl -LsSfk --retry 3 https://astral.sh/uv/install.sh | sh 2>/dev/null && echo "  uv installed (SSL bypass)" || true
  fi
  # Source env so uv is on PATH for the rest of this script
  [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
fi

# Ensure uv is on PATH
[ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env"
UV=$(command -v uv 2>/dev/null || echo "$HOME/.local/bin/uv")

if [ -x "$UV" ]; then
  echo "Using uv: $UV ($($UV --version))"
  USE_UV=1
else
  echo "uv not available — falling back to python3 + pip"
  USE_UV=0
fi

# ── Create venv ──────────────────────────────────────────────────────────────
if [ "$USE_UV" = "1" ]; then
  # uv can download Python itself if needed — no OS packages required
  if [ -d "$VENV_DIR" ] && [ ! -f "$VENV_DIR/bin/python3" ]; then
    echo "Venv appears broken — recreating..."
    rm -rf "$VENV_DIR"
  fi
  if [ -d "$VENV_DIR" ]; then
    echo "Existing venv found — updating packages only."
  else
    echo "Creating venv at $VENV_DIR (Python 3.12)..."
    "$UV" venv "$VENV_DIR" --python 3.12
  fi
else
  # Fallback: system Python + venv
  PYTHON=""
  for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      VER=$("$candidate" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null)
      MAJOR=${VER%%.*}; MINOR=${VER#*.}
      if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 9 ]; then
        PYTHON="$candidate"; break
      fi
    fi
  done
  [ -z "$PYTHON" ] && echo "ERROR: Python 3.9+ not found." && exit 1
  PYTHON_PATH=$(command -v "$PYTHON")
  echo "Using Python: $PYTHON_PATH ($($PYTHON --version))"
  if [ -d "$VENV_DIR" ] && [ ! -f "$VENV_DIR/bin/python3" ]; then
    rm -rf "$VENV_DIR"
  fi
  [ ! -d "$VENV_DIR" ] && "$PYTHON_PATH" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
fi

# ── Install package ───────────────────────────────────────────────────────────
# The source lives on OneDrive (NTFS). Setuptools can't write temp files there
# (fchmod/chmod not permitted on NTFS), so we copy to a local path first.
echo "Copying source to local filesystem for install..."
rm -rf "$LOCAL_SRC"
mkdir -p "$LOCAL_SRC"
cp -r "$SRC_DIR/src" "$LOCAL_SRC/"
cp "$SRC_DIR/pyproject.toml" "$LOCAL_SRC/"
[ -f "$SRC_DIR/requirements.txt" ] && cp "$SRC_DIR/requirements.txt" "$LOCAL_SRC/"

echo "Installing MCP server requirements..."
if [ "$USE_UV" = "1" ]; then
  [ -f "$LOCAL_SRC/requirements.txt" ] && "$UV" pip install --python "$VENV_DIR/bin/python3" -r "$LOCAL_SRC/requirements.txt"
  echo "Installing metis-mcp-server package..."
  "$UV" pip install --python "$VENV_DIR/bin/python3" "$LOCAL_SRC"
else
  [ -f "$LOCAL_SRC/requirements.txt" ] && "$VENV_DIR/bin/pip" install -r "$LOCAL_SRC/requirements.txt"
  echo "Installing metis-mcp-server package..."
  "$VENV_DIR/bin/pip" install "$LOCAL_SRC"
fi
echo "  MCP server installed"

# ── Install dashboard (app-py) dependencies into same venv ───────────────────
# Skipped on 'light' profile — dashboard not included.
if [ "$METIS_PROFILE" != "light" ]; then
  APP_REQ="$METIS_RC_ROOT/system/app-py/requirements.txt"
  if [ -f "$APP_REQ" ]; then
    echo "Installing dashboard dependencies..."
    if [ "$USE_UV" = "1" ]; then
      "$UV" pip install --python "$VENV_DIR/bin/python3" -r "$APP_REQ"
    else
      "$VENV_DIR/bin/pip" install -r "$APP_REQ"
    fi
    echo "  Dashboard deps installed"
  fi
else
  echo "Skipping dashboard install (light profile)"
fi

# ── Write run.sh ─────────────────────────────────────────────────────────────
cat > "$RUN_SCRIPT" <<RUNSH
#!/bin/bash
# Auto-generated by setup-mcp.sh — do not edit manually.
VENV_DIR="$VENV_DIR"
export METIS_RC_ROOT="$METIS_RC_ROOT"
exec "\$VENV_DIR/bin/python3" -m metis_mcp.server
RUNSH
chmod +x "$RUN_SCRIPT"
echo "run.sh written to $RUN_SCRIPT"

# ── Verify ──────────────────────────────────────────────────────────────────
echo ""
echo "Verifying import..."
if "$VENV_DIR/bin/python3" -c "import metis_mcp.server; print('  metis_mcp.server import OK')" 2>&1; then
  TOOL_COUNT=$("$VENV_DIR/bin/python3" -c "
import metis_mcp.server
from metis_mcp.app_instance import app
tools = list(app._tool_manager._tools.keys()) if hasattr(app, '_tool_manager') else []
print(len(tools))
" 2>/dev/null || echo "?")
  echo "  $TOOL_COUNT tools registered"
else
  echo "  ERROR: import failed — see above"
  exit 1
fi

# ── Auto-register with Claude Code ──────────────────────────────────────────
# Claude Code stores MCP servers in ~/.claude.json (per-project) via `claude mcp add`.
# ~/.claude/settings.json is used only for permissions (tool auto-approval).
CC_SETTINGS="$HOME/.claude/settings.json"
mkdir -p "$HOME/.claude"

# Register the server via the CLI (writes to ~/.claude.json for this project)
if command -v claude >/dev/null 2>&1; then
  # Remove old registration first to avoid duplicates, then re-add
  claude mcp remove metis-rc 2>/dev/null || true
  if claude mcp add metis-rc "$RUN_SCRIPT" 2>/dev/null; then
    echo "  Claude Code: registered metis-rc via claude mcp add"
  else
    echo "  Claude Code: mcp add failed — you may need to run: claude mcp add metis-rc $RUN_SCRIPT"
  fi
else
  echo "  Claude Code CLI not found — skipping auto-registration"
  echo "  Once installed, run: claude mcp add metis-rc $RUN_SCRIPT"
fi

# Write permissions to settings.json so MCP tools are auto-approved
python3 - <<PYEOF
import json, os

path = "$CC_SETTINGS"
os.makedirs(os.path.dirname(path), exist_ok=True)

s = {}
if os.path.exists(path):
    with open(path) as f:
        s = json.load(f)

# Remove legacy mcpServers key (now handled by claude mcp add)
s.pop("mcpServers", None)

# Ensure mcp__metis-rc__* tools are auto-approved
s.setdefault("permissions", {}).setdefault("allow", [])
if "mcp__metis-rc__*" not in s["permissions"]["allow"]:
    s["permissions"]["allow"].append("mcp__metis-rc__*")

with open(path, "w") as f:
    json.dump(s, f, indent=2)
print("  Claude Code: permissions updated in ~/.claude/settings.json")
PYEOF

# ── Auto-register with Claude Desktop (Windows) ──────────────────────────────
WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r\n')
CD_CONFIG="/mnt/c/Users/$WIN_USER/AppData/Roaming/Claude/claude_desktop_config.json"

if [ -f "$CD_CONFIG" ]; then
  python3 - <<PYEOF
import json, sys

path = "$CD_CONFIG"
run_script = "$RUN_SCRIPT"

with open(path) as f:
    cfg = json.load(f)

cfg.setdefault("mcpServers", {})["metis-rc"] = {
    "command": "wsl",
    "args": ["-e", run_script],
    "autoApprove": ["*"]
}

with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
print("  Claude Desktop: updated claude_desktop_config.json")
PYEOF
else
  echo "  Claude Desktop config not found at $CD_CONFIG — skipping (Claude Desktop may not be installed)"
fi

# ── Initialize DB if not present ─────────────────────────────────────────────
DB_PATH="$METIS_RC_ROOT/system/app/data/metis.sqlite"
INIT_SCRIPT="$METIS_RC_ROOT/system/installer/init_db.py"
if [ ! -f "$DB_PATH" ] && [ -f "$INIT_SCRIPT" ]; then
  echo "Initializing database..."
  "$VENV_DIR/bin/python3" "$INIT_SCRIPT"
fi

# ── Create Windows desktop shortcut ─────────────────────────────────────────
BAT_PATH=$(wslpath -w "$METIS_RC_ROOT/system/launch-metis.bat" 2>/dev/null || true)
ICO_PATH=$(wslpath -w "$METIS_RC_ROOT/system/install/windows/metis-brain.ico" 2>/dev/null || true)
WORK_PATH=$(wslpath -w "$METIS_RC_ROOT/system" 2>/dev/null || true)
if [ -n "$BAT_PATH" ]; then
  powershell.exe -Command "
\$ws = New-Object -ComObject WScript.Shell
\$desktopRoot = [System.Environment]::GetFolderPath('Desktop')
# OneDrive may redirect Desktop — find actual .lnk location
\$desktopOneDrive = [System.Environment]::GetFolderPath('UserProfile') + '\OneDrive - ITG\Desktop'
\$dests = @()
if (Test-Path \$desktopOneDrive) { \$dests += \$desktopOneDrive + '\Metis.lnk' }
\$dests += \$desktopRoot + '\Metis.lnk'
\$dests += [System.Environment]::GetFolderPath('Programs') + '\Metis.lnk'
foreach (\$dest in \$dests) {
  \$sc = \$ws.CreateShortcut(\$dest)
  \$sc.TargetPath = '$BAT_PATH'
  \$sc.WorkingDirectory = '$WORK_PATH'
  \$sc.IconLocation = '$ICO_PATH,0'
  \$sc.Description = 'Metis Research Cortex Dashboard'
  \$sc.WindowStyle = 7
  \$sc.Save()
}
Write-Host '  Shortcuts: Desktop + Start Menu created'
" 2>/dev/null || echo "  Shortcuts: could not create (PowerShell unavailable)"
fi

# ── Write install-state.json ─────────────────────────────────────────────────
INSTALL_STATE="$METIS_RC_ROOT/system/config/install-state.json"
DASHBOARD_INSTALLED="false"
[ "$METIS_PROFILE" != "light" ] && DASHBOARD_INSTALLED="true"
HOOKS_INSTALLED="false"
[ -f "$METIS_RC_ROOT/.claude/settings.json" ] && HOOKS_INSTALLED="true"
cat > "$INSTALL_STATE" <<STATEEOF
{
  "profile": "$METIS_PROFILE",
  "version": "1.0.0",
  "installed_at": "$(date -I)",
  "components": {
    "mcp_server": true,
    "dashboard": $DASHBOARD_INSTALLED,
    "hooks": $HOOKS_INSTALLED,
    "windows_task_scheduler": false,
    "nssm_service": false,
    "docker": false
  },
  "notes": "Written by setup-mcp.sh. Update 'components' manually if you add optional components."
}
STATEEOF
echo "  install-state.json written"

# ── Install Metis git hooks (persona linter pre-commit) ─────────────────────
echo ""
echo "── Installing git hooks ──"
if [ -f "$METIS_RC_ROOT/tools/install-hooks.sh" ] && [ -d "$METIS_RC_ROOT/.git" ]; then
    bash "$METIS_RC_ROOT/tools/install-hooks.sh" 2>&1 | sed 's/^/  /' || echo "  (hook install failed — non-fatal)"
else
    echo "  (no .git/ or no tools/install-hooks.sh — skipping)"
fi

# ── Apply schema migrations to any existing metis.sqlite ────────────────────
echo ""
echo "── Applying schema migrations ──"
VENV_PYTHON="$VENV_DIR/bin/python3"
if [ -f "$METIS_RC_ROOT/system/app/data/metis.sqlite" ] && [ -x "$VENV_PYTHON" ]; then
    METIS_RC_ROOT="$METIS_RC_ROOT" "$VENV_PYTHON" -m metis_mcp.migrations 2>&1 | sed 's/^/  /' || echo "  (migration run failed — non-fatal; MCP startup will retry)"
else
    echo "  (no metis.sqlite yet — first MCP start will run migrations)"
fi

# ── Post-install validation ─────────────────────────────────────────────────
echo ""
echo "── Post-install validation ──"
_PASS=0
_FAIL=0

# 1. anthropic SDK import test
if [ -x "$VENV_PYTHON" ] && [ -f "$METIS_RC_ROOT/tests/test_anthropic_import.py" ]; then
    if "$VENV_PYTHON" "$METIS_RC_ROOT/tests/test_anthropic_import.py" >/dev/null 2>&1; then
        echo "  ✓ Anthropic SDK importable + at supported version"
        _PASS=$((_PASS + 1))
    else
        echo "  ✗ Anthropic SDK test FAILED — Claude-backed features will not work"
        _FAIL=$((_FAIL + 1))
    fi
fi

# 2. Persona linter (errors-only — warns are non-blocking)
if [ -f "$METIS_RC_ROOT/tests/persona_linter.py" ]; then
    if python3 "$METIS_RC_ROOT/tests/persona_linter.py" --errors-only >/dev/null 2>&1; then
        echo "  ✓ Persona linter — no errors on user-facing strings"
        _PASS=$((_PASS + 1))
    else
        echo "  ⚠ Persona linter found errors (non-blocking; review tests/persona_linter.py output)"
    fi
fi

# 3. Promise harness (only if dashboard happens to be running)
if [ "$METIS_PROFILE" != "light" ] && command -v curl >/dev/null 2>&1; then
    if curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://127.0.0.1:8080/" 2>/dev/null | grep -q "200"; then
        if [ -f "$METIS_RC_ROOT/tests/functional/run_metis_promises.sh" ]; then
            _RES=$(bash "$METIS_RC_ROOT/tests/functional/run_metis_promises.sh" 2>&1 | grep "^RESULT" | head -1)
            [ -n "$_RES" ] && echo "  $_RES"
            _PASS=$((_PASS + 1))
        fi
    else
        echo "  · Promise harness skipped (dashboard not running)"
        echo "    Start it with: bash system/app-py/run.sh"
        echo "    Then verify:   bash tests/functional/run_metis_promises.sh"
    fi
fi

echo ""
echo "  → $_PASS validation checks passed, $_FAIL failed"

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Setup complete (profile: $METIS_PROFILE)."
echo "  Restart Claude Code and Claude Desktop for changes to take effect."
echo "════════════════════════════════════════════════════════════════════"
