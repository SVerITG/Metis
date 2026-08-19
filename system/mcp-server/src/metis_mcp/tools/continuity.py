"""
continuity.py — the "you have been here before" layer.

WHY THIS EXISTS
---------------
Metis stores a great deal: 835 session summaries, 2,217 episodic memories, 22
procedures, a library, a news archive. None of it was reachable cheaply *while
answering a question*, so answers came out as though the conversation had started
five minutes ago. The owner's words: "I do not feel Metis' presence in its
answers… mentioning how long and how many sessions I have worked on the Metis
dashboard would make me feel like I am actually talking to a second brain."

That feeling is not a tone problem, it is a retrieval problem. You cannot say
"this is your fifth session on the dashboard since May" unless something counts.
This module counts, in one call, so referencing the past is accurate rather than
flattering guesswork — the failure mode to avoid is inventing continuity.

Everything returned here is derived from stored rows. If a field is empty, the
honest move is to say nothing rather than to fill it in.

No LLM calls. Pure SQL, cheap enough to call before composing a reply.
"""
from __future__ import annotations

import datetime
import json
import re
import sqlite3

try:
    from mcp.types import TextContent
except ImportError:                                     # pragma: no cover
    TextContent = None                                  # type: ignore[assignment,misc]

from metis_mcp.config import paths

try:
    from metis_mcp.app_instance import app
except ImportError:                                     # pragma: no cover
    class _NoopApp:                                     # type: ignore[no-redef]
        def tool(self, *a, **kw):
            def _dec(fn): return fn
            return _dec
    app = _NoopApp()                                    # type: ignore[assignment]


_STOP = {
    "the", "and", "for", "with", "from", "that", "this", "have", "has", "was",
    "are", "its", "into", "over", "what", "when", "where", "which", "how", "why",
    "you", "your", "can", "should", "would", "could", "about", "there", "their",
    "make", "made", "does", "did", "not", "but", "all", "any", "get", "got",
    "metis", "please", "want", "need", "like", "just", "now", "also", "some",
    # Generic verbs and fillers matched almost every session summary, so an
    # unrelated question still "found" prior work. "something nobody has ever
    # worked on" matched on 'worked'. Continuity has to come from a distinctive
    # term or it is not continuity.
    "something", "nobody", "anyone", "everyone", "ever", "never", "worked",
    "work", "working", "done", "doing", "make", "making", "look", "looking",
    "think", "thinking", "know", "knowing", "help", "using", "used", "based",
    "thing", "things", "stuff", "really", "maybe", "sure", "still", "again",
    "better", "best", "more", "most", "less", "very", "much", "many", "other",
    "with", "without", "into", "onto", "from", "then", "than", "these", "those",
}


def _terms(text: str, limit: int = 8) -> list[str]:
    """Salient search terms from a free-text topic or question."""
    words = re.findall(r"[a-z0-9][a-z0-9\-]{2,}", (text or "").lower())
    out: list[str] = []
    for w in words:
        if w in _STOP or len(w) < 4:
            continue
        if w not in out:
            out.append(w)
        if len(out) >= limit:
            break
    return out


def _days_since(iso: str) -> int | None:
    if not iso:
        return None
    for cut in (19, 10):
        try:
            d = datetime.datetime.fromisoformat(str(iso)[:cut])
            return (datetime.datetime.now() - d).days
        except ValueError:
            continue
    return None


def _human_span(days: int | None) -> str:
    """'3 months', '6 weeks', 'today' — for prose, not for precision.

    Rounds rather than truncating: 89 days is colloquially three months, and
    `//30` reporting it as two made the span read as an undercount.
    """
    if days is None:
        return ""
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days"
    if days < 60:
        return f"{max(1, round(days / 7))} weeks"
    if days < 730:
        return f"{max(1, round(days / 30.4))} months"
    return f"{max(1, round(days / 365))} years"


def _ago(days: int | None) -> str:
    """A phrase that reads correctly on its own — 'today', '3 weeks ago'.

    `_human_span` returns bare durations, so appending ' ago' produced
    'today ago'. Anything that already reads as a point in time is returned
    unchanged.
    """
    span = _human_span(days)
    if not span:
        return ""
    return span if span in ("today", "yesterday") else f"{span} ago"


def _q(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.Error:
        return []


def gather(topic: str = "", project_id: str = "", limit: int = 4) -> dict:
    """Assemble continuity facts. Pure function — no MCP, callable anywhere."""
    out: dict = {
        "overall": {}, "project": {}, "sessions": [], "decisions": [],
        "procedures": [], "library": [], "news": [], "briefing": {}, "terms": [],
    }
    if not paths.db.exists():
        return out

    terms = _terms(f"{topic} {project_id}")
    out["terms"] = terms

    conn = sqlite3.connect(str(paths.db))
    conn.row_factory = sqlite3.Row
    try:
        # ── Overall span: how long has this second brain been running ─────────
        r = _q(conn, "SELECT COUNT(*) n, MIN(created_at) first, MAX(created_at) last "
                     "FROM session_summaries WHERE COALESCE(archived,0)=0")
        if r and r[0]["n"]:
            first_days = _days_since(r[0]["first"])
            out["overall"] = {
                "sessions": r[0]["n"],
                "first": (r[0]["first"] or "")[:10],
                "last": (r[0]["last"] or "")[:10],
                "span_days": first_days,
                "span": _human_span(first_days),
            }
        for label, table in (("memories", "episodic_memory"),
                             ("concepts", "semantic_memory"),
                             ("procedures", "procedural_memory"),
                             ("papers", "literature_metadata")):
            rr = _q(conn, f"SELECT COUNT(*) n FROM {table}")
            if rr:
                out["overall"][label] = rr[0]["n"]

        # ── This project ─────────────────────────────────────────────────────
        if project_id:
            pr = _q(conn, "SELECT project_id, title, status, next_step, created_at, "
                          "started_at, last_session_at, history_log "
                          "FROM projects WHERE project_id=?",
                    (project_id,))
            if pr:
                p = pr[0]
                started = p["started_at"] or p["created_at"] or ""
                age = _days_since(started)
                # Sessions on this project come from projects.history_log — the
                # record update_project_memory() deliberately appends to.
                #
                # Two wrong answers were tried first. Matching session summaries on
                # the project TITLE gave 737 of 835, because "Metis Dashboard"
                # appears as ordinary prose in almost every summary: a large number
                # made of noise, which is the flattering-but-false figure this
                # module exists to avoid. Matching the SLUG instead gave 0, because
                # the slug never appears in summaries at all. history_log is the
                # only place a session is recorded *as being about this project*,
                # so it is the only honest count — even though it is small. A true
                # "4 recorded sessions" is worth more than a false "737".
                title = (p["title"] or "")
                entries: list = []
                raw_hist = p["history_log"] if "history_log" in p.keys() else None
                if raw_hist:
                    try:
                        parsed = json.loads(raw_hist)
                        if isinstance(parsed, list):
                            entries = parsed
                    except (ValueError, TypeError):
                        entries = []
                first_entry = ""
                if entries:
                    dates = sorted(
                        str(e.get("date") or e.get("ts") or "")[:10]
                        for e in entries if isinstance(e, dict))
                    dates = [d for d in dates if d]
                    first_entry = dates[0] if dates else ""
                last_at = (p["last_session_at"] or "")[:10]

                out["project"] = {
                    "id": p["project_id"],
                    "title": title,
                    "status": p["status"],
                    "next_step": p["next_step"] or "",
                    "started": started[:10],
                    "age_days": age,
                    "age": _human_span(age),
                    "sessions": len(entries),
                    "first_session": first_entry,
                    "last_session": last_at,
                    "last_session_ago": _ago(_days_since(p["last_session_at"] or "")),
                    # How long the RECORD spans, which is not the same as how long
                    # the project has existed — worth distinguishing so a project
                    # created in March with notes only since August reads honestly.
                    "recorded_span": _human_span(_days_since(first_entry)) if first_entry else "",
                }

        # ── Past sessions on this topic ───────────────────────────────────────
        if terms:
            where = " OR ".join(["summary LIKE ? OR key_topics LIKE ?"] * len(terms))
            params: list = []
            for t in terms:
                params += [f"%{t}%", f"%{t}%"]
            rows = _q(conn,
                      f"SELECT summary, key_topics, decisions, created_at, client "
                      f"FROM session_summaries WHERE COALESCE(archived,0)=0 AND ({where}) "
                      f"ORDER BY created_at DESC LIMIT ?", tuple(params + [limit]))
            for s in rows:
                out["sessions"].append({
                    "when": (s["created_at"] or "")[:10],
                    "ago": _ago(_days_since(s["created_at"] or "")),
                    "summary": (s["summary"] or "")[:260],
                    "topics": (s["key_topics"] or "")[:120],
                    "client": s["client"] or "",
                })
                # Decisions ride along inside session_summaries.decisions (JSON
                # or plain text depending on when it was written).
                raw = s["decisions"]
                if raw:
                    try:
                        items = json.loads(raw) if isinstance(raw, str) and raw.strip().startswith("[") else [raw]
                    except (ValueError, TypeError):
                        items = [raw]
                    for d in items:
                        d = str(d).strip()
                        if d and len(d) > 12:
                            out["decisions"].append({
                                "when": (s["created_at"] or "")[:10],
                                "decision": d[:240],
                            })

            # ── Procedures whose trigger matches ─────────────────────────────
            pwhere = " OR ".join(["procedure_name LIKE ? OR trigger_context LIKE ?"] * len(terms))
            pparams: list = []
            for t in terms:
                pparams += [f"%{t}%", f"%{t}%"]
            for p in _q(conn,
                        f"SELECT procedure_name, trigger_context, success_count, last_used "
                        f"FROM procedural_memory WHERE {pwhere} "
                        f"ORDER BY COALESCE(success_count,0) DESC LIMIT 3", tuple(pparams)):
                out["procedures"].append({
                    "name": p["procedure_name"],
                    "trigger": (p["trigger_context"] or "")[:120],
                    "used": p["success_count"] or 0,
                    "last_used": (p["last_used"] or "")[:10],
                })

            # ── Library ──────────────────────────────────────────────────────
            lwhere = " OR ".join(["title LIKE ?"] * len(terms))
            for l in _q(conn, f"SELECT title, year FROM literature_metadata "
                              f"WHERE {lwhere} ORDER BY COALESCE(year,0) DESC LIMIT 3",
                        tuple(f"%{t}%" for t in terms)):
                out["library"].append({"title": (l["title"] or "")[:140], "year": l["year"]})

            # ── News threads ─────────────────────────────────────────────────
            nwhere = " OR ".join(["label LIKE ? OR thread_id LIKE ?"] * len(terms))
            nparams: list = []
            for t in terms:
                nparams += [f"%{t}%", f"%{t}%"]
            for n in _q(conn,
                        f"SELECT thread_id, label, item_count, substr(last_seen,1,10) seen "
                        f"FROM news_threads WHERE {nwhere} "
                        f"ORDER BY item_count DESC LIMIT 3", tuple(nparams)):
                out["news"].append({
                    "thread": n["thread_id"], "label": n["label"],
                    "items": n["item_count"], "last_seen": n["seen"],
                })

        # ── Most recent briefing, and whether it was read ────────────────────
        b = _q(conn, "SELECT insight_date, read_at FROM daily_insights "
                     "WHERE content IS NOT NULL ORDER BY insight_date DESC LIMIT 1")
        if b:
            out["briefing"] = {
                "date": (b[0]["insight_date"] or "")[:10],
                "read": bool(b[0]["read_at"]),
                "ago": _ago(_days_since(b[0]["insight_date"] or "")),
            }
    finally:
        conn.close()
    return out


def continuity_line(ctx: dict) -> str:
    """One honest sentence of continuity, or '' if there is nothing true to say.

    Deliberately returns empty rather than something vague. A fabricated or
    padded continuity line is worse than none: it makes the memory layer feel
    decorative, which is the opposite of the point.
    """
    o, p = ctx.get("overall") or {}, ctx.get("project") or {}
    prior = ctx.get("sessions") or []

    # No topical match and no project scope means there is no CONTINUITY, only a
    # total. Reporting "835 recorded sessions" against an unrelated question dresses
    # a database count as relevant history — the padding this module exists to
    # prevent. Return empty and let the caller say nothing.
    if not prior and not p.get("sessions"):
        return ""

    bits: list[str] = []
    if p.get("sessions"):
        n = p["sessions"]
        span = p.get("recorded_span") or ""
        # "over today" is not a span. When the whole record is same-day, the
        # last-worked clause already carries the timing.
        if span in ("today", "yesterday"):
            span = ""
        bits.append(f"{n} recorded session{'s' if n != 1 else ''} on "
                    f"{p.get('title') or p.get('id')}"
                    + (f" over {span}" if span else ""))
    elif o.get("sessions") and o.get("span"):
        bits.append(f"{o['sessions']} recorded sessions across {o['span']}")
    if p.get("last_session_ago"):
        bits.append(f"last worked on it {p['last_session_ago']}")
    elif prior:
        last = (prior[0].get("ago") or "").strip()
        bits.append(f"last touched this {last}" if last else "touched before")
    return " · ".join(bits)


@app.tool()
async def get_continuity_context(
    topic: str = "",
    project_id: str = "",
    limit: int = 4,
) -> list[TextContent]:
    """Find what the researcher has already done that bears on the current question.

    Call this before answering anything substantive, so the reply can be framed in
    their own prior work instead of starting from nothing. This is what makes Metis
    read as a second brain rather than a fresh chat: "this is your fifth session on
    the dashboard since May" is only sayable if something counted.

    Returns, where each exists:
      - overall span — recorded sessions, how long Metis has been running, and how
        much is stored (memories, concepts, procedures, papers)
      - this project — age, session count, current next step
      - prior sessions on the same topic, newest first
      - decisions already taken (so a settled question is not reopened)
      - procedures that already cover this (follow them rather than improvising)
      - library items and news threads on the topic
      - the most recent briefing and whether it was read

    USE IT HONESTLY. Weave one or two genuine references into the answer; do not
    recite the whole payload, and never invent continuity. Empty fields mean there
    is nothing to say — say nothing rather than padding. A fabricated link makes
    the memory layer feel decorative, which defeats the purpose.

    Args:
        topic: The question or subject being worked on. Free text; salient terms
            are extracted for matching.
        project_id: Project slug to scope to (e.g. "metis-dashboard"), if known.
        limit: How many prior sessions to return. Default 4.

    Returns:
        A compact readable digest, plus a ready-made one-line continuity summary.
    """
    ctx = gather(topic=topic, project_id=project_id, limit=limit)
    o, p = ctx["overall"], ctx["project"]

    if not o and not p and not ctx["sessions"]:
        return [TextContent(type="text", text=(
            "No continuity found — nothing stored yet on this, or the memory "
            "tables are empty. Answer without a past reference rather than "
            "inventing one."
        ))]

    lines: list[str] = []
    one = continuity_line(ctx)
    if one:
        lines += [f"**Continuity:** {one}", ""]

    if o:
        span = (f"{o.get('sessions', 0)} sessions since {o.get('first', '?')} "
                f"({o.get('span', '?')})")
        store = ", ".join(
            f"{o[k]:,} {k}" for k in ("memories", "concepts", "procedures", "papers")
            if o.get(k))
        lines.append(f"OVERALL · {span}" + (f" · holding {store}" if store else ""))

    if p:
        lines.append(
            f"PROJECT · {p.get('title')} — {p.get('sessions', 0)} recorded session(s)"
            + (f" spanning {p['recorded_span']}" if p.get("recorded_span") else "")
            + f", project created {p.get('started')} ({p.get('age')} ago)"
            + f", status {p.get('status')}")
        if p.get("last_session_ago"):
            lines.append(f"  last worked on: {p['last_session_ago']}")
        if p.get("next_step"):
            lines.append(f"  next step on record: {p['next_step'][:200]}")

    if ctx["sessions"]:
        lines.append("")
        lines.append(f"PRIOR SESSIONS ON THIS ({len(ctx['sessions'])}):")
        for s in ctx["sessions"]:
            where = f" [{s['client']}]" if s.get("client") else ""
            lines.append(f"  · {s['when']} ({s['ago']}){where} — {s['summary']}")

    if ctx["decisions"]:
        lines.append("")
        lines.append("ALREADY DECIDED — do not reopen these without a reason:")
        for d in ctx["decisions"][:6]:
            lines.append(f"  · [{d['when']}] {d['decision']}")

    if ctx["procedures"]:
        lines.append("")
        lines.append("PROCEDURES THAT COVER THIS — follow them rather than improvising:")
        for pr in ctx["procedures"]:
            lines.append(f"  · {pr['name']} (used {pr['used']}×, last {pr['last_used'] or 'never'})")

    if ctx["library"]:
        lines.append("")
        lines.append("IN YOUR LIBRARY:")
        for l in ctx["library"]:
            yr = f" ({l['year']})" if l.get("year") else ""
            lines.append(f"  · {l['title']}{yr}")

    if ctx["news"]:
        lines.append("")
        lines.append("RUNNING NEWS THREADS:")
        for n in ctx["news"]:
            lines.append(f"  · {n['label']} — {n['items']} items, last {n['last_seen']}")

    if ctx["briefing"]:
        b = ctx["briefing"]
        state = "read" if b.get("read") else "UNREAD"
        lines.append("")
        lines.append(f"LAST BRIEFING · {b.get('date')} ({b.get('ago')}) — {state}")

    return [TextContent(type="text", text="\n".join(lines))]
