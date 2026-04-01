# Metis MCP Server

MCP server that exposes the Metis research PKM to Claude Code, Claude Desktop, and Claude Cowork.

## Installation

```bash
cd "08_system/mcp-server"
pip install -e .
```

Or with uv:

```bash
cd "08_system/mcp-server"
uv pip install -e .
```

## Configuration

### Claude Code (settings.json)

Add to `.claude/settings.json` (global) or project-level `.claude/settings.json`:

```json
{
  "mcpServers": {
    "metis-pkm": {
      "command": "metis-mcp",
      "env": {
        "METIS_PKM_ROOT": "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain"
      }
    }
  }
}
```

If installed with uv and not on PATH, use the full path:

```json
{
  "mcpServers": {
    "metis-pkm": {
      "command": "uv",
      "args": ["run", "--directory", "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain/08_system/mcp-server", "metis-mcp"],
      "env": {
        "METIS_PKM_ROOT": "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/0. Personal/X. KPM/monia-second-brain"
      }
    }
  }
}
```

### Claude Desktop (claude_desktop_config.json)

Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "metis-pkm": {
      "command": "metis-mcp",
      "env": {
        "METIS_PKM_ROOT": "C:\\Users\\sverschaeve\\OneDrive - ITG\\Documents\\0. Personal\\X. KPM\\monia-second-brain"
      }
    }
  }
}
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `METIS_PKM_ROOT` | Absolute path to PKM root | Inferred from server location |

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
| `get_phd_context` | Retrieve PhD project context |
