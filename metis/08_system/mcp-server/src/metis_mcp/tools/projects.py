"""Project status retrieval from YAML frontmatter and SQLite tasks."""

import re
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


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

    sections.append("\n---\n[Open Metis Dashboard](http://localhost:3939)")
    return [TextContent(type="text", text="\n\n".join(sections))]


@app.tool()
async def archive_project(project_id: str) -> list[TextContent]:
    """Archive a project — marks it inactive but keeps all data.

    Sets status='archived' in projects table. Project disappears from
    active view but remains available for brainstorm context and search.

    Args:
        project_id: The project_id to archive.
    """
    with connect(paths.db) as conn:
        cur = conn.execute(
            "SELECT project_id, title FROM projects WHERE project_id = ?",
            (project_id,),
        )
        row = cur.fetchone()
        if not row:
            return [TextContent(type="text", text=f"Project not found: {project_id}")]
        conn.execute(
            "UPDATE projects SET status = ? WHERE project_id = ?",
            ("archived", project_id),
        )
    return [
        TextContent(
            type="text",
            text=f"Project '{row['title']}' ({project_id}) has been archived.",
        )
    ]


@app.tool()
async def unarchive_project(project_id: str) -> list[TextContent]:
    """Restore an archived project to active status.

    Args:
        project_id: The project_id to restore.
    """
    with connect(paths.db) as conn:
        cur = conn.execute(
            "SELECT project_id, title FROM projects WHERE project_id = ?",
            (project_id,),
        )
        row = cur.fetchone()
        if not row:
            return [TextContent(type="text", text=f"Project not found: {project_id}")]
        conn.execute(
            "UPDATE projects SET status = ? WHERE project_id = ?",
            ("active", project_id),
        )
    return [
        TextContent(
            type="text",
            text=f"Project '{row['title']}' ({project_id}) has been restored to active status.",
        )
    ]


@app.tool()
async def remove_project(project_id: str, delete_files: bool = False) -> list[TextContent]:
    """Remove a project from Metis entirely.

    Deletes project record and associated tasks from DB.
    If delete_files=True, also deletes the external_path folder from disk
    (only if path is within RC root — safety check enforced).

    Args:
        project_id: The project_id to remove.
        delete_files: If True, delete the project folder from disk. Default False.
    """
    import shutil

    with connect(paths.db) as conn:
        cur = conn.execute(
            "SELECT project_id, title, external_path FROM projects WHERE project_id = ?",
            (project_id,),
        )
        row = cur.fetchone()
        if not row:
            return [TextContent(type="text", text=f"Project not found: {project_id}")]

        title = row["title"]
        external_path = row["external_path"]

        conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))

        # Delete associated tasks if the table exists
        tasks_exist = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
        ).fetchone()
        if tasks_exist:
            conn.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))

    lines = [f"Project '{title}' ({project_id}) has been removed from Metis."]

    if delete_files:
        if not external_path:
            lines.append("No external_path set — no files deleted.")
        else:
            folder = Path(external_path).resolve()
            rc_root = str(paths.root.resolve())
            if not str(folder).startswith(rc_root):
                lines.append(
                    f"File deletion skipped: '{folder}' is outside PKM root '{rc_root}'."
                )
            elif not folder.exists():
                lines.append(f"File deletion skipped: '{folder}' does not exist on disk.")
            else:
                shutil.rmtree(folder)
                lines.append(f"Deleted folder from disk: {folder}")

    return [TextContent(type="text", text="\n".join(lines))]
