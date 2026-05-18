# Metis — Installation Guide

All installation paths. Choose the one that fits you.

---

## For Researchers (no technical knowledge needed)

### Windows — one double-click

**Download `MetisSetup.exe`** from the [latest release](https://github.com/SVerITG/Metis_PH/releases/latest).

Double-click it. Follow the three screens. Takes about 8 minutes.

What it installs:
- Claude Desktop (the AI interface)
- Python (runs silently in the background, you never see it)
- Metis research files in your Documents folder
- Desktop shortcuts

When Claude Desktop opens, Metis will guide you through the 13-question setup wizard.

**Requirements:** Windows 10 or 11. Internet connection. An [Anthropic API key](https://console.anthropic.com).

---

## For Researchers — manual Windows install

If the `.exe` doesn't work, use the PowerShell script instead:

1. Download and unzip this repository
2. Open the `metis/system/install/windows/` folder
3. Right-click `install.bat` → Run as administrator *(only needed if Python install fails)*
4. Follow the prompts

**Stage 1 only** (AI assistant, no dashboard, fastest):
```
install.bat -Stage1Only
```

**Full install** (AI + dashboard + all tools):
```
install.bat
```

---

## For Developers

### Linux / WSL / macOS — one command

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/SVerITG/Metis_PH/main/metis/system/mcp-server/setup-mcp.sh)
```

Detects Ubuntu 20/22/24 and macOS. Creates a venv, installs all dependencies,
registers with Claude Code and Claude Desktop. Idempotent.

Dashboard:
```bash
cd ~/Metis_PH/metis/system/app-py && bash run.sh
# → http://127.0.0.1:8000
```

### Manual install (any OS)

```bash
git clone https://github.com/SVerITG/Metis_PH.git
cd Metis_PH/metis/system/mcp-server

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
pip install faster-whisper      # optional: voice capture

# Set environment
export METIS_RC_ROOT="$(pwd)/../../.."
export ANTHROPIC_API_KEY="sk-ant-..."

# Run MCP server
python -m metis_mcp.server

# In a second terminal — run dashboard
cd ../app-py && uvicorn app:app --host 127.0.0.1 --port 8000
```

### Register with Claude Desktop (Windows + WSL)

`%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "wsl.exe",
      "args": ["-e", "bash", "/home/<username>/.local/share/metis-mcp/run.sh"]
    }
  }
}
```

### Register with Claude Code

`~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "/home/<username>/.local/share/metis-mcp/run.sh"
    }
  }
}
```

### Register with Claude Desktop (Windows native — no WSL)

`%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "C:\\Users\\<username>\\Documents\\Metis\\system\\mcp-server\\.venv-win\\Scripts\\pythonw.exe",
      "args": ["-m", "metis_mcp.server"],
      "env": {
        "METIS_RC_ROOT": "C:\\Users\\<username>\\Documents\\Metis",
        "PYTHONPATH": "C:\\Users\\<username>\\Documents\\Metis\\system\\mcp-server\\src"
      }
    }
  }
}
```

---

## Docker

```bash
# Clone the repo
git clone https://github.com/SVerITG/Metis_PH.git
cd Metis_PH/metis/system/install/docker

# Configure
cp .env.example .env
# Edit .env: add your API key, set METIS_DATA_DIR

# Start
docker-compose up -d

# Dashboard
open http://localhost:8000
```

**MCP server inside Docker** — for Claude Desktop to reach the MCP server inside Docker,
use the `stdio` transport via:
```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "docker",
      "args": ["exec", "-i", "metis-mcp", "python", "-m", "metis_mcp.server"]
    }
  }
}
```

---

## Installation comparison

| Method | For whom | Time | Admin needed | WSL needed |
|---|---|---|---|---|
| **MetisSetup.exe** | Researchers, non-technical | ~8 min | No* | No |
| **install.bat** | Windows users, some experience | ~5 min | Sometimes | No |
| **setup-mcp.sh** | Developers, Linux/Mac | ~3 min | No | Optional |
| **Manual** | Developers, full control | ~10 min | No | No |
| **Docker** | Institutions, deployment | ~15 min | No | No |

*Admin required only if Python auto-install fails via winget.

---

## Uninstall

**Windows:** Control Panel → Programs → Metis Research Cortex → Uninstall

Or manually:
1. Delete `%USERPROFILE%\Documents\Metis` (your research files — keep if you want them)
2. Delete `%USERPROFILE%\.claude\CLAUDE.md`
3. Remove `metis-rc` from `%APPDATA%\Claude\claude_desktop_config.json`
4. Uninstall Claude Desktop separately if no longer needed

---

## Troubleshooting

**"Python not found" after install**
Close and reopen the terminal. The PATH update sometimes requires a restart.

**"MCP server not connecting" in Claude Desktop**
Check that `claude_desktop_config.json` has the correct Python path.
The Windows installer writes this automatically — re-run `install.bat` to fix it.

**Dashboard won't start**
Make sure the venv was created: `Metis\system\mcp-server\.venv-win\` should exist.
Re-run `install.bat` to repair.

**API key not working**
Check `Metis\system\.env` — the key should start with `sk-ant-`.
