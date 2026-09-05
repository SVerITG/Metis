"""
routers/work.py — Work tab routes + project launcher + task actions (v7.0).

Project launcher ports the logic from metis/system/app/R/mod_work.R (lines 29-160)
to FastAPI. Supports rstudio, vscode, explorer, claude_desktop, claude_code.
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

import logging
from db import db_execute, db_query, db_scalar, live_task_sql

log = logging.getLogger("metis.work")

_wlog = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


# ---------------------------------------------------------------------------
# Full page
# ---------------------------------------------------------------------------


@router.get("/tab/work", response_class=HTMLResponse)
async def work_tab(request: Request):
    return templates.TemplateResponse(
        request, "work.html", {"active_tab": "work"}
    )


@router.get("/api/tab/work", response_class=HTMLResponse)
async def work_tab_partial(request: Request):
    return templates.TemplateResponse(
        request, "work.html", {"active_tab": "work"}
    )


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/meta", response_class=HTMLResponse)
async def work_meta(request: Request):
    projects = db_scalar("SELECT COUNT(*) FROM projects WHERE status='active'", default=0) or 0
    tasks = db_scalar(f"SELECT COUNT(*) FROM tasks WHERE {live_task_sql()}", default=0) or 0
    paused = db_scalar("SELECT COUNT(*) FROM projects WHERE status='incubating'", default=0) or 0

    # ── "What changed" comes from the SHARED mechanism, not a second one ──
    # The strip that rendered "53 TASKS · FIRST VISIT — NOTHING MARKED SEEN YET"
    # is gone: it printed the same number the figures below already print, once
    # with a direction and once without. But the answer it carried should not
    # be gone with it, and a bespoke opened-minus-closed query here would be a
    # SECOND way of answering a question ui.whats_new already answers for News,
    # Library and the reading stack. Two mechanisms is how the surfaces drifted
    # apart in the first place.
    #
    # So: same helper, different presentation. The number lands inside the
    # figure instead of trailing after it.
    delta = 0
    try:
        import ui
        wn = ui.whats_new("work", "tasks", "created_at",
                          where=f"{live_task_sql()}")
        # On a first visit `newer` is the whole table, and "+53 since you looked"
        # would be a lie about a number that has always been there.
        delta = 0 if wn.get("first_visit") else int(wn.get("newer") or 0)
    except Exception as exc:
        log.warning("work meta: whats_new unavailable: %s", exc)

    # Denominator, direction, and a door — see partials/work_meta.html.
    projects_total = db_scalar("SELECT COUNT(*) FROM projects", default=0) or 0
    overdue = db_scalar(
        f"SELECT COUNT(*) FROM tasks WHERE {live_task_sql()} "
        "AND COALESCE(due_date,'') != '' AND due_date < date('now')", default=0) or 0
    return templates.TemplateResponse(
        request,
        "partials/work_meta.html",
        {"projects": projects, "projects_total": projects_total,
         "tasks": tasks, "overdue": overdue, "delta": delta,
        },
    )


@router.get("/api/partial/work/filter-chips", response_class=HTMLResponse)
async def work_filter_chips(request: Request):
    projects = db_query(
        "SELECT title FROM projects WHERE status IN ('active','incubating') ORDER BY status DESC, title LIMIT 6"
    ) or []
    chips = "".join(
        f'<span class="chip chip--plain" style="cursor:pointer;">{p["title"][:22]}</span>'
        for p in projects
    )
    return HTMLResponse(
        f'<div style="display:flex;gap:10px;margin-bottom:20px;align-items:center;flex-wrap:wrap;">'
        f'<span class="chip chip--mute chip--plain" style="cursor:pointer;">ALL</span>'
        f'{chips}'
        f'<div style="margin-left:auto;display:flex;gap:6px;">'
        f'<button class="btn btn--sec btn--caps" onclick="openCapture(\'t\')">+ Task</button>'
        f'</div></div>'
    )


@router.get("/api/partial/work/kanban", response_class=HTMLResponse)
async def work_kanban(request: Request, filter: str = ""):
    """Tasks by status — the panel the researcher asked to have at the top of the page.

    THE COLUMNS ARE THE STATES, so moving a card between them IS the edit. That
    is the point of putting it first: "Today" was a thing you could only achieve
    by knowing that a task with today's date, or a starred one, surfaces on the
    Today page. Nothing said so, which is why 0 of 92 tasks were starred and 2
    were dated. Dropping a card into Today sets today's date; the same task then
    appears on Today AND in the week on the calendar, because all three read the
    same column.

    Four columns, not five. "Closed this week" was the fourth and it is a log,
    not a state you move work into — the done count lives in the header figures.
    What replaced it is UNDATED, which is where 56 of the 58 live tasks actually
    are and which had no representation at all.

    Cancelled work is not shown anywhere here. Counting it produced the "92" this
    comment used to quote; see `live_task_sql`.
    """
    today_d = datetime.date.today()
    today = today_d.isoformat()
    # End of the working week, not seven days out — the same rule as the date
    # control in `_duedate.html`, so "this week" means one thing in this app.
    week_end = (today_d + datetime.timedelta(days=(4 - today_d.weekday()) % 7)).isoformat()

    # The board honours the project filter, so filtering to Software narrows the
    # board and the project list together rather than only half the page.
    f = (filter or "").strip().lower()
    scope, params = "", []
    if f and f not in ("", "active", "all", "archived"):
        scope = (" AND t.project_id IN (SELECT project_id FROM projects "
                 "WHERE LOWER(COALESCE(category,''))=? OR LOWER(COALESCE(tags,'')) LIKE ? "
                 "OR LOWER(COALESCE(domain,''))=?)")
        params = [f, f"%{f}%", f]

    cols = (
        "SELECT t.task_id as id, t.title, COALESCE(t.category,'') as tag, t.priority, "
        "       t.due_date, t.status, t.project_id, p.title AS project_title "
        "FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id "
    )

    def q(where: str, order: str, limit: int, extra=()):
        return db_query(cols + "WHERE " + where + scope + f" ORDER BY {order} LIMIT {limit}",
                        tuple(list(extra) + params)) or []

    # Overdue belongs in TODAY, not in a column of its own: it is the work you
    # are behind on, and splitting it off is how a separate overdue list becomes
    # a place things go to be ignored.
    # THE FOUR COLUMNS MUST PARTITION, and three of them are date buckets while
    # one is a status. That is the tension to resolve explicitly, because a task
    # that is both in progress and due today would otherwise be drawn twice and
    # counted twice.
    #
    # In progress WINS: it is the strongest thing the row knows about itself.
    # So the date columns take live work that is NOT in progress. Derived from
    # `live_task_sql` rather than a second hand-written status list — this file
    # already carried three rival definitions of "open" and that is precisely
    # how they drifted apart.
    DATED = f"{live_task_sql('t.status')} AND t.status != 'in_progress'"

    today_col = q(f"{DATED} AND COALESCE(t.due_date,'') != '' AND date(t.due_date) <= date(?)",
                  "t.due_date", 12, (today,))
    this_week = q(f"{DATED} AND COALESCE(t.due_date,'') != '' "
                  "AND date(t.due_date) > date(?) AND date(t.due_date) <= date(?)",
                  "t.due_date", 12, (today, week_end))
    in_progress = q("t.status='in_progress'", "t.updated_at DESC", 12)
    undated = q(f"{DATED} AND COALESCE(t.due_date,'') = ''",
                "COALESCE(t.priority, 99), t.created_at DESC", 12)

    def total(where: str, extra=()):
        return db_scalar(
            "SELECT COUNT(*) FROM tasks t WHERE " + where + scope,
            tuple(list(extra) + params), default=0) or 0

    def held(where: str, extra=()):
        """How much of this column is waiting on something else.

        A column is capped at twelve cards and the undated pile is fifty-six
        deep, so including held work in the query made it COUNTED without
        making it SEEN — the two held rows sort to position 47. Reordering the
        backlog to float them would be worse: stuck work would then outrank
        work you could actually start. So the header carries the number, and
        the filter is how you go and look.
        """
        return total(where + " AND t.status='blocked'", extra)

    return templates.TemplateResponse(
        request,
        "partials/work_kanban.html",
        {
            "today": today,
            "filter": f,
            "columns": [
                {"key": "today", "label": "Today", "tasks": today_col,
                 "total": total(f"{DATED} AND COALESCE(t.due_date,'') != '' "
                                "AND date(t.due_date) <= date(?)", (today,)),
                 "held": held(f"{DATED} AND COALESCE(t.due_date,'') != '' "
                              "AND date(t.due_date) <= date(?)", (today,)),
                 "empty": "Nothing due today.",
                 "drop": "Give this today's date"},
                {"key": "week", "label": "This week", "tasks": this_week,
                 "total": total(f"{DATED} AND COALESCE(t.due_date,'') != '' "
                                "AND date(t.due_date) > date(?) AND date(t.due_date) <= date(?)",
                                (today, week_end)),
                 "held": held(f"{DATED} AND COALESCE(t.due_date,'') != '' "
                              "AND date(t.due_date) > date(?) AND date(t.due_date) <= date(?)",
                              (today, week_end)),
                 "empty": "Nothing else due this week.",
                 "drop": "Due by the end of this week"},
                {"key": "progress", "label": "In progress", "tasks": in_progress,
                 "total": total("t.status='in_progress'"),
                 "empty": "Nothing started.",
                 "drop": "Mark as started"},
                {"key": "undated", "label": "No date", "tasks": undated,
                 "total": total(f"{DATED} AND COALESCE(t.due_date,'') = ''"),
                 "held": held(f"{DATED} AND COALESCE(t.due_date,'') = ''"),
                 "empty": "Everything open has a date.",
                 "drop": "Take the date off — undated is never late"},
            ],
        },
    )


@router.post("/api/partial/work/kanban/move", response_class=HTMLResponse)
async def work_kanban_move(request: Request, task_id: str = Form(...),
                           column: str = Form(...), filter: str = Form("")):
    """Move a task between board columns, which means editing what the column means.

    The columns are states, so the drop applies the state:
        today     → due today
        week      → due by the end of the working week
        progress  → status in_progress, date untouched
        undated   → date cleared, which is a real and common choice
                    ("often i dont know when i will work on something")

    `progress` deliberately does NOT clear the date. Starting something does not
    change when it is due, and the earlier version of this board offered only a
    status dropdown, which is why the date and the status could never be set in
    the same gesture.
    """
    today_d = datetime.date.today()
    col = (column or "").strip().lower()
    # Setting a DATE must not silently change a STATUS. An earlier version wrote
    # `status='open'` alongside the date, which would quietly unblock a blocked
    # task because someone dated it — two edits from one gesture, and the one
    # nobody asked for is invisible.
    if col == "today":
        db_execute("UPDATE tasks SET due_date=?, updated_at=? WHERE task_id=?",
                   (today_d.isoformat(), datetime.datetime.now().isoformat(), task_id))
    elif col == "week":
        end = (today_d + datetime.timedelta(days=(4 - today_d.weekday()) % 7)).isoformat()
        db_execute("UPDATE tasks SET due_date=?, updated_at=? WHERE task_id=?",
                   (end, datetime.datetime.now().isoformat(), task_id))
    elif col == "progress":
        db_execute("UPDATE tasks SET status='in_progress', updated_at=? WHERE task_id=?",
                   (datetime.datetime.now().isoformat(), task_id))
    elif col == "undated":
        db_execute("UPDATE tasks SET due_date=NULL, updated_at=? WHERE task_id=?",
                   (datetime.datetime.now().isoformat(), task_id))
    else:
        log.warning("[kanban] unknown column %r for %s", column, task_id)
    return await work_kanban(request, filter=filter)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/stats", response_class=HTMLResponse)
async def work_stats(request: Request):
    today = str(datetime.date.today())
    week_start = (
        datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    ).isoformat()

    open_tasks = db_scalar(
        f"SELECT COUNT(*) FROM tasks WHERE {live_task_sql()}", default=0
    )
    overdue = db_scalar(
        f"SELECT COUNT(*) FROM tasks WHERE {live_task_sql()} "
        "AND COALESCE(due_date,'') != '' AND due_date < ?",
        (today,),
        default=0,
    )
    done_week = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE status = 'done' AND created_at >= ?",
        (week_start,),
        default=0,
    )
    active_projects = db_scalar(
        "SELECT COUNT(*) FROM projects WHERE status = 'active'", default=0
    )
    return templates.TemplateResponse(
        request,
        "partials/work_stats.html",
        {
            "open_tasks": open_tasks,
            "overdue": overdue,
            "done_week": done_week,
            "active_projects": active_projects,
        },
    )


# ---------------------------------------------------------------------------
# Tasks list
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/tasks", response_class=HTMLResponse)
async def work_tasks(request: Request, status: str = "open"):
    if status == "open":
        where = f"{live_task_sql()}"
        params: tuple = ()
    elif status == "all":
        where = "1=1"
        params = ()
    else:
        where = "status = ?"
        params = (status,)

    tasks = db_query(
        f"SELECT task_id as id, title, COALESCE(category,'') as project, "
        f"'medium' as priority, status, due_date "
        f"FROM tasks WHERE {where} "
        f"ORDER BY due_date NULLS LAST, created_at DESC LIMIT 50",
        params,
    )
    return templates.TemplateResponse(
        request,
        "partials/work_tasks.html",
        {"tasks": tasks, "status_filter": status},
    )


# ---------------------------------------------------------------------------
# Due today / overdue strip
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/due-today", response_class=HTMLResponse)
async def work_due_today(request: Request, bare: int = 0):
    today = str(datetime.date.today())
    rows = db_query(
        "SELECT t.task_id as id, t.title, t.status, t.due_date, "
        "COALESCE(t.priority,'medium') as priority, "
        "p.title as project "
        "FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id "
        f"WHERE {live_task_sql('t.status')} "
        "AND COALESCE(t.due_date,'') != '' AND t.due_date <= ? "
        "ORDER BY t.due_date, "
        "CASE COALESCE(t.priority,'medium') WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END "
        "LIMIT 10",
        (today,),
        default=[],
    ) or []
    overdue = [r for r in rows if r["due_date"] < today]
    due_today = [r for r in rows if r["due_date"] == today]
    return templates.TemplateResponse(
        request,
        "partials/work_due_today.html",
        {"overdue": overdue, "due_today": due_today, "today": today, "bare": bool(bare)},
    )


# ---------------------------------------------------------------------------
# All-tasks cross-project view
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/all-tasks", response_class=HTMLResponse)
async def work_all_tasks(request: Request):
    """All open tasks across every project, sorted by priority then due date."""
    today = str(datetime.date.today())
    tasks = db_query(
        "SELECT t.task_id as id, t.title, t.status, t.due_date, "
        "COALESCE(t.priority, 'medium') as priority, COALESCE(t.category,'') as category, "
        "p.title as project "
        "FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id "
        f"WHERE {live_task_sql('t.status')} "
        "ORDER BY "
        "  CASE COALESCE(t.priority,'medium') WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
        "  CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END, "
        "  t.due_date LIMIT 40",
        default=[],
    )
    overdue_ids = {
        r["id"] for r in (db_query(
            f"SELECT task_id as id FROM tasks WHERE {live_task_sql()} "
            "AND COALESCE(due_date,'') != '' AND due_date < ?", (today,), default=[]
        ) or [])
    }
    return templates.TemplateResponse(
        request,
        "partials/work_all_tasks.html",
        {"tasks": tasks, "today": today, "overdue_ids": overdue_ids},
    )


# ---------------------------------------------------------------------------
# Projects list
# ---------------------------------------------------------------------------


# ── WHAT A LAUNCHER ACTUALLY NEEDS ───────────────────────────────────────────
# Every button on a project card used to be offered unconditionally, so the row
# advertised a capability instead of reflecting one. Measured 2026-09-03: the
# launcher list was unset on 17 of 18 projects, and the fallback offered Claude
# Code, Chat and Cowork **even with no folder path** — while 7 of 16 active
# projects have no path at all. Pressing the button then produced a raw
# `[Errno 8] Exec format error`, which tells the reader nothing.
#
# So each target declares its requirements, and nothing is offered that cannot
# run. Two requirements exist:
#
#   "path"  — the target opens a FOLDER, so without one there is nothing to open
#   "url:<column>" — the target opens a stored address
#
# Every target additionally needs Windows interop, because each one ultimately
# starts a Windows application. That is checked separately, once, because when
# it is down NOTHING can launch and saying so once beats eight dead buttons.
_LAUNCH_NEEDS: dict[str, tuple[str, ...]] = {
    "claude_code":   ("path",),      # writes CLAUDE.md there, opens a terminal in it
    "rstudio":       ("path",),
    "vscode":        ("path",),
    "explorer":      ("path",),
    "claude_chat":   (),             # a protocol handler; no folder involved
    "claude_cowork": (),             # copies the path if there is one, works without
    "dashboard":     ("url:dashboard_url",),
    "github":        ("url:github_url",),
}

# Why each target cannot run, written for someone who did not build it.
_LAUNCH_BLOCKED_BECAUSE = {
    "path": "this project has no folder yet",
    "url:dashboard_url": "no dashboard address is saved for this project",
    "url:github_url": "no repository address is saved for this project",
}


def _interop_state() -> tuple[bool, str]:
    """Can this process start a Windows application, and if not, what to do.

    Checked rather than assumed. WSL registers a handler for Windows binaries
    under binfmt_misc; when that registration is missing, every `.exe` fails at
    exec time with `Exec format error` — which is what the page was showing.
    The condition is real, it is not the researcher's mistake, and it has a
    one-line fix, so it is worth saying in words.
    """
    if os.name == "nt":
        return True, ""
    marker = "/proc/sys/fs/binfmt_misc/WSLInterop"
    try:
        if os.path.exists(marker):
            # The handler can be registered but switched off; the file says which.
            with open(marker, "r", encoding="utf-8", errors="replace") as fh:
                if "disabled" in fh.read(64).lower():
                    return False, ("Windows apps are switched off for this Linux "
                                   "session. Run `wsl --shutdown` from a Windows "
                                   "terminal, then start Metis again.")
            return True, ""
    except OSError:
        # Unreadable is not the same as absent; assume it works and let the
        # launch itself report, rather than blocking every button on a guess.
        return True, ""
    return False, ("Windows apps cannot be started from here at the moment, so "
                   "none of these will open. Run `wsl --shutdown` from a Windows "
                   "terminal (PowerShell or Command Prompt), then start Metis "
                   "again — it takes a few seconds and this comes back.")


def _launch_capability(p: dict, target: str) -> tuple[bool, str]:
    """Whether one target can run for one project, and why not."""
    for need in _LAUNCH_NEEDS.get(target, ()):
        if need == "path":
            if not (p.get("external_path") or "").strip():
                return False, _LAUNCH_BLOCKED_BECAUSE["path"]
        elif need.startswith("url:"):
            if not (p.get(need[4:]) or "").strip():
                return False, _LAUNCH_BLOCKED_BECAUSE[need]
    return True, ""


def _parse_launchers(p: dict) -> list:
    """Return launcher list from the launchers JSON column, falling back to launcher_type."""
    raw = p.get("launchers")
    if raw:
        try:
            return _capable_only(p, json.loads(raw))
        except Exception:
            pass
    # Legacy fallback: derive from launcher_type. Each branch lists what this
    # KIND of project would ideally offer; the filter at the end removes
    # whatever this PARTICULAR project cannot do, so a branch can stay generous
    # without the card making a promise it cannot keep.
    lt = p.get("launcher_type") or ""
    if lt == "article":
        wanted = ["explorer", "claude_chat", "claude_cowork"]
    elif lt == "rstudio":
        wanted = ["rstudio", "claude_code", "claude_chat", "claude_cowork", "explorer"]
    elif lt == "vscode":
        wanted = ["vscode", "claude_code", "claude_chat", "claude_cowork", "explorer"]
    else:
        wanted = ["claude_code", "claude_chat", "claude_cowork", "explorer"]

    # A stored address is worth offering wherever it exists, whatever the type.
    for extra, col in (("dashboard", "dashboard_url"), ("github", "github_url")):
        if (p.get(col) or "").strip() and extra not in wanted:
            wanted.insert(0, extra)

    return _capable_only(p, wanted)


def _capable_only(p: dict, targets: list) -> list:
    """Drop every target this project cannot actually run.

    Applied to the EXPLICIT list too, not just the fallback. A launcher list
    saved when a folder existed must not keep advertising the folder after it
    is gone — the stored list is a preference, never a claim about the present.
    """
    return [t for t in targets if _launch_capability(p, t)[0]]


# ── Project categories as a first-class thing ────────────────────────────────
# They used to exist ONLY as whatever strings happened to sit in
# `projects.category`, discovered with SELECT DISTINCT. That is enough to filter
# by and not enough to own: you cannot rename one, merge two, reorder them, or
# create an empty one to move projects into — and a category that disappears the
# moment its last project leaves cannot be a place you put things.
#
# The consequence was visible in the data: 5 of 9 categories held exactly ONE
# project and 2 projects held none, with no way to fix either from the page.
#
# The table carries the NAME as its key rather than an id, so `projects.category`
# stays readable and every existing row keeps working untouched. Renaming is
# therefore a two-step write, which is the price of not migrating 18 rows to
# integer keys for no reader's benefit.
_CATEGORY_DDL = """
CREATE TABLE IF NOT EXISTS project_categories (
    name          TEXT PRIMARY KEY,
    display_order INTEGER NOT NULL DEFAULT 100,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


# Set once the table is known to exist and be seeded. A read path must not take
# a write lock: `CREATE TABLE IF NOT EXISTS` opens a write transaction even when
# it changes nothing, and in WAL mode a write transaction is exclusive across
# EVERY connection — the dashboard, both MCP servers, and any other session on
# this machine. That is precisely the mechanism that made every write in the
# system fail for five minutes after each restart in August, and this function
# sits on the render path of the projects list.
#
# Process-level rather than cached with a TTL: the only thing that could
# invalidate it is the table being dropped, which nothing does.
_CATEGORIES_READY = False


def _ensure_categories(force: bool = False) -> None:
    """Create the table and adopt whatever categories the projects already use.

    Idempotent, additive, and — after the first call in this process — free.
    Seeding never removes a category the researcher created and never renames one. A
    project whose category is not in the table is still shown, under its own
    heading, because dropping it would hide work.
    """
    global _CATEGORIES_READY
    if _CATEGORIES_READY and not force:
        return
    try:
        db_execute(_CATEGORY_DDL)
        existing = {r["name"] for r in (db_query("SELECT name FROM project_categories") or [])}
        rows = db_query(
            "SELECT DISTINCT TRIM(category) AS c FROM projects "
            "WHERE category IS NOT NULL AND TRIM(category) != ''"
        ) or []
        for i, r in enumerate(sorted({r["c"] for r in rows if r["c"]}, key=str.lower)):
            if r not in existing:
                db_execute(
                    "INSERT OR IGNORE INTO project_categories (name, display_order) VALUES (?, ?)",
                    (r, (i + 1) * 10),
                )
        _CATEGORIES_READY = True
    except Exception as exc:
        # Left False on purpose: a transient failure should be retried on the
        # next render rather than latched for the life of the process.
        _wlog.warning("project_categories unavailable: %s", exc)


def _category_order() -> list[str]:
    _ensure_categories()
    rows = db_query(
        "SELECT name FROM project_categories ORDER BY display_order, name COLLATE NOCASE"
    ) or []
    return [r["name"] for r in rows]


def _activity_band(quiet_days) -> str:
    """How alive a project is, in three states rather than two.

    The researcher asked for "active and not so active". The data needs a third: four
    projects have never been opened at all, which is not the same as one that was
    busy in June and has gone quiet. A fortnight is the boundary because it is
    the span in which "I was just working on this" stops being true.
    """
    if quiet_days is None:
        return "never"
    return "hot" if quiet_days <= 14 else "cold"


@router.get("/api/partial/work/projects", response_class=HTMLResponse)
async def work_projects(request: Request, filter: str = ""):
    """Project list, optionally filtered.

    filter='' or 'active' → active, tracked projects
    filter='archived'     → archived projects
    filter=<category>     → active projects whose category OR any tag matches
    """
    cols = (
        "SELECT project_id as id, title, description, domain, priority, next_step, status, "
        "external_path, launcher_type, github_url, launchers, dashboard_url, "
        "project_type, last_session_at, accent_color, category, tags "
        "FROM projects "
    )
    f = (filter or "").strip().lower()
    if f == "archived":
        projects = db_query(cols + "WHERE status = 'archived' ORDER BY COALESCE(display_order, 999) ASC LIMIT 50")
    elif f in ("", "active", "all"):
        projects = db_query(
            cols + "WHERE status = 'active' AND COALESCE(tracked, 1) = 1 "
            "ORDER BY COALESCE(display_order, 999) ASC LIMIT 50"
        )
    else:
        like = f"%{f}%"
        projects = db_query(
            cols + "WHERE status = 'active' AND COALESCE(tracked, 1) = 1 "
            "AND (LOWER(COALESCE(category,'')) = ? OR LOWER(COALESCE(tags,'')) LIKE ? "
            "OR LOWER(COALESCE(domain,'')) = ?) "
            "ORDER BY COALESCE(display_order, 999) ASC LIMIT 50",
            (f, like, f),
        )
    # HOW LONG SINCE THIS MOVED. The card already printed "Last session ·
    # 2026-06-11", which contains the answer but makes the reader do date
    # arithmetic on sixteen cards to find the stalled ones. An age is directly
    # comparable; a date is not.
    #
    # This replaces the sparkline that was approved on 2026-08-28. The data does
    # not support one: there is ONE task event in the last fourteen days, and
    # widening the window makes it worse rather than better — 58 of the last 100
    # events share the date 2026-08-14, which is a bulk write, so the chart would
    # draw a mountain where a migration happened and call it activity. A flat
    # line on fifteen of sixteen rows is a chart of nothing; a misleading spike
    # is worse than nothing.
    today = datetime.date.today()
    for p in (projects or []):
        p["launchers_list"] = _parse_launchers(p)
        p["tags_list"] = [t.strip() for t in (p.get("tags") or "").split(",") if t.strip()]
        p["quiet_days"] = None
        stamp = (p.get("last_session_at") or "")[:10]
        if stamp:
            try:
                p["quiet_days"] = (today - datetime.date.fromisoformat(stamp)).days
            except ValueError:
                pass
    # ── GROUP BY CATEGORY, with each group's own weight ──────────────────────
    # Sixteen cards in one flat two-column grid, ordered by a display_order
    # nobody set, is a list you scan rather than a structure you read. Grouped,
    # each heading carries what the group actually costs — how many projects and
    # how many open tasks — so a collapsed section still tells you whether to
    # open it.
    #
    # Uncategorised comes LAST and is named, not hidden: two projects are in it,
    # and a bucket you cannot see is a bucket you never empty.
    projects = projects or []
    open_by_project = {
        r["pid"]: r["n"] for r in (db_query(
            "SELECT project_id AS pid, COUNT(*) AS n FROM tasks "
            f"WHERE {live_task_sql()} AND project_id IS NOT NULL GROUP BY project_id"
        ) or [])
    }
    for p in projects:
        p["open_tasks"] = open_by_project.get(p.get("id"), 0)
        p["activity"] = _activity_band(p.get("quiet_days"))

    UNCAT = "Uncategorised"
    buckets: dict[str, list] = {}
    for p in projects:
        buckets.setdefault((p.get("category") or "").strip() or UNCAT, []).append(p)

    # EMPTY CATEGORIES STILL GET A HEADING — when the view is unfiltered.
    # Without this, pressing "New category" appeared to do nothing: the category
    # was created, the zone re-rendered, and it was invisible because it held no
    # projects. Which also made the whole point of a first-class category
    # unreachable — you could not create a home and then move things into it.
    #
    # Only when unfiltered, though. Under a filter the empty sections are noise:
    # you asked to see one category, not the nine that do not match.
    show_empty = f in ("", "active", "all")
    ordered = [c for c in _category_order() if c in buckets or show_empty]
    # A category present on a project but not in the table still gets a heading —
    # seeding is additive and must never hide work.
    ordered += sorted((c for c in buckets if c not in ordered and c != UNCAT), key=str.lower)
    if UNCAT in buckets:
        ordered.append(UNCAT)

    groups = [{
        "name": c,
        "slug": re.sub(r"[^a-z0-9]+", "-", c.lower()).strip("-") or "uncategorised",
        "is_uncategorised": c == UNCAT,
        "projects": buckets.get(c, []),
        "n_projects": len(buckets.get(c, [])),
        "n_open": sum(x["open_tasks"] for x in buckets.get(c, [])),
        "n_hot": sum(1 for x in buckets.get(c, []) if x["activity"] == "hot"),
    } for c in ordered]

    # What has been filed against each project, so the evidence appears on the
    # work it belongs to. Omitted refs simply have nothing filed.
    try:
        from routers.shelves import kept_by_ref
        kept = kept_by_ref()
    except Exception:
        log.warning("could not read filed evidence per project", exc_info=True)
        kept = {}
    for _p in projects:
        _p["kept"] = kept.get(_p.get("id") or _p.get("project_id") or "")

    return templates.TemplateResponse(
        request,
        "partials/work_projects.html",
        # The interop state travels with the render so the notice is stated
        # ONCE for the page rather than discovered eight times by pressing
        # eight buttons that all fail the same way.
        {"projects": projects, "groups": groups,
         "all_categories": _category_order(), "uncat_label": UNCAT,
         "interop_ok": _interop_state()[0], "interop_why": _interop_state()[1]},
    )


@router.get("/api/partial/work/category-filters", response_class=HTMLResponse)
async def work_category_filters(request: Request):
    """Filter chips for the Work tab: All · <categories> · Archived.

    Categories are drawn from distinct project categories AND distinct tags, so a
    project carrying multiple tags shows up under each.
    """
    cat_rows = db_query(
        "SELECT DISTINCT category AS c FROM projects "
        "WHERE status='active' AND category IS NOT NULL AND category != ''"
    ) or []
    tag_rows = db_query(
        "SELECT tags FROM projects WHERE status='active' AND tags IS NOT NULL AND tags != ''"
    ) or []
    values = {r["c"].strip() for r in cat_rows if r["c"]}
    for r in tag_rows:
        for t in (r["tags"] or "").split(","):
            if t.strip():
                values.add(t.strip())
    has_archived = (db_scalar("SELECT COUNT(*) FROM projects WHERE status='archived'", default=0) or 0) > 0

    def chip(label, value, active=False):
        """One filter control.

        These are CONTROLS, not badges — you press them and the page changes.
        They were filled pills in the same olive as the project category
        labels beside them, so the row of things you can press and the row of
        things that merely describe a project were the same shape. `.chip-btn`
        is the existing control idiom: text, no fill, a border only when the
        filter is on, which is also the only way to see WHICH filter is on.
        `aria-pressed` says the same thing to a screen reader; the toggling
        JS in work.html keeps it in step.
        """
        cls = "chip-btn work-filter-chip" + (" chip-btn--on" if active else "")
        return (
            f'<button type="button" class="{cls}" data-filter="{value}" '
            f'aria-pressed="{"true" if active else "false"}" '
            f'onclick="filterProjects(\'{value}\', this)">{label}</button>'
        )

    chips = [chip("ALL", "", active=True)]
    chips += [chip(v.upper()[:20], v) for v in sorted(values, key=str.lower)]
    if has_archived:
        chips.append(chip("ARCHIVED", "archived"))

    return HTMLResponse(
        '<div class="work-filter-bar">' + "".join(chips) + "</div>"
    )


@router.post("/api/project/create")
async def project_create(request: Request):
    """Quick-create a project from the Work tab modal."""
    data = await request.json()
    title = (data.get("title") or "").strip()
    if not title:
        return JSONResponse({"status": "error", "message": "Title required"}, status_code=400)
    project_id = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    # Ensure unique id
    existing = db_scalar("SELECT COUNT(*) FROM projects WHERE project_id=?", (project_id,), default=0)
    if existing:
        project_id = f"{project_id}-{uuid.uuid4().hex[:4]}"
    now = datetime.datetime.now().isoformat()
    launchers_default = data.get("launchers", ["claude_code", "claude_desktop"])
    db_execute(
        "INSERT INTO projects (project_id, title, domain, status, priority, description, "
        "external_path, launcher_type, launchers, github_url, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (project_id, title,
         data.get("domain", ""),
         "active",
         data.get("priority", "medium"),
         data.get("description", ""),
         data.get("external_path", ""),
         data.get("launcher_type", "vscode"),
         json.dumps(launchers_default),
         data.get("github_url", ""),
         now),
    )
    return JSONResponse({"status": "ok", "project_id": project_id, "title": title})


_PROJECT_EDITABLE_FIELDS = {
    "title", "category", "accent_color", "description", "domain", "next_step",
}


@router.post("/api/project/update/{project_id}")
async def project_update(project_id: str, request: Request):
    """Update editable project fields (title, category, accent_color, etc.).

    Accepts a JSON body with any subset of the whitelisted fields. Only fields
    present in the body are changed.
    """
    data = await request.json()
    fields = {k: (v or "") for k, v in data.items() if k in _PROJECT_EDITABLE_FIELDS}
    if not fields:
        return JSONResponse({"status": "error", "message": "No editable fields provided"}, status_code=400)
    # Guard: title must not be blanked.
    if "title" in fields and not str(fields["title"]).strip():
        return JSONResponse({"status": "error", "message": "Title cannot be empty"}, status_code=400)
    set_clause = ", ".join(f"{k}=?" for k in fields)
    params = list(fields.values()) + [project_id]
    db_execute(f"UPDATE projects SET {set_clause} WHERE project_id=?", tuple(params))
    return JSONResponse({"status": "ok", "updated": list(fields.keys())})


def _windows_to_wsl(path: str) -> str:
    r"""`C:\Users\...` or `C:/Users/...` → `/mnt/c/Users/...`.

    Accepting the Windows form matters because that is what copying a folder
    address in Explorer gives you, and asking someone to hand-translate it is
    asking them to get it wrong.
    """
    t = (path or "").strip().strip('"').strip("'")
    if not t:
        return ""
    t = t.replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", t)
    if m:
        return f"/mnt/{m.group(1).lower()}/{m.group(2)}"
    return t


@router.post("/api/project/{project_id}/set-path")
async def project_set_path(project_id: str, request: Request):
    """Point a project at the folder it lives in.

    THIS IS WHY SEVEN ACTIVE PROJECTS HAD NO FOLDER. `external_path` was never
    in the editable-fields whitelist, so it could only ever be set at the moment
    a project was created — and every project made without one stayed that way
    with no control anywhere to fix it. The launcher row then offered to open a
    folder that did not exist.

    Validated rather than trusted, for one specific reason: launching Claude
    Code WRITES a CLAUDE.md into this folder. A stored path that is not a real
    directory would turn that into a write somewhere unintended, so the path
    must resolve to a directory that exists before it is saved.
    """
    data = await request.json()
    raw = str(data.get("path") or "")
    if not raw.strip():
        # Deliberately allowed: clearing the path is how you say "this has no
        # folder", and the launcher row then stops offering to open one.
        db_execute("UPDATE projects SET external_path='' WHERE project_id=?", (project_id,))
        return JSONResponse({"status": "ok", "path": "", "cleared": True})

    path = _windows_to_wsl(raw)
    if not os.path.isabs(path):
        return JSONResponse(
            {"status": "error",
             "message": "That needs to be a full path — one starting at the drive "
                        "or at /, not a folder name on its own."},
            status_code=400)
    if not os.path.exists(path):
        return JSONResponse(
            {"status": "error",
             "message": f"Nothing is at {path}. Check the spelling, or paste the "
                        "address from the folder's title bar."},
            status_code=400)
    if not os.path.isdir(path):
        return JSONResponse(
            {"status": "error",
             "message": f"{path} is a file, not a folder. Point this at the folder "
                        "that holds the work."},
            status_code=400)

    path = os.path.normpath(path).rstrip("/") or "/"
    db_execute("UPDATE projects SET external_path=? WHERE project_id=?", (path, project_id))
    return JSONResponse({"status": "ok", "path": path,
                         "windows_path": _wsl_to_windows(path)})


@router.get("/api/project/{project_id}/launch-state")
async def project_launch_state(project_id: str):
    """What this project can actually be opened with, and why not otherwise.

    Exists so the answer has ONE author. The card renders from it, the launch
    endpoint enforces it, and a test can read it — rather than three places each
    deciding independently what a project is capable of.
    """
    rows = db_query(
        "SELECT project_id, title, COALESCE(external_path,'') AS external_path, "
        "       COALESCE(launcher_type,'') AS launcher_type, COALESCE(launchers,'') AS launchers, "
        "       COALESCE(dashboard_url,'') AS dashboard_url, "
        "       COALESCE(github_url,'') AS github_url "
        "FROM projects WHERE project_id=? LIMIT 1", (project_id,))
    if not rows:
        return JSONResponse({"status": "error", "message": "Project not found"}, status_code=404)
    row = rows[0]
    interop_ok, interop_why = _interop_state()
    targets = {}
    for t in _LAUNCH_NEEDS:
        ok, why = _launch_capability(row, t)
        targets[t] = {"can": ok and interop_ok,
                      "why": "" if ok else why} | ({"why": "interop"} if ok and not interop_ok else {})
    return JSONResponse({
        "status": "ok",
        "project": row.get("title"),
        "path": row.get("external_path") or "",
        "has_path": bool(row.get("external_path")),
        "interop": {"ok": interop_ok, "message": interop_why},
        "offered": _parse_launchers(row),
        "targets": targets,
    })


def _project_tags(project_id: str) -> list[str]:
    raw = db_scalar("SELECT tags FROM projects WHERE project_id=?", (project_id,), default="") or ""
    return [t.strip() for t in raw.split(",") if t.strip()]


@router.post("/api/project/{project_id}/tag-add")
async def project_tag_add(project_id: str, request: Request):
    """Add a tag to a project (projects can carry multiple tags)."""
    data = await request.json()
    tag = (data.get("tag") or "").strip()
    if not tag:
        return JSONResponse({"status": "error", "message": "Tag required"}, status_code=400)
    tags = _project_tags(project_id)
    if tag.lower() not in [t.lower() for t in tags]:
        tags.append(tag)
    db_execute("UPDATE projects SET tags=? WHERE project_id=?", (",".join(tags), project_id))
    return JSONResponse({"status": "ok", "tags": tags})


@router.post("/api/project/{project_id}/tag-remove")
async def project_tag_remove(project_id: str, request: Request):
    """Remove a tag from a project."""
    data = await request.json()
    tag = (data.get("tag") or "").strip()
    tags = [t for t in _project_tags(project_id) if t.lower() != tag.lower()]
    db_execute("UPDATE projects SET tags=? WHERE project_id=?", (",".join(tags), project_id))
    return JSONResponse({"status": "ok", "tags": tags})


@router.post("/api/project/{project_id}/clear-next-step")
async def project_clear_next_step(project_id: str):
    """Clear a project's 'next step' (mark it done)."""
    db_execute("UPDATE projects SET next_step='' WHERE project_id=?", (project_id,))
    return JSONResponse({"status": "ok"})


@router.get("/api/project/categories")
async def project_categories():
    """Distinct categories already in use, for the category picker datalist."""
    rows = db_query(
        "SELECT DISTINCT category FROM projects "
        "WHERE category IS NOT NULL AND category != '' ORDER BY category"
    ) or []
    return JSONResponse({"categories": [r["category"] for r in rows]})


# ── Category management ──────────────────────────────────────────────────────
# Every one of these keeps `projects.category` and `project_categories` in step.
# They are separate writes rather than a foreign key, which means each operation
# has to do both halves or neither — so each returns what it actually changed,
# and none of them silently leaves a project pointing at a category that is gone.


def _count_in_category(name: str) -> int:
    """How many projects sit in a category right now.

    Counted BEFORE the write, because `db_execute` returns None — assigning its
    result to a variable called `moved` produced an endpoint that reported
    `"moved": null` while claiming to say how many projects it had touched.
    """
    return db_scalar(
        "SELECT COUNT(*) FROM projects WHERE TRIM(COALESCE(category,''))=?",
        (name,), default=0) or 0


@router.get("/api/project-category/list")
async def project_category_list():
    """Categories in display order, each with what it holds."""
    _ensure_categories()
    rows = db_query(
        "SELECT c.name, c.display_order, "
        "  (SELECT COUNT(*) FROM projects p "
        "     WHERE TRIM(COALESCE(p.category,'')) = c.name AND p.status='active') AS n_projects "
        "FROM project_categories c ORDER BY c.display_order, c.name COLLATE NOCASE"
    ) or []
    uncat = db_scalar(
        "SELECT COUNT(*) FROM projects WHERE status='active' "
        "AND TRIM(COALESCE(category,'')) = ''", default=0) or 0
    return JSONResponse({"status": "ok", "categories": rows, "uncategorised": uncat})


@router.post("/api/project-category/create")
async def project_category_create(request: Request):
    """Create a category, which may legitimately be empty.

    An empty category has to be creatable, or there is nowhere to move the first
    project TO — which is the whole reason these stopped being SELECT DISTINCT.
    """
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse({"status": "error", "message": "A name is required"}, status_code=400)
    if len(name) > 60:
        return JSONResponse({"status": "error", "message": "That name is too long"}, status_code=400)
    _ensure_categories()
    clash = db_query("SELECT name FROM project_categories WHERE name = ? COLLATE NOCASE", (name,))
    if clash:
        return JSONResponse({"status": "error",
                             "message": f"“{clash[0]['name']}” already exists"}, status_code=409)
    nxt = (db_scalar("SELECT MAX(display_order) FROM project_categories", default=0) or 0) + 10
    db_execute("INSERT INTO project_categories (name, display_order) VALUES (?, ?)", (name, nxt))
    return JSONResponse({"status": "ok", "name": name})


@router.post("/api/project-category/rename")
async def project_category_rename(request: Request):
    """Rename a category AND every project pointing at it, in that order.

    Both halves or neither: renaming the row without moving the projects would
    orphan them under a heading that no longer exists, and they would silently
    reappear as an unmanaged category on the next render.
    """
    data = await request.json()
    old = (data.get("from") or "").strip()
    new = (data.get("to") or "").strip()
    if not old or not new:
        return JSONResponse({"status": "error", "message": "Both names are required"}, status_code=400)
    if old == new:
        return JSONResponse({"status": "ok", "moved": 0, "note": "unchanged"})
    _ensure_categories()
    if db_query("SELECT name FROM project_categories WHERE name = ? COLLATE NOCASE", (new,)):
        return JSONResponse({"status": "error",
                             "message": f"“{new}” already exists — merge into it instead"},
                            status_code=409)
    order = db_scalar("SELECT display_order FROM project_categories WHERE name=?", (old,), default=100)
    db_execute("DELETE FROM project_categories WHERE name=?", (old,))
    db_execute("INSERT OR REPLACE INTO project_categories (name, display_order) VALUES (?, ?)",
               (new, order))
    moved = _count_in_category(old)
    db_execute("UPDATE projects SET category=? WHERE TRIM(COALESCE(category,''))=?", (new, old))
    return JSONResponse({"status": "ok", "from": old, "to": new, "moved": moved})


@router.post("/api/project-category/merge")
async def project_category_merge(request: Request):
    """Move every project from one category into another, then drop the empty one.

    This is the operation the researcher's data most needs: five categories held a single
    project each, which is a taxonomy that sorts nothing.
    """
    data = await request.json()
    src = (data.get("from") or "").strip()
    dst = (data.get("into") or "").strip()
    if not src or not dst:
        return JSONResponse({"status": "error", "message": "Both names are required"}, status_code=400)
    if src == dst:
        return JSONResponse({"status": "error", "message": "Those are the same category"}, status_code=400)
    _ensure_categories()
    if not db_query("SELECT name FROM project_categories WHERE name=?", (dst,)):
        return JSONResponse({"status": "error", "message": f"“{dst}” does not exist"}, status_code=404)
    moved = _count_in_category(src)
    db_execute("UPDATE projects SET category=? WHERE TRIM(COALESCE(category,''))=?", (dst, src))
    db_execute("DELETE FROM project_categories WHERE name=?", (src,))
    return JSONResponse({"status": "ok", "from": src, "into": dst, "moved": moved})


@router.post("/api/project-category/delete")
async def project_category_delete(request: Request):
    """Remove a category. Its projects become uncategorised rather than vanishing.

    Refuses silently-destructive behaviour: a project must never disappear
    because its heading did, so this reports how many it uncategorised and they
    show up under the Uncategorised group immediately.
    """
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse({"status": "error", "message": "A name is required"}, status_code=400)
    _ensure_categories()
    freed = _count_in_category(name)
    db_execute("UPDATE projects SET category='' WHERE TRIM(COALESCE(category,''))=?", (name,))
    db_execute("DELETE FROM project_categories WHERE name=?", (name,))
    return JSONResponse({"status": "ok", "name": name, "uncategorised": freed})


@router.post("/api/project-category/reorder")
async def project_category_reorder(request: Request):
    """Set the order of the category sections.

    Accepts either a full `order` list, or a single `name` plus `direction`
    ("up"/"down") so the page can offer one-click nudges without shipping a
    drag library.
    """
    data = await request.json()
    _ensure_categories()
    names = [r["name"] for r in (db_query(
        "SELECT name FROM project_categories ORDER BY display_order, name COLLATE NOCASE") or [])]

    order = data.get("order")
    if isinstance(order, list) and order:
        names = [n for n in order if n in names] + [n for n in names if n not in order]
    else:
        name = (data.get("name") or "").strip()
        direction = (data.get("direction") or "").strip().lower()
        if name not in names or direction not in ("up", "down"):
            return JSONResponse({"status": "error",
                                 "message": "Need an order list, or a name plus up/down"},
                                status_code=400)
        i = names.index(name)
        j = i - 1 if direction == "up" else i + 1
        if 0 <= j < len(names):
            names[i], names[j] = names[j], names[i]

    for i, n in enumerate(names):
        db_execute("UPDATE project_categories SET display_order=? WHERE name=?", ((i + 1) * 10, n))
    return JSONResponse({"status": "ok", "order": names})


@router.post("/api/project/{project_id}/move-category")
async def project_move_category(project_id: str, request: Request):
    """Move one project to another category — the control that did not exist.

    `/api/project/update` has always accepted `category`; nothing on any surface
    exposed it, so the only way to re-file a project was to edit the database.
    An unknown category is created rather than rejected: re-filing and inventing
    a home for something are the same gesture in practice.
    """
    data = await request.json()
    target = (data.get("category") or "").strip()
    if not db_query("SELECT project_id FROM projects WHERE project_id=?", (project_id,)):
        return JSONResponse({"status": "error", "message": "Project not found"}, status_code=404)
    _ensure_categories()
    if target and not db_query(
            "SELECT name FROM project_categories WHERE name=? COLLATE NOCASE", (target,)):
        nxt = (db_scalar("SELECT MAX(display_order) FROM project_categories", default=0) or 0) + 10
        db_execute("INSERT OR IGNORE INTO project_categories (name, display_order) VALUES (?, ?)",
                   (target, nxt))
    db_execute("UPDATE projects SET category=? WHERE project_id=?", (target, project_id))
    return JSONResponse({"status": "ok", "project_id": project_id,
                         "category": target or None})


@router.post("/api/project/scan/{project_id}")
async def project_scan(project_id: str):
    """Scan a single project folder for activity and refresh its CLAUDE.md."""
    try:
        import sys as _sys
        rc = os.environ.get("METIS_RC_ROOT", "")
        if rc:
            mcp_src = str(Path(rc) / "system" / "mcp-server" / "src")
            if mcp_src not in _sys.path:
                _sys.path.insert(0, mcp_src)
        from metis_mcp.tools.project_tracker import scan_project_folder
        result = await scan_project_folder(project_id)
        return JSONResponse({"ok": True, "summary": result[0].text if result else ""})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/project/scan-all")
async def project_scan_all():
    """Scan all active project folders. Called by the dashboard Update button."""
    try:
        import sys as _sys
        rc = os.environ.get("METIS_RC_ROOT", "")
        if rc:
            mcp_src = str(Path(rc) / "system" / "mcp-server" / "src")
            if mcp_src not in _sys.path:
                _sys.path.insert(0, mcp_src)
        from metis_mcp.tools.project_tracker import update_all_projects
        result = await update_all_projects()
        return JSONResponse({"ok": True, "summary": result[0].text if result else ""})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/project/create-full")
async def project_create_full(request: Request):
    """Create a project with full integration: DB, CLAUDE.md, Claude Desktop."""
    data = await request.json()
    title = (data.get("title") or data.get("name") or "").strip()
    if not title:
        return JSONResponse({"status": "error", "message": "Title required"}, status_code=400)
    try:
        import sys as _sys
        rc = os.environ.get("METIS_RC_ROOT", "")
        if rc:
            mcp_src = str(Path(rc) / "system" / "mcp-server" / "src")
            if mcp_src not in _sys.path:
                _sys.path.insert(0, mcp_src)
        from metis_mcp.tools.project_tracker import create_project_full
        result = await create_project_full(
            title=title,
            folder_path=data.get("folder", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            scan_type=data.get("scan_type", "names"),
            link_claude_desktop_auto=data.get("link_claude_desktop", True),
        )
        return JSONResponse({"status": "ok", "message": result[0].text if result else ""})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/api/project/session-end")
async def project_session_end(request: Request):
    """Called by the Claude Code stop hook. Detects which project was active from cwd."""
    data = await request.json()
    cwd = (data.get("cwd") or "").strip().rstrip("/\\")
    ts = data.get("ts", datetime.datetime.now().isoformat())

    if not cwd:
        return JSONResponse({"ok": False, "reason": "no cwd"})

    # Normalise: convert WSL /mnt/c/... → C:/... for comparison
    def normalise(p: str) -> str:
        import re as _re
        m = _re.match(r"^/mnt/([a-zA-Z])/(.*)", p)
        if m:
            return (m.group(1).upper() + ":/" + m.group(2)).rstrip("/\\")
        return p.rstrip("/\\")

    cwd_norm = normalise(cwd)

    rows = db_query(
        "SELECT project_id, title, external_path FROM projects "
        "WHERE status='active' AND external_path IS NOT NULL AND external_path != ''"
    )
    matched_id = None
    for row in rows:
        ep = normalise(row["external_path"])
        if cwd_norm == ep or cwd_norm.startswith(ep + "/") or cwd_norm.startswith(ep + "\\"):
            matched_id = row["project_id"]
            break

    if not matched_id:
        return JSONResponse({"ok": True, "project_id": None, "reason": "no project matched"})

    db_execute(
        "UPDATE projects SET last_session_at = ? WHERE project_id = ?",
        (ts, matched_id),
    )
    return JSONResponse({"ok": True, "project_id": matched_id})


@router.post("/api/project/untrack/{project_id}")
async def project_untrack(project_id: str):
    """Hide a project from the Work tab without deleting it."""
    db_execute("UPDATE projects SET tracked = 0 WHERE project_id = ?", (project_id,))
    return JSONResponse({"status": "ok"})


@router.post("/api/project/track/{project_id}")
async def project_track(project_id: str):
    """Restore a previously untracked project."""
    db_execute("UPDATE projects SET tracked = 1 WHERE project_id = ?", (project_id,))
    return JSONResponse({"status": "ok"})


@router.get("/api/partial/work/hidden-projects", response_class=HTMLResponse)
async def hidden_projects_partial(request: Request):
    """Small chip showing count of hidden projects with a reveal option."""
    hidden = db_query(
        "SELECT project_id as id, title FROM projects WHERE tracked = 0 ORDER BY title"
    )
    if not hidden:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request, "partials/work_hidden_projects.html", {"hidden": hidden}
    )


@router.post("/api/project/reorder")
async def project_reorder(request: Request):
    """Save project display order after drag-and-drop."""
    data = await request.json()
    order = data.get("order", [])
    for i, pid in enumerate(order):
        db_execute(
            "UPDATE projects SET display_order = ? WHERE project_id = ?",
            (i + 1, pid),
        )
    return JSONResponse({"status": "ok", "saved": len(order)})


@router.get("/api/partial/work/project-tasks/{project_id}", response_class=HTMLResponse)
async def project_tasks_partial(request: Request, project_id: str):
    all_open = db_query(
        # `due_date` comes along so the row can carry the date control that the
        # flat task list has had all along. It was the only place a date could be
        # set, and it is the list nobody opens — hence 2 dated tasks out of 92.
        # Cancelled is not a kind of open. This list named 'deleted' — a status
        # the store has never held — while letting 'cancelled' through, so 34
        # abandoned tasks were drawn as live work across nine project cards,
        # eleven of them on one. The ORDER BY here has always floated blocked
        # work to the top, which is the right instinct and the other half of
        # the same definition; both now come from one place.
        "SELECT task_id, title, status, category, updated_at, starred, "
        "       COALESCE(due_date,'') AS due_date FROM tasks "
        f"WHERE project_id=? AND {live_task_sql()} "
        "ORDER BY starred DESC, COALESCE(display_order,999), "
        "CASE status WHEN 'blocked' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END, created_at DESC",
        params=(project_id,),
    ) or []
    total_open = len(all_open)
    tasks = all_open[:5]
    done_count = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE project_id=? AND status='done'",
        params=(project_id,),
        default=0,
    )
    return templates.TemplateResponse(
        request,
        "partials/work_project_tasks.html",
        {
            "tasks": tasks,
            "total_open": total_open,
            "done_count": done_count,
            "project_id": project_id,
        },
    )


@router.get("/api/partial/work/project-detail/{project_id}", response_class=HTMLResponse)
async def project_detail_panel(request: Request, project_id: str):
    rows = db_query(
        "SELECT project_id as id, title, description, domain, priority, next_step, status, "
        "created_at, external_path, github_url, project_type, context_doc, "
        "history_log, prompt_memory, last_session_at, "
        "tags, started_at, completed_at, image_url, accent_color, category "
        "FROM projects WHERE project_id=? LIMIT 1",
        (project_id,),
    )
    if not rows:
        return HTMLResponse("<p>Project not found.</p>", status_code=404)
    p = rows[0]

    open_tasks = db_query(
        "SELECT task_id, title, status, category, updated_at FROM tasks "
        f"WHERE project_id=? AND {live_task_sql()} "
        "ORDER BY COALESCE(display_order,999), "
        "CASE status WHEN 'blocked' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END, created_at DESC",
        (project_id,),
    ) or []

    done_tasks = db_query(
        "SELECT task_id, title, updated_at FROM tasks "
        "WHERE project_id=? AND status='done' "
        "ORDER BY updated_at DESC",
        (project_id,),
    ) or []

    linked_notes = db_query(
        "SELECT note_id, content, title, created_at FROM personal_notes "
        "WHERE project_id=? ORDER BY created_at DESC LIMIT 20",
        (project_id,),
    ) or []

    # Last activity
    last_activity = None
    try:
        act = db_query(
            "SELECT MAX(updated_at) as ts FROM tasks WHERE project_id=? AND updated_at IS NOT NULL",
            (project_id,),
        )
        if act and act[0].get("ts"):
            last_activity = act[0]["ts"]
        ar = db_query(
            "SELECT MAX(created_at) as ts FROM agent_runs WHERE input_path LIKE ?",
            (f"%{project_id}%",),
        )
        if ar and ar[0].get("ts"):
            if not last_activity or ar[0]["ts"] > last_activity:
                last_activity = ar[0]["ts"]
    except Exception:
        pass

    # Parse history_log
    history_entries = []
    try:
        import json as _json
        history_entries = _json.loads(p.get("history_log") or "[]")[-20:]
    except Exception:
        pass

    # Parse tags into list
    tags_raw = p.get("tags") or ""
    tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

    return templates.TemplateResponse(
        request,
        "partials/work_project_detail.html",
        {
            "p": p,
            "open_tasks": open_tasks,
            "open_count": len(open_tasks),
            "done_tasks": done_tasks,
            "linked_notes": linked_notes,
            "last_activity": last_activity,
            "history_entries": list(reversed(history_entries)),
            "tags_list": tags_list,
        },
    )


# ---------------------------------------------------------------------------
# Task actions — mark done, delete
# ---------------------------------------------------------------------------


def _next_due(due_date: str, recurrence: str) -> str:
    """Advance a YYYY-MM-DD date by one recurrence period. Empty if not derivable."""
    try:
        d = datetime.date.fromisoformat((due_date or "")[:10])
    except Exception:
        d = datetime.date.today()
    if recurrence == "daily":
        d += datetime.timedelta(days=1)
    elif recurrence == "weekly":
        d += datetime.timedelta(weeks=1)
    elif recurrence == "monthly":
        m = d.month + 1
        y = d.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
        dim = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
        d = datetime.date(y, m, min(d.day, dim))
    elif recurrence == "yearly":
        d = d.replace(year=d.year + 1)
    else:
        return ""
    return d.isoformat()


@router.post("/api/task/{task_id}/done")
async def task_mark_done(task_id: str):
    try:
        now = datetime.datetime.now().isoformat()
        db_execute(
            "UPDATE tasks SET status = 'done', updated_at = ? WHERE task_id = ?",
            (now, task_id),
        )
        # If this was a recurring task, spawn the next occurrence so the series continues.
        spawned = None
        try:
            rows = db_query(
                "SELECT title, project_id, owner, notes, due_date, "
                "COALESCE(recurrence,'') AS recurrence FROM tasks WHERE task_id = ?",
                (task_id,),
            )
            if rows:
                r = rows[0]
                rec = (r.get("recurrence") or "").strip().lower()
                if rec in ("daily", "weekly", "monthly", "yearly"):
                    new_due = _next_due(r.get("due_date", ""), rec)
                    import re as _re
                    slug = _re.sub(r"-+", "-", _re.sub(r"[^\w\s-]", "", (r["title"] or "").lower()).replace(" ", "-")).strip("-")[:60]
                    new_id = f"{r['project_id']}-{slug}-{new_due or now[:10]}"
                    db_execute(
                        "INSERT OR REPLACE INTO tasks "
                        "(task_id, title, project_id, owner, status, notes, due_date, recurrence, parent_task_id, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)",
                        (new_id, r["title"], r["project_id"], r.get("owner") or "Metis",
                         r.get("notes") or "", new_due, rec, task_id, now, now),
                    )
                    spawned = new_id
        except Exception:
            pass  # recurrence is best-effort; never block the completion
        return JSONResponse({"status": "ok", "task_id": task_id, "spawned": spawned})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/api/task/{task_id}/delete")
async def task_delete(task_id: str):
    # `int`, until 2026-09-01. Task ids are strings —
    # "71e4cde6-clean-up-stray-placeholders-and-fix-cross-references" — so
    # FastAPI rejected every real one with a 422 before the handler ran, and
    # the three callers (two in app.js, one in the project detail panel) all
    # ignore the status and redraw regardless. Deleting a task therefore did
    # nothing, silently, everywhere, and the row reappeared on the next load.
    # Every sibling route in this file was already `str`; this one was not.
    try:
        db_execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        return JSONResponse({"status": "ok", "task_id": task_id})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Task create (quick-add per project)
# ---------------------------------------------------------------------------


@router.post("/api/task/quick", response_class=HTMLResponse)
async def task_quick_add(request: Request, bare: int = 0):
    """Create a task due today and hand back the refreshed Due-Today strip.

    Reported 2026-09-01: "its not clear to me how to add projects or tasks ... nor
    how to easily add or delete tasks/things to do."

    Everything he named already existed — on Work. `+ Project`, `+ add task` per
    project card, a delete on every task row. What did not exist anywhere was a
    way to do any of it from TODAY, which is the surface he starts on: its only
    answer was the sentence "Star a task in Work, or give one a date", an
    instruction to go somewhere else rather than a control.

    This is separate from `/api/task/create` on purpose. That one is the
    per-project quick-add and answers with the PROJECT's task list, which is the
    wrong fragment for Today and needs a project_id Today does not have. A task
    added here belongs to no project and is due today, so it appears in the strip
    it was typed into — the shortest possible loop between wanting a thing
    written down and seeing it written down.
    """
    form = await request.form()
    title = (form.get("title") or "").strip()
    if title:
        db_execute(
            "INSERT INTO tasks (task_id, project_id, title, status, category, due_date, "
            "priority, created_at, updated_at) VALUES (?, '', ?, 'open', 'general', ?, "
            "'medium', ?, ?)",
            (uuid.uuid4().hex[:12], title, str(datetime.date.today()),
             datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()),
        )
    return await work_due_today(request, bare=bare)


@router.post("/api/task/{task_id}/drop", response_class=HTMLResponse)
async def task_drop(request: Request, task_id: str, bare: int = 0):
    """Delete a task and redraw the Due-Today strip.

    `/api/task/{id}/delete` already does the deleting, but it answers with JSON
    and is typed `int` while task_ids are 12-char hex — so it could not be
    called from a list that has to redraw itself, and would 422 on a real id.
    """
    db_execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    return await work_due_today(request, bare=bare)


@router.post("/api/task/create", response_class=HTMLResponse)
async def task_create(request: Request):
    data = await request.json()
    project_id = data.get("project_id", "")
    title = (data.get("title") or "").strip()
    category = (data.get("category") or "general").strip() or "general"
    # Accept a due date and a priority if the caller sends them.
    #
    # Neither was captured anywhere in the dashboard, so ZERO of 105 tasks had a
    # due date and every deadline-shaped feature was decorative: "due today" was
    # structurally empty, the Planner week grid had nothing to place, and the
    # overdue calculation could never fire. The MCP `create_task` has always
    # accepted due_date; only the dashboard dropped it. Optional, so nothing
    # changes for a caller that does not send one.
    due_date = (data.get("due_date") or "").strip()
    priority = (data.get("priority") or "medium").strip() or "medium"
    if not title:
        return JSONResponse({"status": "error", "message": "Title required"}, status_code=400)
    task_id = uuid.uuid4().hex[:12]
    now = datetime.datetime.now().isoformat()
    db_execute(
        "INSERT INTO tasks (task_id, project_id, title, status, category, due_date, priority, "
        "created_at, updated_at) VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?)",
        (task_id, project_id, title, category, due_date or None, priority, now, now),
    )
    tasks = db_query(
        # Same columns as the other render of this partial — a template fed by
        # two queries needs both to supply what it reads, or the date control
        # silently shows "no date" on whichever path forgot.
        "SELECT task_id, title, status, category, starred, "
        "       COALESCE(due_date,'') AS due_date FROM tasks "
        f"WHERE project_id=? AND {live_task_sql()} "
        "ORDER BY category, created_at LIMIT 15",
        params=(project_id,),
    )
    done_count = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE project_id=? AND status='done'",
        params=(project_id,),
        default=0,
    )
    # `total_open` is required by the template and was never passed here, so
    # adding a task from the dashboard ALWAYS returned a 500: the task saved, then
    # the response blew up rendering it. The other renderer of this template (the
    # project detail panel) passes it; this one was written without it and nobody
    # noticed, because the task does appear — on the next page load.
    total_open = db_scalar(
        f"SELECT COUNT(*) FROM tasks WHERE project_id=? AND {live_task_sql()}",
        params=(project_id,),
        default=0,
    )
    return templates.TemplateResponse(
        request,
        "partials/work_project_tasks.html",
        {"tasks": tasks, "done_count": done_count, "project_id": project_id,
         "total_open": total_open},
    )


# ---------------------------------------------------------------------------
# Project notes
# ---------------------------------------------------------------------------

# Ensure notes column exists on startup (safe to run repeatedly)
try:
    db_execute("ALTER TABLE projects ADD COLUMN notes TEXT")
except Exception:
    pass


@router.get("/api/project/{project_id}/notes", response_class=HTMLResponse)
async def get_project_notes(request: Request, project_id: str):
    notes = db_scalar(
        "SELECT notes FROM projects WHERE project_id=?", (project_id,), default=""
    ) or ""
    return templates.TemplateResponse(
        request,
        "partials/work_project_notes.html",
        {"project_id": project_id, "notes": notes},
    )


@router.post("/api/project/{project_id}/notes")
async def save_project_notes(project_id: str, request: Request):
    data = await request.json()
    notes = data.get("notes", "")
    db_execute("UPDATE projects SET notes=? WHERE project_id=?", (notes, project_id))
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Project context (context_doc + history_log + prompt_memory)
# ---------------------------------------------------------------------------

for _col, _default in [
    ("project_type TEXT DEFAULT 'research'", None),
    ("context_doc TEXT DEFAULT ''", None),
    ("history_log TEXT DEFAULT '[]'", None),
    ("prompt_memory TEXT DEFAULT ''", None),
    ("last_session_at TEXT", None),
    ("detection_source TEXT DEFAULT 'manual'", None),
]:
    try:
        db_execute(f"ALTER TABLE projects ADD COLUMN {_col}")
    except Exception:
        pass


@router.get("/api/project/{project_id}/context")
async def get_project_context(project_id: str):
    rows = db_query(
        "SELECT project_id, title, description, domain, next_step, project_type, "
        "context_doc, history_log, prompt_memory, last_session_at "
        "FROM projects WHERE project_id=? LIMIT 1",
        (project_id,),
    )
    if not rows:
        return JSONResponse({"error": "not found"}, status_code=404)
    p = rows[0]
    history = []
    try:
        history = json.loads(p.get("history_log") or "[]")
    except Exception:
        pass
    return JSONResponse({
        "project_id": project_id,
        "title": p.get("title") or "",
        "description": p.get("description") or "",
        "domain": p.get("domain") or "",
        "next_step": p.get("next_step") or "",
        "project_type": p.get("project_type") or "research",
        "context_doc": p.get("context_doc") or "",
        "prompt_memory": p.get("prompt_memory") or "",
        "history": history[-10:],
        "last_session_at": p.get("last_session_at"),
    })


@router.post("/api/project/{project_id}/context")
async def save_project_context(project_id: str, request: Request):
    data = await request.json()
    context_doc = data.get("context_doc", "")
    db_execute(
        "UPDATE projects SET context_doc=? WHERE project_id=?",
        (context_doc, project_id),
    )
    return JSONResponse({"status": "ok"})


@router.post("/api/project/{project_id}/history")
async def append_project_history(project_id: str, request: Request):
    data = await request.json()
    summary = (data.get("summary") or "").strip()
    if not summary:
        return JSONResponse({"status": "error", "message": "summary required"}, status_code=400)
    now = datetime.datetime.now().isoformat()
    raw = db_scalar(
        "SELECT history_log FROM projects WHERE project_id=?",
        (project_id,),
        default="[]",
    ) or "[]"
    try:
        history = json.loads(raw)
    except Exception:
        history = []
    history.append({
        "date": now[:10],
        "ts": now,
        "summary": summary,
        "author": data.get("author", "metis"),
    })
    history = history[-50:]
    recent = history[-5:]
    pm_lines = [f"- {e['date']}: {e['summary']}" for e in reversed(recent)]
    prompt_memory = "Recent session history:\n" + "\n".join(pm_lines)
    db_execute(
        "UPDATE projects SET history_log=?, prompt_memory=?, last_session_at=? WHERE project_id=?",
        (json.dumps(history), prompt_memory, now, project_id),
    )
    return JSONResponse({"status": "ok", "entries": len(history)})


# ---------------------------------------------------------------------------
# Project metadata — tags, dates, image, next-step clear
# ---------------------------------------------------------------------------


@router.post("/api/project/{project_id}/meta")
async def save_project_meta(project_id: str, request: Request):
    """Update tags, started_at, completed_at, image_url, description, next_step."""
    data = await request.json()
    fields = {}
    for col in ("tags", "started_at", "completed_at", "image_url", "description", "next_step", "title"):
        if col in data:
            fields[col] = data[col]
    if not fields:
        return JSONResponse({"status": "noop"})
    set_clause = ", ".join(f"{k}=?" for k in fields)
    db_execute(
        f"UPDATE projects SET {set_clause} WHERE project_id=?",
        tuple(fields.values()) + (project_id,),
    )
    return JSONResponse({"status": "ok"})


@router.post("/api/project/{project_id}/next-step/clear")
async def clear_next_step(project_id: str):
    """Mark the 'Next step' note as done — clear it and log to history."""
    row = db_query(
        "SELECT next_step, history_log FROM projects WHERE project_id=? LIMIT 1",
        (project_id,),
    )
    if not row:
        return JSONResponse({"status": "not found"}, status_code=404)
    next_step = (row[0].get("next_step") or "").strip()
    now = datetime.datetime.now().isoformat()
    if next_step:
        raw = row[0].get("history_log") or "[]"
        try:
            history = json.loads(raw)
        except Exception:
            history = []
        history.append({"date": now[:10], "ts": now, "summary": f"[Done] {next_step}", "author": "user"})
        db_execute(
            "UPDATE projects SET next_step='', history_log=? WHERE project_id=?",
            (json.dumps(history[-50:]), project_id),
        )
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Task reordering
# ---------------------------------------------------------------------------


@router.post("/api/project/{project_id}/tasks/reorder")
async def reorder_project_tasks(project_id: str, request: Request):
    """Save task display order. Body: {order: [task_id, ...]}"""
    data = await request.json()
    for i, tid in enumerate(data.get("order", [])):
        db_execute(
            "UPDATE tasks SET display_order=? WHERE task_id=?",
            (i + 1, tid),
        )
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Task status update (status change, not just done/delete)
# ---------------------------------------------------------------------------


@router.post("/api/task/{task_id}/star")
async def task_toggle_star(task_id: str):
    current = db_scalar("SELECT starred FROM tasks WHERE task_id=?", (task_id,), default=0)
    new_val = 0 if current else 1
    db_execute("UPDATE tasks SET starred=? WHERE task_id=?", (new_val, task_id))
    return JSONResponse({"status": "ok", "starred": new_val})


@router.post("/api/task/{task_id}/status")
async def task_set_status(task_id: str, request: Request):
    data = await request.json()
    status = data.get("status", "open")
    now = datetime.datetime.now().isoformat()
    db_execute(
        "UPDATE tasks SET status=?, updated_at=? WHERE task_id=?",
        (status, now, task_id),
    )
    return JSONResponse({"status": "ok"})


@router.post("/api/task/{task_id}/rename")
async def task_rename(task_id: str, request: Request):
    data = await request.json()
    title = (data.get("title") or "").strip()
    if not title:
        return JSONResponse({"status": "error"}, status_code=400)
    db_execute("UPDATE tasks SET title=? WHERE task_id=?", (title, task_id))
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Project-linked notes (personal_notes with project_id set)
# ---------------------------------------------------------------------------


@router.get("/api/project/{project_id}/linked-notes", response_class=HTMLResponse)
async def get_project_linked_notes(request: Request, project_id: str):
    notes = db_query(
        "SELECT note_id, content, title, created_at FROM personal_notes "
        "WHERE project_id=? ORDER BY created_at DESC LIMIT 30",
        (project_id,),
    ) or []
    return templates.TemplateResponse(
        request,
        "partials/work_project_linked_notes.html",
        {"notes": notes, "project_id": project_id},
    )


@router.post("/api/project/{project_id}/linked-notes")
async def add_project_linked_note(project_id: str, request: Request):
    data = await request.json()
    content = (data.get("content") or "").strip()
    if not content:
        return JSONResponse({"status": "error", "message": "content required"}, status_code=400)
    import uuid as _uuid
    note_id = _uuid.uuid4().hex
    now = datetime.datetime.now().isoformat()
    db_execute(
        "INSERT INTO personal_notes (note_id, content, title, tags, created_at, updated_at, project_id) "
        "VALUES (?,?,?,?,?,?,?)",
        (note_id, content, data.get("title", ""), data.get("tags", ""), now, now, project_id),
    )
    return JSONResponse({"status": "ok", "note_id": note_id})


@router.delete("/api/note/{note_id}")
async def delete_note(note_id: str):
    db_execute("DELETE FROM personal_notes WHERE note_id=?", (note_id,))
    return JSONResponse({"status": "ok"})


@router.get("/api/projects/detect")
async def detect_projects():
    """Scan parent folder of METIS_RC_ROOT for unregistered git repos and article folders."""
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if not rc_root:
        return JSONResponse({"detected": [], "message": "METIS_RC_ROOT not set"})

    existing_ids = {
        r["project_id"]
        for r in (db_query("SELECT project_id FROM projects") or [])
    }
    existing_paths = {
        (r.get("external_path") or "").rstrip("/\\")
        for r in (db_query(
            "SELECT external_path FROM projects WHERE external_path IS NOT NULL AND external_path != ''"
        ) or [])
    }

    scan_root = Path(rc_root).parent
    detected = []
    checked: set = set()

    if scan_root.exists():
        try:
            for item in scan_root.iterdir():
                if item.name.startswith(".") or not item.is_dir():
                    continue
                path_str = str(item)
                if path_str in checked or path_str in existing_paths:
                    continue
                checked.add(path_str)
                has_git = (item / ".git").exists()
                doc_files = (
                    list(item.glob("*.md"))
                    + list(item.glob("*.Rmd"))
                    + list(item.glob("*.qmd"))
                )
                slug = re.sub(r"[^a-z0-9]+", "-", item.name.lower()).strip("-")[:40]
                if slug in existing_ids:
                    continue
                if has_git or doc_files:
                    detected.append({
                        "folder": item.name,
                        "path": path_str,
                        "suggested_id": slug,
                        "has_git": has_git,
                        "doc_count": len(doc_files),
                    })
        except (PermissionError, OSError):
            pass

    return JSONResponse({"detected": detected[:20]})


# ---------------------------------------------------------------------------
# Planner — set status on the oldest open task (retire / pause / schedule)
# ---------------------------------------------------------------------------

_TASK_STATUS_MAP = {
    "retire":   ("cancelled", None),
    "pause":    ("paused", None),
    "schedule": ("open", (datetime.date.today() + datetime.timedelta(days=1)).isoformat()),
}


@router.post("/api/task/oldest-open/{action}")
async def task_oldest_open(action: str):
    if action not in _TASK_STATUS_MAP:
        return JSONResponse(
            {"status": "error", "message": f"Unknown action: {action}"},
            status_code=400,
        )
    target_status, due = _TASK_STATUS_MAP[action]
    rows = db_query(
        f"SELECT task_id FROM tasks WHERE {live_task_sql()} "
        "ORDER BY created_at LIMIT 1"
    ) or []
    if not rows:
        return JSONResponse(
            {"status": "empty", "message": "No open task to update."}
        )
    task_id = rows[0]["task_id"]
    try:
        if due:
            db_execute(
                "UPDATE tasks SET status=?, due_date=?, updated_at=? WHERE task_id=?",
                (target_status, due, datetime.datetime.now().isoformat(), task_id),
            )
        else:
            db_execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE task_id=?",
                (target_status, datetime.datetime.now().isoformat(), task_id),
            )
        return JSONResponse({"status": "ok", "task_id": task_id, "new_status": target_status})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Focus project (used by launchPrompt() for context)
# ---------------------------------------------------------------------------


@router.get("/api/project/focus")
async def project_focus():
    try:
        rows = db_query(
            "SELECT project_id, title, external_path, launcher_type "
            "FROM projects WHERE status='active' "
            "ORDER BY CASE priority "
            "  WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
            "created_at DESC LIMIT 1"
        )
        if rows:
            return JSONResponse(dict(rows[0]))
    except Exception:
        pass
    return JSONResponse({"project_id": None, "title": None})


# ---------------------------------------------------------------------------
# Project launcher — open external app with project folder
# ---------------------------------------------------------------------------


def _wsl_to_windows(path: str) -> str:
    """Convert a WSL-visible path like /mnt/c/... to C:\\... for Windows apps."""
    if not path:
        return path
    if path.startswith("/mnt/"):
        # /mnt/c/Users/... → C:/Users/...
        parts = path[5:].split("/", 1)
        drive = parts[0].upper()
        rest = parts[1] if len(parts) > 1 else ""
        return f"{drive}:/{rest}"
    return path


def _windows_to_cmd(path: str) -> str:
    """Windows apps prefer backslashes in some contexts; most accept forward slashes too."""
    return path.replace("/", "\\") if path else path


def _run_windows_cmd(args: list, cwd: str = None):
    """Run a Windows command via cmd.exe from WSL or native Windows.
    Uses full path to cmd.exe when in WSL to avoid PATH issues."""
    cmd_exe = "/mnt/c/Windows/System32/cmd.exe"
    if not os.path.exists(cmd_exe):
        cmd_exe = "cmd.exe"
    # cmd.exe /c START "title" <command...>
    subprocess.Popen(
        [cmd_exe, "/c", *args],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _ensure_project_claude_md(project_id: str, external_path: str, project_row: dict):
    """Write/refresh CLAUDE.md in the project folder with live task context.

    This lets Claude Code immediately understand the project and allows it to
    call Metis MCP tools to push updates back to the platform.
    """
    if not external_path:
        return
    # Convert Windows path to WSL path for file writes
    wsl_path = external_path
    if external_path and ":" in external_path and not external_path.startswith("/mnt/"):
        drive = external_path[0].lower()
        rest = external_path[2:].replace("\\", "/")
        wsl_path = f"/mnt/{drive}{rest}"
    folder = Path(wsl_path)
    if not folder.is_dir():
        return
    claude_md = folder / "CLAUDE.md"

    # Fetch open tasks for this project
    try:
        tasks = db_query(
            "SELECT title, status, category FROM tasks "
            f"WHERE project_id=? AND {live_task_sql()} "
            "ORDER BY category, created_at LIMIT 20",
            params=(project_id,),
        ) or []
    except Exception:
        tasks = []

    title = project_row.get("title", project_id)
    description = project_row.get("description") or ""
    next_step = project_row.get("next_step") or ""
    domain = project_row.get("domain") or ""

    task_lines = "\n".join(
        f"- [{t['status'].upper()}] {t['title']}" for t in tasks
    ) or "_No open tasks._"

    content = (
        f"# {title}\n\n"
        f"**Domain:** {domain}\n"
        f"**Project ID:** `{project_id}`\n\n"
        + (f"## Description\n{description}\n\n" if description else "")
        + (f"## Next step\n{next_step}\n\n" if next_step else "")
        + f"## Open tasks\n{task_lines}\n\n"
        f"## Metis integration\n"
        f"The Metis MCP server (`metis-rc`) is available. Use its tools to:\n"
        f"- `update_task` — mark tasks done or update status\n"
        f"- `add_task` — add new tasks to this project (project_id: `{project_id}`)\n"
        f"- `update_project` — update next_step or description\n"
        f"\nChanges made via these tools appear immediately in the Metis dashboard.\n"
    )

    try:
        claude_md.write_text(content, encoding="utf-8")
    except Exception:
        pass  # Non-fatal: if we can't write, the launch still proceeds


@router.post("/api/project/launch")
async def project_launch(
    project_id: str = Form(""),
    target: str = Form(...),
    prompt: str = Form(""),
):
    """Launch an external application scoped to a project folder.

    Targets: rstudio | vscode | explorer | claude_desktop | claude_code
    Special project_id "rc-root" uses METIS_RC_ROOT as the working dir.
    Optional `prompt` is appended to Claude Code invocations as initial input.
    """
    external_path = None
    project_title = None

    if project_id in ("rc-root", "", None):
        # Open at the Metis RC root
        rc_root = os.environ.get("METIS_RC_ROOT", "")
        if not rc_root:
            return JSONResponse(
                {"status": "error", "message": "METIS_RC_ROOT not set"},
                status_code=400,
            )
        external_path = rc_root
        project_title = "Research Cortex"
        p = {"external_path": rc_root, "launcher_path": None}
    else:
        try:
            rows = db_query(
                "SELECT project_id, title, external_path, launcher_type, launcher_path, "
                "       COALESCE(dashboard_url,'') AS dashboard_url, "
                "       COALESCE(github_url,'')    AS github_url "
                "FROM projects WHERE project_id = ? LIMIT 1",
                (project_id,),
            )
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"DB error: {e}"}, status_code=500)

        if not rows:
            return JSONResponse({"status": "error", "message": "Project not found"}, status_code=404)

        p = rows[0]
        external_path = p.get("external_path")
        project_title = p.get("title")

        # ASK BEFORE TRYING. The old version rejected every target whenever the
        # folder was missing — including Chat and Cowork, which do not use one —
        # and its message told the reader to "seed it in the DB first", which is
        # not something they can act on. Now the requirement that is actually
        # unmet is the one reported, in words, with the thing to do next.
        ok, why = _launch_capability(p, target)
        if not ok:
            return JSONResponse(
                {"status": "error", "reason": why,
                 "message": f"Can't open “{project_title or project_id}” that way — {why}."
                            + (" Use “Where does this live?” on the card to point it at a folder."
                               if why == _LAUNCH_BLOCKED_BECAUSE["path"] else "")},
                status_code=400,
            )

    win_path = _wsl_to_windows(external_path)

    # Every target below ultimately starts a Windows application. When the
    # handler for Windows binaries is not registered, all of them fail
    # identically at exec time — so check once and say so plainly, rather than
    # letting eight buttons each surface the same errno.
    interop_ok, interop_why = _interop_state()
    if not interop_ok:
        return JSONResponse(
            {"status": "error", "reason": "interop", "message": interop_why},
            status_code=503,
        )

    try:
        if target == "rstudio":
            rproj_path = p.get("launcher_path") or ""
            if not rproj_path and external_path.startswith("/mnt/"):
                if os.path.isdir(external_path):
                    for f in os.listdir(external_path):
                        if f.endswith(".Rproj"):
                            rproj_path = f"{external_path}/{f}"
                            break
            if rproj_path:
                _run_windows_cmd(["start", "", _wsl_to_windows(rproj_path)])
            else:
                _run_windows_cmd(["start", "", win_path])

        elif target == "vscode":
            _run_windows_cmd(["code", win_path])

        elif target == "explorer":
            _run_windows_cmd(["explorer", _windows_to_cmd(win_path)])

        elif target in ("claude_desktop", "claude_chat"):
            # Open Claude Desktop chat interface.
            # claude:// protocol handler opens the app; no path param needed for chat.
            _run_windows_cmd(["start", "", "claude://"])

        elif target == "claude_cowork":
            # Open Claude Desktop in cowork mode.
            # Copies project path to clipboard so user can paste it into a new cowork space.
            if win_path:
                try:
                    import subprocess as _sp
                    _sp.run(
                        ["powershell.exe", "-NoProfile", "-Command",
                         f"Set-Clipboard -Value '{win_path}'"],
                        check=False,
                    )
                except Exception:
                    pass
            _run_windows_cmd(["start", "", "claude://"])

        elif target == "claude_code":
            # Ensure CLAUDE.md exists in the project folder with live task context.
            _ensure_project_claude_md(project_id, external_path, p)
            # Launch Windows Terminal via WSL so `claude` CLI (installed in WSL)
            # is found on PATH. bash -ic loads ~/.bashrc which sets up PATH.
            claude_cmd = "claude"
            if prompt:
                safe_prompt = prompt.replace("'", "'\\''")
                claude_cmd = f"claude '{safe_prompt}'"
            args = [
                "start", "wt.exe", "-w", "0", "new-tab", "-d", win_path,
                "wsl.exe", "--", "bash", "-ic", claude_cmd,
            ]
            _run_windows_cmd(args)

        elif target == "github":
            # Offerable from the template since it was written, and never
            # implemented — it fell through to "Unknown target". Reachable only
            # for a project that saved a repository address, which capability
            # now enforces, so the address here is always present.
            _run_windows_cmd(["start", "", (p.get("github_url") or "").strip()])

        elif target == "dashboard":
            # Open the project's dashboard URL in the default browser.
            # If the URL is local and not yet responding, try to start the app
            # via launch_dashboard.R before opening the browser.
            dash_row = db_query(
                "SELECT dashboard_url FROM projects WHERE project_id=?",
                params=(project_id,),
            )
            dash_url = (dash_row[0].get("dashboard_url") or "") if dash_row else ""
            if not dash_url:
                return JSONResponse(
                    {"status": "error", "message": "No dashboard_url configured for this project."},
                    status_code=400,
                )

            # Check if the local URL is already responding
            is_local = "127.0.0.1" in dash_url or "localhost" in dash_url
            is_running = False
            if is_local:
                import urllib.request as _ur
                try:
                    _ur.urlopen(dash_url, timeout=1)
                    is_running = True
                except Exception:
                    pass

            if is_local and not is_running:
                # Resolve WSL path for the project folder
                wsl_ext = external_path or ""
                if wsl_ext and ":" in wsl_ext and not wsl_ext.startswith("/mnt/"):
                    drive = wsl_ext[0].lower()
                    rest = wsl_ext[2:].replace("\\", "/")
                    wsl_ext = f"/mnt/{drive}{rest}"

                # Prefer dedicated launchers that poll for readiness before opening browser
                bat_wsl = f"{wsl_ext.rstrip('/')}/launch_hat_dashboard.bat"
                vbs_wsl = f"{wsl_ext.rstrip('/')}/launch_hat_dashboard.vbs"
                launch_r_wsl = f"{wsl_ext.rstrip('/')}/launch_dashboard.R"

                cmd_exe = "/mnt/c/Windows/System32/cmd.exe"
                if not os.path.exists(cmd_exe):
                    cmd_exe = "cmd.exe"

                # Dedicated launchers (.bat/.vbs) poll for readiness and open
                # the browser themselves — no extra browser-open needed.
                launcher_opens_browser = False

                if os.path.exists(bat_wsl):
                    win_bat = _windows_to_cmd(_wsl_to_windows(bat_wsl))
                    subprocess.Popen(
                        [cmd_exe, "/c", f'start "" "{win_bat}"'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    launcher_opens_browser = True
                elif os.path.exists(vbs_wsl):
                    # VBS launcher polls until R responds — no premature browser open
                    win_vbs = _windows_to_cmd(_wsl_to_windows(vbs_wsl))
                    subprocess.Popen(
                        [cmd_exe, "/c", f'start "" wscript.exe "{win_vbs}"'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    launcher_opens_browser = True
                elif os.path.exists(launch_r_wsl):
                    win_proj_dir = _wsl_to_windows(wsl_ext.rstrip("/"))
                    win_proj_dir_bs = _windows_to_cmd(win_proj_dir)
                    subprocess.Popen(
                        [cmd_exe, "/c",
                         f'start "" /d "{win_proj_dir_bs}" Rscript.exe launch_dashboard.R'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                else:
                    # No launcher found — open URL anyway (user sees connection refused)
                    _run_windows_cmd(["start", "", dash_url])
                    return JSONResponse({
                        "status": "error",
                        "message": "No launcher script found in project folder. Open manually.",
                    }, status_code=400)

                # Only open the browser from Python when the launcher doesn't do it
                if not launcher_opens_browser:
                    import threading
                    def _open_browser():
                        import time, subprocess as _sp
                        time.sleep(8)
                        _sp.Popen(
                            [cmd_exe, "/c", f'start "" "{dash_url}"'],
                            stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
                        )
                    threading.Thread(target=_open_browser, daemon=True).start()

                win_proj_dir = _wsl_to_windows(wsl_ext.rstrip("/"))
                msg = (
                    "Launcher started — it will open the browser once R is ready."
                    if launcher_opens_browser
                    else "Starting R Dashboard — browser opens in ~8 s. First load takes 30–60 s while R loads packages."
                )
                return JSONResponse({
                    "status": "starting",
                    "message": msg,
                    "target": target,
                    "path": win_proj_dir,
                    "project": project_title,
                })
            else:
                _run_windows_cmd(["start", "", dash_url])

        else:
            return JSONResponse(
                {"status": "error", "message": f"Unknown target: {target}"},
                status_code=400,
            )

        # Stamp last_session_at so "Recent work" on Today reflects actual usage
        if project_id not in ("rc-root", "", None):
            try:
                db_execute(
                    "UPDATE projects SET last_session_at = ? WHERE project_id = ?",
                    (datetime.datetime.now().isoformat(), project_id),
                )
            except Exception:
                pass

        return JSONResponse({
            "status": "ok",
            "target": target,
            "path": win_path,
            "project": project_title,
            "prompt_sent": prompt or None,
        })

    except OSError as e:
        # errno 8 (ENOEXEC) from starting a Windows binary means the interop
        # handler went away between the check above and the attempt. The raw
        # text — "[Errno 8] Exec format error" — describes a kernel condition
        # and gives the reader nothing to do, so translate it.
        if e.errno == 8:
            return JSONResponse(
                {"status": "error", "reason": "interop", "message": _interop_state()[1]
                 or "Windows apps cannot be started from here at the moment."},
                status_code=503,
            )
        return JSONResponse(
            {"status": "error", "message": f"Could not open that: {e.strerror or e}"},
            status_code=500,
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Could not open that: {e}"},
            status_code=500,
        )


@router.post("/api/launch/claude-desktop")
async def launch_claude_desktop():
    """Open Claude Desktop via Windows protocol handler — used by course idea builder."""
    try:
        _run_windows_cmd(["start", "", "claude://"])
        return JSONResponse({"status": "ok"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# An optional target date
# ---------------------------------------------------------------------------
# Reported 2026-08-27: give the option to date a task, "but dont make it
# obligatory, because often i dont know when i will work on something."
#
# `tasks.due_date` has existed all along; 70 of 71 open tasks had nothing in it,
# because the only control was a bare date picker. These are the words a date
# actually gets decided in.
#
# The empty string is stored as NULL, never ''. In SQLite '' sorts BEFORE any
# date, so an empty-string due_date made every undated task overdue — which is
# how 69 of 71 tasks came to be reported as late.
_WHEN = {
    "today":      lambda d: d,
    "tomorrow":   lambda d: d + datetime.timedelta(days=1),
    # "This week" means the end of the working week, not seven days out — a task
    # you say you will do this week is not due next Wednesday.
    "this-week":  lambda d: d + datetime.timedelta(days=(4 - d.weekday()) % 7),
    "next-week":  lambda d: d + datetime.timedelta(days=(4 - d.weekday()) % 7 + 7),
    "this-month": lambda d: (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
                            - datetime.timedelta(days=1),
}


@router.post("/api/task/{task_id}/due", response_class=HTMLResponse)
async def set_task_due(request: Request, task_id: str, when: str = Form("")):
    """Set, change or clear a task's target date. Always optional."""
    from main import templates
    when = (when or "").strip().lower()
    today = datetime.date.today()

    if not when:
        due = None                       # cleared: undated, not late
    elif when in _WHEN:
        due = _WHEN[when](today).isoformat()
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", when):
        due = when                       # straight from the picker
    else:
        log.warning("[due] unrecognised value %r for %s", when, task_id)
        due = None

    db_execute("UPDATE tasks SET due_date = ?, updated_at = ? WHERE task_id = ?",
               (due, datetime.datetime.now().isoformat(), task_id))

    row = (db_query("SELECT task_id, COALESCE(due_date,'') AS due FROM tasks "
                    "WHERE task_id = ?", (task_id,)) or [{}])[0]
    return templates.TemplateResponse(
        request, "partials/_due_fragment.html",
        {"task_id": task_id, "due": row.get("due", "")})
