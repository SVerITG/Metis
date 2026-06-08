"""
tools/knowledge_graph.py — Phase 5.8: Knowledge graph tools.

Three MCP tools:

  kg_index_notes()
      Scan all knowledge/library/ .md files, parse YAML frontmatter,
      and populate the note_links table with bidirectional related-concept
      edges. Safe to re-run — uses REPLACE into the unique index.

  kg_paths(from_path, to_path, max_hops)
      BFS traversal of note_links to find connection paths between two
      library notes. Returns all paths up to max_hops length.

  kg_community(note_path)
      Return the connected cluster around a given note (BFS flood-fill,
      depth-limited). Useful for surfacing related concepts when working
      on a specific topic.
"""

import json
from collections import deque
from pathlib import Path
from typing import Optional

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS note_links (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path  TEXT NOT NULL,
    target_path  TEXT NOT NULL,
    link_type    TEXT NOT NULL DEFAULT 'related',
    source_title TEXT,
    target_title TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_note_links_uniq
    ON note_links(source_path, target_path);
CREATE INDEX IF NOT EXISTS idx_note_links_source
    ON note_links(source_path);
CREATE INDEX IF NOT EXISTS idx_note_links_target
    ON note_links(target_path);
"""


def _ensure_table(conn):
    for stmt in _DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()


# ---------------------------------------------------------------------------
# Frontmatter parser (no PyYAML dependency — simple key/list extraction)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict:
    """Parse a minimal YAML frontmatter block (---...---) from a .md file."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end].strip()
    result = {}
    current_key = None
    current_list = None

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item
        if stripped.startswith("- "):
            val = stripped[2:].strip().strip('"').strip("'")
            if current_list is not None:
                current_list.append(val)
            continue

        # Key: value
        if ":" in stripped:
            colon = stripped.index(":")
            key = stripped[:colon].strip()
            val = stripped[colon + 1:].strip().strip('"').strip("'")
            current_key = key
            if val == "":
                # Next lines are list items
                current_list = []
                result[key] = current_list
            else:
                result[key] = val
                current_list = None

    return result


# ---------------------------------------------------------------------------
# Wikilink parser — [[Target]] / [[Target|alias]] from note bodies
# ---------------------------------------------------------------------------

import re as _re

_WIKILINK_RE = _re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]")


def _strip_frontmatter(text: str) -> str:
    """Return the note body with any leading YAML frontmatter removed."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            nl = text.find("\n", end + 1)
            return text[nl + 1:] if nl != -1 else ""
    return text


def _extract_wikilinks(text: str) -> list[str]:
    """Extract [[wikilink]] targets from a note body (ignores ``code`` fences)."""
    body = _strip_frontmatter(text)
    # Drop fenced code blocks so example [[...]] inside code aren't treated as links
    body = _re.sub(r"```.*?```", "", body, flags=_re.DOTALL)
    seen, out = set(), []
    for m in _WIKILINK_RE.findall(body):
        t = m.strip()
        key = t.lower()
        if t and key not in seen:
            seen.add(key)
            out.append(t)
    return out


# ---------------------------------------------------------------------------
# M5.8.2 + M5.8.3a — kg_index_notes
# ---------------------------------------------------------------------------

@app.tool()
def _obsidian_vault() -> "Path | None":
    """Resolve the configured Obsidian vault path, if one is set and valid.

    Looks up the user's external Obsidian vault so note-indexing tools
    (e.g. kg_index_notes) know where to read .md notes from. Checks the
    METIS_OBSIDIAN_VAULT environment variable first, then the
    integrations.obsidian_vault (or top-level obsidian_vault) key in
    user-config.yaml.

    Takes no arguments.

    Returns:
        A Path to the vault directory if it is configured and exists on disk,
        otherwise None.
    """
    import os as _os
    p = _os.environ.get("METIS_OBSIDIAN_VAULT", "").strip()
    if not p:
        try:
            import yaml as _yaml
            cfg = paths.config / "user-config.yaml"
            if cfg.exists():
                data = _yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
                p = ((data.get("integrations") or {}).get("obsidian_vault")
                     or data.get("obsidian_vault") or "")
        except Exception:
            p = ""
    if not p:
        return None
    vp = Path(p)
    return vp if vp.exists() and vp.is_dir() else None


async def kg_index_notes() -> list[TextContent]:
    """Index .md notes into the knowledge graph: knowledge/library/ plus, if
    configured, an external Obsidian vault. Parses YAML frontmatter `related:`
    and `[[wikilinks]]` from note bodies into bidirectional note_links edges.

    Configure a vault via METIS_OBSIDIAN_VAULT env var or `obsidian_vault:` in
    user-config.yaml. Re-running is safe (REPLACE semantics).
    """
    library_root = paths.library
    if not library_root.exists():
        return [TextContent(type="text", text="ERROR: knowledge/library/ directory not found")]

    vault_root = _obsidian_vault()

    with connect(paths.db) as conn:
        _ensure_table(conn)
        conn.execute("DELETE FROM note_links")
        conn.commit()

        indexed = 0
        edges = 0
        wiki_edges = 0
        skipped = []
        vault_notes = 0

        # Collect (root, path-prefix) sources. Vault files get a 'vault:' prefix
        # on their rel_path to avoid collisions with library paths.
        sources = [(library_root, "")]
        if vault_root:
            sources.append((vault_root, "vault:"))

        # ── Pass 1: build a resolution index so [[wikilinks]] and related: paths
        #    can be matched by title, filename stem, or relative path. ──────────
        files = []  # (rel_path, text, fm, title)
        title_index: dict[str, tuple[str, str]] = {}  # key -> (rel_path, title)
        for root, prefix in sources:
            for md_file in sorted(root.rglob("*.md")):
                rel_path = prefix + str(md_file.relative_to(root))
                text = md_file.read_text(encoding="utf-8", errors="replace")
                fm = _parse_frontmatter(text)
                title = (fm.get("title") if fm else None) or md_file.stem.replace("-", " ").title()
                files.append((rel_path, text, fm, title))
                if prefix:
                    vault_notes += 1
                for key in {title.lower(), md_file.stem.lower(), rel_path.lower()}:
                    title_index.setdefault(key, (rel_path, title))

        def _resolve(target: str) -> tuple[str, str]:
            """Resolve a link target to (path, title); fall back to the raw string."""
            t = target.strip().strip('"').strip("'")
            hit = title_index.get(t.lower())
            if hit:
                return hit
            return (t, t)

        def _add_pair(src_path, src_title, tgt_path, tgt_title, link_type):
            conn.execute(
                """INSERT OR REPLACE INTO note_links
                   (source_path, target_path, link_type, source_title, target_title)
                   VALUES (?, ?, ?, ?, ?)""",
                (src_path, tgt_path, link_type, src_title, tgt_title),
            )
            conn.execute(
                """INSERT OR REPLACE INTO note_links
                   (source_path, target_path, link_type, source_title, target_title)
                   VALUES (?, ?, ?, ?, ?)""",
                (tgt_path, src_path, link_type, tgt_title, src_title),
            )

        # ── Pass 2: emit edges from both related: frontmatter and [[wikilinks]] ──
        for rel_path, text, fm, title in files:
            related = (fm.get("related", []) if fm else [])
            if isinstance(related, str):
                related = [related]
            wikilinks = _extract_wikilinks(text)

            # A note counts as indexed if it has frontmatter OR any link.
            if not fm and not wikilinks:
                skipped.append(rel_path)
                continue
            indexed += 1

            for target in related:
                tgt_path, tgt_title = _resolve(target)
                _add_pair(rel_path, title, tgt_path, tgt_title, "related")
                edges += 1

            for target in wikilinks:
                tgt_path, tgt_title = _resolve(target)
                if tgt_path == rel_path:
                    continue  # skip self-links
                _add_pair(rel_path, title, tgt_path, tgt_title, "wikilink")
                wiki_edges += 1

        conn.commit()

    vault_note = f" · {vault_notes} from Obsidian vault" if vault_root else ""
    lines = [
        f"Knowledge graph indexed: {indexed} notes{vault_note}, "
        f"{(edges + wiki_edges) * 2} directed edges "
        f"({edges} related: + {wiki_edges} [[wikilink]] bidirectional pairs)",
        "",
    ]
    if skipped:
        lines.append(f"Skipped (no frontmatter): {', '.join(skipped)}")

    return [TextContent(type="text", text="\n".join(lines))]


# ---------------------------------------------------------------------------
# M5.8.3b — kg_paths
# ---------------------------------------------------------------------------

@app.tool()
async def kg_paths(
    from_path: str,
    to_path: str,
    max_hops: int = 4,
) -> list[TextContent]:
    """Find connection paths between two knowledge library notes via BFS.

    Args:
        from_path: Relative path from knowledge/library/ (e.g. 'concepts/elimination-framework.md')
        to_path:   Target note path.
        max_hops:  Maximum path length (default 4).

    Returns all paths found up to max_hops, ranked by length.
    """
    with connect(paths.db) as conn:
        _ensure_table(conn)

        # Build adjacency from note_links
        rows = conn.execute(
            "SELECT source_path, target_path, source_title, target_title FROM note_links"
        ).fetchall()

    # adjacency: source → list of (target, target_title)
    adj: dict[str, list[tuple[str, str]]] = {}
    titles: dict[str, str] = {}
    for src, tgt, src_title, tgt_title in rows:
        adj.setdefault(src, []).append((tgt, tgt_title or tgt))
        titles[src] = src_title or src
        titles[tgt] = tgt_title or tgt

    if from_path not in adj and from_path not in titles:
        return [TextContent(type="text", text=f"Note not in graph: {from_path}\nRun kg_index_notes first.")]

    if from_path == to_path:
        return [TextContent(type="text", text="Source and target are the same note.")]

    # BFS — find all paths up to max_hops
    found_paths = []
    queue = deque([[from_path]])
    visited_states: set[tuple] = set()

    while queue:
        path = queue.popleft()
        current = path[-1]

        if len(path) > max_hops + 1:
            continue

        state = tuple(path)
        if state in visited_states:
            continue
        visited_states.add(state)

        if current == to_path:
            found_paths.append(path)
            continue

        for neighbor, _ in adj.get(current, []):
            if neighbor not in path:  # no cycles
                queue.append(path + [neighbor])

    if not found_paths:
        return [TextContent(
            type="text",
            text=f"No path found between '{from_path}' and '{to_path}' within {max_hops} hops.",
        )]

    found_paths.sort(key=len)
    lines = [
        f"Paths from '{titles.get(from_path, from_path)}' → '{titles.get(to_path, to_path)}':",
        "",
    ]
    for i, path in enumerate(found_paths[:5], 1):
        hop_labels = [titles.get(p, p) for p in path]
        lines.append(f"  Path {i} ({len(path) - 1} hops): " + " → ".join(hop_labels))

    return [TextContent(type="text", text="\n".join(lines))]


# ---------------------------------------------------------------------------
# M5.8.3c — kg_community
# ---------------------------------------------------------------------------

@app.tool()
async def kg_community(
    note_path: str,
    depth: int = 2,
) -> list[TextContent]:
    """Return the connected cluster around a given knowledge library note.

    Performs BFS flood-fill from the given note up to `depth` hops,
    returning all reachable notes grouped by distance. Useful for surfacing
    related concepts when working on a specific topic.

    Args:
        note_path: Relative path from knowledge/library/ (e.g. 'disease-areas/[condition].md')
        depth:     Maximum hop distance to explore (default 2).
    """
    with connect(paths.db) as conn:
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT source_path, target_path, source_title, target_title FROM note_links"
        ).fetchall()

    adj: dict[str, list[tuple[str, str]]] = {}
    titles: dict[str, str] = {}
    tags_map: dict[str, list[str]] = {}

    for src, tgt, src_title, tgt_title in rows:
        adj.setdefault(src, []).append((tgt, tgt_title or tgt))
        titles[src] = src_title or src
        titles[tgt] = tgt_title or tgt

    # Also pull domain/tags from frontmatter for richer output
    library_root = paths.library
    if library_root.exists():
        for md_file in library_root.rglob("*.md"):
            rel = str(md_file.relative_to(library_root))
            try:
                fm = _parse_frontmatter(md_file.read_text(encoding="utf-8", errors="replace"))
                if fm:
                    tags = fm.get("tags", [])
                    if isinstance(tags, str):
                        tags = [tags]
                    tags_map[rel] = tags
            except Exception:
                pass

    if note_path not in adj and note_path not in titles:
        return [TextContent(type="text", text=f"Note not in graph: {note_path}\nRun kg_index_notes first.")]

    # BFS by depth level
    visited = {note_path: 0}
    queue = deque([(note_path, 0)])
    levels: dict[int, list[str]] = {0: [note_path]}

    while queue:
        current, d = queue.popleft()
        if d >= depth:
            continue
        for neighbor, _ in adj.get(current, []):
            if neighbor not in visited:
                visited[neighbor] = d + 1
                levels.setdefault(d + 1, []).append(neighbor)
                queue.append((neighbor, d + 1))

    root_title = titles.get(note_path, note_path)
    lines = [f"Knowledge cluster around: {root_title}", "=" * 50, ""]

    for level in range(1, depth + 1):
        nodes = levels.get(level, [])
        if not nodes:
            continue
        lines.append(f"Hop {level} ({len(nodes)} notes):")
        for n in sorted(nodes):
            t = titles.get(n, n)
            tags = tags_map.get(n, [])
            tag_str = f"  [{', '.join(tags[:4])}]" if tags else ""
            lines.append(f"  • {t}{tag_str}")
            lines.append(f"    path: {n}")
        lines.append("")

    total = sum(len(v) for k, v in levels.items() if k > 0)
    lines.append(f"Total: {total} related notes within {depth} hops")

    return [TextContent(type="text", text="\n".join(lines))]
