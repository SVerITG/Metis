---
name: Metis Doctor
description: "metis doctor, health check, diagnose, what's broken, troubleshoot, system status, self-test, sanity check, metis-doctor"
model: claude-haiku-4-5-20251001
effort: normal
complexity: quick
---

## Purpose

Run a one-screen health check on Metis. Reports on Python, the SQLite database, the Anthropic API key, your `user-config.yaml`, agent and skill folders, folder-rename hygiene, MCP imports, and `.env` git safety.

Use whenever:
- Something feels broken and you want a single command to triage.
- You just `git pull`-ed and want to confirm nothing regressed.
- You're about to publish or share the repo and want to catch hygiene issues.

## What to do when invoked

Call the MCP tool `metis_doctor` directly. It returns a Metis-branded status block (the same `Metis · Research Cortex` look as the dashboard, with ✓ / ⚠ / ✗ status glyphs). **Render it as-is — do not paraphrase.** Then, for every ⚠ or ✗ row, add a short plain-language paragraph telling the user what it means and the exact next step — in researcher language, never developer jargon.

The check covers: Python, the database, the Anthropic API key, the **embedding/RAG engine** (fastembed + sqlite-vec), the **knowledge layer** (are docs indexed?), agents/skills, the **dashboard on :8080**, the **Claude Desktop link** (is metis-rc registered?), folder hygiene, MCP imports, and `.env` git safety.

## Output format

```
════════════════════════════════════════════════════
  Metis · Research Cortex — Health Check
════════════════════════════════════════════════════
  Status: ✓ HEALTHY  |  ⚠ NEEDS ATTENTION  |  ✗ PROBLEMS FOUND
  <one-line summary>

  ✓  Python 3.10+              running 3.12.3
  ✓  Embedding / RAG engine    fastembed + sqlite-vec installed
  ⚠  Anthropic API key         not found in env or .env
  ⚠  Claude Desktop link       found but metis-rc not registered — re-run setup-mcp.sh
  ...
────────────────────────────────────────────────────
  Next step → <most severe open item, in plain language>
```

Translate each open item into a plain fix, e.g.:
- *Embedding / RAG engine missing* → "Semantic search is off. Reinstall Metis with the embedding extra: `bash tools/reinstall-mcp.sh`."
- *Anthropic API key* → "Run `/metis_config` (or `/metis-customize`) to paste your key."
- *Claude Desktop link* → "Re-run `bash system/mcp-server/setup-mcp.sh`, then quit and reopen Claude Desktop."
- *Dashboard not running* → "Start it from the Metis desktop icon, or run `bash system/app-py/run.sh`."

## Edge cases

- Doctor itself fails to import: tell the user the MCP server may not be installed yet — direct to `bash setup-mcp.sh`.
- All checks pass but user reports something is broken: ask them what surface is misbehaving (which tab, which command) — Doctor is broad, not deep.
