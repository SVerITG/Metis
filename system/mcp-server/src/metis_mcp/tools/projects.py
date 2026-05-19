"""Project tools — create, read, archive, remove projects in Metis."""

import json
import re
import datetime
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


def _ensure_project_columns(conn) -> None:
    """Add columns introduced after initial schema creation (idempotent)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(projects)")}
    if "source" not in existing:
        conn.execute("ALTER TABLE projects ADD COLUMN source TEXT DEFAULT 'manual'")
    if "description" not in existing:
        conn.execute("ALTER TABLE projects ADD COLUMN description TEXT")


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:60]


@app.tool()
async def create_project(
    title: str,
    description: str = "",
    domain: str = "",
    source: str = "claude_project",
) -> list[TextContent]:
    """Register a new project in the Metis platform.

    Called when a researcher confirms they want a Claude conversation or project
    tracked permanently in Metis. Creates the project record in the DB so it
    appears in the Work tab and is available for task linking and memory search.

    Args:
        title: Human-readable project name, e.g. "Statistics Course".
        description: What this project is about (one sentence).
        domain: Research domain, e.g. "education", "epidemiology". Optional.
        source: Origin — "claude_project" (default), "claude_cowork", or "manual".
    """
    project_id = _slugify(title)
    now = datetime.datetime.now().isoformat(timespec="seconds")

    with connect(paths.db) as conn:
        _ensure_project_columns(conn)

        existing = conn.execute(
            "SELECT project_id, title FROM projects WHERE project_id = ?",
            (project_id,),
        ).fetchone()

        if existing:
            return [TextContent(
                type="text",
                text=(
                    f"Project already registered: '{existing['title']}' (id: {project_id}). "
                    "This conversation is now linked to it."
                ),
            )]

        conn.execute(
            """INSERT INTO projects
               (project_id, title, description, domain, status, priority,
                next_step, created_at, source)
               VALUES (?, ?, ?, ?, 'active', 'medium', '', ?, ?)""",
            (project_id, title, description, domain, now, source),
        )

    return [TextContent(
        type="text",
        text=(
            f"Project registered in Metis: '{title}' (id: {project_id}). "
            "All work in this conversation will be tracked against it. "
            "You can see it in the Work tab of the Metis dashboard."
        ),
    )]


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


def _ensure_context_columns(conn) -> None:
    """Add context container columns introduced after initial schema."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(projects)")}
    additions = [
        ("project_type", "TEXT DEFAULT 'research'"),
        ("context_doc", "TEXT DEFAULT ''"),
        ("history_log", "TEXT DEFAULT '[]'"),
        ("prompt_memory", "TEXT DEFAULT ''"),
        ("last_session_at", "TEXT"),
        ("detection_source", "TEXT DEFAULT 'manual'"),
    ]
    for col, typedef in additions:
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {typedef}")
            except Exception:
                pass


@app.tool()
async def load_project_context(project_id: str) -> list[TextContent]:
    """Load the full context block for a project — ready to paste into Claude.

    Returns the project's context_doc, recent session history, and next step
    formatted as a structured brief. Use this at the start of any work session
    on a specific project so Claude has full background.

    Args:
        project_id: The project slug (e.g. "hat-dashboard", "article-1").
    """
    with connect(paths.db) as conn:
        _ensure_context_columns(conn)
        row = conn.execute(
            "SELECT project_id, title, description, domain, next_step, project_type, "
            "context_doc, history_log, prompt_memory, last_session_at, status "
            "FROM projects WHERE project_id = ?",
            (project_id,),
        ).fetchone()

    if not row:
        # Try partial match
        with connect(paths.db) as conn:
            row = conn.execute(
                "SELECT project_id, title, description, domain, next_step, project_type, "
                "context_doc, history_log, prompt_memory, last_session_at, status "
                "FROM projects WHERE project_id LIKE ? LIMIT 1",
                (f"%{project_id}%",),
            ).fetchone()

    if not row:
        return [TextContent(type="text", text=f"No project found matching '{project_id}'.")]

    history = []
    try:
        history = json.loads(row["history_log"] or "[]")[-5:]
    except Exception:
        pass

    lines = [
        f"# PROJECT CONTEXT: {row['title']}",
        f"**ID:** {row['project_id']}  |  **Type:** {row['project_type'] or 'research'}  |  **Status:** {row['status']}",
    ]
    if row["domain"]:
        lines.append(f"**Domain:** {row['domain']}")
    if row["last_session_at"]:
        lines.append(f"**Last Metis session:** {row['last_session_at'][:10]}")
    lines.append("")

    if row["context_doc"]:
        lines.append("## Context")
        lines.append(row["context_doc"])
        lines.append("")

    if row["description"] and not row["context_doc"]:
        lines.append("## Description")
        lines.append(row["description"])
        lines.append("")

    if history:
        lines.append("## Recent session history")
        for e in reversed(history):
            lines.append(f"- **{e.get('date', '')}**: {e.get('summary', '')}")
        lines.append("")

    if row["next_step"]:
        lines.append(f"## Next step\n{row['next_step']}")
        lines.append("")

    lines.append("---")
    lines.append("*Paste this block into any Claude conversation to give full project context.*")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def update_project_memory(
    project_id: str,
    what_was_done: str,
    next_steps: str = "",
) -> list[TextContent]:
    """Append a session summary to a project's history and refresh its prompt memory.

    Call this at the end of any work session on a project. The history feeds
    into load_project_context() so future sessions automatically know what
    happened before.

    Args:
        project_id: The project slug.
        what_was_done: 1-3 sentence summary of what was accomplished this session.
        next_steps: Optional: what needs to happen next. Updates the next_step field.
    """
    now = datetime.datetime.now().isoformat()

    with connect(paths.db) as conn:
        _ensure_context_columns(conn)
        row = conn.execute(
            "SELECT project_id, title, history_log FROM projects WHERE project_id = ?",
            (project_id,),
        ).fetchone()

        if not row:
            return [TextContent(type="text", text=f"Project not found: {project_id}")]

        try:
            history = json.loads(row["history_log"] or "[]")
        except Exception:
            history = []

        history.append({
            "date": now[:10],
            "ts": now,
            "summary": what_was_done,
            "author": "metis",
        })
        history = history[-50:]

        recent = history[-5:]
        pm_lines = [f"- {e['date']}: {e['summary']}" for e in reversed(recent)]
        prompt_memory = "Recent session history:\n" + "\n".join(pm_lines)

        updates = {
            "history_log": json.dumps(history),
            "prompt_memory": prompt_memory,
            "last_session_at": now,
        }
        if next_steps:
            updates["next_step"] = next_steps

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE projects SET {set_clause} WHERE project_id = ?",
            list(updates.values()) + [project_id],
        )

    return [TextContent(
        type="text",
        text=(
            f"Session recorded for '{row['title']}' ({project_id}).\n"
            f"History entries: {len(history)}\n"
            f"Memory updated: {now[:10]}"
        ),
    )]


@app.tool()
async def detect_projects(scan_path: str = "") -> list[TextContent]:
    """Scan a folder for unregistered git repos and article folders.

    Useful for onboarding — finds existing project folders that are not yet
    tracked in Metis. Call create_project() for each item you want to register.

    Args:
        scan_path: Absolute path to scan. Defaults to the parent of METIS_RC_ROOT.
    """
    import os

    if scan_path:
        root = Path(scan_path)
    else:
        rc_root = os.environ.get("METIS_RC_ROOT", str(paths.root))
        root = Path(rc_root).parent

    if not root.exists():
        return [TextContent(type="text", text=f"Path not found: {root}")]

    with connect(paths.db) as conn:
        existing_ids = {
            row[0]
            for row in conn.execute("SELECT project_id FROM projects").fetchall()
        }
        existing_paths = {
            (row[0] or "").rstrip("/\\")
            for row in conn.execute(
                "SELECT external_path FROM projects "
                "WHERE external_path IS NOT NULL AND external_path != ''"
            ).fetchall()
        }

    found = []
    try:
        for item in sorted(root.iterdir()):
            if item.name.startswith(".") or not item.is_dir():
                continue
            path_str = str(item)
            if path_str in existing_paths:
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", item.name.lower()).strip("-")[:40]
            if slug in existing_ids:
                continue
            has_git = (item / ".git").exists()
            doc_files = (
                list(item.glob("*.md"))
                + list(item.glob("*.Rmd"))
                + list(item.glob("*.qmd"))
            )
            if has_git or doc_files:
                found.append((item.name, path_str, slug, has_git, len(doc_files)))
    except (PermissionError, OSError) as e:
        return [TextContent(type="text", text=f"Scan error: {e}")]

    if not found:
        return [TextContent(type="text", text=f"No unregistered projects found in {root}")]

    lines = [f"Found {len(found)} unregistered project(s) in {root}:\n"]
    for name, path, slug, has_git, ndocs in found[:20]:
        indicators = []
        if has_git:
            indicators.append("git repo")
        if ndocs:
            indicators.append(f"{ndocs} doc(s)")
        lines.append(f"- **{name}** ({', '.join(indicators)})")
        lines.append(f"  Path: {path}")
        lines.append(f"  Suggested ID: `{slug}`")
        lines.append(f"  Register: `create_project(title=\"{name}\", external_path=\"{path}\")`")
        lines.append("")

    return [TextContent(type="text", text="\n".join(lines))]
