"""Search markdown notes across the PKM."""

import re
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.app_instance import app


def _query_words(query: str) -> list[str]:
    """The query as words, for all-words-must-appear matching.

    Plain substring matching fails on the way people actually search. A note reading
    "tiny targets NEEDS re-costing" does not match the query "tiny targets
    re-costing", because one word sits between them — so the researcher's own note
    is invisible to their own recollection of it. Requiring every word to appear
    (order-independent) fixes that while staying predictable and cheap.

    The exact phrase is still tried first by the callers, so a quoted-feeling exact
    search keeps ranking ahead of a loose word match.
    """
    return [w for w in re.split(r"\W+", query.lower()) if len(w) > 1]


def _line_matches(line_lower: str, query_lower: str, words: list[str]) -> bool:
    if query_lower in line_lower:
        return True
    return bool(words) and all(w in line_lower for w in words)


def _search_dir(directory: Path, query: str, limit: int) -> list[dict]:
    """Case-insensitive search in .md files under directory."""
    results = []
    query_lower = query.lower()
    words = _query_words(query)

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
                if _line_matches(line.lower(), query_lower, words):
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
    query: str,
    scope: str = "all",
    limit: int = 15,
    max_chars_per_result: int = 500,
) -> list[TextContent]:
    """Search markdown notes across domains, projects, and library.

    Case-insensitive substring search with surrounding context lines.

    Args:
        query: Search term.
        scope: Where to search -- "all", "domains", "projects", "library".
        limit: Maximum results (default 15).
        max_chars_per_result: Truncate each result's context to this many characters (default 500).
                              Pass 0 for no truncation.
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

    # Also search notes captured in the DASHBOARD (Keystone M7).
    #
    # Metis had two disjoint notes systems that could not see each other: this
    # tool greps .md files on disk, while the dashboard's capture modal writes rows
    # to `personal_notes`. A note typed into the dashboard was invisible to every
    # search in chat, and vice versa — the researcher had to remember WHERE a
    # thought was written in order to find it again, which is the one thing a
    # second brain exists to prevent.
    #
    # Searching both here unifies retrieval without a migration: the two stores
    # stay where they are, but one question reaches both.
    if scope in ("all", "projects") and len(results) < limit:
        try:
            from metis_mcp.config import paths as _paths
            from metis_mcp.db import connect as _connect

            # Same all-words semantics as the file search above, so a phrase
            # behaves identically whichever store the note happens to live in.
            _words = _query_words(query)
            _clauses = ["content LIKE ? COLLATE NOCASE"]
            _params: list = [f"%{query}%"]
            if _words:
                _clauses.append(
                    "(" + " AND ".join("content LIKE ? COLLATE NOCASE" for _ in _words) + ")"
                )
                _params += [f"%{w}%" for w in _words]
            with _connect(_paths.db) as _con:
                _rows = _con.execute(
                    "SELECT note_id, content, created_at, project_id FROM personal_notes "
                    f"WHERE {' OR '.join(_clauses)} "
                    "ORDER BY created_at DESC LIMIT ?",
                    (*_params, limit - len(results)),
                ).fetchall()
            for _r in _rows:
                results.append({
                    "file": f"[dashboard note {_r['created_at'][:10]}"
                            + (f" · {_r['project_id']}" if _r["project_id"] else "") + "]",
                    "line": 0,
                    "context": _r["content"],
                })
        except Exception:
            pass  # a missing/absent table must not break note search on disk

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
        context = r["context"]
        if max_chars_per_result > 0 and len(context) > max_chars_per_result:
            context = context[:max_chars_per_result] + "…"
        output_lines.append(f"### {rel} (line {r['line']})")
        output_lines.append(f"```\n{context}\n```\n")

    return [TextContent(type="text", text="\n".join(output_lines))]
