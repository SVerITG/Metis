"""
routers/meetings.py — Meetings tab routes.
"""

import datetime
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query, db_scalar, _connect

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


# ---------------------------------------------------------------------------
# DB migration — add columns that may not exist yet
# ---------------------------------------------------------------------------

def _ensure_columns():
    """Add extra columns if they don't exist (idempotent)."""
    try:
        conn = _connect()
        cur = conn.cursor()
        for col, typedef in [
            ("transcript", "TEXT"),
            ("duration_minutes", "INTEGER"),
            ("status", "TEXT DEFAULT 'filed'"),
        ]:
            try:
                cur.execute(f"ALTER TABLE meetings ADD COLUMN {col} {typedef}")
                conn.commit()
            except Exception:
                pass  # column already exists
        # create meeting_actions if missing
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meeting_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                due_date TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass


# NOTE: _ensure_columns() is invoked from main.py's lifespan startup (wrapped),
# not at import time — so a DB hiccup can never crash the whole dashboard.


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

_ACTION_RE = re.compile(
    r"^(?:[-*]\s*)?(?:action|todo|to[\s-]do|task|action item)s?:\s*(.+)$",
    re.IGNORECASE,
)
_CHECKBOX_RE = re.compile(r"^[-*]\s*\[[ x]\]\s*(.+)$", re.IGNORECASE)
_DECISION_RE = re.compile(
    r"^(?:[-*]\s*)?(?:decision|decided|agreed|resolved|conclusion)s?:\s*(.+)$",
    re.IGNORECASE,
)
_FOLLOWUP_RE = re.compile(
    r"^(?:[-*]\s*)?(?:follow[\s-]?up|next step|next action|by next)s?:\s*(.+)$",
    re.IGNORECASE,
)


def _extract_structure(text: str) -> dict:
    """Return {actions, decisions, follow_ups} extracted from free text."""
    actions, decisions, follow_ups = [], [], []
    lines = text.splitlines()
    in_actions_block = False
    in_decisions_block = False
    in_followups_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            in_actions_block = in_decisions_block = in_followups_block = False
            continue

        # Section header detection
        low = stripped.lower()
        if re.match(r"^(?:action items?|actions?|todos?|tasks?)[\s:]*$", low):
            in_actions_block = True
            in_decisions_block = in_followups_block = False
            continue
        if re.match(r"^(?:decisions?|agreed|resolved)[\s:]*$", low):
            in_decisions_block = True
            in_actions_block = in_followups_block = False
            continue
        if re.match(r"^(?:follow[\s-]?ups?|next steps?)[\s:]*$", low):
            in_followups_block = True
            in_actions_block = in_decisions_block = False
            continue

        # Collect under active section
        if in_actions_block and stripped.startswith(("-", "*", "•")):
            item = re.sub(r"^[-*•]\s*(?:\[[ x]\])?\s*", "", stripped).strip()
            if item:
                actions.append(item)
            continue
        if in_decisions_block and stripped.startswith(("-", "*", "•")):
            item = re.sub(r"^[-*•]\s*", "", stripped).strip()
            if item:
                decisions.append(item)
            continue
        if in_followups_block and stripped.startswith(("-", "*", "•")):
            item = re.sub(r"^[-*•]\s*", "", stripped).strip()
            if item:
                follow_ups.append(item)
            continue

        # Inline pattern matching
        m = _ACTION_RE.match(stripped)
        if m:
            actions.append(m.group(1).strip())
            continue
        m = _CHECKBOX_RE.match(stripped)
        if m:
            actions.append(m.group(1).strip())
            continue
        m = _DECISION_RE.match(stripped)
        if m:
            decisions.append(m.group(1).strip())
            continue
        m = _FOLLOWUP_RE.match(stripped)
        if m:
            follow_ups.append(m.group(1).strip())
            continue

    return {"actions": actions, "decisions": decisions, "follow_ups": follow_ups}


def _fast_keyword_connections(text: str, max_results: int = 6) -> list[dict]:
    """Keyword-only SQL cross-pollination — no embedding model required."""
    import re as _re
    stopwords = {"about", "after", "before", "between", "could", "should",
                 "would", "their", "there", "which", "where", "these", "those",
                 "with", "from", "have", "been", "this", "that", "into", "also",
                 "when", "then", "than", "they", "were", "what", "your", "just"}
    words = _re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    keywords = [w for w in words if w not in stopwords][:8]
    if not keywords:
        return []
    try:
        from db import get_db_path
        db_path = get_db_path()
        if not db_path or not db_path.exists():
            return []
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        results: list[dict] = []
        like_conds = " OR ".join(["title LIKE ?" for _ in keywords])
        params = [f"%{k}%" for k in keywords]
        for table, col, source in [
            ("literature_metadata", "title", "library"),
            ("meetings",           "title", "meeting"),
            ("news_briefs",        "title", "news"),
            ("ideas",              "content", "idea"),
        ]:
            try:
                q = f"SELECT title, '{source}' as source FROM {table} WHERE "
                if table == "ideas":
                    q = f"SELECT content as title, '{source}' as source FROM {table} WHERE "
                    like_conds2 = " OR ".join(["content LIKE ?" for _ in keywords])
                    rows = conn.execute(q + like_conds2 + " LIMIT ?", params + [max_results]).fetchall()
                else:
                    rows = conn.execute(q + like_conds + " LIMIT ?", params + [max_results]).fetchall()
                for r in rows:
                    results.append({"title": (r["title"] or "")[:100], "source": source})
                    if len(results) >= max_results:
                        break
            except Exception:
                continue
        conn.close()
        seen: set[str] = set()
        unique = []
        for r in results:
            k = r["title"][:40].lower()
            if k not in seen:
                seen.add(k)
                unique.append(r)
            if len(unique) >= max_results:
                break
        return unique
    except Exception:
        return []


def _surface_connections(text: str, max_results: int = 6) -> list[dict]:
    """Return cross-pollination matches — tries MCP vector+keyword first, SQL-only fallback."""
    try:
        from metis_mcp.tools.ideas import _cross_pollinate_core  # type: ignore
        result = _cross_pollinate_core(text, max_results=max_results) or []
        if result:
            return result
    except Exception as e:
        import sys
        print(f"[live-meeting] _cross_pollinate_core failed: {e}", file=sys.stderr, flush=True)
    return _fast_keyword_connections(text, max_results=max_results)


# ---------------------------------------------------------------------------
# Core tab routes
# ---------------------------------------------------------------------------


@router.get("/tab/meetings", response_class=HTMLResponse)
async def meetings_tab(request: Request):
    return templates.TemplateResponse(
        request, "meetings.html", {"active_tab": "meetings"}
    )


@router.get("/api/tab/meetings", response_class=HTMLResponse)
async def meetings_tab_partial(request: Request):
    return templates.TemplateResponse(
        request, "meetings.html", {"active_tab": "meetings"}
    )


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/meta", response_class=HTMLResponse)
async def meetings_meta(request: Request):
    today = datetime.date.today().isoformat()
    today_count = db_scalar(
        "SELECT COUNT(*) FROM meetings WHERE meeting_date = ?", (today,), default=0
    ) or 0
    week_start = (
        datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    ).isoformat()
    week_count = db_scalar(
        "SELECT COUNT(*) FROM meetings WHERE meeting_date >= ?", (week_start,), default=0
    ) or 0
    total = db_scalar("SELECT COUNT(*) FROM meetings", default=0) or 0
    return HTMLResponse(
        f"{today_count} TODAY · {week_count} THIS WEEK · {total} TOTAL"
    )


@router.get("/api/partial/meetings/next-label", response_class=HTMLResponse)
async def meetings_next_label(request: Request):
    today = datetime.date.today().isoformat()
    nxt = db_query(
        "SELECT title, meeting_date, transcript_status FROM meetings "
        "WHERE meeting_date >= ? ORDER BY meeting_date LIMIT 1",
        (today,),
    )
    if nxt:
        m = nxt[0]
        status = (m.get("transcript_status") or "UPCOMING").upper()
        label = (m.get("meeting_date") or "")[:10]
        return HTMLResponse(
            f'<span>Next meeting</span><span class="tail">{status} · {label}</span>'
        )
    return HTMLResponse(
        '<span>Next meeting</span><span class="tail">NONE SCHEDULED</span>'
    )


@router.get("/api/partial/meetings/upcoming", response_class=HTMLResponse)
async def meetings_upcoming(request: Request):
    today = datetime.date.today().isoformat()
    rows = db_query(
        "SELECT meeting_id as id, meeting_date as date, title, attendees as participants, "
        "duration_minutes, transcript_status as status, decisions as notes "
        "FROM meetings WHERE meeting_date >= ? ORDER BY meeting_date LIMIT 1",
        (today,),
    ) or []
    meeting = rows[0] if rows else None
    return templates.TemplateResponse(
        request, "partials/meetings_upcoming.html", {"meeting": meeting}
    )


@router.get("/api/partial/meetings/transcripts", response_class=HTMLResponse)
async def meetings_transcripts(request: Request):
    rows = db_query(
        "SELECT meeting_id as id, meeting_date as date, title, duration_minutes, "
        "transcript_status as status "
        "FROM meetings ORDER BY meeting_date DESC LIMIT 5"
    ) or []
    return templates.TemplateResponse(
        request, "partials/meetings_transcripts.html", {"meetings": rows}
    )


@router.get("/api/partial/meetings/week-ahead", response_class=HTMLResponse)
async def meetings_week_ahead(request: Request):
    today = datetime.date.today().isoformat()
    week_end = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    rows = db_query(
        "SELECT meeting_date as date, title, attendees as participants, "
        "transcript_status as status "
        "FROM meetings WHERE meeting_date >= ? AND meeting_date <= ? "
        "ORDER BY meeting_date LIMIT 5",
        (today, week_end),
    ) or []
    return templates.TemplateResponse(
        request, "partials/meetings_week_ahead.html", {"meetings": rows}
    )


@router.get("/api/partial/meetings/follow-ups", response_class=HTMLResponse)
async def meetings_follow_ups(request: Request):
    actions = db_query(
        "SELECT ma.description, ma.status, ma.due_date, "
        "m.title as meeting_title, m.meeting_date as meeting_date "
        "FROM meeting_actions ma JOIN meetings m ON ma.meeting_id = m.meeting_id "
        "WHERE ma.status != 'done' ORDER BY ma.due_date NULLS LAST LIMIT 10"
    ) or []
    return templates.TemplateResponse(
        request, "partials/meetings_follow_ups.html", {"actions": actions}
    )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/stats", response_class=HTMLResponse)
async def meetings_stats(request: Request):
    total = db_scalar("SELECT COUNT(*) FROM meetings", default=0)
    month_start = datetime.date.today().replace(day=1).isoformat()
    this_month = db_scalar(
        "SELECT COUNT(*) FROM meetings WHERE meeting_date >= ?",
        (month_start,),
        default=0,
    )
    open_actions = db_scalar(
        "SELECT COUNT(*) FROM meeting_actions WHERE status != 'done'", default=0
    )
    avg_dur = db_scalar(
        "SELECT ROUND(AVG(duration_minutes)) FROM meetings WHERE duration_minutes IS NOT NULL",
        default=0,
    )
    return templates.TemplateResponse(
        request,
        "partials/meetings_stats.html",
        {
            "total": total,
            "this_month": this_month,
            "open_actions": open_actions,
            "avg_dur": avg_dur,
        },
    )


# ---------------------------------------------------------------------------
# Meeting list + search
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/list", response_class=HTMLResponse)
async def meetings_list(request: Request, filter: str = "month"):
    if filter == "week":
        cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    elif filter == "month":
        cutoff = datetime.date.today().replace(day=1).isoformat()
    else:
        cutoff = "2000-01-01"
    meetings = db_query(
        "SELECT meeting_id as id, meeting_date as date, title, "
        "attendees as participants, duration_minutes, "
        "transcript_status as status "
        "FROM meetings WHERE meeting_date >= ? ORDER BY meeting_date DESC LIMIT 100",
        (cutoff,),
    )
    return templates.TemplateResponse(
        request, "partials/meetings_list.html", {"meetings": meetings}
    )


@router.get("/api/partial/meetings/search", response_class=HTMLResponse)
async def meetings_search(request: Request, q: str = ""):
    if not q or len(q) < 2:
        meetings = db_query(
            "SELECT meeting_id as id, meeting_date as date, title, "
            "attendees as participants, duration_minutes, transcript_status as status "
            "FROM meetings ORDER BY meeting_date DESC LIMIT 100"
        )
    else:
        pattern = f"%{q}%"
        meetings = db_query(
            "SELECT meeting_id as id, meeting_date as date, title, "
            "attendees as participants, duration_minutes, transcript_status as status "
            "FROM meetings WHERE title LIKE ? OR attendees LIKE ? OR transcript LIKE ? "
            "ORDER BY meeting_date DESC LIMIT 50",
            (pattern, pattern, pattern),
        )
    return templates.TemplateResponse(
        request, "partials/meetings_list.html", {"meetings": meetings}
    )


# ---------------------------------------------------------------------------
# Import form
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/import-form", response_class=HTMLResponse)
async def meetings_import_form(request: Request):
    today = datetime.date.today().isoformat()
    return templates.TemplateResponse(
        request, "partials/meeting_import_form.html", {"today": today}
    )


@router.post("/api/meeting/import", response_class=HTMLResponse)
async def meeting_import(
    request: Request,
    title: str = Form(...),
    meeting_date: str = Form(...),
    attendees: str = Form(""),
    duration_minutes: str = Form(""),
    meeting_type: str = Form("meeting"),
    transcript: str = Form(""),
):
    now = datetime.datetime.now().isoformat(timespec="seconds")

    extracted = _extract_structure(transcript)
    actions_json = json.dumps(extracted["actions"])
    decisions_json = json.dumps(extracted["decisions"])
    followups_json = json.dumps(extracted["follow_ups"])

    dur = None
    try:
        dur = int(duration_minutes) if duration_minutes.strip() else None
    except ValueError:
        pass

    try:
        db_execute(
            """INSERT INTO meetings
               (title, meeting_date, attendees, meeting_type, transcript,
                action_items, decisions, follow_ups, transcript_status,
                duration_minutes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'filed', ?, ?)""",
            (
                title.strip(),
                meeting_date,
                attendees.strip(),
                meeting_type,
                transcript.strip(),
                actions_json,
                decisions_json,
                followups_json,
                dur,
                now,
            ),
        )

        # Save extracted actions to meeting_actions table
        if extracted["actions"]:
            row = db_query(
                "SELECT meeting_id FROM meetings WHERE created_at = ? LIMIT 1", (now,)
            )
            if row:
                mid = row[0]["meeting_id"]
                for act in extracted["actions"]:
                    db_execute(
                        "INSERT INTO meeting_actions (meeting_id, description, status, created_at) "
                        "VALUES (?, ?, 'open', ?)",
                        (mid, act, now),
                    )

        connections = _surface_connections(
            (title + " " + transcript)[:800]
        )

    except Exception as e:
        return HTMLResponse(
            f'<div style="color:var(--m-alert);font-family:var(--m-mono);font-size:10px;'
            f'padding:12px 0;">ERROR: {e}</div>'
        )

    return templates.TemplateResponse(
        request,
        "partials/meeting_import_result.html",
        {
            "title": title,
            "extracted": extracted,
            "connections": connections,
        },
    )


# ---------------------------------------------------------------------------
# Meeting detail
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/detail/{meeting_id}", response_class=HTMLResponse)
async def meeting_detail(request: Request, meeting_id: int):
    rows = db_query(
        "SELECT meeting_id as id, title, meeting_date as date, attendees as participants, "
        "duration_minutes, transcript_status as status, transcript, "
        "decisions, action_items, follow_ups, meeting_type, domain "
        "FROM meetings WHERE meeting_id = ?",
        (meeting_id,),
    )
    if not rows:
        return HTMLResponse(
            '<div class="panel panel-pad" style="padding:24px;">Meeting not found.</div>'
        )
    m = rows[0]

    def _parse_list(val):
        if not val:
            return []
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except Exception:
            return [line.strip() for line in str(val).splitlines() if line.strip()]

    actions = _parse_list(m.get("action_items"))
    decisions = _parse_list(m.get("decisions"))
    follow_ups = _parse_list(m.get("follow_ups"))
    connections = _surface_connections(
        ((m.get("title") or "") + " " + (m.get("transcript") or ""))[:800]
    )

    return templates.TemplateResponse(
        request,
        "partials/meeting_detail.html",
        {
            "meeting": m,
            "actions": actions,
            "decisions": decisions,
            "follow_ups": follow_ups,
            "connections": connections,
        },
    )


# ---------------------------------------------------------------------------
# Live assistant — cross-pollinate without saving
# ---------------------------------------------------------------------------


@router.post("/api/meeting/live-connections", response_class=HTMLResponse)
async def meeting_live_connections(text: str = Form("")):
    if len(text.strip()) < 10:
        return HTMLResponse("")
    connections = _surface_connections(text[:800], max_results=5)
    if not connections:
        return HTMLResponse(
            '<div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;'
            'color:var(--m-muted);padding:8px 0;">NO CONNECTIONS YET</div>'
        )
    source_colors = {
        "library": "var(--m-accent)",
        "meeting": "var(--m-ochre)",
        "news": "var(--m-ok)",
        "idea": "var(--m-muted)",
    }
    rows = "".join(
        f'<div style="display:flex;align-items:baseline;gap:8px;padding:6px 0;'
        f'border-bottom:1px solid var(--m-rule-soft);">'
        f'<span style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.12em;'
        f'color:{source_colors.get(c["source"], "var(--m-muted)")};flex-shrink:0;width:48px;">'
        f'{c["source"].upper()}</span>'
        f'<span style="font-family:var(--m-display);font-size:13px;color:var(--m-ink);'
        f'line-height:1.3;">{(c.get("title") or "")[:80]}</span>'
        f'</div>'
        for c in connections
    )
    label = f"{len(connections)} CONNECTION{'S' if len(connections) != 1 else ''}"
    return HTMLResponse(
        f'<div style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.14em;'
        f'color:var(--m-muted);margin-bottom:6px;">{label} SURFACED</div>'
        f'{rows}'
    )


# ---------------------------------------------------------------------------
# Live session endpoints
# ---------------------------------------------------------------------------


@router.get("/api/partial/meetings/live-assist", response_class=HTMLResponse)
async def meetings_live_assist(request: Request):
    """Read-only status pane for the live meeting assistant.

    Shows whether a live session is active, the last few cross-pollination
    connections we've surfaced in recent meetings, and an invitation to start
    a new one.
    """
    now = datetime.datetime.now()
    today = now.date().isoformat()

    # 'Live' = a meeting filed today with meeting_type='live'
    # We also try to detect any meeting started in the last 60 minutes,
    # regardless of meeting_type, since a recording session is the truest signal.
    live_today = db_query(
        "SELECT meeting_id, title, attendees, meeting_date, created_at, "
        "duration_minutes, status FROM meetings "
        "WHERE meeting_type = 'live' AND meeting_date = ? "
        "ORDER BY meeting_id DESC LIMIT 1",
        (today,),
    ) or []
    live = live_today[0] if live_today else None

    # Elapsed minutes — "started" is approximated from created_at where present
    elapsed_min = None
    fresh = False
    if live:
        try:
            created_raw = (live.get("created_at") or "").replace("Z", "")
            if created_raw:
                started = datetime.datetime.fromisoformat(created_raw[:19])
                elapsed_min = int((now - started).total_seconds() // 60)
                fresh = elapsed_min is not None and elapsed_min <= 60
        except Exception:
            elapsed_min = None
            fresh = True  # filed today is a fair "fresh" signal

    # Last few connections: derive from the most recent live meetings by
    # cross-pollinating their title + transcript snippet.
    recent_live = db_query(
        "SELECT title, transcript FROM meetings "
        "WHERE meeting_type = 'live' AND transcript IS NOT NULL AND transcript != '' "
        "ORDER BY meeting_id DESC LIMIT 3",
    ) or []

    connections: list[dict] = []
    for m in recent_live:
        seed = ((m.get("title") or "") + " " + (m.get("transcript") or ""))[:400]
        try:
            for c in _fast_keyword_connections(seed, max_results=1) or []:
                connections.append({
                    "title": c.get("title", "")[:80],
                    "source": c.get("source", ""),
                    "from_meeting": (m.get("title") or "")[:60],
                })
        except Exception:
            continue
        if len(connections) >= 3:
            break

    return templates.TemplateResponse(
        request,
        "partials/meetings_live_assist.html",
        {
            "live": live,
            "live_fresh": fresh,
            "elapsed_min": elapsed_min,
            "connections": connections,
        },
    )


@router.get("/api/partial/meetings/live-setup", response_class=HTMLResponse)
async def meeting_live_setup(request: Request):
    return templates.TemplateResponse(
        request, "partials/meeting_live_setup.html", {}
    )


@router.get("/api/partial/meetings/live-session", response_class=HTMLResponse)
async def meeting_live_session(
    request: Request,
    title: str = Query("Meeting"),
    speakers: str = Query(""),
):
    return templates.TemplateResponse(
        request,
        "partials/meeting_live_session.html",
        {"title": title, "speakers": [s.strip() for s in speakers.split(",") if s.strip()]},
    )


@router.post("/api/meeting/live-segment")
async def meeting_live_segment(
    text: str = Form(""),
    seg_idx: int = Form(0),
):
    """Cross-pollinate a single speech segment. Returns JSON."""
    if len(text.strip()) < 8:
        return JSONResponse({"connections": []})
    connections = _surface_connections(text[:600], max_results=4)
    return JSONResponse({"connections": connections, "seg_idx": seg_idx})


@router.post("/api/meeting/generate-report", response_class=HTMLResponse)
async def meeting_generate_report(
    request: Request,
    transcript: str = Form(""),
    title: str = Form("Meeting"),
    participants: str = Form(""),
    duration: str = Form(""),
    connections: str = Form("[]"),
):
    """Generate a structured meeting report from the live transcript."""
    extracted = _extract_structure(transcript)

    # Parse connections JSON
    try:
        conn_list = json.loads(connections)
    except Exception:
        conn_list = []

    # Build per-speaker word counts for summary
    speaker_turns: dict[str, list[str]] = {}
    for line in transcript.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^\[([^\]]+)\](?:\s*\(\d+:\d+\))?\s*(.*)", line)
        if m:
            spk, text = m.group(1), m.group(2).strip()
            speaker_turns.setdefault(spk, []).append(text)

    # Rough summary: first substantial sentence from each speaker block
    summary_lines = []
    for spk, turns in speaker_turns.items():
        combined = " ".join(turns)
        first = re.split(r"(?<=[.!?])\s+", combined)[:2]
        if first and len(first[0]) > 20:
            summary_lines.append(first[0])

    # Unique connection sources for the report
    lib_connections = [c for c in conn_list if c.get("source") == "library"]
    meeting_connections = [c for c in conn_list if c.get("source") == "meeting"]
    idea_connections = [c for c in conn_list if c.get("source") == "idea"]

    # Save to DB
    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        dur_min = None
        m = re.match(r"(\d+):(\d+)", duration)
        if m:
            dur_min = int(m.group(1)) * 60 + int(m.group(2))
            dur_min = max(1, dur_min // 60)
        db_execute(
            """INSERT INTO meetings
               (title, meeting_date, attendees, meeting_type, transcript,
                action_items, decisions, follow_ups, transcript_status,
                duration_minutes, created_at)
               VALUES (?, ?, ?, 'live', ?, ?, ?, ?, 'filed', ?, ?)""",
            (
                title,
                datetime.date.today().isoformat(),
                participants,
                transcript,
                json.dumps(extracted["actions"]),
                json.dumps(extracted["decisions"]),
                json.dumps(extracted["follow_ups"]),
                dur_min,
                now,
            ),
        )
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "partials/meeting_report.html",
        {
            "title": title,
            "date": datetime.date.today().isoformat(),
            "participants": participants,
            "duration": duration,
            "extracted": extracted,
            "summary_lines": summary_lines,
            "lib_connections": lib_connections,
            "meeting_connections": meeting_connections,
            "idea_connections": idea_connections,
            "all_connections": conn_list,
            "transcript": transcript,
        },
    )


# ---------------------------------------------------------------------------
# Action item toggle (open ↔ done)
# ---------------------------------------------------------------------------


@router.post("/api/meeting/action/{action_id}/toggle", response_class=HTMLResponse)
async def toggle_action(action_id: int):
    row = db_query(
        "SELECT status FROM meeting_actions WHERE id = ?", (action_id,)
    )
    if not row:
        return HTMLResponse("")
    new_status = "done" if row[0]["status"] == "open" else "open"
    db_execute(
        "UPDATE meeting_actions SET status = ? WHERE id = ?",
        (new_status, action_id),
    )
    checked = "checked" if new_status == "done" else ""
    color = "var(--m-muted)" if new_status == "done" else "var(--m-ink)"
    decoration = "line-through" if new_status == "done" else "none"
    return HTMLResponse(
        f'<input type="checkbox" {checked} '
        f'hx-post="/api/meeting/action/{action_id}/toggle" '
        f'hx-target="closest .action-row" hx-swap="outerHTML" '
        f'style="margin-right:8px;cursor:pointer;"> '
        f'<span style="color:{color};text-decoration:{decoration};">'
        f'{row[0].get("description","")}</span>'
    )


# ---------------------------------------------------------------------------
# Create tasks from meeting action items
# ---------------------------------------------------------------------------


@router.post("/api/meeting/{meeting_id}/create-tasks", response_class=HTMLResponse)
async def meeting_create_tasks(request: Request, meeting_id: int):
    """Parse action items from a meeting and insert them as tasks."""
    # Fetch meeting row
    rows = db_query(
        "SELECT meeting_id, title, meeting_date, action_items, transcript "
        "FROM meetings WHERE meeting_id = ?",
        (meeting_id,),
    )
    if not rows:
        return HTMLResponse(
            '<div style="font-family:var(--m-mono);font-size:10px;color:var(--m-alert);padding:10px 0;">'
            "Meeting not found.</div>"
        )
    meeting = rows[0]
    mtitle = meeting.get("title") or "Untitled meeting"
    mdate = (meeting.get("meeting_date") or "")[:10]

    # Prefer structured meeting_actions rows if they exist
    existing_actions = db_query(
        "SELECT description FROM meeting_actions WHERE meeting_id = ? AND status != 'done'",
        (meeting_id,),
    ) or []

    if existing_actions:
        action_texts = [r["description"] for r in existing_actions if r.get("description")]
    else:
        # Fall back to parsing action_items JSON or transcript text
        action_items_raw = meeting.get("action_items") or ""
        action_texts = []
        if action_items_raw:
            try:
                parsed = json.loads(action_items_raw)
                if isinstance(parsed, list):
                    action_texts = [str(a).strip() for a in parsed if str(a).strip()]
            except Exception:
                action_texts = [
                    line.strip() for line in str(action_items_raw).splitlines()
                    if line.strip()
                ]
        # If still empty, try parsing transcript
        if not action_texts and meeting.get("transcript"):
            extracted = _extract_structure(meeting["transcript"])
            action_texts = extracted.get("actions", [])

    if not action_texts:
        return HTMLResponse(
            '<div style="font-family:var(--m-sans);font-size:13px;color:var(--m-muted);'
            'font-style:italic;padding:10px 0;">'
            "No action items found in this meeting’s notes. "
            "Add a meeting report first.</div>"
        )

    now = datetime.datetime.now().isoformat(timespec="seconds")
    notes_prefix = f"Auto-created from meeting: {mtitle} ({mdate})"
    created = 0
    for text in action_texts:
        title = text[:200]
        if not title:
            continue
        task_id = uuid.uuid4().hex[:12]
        try:
            db_execute(
                "INSERT INTO tasks (task_id, project_id, title, status, notes, created_at, updated_at, category) "
                "VALUES (?, NULL, ?, 'open', ?, ?, ?, 'meeting')",
                (task_id, title, notes_prefix, now, now),
            )
            created += 1
        except Exception:
            pass

    if created == 0:
        return HTMLResponse(
            '<div style="font-family:var(--m-sans);font-size:13px;color:var(--m-alert);padding:10px 0;">'
            "I couldn't create tasks — an error occurred.</div>"
        )

    plural = "task" if created == 1 else "tasks"
    return HTMLResponse(
        f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;">'
        f'<span style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;'
        f'color:var(--m-ok);">&#10003; {created} {plural.upper()} CREATED</span>'
        f'<a href="/tab/work" style="font-family:var(--m-mono);font-size:10px;'
        f'letter-spacing:0.12em;color:var(--m-accent);text-decoration:underline;">'
        f'VIEW IN WORK TAB →</a>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Audio transcription — upload audio file → transcribe → store as meeting
# ---------------------------------------------------------------------------

_meeting_whisper = None


def _get_meeting_whisper():
    global _meeting_whisper
    if _meeting_whisper is None:
        from faster_whisper import WhisperModel
        _meeting_whisper = WhisperModel("base", device="cpu", compute_type="int8")
    return _meeting_whisper


@router.post("/meetings/transcribe-audio")
async def meetings_transcribe_audio(
    audio: UploadFile = File(...),
    title: str = Form(""),
):
    """Upload audio file → local transcription → store as meeting with timestamped transcript."""
    suffix = Path(audio.filename or "audio.wav").suffix.lower() or ".wav"
    raw = await audio.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        model = _get_meeting_whisper()
        segments, info = model.transcribe(tmp_path, beam_size=5)
        lines = []
        for s in segments:
            mins, secs = divmod(int(s.start), 60)
            lines.append(f"[{mins:02d}:{secs:02d}] {s.text.strip()}")
        transcript = "\n".join(lines)
        duration_minutes = int(getattr(info, "duration", 0)) // 60

        now = datetime.datetime.now()
        mtitle = title.strip() or f"Meeting {now.strftime('%Y-%m-%d %H:%M')}"
        db_execute(
            "INSERT INTO meetings (title, meeting_date, transcript, duration_minutes, status, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (mtitle, now.date().isoformat(), transcript, duration_minutes, "processed",
             now.isoformat(timespec="seconds")),
        )
        return JSONResponse({
            "ok": True,
            "title": mtitle,
            "lines": len(lines),
            "duration_minutes": duration_minutes,
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
