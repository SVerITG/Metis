"""Search markdown notes across the PKM."""

from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.server import app


def _search_dir(directory: Path, query: str, limit: int) -> list[dict]:
    """Case-insensitive search in .md files under directory."""
    results = []
    query_lower = query.lower()

    if not directory.exists():
        return results

    try:
        for md_file in directory.rglob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            lines = text.splitlines()
            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    # Grab context: 1 line before and after
                    start = max(0, i - 1)
                    end = min(len(lines), i + 2)
                    context = "\n".join(lines[start:end])
                    results.append(
                        {
                            "file": str(md_file),
                            "line": i + 1,
                            "context": context,
                        }
                    )
                    if len(results) >= limit:
                        return results
    except Exception:
        pass

    return results


@app.tool()
async def search_notes(
    query: str, scope: str = "all", limit: int = 15
) -> list[TextContent]:
    """Search markdown notes across domains, projects, and library.

    Case-insensitive substring search with surrounding context lines.

    Args:
        query: Search term.
        scope: Where to search -- "all", "domains", "projects", "library".
        limit: Maximum results (default 15).
    """
    scope_dirs = {
        "domains": [paths.domains],
        "projects": [paths.projects_active],
        "library": [paths.library],
        "all": [paths.domains, paths.projects_active, paths.library],
    }

    if scope not in scope_dirs:
        return [
            TextContent(
                type="text",
                text=f"Invalid scope '{scope}'. Choose from: {', '.join(scope_dirs.keys())}",
            )
        ]

    results: list[dict] = []
    for d in scope_dirs[scope]:
        if len(results) >= limit:
            break
        results.extend(_search_dir(d, query, limit - len(results)))

    if not results:
        return [
            TextContent(
                type="text",
                text=f"No matches for '{query}' in scope '{scope}'.",
            )
        ]

    # Make paths relative to PKM root for readability
    output_lines = [f"**{len(results)} matches for '{query}':**\n"]
    for r in results:
        try:
            rel = Path(r["file"]).relative_to(paths.root)
        except ValueError:
            rel = r["file"]
        output_lines.append(f"### {rel} (line {r['line']})")
        output_lines.append(f"```\n{r['context']}\n```\n")

    return [TextContent(type="text", text="\n".join(output_lines))]
