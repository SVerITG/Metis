"""PhD context retrieval from the PKM structure and SQLite."""

from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.server import app


def _read_dir_markdown(directory: Path) -> str:
    """Read and concatenate all .md files in a directory."""
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

    return "\n\n---\n\n".join(parts) if parts else "_No markdown files found._"


@app.tool()
async def get_phd_context(section: str = "overview") -> list[TextContent]:
    """Retrieve PhD project context from the PKM.

    Gathers information about the PhD structure, articles, milestones,
    and methods to help with PhD planning and writing.

    Args:
        section: What to retrieve -- "overview", "articles", "milestones", "methods".
    """
    phd_root = paths.phd

    if not phd_root.exists():
        return [
            TextContent(
                type="text",
                text=f"PhD directory not found: {phd_root}",
            )
        ]

    if section == "overview":
        center = phd_root / "00_center"
        text = f"# PhD Overview\n\n{_read_dir_markdown(center)}"
        return [TextContent(type="text", text=text)]

    elif section == "articles":
        articles = phd_root / "01_current-articles"
        text = f"# PhD Articles\n\n{_read_dir_markdown(articles)}"
        return [TextContent(type="text", text=text)]

    elif section == "milestones":
        if not paths.db.exists():
            return [
                TextContent(type="text", text=f"Database not found: {paths.db}")
            ]
        try:
            with connect(paths.db) as conn:
                cur = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='phd_milestones'"
                )
                if not cur.fetchone():
                    return [
                        TextContent(
                            type="text",
                            text="Table 'phd_milestones' not found in database.",
                        )
                    ]

                cur = conn.execute(
                    "SELECT * FROM phd_milestones ORDER BY due_date"
                )
                rows = cur.fetchall()

                if not rows:
                    return [
                        TextContent(type="text", text="No milestones found.")
                    ]

                columns = [desc[0] for desc in cur.description]
                lines = [
                    "# PhD Milestones\n",
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
        methods = phd_root / "03_methods"
        text = f"# PhD Methods\n\n{_read_dir_markdown(methods)}"
        return [TextContent(type="text", text=text)]

    else:
        return [
            TextContent(
                type="text",
                text=f"Unknown section '{section}'. Choose from: overview, articles, milestones, methods.",
            )
        ]
