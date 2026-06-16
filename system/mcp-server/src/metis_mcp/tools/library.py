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
    """Remove a library item from the Metis index, optionally deleting the file.

    De-indexes a paper or document by deleting its row from library_seeded. By
    default the file on disk is left untouched (index-only removal); set
    delete_file=True to also delete the file, which is guarded so only paths
    inside the PKM root can be removed. To hide rather than remove an item, use
    archive_library_item instead.

    Args:
        relative_path: The relative_path primary key identifying the row in the
            library_seeded table.
        delete_file: If True, also delete the underlying file from disk (subject
            to the within-PKM-root safety check); if False (default), only the
            index row is removed.

    Returns:
        A confirmation message of what was removed, or a not-found / error
        message if the item or table is missing.
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


def _slugify(text: str, maxlen: int = 80) -> str:
    """Filesystem-safe slug for a markdown note filename."""
    import re as _re
    s = _re.sub(r"[^\w\s-]", "", (text or "untitled").lower())
    s = _re.sub(r"[\s_-]+", "-", s).strip("-")
    return (s or "untitled")[:maxlen]


@app.tool()
async def export_knowledge_markdown(out_dir: str = "") -> list[TextContent]:
    """Export the library as a cross-linked Obsidian-style Markdown vault.

    Writes one Markdown note per library item (YAML frontmatter + abstract) plus
    an index, with [[wikilinks]] between items that share a tag — the
    claude-obsidian / LLM-Wiki pattern. Gives you a portable, human-readable,
    git-diffable view of the knowledge graph you can open in Obsidian. Read-only
    on the database; writes only Markdown.

    Args:
        out_dir: Destination folder. Default: outputs/knowledge-export/ under the RC root.
    """
    from pathlib import Path as _Path

    base = _Path(out_dir) if out_dir else (paths.root / "outputs" / "knowledge-export")
    notes_dir = base / "notes"
    try:
        notes_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return [TextContent(type="text", text=f"Could not create {base}: {e}")]

    try:
        with connect(paths.db) as conn:
            rows = conn.execute(
                "SELECT id, title, authors, year, journal, source, tags, doi, url, abstract "
                "FROM literature_metadata WHERE title IS NOT NULL AND title != '' "
                "ORDER BY year DESC, title"
            ).fetchall()
    except Exception as e:
        return [TextContent(type="text", text=f"DB read error: {e}")]

    if not rows:
        return [TextContent(type="text", text="No library items to export.")]

    # Build tag → [item] index for cross-linking, and assign unique slugs.
    def _tags_of(r):
        return [t.strip() for t in (r["tags"] or "").split(",") if t.strip()]

    slugs: dict = {}
    used: set = set()
    for r in rows:
        s = _slugify(r["title"])
        orig = s
        i = 2
        while s in used:
            s = f"{orig}-{i}"
            i += 1
        used.add(s)
        slugs[r["id"]] = s

    tag_index: dict = {}
    for r in rows:
        for t in _tags_of(r):
            tag_index.setdefault(t.lower(), []).append(r["id"])

    written = 0
    for r in rows:
        tags = _tags_of(r)
        # Related = other items sharing any tag (capped).
        related_ids: list = []
        seen = {r["id"]}
        for t in tags:
            for oid in tag_index.get(t.lower(), []):
                if oid not in seen:
                    seen.add(oid)
                    related_ids.append(oid)
        related_ids = related_ids[:8]

        title = (r["title"] or "Untitled").replace('"', "'")
        fm = [
            "---",
            f'title: "{title}"',
            f'authors: "{(r["authors"] or "").replace(chr(34), chr(39))}"',
            f"year: {r['year'] or ''}",
            f'journal: "{(r["journal"] or r["source"] or "").replace(chr(34), chr(39))}"',
            f'doi: "{r["doi"] or ""}"',
            # Quote every tag: MeSH tags can start with '*' (a YAML alias) or
            # contain '/' ':' — unquoted they produce invalid YAML frontmatter.
            "tags: [" + ", ".join('"' + t.replace('"', "'") + '"' for t in tags) + "]",
            "---",
            "",
            f"# {title}",
            "",
        ]
        if r["authors"]:
            fm.append(f"**Authors:** {r['authors']}  ")
        if r["year"]:
            fm.append(f"**Year:** {r['year']}  ")
        if r["doi"]:
            fm.append(f"**DOI:** [{r['doi']}](https://doi.org/{r['doi']})  ")
        elif r["url"]:
            fm.append(f"**Link:** {r['url']}  ")
        if r["abstract"]:
            fm += ["", "## Abstract", "", r["abstract"]]
        if related_ids:
            fm += ["", "## Related", ""]
            fm += [f"- [[{slugs[oid]}]]" for oid in related_ids]
        fm += ["", f"_Tags: {', '.join(tags) if tags else 'none'}_", ""]

        try:
            (notes_dir / f"{slugs[r['id']]}.md").write_text("\n".join(fm), encoding="utf-8")
            written += 1
        except Exception:
            continue

    # Index grouped by tag.
    idx = ["# Knowledge Vault — Index", "", f"{written} notes · {len(tag_index)} tags", ""]
    for tag in sorted(tag_index):
        idx.append(f"## {tag}")
        for oid in tag_index[tag][:50]:
            idx.append(f"- [[{slugs[oid]}]]")
        idx.append("")
    try:
        (base / "_index.md").write_text("\n".join(idx), encoding="utf-8")
    except Exception:
        pass

    return [TextContent(type="text", text=(
        f"Knowledge vault exported: {written} notes + index → {base}\n"
        f"Open the folder in Obsidian; [[wikilinks]] connect items sharing tags."
    ))]
