"""Ideas, journal, contacts, glossary, cross-pollination, and brainstorm tools."""

import datetime
import re

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app

_IDEAS_DDL = """
CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    source TEXT DEFAULT 'manual',
    mood TEXT DEFAULT '',
    energy INTEGER DEFAULT 0,
    tags TEXT DEFAULT '',
    domain_links TEXT DEFAULT '',
    project_links TEXT DEFAULT '',
    image_path TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    week TEXT NOT NULL
)
"""

_JOURNAL_DDL = """
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    mood TEXT DEFAULT '',
    energy_score INTEGER DEFAULT 0,
    summary TEXT DEFAULT '',
    image_path TEXT DEFAULT '',
    created_at TEXT NOT NULL
)
"""

_CONTACTS_DDL = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    birthday TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    updated_at TEXT NOT NULL
)
"""

_GLOSSARY_DDL = """
CREATE TABLE IF NOT EXISTS glossary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL UNIQUE,
    definition TEXT DEFAULT '',
    created_at TEXT NOT NULL
)
"""

# Simple keyword lists for auto-extraction
_MOOD_KEYWORDS = {
    "happy", "sad", "anxious", "calm", "excited", "frustrated", "tired",
    "energetic", "stressed", "relaxed", "motivated", "overwhelmed",
    "grateful", "inspired", "bored", "focused", "scattered", "hopeful",
}

_ENERGY_MAP = {
    "exhausted": 1, "tired": 2, "low": 2, "ok": 3, "normal": 3,
    "good": 4, "energetic": 5, "high": 5,
}


def _extract_tags(content: str) -> str:
    """Extract simple keyword tags from content."""
    # Look for hashtags first
    hashtags = re.findall(r"#(\w+)", content)
    if hashtags:
        return ",".join(hashtags[:10])
    # Fall back to extracting significant words (>5 chars, not common)
    stopwords = {"about", "after", "before", "between", "could", "should",
                 "would", "their", "there", "which", "where", "these", "those"}
    words = re.findall(r"\b[a-zA-Z]{5,}\b", content.lower())
    unique = []
    seen = set()
    for w in words:
        if w not in stopwords and w not in seen:
            seen.add(w)
            unique.append(w)
        if len(unique) >= 5:
            break
    return ",".join(unique)


def _extract_mood(content: str) -> str:
    """Extract mood keywords from content."""
    words = set(re.findall(r"\b\w+\b", content.lower()))
    found = words & _MOOD_KEYWORDS
    return ",".join(sorted(found)) if found else ""


def _extract_energy(content: str) -> int:
    """Extract energy score from content (0 = not detected)."""
    words = set(re.findall(r"\b\w+\b", content.lower()))
    for keyword, score in _ENERGY_MAP.items():
        if keyword in words:
            return score
    return 0


def _iso_week(dt: datetime.datetime) -> str:
    """Return ISO week string like '2026-W14'."""
    cal = dt.isocalendar()
    return f"{cal[0]}-W{cal[1]:02d}"


def _cross_pollinate_core(content: str, max_results: int = 5) -> list[dict]:
    """Hybrid vector + keyword cross-pollination with RRF merge and title dedup.

    1. Vector search against episodic_memory (ideas/notes embedded at capture time).
    2. Keyword SQL search across library, meetings, news, ideas tables.
    3. RRF merge to combine both result sets.
    4. Title-dedup pass for diversity (MMR-lite).
    """
    if not paths.db.exists():
        return []

    # ── 1. Vector search (episodic memory) ───────────────────────────────────
    vec_hits: list[dict] = []
    try:
        import struct
        import sqlite_vec
        from metis_mcp.embeddings import embed_query
        from metis_mcp.tools.vector_memory import _setup_tables, _encode_vec

        qvec = embed_query(content)
        qbytes = _encode_vec(qvec)

        with connect(paths.db) as conn:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            _setup_tables(conn)

            rows = conn.execute(
                """SELECT e.id, e.event_type, e.content, e.created_at, v.distance
                     FROM vec_episodic v
                     JOIN episodic_memory e ON e.id = v.rowid
                    WHERE v.embedding MATCH ?
                      AND k = ?
                    ORDER BY v.distance""",
                (qbytes, max_results * 3),
            ).fetchall()

            for i, r in enumerate(rows):
                vec_hits.append({
                    "source": r["event_type"] or "memory",
                    "title": (r["content"] or "")[:120],
                    "snippet": "",
                    "_key": f"episodic:{r['id']}",
                    "_vec_rank": i + 1,
                })
    except Exception:
        pass  # vector search unavailable — fall back to SQL only

    # ── 2. Keyword SQL search ─────────────────────────────────────────────────
    words = re.findall(r"\b[a-zA-Z]{4,}\b", content.lower())
    stopwords = {"about", "after", "before", "between", "could", "should",
                 "would", "their", "there", "which", "where", "these", "those",
                 "with", "from", "have", "been", "this", "that", "into", "also"}
    keywords = [w for w in words if w not in stopwords][:8]

    sql_hits: list[dict] = []
    if keywords:
        try:
            with connect(paths.db) as conn:
                conn.execute(_IDEAS_DDL)
                # literature_metadata has title + abstract from Zotero — primary library source
                _search_table(conn, "literature_metadata", ["title", "abstract", "tags"],
                              keywords, "library", sql_hits, max_results * 2)
                # library_seeded as fallback (file-level metadata)
                _search_table(conn, "library_seeded", ["title", "relevance_note"],
                              keywords, "library", sql_hits, max_results)
                _search_table(conn, "meetings", ["title", "transcript", "decisions"],
                              keywords, "meeting", sql_hits, max_results)
                _search_table(conn, "news_briefs", ["title", "summary"],
                              keywords, "news", sql_hits, max_results)
                _search_table(conn, "ideas", ["content", "title"],
                              keywords, "idea", sql_hits, max_results)
                # Registered projects — so a brainstorm connects to your actual work
                _search_table(conn, "projects", ["title", "description", "next_step"],
                              keywords, "project", sql_hits, max_results)
                # Personal notes
                _search_table(conn, "personal_notes", ["title", "content"],
                              keywords, "note", sql_hits, max_results)
        except Exception:
            pass

    # ── 3. RRF merge ─────────────────────────────────────────────────────────
    RRF_K = 60
    score_map: dict[str, float] = {}
    result_map: dict[str, dict] = {}

    for rank, hit in enumerate(vec_hits, 1):
        k = hit["_key"]
        score_map[k] = score_map.get(k, 0) + 1.0 / (RRF_K + rank)
        result_map[k] = hit

    for rank, hit in enumerate(sql_hits, 1):
        k = f"sql:{hit['source']}:{hit['title'][:40]}"
        score_map[k] = score_map.get(k, 0) + 1.0 / (RRF_K + rank)
        result_map[k] = {**hit, "_key": k}

    ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)

    # ── 4. Title-dedup for diversity ──────────────────────────────────────────
    seen: set[str] = set()
    unique: list[dict] = []
    for key, _ in ranked:
        r = result_map[key]
        title_key = r.get("title", "")[:40].lower()
        if title_key not in seen:
            seen.add(title_key)
            unique.append(r)
        if len(unique) >= max_results:
            break

    return unique


@app.tool()
async def capture_idea(
    content: str,
    source: str = "manual",
    image_path: str = "",
    auto_cross_pollinate: bool = True,
) -> list[TextContent]:
    """Store an idea in the SQLite ideas table.

    Auto-extracts tags from content. Links to domains/projects if keywords match.
    Unless `auto_cross_pollinate=False`, automatically surfaces up to 5 cross-
    pollination matches from library / meetings / news / older ideas in the same
    response — so the user sees connections without a second tool call.

    Args:
        content: The idea text.
        source: Where the idea came from (default "manual").
        image_path: Optional path to an associated image.
        auto_cross_pollinate: When True (default), include connection matches in the response.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    tags = _extract_tags(content)
    week = _iso_week(now)

    try:
        with connect(paths.db) as conn:
            conn.execute(_IDEAS_DDL)
            # Detect which text column the table actually uses (content vs text)
            existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(ideas)")}
            text_col = "content" if "content" in existing_cols else "text"
            conn.execute(
                f"INSERT INTO ideas ({text_col}, tags, created_at) VALUES (?, ?, ?)",
                (content, tags, now.isoformat()),
            )
            conn.commit()

        # Also embed into episodic memory so vector cross-pollination can find it
        try:
            import struct as _struct
            import sqlite_vec as _svec
            from metis_mcp.embeddings import embed_document
            from metis_mcp.tools.vector_memory import _setup_tables, _encode_vec

            _vec = embed_document(content)
            _now2 = now.isoformat()
            with connect(paths.db) as _conn:
                _conn.enable_load_extension(True)
                _svec.load(_conn)
                _conn.enable_load_extension(False)
                _setup_tables(_conn)
                _cur2 = _conn.execute(
                    "INSERT INTO episodic_memory (session_id, event_type, content, metadata, created_at)"
                    " VALUES ('', 'idea', ?, '{}', ?)",
                    (content, _now2),
                )
                _conn.execute(
                    "INSERT INTO vec_episodic (rowid, embedding) VALUES (?, ?)",
                    (_cur2.lastrowid, _encode_vec(_vec)),
                )
                _conn.commit()
        except Exception:
            pass  # non-fatal: idea already saved to SQL above

        lines = [
            f"Idea captured (week {week}).",
            f"- Tags: {tags}",
            f"- Source: {source}",
        ]

        if auto_cross_pollinate:
            matches = _cross_pollinate_core(content, max_results=5)
            if matches:
                lines.append(f"\n**{len(matches)} connection{'s' if len(matches) != 1 else ''} surfaced:**")
                for m in matches:
                    lines.append(f"- [{m['source']}] {m['title']}")
                    if m.get("snippet"):
                        lines.append(f"  _{m['snippet']}_")
            else:
                lines.append("\n_No cross-pollination matches yet — connections build up as your library and history grow._")

        return [TextContent(type="text", text="\n".join(lines))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error capturing idea: {e}")]


@app.tool()
async def get_ideas(
    scope: str = "week",
    limit: int = 20,
) -> list[TextContent]:
    """List captured ideas from your knowledge base, newest first.

    Use this to review what you've been thinking about over a chosen time
    window — the ideas you logged with capture_idea — so you can revisit,
    connect, or act on them. Pairs with capture_idea (to add) and
    cross_pollinate (to surface related work).

    Args:
        scope: Time window to retrieve. One of "today", "week" (last 7 days),
            "month" (last 30 days), or "all". Defaults to "week".
        limit: Maximum number of ideas to return, newest first. Defaults to 20.

    Returns:
        A formatted list of matching ideas with their timestamps and tags, or a
        friendly note if none were found in that window.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    scope_map = {
        "today": now.strftime("%Y-%m-%d"),
        "week": (now - datetime.timedelta(days=7)).isoformat(),
        "month": (now - datetime.timedelta(days=30)).isoformat(),
    }

    try:
        with connect(paths.db) as conn:
            conn.execute(_IDEAS_DDL)

            if scope == "all":
                cur = conn.execute(
                    "SELECT * FROM ideas ORDER BY created_at DESC LIMIT ?", (limit,)
                )
            elif scope == "today":
                cur = conn.execute(
                    "SELECT * FROM ideas WHERE created_at LIKE ? ORDER BY created_at DESC LIMIT ?",
                    (scope_map["today"] + "%", limit),
                )
            elif scope in scope_map:
                cur = conn.execute(
                    "SELECT * FROM ideas WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                    (scope_map[scope], limit),
                )
            else:
                return [TextContent(type="text", text=f"Invalid scope '{scope}'. Use: today, week, month, all")]

            rows = cur.fetchall()
            if not rows:
                return [TextContent(type="text", text=f"No ideas found (scope: {scope}).")]

            lines = [f"**{len(rows)} ideas ({scope}):**\n"]
            cols = {d[0] for d in cur.description} if cur.description else set()
            for row in rows:
                ts = (row["created_at"] or "")[:16]
                tags = (row["tags"] or "none") if "tags" in cols else "none"
                text = (row["content"] if "content" in cols else row["text"] if "text" in cols else "") or ""
                lines.append(f"- [{ts}] {text[:200]}\n  Tags: {tags}")

            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving ideas: {e}")]


@app.tool()
async def add_journal_entry(
    content: str,
    image_path: str = "",
) -> list[TextContent]:
    """Store a journal entry with auto-extracted mood and energy.

    Args:
        content: The journal entry text.
        image_path: Optional path to an associated image.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    mood = _extract_mood(content)
    energy = _extract_energy(content)

    try:
        with connect(paths.db) as conn:
            conn.execute(_JOURNAL_DDL)
            conn.execute(
                """INSERT INTO journal_entries
                   (content, mood, energy_score, image_path, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (content, mood, energy, image_path, now.isoformat()),
            )
            conn.commit()

        parts = [f"Journal entry saved ({now.strftime('%Y-%m-%d %H:%M')})."]
        if mood:
            parts.append(f"Mood: {mood}")
        if energy:
            parts.append(f"Energy: {energy}/5")
        return [TextContent(type="text", text="\n".join(parts))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error saving journal entry: {e}")]


@app.tool()
async def daily_note(text: str = "") -> list[TextContent]:
    """Append to (or read) today's daily note — one rolling note per day.

    Unlike add_journal_entry (which creates a new row each time), daily_note
    keeps a single entry per calendar day and appends timestamped lines to it —
    the Reflect/Tana "daily note" pattern for fast, low-friction capture.

    Args:
        text: Line to append. Leave empty to just read today's note so far.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%H:%M")
    try:
        with connect(paths.db) as conn:
            conn.execute(_JOURNAL_DDL)
            # entry_id is a TEXT PRIMARY KEY that the insert path leaves NULL, so
            # use rowid as the stable row identifier for the append UPDATE.
            row = conn.execute(
                "SELECT rowid, content FROM journal_entries "
                "WHERE date(created_at) = ? AND tags LIKE '%daily-note%' "
                "ORDER BY rowid DESC LIMIT 1",
                (today,),
            ).fetchone()

            if not text:
                if row:
                    return [TextContent(type="text", text=row[1])]
                return [TextContent(type="text", text=f"No daily note yet for {today}. Add a line with daily_note(text=...).")]

            line = f"- {stamp} · {text.strip()}"
            if row:
                new_content = f"{row[1]}\n{line}"
                conn.execute(
                    "UPDATE journal_entries SET content = ? WHERE rowid = ?",
                    (new_content, row[0]),
                )
            else:
                new_content = f"# Daily note — {today}\n{line}"
                conn.execute(
                    "INSERT INTO journal_entries (content, mood, energy_score, image_path, tags, created_at) "
                    "VALUES (?, '', 0, '', 'daily-note', ?)",
                    (new_content, now.isoformat()),
                )
            conn.commit()
        return [TextContent(type="text", text=f"Added to today's note ({stamp}):\n{line}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error updating daily note: {e}")]


@app.tool()
async def get_journal(
    date_from: str = "",
    limit: int = 10,
) -> list[TextContent]:
    """List journal entries from your knowledge base, newest first.

    Use this to look back over your dated journal/log entries — reflections,
    progress notes, and session handoffs — optionally from a given start date.
    Helpful for "what was I working on lately?" and for rebuilding context at
    the start of a session.

    Args:
        date_from: Earliest entry date to include, as "YYYY-MM-DD". Empty
            string (the default) applies no date filter and returns the most
            recent entries.
        limit: Maximum number of entries to return, newest first. Defaults to 10.

    Returns:
        A formatted list of journal entries with their dates, or a note if none
        match.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_JOURNAL_DDL)

            if date_from:
                cur = conn.execute(
                    "SELECT * FROM journal_entries WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                    (date_from, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM journal_entries ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )

            rows = cur.fetchall()
            if not rows:
                return [TextContent(type="text", text="No journal entries found.")]

            lines = [f"**{len(rows)} journal entries:**\n"]
            for row in rows:
                ts = (row["created_at"] or "")[:16]
                mood = row["mood"] or "-"
                energy = row["energy_score"] or "-"
                content = row["content"][:300]
                lines.append(f"### {ts}\n- Mood: {mood} | Energy: {energy}\n\n{content}\n")

            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving journal: {e}")]


@app.tool()
async def get_contacts() -> list[TextContent]:
    """Retrieve all contacts from the contacts table."""
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_CONTACTS_DDL)
            cur = conn.execute("SELECT * FROM contacts ORDER BY name")
            rows = cur.fetchall()

            if not rows:
                return [TextContent(type="text", text="No contacts found.")]

            cols = ["name", "role", "birthday", "notes"]
            lines = ["| " + " | ".join(cols) + " |"]
            lines.append("| " + " | ".join("---" for _ in cols) + " |")
            for row in rows:
                vals = [str(row[c] or "")[:80] for c in cols]
                lines.append("| " + " | ".join(vals) + " |")

            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving contacts: {e}")]


@app.tool()
async def update_contact(
    name: str,
    notes: str,
    role: str = "",
    birthday: str = "",
) -> list[TextContent]:
    """Add or update a contact record.

    Args:
        name: Contact's full name (used as unique key).
        notes: Notes about this contact.
        role: Contact's role or affiliation.
        birthday: Birthday in YYYY-MM-DD format.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        with connect(paths.db) as conn:
            conn.execute(_CONTACTS_DDL)
            conn.execute(
                """INSERT INTO contacts (name, role, birthday, notes, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       role = CASE WHEN excluded.role != '' THEN excluded.role ELSE contacts.role END,
                       birthday = CASE WHEN excluded.birthday != '' THEN excluded.birthday ELSE contacts.birthday END,
                       notes = excluded.notes,
                       updated_at = excluded.updated_at""",
                (name, role, birthday, notes, now),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Contact updated: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error updating contact: {e}")]


@app.tool()
async def get_glossary() -> list[TextContent]:
    """Retrieve all glossary terms."""
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_GLOSSARY_DDL)
            cur = conn.execute("SELECT * FROM glossary ORDER BY term")
            rows = cur.fetchall()

            if not rows:
                return [TextContent(type="text", text="No glossary terms found.")]

            lines = [f"**{len(rows)} glossary terms:**\n"]
            for row in rows:
                lines.append(f"- **{row['term']}**: {row['definition']}")

            return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error retrieving glossary: {e}")]


@app.tool()
async def add_glossary_term(
    term: str,
    definition: str,
) -> list[TextContent]:
    """Add or update a glossary term.

    Args:
        term: The term to define.
        definition: The definition text.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        with connect(paths.db) as conn:
            conn.execute(_GLOSSARY_DDL)
            conn.execute(
                """INSERT INTO glossary (term, definition, created_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(term) DO UPDATE SET definition = excluded.definition""",
                (term, definition, now),
            )
            conn.commit()

        return [TextContent(type="text", text=f"Glossary term added: **{term}**")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error adding glossary term: {e}")]


@app.tool()
async def find_connections(
    content: str,
    limit: int = 5,
) -> list[TextContent]:
    """Search library, meetings, and news for items related to given text.

    Searches library_seeded, meetings, and news_briefs tables for related
    content using keyword matching.

    Args:
        content: Text snippet to find connections for.
        limit: Maximum results per source (default 5).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    # Extract keywords for search
    words = re.findall(r"\b[a-zA-Z]{4,}\b", content.lower())
    stopwords = {"about", "after", "before", "between", "could", "should",
                 "would", "their", "there", "which", "where", "these", "those",
                 "with", "from", "have", "been", "this", "that", "into", "also"}
    keywords = [w for w in words if w not in stopwords][:8]

    if not keywords:
        return [TextContent(type="text", text="No meaningful keywords extracted from content.")]

    results = []

    try:
        with connect(paths.db) as conn:
            # Search library_seeded
            _search_table(conn, "library_seeded", ["title", "relevance_note"],
                          keywords, "library", results, limit)
            # Search meetings
            _search_table(conn, "meetings", ["title"],
                          keywords, "meeting", results, limit)
            # Search news_briefs
            _search_table(conn, "news_briefs", ["title", "summary"],
                          keywords, "news", results, limit)

        if not results:
            return [TextContent(type="text", text="No connections found.")]

        lines = [f"**{len(results)} connections found:**\n"]
        for r in results:
            lines.append(f"- [{r['source']}] {r['title']}\n  {r['snippet']}")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error finding connections: {e}")]


def _search_table(conn, table: str, columns: list, keywords: list,
                  source_label: str, results: list, limit: int):
    """Search a table for keyword matches across specified columns."""
    cur = conn.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
    )
    if not cur.fetchone():
        return

    # Check which columns actually exist
    cur = conn.execute(f"PRAGMA table_info({table})")
    existing_cols = {row["name"] for row in cur.fetchall()}
    valid_cols = [c for c in columns if c in existing_cols]
    if not valid_cols:
        return

    # Build OR clauses for each keyword across valid columns
    clauses = []
    params = []
    for kw in keywords:
        for col in valid_cols:
            clauses.append(f"[{col}] LIKE ?")
            params.append(f"%{kw}%")

    if not clauses:
        return

    # Always fetch title separately when available
    title_col = "title" if "title" in existing_cols else valid_cols[0]
    sql = f"SELECT * FROM {table} WHERE {' OR '.join(clauses)} LIMIT ?"
    params.append(limit)

    try:
        cur = conn.execute(sql, params)
        cur.row_factory = None
        cols = [d[0] for d in cur.description] if cur.description else []
        for row in cur.fetchall():
            row_dict = dict(zip(cols, row)) if cols else {}
            title = row_dict.get(title_col) or (row_dict.get(valid_cols[0]) if row_dict else "")
            # Use abstract > summary > relevance_note > second column as snippet
            snippet = (
                row_dict.get("abstract")
                or row_dict.get("summary")
                or row_dict.get("relevance_note")
                or (str(row_dict.get(valid_cols[1], "") or "") if len(valid_cols) > 1 else "")
            )
            results.append({
                "source": source_label,
                "title": str(title or "")[:200],
                "snippet": str(snippet or "")[:150],
            })
    except Exception:
        pass


@app.tool()
async def cross_pollinate(content: str) -> list[TextContent]:
    """Find cross-domain connections for given text.

    Searches library_seeded, meetings, news_briefs, and ideas tables
    for related items. Returns top 5 with source type, title, and snippet.

    Args:
        content: Text to find cross-domain connections for.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    matches = _cross_pollinate_core(content, max_results=5)
    if not matches:
        return [TextContent(type="text", text="No cross-pollination matches found.")]

    lines = [f"**{len(matches)} cross-pollination matches:**\n"]
    for r in matches:
        lines.append(f"- **[{r['source']}]** {r['title']}")
        if r.get("snippet"):
            lines.append(f"  _{r['snippet']}_")
    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def assemble_brainstorm_context(
    sources: list[str],
    date_filters: dict | None = None,
) -> list[TextContent]:
    """Assemble context from multiple sources for brainstorming.

    Gathers recent content from selected sources, respecting an 8000 char
    limit per source. Returns assembled context string with source labels.

    Args:
        sources: List of sources to include: "library", "meetings", "news", "ideas", "journal".
        date_filters: Optional dict with source-specific date filters, e.g. {"ideas": "2026-03-01"}.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    if date_filters is None:
        date_filters = {}

    MAX_CHARS = 8000
    sections = []

    source_queries = {
        "library": ("library_seeded", "SELECT title, relevance_note FROM library_seeded ORDER BY rowid DESC LIMIT 30", ["title", "relevance_note"]),
        "meetings": ("meetings", "SELECT title, date FROM meetings ORDER BY date DESC LIMIT 20", ["title", "date"]),
        "news": ("news_briefs", "SELECT title, summary FROM news_briefs ORDER BY rowid DESC LIMIT 20", ["title", "summary"]),
        "ideas": ("ideas", "SELECT content, tags, created_at FROM ideas ORDER BY created_at DESC LIMIT 30", ["content", "tags", "created_at"]),
        "journal": ("journal_entries", "SELECT content, mood, created_at FROM journal_entries ORDER BY created_at DESC LIMIT 15", ["content", "mood", "created_at"]),
        # Registered projects + personal notes — so a brainstorm cross-pollinates
        # against your actual work, not just library/news.
        "projects": ("projects", "SELECT title, next_step, description FROM projects WHERE COALESCE(status,'') != 'archived' ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, title", ["title", "next_step", "description"]),
        "notes": ("personal_notes", "SELECT title, content, created_at FROM personal_notes ORDER BY created_at DESC LIMIT 20", ["title", "content", "created_at"]),
    }

    try:
        with connect(paths.db) as conn:
            conn.execute(_IDEAS_DDL)
            conn.execute(_JOURNAL_DDL)

            for src in sources:
                if src not in source_queries:
                    sections.append(f"## {src}\n_Unknown source._\n")
                    continue

                table, sql, cols = source_queries[src]

                # Check table exists
                cur = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                if not cur.fetchone():
                    sections.append(f"## {src}\n_Table not found._\n")
                    continue

                cur = conn.execute(sql)
                rows = cur.fetchall()

                if not rows:
                    sections.append(f"## {src}\n_No data._\n")
                    continue

                text = f"## {src.upper()}\n\n"
                for row in rows:
                    entry = " | ".join(str(row[c] or "")[:200] for c in cols if c in row.keys())
                    text += f"- {entry}\n"
                    if len(text) >= MAX_CHARS:
                        text = text[:MAX_CHARS] + "\n...(truncated)"
                        break

                sections.append(text)

        assembled = "\n\n".join(sections)
        return [TextContent(type="text", text=assembled)]

    except Exception as e:
        return [TextContent(type="text", text=f"Error assembling brainstorm context: {e}")]
