# Software Engineer Patterns Log

This file is appended by the software-engineer agent after every successful resolution.
Format: date, title, problem, solution, stack, gotcha.

---

## 2026-04-08 — MLM concept graph (SVG in app.js)

**Problem:** Course Map showed only curriculum layout; no concept-relationship view.  
**Solution:** Added `CONCEPT_NODES`/`CONCEPT_EDGES` constants + `renderConceptGraph()` (inline SVG, bezier arrows, section-colour nodes, click-to-navigate). Toggle via `state.mapMode` in `renderCourseMap()`. Event handling via existing `handleAction()` pattern.  
**Stack:** Vanilla JS, inline SVG, CSS custom properties.  
**Gotcha:** Use `data-action` attributes on `<g>` elements — inline `onclick` attributes are blocked by the app's CSP. Edge labels need `pointer-events: none` or they eat hover events.

---

## 2026-04-08 — Subagent file-permission boundary

**Problem:** When launched as a Claude Code background subagent, Edit/Write tools are denied for `.qmd` files in OneDrive paths, even though the parent session can edit them.  
**Solution:** Detect the block early. Return the exact replacement code as a diff in the result so the parent session can apply it directly. Never retry the same Edit call after a permission denial.  
**Stack:** Claude Code subagent sandbox.  
**Gotcha:** The parent session always has broader permissions than a subagent. For file-heavy tasks in restricted paths, have the subagent produce the diff and let the parent apply it.

---

## 2026-05-26 — DHIS2 dataValueSets empty response (KeyError fix)

**Problem:** Script calling `response['dataValues']` crashes with `KeyError` when a DHIS2 org unit has no data for the requested period — the API returns `{}` (no key) or `{"dataValues": []}`.
**Solution:** Replace all `response['dataValues']` with `response.get('dataValues', [])`. Wrap each per-org-unit request in a try/except covering `HTTPError`, `ConnectionError`, and `JSONDecodeError`. Log skips at DEBUG level so silence is explicit, not invisible.
**Stack:** Python, `requests`, DHIS2 `/api/dataValueSets`.
**Gotcha:** `.get()` is safe for all DHIS2 versions (2.36–2.40+). If using the Analytics API (`/api/analytics`) the empty key is `rows`, not `dataValues` — same `.get()` fix applies. Connection errors should be re-raised (fatal); HTTP and JSON errors should log-and-continue (per-org-unit recoverable).

---

## 2026-04-08 — agent_runs schema alignment

**Problem:** MCP server `_AGENT_RUNS_DDL` used `id`/`complexity`/`timestamp` but the actual DB table uses `run_id`/`status`/`created_at`.  
**Solution:** Updated DDL and INSERT in `agents.py` to match the real schema. Kept `complexity` as the Python parameter name (maps to `status` column) for backwards API compatibility.  
**Stack:** Python, SQLite, FastMCP.  
**Gotcha:** Always verify the real table schema with `PRAGMA table_info(agent_runs)` before writing INSERT statements. The DDL `CREATE TABLE IF NOT EXISTS` silently no-ops if the table already exists — it won't fix column name mismatches.
