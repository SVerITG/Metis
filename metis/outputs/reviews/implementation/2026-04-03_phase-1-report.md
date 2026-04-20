# Phase 1 — Foundation & Cleanup
**Date:** 2026-04-03

---

## Completed

### 1.1 Metis → Metis rename

- **Root folder:** `metis-second-brain/` → `metis/`
- **MCP README:** Updated all 3 path references from `0. Personal/X. KPM/metis-second-brain` → `7. Software/PKM/metis`
- **data-guardian-hook.py:** Updated PKM_ROOT default path
- **build_inventory.sh:** Updated OUT_DIR path
- **seed_phd_subset.sh:** Updated INPUT/OUTPUT paths
- **tools/research.py:** Created (replaces tools/phd.py); updated `get_research_context` tool
- **tools/phd.py:** Deleted
- **server.py:** `phd` import → `research`
- **config.py:** `self.phd` → `self.research`

### 1.2 Dashboard tab cleanup

- **Deleted modules:** `mod_finance.R`, `mod_talks.R`, `mod_agents.R`, `mod_search.R`, `mod_graph.R`, `mod_phd.R`, `mod_crucible.R`
- **Created:** `mod_research.R` (renamed from mod_phd.R with all internal refs updated)
- **Created:** `mod_dropzone.R` (renamed from mod_crucible.R with all internal refs updated)
- **app.R:** Removed `nav_menu("More", ...)` + all children; renamed PhD → Research, Crucible → Dropzone; removed server calls for deleted modules
- **data_store.R:** `phd_milestones` table → `research_milestones`; `crucible_intake` table → `dropzone_intake`; added migration for existing phd_milestones data; renamed `insert_phd_milestone` → `insert_research_milestone`, `get_phd_milestones` → `get_research_milestones`
- **helpers.R:** `phd_root` → `research_root`; `phd_documents` → `research_documents`; `random_phd_paper` → `random_research_paper`
- **mod_control_room.R:** Updated call from `random_phd_paper` → `random_research_paper`

### 1.3 Domain folder rename

- `03_domains/phd/` → `03_domains/research/`

### 1.4 Red lines document

- **Created:** `08_system/red-lines.md` — 5 red lines + data classification table

### 1.5 Workflows document

- **Created:** `08_system/workflows.md` — all 11 workflows documented with steps

---

## Skipped / deferred

- **Agent README files** referencing "Metis" in 01_control-room: these are historical planning docs — left as-is (they document the old system name and are not active code)
- **Ontology file** (`08_system/ontology/ontology-v1.md`): contains "Metis" conceptually — deferred to Phase 2 agent refactor
- **launch_monia.bat**: Not found in scanned directories (may not exist yet or is outside PKM root)
- **CSS class renames** (`phd-timeline-wrap` → `research-timeline-wrap`): CSS file in `www/styles.css` still uses old class names. The R module uses new names. Update `styles.css` in Phase 4.1 (CSS theme overhaul).

---

## Issues found

- The `dropzone_intake` table was previously `crucible_intake` (with `phd_article_link` column). Existing intake records in SQLite will remain in old `crucible_intake` table. If migration is needed, add to `ensure_db_schema` similarly to the `phd_milestones` migration.
- `C:\\...\\metis-second-brain` path in Claude Desktop config is not updated here — user must update `%APPDATA%\Claude\claude_desktop_config.json` manually (see Verification below).

---

## Verification

1. **MCP server loads:**
   ```bash
   cd "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/08_system/mcp-server"
   python -c "from metis_mcp.tools.research import get_research_context; print('OK')"
   ```

2. **Dashboard launches:**
   ```r
   shiny::runApp('/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/07_outputs/apps/metis-dashboard')
   ```
   Expected: 9 tabs (Control Room, Library, Research, Projects, Meetings, News, Learning, Ideas, Dropzone) — no More menu.

3. **Update Claude Desktop config:**
   In `%APPDATA%\Claude\claude_desktop_config.json`, change:
   ```
   "METIS_PKM_ROOT": "C:\\...\\metis-second-brain"
   ```
   to:
   ```
   "METIS_PKM_ROOT": "C:\\Users\\sverschaeve\\OneDrive - ITG\\Documents\\7. Software\\PKM\\metis"
   ```

4. **Update Claude Code settings.json** (if configured with absolute path):
   Change `metis-second-brain` → `metis` in `METIS_PKM_ROOT`.
