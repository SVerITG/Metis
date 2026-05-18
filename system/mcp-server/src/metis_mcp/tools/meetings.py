"""Meeting cross-reference enrichment tool.

After a meeting transcript is saved (via the Meetings tab or transcribe_recording()),
call enrich_meeting_with_crossrefs() to automatically:

  1. Extract key topics and action items from the transcript
  2. Match action items to open tasks in the database
  3. Surface related papers from the library
  4. Save the cross-reference brief alongside the meeting record
"""

import datetime
import re
from typing import Optional

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


def _extract_keywords(text: str, top_n: int = 12) -> list[str]:
    """Extract salient keywords by filtering stopwords and ranking by frequency."""
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "was", "are", "were", "be", "been", "have", "has",
        "had", "do", "does", "did", "will", "would", "could", "should", "may",
        "might", "this", "that", "these", "those", "we", "i", "you", "they",
        "he", "she", "it", "our", "their", "my", "your", "its", "not", "no",
        "also", "so", "then", "than", "from", "by", "as", "up", "about",
        "into", "through", "during", "before", "after", "between", "each",
        "all", "both", "few", "more", "most", "other", "some", "such", "over",
        "what", "which", "who", "when", "where", "how", "if", "can",
    }
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:top_n]]


def _find_open_tasks(conn, keywords: list[str]) -> list[dict]:
    """Find open tasks whose title contains any of the extracted keywords."""
    if not keywords:
        return []
    like_clauses = " OR ".join("LOWER(title) LIKE ?" for _ in keywords)
    params = [f"%{kw}%" for kw in keywords]
    rows = conn.execute(
        f"""
        SELECT task_id as id, title, priority, status, due_date
          FROM tasks
         WHERE status NOT IN ('done', 'cancelled')
           AND ({like_clauses})
         ORDER BY priority DESC, due_date ASC
         LIMIT 8
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def _find_related_papers(conn, keywords: list[str]) -> list[dict]:
    """Find library papers whose title or abstract contains any keyword."""
    if not keywords:
        return []
    like_clauses = " OR ".join(
        "LOWER(title) LIKE ? OR LOWER(abstract) LIKE ?" for _ in keywords
    )
    params = []
    for kw in keywords:
        params += [f"%{kw}%", f"%{kw}%"]
    rows = conn.execute(
        f"""
        SELECT id, title, authors, year, journal, doi
          FROM literature_metadata
         WHERE ({like_clauses})
         ORDER BY year DESC
         LIMIT 6
        """,
        params,
    ).fetchall()
    if rows:
        return [dict(r) for r in rows]

    # Fallback: try library_cards if literature_metadata is empty
    like_clauses2 = " OR ".join("LOWER(title) LIKE ? OR LOWER(notes) LIKE ?" for _ in keywords)
    params2 = []
    for kw in keywords:
        params2 += [f"%{kw}%", f"%{kw}%"]
    rows2 = conn.execute(
        f"""
        SELECT id, title, source, tags
          FROM library_cards
         WHERE ({like_clauses2})
         ORDER BY id DESC
         LIMIT 6
        """,
        params2,
    ).fetchall()
    return [dict(r) for r in rows2]


def _find_related_projects(conn, keywords: list[str]) -> list[dict]:
    """Find active projects whose title or description matches keywords."""
    if not keywords:
        return []
    like_clauses = " OR ".join("LOWER(title) LIKE ? OR LOWER(description) LIKE ?" for _ in keywords)
    params = []
    for kw in keywords:
        params += [f"%{kw}%", f"%{kw}%"]
    rows = conn.execute(
        f"""
        SELECT project_id as id, title, status, next_step
          FROM projects
         WHERE status = 'active'
           AND ({like_clauses})
         ORDER BY title ASC
         LIMIT 5
        """,
        params,
    ).fetchall()
    return [dict(r) for r in rows]


@app.tool()
async def enrich_meeting_with_crossrefs(meeting_id: str) -> list[TextContent]:
    """Find cross-references for a saved meeting: open tasks, related papers, active projects.

    Call this after saving a meeting transcript (via Meetings tab or
    transcribe_recording()). It extracts key topics from the transcript,
    matches them against tasks, library papers, and active projects, and
    returns a structured cross-reference brief.

    The result is also written to the meeting's notes field in the database
    so it appears in the Meetings tab.

    Args:
        meeting_id: The meeting_id from the meetings table.

    Returns:
        Formatted cross-reference brief listing matched tasks, papers, and projects.
    """
    with connect(paths.db) as conn:
        row = conn.execute(
            """
            SELECT meeting_id, title, summary, decisions, transcript_path
              FROM meetings
             WHERE meeting_id = ?
            """,
            (meeting_id,),
        ).fetchone()

    if not row:
        return [TextContent(type="text", text=f"Meeting '{meeting_id}' not found.")]

    row = dict(row)
    title = row.get("title") or meeting_id

    # Build a text corpus from whatever content is available
    corpus_parts = [title]
    if row.get("summary"):
        corpus_parts.append(row["summary"])
    if row.get("decisions"):
        corpus_parts.append(row["decisions"])
    if row.get("transcript_path"):
        try:
            from pathlib import Path
            tp = Path(row["transcript_path"])
            if tp.exists():
                corpus_parts.append(tp.read_text(encoding="utf-8", errors="replace")[:3000])
        except Exception:
            pass
    corpus = " ".join(corpus_parts)

    keywords = _extract_keywords(corpus, top_n=14)

    with connect(paths.db) as conn:
        tasks   = _find_open_tasks(conn, keywords)
        papers  = _find_related_papers(conn, keywords)
        projects = _find_related_projects(conn, keywords)

    # ── Build the cross-reference brief ────────────────────────────────────
    lines = [
        f"## Cross-references for: {title}",
        f"_Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}_ · "
        f"Keywords: {', '.join(keywords[:8])}",
        "",
    ]

    if tasks:
        lines.append("### Open tasks linked to this meeting")
        for t in tasks:
            due = f" · due {t['due_date']}" if t.get("due_date") else ""
            lines.append(f"- **{t['title']}** [{t['status']}{due}]")
        lines.append("")

    if projects:
        lines.append("### Active projects connected")
        for p in projects:
            ns = f" — {p['next_step']}" if p.get("next_step") else ""
            lines.append(f"- **{p['title']}**{ns}")
        lines.append("")

    if papers:
        lines.append("### Related papers in library")
        for p in papers:
            if p.get("authors"):
                auth = p["authors"].split(";")[0].strip() + " et al."
                year = f" ({p['year']})" if p.get("year") else ""
                lines.append(f"- {p['title']} — {auth}{year}")
            else:
                lines.append(f"- {p['title']}")
        lines.append("")

    if not tasks and not papers and not projects:
        lines.append(
            "_No strong matches found. Try running after adding more content "
            "to your tasks, projects, or library._"
        )

    brief = "\n".join(lines)

    # ── Persist the cross-ref brief back to the meeting row ─────────────────
    try:
        with connect(paths.db) as conn:
            existing = conn.execute(
                "SELECT notes FROM meetings WHERE meeting_id = ?", (meeting_id,)
            ).fetchone()
            existing_notes = (existing["notes"] if existing and existing["notes"] else "")
            separator = "\n\n---\n" if existing_notes else ""
            conn.execute(
                "UPDATE meetings SET notes = ? WHERE meeting_id = ?",
                (existing_notes + separator + brief, meeting_id),
            )
            conn.commit()
    except Exception:
        pass

    summary = (
        f"Found {len(tasks)} task(s), {len(projects)} project(s), "
        f"{len(papers)} paper(s) related to **{title}**."
    )
    return [TextContent(type="text", text=f"{summary}\n\n{brief}")]
