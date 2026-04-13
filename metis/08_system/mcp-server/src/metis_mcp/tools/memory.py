"""Persistent memory palace: sessions, ideas, decisions, journal entries."""

import datetime
import subprocess
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.server import app

_MEMORY_DDL = """
CREATE TABLE IF NOT EXISTS memory_entries (
  entry_id TEXT PRIMARY KEY,
  entry_date TEXT,
  entry_type TEXT,
  topics TEXT,
  title TEXT,
  summary TEXT,
  file_path TEXT,
  computer TEXT,
  created_at TEXT
)
"""

_MEMORY_DIR = "01_control-room/memory"


def _memory_root() -> Path:
    return paths.root / _MEMORY_DIR


@app.tool()
async def search_memory(
    query: str,
    entry_type: str = "",
) -> list[TextContent]:
    """Search the memory palace by keyword.

    Searches the memory_entries table (title, summary, topics) and performs a
    filesystem grep across 01_control-room/memory/**/*.md files.

    Args:
        query: Search keyword or phrase.
        entry_type: Optional filter -- "session", "journal", "idea", "decision", "topic".
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    results = []

    try:
        with connect(paths.db) as conn:
            conn.execute(_MEMORY_DDL)

            like = f"%{query}%"
            if entry_type:
                cur = conn.execute(
                    """SELECT entry_id, entry_date, entry_type, topics, title, summary, file_path
                       FROM memory_entries
                       WHERE entry_type = ?
                         AND (title LIKE ? OR summary LIKE ? OR topics LIKE ?)
                       ORDER BY entry_date DESC
                       LIMIT 20""",
                    (entry_type, like, like, like),
                )
            else:
                cur = conn.execute(
                    """SELECT entry_id, entry_date, entry_type, topics, title, summary, file_path
                       FROM memory_entries
                       WHERE title LIKE ? OR summary LIKE ? OR topics LIKE ?
                       ORDER BY entry_date DESC
                       LIMIT 20""",
                    (like, like, like),
                )

            rows = cur.fetchall()
            for row in rows:
                results.append(
                    f"[{row['entry_date']} | {row['entry_type']}] {row['title']}\n"
                    f"  Topics: {row['topics']}\n"
                    f"  {row['summary'][:200]}"
                )

    except Exception as e:
        return [TextContent(type="text", text=f"Error searching memory DB: {e}")]

    # Filesystem grep across memory markdown files
    fs_results = []
    mem_root = _memory_root()
    if mem_root.is_dir():
        try:
            proc = subprocess.run(
                ["grep", "-ril", query, str(mem_root)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0:
                matched_files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
                for fp in matched_files[:10]:
                    rel = Path(fp).relative_to(paths.root) if Path(fp).is_absolute() else fp
                    fs_results.append(f"  {rel}")
        except Exception:
            pass

    lines = []
    if results:
        lines.append(f"**{len(results)} DB matches for '{query}':**\n")
        lines.extend(results)
    else:
        lines.append(f"No DB entries found for '{query}'.")

    if fs_results:
        lines.append(f"\n**Filesystem matches ({len(fs_results)} files):**")
        lines.extend(fs_results)
    elif mem_root.is_dir():
        lines.append("\nNo filesystem matches found.")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def add_memory_entry(
    title: str,
    summary: str,
    topics: str,
    entry_type: str = "journal",
    detail: str = "",
    computer: str = "",
) -> list[TextContent]:
    """Add a new memory entry to the memory palace.

    Inserts into the memory_entries table. If detail is provided, also writes
    a markdown file under 01_control-room/memory/{entry_type}s/.

    Args:
        title: Short title for the entry.
        summary: One-paragraph summary (stored in DB, shown in search).
        topics: Comma-separated topic tags, e.g. "metis-setup,mcp-server".
        entry_type: One of "session", "journal", "idea", "decision", "topic".
        detail: Full markdown content for the .md file (optional).
        computer: Hostname of the computer this entry is from (optional).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    entry_date = now.strftime("%Y-%m-%d")
    created_at = now.isoformat()

    # Build entry_id from date + slugified title
    slug = title.lower()
    for ch in " /\\:*?\"<>|":
        slug = slug.replace(ch, "-")
    slug = "-".join(p for p in slug.split("-") if p)[:40]
    entry_id = f"mem-{entry_date.replace('-', '')}-{slug}"

    file_path = ""

    # Optionally write markdown file
    if detail:
        type_dir = _memory_root() / f"{entry_type}s"
        type_dir.mkdir(parents=True, exist_ok=True)
        md_filename = f"{entry_date}-{slug}.md"
        md_path = type_dir / md_filename
        try:
            md_path.write_text(detail, encoding="utf-8")
            file_path = str(md_path.relative_to(paths.root))
        except Exception as e:
            return [TextContent(type="text", text=f"Error writing markdown file: {e}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_MEMORY_DDL)
            conn.execute(
                """INSERT OR REPLACE INTO memory_entries
                   (entry_id, entry_date, entry_type, topics, title, summary, file_path, computer, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, entry_date, entry_type, topics, title, summary, file_path, computer, created_at),
            )
            conn.commit()

        parts = [f"Memory entry saved: **{title}**"]
        parts.append(f"- ID: {entry_id}")
        parts.append(f"- Type: {entry_type}")
        parts.append(f"- Topics: {topics}")
        if file_path:
            parts.append(f"- File: {file_path}")

        return [TextContent(type="text", text="\n".join(parts))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error saving memory entry: {e}")]


@app.tool()
async def get_topic_memory(topic: str) -> list[TextContent]:
    """Return all memory entries tagged with a specific topic, newest first.

    Args:
        topic: Topic tag to filter by (e.g. "metis-setup", "phd-research").
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_MEMORY_DDL)
            cur = conn.execute(
                """SELECT entry_id, entry_date, entry_type, topics, title, summary, file_path, computer
                   FROM memory_entries
                   WHERE topics LIKE ?
                   ORDER BY entry_date DESC""",
                (f"%{topic}%",),
            )
            rows = cur.fetchall()

        if not rows:
            return [TextContent(type="text", text=f"No memory entries found for topic '{topic}'.")]

        lines = [f"**{len(rows)} entries for topic '{topic}':**\n"]
        for row in rows:
            lines.append(
                f"### [{row['entry_date']}] {row['title']}"
            )
            lines.append(f"- Type: {row['entry_type']} | Computer: {row['computer'] or '-'}")
            lines.append(f"- Topics: {row['topics']}")
            lines.append(f"\n{row['summary'][:400]}")
            if row["file_path"]:
                lines.append(f"\n_File: {row['file_path']}_")
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving topic memory: {e}")]


@app.tool()
async def list_recent_memory(n: int = 10) -> list[TextContent]:
    """Return the n most recent memory entries (default 10).

    Useful at the start of a session to recall what was last worked on.

    Args:
        n: Number of entries to return (default 10).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_MEMORY_DDL)
            cur = conn.execute(
                """SELECT entry_id, entry_date, entry_type, topics, title, summary, computer
                   FROM memory_entries
                   ORDER BY entry_date DESC, created_at DESC
                   LIMIT ?""",
                (n,),
            )
            rows = cur.fetchall()

        if not rows:
            return [TextContent(type="text", text="No memory entries found.")]

        lines = [f"**{len(rows)} most recent memory entries:**\n"]
        for row in rows:
            lines.append(
                f"- [{row['entry_date']} | {row['entry_type']}] **{row['title']}**"
            )
            lines.append(f"  Topics: {row['topics']}")
            lines.append(f"  {row['summary'][:150]}")
            if row["computer"]:
                lines.append(f"  _Computer: {row['computer']}_")
            lines.append("")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error listing memory: {e}")]
