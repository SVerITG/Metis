# Metis MCP Server

MCP server that exposes the Metis Research Context (RC) to Claude Code, Claude Desktop, and Claude Cowork.

## How it works on Windows + WSL

The `.venv` lives on OneDrive (NTFS), which does not support symlinks.
Python's `venv` cannot create the `python`/`python3` symlinks in `.venv/bin/`, so
the `metis-mcp` entry-point script fails when called directly.

**Fix**: use `run_mcp_server.sh`, which calls `/usr/bin/python3.12` directly and
adds the venv site-packages to `PYTHONPATH`.

## Installation

```bash
cd "08_system/mcp-server"
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

### Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "wsl",
      "args": [
        "bash",
        "~/.local/share/metis-mcp/run.sh"
      ],
      "env": {
        "METIS_RC_ROOT": "/path/to/your/metis"
      }
    }
  }
}
```

### Claude Code (`.claude/settings.json`)

```json
{
  "mcpServers": {
    "metis-rc": {
      "command": "bash",
      "args": ["/path/to/metis/08_system/mcp-server/run_mcp_server.sh"],
      "env": {
        "METIS_RC_ROOT": "/path/to/your/metis"
      }
    }
  }
}
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `METIS_RC_ROOT` | Absolute path to RC root | Inferred from server location |

## Available Tools

| Tool | Description |
|---|---|
| `search_literature` | Search the sleeping-sickness literature database |
| `get_agent_context` | Load an agent's system prompt and contract |
| `log_agent_run` | Record an agent run for audit tracking |
| `search_notes` | Search markdown notes across domains/projects/library |
| `get_project_status` | Get status of active projects |
| `get_tasks` | Query tasks with filters |
| `create_task` | Create a new task |
| `save_review` | Save a review document |
| `get_research_context` | Retrieve research project context |
