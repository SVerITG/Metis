"""routers/calendar_plan.py — the Work calendar: day, week and month planning.

WHY A CALENDAR IN WORK
    Work could show what exists (projects, tasks) but not WHEN anything happens.
    A researcher plans in days: "Tuesday is the Angola profile", "this whole week
    is the MLA revision". Neither of those is a task — a task has no date and a
    due-date is a deadline, not an intention. So the planner needs its own object.

ONE TABLE, THREE KINDS
    `day_plan` rows differ only in `kind`:
      project   — a project dragged onto a day, that day's focus
      focus     — free text, written for a day or a span of days
      reminder  — the same, with a time, shown with a bell
    Multiple rows per date is the normal case, not an edge case: a day can carry
    several focuses. `end_date` spans a focus across days without duplicating rows,
    which is what keeps "this week is the MLA revision" a single editable thing.

WHY THE PAST IS NOT HIDDEN
    Past days render with their plans intact and dimmed. A planner that erases
    what you intended is useless for the question you actually ask later — "what
    was I doing when this went wrong?"
"""

from __future__ import annotations

import calendar as _calendar
import datetime as dt
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_execute, db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _today() -> dt.date:
    return dt.date.today()


def _parse(s: str | None) -> dt.date:
    try:
        return dt.date.fromisoformat((s or "").strip())
    except Exception:
        return _today()


def _esc(s) -> str:
    return (str(s or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _range_for(view: str, anchor: dt.date) -> tuple[dt.date, dt.date]:
    if view == "day":
        return anchor, anchor
    if view == "week":
        start = anchor - dt.timedelta(days=anchor.weekday())
        return start, start + dt.timedelta(days=6)
    # month: pad to whole weeks so the grid is rectangular
    first = anchor.replace(day=1)
    last = anchor.replace(day=_calendar.monthrange(anchor.year, anchor.month)[1])
    return first - dt.timedelta(days=first.weekday()), last + dt.timedelta(days=6 - last.weekday())


def _plans_between(a: dt.date, b: dt.date) -> dict[str, list[dict]]:
    """Map every date in [a,b] to the plans covering it.

    A span is expanded across the days it covers rather than stored per-day, so
    editing "this week is the MLA revision" edits one row and not seven.
    """
    rows = db_query(
        """SELECT d.plan_id, d.start_date, d.end_date, d.kind, d.project_id, d.text,
                  d.remind_at, d.done, p.title AS project_title, p.accent_color
           FROM day_plan d LEFT JOIN projects p ON p.project_id = d.project_id
           WHERE date(d.start_date) <= date(?)
             AND date(COALESCE(NULLIF(d.end_date,''), d.start_date)) >= date(?)
           ORDER BY d.kind, d.remind_at, d.plan_id""",
        (b.isoformat(), a.isoformat()),
    ) or []
    out: dict[str, list[dict]] = {}
    for r in rows:
        r = dict(r)
        s = _parse(r["start_date"])
        e = _parse(r["end_date"] or r["start_date"])
        cur = max(s, a)
        while cur <= min(e, b):
            r2 = dict(r)
            r2["_is_start"] = (cur == s)
            r2["_spans"] = (e > s)
            out.setdefault(cur.isoformat(), []).append(r2)
            cur += dt.timedelta(days=1)
    return out


def _chip(p: dict, compact: bool = True) -> str:
    """One plan, rendered as a chip. Colour carries the kind; text carries the meaning."""
    pid = p["plan_id"]
    done = int(p.get("done") or 0)
    kind = p.get("kind") or "focus"
    if kind == "project":
        label = p.get("project_title") or p.get("project_id") or "project"
        colour = p.get("accent_color") or "var(--m-accent)"
        icon = "◆"
    elif kind == "reminder":
        label = p.get("text") or "reminder"
        colour = "var(--m-warn, #c98a2b)"
        icon = "◔"
        if p.get("remind_at"):
            label = f"{p['remind_at']} {label}"
    else:
        label = p.get("text") or "focus"
        colour = "var(--m-muted)"
        icon = "▸"
    cont = "" if p.get("_is_start", True) else "… "
    deco = "text-decoration:line-through;opacity:0.45;" if done else ""
    return (
        f'<div class="cal-chip" data-plan="{pid}" draggable="true" '
        f'ondragstart="calDragPlan(event,{pid})" '
        f'title="{_esc(label)} — click to toggle done, ✕ to remove" '
        f'style="display:flex;align-items:center;gap:4px;font-size:10.5px;line-height:1.25;'
        f'padding:2px 5px;margin-bottom:2px;border-radius:4px;cursor:grab;'
        f'border-left:2px solid {colour};background:var(--m-surface-2,rgba(127,127,127,0.08));{deco}">'
        f'<span style="color:{colour};flex-shrink:0;">{icon}</span>'
        f'<span hx-post="/api/plan/{pid}/done" hx-target="#work-calendar" hx-swap="outerHTML"'
        f' style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer;">'
        f'{cont}{_esc(label)[:60]}</span>'
        f'<span hx-post="/api/plan/{pid}/delete" hx-target="#work-calendar" hx-swap="outerHTML"'
        f' hx-confirm="Remove this from the plan?"'
        f' style="opacity:0.35;cursor:pointer;flex-shrink:0;padding:0 2px;">✕</span>'
        f'</div>'
    )


def _day_cell(d: dt.date, plans: list[dict], anchor: dt.date, view: str,
              min_h: int, show_dow: bool = False) -> str:
    today = _today()
    past = d < today
    is_today = d == today
    other_month = (view == "month" and d.month != anchor.month)

    bg = "var(--m-surface,transparent)"
    if is_today:
        bg = "color-mix(in srgb, var(--m-accent) 8%, transparent)"
    opacity = "0.4" if other_month else ("0.72" if past else "1")

    num = f'{d.day}'
    head = (f'<div style="display:flex;align-items:baseline;gap:5px;margin-bottom:3px;">'
            f'<span style="font-family:var(--m-mono);font-size:10px;'
            f'{"font-weight:700;color:var(--m-accent);" if is_today else "color:var(--m-muted);"}">'
            f'{DAY_NAMES[d.weekday()] + " " if show_dow else ""}{num}</span>'
            f'{"<span style=font-size:9px;color:var(--m-accent);>TODAY</span>" if is_today else ""}'
            f'</div>')

    chips = "".join(_chip(p) for p in plans)
    return (
        f'<div class="cal-day" data-date="{d.isoformat()}" '
        f'ondragover="event.preventDefault();this.style.outline=\'1px dashed var(--m-accent)\';" '
        f'ondragleave="this.style.outline=\'none\';" '
        f'ondrop="calDrop(event,\'{d.isoformat()}\')" '
        f'onclick="calAddFocus(event,\'{d.isoformat()}\')" '
        f'style="border:1px solid var(--m-rule);border-radius:5px;padding:5px 6px;'
        f'min-height:{min_h}px;background:{bg};opacity:{opacity};overflow:hidden;cursor:pointer;">'
        f'{head}{chips}</div>'
    )


def _projects_rail() -> str:
    rows = db_query(
        "SELECT project_id, title, accent_color FROM projects "
        "WHERE status IN ('active','incubating') ORDER BY status DESC, display_order, title"
    ) or []
    chips = "".join(
        f'<div draggable="true" ondragstart="calDragProject(event,\'{_esc(r["project_id"])}\')" '
        f'title="Drag onto a day to make it that day\'s focus" '
        f'style="display:flex;align-items:center;gap:5px;font-size:11px;padding:4px 8px;'
        f'border:1px solid var(--m-rule);border-radius:14px;cursor:grab;white-space:nowrap;">'
        f'<span style="width:6px;height:6px;border-radius:50%;flex-shrink:0;'
        f'background:{r["accent_color"] or "var(--m-accent)"};"></span>{_esc(r["title"])[:34]}</div>'
        for r in rows
    )
    return (
        '<div style="margin-bottom:12px;">'
        '<div style="font-family:var(--m-mono);font-size:9.5px;letter-spacing:0.12em;'
        'text-transform:uppercase;color:var(--m-muted);margin-bottom:6px;">'
        'Drag a project onto a day &nbsp;·&nbsp; click a day to write a focus</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;">{chips}</div></div>'
    )


# ── the calendar ──────────────────────────────────────────────────────────────

@router.get("/api/partial/work/calendar", response_class=HTMLResponse)
async def work_calendar(view: str = "month", date: str = "") -> HTMLResponse:
    view = view if view in ("day", "week", "month") else "month"
    anchor = _parse(date) if date else _today()
    a, b = _range_for(view, anchor)
    plans = _plans_between(a, b)

    if view == "month":
        step_prev = (anchor.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
        nxt = anchor.replace(day=_calendar.monthrange(anchor.year, anchor.month)[1]) + dt.timedelta(days=1)
        label = anchor.strftime("%B %Y")
    elif view == "week":
        step_prev, nxt = anchor - dt.timedelta(days=7), anchor + dt.timedelta(days=7)
        label = f"{a.strftime('%d %b')} – {b.strftime('%d %b %Y')}"
    else:
        step_prev, nxt = anchor - dt.timedelta(days=1), anchor + dt.timedelta(days=1)
        label = anchor.strftime("%A %d %B %Y")

    def nav_btn(txt, v, d, primary=False):
        return (f'<button hx-get="/api/partial/work/calendar?view={v}&date={d}" '
                f'hx-target="#work-calendar" hx-swap="outerHTML" '
                f'style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.08em;'
                f'text-transform:uppercase;padding:4px 10px;border:1px solid var(--m-rule);'
                f'border-radius:4px;cursor:pointer;'
                f'background:{"var(--m-accent)" if primary else "transparent"};'
                f'color:{"var(--m-on-accent)" if primary else "var(--m-muted)"};">{txt}</button>')

    switch = "".join(nav_btn(v.upper(), v, anchor.isoformat(), primary=(v == view))
                     for v in ("day", "week", "month"))

    header = (
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'gap:12px;flex-wrap:wrap;margin-bottom:12px;">'
        '<div style="display:flex;align-items:center;gap:8px;">'
        + nav_btn("‹", view, step_prev.isoformat())
        + f'<span style="font-family:var(--m-display);font-size:16px;min-width:190px;'
          f'text-align:center;">{label}</span>'
        + nav_btn("›", view, nxt.isoformat())
        + nav_btn("Today", view, _today().isoformat())
        + '</div>'
        + f'<div style="display:flex;gap:4px;">{switch}</div></div>'
    )

    if view == "day":
        body = ('<div style="display:grid;grid-template-columns:1fr;">'
                + _day_cell(anchor, plans.get(anchor.isoformat(), []), anchor, view, 220, True)
                + '</div>')
    else:
        min_h = 118 if view == "week" else 78
        dow = "".join(
            f'<div style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:var(--m-muted);text-align:center;padding-bottom:4px;">{n}</div>'
            for n in DAY_NAMES)
        cells, cur = [], a
        while cur <= b:
            cells.append(_day_cell(cur, plans.get(cur.isoformat(), []), anchor, view, min_h))
            cur += dt.timedelta(days=1)
        body = (f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;">{dow}</div>'
                f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;">'
                + "".join(cells) + '</div>')

    total = db_scalar("SELECT COUNT(*) FROM day_plan", default=0) or 0
    foot = (f'<div style="margin-top:8px;font-family:var(--m-mono);font-size:9.5px;'
            f'color:var(--m-muted);">{total} planned item(s) · past days stay visible</div>')

    return HTMLResponse(
        f'<div id="work-calendar" data-view="{view}" data-anchor="{anchor.isoformat()}">'
        f'{_projects_rail()}{header}{body}{foot}</div>'
    )


# ── writes ────────────────────────────────────────────────────────────────────

@router.post("/api/plan/create", response_class=HTMLResponse)
async def plan_create(
    start_date: str = Form(...),
    kind: str = Form("focus"),
    project_id: str = Form(""),
    text: str = Form(""),
    end_date: str = Form(""),
    remind_at: str = Form(""),
    view: str = Form("month"),
    anchor: str = Form(""),
) -> HTMLResponse:
    kind = kind if kind in ("project", "focus", "reminder") else "focus"
    if kind == "project" and not project_id:
        kind = "focus"
    if kind != "project" and not text.strip():
        # An empty focus is the user cancelling the prompt; do not write a blank row.
        return await work_calendar(view=view, date=anchor or start_date)
    db_execute(
        "INSERT INTO day_plan (start_date,end_date,kind,project_id,text,remind_at,updated_at) "
        "VALUES (?,?,?,?,?,?,datetime('now'))",
        (start_date, end_date or None, kind, project_id or None,
         text.strip() or None, remind_at or None),
    )
    return await work_calendar(view=view, date=anchor or start_date)


@router.post("/api/plan/{plan_id}/move", response_class=HTMLResponse)
async def plan_move(plan_id: int, start_date: str = Form(...),
                    view: str = Form("month"), anchor: str = Form("")) -> HTMLResponse:
    """Drag an existing plan to another day. A span keeps its length rather than collapsing."""
    row = db_query("SELECT start_date, end_date FROM day_plan WHERE plan_id=?", (plan_id,))
    if row:
        r = dict(row[0])
        new_end = None
        if r.get("end_date"):
            span = (_parse(r["end_date"]) - _parse(r["start_date"])).days
            new_end = (_parse(start_date) + dt.timedelta(days=span)).isoformat()
        db_execute("UPDATE day_plan SET start_date=?, end_date=?, updated_at=datetime('now') "
                   "WHERE plan_id=?", (start_date, new_end, plan_id))
    return await work_calendar(view=view, date=anchor or start_date)


@router.post("/api/plan/{plan_id}/done", response_class=HTMLResponse)
async def plan_done(plan_id: int, view: str = Form("month"), anchor: str = Form("")) -> HTMLResponse:
    cur = db_scalar("SELECT COALESCE(done,0) FROM day_plan WHERE plan_id=?", (plan_id,), default=0)
    db_execute("UPDATE day_plan SET done=?, updated_at=datetime('now') WHERE plan_id=?",
               (0 if cur else 1, plan_id))
    return await work_calendar(view=view, date=anchor)


@router.post("/api/plan/{plan_id}/delete", response_class=HTMLResponse)
async def plan_delete(plan_id: int, view: str = Form("month"), anchor: str = Form("")) -> HTMLResponse:
    db_execute("DELETE FROM day_plan WHERE plan_id=?", (plan_id,))
    return await work_calendar(view=view, date=anchor)
