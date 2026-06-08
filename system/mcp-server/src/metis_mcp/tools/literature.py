"""Search the literature database (library_seeded table in SQLite)."""

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


@app.tool()
async def search_literature(
    query: str, field: str = "all", limit: int = 20
) -> list[TextContent]:
    """Search the user's literature database.

    Searches your curated/seeded literature catalogue by structured facets
    (disease, method, geography, keyword). For your Zotero/manual reference
    metadata use search_library; for full PDF body text use search_fulltext;
    for semantic RAG over indexed PDFs use search_pdf_knowledge.

    Searches the library_seeded SQLite table. Use this to find papers
    by disease focus, methodology, geography, or any keyword.

    Args:
        query: Search term, matched as a case-insensitive substring.
        field: Column to search -- one of "all", "disease", "method",
            "geography", or "article".
        limit: Maximum number of results to return (default 20).

    Returns:
        A single TextContent holding a markdown table of matching rows from the
        library_seeded table, or an error/"no results" message if the database,
        table, or column is missing or nothing matches.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    field_map = {
        "all": None,
        "disease": "disease",
        "method": "method",
        "geography": "geography",
        "article": "article",
    }

    if field not in field_map:
        return [
            TextContent(
                type="text",
                text=f"Invalid field '{field}'. Choose from: {', '.join(field_map.keys())}",
            )
        ]

    try:
        with connect(paths.db) as conn:
            # First check if the table exists
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

            # Get column names for the table
            cur = conn.execute("PRAGMA table_info(library_seeded)")
            columns = [row["name"] for row in cur.fetchall()]

            target = field_map[field]
            if target and target not in columns:
                return [
                    TextContent(
                        type="text",
                        text=f"Column '{target}' not found. Available: {', '.join(columns)}",
                    )
                ]

            # Build query
            pattern = f"%{query}%"
            if target:
                sql = f"SELECT * FROM library_seeded WHERE [{target}] LIKE ? LIMIT ?"
                params = (pattern, limit)
            else:
                # Search across all text columns
                clauses = [f"[{c}] LIKE ?" for c in columns]
                sql = f"SELECT * FROM library_seeded WHERE {' OR '.join(clauses)} LIMIT ?"
                params = tuple(pattern for _ in columns) + (limit,)

            cur = conn.execute(sql, params)
            rows = cur.fetchall()

            if not rows:
                return [
                    TextContent(
                        type="text",
                        text=f"No results for '{query}' in field '{field}'.",
                    )
                ]

            # Build markdown table
            headers = columns
            lines = ["| " + " | ".join(headers) + " |"]
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows:
                vals = [str(row[h] or "").replace("|", "/").replace("\n", " ")[:80] for h in headers]
                lines.append("| " + " | ".join(vals) + " |")

            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error searching literature: {e}")]
