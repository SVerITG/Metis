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
    timestamp TEXT NOT NULL,
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
    timestamp TEXT NOT NULL
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


@app.tool()
async def capture_idea(
    content: str,
    source: str = "manual",
    image_path: str = "",
) -> list[TextContent]:
    """Store an idea in the SQLite ideas table.

    Auto-extracts tags from content. Links to domains/projects if keywords match.

    Args:
        content: The idea text.
        source: Where the idea came from (default "manual").
        image_path: Optional path to an associated image.
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    now = datetime.datetime.now(datetime.timezone.utc)
    tags = _extract_tags(content)
    week = _iso_week(now)

    try:
        with connect(paths.db) as conn:
            conn.execute(_IDEAS_DDL)
            conn.execute(
                """INSERT INTO ideas
                   (content, source, tags, image_path, timestamp, week)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (content, source, tags, image_path, now.isoformat(), week),
            )
            conn.commit()

        return [
            TextContent(
                type="text",
                text=f"Idea captured (week {week}).\n- Tags: {tags}\n- Source: {source}",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error capturing idea: {e}")]


@app.tool()
async def get_ideas(
    scope: str = "week",
    limit: int = 20,
) -> list[TextContent]:
    """Retrieve ideas from the database.

    Args:
        scope: Time scope -- "today", "week", "month", "all".
        limit: Maximum results (default 20).
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
                    "SELECT * FROM ideas ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
            elif scope == "today":
                cur = conn.execute(
                    "SELECT * FROM ideas WHERE timestamp LIKE ? ORDER BY timestamp DESC LIMIT ?",
                    (scope_map["today"] + "%", limit),
                )
            elif scope in scope_map:
                cur = conn.execute(
                    "SELECT * FROM ideas WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                    (scope_map[scope], limit),
                )
            else:
                return [TextContent(type="text", text=f"Invalid scope '{scope}'. Use: today, week, month, all")]

            rows = cur.fetchall()
            if not rows:
                return [TextContent(type="text", text=f"No ideas found (scope: {scope}).")]

            lines = [f"**{len(rows)} ideas ({scope}):**\n"]
            for row in rows:
                ts = row["timestamp"][:16]
                tags = row["tags"] or "none"
                content = row["content"][:200]
                lines.append(f"- [{ts}] {content}\n  Tags: {tags}")

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
                   (content, mood, energy_score, image_path, timestamp)
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
async def get_journal(
    date_from: str = "",
    limit: int = 10,
) -> list[TextContent]:
    """Retrieve journal entries.

    Args:
        date_from: Start date (YYYY-MM-DD). Empty = no filter.
        limit: Maximum results (default 10).
    """
    if not paths.db.exists():
        return [TextContent(type="text", text=f"Database not found: {paths.db}")]

    try:
        with connect(paths.db) as conn:
            conn.execute(_JOURNAL_DDL)

            if date_from:
                cur = conn.execute(
                    "SELECT * FROM journal_entries WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                    (date_from, limit),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM journal_entries ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )

            rows = cur.fetchall()
            if not rows:
                return [TextContent(type="text", text="No journal entries found.")]

            lines = [f"**{len(rows)} journal entries:**\n"]
            for row in rows:
                ts = row["timestamp"][:16]
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

    sql = f"SELECT * FROM {table} WHERE {' OR '.join(clauses)} LIMIT ?"
    params.append(limit)

    try:
        cur = conn.execute(sql, params)
        for row in cur.fetchall():
            title = row[valid_cols[0]] or ""
            snippet = ""
            if len(valid_cols) > 1:
                snippet = str(row[valid_cols[1]] or "")[:150]
            results.append({
                "source": source_label,
                "title": str(title)[:200],
                "snippet": snippet,
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

    words = re.findall(r"\b[a-zA-Z]{4,}\b", content.lower())
    stopwords = {"about", "after", "before", "between", "could", "should",
                 "would", "their", "there", "which", "where", "these", "those",
                 "with", "from", "have", "been", "this", "that", "into", "also"}
    keywords = [w for w in words if w not in stopwords][:8]

    if not keywords:
        return [TextContent(type="text", text="No meaningful keywords extracted.")]

    results = []

    try:
        with connect(paths.db) as conn:
            conn.execute(_IDEAS_DDL)
            _search_table(conn, "library_seeded", ["title", "relevance_note"],
                          keywords, "library", results, 5)
            _search_table(conn, "meetings", ["title"],
                          keywords, "meeting", results, 5)
            _search_table(conn, "news_briefs", ["title", "summary"],
                          keywords, "news", results, 5)
            _search_table(conn, "ideas", ["content"],
                          keywords, "idea", results, 5)

        if not results:
            return [TextContent(type="text", text="No cross-pollination matches found.")]

        # Deduplicate and limit to top 5
        seen = set()
        unique = []
        for r in results:
            key = (r["source"], r["title"][:50])
            if key not in seen:
                seen.add(key)
                unique.append(r)
            if len(unique) >= 5:
                break

        lines = [f"**{len(unique)} cross-pollination matches:**\n"]
        for r in unique:
            lines.append(f"- **[{r['source']}]** {r['title']}")
            if r["snippet"]:
                lines.append(f"  _{r['snippet']}_")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error in cross-pollination: {e}")]


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
        "ideas": ("ideas", "SELECT content, tags, timestamp FROM ideas ORDER BY timestamp DESC LIMIT 30", ["content", "tags", "timestamp"]),
        "journal": ("journal_entries", "SELECT content, mood, timestamp FROM journal_entries ORDER BY timestamp DESC LIMIT 15", ["content", "mood", "timestamp"]),
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
