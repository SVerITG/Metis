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

# ── Prerequisites: ensure curl and python3 are available ─────────────────────
_need_curl=0
_need_python=0
command -v curl    >/dev/null 2>&1 || _need_curl=1
command -v python3 >/dev/null 2>&1 || _need_python=1

if [ "$_need_curl" = "1" ] || [ "$_need_python" = "1" ]; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "Installing prerequisites (curl, python3)…"
    PKGS=""
    [ "$_need_curl"   = "1" ] && PKGS="$PKGS curl"
    [ "$_need_python" = "1" ] && PKGS="$PKGS python3 python3-pip"
    if [ "$(id -u)" = "0" ]; then
      apt-get update -qq && apt-get install -y $PKGS
    else
      sudo apt-get update -qq && sudo apt-get install -y $PKGS
    fi
  elif command -v brew >/dev/null 2>&1; then
    echo "Installing prerequisites via Homebrew…"
    [ "$_need_curl"   = "1" ] && brew install curl
    [ "$_need_python" = "1" ] && brew install python3
  else
    echo "ERROR: curl and/or python3 are missing and no package manager was found."
    echo ""
    echo "  Ubuntu/Debian:  sudo apt-get install -y curl python3"
    echo "  macOS:          brew install python3   (see https://brew.sh)"
    echo "  Other:          install curl and python3 from your distro's package manager"
    exit 1
  fi
fi
unset _need_curl _need_python

# ── Install profile ──────────────────────────────────────────────────────────
# Researcher path (interactive, no METIS_PROFILE set): 2 choices + demo option.
# Developer override via environment:
#   METIS_PROFILE=light    bash setup-mcp.sh   — MCP server only (~5 min)
#   METIS_PROFILE=standard bash setup-mcp.sh   — MCP + dashboard (~15 min)
#   METIS_PROFILE=full     bash setup-mcp.sh   — standard + scheduler (~25 min)
METIS_PROFILE="${METIS_PROFILE:-}"
SEED_DEMO=0

if [ -z "$METIS_PROFILE" ] && [ -t 0 ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Welcome to Metis"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "  What would you like to install?"
  echo ""
  echo "  [1]  Full — AI assistant + research dashboard  (RECOMMENDED)"
  echo "       About 15 minutes. Complete Metis: Claude AI with tools"
  echo "       and the 9-tab research dashboard."
  echo ""
  echo "  [2]  AI only — no dashboard"
  echo "       About 5 minutes. Just the AI with Metis tools."
  echo "       You can add the dashboard later."
  echo ""
  echo "  [D]  Developer — show all install options"
  echo ""
  read -rp "  Choose [1/2/D, Enter for Full]: " PROFILE_CHOICE
  case "$PROFILE_CHOICE" in
    2) METIS_PROFILE="light" ;;
    [Dd]*)
      echo ""
      echo "  Developer options:"
      echo "  [L] light    — MCP server only (~5 min)"
      echo "  [S] standard — MCP server + dashboard (~15 min)  [DEFAULT]"
      echo "  [F] full     — Standard + Windows Task Scheduler (~25 min)"
      echo ""
      read -rp "  Choose [L/S/F, Enter for standard]: " DEV_CHOICE
      case "$DEV_CHOICE" in
        [Ll]) METIS_PROFILE="light" ;;
        [Ff]) METIS_PROFILE="full" ;;
        *)    METIS_PROFILE="standard" ;;
      esac
      ;;
    *) METIS_PROFILE="standard" ;;
  esac

  # ── Demo workspace (standard/full only) ──────────────────────────────────
  SEED_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/system/install/seed_ph_database.py"
  if [ "$METIS_PROFILE" != "light" ] && [ -f "$SEED_SCRIPT" ]; then
    echo ""
    echo "  Start with a demo workspace?"
    echo "  Pre-loads example projects, meetings, literature, and tasks so you"
    echo "  can explore every feature right away. You can clear it at any time."
    echo ""
    read -rp "  Load demo content? [Y/n]: " DEMO_CHOICE
    if [ "$DEMO_CHOICE" != "n" ] && [ "$DEMO_CHOICE" != "N" ]; then
      SEED_DEMO=1
    fi
  fi

elif [ -z "$METIS_PROFILE" ]; then
  METIS_PROFILE="standard"
fi

echo "Installing Metis with profile: $METIS_PROFILE"

# ── Config ──────────────────────────────────────────────────────────────────
VENV_DIR="$HOME/.local/share/metis-mcp/.venv"
RUN_SCRIPT="$HOME/.local/share/metis-mcp/run.sh"
LOCAL_SRC="$HOME/.local/share/metis-mcp/src-install"

# _CODE_ROOT: where the Metis source lives — always derived from script location.
# METIS_RC_ROOT: where user config and data live — can be overridden by env var
#   (e.g. Docker containers set METIS_RC_ROOT=/opt/metis-data to keep data
#   separate from the read-only code mount at /opt/metis).
_CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
METIS_RC_ROOT="${METIS_RC_ROOT:-$_CODE_ROOT}"
SRC_DIR="$_CODE_ROOT/system/mcp-server"

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
  # Fallback: system Python + venv (uv unavailable).
  # Pick a Python in the SUPPORTED range (3.10–3.13) that can actually create a
  # venv. Newer Pythons (3.14+) lack prebuilt wheels for onnxruntime/sqlite-vec/
  # tokenizers and a bare system 3.14 often has no ensurepip, which otherwise
  # fails later with a cryptic "ensurepip is not available" and no guidance.
  PYTHON=""
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    VER=$("$candidate" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null) || continue
    MAJOR=${VER%%.*}; MINOR=${VER#*.}
    if [ "$MAJOR" = "3" ] && [ "$MINOR" -ge 10 ] && [ "$MINOR" -lt 14 ]; then
      # Must be able to bootstrap pip into a venv.
      if "$candidate" -c "import ensurepip" >/dev/null 2>&1; then
        PYTHON="$candidate"; break
      fi
    fi
  done
  if [ -z "$PYTHON" ]; then
    _sys_py="$(command -v python3 >/dev/null 2>&1 && python3 --version 2>&1 || echo 'not found')"
    echo ""
    echo "ERROR: No usable Python found for the fallback installer."
    echo "Metis needs Python 3.10–3.13 that can create a virtual environment."
    echo "Your default python3 is: ${_sys_py}"
    echo ""
    echo "Fix any one of these, then re-run this script:"
    echo "  • Install uv (recommended — downloads its own Python 3.12, no sudo):"
    echo "      curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  • Or install the venv package:   sudo apt install python3-venv"
    echo "  • Or install Python 3.12:        sudo apt install python3.12 python3.12-venv"
    exit 1
  fi
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
# Install WITH the [embedding] and [library] extras so the knowledge layer works
# out of the box: fastembed (semantic search / RAG — required) and paper-qa
# (ask_library). PyMuPDF + pdfminer come from core deps. Without [embedding], all
# semantic search is silently disabled — so it is installed by default here.
if [ "$USE_UV" = "1" ]; then
  [ -f "$LOCAL_SRC/requirements.txt" ] && "$UV" pip install --python "$VENV_DIR/bin/python3" -r "$LOCAL_SRC/requirements.txt"
  echo "Installing metis-mcp-server package (with embedding + library extras)..."
  "$UV" pip install --python "$VENV_DIR/bin/python3" "$LOCAL_SRC[embedding,library,ocr]" \
    || "$UV" pip install --python "$VENV_DIR/bin/python3" "$LOCAL_SRC"
else
  [ -f "$LOCAL_SRC/requirements.txt" ] && "$VENV_DIR/bin/pip" install -r "$LOCAL_SRC/requirements.txt"
  echo "Installing metis-mcp-server package (with embedding + library extras)..."
  "$VENV_DIR/bin/pip" install "$LOCAL_SRC[embedding,library,ocr]" \
    || "$VENV_DIR/bin/pip" install "$LOCAL_SRC"
fi

# ── OCR system binary (Tesseract) — fallback for image-only / scanned PDFs ────
# The Python wrapper (pytesseract) ships via the [ocr] extra above; OCR also needs
# the Tesseract binary. Best-effort install — image-only PDFs simply index as
# text-layer-only (no OCR) if it isn't present. Especially valuable for the
# Background Maker, which scrapes heterogeneous web PDFs.
if ! command -v tesseract >/dev/null 2>&1; then
  echo "Installing Tesseract OCR (for scanned-PDF extraction)…"
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y tesseract-ocr >/dev/null 2>&1 || echo "  (skip) install manually: sudo apt install tesseract-ocr"
  elif command -v brew >/dev/null 2>&1; then
    brew install tesseract >/dev/null 2>&1 || echo "  (skip) install manually: brew install tesseract"
  else
    echo "  (skip) Tesseract not found — install it to enable OCR on scanned PDFs."
  fi
fi

# If a transitive dependency pulled in GPU torch, swap it for the CPU-only build.
# CPU torch is ~200 MB vs ~2 GB for CUDA — researchers don't need GPU acceleration.
if "$VENV_DIR/bin/python3" -c "import torch" 2>/dev/null; then
  echo "Replacing GPU torch with CPU-only build (~200 MB)..."
  if [ "$USE_UV" = "1" ]; then
    "$UV" pip install --python "$VENV_DIR/bin/python3" \
      --index-url https://download.pytorch.org/whl/cpu torch
  else
    "$VENV_DIR/bin/pip" install \
      --index-url https://download.pytorch.org/whl/cpu torch
  fi
fi
echo "  MCP server installed"

# ── Install dashboard (app-py) dependencies into same venv ───────────────────
# Skipped on 'light' profile — dashboard not included.
if [ "$METIS_PROFILE" != "light" ]; then
  APP_REQ="$_CODE_ROOT/system/app-py/requirements.txt"
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
# Per-agent subset mechanism (only filters when METIS_AGENT_SUBSET is also set).
export METIS_TOOL_SUBSETS=1
# Progressive tool disclosure: load only the ~80 everyday 'core' tools; the rest
# are retrieved on demand via find_tools()/load_tool_group(). Cuts the loaded
# toolset ~60% with nothing made unreachable. Set to 0 to load all tools.
export METIS_TOOL_SEARCH=1

# Corporate proxy SSL fix: point Python's httpx/requests at the system CA bundle
# (includes institutional root CAs like ITG's pa-ca.itg.be) so HuggingFace model
# downloads and other HTTPS calls succeed behind intercepting proxies.
_SYS_CA="/etc/ssl/certs/ca-certificates.crt"
if [ -f "\$_SYS_CA" ]; then
    export SSL_CERT_FILE="\$_SYS_CA"
    export REQUESTS_CA_BUNDLE="\$_SYS_CA"
fi

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

# ── Install Claude Code CLI if missing ──────────────────────────────────────
if ! command -v claude >/dev/null 2>&1; then
  echo ""
  echo "── Installing Claude Code CLI ──"
  _installed_node=0

  # Ensure Node.js / npm is available
  if ! command -v npm >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
      echo "  Installing Node.js (LTS)..."
      if [ "$(id -u)" = "0" ]; then
        curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - 2>/dev/null
        apt-get install -y nodejs 2>/dev/null && _installed_node=1
      else
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo bash - 2>/dev/null
        sudo apt-get install -y nodejs 2>/dev/null && _installed_node=1
      fi
    elif command -v brew >/dev/null 2>&1; then
      brew install node 2>/dev/null && _installed_node=1
    fi
  else
    _installed_node=1
  fi

  if [ "$_installed_node" = "1" ] && command -v npm >/dev/null 2>&1; then
    echo "  Installing Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code 2>&1 | sed 's/^/    /' \
      && echo "  Claude Code CLI installed" \
      || echo "  npm install failed — install manually: npm install -g @anthropic-ai/claude-code"
  else
    echo "  Node.js not found — install Claude Code CLI manually:"
    echo "  https://docs.anthropic.com/en/docs/claude-code/getting-started"
  fi
  unset _installed_node
fi

# ── Install Claude Desktop if missing (macOS only) ──────────────────────────
_OS="$(uname -s)"
if [ "$_OS" = "Darwin" ] && [ ! -d "/Applications/Claude.app" ]; then
  echo ""
  echo "── Claude Desktop ──"
  if command -v brew >/dev/null 2>&1; then
    echo "  Installing Claude Desktop via Homebrew..."
    brew install --cask claude 2>&1 | sed 's/^/  /' \
      || echo "  Homebrew install failed. Download from: https://claude.ai/download"
  else
    echo "  Download Claude Desktop from: https://claude.ai/download"
    echo "  (install Homebrew first for automatic install: https://brew.sh)"
  fi
elif [ "$_OS" = "Linux" ] && grep -qi microsoft /proc/version 2>/dev/null && [ ! -f "/.dockerenv" ]; then
  # WSL: Claude Desktop is a Windows app — check for it on the Windows side
  _WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r\n')
  _CD_EXE="/mnt/c/Users/$_WIN_USER/AppData/Local/AnthropicClaude/claude.exe"
  _CD_EXE2="/mnt/c/Program Files/Anthropic/Claude/Claude.exe"
  if [ ! -f "$_CD_EXE" ] && [ ! -f "$_CD_EXE2" ]; then
    echo ""
    echo "── Claude Desktop ──"
    echo "  Claude Desktop is not installed on this Windows machine."
    echo "  Download from: https://claude.ai/download"
    echo "  Metis connects to Claude Desktop automatically after install."
  fi
  unset _WIN_USER _CD_EXE _CD_EXE2
fi
unset _OS

# ── Auto-register with Claude Code ──────────────────────────────────────────
# Claude Code stores MCP servers in ~/.claude.json (per-project) via `claude mcp add`.
# ~/.claude/settings.json is used only for permissions (tool auto-approval).
CC_SETTINGS="$HOME/.claude/settings.json"
mkdir -p "$HOME/.claude"

# Register the server via the CLI (writes to ~/.claude.json for this project)
if command -v claude >/dev/null 2>&1; then
  # Remove old registration first to avoid duplicates, then re-add
  claude mcp remove metis-rc >/dev/null 2>&1 || true
  if claude mcp add metis-rc "$RUN_SCRIPT" >/dev/null 2>&1; then
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

# ── Auto-register with Claude Desktop (Windows/WSL only — skipped in Docker) ─
[ -f "/.dockerenv" ] && WIN_USER="" || WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r\n')
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

# ── Create Windows desktop shortcut (WSL only — skipped inside Docker) ──────
[ -f "/.dockerenv" ] && BAT_PATH="" || BAT_PATH=$(wslpath -w "$METIS_RC_ROOT/system/launch-metis.bat" 2>/dev/null || true)
ICO_PATH=$(wslpath -w "$METIS_RC_ROOT/system/install/windows/metis-brain.ico" 2>/dev/null || true)
WORK_PATH=$(wslpath -w "$METIS_RC_ROOT/system" 2>/dev/null || true)
if [ -n "$BAT_PATH" ]; then
  powershell.exe -Command "
\$ws = New-Object -ComObject WScript.Shell
\$desktopRoot = [System.Environment]::GetFolderPath('Desktop')
\$userProfile = [System.Environment]::GetFolderPath('UserProfile')
\$dests = @()
# OneDrive may redirect Desktop — scan all OneDrive* folders under UserProfile
Get-ChildItem \$userProfile -Directory -Filter 'OneDrive*' -ErrorAction SilentlyContinue | ForEach-Object {
  \$od = \$_.FullName + '\Desktop'
  if (Test-Path \$od) { \$dests += \$od + '\Metis.lnk' }
}
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

# ── Write first-run marker (triggers config wizard on first Claude Code open) ─
mkdir -p "$METIS_RC_ROOT/system/config"
touch "$METIS_RC_ROOT/system/config/.first-run"
echo "  First-run marker written — config wizard will start on next Claude Code open"

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

# ── Seed demo workspace if requested ─────────────────────────────────────────
if [ "$SEED_DEMO" = "1" ]; then
  SEED_SCRIPT_PATH="$_CODE_ROOT/system/install/seed_ph_database.py"
  DB_PATH="$METIS_RC_ROOT/system/app/data/metis.sqlite"
  echo ""
  echo "── Loading demo workspace ──"
  if [ -f "$SEED_SCRIPT_PATH" ]; then
    if "$VENV_DIR/bin/python3" "$SEED_SCRIPT_PATH" --db "$DB_PATH" --quiet 2>&1 | sed 's/^/  /'; then
      echo "  Demo workspace loaded"
    else
      echo "  Demo seed encountered an issue — non-fatal, continuing"
    fi
  else
    echo "  seed_ph_database.py not found — skipping demo seed"
  fi
fi

# ── Install Metis git hooks (persona linter pre-commit) ─────────────────────
echo ""
echo "── Installing git hooks ──"
if [ -f "$_CODE_ROOT/tools/install-hooks.sh" ] && [ -d "$_CODE_ROOT/.git" ]; then
    bash "$_CODE_ROOT/tools/install-hooks.sh" 2>&1 | sed 's/^/  /' || echo "  (hook install failed — non-fatal)"
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

# 0. MCP server smoke test — the authoritative "does the server actually work" check
if [ -f "$_CODE_ROOT/tools/test-mcp.sh" ]; then
    if METIS_RC_ROOT="$METIS_RC_ROOT" bash "$_CODE_ROOT/tools/test-mcp.sh" >/tmp/metis-mcp-smoke.log 2>&1; then
        echo "  ✓ MCP server smoke test: HEALTHY ($(grep -c '✓' /tmp/metis-mcp-smoke.log) checks)"
        _PASS=$((_PASS + 1))
    else
        echo "  ✗ MCP server smoke test FAILED — see /tmp/metis-mcp-smoke.log"
        grep '✗' /tmp/metis-mcp-smoke.log | sed 's/^/      /'
        _FAIL=$((_FAIL + 1))
    fi
fi

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
# ── Run setup wizard ─────────────────────────────────────────────────────────
# Always run the terminal wizard unless already configured.
# For full installs, the dashboard wizard is a second path (first-visit banner);
# the terminal wizard runs first so Metis is configured before anything opens.
WIZARD_SCRIPT="$_CODE_ROOT/system/install/terminal_wizard.py"
USER_CONFIG="$METIS_RC_ROOT/system/config/user-config.yaml"

if [ -f "$WIZARD_SCRIPT" ] && [ ! -f "$USER_CONFIG" ]; then
  echo ""
  "$VENV_DIR/bin/python3" "$WIZARD_SCRIPT" \
    --metis-root "$METIS_RC_ROOT" \
    --skip-if-configured \
    ${ANTHROPIC_API_KEY:+--api-key "$ANTHROPIC_API_KEY"}
  if [ "$METIS_PROFILE" != "light" ]; then
    echo ""
    echo "  Dashboard also available: bash system/app-py/run.sh"
    echo "  Then open: http://localhost:8080"
  fi
else
  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo "  Metis installed successfully."
  echo "  Open Claude Code in this folder to start."
  echo "  Run /metis_config to personalise Metis to your work."
  echo "════════════════════════════════════════════════════════════════════"
fi
