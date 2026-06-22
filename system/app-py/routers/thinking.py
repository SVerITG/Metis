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
        "SELECT idea_id AS id, text AS content, tags, created_at FROM ideas WHERE tags NOT LIKE '%archived%' ORDER BY created_at DESC LIMIT 12"
    ) or []
    today = datetime.date.today()
    items = ""
    for i, t in enumerate(threads):
        title = (t.get("content") or "")[:45]
        date_str = (t.get("created_at") or "")[:10]
        # compute age in days
        age = None
        age_color = "var(--m-accent)"
        try:
            d = datetime.date.fromisoformat(date_str)
            age = (today - d).days
            if age >= 30:
                age_color = "var(--m-alert)"
            elif age >= 14:
                age_color = "var(--m-ochre)"
        except Exception:
            pass
        # mono meta line: "Nd · OPEN"
        age_part = f"{age}D · " if age is not None else ""
        meta = (
            f'<div style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.16em;'
            f'color:{age_color};margin-top:6px;">{age_part}OPEN</div>'
        )
        # first thread reads as active — accent left border + wash
        active = i == 0
        edge = (
            "border-left:2px solid var(--m-accent);background:var(--m-accent-wash);"
            if active else "border-left:2px solid transparent;"
        )
        items += (
            f'<div style="padding:13px 16px 13px 14px;{edge}'
            f'border-bottom:1px solid var(--m-rule-soft);cursor:pointer;'
            f'transition:background 120ms ease;" '
            f'onmouseover="if(!this.dataset.active)this.style.background=\'var(--m-surface-2)\';" '
            f'onmouseout="if(!this.dataset.active)this.style.background=\'transparent\';"'
            f'{" data-active=1" if active else ""}>'
            f'<div style="font-family:var(--m-display);font-size:13px;color:var(--m-ink);line-height:1.35;">{title}</div>'
            f'{meta}</div>'
        )
    if not items:
        items = ('<div style="padding:24px 16px;font-family:var(--m-display);font-style:italic;'
                 'font-size:14px;color:var(--m-muted);line-height:1.6;">'
                 'No open threads. Capture a thought and it will open one here.</div>')
    return HTMLResponse(items)


@router.get("/api/partial/thinking/dialogue", response_class=HTMLResponse)
async def thinking_dialogue(request: Request):
    ideas = db_query(
        "SELECT text AS content, created_at FROM ideas ORDER BY created_at DESC LIMIT 5"
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
        "SELECT idea_id AS id, text AS content, tags, created_at "
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
        "SELECT note_id AS id, content, tags, created_at "
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
        "SELECT idea_id AS id, text AS content, created_at "
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
        "SELECT idea_id AS id, text AS content FROM ideas ORDER BY created_at DESC LIMIT 1"
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


# ---------------------------------------------------------------------------
# Idea mindmap — renders the user's ideas + idea_links as a clustered radial
# mindmap (themes as branches, ideas as leaves, links as cross-connections).
# Pure server-side SVG, no JS graph library.
# ---------------------------------------------------------------------------

_IDEA_TYPE_COLOR = {
    "research": "var(--m-accent)",
    "question": "#c98a2b",
    "note": "#8a8a8a",
    "method": "#3a8f7a",
    "literature": "#7a5ea8",
    "teaching": "#4a8f4a",
}


def _xml(s) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _mm_clean(text: str) -> str:
    t = (text or "").strip()
    # strip a leading "i: " / "q: " / "n: " marker
    if len(t) > 2 and t[1] == ":" and t[0].lower() in "iqnlm":
        t = t[2:].strip()
    return t


def _mm_label(text: str, n: int = 34) -> str:
    t = _mm_clean(text)
    return (t[: n - 1] + "…") if len(t) > n else t


def _build_mindmap_svg(ideas: list, links: list) -> str:
    import math
    W, H = 860, 560
    cx, cy = W / 2, H / 2
    R1, R2 = 132, 232

    groups: dict = {}
    for it in ideas:
        groups.setdefault((it.get("domain") or "Other"), []).append(it)
    domains = list(groups.keys())
    nD = max(1, len(domains))

    pos: dict = {}
    branch_svg, hub_svg, nodes_svg = [], [], []

    for di, dom in enumerate(domains):
        a = -math.pi / 2 + 2 * math.pi * di / nD
        hx, hy = cx + R1 * math.cos(a), cy + R1 * math.sin(a)
        branch_svg.append(
            f'<path d="M{cx:.0f},{cy:.0f} Q{(cx+hx)/2:.0f},{(cy+hy)/2:.0f} {hx:.0f},{hy:.0f}" '
            f'fill="none" stroke="var(--m-rule-strong)" stroke-width="1"/>')
        anchor = "start" if math.cos(a) >= 0 else "end"
        hub_svg.append(f'<circle cx="{hx:.0f}" cy="{hy:.0f}" r="3.5" fill="var(--m-ink)"/>')
        hub_svg.append(
            f'<text x="{hx + (6 if anchor=="start" else -6):.0f}" y="{hy+3:.0f}" '
            f'text-anchor="{anchor}" font-family="var(--m-mono)" font-size="9" '
            f'fill="var(--m-ink)" letter-spacing="0.04em">{_xml(dom.upper())}</text>')

        items = groups[dom]
        k = len(items)
        sector = min(2 * math.pi / nD * 0.85, 1.1)
        for ii, it in enumerate(items):
            off = 0 if k == 1 else (sector * (ii / (k - 1) - 0.5))
            ia = a + off
            ix, iy = cx + R2 * math.cos(ia), cy + R2 * math.sin(ia)
            pos[it.get("idea_id")] = (ix, iy)
            branch_svg.append(
                f'<path d="M{hx:.0f},{hy:.0f} Q{(hx+ix)/2:.0f},{(hy+iy)/2:.0f} {ix:.0f},{iy:.0f}" '
                f'fill="none" stroke="var(--m-rule)" stroke-width="1"/>')
            color = _IDEA_TYPE_COLOR.get(it.get("idea_type") or "", "var(--m-accent)")
            ianchor = "start" if math.cos(ia) >= 0 else "end"
            lx = ix + (9 if ianchor == "start" else -9)
            nodes_svg.append(
                f'<circle cx="{ix:.0f}" cy="{iy:.0f}" r="5.5" fill="{color}">'
                f'<title>{_xml(_mm_clean(it.get("text","")))}</title></circle>')
            nodes_svg.append(
                f'<text x="{lx:.0f}" y="{iy+3:.0f}" text-anchor="{ianchor}" '
                f'font-family="var(--m-display)" font-size="11.5" fill="var(--m-text)">'
                f'{_xml(_mm_label(it.get("text","")))}</text>')

    link_svg = []
    for ln in links:
        a_id, b_id = ln.get("idea_id_a"), ln.get("idea_id_b")
        if a_id in pos and b_id in pos:
            x1, y1 = pos[a_id]
            x2, y2 = pos[b_id]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ctrlx, ctrly = mx + (cx - mx) * 0.30, my + (cy - my) * 0.30
            link_svg.append(
                f'<path d="M{x1:.0f},{y1:.0f} Q{ctrlx:.0f},{ctrly:.0f} {x2:.0f},{y2:.0f}" '
                f'fill="none" stroke="var(--m-accent)" stroke-width="1.1" '
                f'stroke-dasharray="3 3" opacity="0.55">'
                f'<title>{_xml(ln.get("link_label",""))}</title></path>')

    center_svg = (
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="26" fill="var(--m-surface-2)" '
        f'stroke="var(--m-rule-strong)" stroke-width="1"/>'
        f'<text x="{cx:.0f}" y="{cy-1:.0f}" text-anchor="middle" font-family="var(--m-mono)" '
        f'font-size="8.5" fill="var(--m-muted)" letter-spacing="0.1em">MY</text>'
        f'<text x="{cx:.0f}" y="{cy+9:.0f}" text-anchor="middle" font-family="var(--m-mono)" '
        f'font-size="8.5" fill="var(--m-muted)" letter-spacing="0.1em">IDEAS</text>'
    )

    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:100%;height:auto;display:block;">'
        + "".join(branch_svg) + "".join(link_svg) + "".join(hub_svg) + center_svg + "".join(nodes_svg)
        + "</svg>"
    )


@router.get("/api/partial/thinking/mindmap", response_class=HTMLResponse)
async def thinking_mindmap(request: Request):
    """Render the user's ideas + idea_links as a clustered mindmap (SVG)."""
    ideas = db_query(
        "SELECT idea_id, text, domain, idea_type, tags FROM ideas "
        "ORDER BY created_at DESC LIMIT 24"
    ) or []
    try:
        links = db_query("SELECT idea_id_a, idea_id_b, link_label FROM idea_links") or []
    except Exception:
        links = []
    if not ideas:
        return HTMLResponse(
            '<p style="color:var(--m-muted);font-style:italic;font-family:var(--m-display);'
            'font-size:13px;margin:0;">No ideas captured yet — capture a few and they\'ll map here.</p>')
    svg = _build_mindmap_svg(ideas, links)
    legend_items = [
        ("research", "var(--m-accent)"), ("question", "#c98a2b"), ("method", "#3a8f7a"),
        ("note", "#8a8a8a"), ("literature", "#7a5ea8"), ("teaching", "#4a8f4a"),
    ]
    legend = (
        '<div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;padding-top:10px;'
        'border-top:1px solid var(--m-rule-soft);font-family:var(--m-mono);font-size:8.5px;'
        'letter-spacing:0.08em;color:var(--m-muted);">'
        + "".join(
            f'<span style="display:inline-flex;align-items:center;gap:5px;">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{c};display:inline-block;"></span>'
            f'{k.upper()}</span>'
            for k, c in legend_items)
        + '<span style="display:inline-flex;align-items:center;gap:5px;">'
        '<span style="width:14px;border-top:1.5px dashed var(--m-accent);display:inline-block;"></span>'
        'CONNECTION</span></div>'
    )
    return HTMLResponse(svg + legend)
