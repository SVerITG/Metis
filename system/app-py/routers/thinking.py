"""
routers/thinking.py — Thinking tab routes.
"""

import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/thinking", response_class=HTMLResponse)
async def thinking_tab(request: Request):
    return templates.TemplateResponse(
     request, "thinking.html", {"active_tab": "thinking"}
 )


@router.get("/api/tab/thinking", response_class=HTMLResponse)
async def thinking_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "thinking.html", {"active_tab": "thinking"}
 )


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/meta", response_class=HTMLResponse)
async def thinking_meta(request: Request):
    open_count = db_scalar("SELECT COUNT(*) FROM ideas WHERE tags NOT LIKE '%archived%'", default=0) or 0
    last_row = db_query("SELECT created_at FROM ideas ORDER BY created_at DESC LIMIT 1") or []
    last = last_row[0]["created_at"][:10] if last_row else "—"
    return HTMLResponse(f"{open_count} OPEN · LAST TOUCHED {last}")


@router.get("/api/partial/thinking/threads", response_class=HTMLResponse)
async def thinking_threads(request: Request):
    threads = db_query(
        "SELECT id, content, tags, created_at FROM ideas WHERE tags NOT LIKE '%archived%' ORDER BY created_at DESC LIMIT 12"
    ) or []
    today = datetime.date.today()
    items = ""
    for t in threads:
        title = (t.get("content") or "")[:45]
        date_str = (t.get("created_at") or "")[:10]
        # compute age in days
        age_label = ""
        age_color = "var(--m-muted)"
        try:
            d = datetime.date.fromisoformat(date_str)
            age = (today - d).days
            if age >= 30:
                age_label = f"{age}d"
                age_color = "var(--m-alert)"
            elif age >= 14:
                age_label = f"{age}d"
                age_color = "var(--m-warn,#b45309)"
            elif age >= 7:
                age_label = f"{age}d"
        except Exception:
            pass
        staleness = (
            f'<span style="font-family:var(--m-mono);font-size:9px;color:{age_color};'
            f'margin-left:6px;letter-spacing:0.08em;">{age_label}</span>'
            if age_label else ""
        )
        items += (
            f'<div style="padding:12px 16px;border-bottom:1px solid var(--m-rule-soft);'
            f'cursor:pointer;font-family:var(--m-display);font-size:13px;color:var(--m-ink);line-height:1.3;">'
            f'{title}<br>'
            f'<span style="font-family:var(--m-mono);font-size:10px;color:var(--m-muted);">{date_str}</span>'
            f'{staleness}</div>'
        )
    if not items:
        items = '<div style="padding:24px 16px;font-family:var(--m-display);font-style:italic;font-size:14px;color:var(--m-muted);">No open threads.</div>'
    return HTMLResponse(items)


@router.get("/api/partial/thinking/dialogue", response_class=HTMLResponse)
async def thinking_dialogue(request: Request):
    ideas = db_query(
        "SELECT content, created_at FROM ideas ORDER BY created_at DESC LIMIT 5"
    ) or []
    if not ideas:
        return HTMLResponse(
            '<div style="padding:24px 0;font-family:var(--m-display);font-style:italic;font-size:15px;color:var(--m-muted);text-align:center;">'
            'No ideas yet. Capture one with ⌘K.</div>'
        )
    items = ""
    for idea in ideas:
        content = (idea.get("content") or "")[:300]
        date = (idea.get("created_at") or "")[:10]
        items += (
            f'<div style="padding:18px 0;border-bottom:1px solid var(--m-rule-soft);">'
            f'<div style="font-family:var(--m-display);font-size:15px;color:var(--m-text);line-height:1.6;">{content}</div>'
            f'<div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.14em;color:var(--m-muted);margin-top:8px;">{date}</div>'
            f'</div>'
        )
    return HTMLResponse(f'<div>{items}</div>')


@router.get("/api/partial/thinking/marginalia", response_class=HTMLResponse)
async def thinking_marginalia(request: Request):
    notes = db_query(
        "SELECT content, created_at FROM personal_notes ORDER BY created_at DESC LIMIT 4"
    ) or []
    items = ""
    for note in notes:
        content = (note.get("content") or "")[:120]
        date = (note.get("created_at") or "")[:10]
        items += (
            f'<div class="panel panel-pad" style="padding:18px 20px;margin-bottom:12px;">'
            f'<div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.14em;color:var(--m-muted);margin-bottom:6px;">{date} · NOTE</div>'
            f'<div style="font-family:var(--m-display);font-size:13px;color:var(--m-text);line-height:1.5;">{content}</div>'
            f'</div>'
        )
    if not items:
        items = '<div class="panel panel-pad" style="padding:18px 20px;"><div class="ed" style="font-size:13px;color:var(--m-muted);"><em>No notes yet.</em></div></div>'
    return HTMLResponse(items)


# ---------------------------------------------------------------------------
# Ideas
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/ideas", response_class=HTMLResponse)
async def thinking_ideas(request: Request):
    ideas = db_query(
        "SELECT id, content, tags, created_at "
        "FROM ideas ORDER BY created_at DESC LIMIT 30"
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_ideas.html",
        {
            "ideas": ideas
        },
    )


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/notes", response_class=HTMLResponse)
async def thinking_notes(request: Request):
    notes = db_query(
        "SELECT id, content, tags, created_at "
        "FROM personal_notes ORDER BY created_at DESC LIMIT 20"
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_notes.html",
        {
            "notes": notes
        },
    )


# ---------------------------------------------------------------------------
# Open questions
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/questions", response_class=HTMLResponse)
async def thinking_questions(request: Request):
    questions = db_query(
        "SELECT id, content, created_at "
        "FROM ideas WHERE tags LIKE '%question%' "
        "ORDER BY created_at DESC LIMIT 15"
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_questions.html",
        {
            "questions": questions
        },
    )


# ---------------------------------------------------------------------------
# Brainstorm sessions (Phase 8)
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/brainstorm", response_class=HTMLResponse)
async def thinking_brainstorm(request: Request):
    """Brainstorm launcher — recent sessions plus invitation to start a new one."""
    sessions: list[dict] = []
    has_table = db_scalar(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='brainstorm_sessions'",
        default=None,
    )
    if has_table:
        # Pull the 3 most recent. Use sources_used as a proxy for "messages
        # exchanged" — older schemas don't have message_count.
        rows = db_query(
            "SELECT session_id, session_uuid, topic, summary, sources_used, "
            "created_at FROM brainstorm_sessions ORDER BY created_at DESC LIMIT 3",
            default=[],
        ) or []
        for r in rows:
            # Try a few possible companion tables for an accurate count
            sid = r.get("session_uuid") or r.get("session_id")
            msg_count = 0
            for tbl, col in (("brainstorm_turns", "session_uuid"),
                             ("brainstorm_turns", "session_id")):
                try:
                    n = db_scalar(
                        f"SELECT COUNT(*) FROM {tbl} WHERE {col} = ?",
                        (sid,),
                        default=0,
                    ) or 0
                    if n:
                        msg_count = n
                        break
                except Exception:
                    continue
            # Fall back to length of sources_used JSON list if no turns table
            if not msg_count:
                src = r.get("sources_used") or ""
                msg_count = src.count(",") + 1 if src else 0
            sessions.append({
                "session_uuid": r.get("session_uuid") or "",
                "topic": r.get("topic") or "Untitled brainstorm",
                "summary": (r.get("summary") or "")[:160],
                "started_at": (r.get("created_at") or "")[:10],
                "message_count": msg_count,
            })
    return templates.TemplateResponse(
        request,
        "partials/thinking_brainstorm.html",
        {"sessions": sessions},
    )


@router.get("/api/partial/thinking/brainstorm-sessions", response_class=HTMLResponse)
async def thinking_brainstorm_sessions(request: Request):
    sessions = db_query(
        "SELECT bs.session_uuid, bs.title, bs.status, bs.started_at, bs.updated_at, "
        "COUNT(bt.id) as turn_count "
        "FROM brainstorm_sessions bs "
        "LEFT JOIN brainstorm_turns bt ON bs.session_uuid = bt.session_uuid "
        "GROUP BY bs.id ORDER BY bs.updated_at DESC LIMIT 10",
        default=[],
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_brainstorm_sessions.html",
        {"sessions": [dict(s) for s in (sessions or [])]},
    )


# ---------------------------------------------------------------------------
# Export latest idea as a personal note (Phase 9)
# ---------------------------------------------------------------------------


@router.post("/api/note/from-latest-idea")
async def note_from_latest_idea():
    rows = db_query(
        "SELECT id, content FROM ideas ORDER BY created_at DESC LIMIT 1"
    ) or []
    if not rows:
        return JSONResponse(
            {"status": "empty", "message": "No ideas to export."},
            status_code=200,
        )
    idea = rows[0]
    content = idea.get("content") or ""
    now = datetime.datetime.now().isoformat()
    try:
        db_execute(
            "INSERT INTO personal_notes (content, tags, created_at) VALUES (?, ?, ?)",
            (content, "exported-from-idea", now),
        )
        return JSONResponse(
            {"status": "ok", "preview": content[:120], "source_idea_id": idea.get("id")}
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"I couldn't save note: {e}"},
            status_code=500,
        )
