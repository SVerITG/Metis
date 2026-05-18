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

Call the MCP tool `metis_doctor` directly. It returns a plain-text status block. Render it as-is — do not paraphrase. If any check is FAIL or WARN, surface a short paragraph after the report explaining the next step for that specific failure, in researcher language (not developer language).

## Output format

```
Metis Doctor — OK | WARN | FAIL
<one-line summary>

  [  OK] Python 3.10+                — running 3.12.3
  [  OK] METIS_RC_ROOT               — /home/.../metis
  [  OK] SQLite database             — metis.sqlite · 47 tables · 2840 KB
  [WARN] Anthropic API key           — not found in env or .env
  ...
```

If status is OK, end with: "All clear — Metis is healthy."

If status is WARN or FAIL, end with a one-line "Next step:" suggestion for the most severe issue (e.g. "Next step: run `/metis_config` to set the Anthropic API key.").

## Edge cases

- Doctor itself fails to import: tell the user the MCP server may not be installed yet — direct to `bash setup-mcp.sh`.
- All checks pass but user reports something is broken: ask them what surface is misbehaving (which tab, which command) — Doctor is broad, not deep.
