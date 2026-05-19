# Metis Session Log

Running log of setup sessions, debugging discoveries, and decisions made.
Use this before starting a new session on a new computer — it tells you what went wrong
last time so you don't repeat it.

---

## 2026-04-08 — New computer setup + dashboard stabilisation

**Computer:** DL29GY3 (work laptop, WSL Ubuntu-24.04)
**Goal:** Get MCP server and Shiny dashboard working on a second computer

### What we learned

#### WSL has two distributions — always check
`wsl.exe --list --verbose` showed two distros:
- `Ubuntu` (default, marked `*`)
- `Ubuntu-24.04` (where Claude Code actually runs)

Claude Desktop uses the DEFAULT distro. Claude Code uses `Ubuntu-24.04`.
Everything we installed (venv, run.sh) was in `Ubuntu-24.04`.
Claude Desktop kept failing because it launched the server in `Ubuntu` where the files don't exist.
**Fix:** Always specify `-d Ubuntu-24.04` in `claude_desktop_config.json`.

#### Never put the Python venv on OneDrive
The `.venv` was inside `system/mcp-server/` on OneDrive. Every time the other computer synced,
it either deleted the venv or replaced it with an incompatible Windows-native version.
Python venvs are not portable: they embed absolute paths and platform-specific compiled extensions.
**Fix:** Venv lives at `~/.local/share/metis-mcp/.venv` (local WSL, never synced).
Run `setup.sh` once per computer to create it.

#### `pip install -e .` is broken on this Ubuntu + Python 3.12 combo
`BackendUnavailable: Cannot import 'setuptools.backends._legacy'` — setuptools 82
on this system doesn't expose the `backends` module that pip's bundled pyproject-hooks expects.
**Fix:** Manually link the package via a `.pth` file and create the console script by hand.
See `setup.sh` for the exact approach.

#### server.py used `Server` instead of `FastMCP`
The MCP source used `from mcp.server import Server` and `@app.tool()`, but `Server` is the
low-level class that doesn't support `.tool()`. `FastMCP` (from `mcp.server.fastmcp`) does.
**Fix:** `server.py` now uses `FastMCP`. If OneDrive reverts this file (it happened once during
the session), re-apply the fix or run `setup.sh` which will catch it on next install.

#### `transcription.py` was calling `connect()` without `db_path`
All other tools call `connect(paths.db)`. transcription.py called bare `connect()`.
This crashes at runtime when the transcribe tool is invoked.
**Fix:** Changed both calls in `transcription.py` to `connect(paths.db)`.

#### Dashboard: `updateActionButton(class=...)` requires Shiny ≥ 1.8.0
The Windows R had an older Shiny. `mod_notes.R` and `mod_ideas.R` crashed on load.
**Fix:** Wrapped calls in `try(..., silent=TRUE)`. Permanent fix: `install.packages("shiny")` in Windows R.

#### Dashboard: `renderTable(...)()` in mod_system.R
Extra `()` at the end of the renderTable call invoked it immediately, crashing the System tab.
**Fix:** Removed trailing `()`.

#### Dashboard: 10 course projects had WSL paths in the database
When the database was originally seeded from WSL, project `external_path` fields were stored
as `/mnt/c/...` instead of `C:/...`. Windows R's `normalizePath()` turned these into `C:/mnt/c/...`.
**Fix:** SQL UPDATE to replace `/mnt/c/` prefix with `C:/` for all affected rows.

#### Dashboard: `morning_librarian.R` used wrong column names
The script inserted into `(source_filename, source_path, detected_type, processing_status)`
but the `dropzone_intake` table has `(filename, stored_path, file_type, status)`.
**Fix:** Updated the INSERT and SELECT statements to use the correct column names.

#### `seed_projects.R` used `here::here()` which resolved to the wrong directory
Without a `.here` anchor file, `here` walks up the directory tree and may find a different root.
`check_setup.R` uses `getwd()` which is correct; `seed_projects.R` was inconsistent.
**Fix:** Replaced `here::here(...)` with `file.path(normalizePath(getwd(), winslash="/"), ...)`.
Also created a `.here` file in the dashboard root as an extra anchor.

#### `wsl.exe -e bash -c "VAR='path with spaces' cmd"` doesn't work reliably
When Claude Desktop passes arguments with embedded single-quoted paths through `wsl.exe -e bash -c`,
Windows mangles the quoting and the env var isn't set correctly.
**Fix:** Created `/home/sverschaeve/.local/share/metis-mcp/run.sh` which sets `METIS_PKM_ROOT`
and execs the server. Claude Desktop config simply calls `wsl.exe -d Ubuntu-24.04 -e /path/to/run.sh`.

#### `ruflo-reference` agent directory was empty and caused file access warnings
`list.files()` in helpers.R hit an inaccessible OneDrive placeholder inside the empty directory.
**Fix:** Deleted the directory entirely.

### Session checklist (what to run on a new computer)

```bash
# In WSL (Ubuntu-24.04):
cd "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/system/mcp-server"
bash setup.sh
# Then restart Claude Code and Claude Desktop

# In Windows RStudio:
# Open system/app-py/
# Session > Set Working Directory > To Source File Location
source("check_setup.R")
install.packages("shiny")   # if Shiny < 1.8.0
shiny::runApp()
```

---

## 2026-04-08 — MLM course implementation (sessions 2–4)

**Computer:** DL29GY3 (work laptop, Ubuntu-24.04 WSL)
**Goal:** Implement all items from the edu-expert gap analysis for the MLM course QMD files.

### What we implemented
- **G3 (URLs):** All bare URLs in `## Sources` sections converted to `[url](url)` markdown links across sections 1–6. Bug fix: sed was run on already-edited files, causing double-wrapping (`[[url](url)](url)`) and split URLs (`[base/](url)suffix`). Fixed with targeted perl one-liners.
- **G5 (Tidyverse):** All `%>%` → `|>`. All `df$col <-` → `|> mutate()` in sections 1–6. Base-R `hist()/plot()` → ggplot2.
- **DGP annotations:** `# True DGP:` header comments added to all simulation blocks in lessons 5–17, 22, 30b, 31. Parameters annotated inline.
- **Exercises restructured (G4, WS2, ML6, UF4):** `## Exercises` headers removed from intro lessons. Tie-ins moved to `## Tie-ins`. Exercises merged into `{.optional-practice}` blocks.
- **V2/V5 (lesson1-variables):** Duplicate checklist removed. R-check step added to quick-test callout. 6-exercise block + self-check removed.
- **D3/D4/D5 (lesson2-descriptives):** `## Conditions for Application` moved to line 49 (after Key Summary Statistics, before Understanding Shape). Section renamed to `## Pre-Analysis Checks: Normality, Outliers, and Shape`. QQ-plot already shows normal + skewed + heavy-tail facets.
- **G12/G13 (app.js):** Double scrollbar fixed (`overflow:hidden` on iframe). Intro lessons stripped of mastery/practice tabs via `isIntro` flag.
- **ML3, ML7, WS4, UF2, UF5, UF6, ML5:** Verified as done or moot; gap analysis updated.

### What we learned
- **sed on partially-edited files** → double-wrapped URLs. Always check whether a file was already manually edited before running global sed. Use perl with capture groups to handle partial-URL patterns safely.
- **Context compaction mid-session** → prior tool results cleared. The session summary preserves what was done but not the exact in-memory state. Always verify file state after resuming from a summary.
- **Gap analysis vs file reality:** Some items the summary marked as "done" hadn't been saved to the gap analysis markdown. Always re-read the gap analysis at session start to reconcile.

### What remains (blocked — needs external access)
- **ML4:** Paste demo output inline — needs Quarto render or R to pre-compute `set.seed()` output
- **V1, D1:** Empty boxes — CSS/rendering issues visible only in browser
- **V6:** R practice step 2 mismatch — needs app DB investigation
- **D2:** Show code output — needs Quarto execution
- **D7:** 10 mastery check questions — needs SQLite DB insert in dashboard

### Session checklist
- [x] All source URLs verified and fixed (G3)
- [x] Tidyverse conversion complete (G5)
- [x] DGP annotations complete (sections 2–4, 6)
- [x] Intro lesson exercises restructured
- [x] lesson1-variables exercises/self-check removed (V5)
- [x] lesson2-descriptives pre-analysis section reorganised (D3, D4)
- [x] Gap analysis updated to 86% complete (56/65 items)
- [x] Tasks added to Metis planning DB (`multilevel-analysis` project)

---

## Template for future sessions

```
## YYYY-MM-DD — [topic]

**Computer:** [hostname / machine]
**Goal:** [what you were trying to do]

### What we learned
- [problem] → [root cause] → [fix]

### Session checklist
- [ ] item
```

