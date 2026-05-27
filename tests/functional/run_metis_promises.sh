#!/usr/bin/env bash
# Metis Promise Test Harness
# ---------------------------
# Runs concrete checks against every promise in the README v1.0.
# Use it before any release, after a refactor, or when you suspect drift.
#
# Usage:
#   bash tests/functional/run_metis_promises.sh                 # full run
#   bash tests/functional/run_metis_promises.sh --tab today     # one tab
#   bash tests/functional/run_metis_promises.sh --workflows     # workflow checks only
#
# Output: a markdown report at outputs/reviews/metis-evaluation/YYYY-MM-DD_promise-check.md
#         and a one-line PASS / FAIL / WARN summary printed to stdout.

set -uo pipefail

BASE="${METIS_BASE:-http://127.0.0.1:8080}"
RC_ROOT="${METIS_RC_ROOT:-/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex}"
DATE="$(date +%Y-%m-%d)"
OUT_DIR="$RC_ROOT/outputs/reviews/metis-evaluation"
OUT_FILE="$OUT_DIR/${DATE}_promise-check.md"
mkdir -p "$OUT_DIR"

PASS=0; FAIL=0; WARN=0
RESULTS=()

log() {
  local status="$1"; shift
  local msg="$*"
  case "$status" in
    PASS) PASS=$((PASS+1)); RESULTS+=("| ✅ PASS | $msg |") ;;
    FAIL) FAIL=$((FAIL+1)); RESULTS+=("| 🔴 FAIL | $msg |") ;;
    WARN) WARN=$((WARN+1)); RESULTS+=("| 🟡 WARN | $msg |") ;;
  esac
  echo "[$status] $msg"
}

check_endpoint() {
  local label="$1" path="$2" expected="${3:-200}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path" --max-time 10 || echo "000")
  if [[ "$code" == "$expected" ]]; then
    log PASS "$label → $path ($code)"
  elif [[ "$code" == "000" ]]; then
    log FAIL "$label → $path UNREACHABLE"
  else
    log FAIL "$label → $path expected $expected got $code"
  fi
}

check_endpoint_post() {
  local label="$1" path="$2" body="$3" expected="${4:-200}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$body" "$BASE$path" --max-time 10 || echo "000")
  if [[ "$code" == "$expected" ]]; then
    log PASS "$label → POST $path ($code)"
  else
    log FAIL "$label → POST $path expected $expected got $code"
  fi
}

check_db_table() {
  local label="$1" table="$2" min_rows="${3:-0}"
  local db="$RC_ROOT/system/app/data/metis.sqlite"
  if [[ ! -f "$db" ]]; then
    log FAIL "$label → DB file missing at $db"; return
  fi
  local count
  count=$(python3 -c "
import sqlite3, sys
try:
    c = sqlite3.connect('$db')
    n = c.execute('SELECT COUNT(*) FROM $table').fetchone()[0]
    print(n)
except Exception as e:
    print('ERR', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo "ERR")
  if [[ "$count" == "ERR" ]]; then
    log FAIL "$label → table $table missing or unreadable"
  elif (( count >= min_rows )); then
    log PASS "$label → $table has $count rows (≥ $min_rows)"
  else
    log WARN "$label → $table has $count rows (< $min_rows)"
  fi
}

check_file_exists() {
  local label="$1" path="$2"
  if [[ -e "$RC_ROOT/$path" ]]; then
    log PASS "$label → $path"
  else
    log FAIL "$label → $path MISSING"
  fi
}

section() {
  echo ""
  echo "=== $1 ==="
  RESULTS+=("")
  RESULTS+=("## $1")
  RESULTS+=("")
  RESULTS+=("| Status | Check |")
  RESULTS+=("|---|---|")
}

# ============================================================================
# Section 1 — Server reachability
# ============================================================================
section "Server reachability"
check_endpoint "Root page" "/"
check_endpoint "Health" "/health" 200

# ============================================================================
# Section 2 — 9 dashboard tabs
# ============================================================================
section "9 dashboard tabs"
check_endpoint "Today tab"     "/today"
check_endpoint "Knowledge tab" "/knowledge"
check_endpoint "Meetings tab"  "/meetings"
check_endpoint "Learning tab"  "/learning"
check_endpoint "Work tab"      "/work"
check_endpoint "Thinking tab"  "/thinking"
check_endpoint "Planner tab"   "/planner"
check_endpoint "Teach tab"     "/teach"
check_endpoint "Metis tab"     "/metis"

# ============================================================================
# Section 3 — Promised HTMX partials
# ============================================================================
section "Promised partials (from README features)"
check_endpoint "Welcome banner partial"        "/api/partial/welcome-banner"
check_endpoint "Today ledger"                  "/api/partial/today/ledger"
check_endpoint "Morning brief"                 "/api/partial/today/morning-brief"
check_endpoint "Knowledge coverage gap"        "/api/partial/knowledge/coverage-gap"
check_endpoint "Knowledge graph view"          "/api/partial/knowledge/graph"
check_endpoint "Meetings live-assist pane"     "/api/partial/meetings/live-assist"
check_endpoint "Thinking brainstorm launcher"  "/api/partial/thinking/brainstorm"
check_endpoint "Teach gap analysis"            "/api/partial/teach/gap-analysis"
check_endpoint "Teach Q-bank"                  "/api/partial/teach/qbank"
check_endpoint "Learning competency map"       "/api/partial/learning/competencies"
check_endpoint "Learning velocity"             "/api/partial/learning/velocity"
check_endpoint "Planner research timeline"     "/api/partial/planner/timeline"
check_endpoint "Planner focus board"           "/api/partial/planner/focus-board"

# ============================================================================
# Section 4 — Cross-pollination (live meeting + ideas)
# ============================================================================
section "Cross-pollination workflow"
check_endpoint_post "Meeting live-connections" "/api/meeting/live-connections" '{"text":"HAT surveillance passive screening DRC"}'

# ============================================================================
# Section 5 — Database health
# ============================================================================
section "Database health — promised tables"
check_db_table "Agent runs table"     "agent_runs"            1
check_db_table "Reflexion log"        "reflexion_log"         0
check_db_table "Self-improvement proposals" "self_improvement_proposals" 0
check_db_table "User config"          "user_config"           1
check_db_table "Ideas"                "ideas"                 0
check_db_table "Literature metadata"  "literature_metadata"   1
check_db_table "Meetings"             "meetings"              0
check_db_table "News briefs"          "news_briefs"           0
check_db_table "Projects"             "projects"              1
check_db_table "Learning courses"     "learning_courses"      0
check_db_table "Episodic memory"      "episodic_memory"       0
check_db_table "Semantic memory"      "semantic_memory"       0
check_db_table "Working memory"       "working_memory"        0

# ============================================================================
# Section 6 — Files that MUST exist
# ============================================================================
section "Core files present"
check_file_exists "README"                       "README.md"
check_file_exists "CLAUDE.md operating rules"    "CLAUDE.md"
check_file_exists "Persona contract"             "system/config/metis-persona.md"
check_file_exists "Constitution"                 "system/config/constitution.md"
check_file_exists "Red lines"                    "system/config/red-lines.md"
check_file_exists "Feature backlog"              "system/config/feature-backlog.md"
check_file_exists "RAG routing rules"            "system/config/rag-routing-rules.md"
check_file_exists "Self-reflexion prompt"        "system/config/metis-self-reflexion-prompt.md"
check_file_exists "Metis skill"                  ".claude/skills/metis/skill.md"
check_file_exists "Epidemiologist agent"         "agents/epidemiologist/skill.md"
check_file_exists "Librarian agent"              "agents/librarian/skill.md"
check_file_exists "MCP server entry"             "system/mcp-server/src/metis_mcp/server.py"
check_file_exists "FastAPI dashboard entry"      "system/app-py/main.py"

# ============================================================================
# Section 7 — MCP tool registration
# ============================================================================
section "MCP tools surfaced"
TOOLS_DIR="$RC_ROOT/system/mcp-server/src/metis_mcp/tools"
if [[ -d "$TOOLS_DIR" ]]; then
  tool_count=$(find "$TOOLS_DIR" -name "*.py" -not -name "__*" | wc -l)
  if (( tool_count >= 30 )); then
    log PASS "MCP tools directory has $tool_count modules (README promises 76+ tools across modules)"
  else
    log WARN "MCP tools directory only $tool_count modules"
  fi
else
  log FAIL "MCP tools directory missing"
fi

# ============================================================================
# Section 8 — Recent activity (drift indicator)
# ============================================================================
section "Recent activity — drift check"
db="$RC_ROOT/system/app/data/metis.sqlite"
if [[ -f "$db" ]]; then
  for tbl in agent_runs reflexion_log episodic_memory ideas meetings; do
    recent=$(python3 -c "
import sqlite3
try:
    c = sqlite3.connect('$db')
    # detect timestamp column
    cols = [r[1] for r in c.execute('PRAGMA table_info($tbl)').fetchall()]
    ts = 'created_at' if 'created_at' in cols else ('ts' if 'ts' in cols else ('timestamp' if 'timestamp' in cols else None))
    if ts is None:
        print(0); raise SystemExit
    n = c.execute(f\"SELECT COUNT(*) FROM $tbl WHERE {ts} >= datetime('now','-30 days')\").fetchone()[0]
    print(n)
except Exception:
    print(0)
" 2>/dev/null || echo "0")
    if (( recent > 0 )); then
      log PASS "$tbl has $recent rows in last 30d"
    else
      log WARN "$tbl has NO activity in last 30d — possibly unused"
    fi
  done
fi

# ============================================================================
# Section 9 — Agent contract check (structural integrity + run coverage)
# ============================================================================
section "Agent contract check"
contract_script="$RC_ROOT/tests/functional/test_agent_contracts.py"
if [[ ! -f "$contract_script" ]]; then
  log WARN "Agent contract test not found at $contract_script"
else
  # Parse JSON output from the contract test so we can fold results into the harness
  contract_json=$(python3 "$contract_script" --json 2>/dev/null)
  if [[ -z "$contract_json" ]]; then
    log WARN "Agent contract test returned no output (registry missing?)"
  else
    total_agents=$(echo "$contract_json" | python3 -c "import sys,json; a=json.load(sys.stdin); print(len(a))")
    fail_agents=$(echo "$contract_json" | python3 -c "import sys,json; a=json.load(sys.stdin); print(sum(1 for r in a if r['status']=='FAIL' and not r['retired']))")
    warn_agents=$(echo "$contract_json" | python3 -c "import sys,json; a=json.load(sys.stdin); print(sum(1 for r in a if r['status']=='WARN' and not r['retired']))")
    pass_agents=$(echo "$contract_json" | python3 -c "import sys,json; a=json.load(sys.stdin); print(sum(1 for r in a if r['status']=='PASS' and not r['retired']))")
    never_run=$(echo "$contract_json" | python3 -c "import sys,json; a=json.load(sys.stdin); print(sum(1 for r in a if not r['retired'] and r['run_count']==0))")
    active_agents=$(echo "$contract_json" | python3 -c "import sys,json; a=json.load(sys.stdin); print(sum(1 for r in a if not r['retired']))")

    if (( fail_agents > 0 )); then
      # Report each failing agent individually
      echo "$contract_json" | python3 -c "
import sys, json
agents = json.load(sys.stdin)
for a in agents:
    if a['status'] == 'FAIL' and not a['retired']:
        for level, msg in a['issues']:
            if level == 'FAIL':
                print(f\"FAIL:/{a['slug']}: {msg}\")
" | while IFS= read -r line; do
        log FAIL "${line#FAIL:}"
      done
    fi

    if (( pass_agents > 0 )); then
      log PASS "$pass_agents/$active_agents active agents pass all contract checks"
    fi

    if (( warn_agents > 0 )); then
      log WARN "$warn_agents active agent(s) have warnings (model missing / never run / stale)"
    fi

    # Run coverage — separate signal from structural issues
    if (( never_run == 0 )); then
      log PASS "Agent run coverage: all $active_agents active agents have been invoked at least once"
    elif (( never_run == active_agents )); then
      log FAIL "Agent run coverage: 0/$active_agents agents have ever run — routing is broken or agents have never been used"
    else
      invoked=$(( active_agents - never_run ))
      pct=$(( invoked * 100 / active_agents ))
      log WARN "Agent run coverage: $invoked/$active_agents agents invoked ($pct%) — $never_run have never run"
    fi
  fi
fi

# ============================================================================
# Render report
# ============================================================================
TOTAL=$((PASS+FAIL+WARN))
{
  echo "# Metis Promise Check — $DATE"
  echo ""
  echo "**Base URL:** $BASE"
  echo "**Total checks:** $TOTAL · ✅ $PASS · 🔴 $FAIL · 🟡 $WARN"
  echo ""
  printf '%s\n' "${RESULTS[@]}"
  echo ""
  echo "---"
  echo ""
  echo "Re-run: \`bash tests/functional/run_metis_promises.sh\`"
} > "$OUT_FILE"

echo ""
echo "=========================================="
echo "RESULT — ✅ $PASS · 🔴 $FAIL · 🟡 $WARN  (out of $TOTAL)"
echo "Report written to: $OUT_FILE"
echo "=========================================="

# Exit non-zero if any failures
if (( FAIL > 0 )); then
  exit 1
fi
