#!/usr/bin/env bash
# _common.sh — shared install functions for all Metis Linux setup scripts
# Sourced by setup-full.sh, setup-standard.sh, setup-minimal.sh

PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=10

check_python() {
  local py
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
      py="$candidate"
      break
    fi
  done
  if [[ -z "${py:-}" ]]; then
    echo "✗ Python 3.10+ not found. Install it and re-run."
    exit 1
  fi
  local ver
  ver=$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  local major minor
  major="${ver%%.*}"
  minor="${ver#*.}"
  if (( major < PYTHON_MIN_MAJOR || (major == PYTHON_MIN_MAJOR && minor < PYTHON_MIN_MINOR) )); then
    echo "✗ Python $ver found but $PYTHON_MIN_MAJOR.$PYTHON_MIN_MINOR+ required."
    exit 1
  fi
  echo "✓ Python $ver ($py)"
  export METIS_PYTHON="$py"
}

create_install_dir() {
  local dir="$1"
  mkdir -p "$dir"/{journal,inbox,inputs/meetings,inputs/literature,outputs/reviews,archive}
  mkdir -p "$dir"/system/{config,app/data}
  echo "✓ Install directory: $dir"
}

copy_core_files() {
  local repo="$1" dest="$2"
  cp -r "$repo/agents/"         "$dest/agents/"
  cp -r "$repo/.claude/"        "$dest/.claude/"
  cp -r "$repo/system/config/"  "$dest/system/config/" 2>/dev/null || true
  cp -r "$repo/system/mcp-server/" "$dest/system/mcp-server/"
  cp -r "$repo/knowledge/library/"     "$dest/knowledge/library/"   2>/dev/null || true
  cp -r "$repo/knowledge/course-template/" "$dest/knowledge/course-template/" 2>/dev/null || true
  echo "✓ Core files copied"
}

copy_dashboard() {
  local repo="$1" dest="$2"
  rsync -a --exclude="*.pyc" --exclude="__pycache__" \
        --exclude=".venv*"   --exclude="*.sqlite" \
        "$repo/system/app-py/" "$dest/system/app-py/"
  echo "✓ Dashboard files copied"
}

copy_courses() {
  local repo="$1" dest="$2"
  mkdir -p "$dest/knowledge/courses"
  if [[ -d "$repo/knowledge/courses/biostatistics" ]]; then
    cp -r "$repo/knowledge/courses/biostatistics/" \
          "$dest/knowledge/courses/biostatistics/"
    echo "✓ Biostatistics course copied (12 lessons)"
  fi
}

create_venv() {
  local dest="$1"
  local venv="$dest/system/mcp-server/.venv"
  echo "  Creating Python venv…"
  "$METIS_PYTHON" -m venv "$venv"
  "$venv/bin/pip" install --quiet --upgrade pip
  "$venv/bin/pip" install --quiet \
    "mcp>=1.0" "fastapi>=0.111" "uvicorn[standard]>=0.29" \
    "anthropic>=0.25" "apscheduler>=3.10" "pyyaml>=6.0" \
    "httpx>=0.27" "watchdog>=4.0" "aiofiles>=23.0" \
    "jinja2>=3.1" "python-multipart>=0.0.9" "requests>=2.31"
  # Install MCP server package in editable mode
  if [[ -f "$dest/system/mcp-server/pyproject.toml" ]]; then
    "$venv/bin/pip" install --quiet -e "$dest/system/mcp-server/"
  fi
  echo "✓ Python environment ready"
}

init_database() {
  local dest="$1"
  local db="$dest/system/app/data/metis.sqlite"
  mkdir -p "$(dirname "$db")"
  if [[ -f "$dest/system/installer/schema.sql" ]]; then
    "$METIS_PYTHON" -c "
import sqlite3, pathlib
db = sqlite3.connect('$db')
db.executescript(pathlib.Path('$dest/system/installer/schema.sql').read_text())
db.commit(); db.close()
print('  Database initialised')
"
  elif [[ -f "$dest/system/mcp-server/.venv/bin/python" ]]; then
    "$dest/system/mcp-server/.venv/bin/python" \
      "$dest/system/install/seed_epi_base.py" \
      --db "$db" --schema-only --quiet 2>/dev/null || true
  fi
  echo "✓ Database initialised: $db"
}

seed_epi_base() {
  local dest="$1"
  local db="$dest/system/app/data/metis.sqlite"
  if [[ -f "$dest/system/install/seed_epi_base.py" ]]; then
    "$METIS_PYTHON" "$dest/system/install/seed_epi_base.py" \
      --db "$db" --quiet
    echo "✓ Biostatistics course seeded"
  fi
}

configure_mcp() {
  local dest="$1" api_key="$2"
  # Claude Desktop config path varies by OS
  local claude_cfg=""
  if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
    claude_cfg="${APPDATA:-}/Claude/claude_desktop_config.json"
    # WSL: write to Windows AppData
    if [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
      claude_cfg="$(wslpath -u "$(cmd.exe /c echo %APPDATA% 2>/dev/null | tr -d '\r')")/Claude/claude_desktop_config.json"
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    claude_cfg="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
  fi

  if [[ -z "$claude_cfg" ]] || [[ ! -d "$(dirname "$claude_cfg")" ]]; then
    echo "  (Skipping Claude Desktop MCP config — path not found)"
    echo "  Manually add MCP server: $dest/system/mcp-server/"
    return
  fi

  local run_sh="$dest/system/mcp-server/run.sh"
  cat > "$run_sh" <<EOF
#!/usr/bin/env bash
export METIS_RC_ROOT="$dest"
export PYTHONPATH="$dest/system/mcp-server/src"
exec "$dest/system/mcp-server/.venv/bin/python" -m metis_mcp.server "\$@"
EOF
  chmod +x "$run_sh"
  echo "✓ MCP run script: $run_sh"
}

write_env_file() {
  local dest="$1" api_key="$2"
  cat > "$dest/system/.env" <<EOF
ANTHROPIC_API_KEY=${api_key}
METIS_RC_ROOT=${dest}
EOF
  echo "✓ Environment config: $dest/system/.env"
}

write_launcher() {
  local dest="$1" type="$2"
  local launcher="$dest/start.sh"
  cat > "$launcher" <<EOF
#!/usr/bin/env bash
# Metis Research Cortex — start script ($type install)
export METIS_RC_ROOT="$dest"
export PYTHONPATH="$dest/system/mcp-server/src:$dest/system/app-py"
set -a; source "$dest/system/.env" 2>/dev/null || true; set +a

EOF
  if [[ "$type" != "minimal" ]]; then
    cat >> "$launcher" <<EOF
echo "Starting Metis dashboard on http://localhost:8080 …"
cd "$dest/system/app-py"
exec "$dest/system/mcp-server/.venv/bin/uvicorn" main:app \
     --host 0.0.0.0 --port 8080 --reload
EOF
  else
    cat >> "$launcher" <<EOF
echo "Starting Metis MCP server (stdio) …"
exec "$dest/system/mcp-server/.venv/bin/python" -m metis_mcp.server
EOF
  fi
  chmod +x "$launcher"
  echo "✓ Launcher: $launcher"
}
