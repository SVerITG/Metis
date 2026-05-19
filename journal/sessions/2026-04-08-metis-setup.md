---
date: 2026-04-08
computer: DL29GY3
os: WSL Ubuntu-24.04
topics:
  - metis-setup
  - mcp-server
  - wsl
  - shiny-dashboard
  - onedrive
  - claude-desktop
---

# Session: Metis setup on DL29GY3

**Goal:** Get the MCP server and Shiny dashboard running on a second (work) laptop.

---

## What was done

This was a full bring-up session on a new computer (DL29GY3, work laptop). The PKM
already existed on OneDrive but nothing was running locally. By the end of the session
the MCP server was connected to Claude Desktop and the Shiny dashboard was loading
without crashes.

---

## Discoveries and fixes (ordered by impact)

### 1. WSL has two distributions — and Claude Desktop uses the wrong one

`wsl.exe --list --verbose` revealed two distros:
- `Ubuntu` — the default (marked `*`), the one Claude Desktop launches by default
- `Ubuntu-24.04` — where Claude Code runs, where everything was actually installed

Everything (venv, `run.sh`, the entire MCP server) was in `Ubuntu-24.04`.
Claude Desktop kept failing silently because it launched the server in `Ubuntu` where
none of those files exist.

**Fix applied:** `claude_desktop_config.json` now uses `-d Ubuntu-24.04` explicitly:
```json
{
  "command": "wsl.exe",
  "args": ["-d", "Ubuntu-24.04", "-e", "/home/sverschaeve/.local/share/metis-mcp/run.sh"]
}
```

**Rule:** Always specify the distro. Never rely on the WSL default.

---

### 2. Python venv must not live on OneDrive

The `.venv` was inside `system/mcp-server/` — on OneDrive. Two failure modes:
1. The other computer's OneDrive sync replaced the venv with a Windows-native version
   (wrong platform, wrong absolute paths).
2. File locks from `uvicorn` / `python` prevented OneDrive from syncing, triggering
   conflicts.

**Fix applied:** Venv relocated to `~/.local/share/metis-mcp/.venv` — local WSL filesystem,
never synced. `setup.sh` creates it fresh on each computer.

**Rule:** Python venvs embed absolute paths and platform binaries. They are not portable
across machines or OS types. Never commit or sync them.

---

### 3. `pip install -e .` broken on Ubuntu + Python 3.12

`BackendUnavailable: Cannot import 'setuptools.backends._legacy'` — setuptools 82 on
this Ubuntu/Python 3.12 combination doesn't expose the `backends` submodule that pip's
bundled pyproject-hooks expects.

**Fix applied:** `setup.sh` bypasses `pip install -e .` entirely:
1. Writes a `.pth` file to `site-packages` pointing at the `src/` directory.
2. Creates the `metis-mcp` console script by hand in `.venv/bin/`.

---

### 4. `server.py` used `Server` instead of `FastMCP`

Original `server.py` imported `from mcp.server import Server` and decorated tools with
`@app.tool()`. `Server` is the low-level MCP class — it does not support `.tool()`.
`FastMCP` (from `mcp.server.fastmcp`) does.

**Fix applied:** `server.py` now imports and instantiates `FastMCP`.

**Watch out:** OneDrive reverted this file once during the session (it synced an older
version from the other computer). If the MCP server starts failing mysteriously, check
whether `server.py` has been reverted.

---

### 5. `transcription.py` called `connect()` without the db path

All other tool modules call `connect(paths.db)`. `transcription.py` was calling bare
`connect()` — which crashes at runtime when the transcribe tool is invoked.

**Fix applied:** Both `connect()` calls in `transcription.py` changed to `connect(paths.db)`.

---

### 6. Dashboard: `updateActionButton(class=...)` requires Shiny >= 1.8.0

`mod_notes.R` and `mod_ideas.R` crashed on load because the Windows R installation had
an older version of Shiny that doesn't support the `class` argument to `updateActionButton`.

**Fix applied:** Wrapped the `updateActionButton` calls in `try(..., silent=TRUE)`.
Permanent fix: run `install.packages("shiny")` in Windows R to upgrade.

---

### 7. Dashboard: `renderTable(...)()` extra call in `mod_system.R`

The System tab crashed immediately. Root cause: `renderTable(...)` was followed by `()`
which invoked the render function immediately instead of registering it as a reactive.

**Fix applied:** Removed the trailing `()`.

---

### 8. Dashboard: 10 course projects had WSL paths in the database

When the database was originally seeded from WSL, `external_path` fields for 10 project
rows were stored as `/mnt/c/...` instead of `C:/...`. On Windows R, `normalizePath()`
turned `/mnt/c/foo` into `C:/mnt/c/foo` — a path that doesn't exist.

**Fix applied:**
```sql
UPDATE projects
SET external_path = REPLACE(external_path, '/mnt/c/', 'C:/')
WHERE external_path LIKE '/mnt/c/%';
```

---

### 9. Dashboard: `morning_librarian.R` used wrong column names

The script inserted into `(source_filename, source_path, detected_type, processing_status)`
but the actual `dropzone_intake` table schema uses `(filename, stored_path, file_type, status)`.

**Fix applied:** Updated the `INSERT` and `SELECT` statements to match the real schema.

---

### 10. `seed_projects.R` used `here::here()` with no anchor

Without a `.here` anchor file, the `here` package walks up the directory tree and may
resolve to a different root depending on where R was launched from. `check_setup.R` used
`getwd()` consistently; `seed_projects.R` was inconsistent.

**Fix applied:** Replaced `here::here(...)` with `file.path(normalizePath(getwd(), winslash="/"), ...)`.
Also created a `.here` file in the dashboard root as an anchor for future use.

---

### 11. `wsl.exe -e bash -c "VAR='path with spaces' cmd"` is unreliable

When Claude Desktop passes command arguments with embedded single-quoted paths through
`wsl.exe -e bash -c "..."`, Windows mangles the quoting and the env var is not set.

**Fix applied:** Created `/home/sverschaeve/.local/share/metis-mcp/run.sh` which sets
`METIS_PKM_ROOT` and execs the uvicorn server. Claude Desktop config calls the script
directly — no inline env vars needed.

---

### 12. `ruflo-reference` agent directory was empty and caused file access warnings

`list.files()` in `helpers.R` hit an inaccessible OneDrive placeholder file inside the
empty `ruflo-reference` directory.

**Fix applied:** Deleted `agents/ruflo-reference/` entirely.

---

## Artefacts created this session

| File | Purpose |
|---|---|
| `system/mcp-server/setup.sh` | One-command setup for a new computer |
| `system/SETUP.md` | Human-readable setup instructions |
| `system/session-log.md` | Running log of discoveries (this session was its first entry) |
| `~/.local/share/metis-mcp/run.sh` | Wrapper script for Claude Desktop |
| `01_control-room/memory/` | Memory palace (this session seeds it) |

---

## What to do next session (on any computer)

1. Run `list_recent_memory(5)` to re-orient.
2. Check `get_topic_memory("metis-setup")` for current architecture facts.
3. If on a new computer: follow `system/SETUP.md`.
4. Continue with Phase 2 of the implementation plan (see `01_control-room/implementation-plan-phase2.md`).
