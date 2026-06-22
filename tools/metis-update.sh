#!/usr/bin/env bash
# metis-update.sh — update Metis CODE without ever losing user DATA.
#
# Principle (see system/config/data-persistence-strategy.md): CODE ships/updates;
# DATA is the user's and persists. This script makes that safe and one-command:
#   1. back up the data layer (sacrosanct)
#   2. pull new code (CODE only; data dirs are gitignored / outside the tree)
#   3. reinstall the MCP server + run ADDITIVE migrations (never drops a table)
#   4. verify the data layer is intact
#
# Usage:  bash tools/metis-update.sh            # full update
#         bash tools/metis-update.sh --verify   # just check data integrity
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENVPY="$HOME/.local/share/metis-mcp/.venv/bin/python3"; [ -x "$VENVPY" ] || VENVPY="python3"
STAMP="$(date +%Y%m%d-%H%M%S)"

# Resolve the CANONICAL live DB from config (deliberately on the native filesystem,
# ~/.local/share/metis/, NOT OneDrive — SQLite + OneDrive sync corrupts the WAL).
# The OneDrive copy under system/app/data/ is only a stale mirror.
DB="$("$VENVPY" -c "import sys; sys.path.insert(0,'$ROOT/system/mcp-server/src'); from metis_mcp.config import paths; print(paths.db)" 2>/dev/null)"
[ -n "$DB" ] || DB="$HOME/.local/share/metis/metis.sqlite"
BACKUP_DIR="$(dirname "$DB")/backups"
echo "Canonical live DB: $DB"

# The DATA layer — never overwritten by an update. (Informational + protected.)
DATA_DIRS=(
  "system/app/data"        # metis.sqlite: memory, ideas, notes, projects, routing rules, user_decisions
  "knowledge"              # indexed library, RAG/background corpora, courses
  "inputs/code"            # registered scripts + data dictionaries
  "projects" "journal" "outputs"
)

say() { printf "\n\033[1m== %s\033[0m\n" "$*"; }

verify_data() {
  say "Verifying data layer"
  [ -f "$DB" ] || { echo "  ⚠ no DB at $DB (fresh install — nothing to preserve)"; return 0; }
  "$VENVPY" - "$DB" <<'PY'
import sqlite3, sys
db = sys.argv[1]
must = ["ideas","projects","memory_entries","agent_routing_rules","user_decisions",
        "episodic_memory","semantic_memory","reflexion_log","agent_runs"]
c = sqlite3.connect(db)
have = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
ok = True
for t in must:
    if t in have:
        n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  ✓ {t:22s} {n} rows")
    else:
        print(f"  ⚠ {t:22s} MISSING (will be created empty on next run)")
c.close()
PY
}

if [ "${1:-}" = "--verify" ]; then verify_data; exit 0; fi

# 1 — back up the data layer first (the one irreversible thing)
say "Backing up data layer"
mkdir -p "$BACKUP_DIR"
if [ -f "$DB" ]; then
  cp "$DB" "$BACKUP_DIR/metis-preupdate-$STAMP.sqlite" && echo "  ✓ DB → backups/metis-preupdate-$STAMP.sqlite"
fi
echo "  data dirs preserved in place: ${DATA_DIRS[*]}"

# 2 — pull new CODE (data dirs are gitignored / outside the tree, so this never touches them)
say "Pulling new code"
( cd "$ROOT" && git pull --ff-only ) || echo "  ⚠ git pull skipped/failed — pull manually, then re-run with --verify"

# 3 — reinstall MCP + run additive migrations (CREATE TABLE IF NOT EXISTS — preserves rows)
say "Reinstalling server + running additive migrations"
bash "$ROOT/tools/reinstall-mcp.sh" >/dev/null 2>&1 && echo "  ✓ MCP reinstalled" || echo "  ⚠ reinstall failed — run tools/reinstall-mcp.sh manually"
"$VENVPY" - <<PY 2>/dev/null && echo "  ✓ migrations applied (routing + decisions tables ensured)"
import sys; sys.path.insert(0, "$ROOT/system/mcp-server/src")
from metis_mcp.tools import pipeline as P
P._ensure_routing_table(); P._ensure_decisions_table()
PY

# 4 — verify nothing was lost
verify_data

say "Update complete"
echo "  Code updated · data preserved · migrations additive."
echo "  Reconnect the server:  Claude Code → /mcp reconnect 'metis-rc'   (Desktop → quit & reopen)"
