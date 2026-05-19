"""Library management tools: archive, remove, and extended search for library_seeded."""

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

_STATUS_MIGRATE = "ALTER TABLE library_seeded ADD COLUMN status TEXT DEFAULT 'active'"


def _ensure_status_column(conn) -> None:
    """Add status column to library_seeded if it does not yet exist."""
    cur = conn.execute("PRAGMA table_info(library_seeded)")
    columns = [row["name"] for row in cur.fetchall()]
    if "status" not in columns:
        try:
            conn.execute(_STATUS_MIGRATE)
        except Exception:
            pass  # Column was added by a concurrent caller


@app.tool()
async def archive_library_item(relative_path: str) -> list[TextContent]:
    """Archive a library item (mark as no longer active but keep in DB).

    Sets status='archived' in library_seeded table. Item stays available
    for search and cross-pollination but disappears from default view.

    Args:
        relative_path: The relative_path primary key in library_seeded table.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='library_seeded'"
            )
            if not cur.fetchone():
                return [
                    TextContent(
                        type="text",
                        text="Table 'library_seeded' not found in database.",
                    )
                ]

            _ensure_status_column(conn)

            # Check item exists
            cur = conn.execute(
                "SELECT relative_path FROM library_seeded WHERE relative_path = ?",
                (relative_path,),
            )
            if not cur.fetchone():
                return [
                    TextContent(
                        type="text",
                        text=f"Item not found in library_seeded: '{relative_path}'",
                    )
                ]

            conn.execute(
                "UPDATE library_seeded SET status = 'archived' WHERE relative_path = ?",
                (relative_path,),
            )
            conn.commit()

        return [
            TextContent(
                type="text",
                text=f"Archived library item: '{relative_path}'\nStatus set to 'archived'. Item remains in the database and is still searchable.",
            )
        ]

    except Exception as e:
        return [TextContent(type="text", text=f"Error archiving library item: {e}")]


@app.tool()
async def remove_library_item(
    relative_path: str, delete_file: bool = False
) -> list[TextContent]:
    """Remove a library item from the Metis index.

    Deletes the row from library_seeded. If delete_file=True, also deletes
    the actual file from disk (only if path is within PKM root — safety check required).

    Args:
        relative_path: The relative_path primary key in library_seeded table.
        delete_file: If True, also delete the file from disk. Default False.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='library_seeded'"
            )
            if not cur.fetchone():
                return [
                    TextContent(
                        type="text",
                        text="Table 'library_seeded' not found in database.",
                    )
                ]

            # Check item exists and grab basename for reporting
            cur = conn.execute(
                "SELECT relative_path, basename FROM library_seeded WHERE relative_path = ?",
                (relative_path,),
            )
            row = cur.fetchone()
            if not row:
                return [
                    TextContent(
                        type="text",
                        text=f"Item not found in library_seeded: '{relative_path}'",
                    )
                ]

            basename = row["basename"] if "basename" in row.keys() else relative_path

            conn.execute(
                "DELETE FROM library_seeded WHERE relative_path = ?",
                (relative_path,),
            )
            conn.commit()

        messages = [f"Removed library item from index: '{relative_path}' ({basename})"]

        if delete_file:
            # Resolve the literature root from the metadata path
            literature_root = paths.literature_metadata.parent.parent
            file_path = (literature_root / relative_path).resolve()
            pkm_root = str(paths.root.resolve())

            if not str(file_path).startswith(pkm_root):
                messages.append(
                    f"Safety check failed: resolved path '{file_path}' is outside PKM root '{pkm_root}'. File was NOT deleted."
                )
            elif not file_path.exists():
                messages.append(
                    f"File not found on disk (already gone?): '{file_path}'"
                )
            else:
                file_path.unlink()
                messages.append(f"Deleted file from disk: '{file_path}'")

        return [TextContent(type="text", text="\n".join(messages))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error removing library item: {e}")]


@app.tool()
async def search_literature_extended(
    query: str,
    include_archived: bool = False,
    limit: int = 20,
) -> list[TextContent]:
    """Search literature with optional inclusion of archived items.

    Searches library_seeded table across basename, relevance_note, disease,
    geography, method fields. By default excludes archived items.

    Args:
        query: Search term.
        include_archived: Include items with status='archived'. Default False.
        limit: Max results. Default 20.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='library_seeded'"
            )
            if not cur.fetchone():
                return [
                    TextContent(
                        type="text",
                        text="Table 'library_seeded' not found in database.",
                    )
                ]

            _ensure_status_column(conn)

            # Get actual columns present in the table
            cur = conn.execute("PRAGMA table_info(library_seeded)")
            all_columns = [row["name"] for row in cur.fetchall()]

            # Preferred search columns (use only those that actually exist)
            preferred_search = ["basename", "relevance_note", "disease", "geography", "method"]
            search_columns = [c for c in preferred_search if c in all_columns]

            if not search_columns:
                # Fall back to all text-like columns if none of the preferred ones exist
                search_columns = all_columns

            pattern = f"%{query}%"
            clauses = [f"[{c}] LIKE ?" for c in search_columns]
            match_filter = f"({' OR '.join(clauses)})"

            if include_archived:
                sql = f"SELECT * FROM library_seeded WHERE {match_filter} LIMIT ?"
                params = tuple(pattern for _ in search_columns) + (limit,)
            else:
                # Exclude archived: status IS NULL (old rows) or status != 'archived'
                sql = (
                    f"SELECT * FROM library_seeded "
                    f"WHERE {match_filter} "
                    f"AND (status IS NULL OR status != 'archived') "
                    f"LIMIT ?"
                )
                params = tuple(pattern for _ in search_columns) + (limit,)

            cur = conn.execute(sql, params)
            rows = cur.fetchall()

            if not rows:
                archived_note = "" if include_archived else " (archived items excluded)"
                return [
                    TextContent(
                        type="text",
                        text=f"No results for '{query}'{archived_note}.",
                    )
                ]

            # Build markdown table using all columns
            headers = all_columns
            lines = ["| " + " | ".join(headers) + " |"]
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows:
                vals = [
                    str(row[h] or "").replace("|", "/").replace("\n", " ")[:80]
                    for h in headers
                ]
                lines.append("| " + " | ".join(vals) + " |")

            archived_note = " (including archived)" if include_archived else ""
            header_line = f"Results for '{query}'{archived_note}: {len(rows)} item(s)\n\n"
            return [TextContent(type="text", text=header_line + "\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error searching literature: {e}")]
