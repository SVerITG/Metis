---
topic: metis-setup
updated: 2026-04-08
computers_tested:
  - DL29GY3
---

# Topic: Metis System Setup

Standing facts about how Metis is installed and configured. These are facts, not instructions.
For step-by-step instructions see `08_system/SETUP.md`.

---

## WSL environment

| Fact | Value |
|---|---|
| WSL distro for Claude Code | `Ubuntu-24.04` |
| WSL distro for Claude Desktop default | `Ubuntu` (wrong — always override) |
| How to list distros | `wsl.exe --list --verbose` |
| Correct flag for Claude Desktop | `-d Ubuntu-24.04` |

Claude Desktop launches commands in the **default** WSL distro. The default distro on DL29GY3
is plain `Ubuntu`, which is not where the MCP server lives. Always specify `-d Ubuntu-24.04`.

---

## Python venv

| Fact | Value |
|---|---|
| Venv location | `~/.local/share/metis-mcp/.venv` (local WSL) |
| Why not on OneDrive | Venvs embed absolute paths + platform binaries; not portable |
| How to create | Run `bash setup.sh` from `08_system/mcp-server/` |
| `pip install -e .` status | Broken on Ubuntu + Python 3.12 (setuptools 82 bug) |
| Workaround | `setup.sh` writes a `.pth` file + console script manually |

---

## Claude Desktop configuration

Config file path (Windows): `%APPDATA%\Claude\claude_desktop_config.json`
WSL equivalent: `/mnt/c/Users/sverschaeve/AppData/Roaming/Claude/claude_desktop_config.json`

Correct server entry:
```json
"metis-pkm": {
  "command": "wsl.exe",
  "args": ["-d", "Ubuntu-24.04", "-e", "/home/sverschaeve/.local/share/metis-mcp/run.sh"]
}
```

The `run.sh` script sets `METIS_PKM_ROOT` and execs uvicorn. This avoids the quoting
problems that arise when passing `VAR='path with spaces'` through `wsl.exe -e bash -c`.

---

## MCP server

| Fact | Value |
|---|---|
| Server framework | `FastMCP` (from `mcp.server.fastmcp`) |
| Entry point | `metis_mcp.server:app` via `run.sh` |
| Source location | `08_system/mcp-server/src/metis_mcp/` |
| Tool registration | Each `tools/*.py` imports `app` from `server.py` and uses `@app.tool()` |
| DB path | `07_outputs/apps/metis-dashboard/data/metis.sqlite` |
| `connect()` signature | Always `connect(paths.db)` — never bare `connect()` |

**OneDrive revert risk:** `server.py` has been reverted by OneDrive sync at least once,
switching it back to the broken `Server` import. If tools stop working, check `server.py`.

---

## Shiny dashboard

| Fact | Value |
|---|---|
| Location | `07_outputs/apps/metis-dashboard/` |
| Database | `data/metis.sqlite` |
| R platform | Windows (not WSL) |
| Minimum Shiny version | 1.8.0 (for `updateActionButton(class=...)`) |
| `.here` anchor | `.here` file in dashboard root |

Known issues fixed as of 2026-04-08:
- `renderTable(...)()` extra `()` in `mod_system.R` — removed
- `morning_librarian.R` wrong column names — fixed to match actual schema
- WSL paths (`/mnt/c/...`) in `projects.external_path` — SQL-updated to `C:/...`
- `seed_projects.R` used `here::here()` without anchor — replaced with `normalizePath(getwd())`

---

## Database schema (key tables)

| Table | Purpose |
|---|---|
| `agent_runs` | Audit log of every agent task |
| `ideas` | Captured ideas with tags and mood |
| `journal_entries` | Personal journal |
| `contacts` | Named contacts with notes |
| `glossary` | Term definitions |
| `memory_entries` | Memory palace entries (sessions, decisions, topics) |
| `projects` | Active and archived projects |
| `dropzone_intake` | Files queued for processing |

---

## Key architectural decisions

1. **OneDrive is the sync layer, not a build artifact store.** No venvs, no compiled
   artifacts, no `.here`-resolved paths that depend on machine state.

2. **Claude Desktop uses a wrapper script, not inline env vars.** `run.sh` is the
   stable entry point; quoting through `wsl.exe -e bash -c` is unreliable.

3. **Tool modules register themselves.** Each `tools/*.py` imports `app` from `server.py`
   at module load time and decorates its functions. `server.py` simply imports them all.

4. **Dual storage for memory.** Every memory entry goes into SQLite (fast search) AND
   a markdown file (human-readable, OneDrive-synced). Neither is the sole truth.
