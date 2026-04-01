"""Project status retrieval from YAML frontmatter and SQLite tasks."""

import re
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.server import app


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a markdown file as a dict."""
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


def _get_task_counts(conn, project_id: str) -> dict:
    """Get task status counts for a project from the tasks table."""
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
        )
        if not cur.fetchone():
            return {}
        cur = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks WHERE project_id = ? GROUP BY status",
            (project_id,),
        )
        return {row["status"]: row["cnt"] for row in cur.fetchall()}
    except Exception:
        return {}


@app.tool()
async def get_project_status(project_id: str = "") -> list[TextContent]:
    """Get status of active projects from their YAML frontmatter.

    Reads project card markdown files and queries the tasks table for
    completion counts.

    Args:
        project_id: Specific project folder name. Empty string = all active projects.
    """
    proj_dir = paths.projects_active
    if not proj_dir.exists():
        return [
            TextContent(type="text", text=f"Projects directory not found: {proj_dir}")
        ]

    if project_id:
        targets = [proj_dir / project_id]
    else:
        try:
            targets = sorted(
                d for d in proj_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
            )
        except FileNotFoundError:
            return [TextContent(type="text", text="No active projects found.")]

    if not targets:
        return [TextContent(type="text", text="No active projects found.")]

    # Open DB once for task counts
    db_available = paths.db.exists()
    sections = []

    for proj_path in targets:
        if not proj_path.is_dir():
            sections.append(f"## {proj_path.name}\n\n_Directory not found._")
            continue

        # Look for project card (any .md in project root)
        md_files = list(proj_path.glob("*.md"))
        fm = {}
        for mf in md_files:
            try:
                fm = _parse_frontmatter(mf.read_text(encoding="utf-8"))
                if fm:
                    break
            except (OSError, UnicodeDecodeError):
                continue

        pid = fm.get("project_id", proj_path.name)
        title = fm.get("title", proj_path.name)
        status = fm.get("status", "unknown")
        owner = fm.get("owner", "")

        section = f"## {title}\n- **ID:** {pid}\n- **Status:** {status}"
        if owner:
            section += f"\n- **Owner:** {owner}"

        # Add remaining frontmatter fields
        for k, v in fm.items():
            if k not in ("project_id", "title", "status", "owner"):
                section += f"\n- **{k}:** {v}"

        # Task counts
        if db_available:
            try:
                with connect(paths.db) as conn:
                    counts = _get_task_counts(conn, pid)
                    if counts:
                        section += "\n- **Tasks:** " + ", ".join(
                            f"{s}: {c}" for s, c in sorted(counts.items())
                        )
            except Exception:
                pass

        sections.append(section)

    return [TextContent(type="text", text="\n\n".join(sections))]
