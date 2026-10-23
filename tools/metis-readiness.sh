#!/bin/bash
# metis-readiness.sh — run tools/metis-readiness.py with the Metis venv.
# The scheduled task (tools/install-readiness-schedule.sh) calls this.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$HOME/.local/share/metis-mcp/.venv/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"
export METIS_RC_ROOT="${METIS_RC_ROOT:-$ROOT}"
exec "$PY" "$ROOT/tools/metis-readiness.py" "$@"
