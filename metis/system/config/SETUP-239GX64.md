# Metis — New Machine Setup Guide

Follow these steps on any new Windows machine to get Metis fully running.

---

## Prerequisites — install in this order

| Software | Where | Notes |
|---|---|---|
| **R** | https://cran.r-project.org/ → Download R for Windows | Version 4.3 or later |
| **RStudio** | https://posit.co/download/rstudio-desktop/ | Free Desktop version |
| **Python** | https://www.python.org/downloads/ | 3.11 or 3.12 — **tick "Add to PATH"** during install |
| **WSL** | Built into Windows — see Step 0 below | Needed for the MCP server |
| **Claude Desktop** | https://claude.ai/download | Sign in with your Anthropic account |
| **OneDrive** | Must already be signed in and syncing | PKM folder must be green-ticked |

If any of these is already installed, skip it.

---

## Step 0 — Install WSL (Windows Subsystem for Linux)

WSL is needed for Metis's background intelligence layer. It is built into Windows but not always enabled.

1. Open the **Start Menu**, search for **PowerShell**, right-click → **Run as administrator**
2. Run:
   ```
   wsl --install
   ```
3. Restart your computer when prompted
4. After restart, open **Ubuntu** from the Start Menu and let it finish first-time setup (set a username and password — you will need these later)

If `wsl --install` says WSL is already installed, skip this step.

---

## Step 1 — Verify OneDrive sync

The PKM folder must be synced before anything else works.

Check that this folder exists and is populated:
```
C:\Users\<you>\OneDrive - ITG\Documents\7. Software\PKM\metis\
```

If it's still syncing, wait until the folder is green-ticked.

---

## Step 2 — Install R packages

**Important:** R packages are installed per R version. If you have more than one version of R installed, you must install the packages into the same version that `launch_metis.bat` uses.

The easiest and most reliable way is to run the installer directly from the Command Prompt:

1. Open **Command Prompt** (search "cmd" in Start Menu)
2. Paste this command and press Enter:

```
"C:\Program Files\R\R-4.5.0\bin\Rscript.exe" -e "install.packages(c('shiny','bslib','shinyBS','DBI','RSQLite','dplyr','tidyr','lubridate','plotly','ggplot2','httr','rvest','jsonlite','xml2','DT','htmltools','visNetwork'), repos='https://cloud.r-project.org/')"
```

> If your R version is different from 4.5.0, adjust the path accordingly (e.g. `R-4.4.2`). Check `C:\Program Files\R\` to see which version you have.

This takes 5–10 minutes. Run once per machine.

**If you later upgrade R to a new version**, you must re-run this command using the new version's path — packages do not carry over automatically between R versions.

---

## Step 3 — Set up the MCP server (Python)

Open a WSL terminal and run:

```bash
cd "/mnt/c/Users/<you>/OneDrive - ITG/Documents/7. Software/PKM/metis/08_system/mcp-server"

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install the MCP server package
pip install -e .
```

Verify it works:
```bash
python -m metis_mcp.server
# Should print: Metis MCP server starting...
# Press Ctrl+C to stop
```

---

## Step 4 — Configure Claude Desktop

Open (or create) this file:
```
C:\Users\<you>\AppData\Roaming\Claude\claude_desktop_config.json
```

Paste this content (replace `<you>` with your Windows username):

```json
{
  "mcpServers": {
    "metis-pkm": {
      "command": "wsl",
      "args": [
        "bash",
        "/mnt/c/Users/<you>/OneDrive - ITG/Documents/7. Software/PKM/metis/08_system/mcp-server/run_mcp_server.sh"
      ],
      "env": {
        "METIS_RC_ROOT": "/mnt/c/Users/<you>/OneDrive - ITG/Documents/7. Software/PKM/metis"
      }
    }
  },
  "preferences": {
    "coworkScheduledTasksEnabled": false,
    "ccdScheduledTasksEnabled": true,
    "sidebarMode": "chat",
    "coworkWebSearchEnabled": false
  }
}
```

Restart Claude Desktop after saving.

---

## Step 5 — Test the MCP connection

In Claude Desktop, type:
```
What are my active projects?
```

Metis should respond with your project list. If it says "MCP server unavailable", check the WSL path in the config file.

---

## Step 6 — Create desktop and Start Menu shortcuts (recommended)

Run the shortcut creator once so you can launch Metis from anywhere:

1. In Windows Explorer, navigate to:
   ```
   Documents\7. Software\PKM\metis\07_outputs\apps\metis-dashboard\
   ```
2. Right-click **`create_shortcut.ps1`** → **Run with PowerShell**
3. A desktop shortcut and Start Menu entry called **"Metis"** will be created

From now on, just double-click "Metis" on your desktop or search "Metis" in the Start Menu.

---

## Step 7 — Launch the Metis Dashboard

Double-click the desktop shortcut **"Metis"**, or double-click:
```
C:\Users\<you>\OneDrive - ITG\Documents\7. Software\PKM\metis\07_outputs\apps\metis-dashboard\launch_metis.bat
```

A CMD window will open — keep it open. The dashboard will open in your browser at **http://localhost:3939**

If the browser does not open automatically, go to `http://localhost:3939` manually.

---

## Port reference

| App | Port | Launcher |
|---|---|---|
| Metis Dashboard | 3939 | `launch_metis.bat` |
| HAT Dashboard | 4040 | `launch_hat_dashboard.bat` |
| MLM Course app | 3000 | `node server.js` in `mlm-app/` |

---

## Troubleshooting

**Dashboard shows blank page / error**
- Check the CMD window that opened — R errors appear there
- Run `install.packages("plotly")` and `install.packages("shinyBS")` if missing

**MCP server not connecting**
- Make sure WSL is running (open a WSL terminal, wait for it to start)
- Check that Python venv exists: `ls /mnt/c/.../mcp-server/.venv/`
- Re-run `pip install -e .` if the venv was wiped

**OneDrive path issues**
- The path in `claude_desktop_config.json` uses forward slashes and `/mnt/c/` prefix (WSL format)
- The Windows path `C:\Users\...` becomes `/mnt/c/Users/...` in WSL

---

## Two-account setup

If you use two Claude accounts on the same machine:
- Both accounts share the same `claude_desktop_config.json` (one config file per Windows user)
- Both accounts can access Metis — the MCP server doesn't care which account is calling
- Your PKM data and PLANNING.md files are shared automatically

---

## Second computer checklist

- [ ] OneDrive synced
- [ ] R + packages installed (Step 2)
- [ ] Python venv created (Step 3)
- [ ] `claude_desktop_config.json` updated (Step 4)
- [ ] Test: "What are my active projects?" works in Claude Desktop (Step 5)
- [ ] Metis Dashboard launches at localhost:3939 (Step 6)
