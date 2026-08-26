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
from fastapi.responses import HTMLResponse, JSONResponse
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


def _add_months(base: dt.date, n: int) -> dt.date:
    """`base` shifted by n months, clamped to the last valid day.

    31 January + 1 month is 28 February, not an error and not 3 March. Clamping
    is the behaviour a person expects from "the 31st of every month" in a month
    that has no 31st.
    """
    y, m = divmod((base.year * 12 + base.month - 1) + n, 12)
    m += 1
    last = [31, 29 if (y % 4 == 0 and (y % 100 or y % 400 == 0)) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return dt.date(y, m, min(base.day, last))


def _occurrences(start: dt.date, rule: str, until, a: dt.date, b: dt.date) -> list:
    """Every date in [a,b] on which a repeating plan falls.

    The first occurrence inside the window is computed directly rather than by
    stepping from `start`, so a rule that began years ago costs the same as one
    that began yesterday. A calendar drawn for one month must not get slower
    because a weekly reminder is old.
    """
    if start > b or (until and until < a):
        return []
    stop = min(b, until) if until else b
    out: list = []
    if rule == "weekdays":
        # Monday-to-Friday. The common case for work reminders, and clumsy to
        # express otherwise — five weekly rules is five rows to keep in step.
        cur = max(start, a)
        while cur <= stop:
            if cur.weekday() < 5:
                out.append(cur)
            cur += dt.timedelta(days=1)
        return out
    if rule == "daily":
        cur = max(start, a)
    elif rule == "weekly":
        cur = start
        if cur < a:
            cur += dt.timedelta(weeks=((a - cur).days + 6) // 7)
    elif rule in ("monthly", "yearly"):
        step = 1 if rule == "monthly" else 12
        n = 0
        if start < a:
            gap = (a.year * 12 + a.month) - (start.year * 12 + start.month)
            n = max(0, (gap // step) - 1)
        cur = _add_months(start, n * step)
        while cur < a:
            n += 1
            cur = _add_months(start, n * step)
        while cur <= stop:
            out.append(cur)
            n += 1
            cur = _add_months(start, n * step)
        return out
    else:
        return []
    delta = dt.timedelta(days=1) if rule == "daily" else dt.timedelta(weeks=1)
    while cur <= stop:
        out.append(cur)
        cur += delta
    return out


def _plans_between(a: dt.date, b: dt.date) -> dict[str, list[dict]]:
    """Map every date in [a,b] to the plans covering it.

    A span is expanded across the days it covers rather than stored per-day, so
    editing "this week is the MLA revision" edits one row and not seven.
    """
    # `recurrence` may not exist on an install that predates repeating plans, and
    # a calendar that 500s because of a missing column is worse than one that
    # shows no repeats. Detect once, degrade quietly.
    has_rec = bool(db_query(
        "SELECT 1 FROM pragma_table_info('day_plan') WHERE name='recurrence'", default=[]))
    rec_col = "d.recurrence" if has_rec else "'' AS recurrence"
    rec_filter = "AND COALESCE(d.recurrence,'') = ''" if has_rec else ""

    rows = db_query(
        f"""SELECT d.plan_id, d.start_date, d.end_date, d.kind, d.project_id, d.text,
                  d.remind_at, d.done, {rec_col}, p.title AS project_title, p.accent_color
           FROM day_plan d LEFT JOIN projects p ON p.project_id = d.project_id
           WHERE date(d.start_date) <= date(?)
             AND date(COALESCE(NULLIF(d.end_date,''), d.start_date)) >= date(?)
             {rec_filter}
           ORDER BY d.kind, d.remind_at, d.plan_id""",
        (b.isoformat(), a.isoformat()),
    ) or []
    out: dict[str, list[dict]] = {}
    for r in rows:
        r = dict(r)
        st = _parse(r["start_date"])
        e = _parse(r["end_date"] or r["start_date"])
        cur = max(st, a)
        while cur <= min(e, b):
            r2 = dict(r)
            r2["_is_start"] = (cur == st)
            r2["_spans"] = (e > st)
            out.setdefault(cur.isoformat(), []).append(r2)
            cur += dt.timedelta(days=1)

    if not has_rec:
        return out

    # Repeating plans: one row, expanded here. `end_date` on a recurring row is
    # when the SERIES stops, not a multi-day span — the two readings are mutually
    # exclusive and add_reminder documents that.
    has_dur = bool(db_query(
        "SELECT 1 FROM pragma_table_info('day_plan') WHERE name='duration_days'", default=[]))
    dur_col = "d.duration_days" if has_dur else "1 AS duration_days"
    reps = db_query(
        f"""SELECT d.plan_id, d.start_date, d.end_date, d.kind, d.project_id, d.text,
                  d.remind_at, d.done, d.recurrence, {dur_col},
                  p.title AS project_title, p.accent_color
           FROM day_plan d LEFT JOIN projects p ON p.project_id = d.project_id
           WHERE COALESCE(d.recurrence,'') <> '' AND date(d.start_date) <= date(?)
           ORDER BY d.kind, d.remind_at, d.plan_id""",
        (b.isoformat(),),
    ) or []
    if not reps:
        return out

    ids = [r["plan_id"] for r in reps]
    marks = db_query(
        "SELECT plan_id, occurred_on, status, moved_to FROM day_plan_occurrence "
        f"WHERE plan_id IN ({','.join('?' * len(ids))})", tuple(ids), default=[]) or []
    by_occ = {(m["plan_id"], m["occurred_on"]): m for m in marks}

    for r in reps:
        r = dict(r)
        pid = r["plan_id"]
        rule = r["recurrence"]
        dur = max(1, int(r.get("duration_days") or 1))
        until = _parse(r["end_date"]) if r.get("end_date") else None
        # Widen the search window backwards by the span length, or an occurrence
        # that STARTED before this month would vanish from it entirely.
        for occ in _occurrences(_parse(r["start_date"]), rule, until,
                                a - dt.timedelta(days=dur - 1), b):
            mark = by_occ.get((pid, occ.isoformat()))
            status = (mark or {}).get("status") or ""
            if status == "skipped":
                continue  # this one occurrence was dropped; the series continues
            # A moved occurrence renders on its new date but keeps its RULE date
            # as its identity, so un-moving it later is still possible.
            shown = _parse(mark["moved_to"]) if (status == "moved" and mark.get("moved_to")) else occ
            for i in range(dur):
                d = shown + dt.timedelta(days=i)
                if not (a <= d <= b):
                    continue
                r2 = dict(r)
                r2["_is_start"] = (i == 0)
                r2["_spans"] = dur > 1
                r2["_occ"] = occ.isoformat()
                r2["_moved"] = (status == "moved")
                r2["done"] = 1 if status == "done" else 0
                out.setdefault(d.isoformat(), []).append(r2)
    return out


# A stable colour per project, derived from its id.
#
# The dot exists to tell one project from another at a glance in a dense week.
# Only 1 of 15 active projects has an `accent_color` set, so a dot drawn only
# when one exists was a channel that worked for one project and nobody else —
# which is the same as not having it.
#
# Derived, not random: the same project gets the same hue on every machine and
# every reload, because the input is its id. And derived colours are constrained
# to a fixed lightness and saturation so they read as one family rather than
# fifteen unrelated colours — the design audit's conclusion was that the visual
# system is not the problem, and fifteen arbitrary hues would make it one.
#
# An explicitly chosen `accent_color` always wins. A colour the researcher picked
# means something; this one only has to be consistent.
def _project_hue(key: str) -> str:
    import hashlib
    h = int(hashlib.sha1((key or "").encode("utf-8")).hexdigest()[:8], 16)
    # 12 well-separated hues, skipping the 0-20 deg band reserved for alerts.
    hue = 30 + (h % 12) * 27
    return f"hsl({hue} 42% 52%)"


def _chip(p: dict, compact: bool = True) -> str:
    """One plan, rendered as a chip.

    ONE CHANNEL, ONE MEANING. The docstring used to say "colour carries the kind"
    while the code did something else: a project chip took the PROJECT's
    `accent_color`, so colour meant "kind" for reminders, learning and focus, and
    "which project" for the fourth. A blue chip could be a study block or it could
    be the project whose accent happens to be blue, and nothing on the calendar
    told you which. Two variables on one channel is not a legend, it is a guess.

    Fixed 2026-08-26 by splitting them:
        border + icon colour  → the KIND, always, all four values
        the dot before the label → WHICH PROJECT, matching the legend under the
                                   calendar, and drawn only when there is one

    Both signals survive; neither has to be inferred from the other.
    """
    pid = p["plan_id"]
    done = int(p.get("done") or 0)
    kind = p.get("kind") or "focus"
    project_dot = ""
    if kind == "project":
        label = p.get("project_title") or p.get("project_id") or "project"
        colour = "var(--m-accent)"
        icon = "◆"
        _pc = p.get("accent_color") or _project_hue(p.get("project_id") or label)
        project_dot = (
            f'<span title="{_esc(label)}" style="width:6px;height:6px;'
            f'border-radius:50%;background:{_pc};flex-shrink:0;"></span>')
    elif kind == "reminder":
        label = p.get("text") or "reminder"
        colour = "var(--m-warn, #c98a2b)"
        icon = "◔"
        if p.get("remind_at"):
            label = f"{p['remind_at']} {label}"
    elif kind == "learning":
        # A scheduled lesson or study block. Text carries "Course — lesson".
        label = p.get("text") or "study"
        colour = "var(--m-accent-2, #4a7fa5)"
        icon = "◈"
    else:
        label = p.get("text") or "focus"
        colour = "var(--m-muted)"
        icon = "▸"
    cont = "" if p.get("_is_start", True) else "… "
    _occ_hint = (" — repeats; click to tick off this occurrence, ✕ to skip it, "
                 "⦸ to end the series") if p.get("_occ") else \
                " — click to toggle done, ✕ to remove"
    # A repeating chip must tell the toggle WHICH occurrence was clicked.
    _occ = p.get("_occ") or ""
    _occ_vals = (' hx-vals=\'{"occurred_on": "%s"}\'' % _occ) if _occ else ""
    if _occ:
        icon = "⇄" if p.get("_moved") else "↻"
    deco = "text-decoration:line-through;opacity:0.45;" if done else ""

    # A repeating plan needs TWO removals, because "delete" is ambiguous on a
    # series and silently picking one is how people lose a year of reminders.
    # ✕ drops this occurrence only; ⦸ ends the whole series. Every calendar that
    # gets this right — Outlook, Google, iCal — asks the same question.
    if _occ:
        _remove_controls = (
            f'<span hx-post="/api/plan/{pid}/skip" hx-target="#work-calendar"'
            f' hx-swap="outerHTML"{_occ_vals}'
            f' hx-confirm="Skip just this one occurrence? The series continues."'
            f' title="Skip only this occurrence — the series continues"'
            f' aria-label="Skip only this occurrence"'
            f' style="opacity:0.35;cursor:pointer;flex-shrink:0;padding:0 2px;">✕</span>'
            f'<span hx-post="/api/plan/{pid}/delete" hx-target="#work-calendar"'
            f' hx-swap="outerHTML"'
            f' hx-confirm="Delete the WHOLE repeating series, every past and future'
            f' occurrence? This cannot be undone."'
            f' title="Delete the entire series — every occurrence, past and future"'
            f' aria-label="Delete the entire repeating series"'
            f' style="opacity:0.45;cursor:pointer;flex-shrink:0;padding:0 2px;'
            f'font-size:9px;font-family:var(--m-mono);letter-spacing:.04em;'
            f'white-space:nowrap;">⦸ ALL</span>'
        )
    else:
        _remove_controls = (
            f'<span hx-post="/api/plan/{pid}/delete" hx-target="#work-calendar"'
            f' hx-swap="outerHTML" hx-confirm="Remove this from the plan?"'
            f' style="opacity:0.35;cursor:pointer;flex-shrink:0;padding:0 2px;">✕</span>'
        )
    return (
        f'<div class="cal-chip" data-plan="{pid}" draggable="true" '
        f'ondragstart="calDragPlan(event,{pid})" '
        f'title="{_esc(label)}{_occ_hint}" '
        f'style="display:flex;align-items:center;gap:4px;font-size:10.5px;line-height:1.25;'
        f'padding:2px 5px;margin-bottom:2px;border-radius:4px;cursor:grab;'
        f'border-left:2px solid {colour};background:var(--m-surface-2,rgba(127,127,127,0.08));{deco}">'
        f'<span style="color:{colour};flex-shrink:0;">{icon}</span>'
        f'{project_dot}'
        f'<span hx-post="/api/plan/{pid}/done" hx-target="#work-calendar" hx-swap="outerHTML"'
        f'{_occ_vals}'
        f' style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer;">'
        f'{cont}{_esc(label)[:60]}</span>'
        f'{_remove_controls}'
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
        f'background:{r["accent_color"] or _project_hue(r["project_id"] or r["title"])};'
        f'"></span>{_esc(r["title"])[:34]}</div>'
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
    kind = kind if kind in ("project", "focus", "reminder", "learning") else "focus"
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


@router.post("/api/plan/learning/schedule", response_class=JSONResponse)
async def schedule_course(
    slug: str = Form(...),
    title: str = Form(""),
    start_date: str = Form(""),
    weekdays: str = Form("1"),        # comma-separated, Mon=0 … Sun=6
    per_slot: int = Form(1),          # lessons per scheduled day
) -> JSONResponse:
    """Lay a course's remaining lessons across the Work calendar.

    One day_plan row per study block, kind='learning', so a course plans exactly
    like a project and shows up beside project work. Idempotent per lesson: a
    lesson already scheduled and not yet done is left where it is.
    """
    from routers.learning import _load_lessons_json  # local import avoids a cycle

    data = _load_lessons_json(slug)
    lessons = data.get("lessons", []) or []
    if not lessons:
        return JSONResponse({"status": "empty",
                             "message": "That course has no lessons yet."}, status_code=400)

    done_ids = set()
    try:
        rows = db_query("SELECT lesson_id FROM lesson_completions WHERE course_slug=?",
                        (slug,), default=[]) or []
        done_ids = {r["lesson_id"] for r in rows}
    except Exception:
        pass

    already = set()
    try:
        rows = db_query("SELECT text FROM day_plan WHERE kind='learning' AND COALESCE(done,0)=0 "
                        "AND text LIKE ?", (f"%[{slug}]%",), default=[]) or []
        already = {r["text"] for r in rows}
    except Exception:
        pass

    todo = [l for l in lessons if l["id"] not in done_ids]
    if not todo:
        return JSONResponse({"status": "complete",
                             "message": "Every lesson in that course is already done."})

    try:
        days = sorted({int(x) for x in weekdays.split(",") if x.strip() != ""})
    except ValueError:
        days = [1]
    days = [d for d in days if 0 <= d <= 6] or [1]
    per_slot = max(1, min(per_slot, 5))

    cursor = _parse(start_date) if start_date else _today()
    label = title or slug.replace("-", " ").title()
    written = 0
    for i in range(0, len(todo), per_slot):
        # advance to the next allowed weekday
        guard = 0
        while cursor.weekday() not in days and guard < 14:
            cursor += dt.timedelta(days=1)
            guard += 1
        chunk = todo[i:i + per_slot]
        text = f"{label} — " + "; ".join(l["title"][:48] for l in chunk) + f" [{slug}]"
        if text not in already:
            db_execute(
                "INSERT INTO day_plan (start_date,end_date,kind,project_id,text,updated_at) "
                "VALUES (?,NULL,'learning',NULL,?,datetime('now'))",
                (cursor.isoformat(), text),
            )
            written += 1
        cursor += dt.timedelta(days=1)

    return JSONResponse({"status": "ok", "scheduled": written,
                         "lessons": len(todo), "from": start_date or str(_today()),
                         "message": f"Scheduled {written} study block(s) for {label}."})


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
async def plan_done(plan_id: int, view: str = Form("month"), anchor: str = Form(""),
                    occurred_on: str = Form("")) -> HTMLResponse:
    # A repeating plan is one row covering many days, so `done` cannot live on it:
    # ticking one Monday would strike through every Monday. Those are recorded per
    # occurrence instead. Single-date plans keep the original behaviour exactly.
    if occurred_on:
        _ensure_occ_table()
        cur_status = db_scalar(
            "SELECT status FROM day_plan_occurrence WHERE plan_id=? AND occurred_on=?",
            (plan_id, occurred_on), default="")
        _set_occ(plan_id, occurred_on, "" if cur_status == "done" else "done")
        return await work_calendar(view=view, date=anchor)

    cur = db_scalar("SELECT COALESCE(done,0) FROM day_plan WHERE plan_id=?", (plan_id,), default=0)
    db_execute("UPDATE day_plan SET done=?, updated_at=datetime('now') WHERE plan_id=?",
               (0 if cur else 1, plan_id))
    return await work_calendar(view=view, date=anchor)


def _ensure_occ_table() -> None:
    db_execute(
        "CREATE TABLE IF NOT EXISTS day_plan_occurrence ("
        "plan_id INTEGER NOT NULL, occurred_on TEXT NOT NULL, "
        "status TEXT NOT NULL DEFAULT '', moved_to TEXT, notified_at TEXT, "
        "updated_at TEXT NOT NULL DEFAULT (datetime('now')), "
        "PRIMARY KEY (plan_id, occurred_on))")


def _set_occ(plan_id: int, occurred_on: str, status: str, moved_to=None) -> None:
    """Record what happened to ONE occurrence of a repeating plan."""
    db_execute(
        "INSERT INTO day_plan_occurrence (plan_id, occurred_on, status, moved_to, updated_at) "
        "VALUES (?,?,?,?,datetime('now')) "
        "ON CONFLICT(plan_id, occurred_on) DO UPDATE SET "
        "status=excluded.status, moved_to=excluded.moved_to, updated_at=datetime('now')",
        (plan_id, occurred_on, status, moved_to))


@router.post("/api/plan/{plan_id}/skip", response_class=HTMLResponse)
async def plan_skip(plan_id: int, view: str = Form("month"), anchor: str = Form(""),
                    occurred_on: str = Form("")) -> HTMLResponse:
    """Drop ONE occurrence of a repeat without touching the series.

    Deleting the row would remove every occurrence, which is almost never what
    "remove this one" means — and is unrecoverable.
    """
    if occurred_on:
        _ensure_occ_table()
        _set_occ(plan_id, occurred_on, "skipped")
    return await work_calendar(view=view, date=anchor)


@router.post("/api/plan/{plan_id}/move-occurrence", response_class=HTMLResponse)
async def plan_move_occurrence(plan_id: int, view: str = Form("month"),
                               anchor: str = Form(""), occurred_on: str = Form(""),
                               to: str = Form("")) -> HTMLResponse:
    """Move ONE occurrence to another date, leaving the rule alone.

    The occurrence keeps its rule date as its identity, so it can be moved again
    or put back; `moved_to` is where it is drawn, not what it is.
    """
    if occurred_on and to:
        _ensure_occ_table()
        _set_occ(plan_id, occurred_on, "moved", to)
    return await work_calendar(view=view, date=anchor)


@router.post("/api/plan/{plan_id}/delete", response_class=HTMLResponse)
async def plan_delete(plan_id: int, view: str = Form("month"), anchor: str = Form("")) -> HTMLResponse:
    db_execute("DELETE FROM day_plan WHERE plan_id=?", (plan_id,))
    # Occurrence rows would otherwise outlive their plan and silently re-apply if
    # a future plan reused the id.
    db_execute("DELETE FROM day_plan_occurrence WHERE plan_id=?", (plan_id,))
    return await work_calendar(view=view, date=anchor)
