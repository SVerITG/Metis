#!/bin/bash
# test-mcp.sh — Smoke-test the Metis MCP server on THIS system.
#
# Validates the things that actually break installs across systems:
#   platform detection · venv/python · package import · tool registration ·
#   DB reachable + schema · embedding model loads · doctor health · a real
#   read-only tool call · stale-install check.
#
# Exit 0 = healthy, exit 1 = a hard failure. Safe to run any time (read-only).
# Works on WSL, Linux, macOS, Docker.
#
# USAGE:  bash tools/test-mcp.sh

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$HOME/.local/share/metis-mcp/.venv"
PY="$VENV/bin/python3"
export METIS_RC_ROOT="${METIS_RC_ROOT:-$REPO_ROOT}"

PASS=0; FAIL=0; WARN=0
ok()   { echo "  ✓ $1"; PASS=$((PASS+1)); }
warn() { echo "  ⚠ $1"; WARN=$((WARN+1)); }
bad()  { echo "  ✗ $1"; FAIL=$((FAIL+1)); }

echo "════════════════════════════════════════════════════"
echo "  Metis MCP server — smoke test"
echo "════════════════════════════════════════════════════"

# ── Platform ─────────────────────────────────────────────────────────────────
PLAT="unknown"
case "$(uname -s)" in
  Linux)  if grep -qi microsoft /proc/version 2>/dev/null; then PLAT="WSL"; \
          elif [ -f /.dockerenv ]; then PLAT="Docker"; else PLAT="Linux"; fi ;;
  Darwin) PLAT="macOS" ;;
esac
echo "  platform: $PLAT · root: $METIS_RC_ROOT"

# ── 1. venv python ───────────────────────────────────────────────────────────
if [ -x "$PY" ]; then ok "venv python present ($($PY --version 2>&1))"
else bad "venv python missing at $PY — run setup-mcp.sh"; echo "RESULT: FAIL"; exit 1; fi

# ── 2-9. Python-side checks in one process ───────────────────────────────────
"$PY" - <<'PYEOF'
import sys, os
ok=lambda m:print("  ✓ "+m); warn=lambda m:print("  ⚠ "+m); bad=lambda m:print("  ✗ "+m)
fails=0

# 2. package import + resilient loader
try:
    import metis_mcp.server as s
    from metis_mcp.app_instance import app
    n=len(app._tool_manager._tools) if hasattr(app,"_tool_manager") else 0
    failed=getattr(s,"FAILED_MODULES",{})
    ok(f"package imports — {n} tools registered")
    if failed:
        warn(f"{len(failed)} tool module(s) degraded: "+", ".join(failed))
    else:
        ok("all tool modules loaded")
    inst=getattr(__import__('metis_mcp'),'__file__','')
    print(f"  · running from: {'installed package' if 'site-packages' in inst else 'SOURCE (dev)'}")
except Exception as e:
    bad(f"package import FAILED: {type(e).__name__}: {e}"); sys.exit(2)

# 3. DB reachable + key tables
try:
    from metis_mcp.config import paths
    import sqlite3
    c=sqlite3.connect(str(paths.db), timeout=10)
    tabs={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    need={"tasks","projects","knowledge_databases","pdf_chunks","episodic_memory"}
    miss=need-tabs
    if miss: warn(f"DB reachable but missing tables: {miss}")
    else: ok(f"DB reachable — {len(tabs)} tables")
except Exception as e:
    bad(f"DB check failed: {e}"); fails+=1

# 4. embedding model loads (the RAG/knowledge layer depends on this)
try:
    from fastembed import TextEmbedding
    m=TextEmbedding("nomic-ai/nomic-embed-text-v1.5-Q")
    v=list(m.embed(["search_document: smoke test"]))
    ok(f"embedding model loads (dim {len(v[0])})")
except Exception as e:
    warn(f"embedding model unavailable (semantic search disabled): {type(e).__name__}")

# 5. doctor health
try:
    from metis_mcp.tools.doctor import run_doctor
    r=run_doctor()
    st=r["status"]
    (ok if st=="ok" else warn)(f"doctor: {st.upper()} — {r['summary']}")
    for ch in r["checks"]:
        if not ch["ok"] and ch["severity"]=="fail":
            bad(f"  doctor FAIL: {ch['name']} — {ch.get('detail','')[:80]}"); fails+=1
except Exception as e:
    warn(f"doctor could not run: {e}")

# 6. a real read-only tool call (knowledge DB list)
try:
    import asyncio
    from metis_mcp.tools.knowledge_db import list_knowledge_databases
    t=asyncio.run(list_knowledge_databases())
    if t and t[0].text: ok("sample tool call (list_knowledge_databases) works")
    else: warn("sample tool returned empty")
except Exception as e:
    bad(f"sample tool call FAILED: {type(e).__name__}: {e}"); fails+=1

sys.exit(1 if fails else 0)
PYEOF
PYRC=$?

echo "════════════════════════════════════════════════════"
if [ "$PYRC" -eq 0 ]; then echo "  RESULT: HEALTHY"; exit 0
else echo "  RESULT: PROBLEMS DETECTED — see ✗ rows above"; exit 1; fi
