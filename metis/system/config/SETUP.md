# Metis System Setup Guide

Complete installation guide for the Metis PKM system on a new computer.
Documents every issue encountered during setup and how each was resolved.

---

## Architecture Overview

| Component | Location | Runs on |
|-----------|----------|---------|
| MCP Server (Python) | `08_system/mcp-server/` (OneDrive) | WSL (Linux) |
| MCP venv | `~/.local/share/metis-mcp/.venv` (local) | WSL |
| Shiny Dashboard (R) | `07_outputs/apps/metis-dashboard/` (OneDrive) | Windows RStudio |
| SQLite database | `07_outputs/apps/metis-dashboard/data/metis.sqlite` | Shared via OneDrive |
| PKM files | `metis/` (OneDrive) | Both |

The key principle: **code and PKM on OneDrive, Python venv local**. The venv is created locally on each computer because OneDrive corrupts cross-platform Python environments.

---

## Prerequisites

### Windows
- [Git for Windows](https://git-scm.com/) — for project git status in dashboard
- [R 4.4+](https://cran.r-project.org/) — for the Shiny dashboard
- [RStudio](https://posit.co/download/rstudio-desktop/) — for running the dashboard
- [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) — for the MCP server

### WSL (Ubuntu)
- Python 3.10+ (pre-installed on Ubuntu 22.04+)
- `python3-venv` — `sudo apt install python3-venv`

---

## 1. MCP Server Setup (WSL)

### First time on any computer

```bash
cd "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/08_system/mcp-server"
bash setup.sh
```

That's it. The script:
1. Creates `~/.local/share/metis-mcp/.venv` (local, not synced by OneDrive)
2. Installs `mcp`, `pyyaml`, `requests` into the venv
3. Links the source code via a `.pth` file (bypasses broken editable install)
4. Creates the `metis-mcp` console script
5. Updates `~/.claude/settings.json` automatically

**Why local venv?** OneDrive syncs `.venv` between computers but Python venvs are not
portable across platforms or even across machines (absolute paths embedded in scripts,
compiled C extensions tied to the local Python ABI). Syncing them causes:
- Silent import failures
- Invalid metadata warnings from pip
- The venv disappearing when the other computer syncs a deletion

### Verify

```bash
~/.local/share/metis-mcp/.venv/bin/python3 -c \
  "from metis_mcp.server import app; print('OK:', app.name)"
```

Expected output: `OK: metis-pkm`

### Restart Claude Code

After setup or after any change to `server.py`, restart Claude Code for the MCP
server changes to take effect.

---

## 2. Claude Code Integration

`~/.claude/settings.json` (set automatically by `setup.sh`):

```json
{
  "mcpServers": {
    "metis-pkm": {
      "command": "/home/sverschaeve/.local/share/metis-mcp/.venv/bin/metis-mcp",
      "env": {
        "METIS_PKM_ROOT": "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis"
      }
    }
  }
}
```

---

## 3. Claude Desktop Integration (Windows)

Claude Desktop runs natively on Windows. To use the WSL-based MCP server:

**Location:** `C:\Users\sverschaeve\AppData\Roaming\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "metis-pkm": {
      "command": "wsl.exe",
      "args": [
        "-e",
        "bash", "-c",
        "METIS_PKM_ROOT='/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis' /home/sverschaeve/.local/share/metis-mcp/.venv/bin/metis-mcp"
      ]
    }
  }
}
```

**Note:** Claude Desktop must be restarted after editing this file.

**Important — WSL distro name:** If you have multiple WSL distributions, the `-d` flag
must match the one where `setup.sh` was run. Check with `wsl.exe --list` from PowerShell.
On this machine the correct distro is `Ubuntu-24.04`. Update the `-d` value if different
on your other computer.

The wrapper script `/home/sverschaeve/.local/share/metis-mcp/run.sh` sets `METIS_PKM_ROOT`
and launches the server. This avoids shell quoting issues when Windows passes arguments
through `wsl.exe`. The `setup.sh` script creates this wrapper automatically.

---

## 4. Shiny Dashboard Setup (Windows RStudio)

### First run

1. Open RStudio
2. Open the project: `07_outputs/apps/metis-dashboard/`
3. Set working directory: **Session → Set Working Directory → To Source File Location**
4. Run the setup check:
   ```r
   source("check_setup.R")
   ```
5. Install any missing packages shown by the check (usually on first install):
   ```r
   install.packages(c("shiny", "bslib", "DBI", "RSQLite", "xml2", "here",
                      "visNetwork", "jsonlite"))
   ```
   Note: `taskscheduleR` is listed in `check_setup.R` but is not actually used — skip it.
6. Launch:
   ```r
   shiny::runApp()
   ```

### Database

The SQLite database (`data/metis.sqlite`) is shared via OneDrive. It is pre-populated
and syncs automatically between computers. Do not run `seed_projects.R` unless
the database is empty — it uses `INSERT OR IGNORE` so it is safe, but unnecessary.

**If `seed_projects.R` fails with "unable to open database file":**
This means `here::here()` is resolving to the wrong directory.
Workaround: the script now uses `getwd()` instead of `here::here()`. Ensure your
RStudio working directory is set to the `metis-dashboard` folder before running.

**If the database file is cloud-only on Windows:**
In File Explorer, right-click `data/metis.sqlite` → "Always keep on this device".

---

## 5. Known Issues and Fixes Applied

### MCP Server

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `AttributeError: 'Server' has no attribute 'tool'` | `server.py` imported `mcp.server.Server` (low-level) instead of `FastMCP` which supports `@app.tool()` | Changed import to `from mcp.server.fastmcp import FastMCP` |
| `connect()` missing argument in `transcription.py` | Called `connect()` without required `db_path` arg | Changed to `connect(paths.db)` in both calls |
| MCP server venv deleted/corrupted by OneDrive | OneDrive syncs `.venv` from other computer, overwriting local version | Moved venv to `~/.local/share/metis-mcp/.venv` (local, never synced) |
| `BackendUnavailable: Cannot import 'setuptools.backends._legacy'` | pip's editable install mechanism incompatible with setuptools 82 on this Ubuntu | Bypassed with `.pth` file instead of `pip install -e .` |

### Shiny Dashboard

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Notes and Ideas modules crash on load | `updateActionButton(class=...)` added in Shiny 1.8.0; Windows had older version | Wrapped calls in `try(..., silent=TRUE)` in `mod_notes.R` and `mod_ideas.R`. Permanent fix: `install.packages("shiny")` |
| System tab crashes (token usage table) | `renderTable(...)()` — extra `()` invoked the render function immediately | Removed trailing `()` in `mod_system.R` |
| 10 course projects show wrong paths in git panel | Paths stored as `/mnt/c/...` (WSL format) in database when seeded from WSL | SQL `UPDATE` to replace `/mnt/c/` prefix with `C:/` |
| Git status warnings flooding RStudio console | `system2("git", ...)` prints R warning for every non-zero exit status | Wrapped with `suppressWarnings()` in `helpers.R` |
| "Open document" button broken in Research tab | `gsub("/", "\\\\", path)` converted forward slashes to backslashes in file URL | Changed to `gsub("\\\\", "/", path)` to normalize backslashes to forward |
| Dropzone morning scan silently fails | `morning_librarian.R` inserted into wrong column names (`source_filename`, `source_path`, `detected_type`, `processing_status`) that don't exist in schema | Fixed to correct names: `filename`, `stored_path`, `file_type`, `status` |
| File access warning for `ruflo-reference` on startup | Agent directory existed but was completely empty; `list.files()` hit an inaccessible OneDrive placeholder inside it | Deleted the empty directory |
| `seed_projects.R` fails with "Could not connect to database" | `here::here()` resolves to wrong root when `.here` anchor file is absent | Replaced `here::here()` with `file.path(normalizePath(getwd(), winslash="/"), ...)` |

### Database

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Dashboard loaded but showed no data on first launch | Database was empty; `seed_default_data()` only seeds 3 default projects | Run `seed_projects.R` once after first launch to populate projects and tasks |
| `seed_projects.R` fails with "Invalid or closed connection" | Suspected OneDrive file locking during active sync | Run when OneDrive sync is idle; or pin file locally ("Always keep on this device") |

---

## 6. Multi-Computer Setup

Metis is designed for use on multiple computers. Here's what lives where:

| What | Where | Sync method |
|------|-------|-------------|
| PKM content (notes, projects, library) | OneDrive | Automatic |
| SQLite database | OneDrive | Automatic — shared state |
| MCP server source code | OneDrive | Automatic |
| R dashboard code | OneDrive | Automatic |
| **Python venv** | **Local (`~/.local/share/metis-mcp/`)** | **Manual — run `setup.sh` once per computer** |
| Claude Code settings | Local (`~/.claude/`) | Manual — `setup.sh` updates this |
| R packages | Local (R library) | Manual — `check_setup.R` installs missing ones |

### Adding a new computer

```bash
# 1. Clone/sync the PKM via OneDrive (automatic)

# 2. Run MCP setup
cd "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/PKM/metis/08_system/mcp-server"
bash setup.sh

# 3. In Windows RStudio:
#    source("check_setup.R") then shiny::runApp()
```

---

## 7. Docker Consideration

**Current recommendation: Not needed.**

Docker would solve the Python environment portability problem (no more "run setup.sh
on each computer"), but adds overhead that isn't worth it for a personal PKM:
- Volume mounts needed for OneDrive files add complexity
- WSL already provides the Linux environment Claude Code needs
- The `setup.sh` script achieves the same result in ~30 seconds

**When Docker would make sense:**
- Deploying Metis for other users who don't have WSL
- Running the MCP server on a remote server (e.g., always-on NAS or VPS)
- Multi-user Metis installations

A `Dockerfile` for the MCP server would be straightforward when needed — the
`pyproject.toml` dependencies are minimal (`mcp`, `pyyaml`, `requests`).

---

## 8. Agent Inventory

| Agent | Status | Role |
|-------|--------|------|
| builder | ✅ | Scaffolds code, MCP tools, Shiny modules |
| dashboard-engineer | ✅ | Shiny dashboard maintenance |
| epidemiologist | ✅ | Epi analysis, HAT disease research |
| methods-coach | ✅ | Statistical methods |
| phd-architect | ⚠️ missing skill.md | PhD thesis structure |
| librarian | ✅ | Literature management |
| research-architect | ✅ | Research design |
| writing-partner | ✅ | Academic writing |
| presentation-maker | ✅ | Slides and visuals |
| news-aggregator | ✅ | Pulls and categorizes news |
| news-radar | ✅ | Surfaces high-signal items |
| learning-coach | ✅ | Learning path management |
| meeting-memory | ✅ | Meeting structuring |
| metis | ✅ | Meta-agent / router |
| software-engineer | ✅ | General software development |
| ux-engineer | ✅ | UI/UX |
| data-guardian | ✅ | Data safety |
| cybersecurity | ✅ | Security audits |
| career-coach | ✅ | Career strategy |
| edu-expert | ❌ missing system-prompt | Education domain |
| hr-talent | ❌ missing system-prompt | HR/recruitment |
| rc-builder | ✅ skill.md + contract.md | RC system builder |
