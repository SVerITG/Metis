"""Research context retrieval from the PKM structure and SQLite."""

from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


def _read_dir_markdown(directory: Path, max_chars: int = 0) -> str:
    """Read and concatenate all .md files in a directory.

    Args:
        directory: Directory to read from.
        max_chars: If > 0, truncate combined output to this many characters.
    """
    if not directory.exists():
        return f"_Directory not found: {directory}_"

    parts = []
    try:
        for md in sorted(directory.rglob("*.md")):
            try:
                rel = md.relative_to(directory)
                text = md.read_text(encoding="utf-8")
                parts.append(f"## {rel}\n\n{text}")
            except (OSError, UnicodeDecodeError) as e:
                parts.append(f"## {md.name}\n\n_Error reading: {e}_")
    except Exception as e:
        return f"_Error scanning directory: {e}_"

    combined = "\n\n---\n\n".join(parts) if parts else "_No markdown files found._"

    if max_chars > 0 and len(combined) > max_chars:
        combined = (
            combined[:max_chars]
            + f"\n\n_[Truncated at {max_chars} chars. Request a specific subsection for full detail.]_"
        )

    return combined


@app.tool()
async def get_research_context(
    section: str = "overview", max_chars: int = 8000
) -> list[TextContent]:
    """Retrieve research project context from the PKM.

    Gathers information about the research structure, articles, milestones,
    and methods to help with research planning and writing.

    Args:
        section: What to retrieve -- "overview", "articles", "milestones", "methods".
        max_chars: Maximum characters to return for file-based sections (default 8000).
                   Pass 0 for no limit.
    """
    research_root = paths.research

    if not research_root.exists():
        return [
            TextContent(
                type="text",
                text=f"Research directory not found: {research_root}",
            )
        ]

    if section == "overview":
        center = research_root / "00_center"
        text = f"# Research Overview\n\n{_read_dir_markdown(center, max_chars)}"
        return [TextContent(type="text", text=text)]

    elif section == "articles":
        articles = research_root / "01_current-articles"
        text = f"# Research Articles\n\n{_read_dir_markdown(articles, max_chars)}"
        return [TextContent(type="text", text=text)]

    elif section == "milestones":
        if not paths.db.exists():
            return [
                TextContent(type="text", text=f"Database not found: {paths.db}")
            ]
        try:
            with connect(paths.db) as conn:
                # Support both new and legacy table names
                for table_name in ("research_milestones", "phd_milestones"):
                    cur = conn.execute(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                    )
                    if cur.fetchone():
                        break
                else:
                    return [
                        TextContent(
                            type="text",
                            text="Table 'research_milestones' not found in database.",
                        )
                    ]

                cur = conn.execute(
                    f"SELECT * FROM {table_name} ORDER BY due_date"
                )
                rows = cur.fetchall()

                if not rows:
                    return [
                        TextContent(type="text", text="No milestones found.")
                    ]

                columns = [desc[0] for desc in cur.description]
                lines = [
                    "# Research Milestones\n",
                    "| " + " | ".join(columns) + " |",
                    "| " + " | ".join("---" for _ in columns) + " |",
                ]
                for row in rows:
                    vals = [str(row[c] or "") for c in columns]
                    lines.append("| " + " | ".join(vals) + " |")

                return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            return [
                TextContent(type="text", text=f"Error reading milestones: {e}")
            ]

    elif section == "methods":
        methods = research_root / "03_methods"
        text = f"# Research Methods\n\n{_read_dir_markdown(methods, max_chars)}"
        return [TextContent(type="text", text=text)]

    else:
        return [
            TextContent(
                type="text",
                text=f"Unknown section '{section}'. Choose from: overview, articles, milestones, methods.",
            )
        ]
