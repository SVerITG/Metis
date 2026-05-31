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

from db import db_execute, db_query, db_scalar

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
    tasks = db_scalar("SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done','cancelled')", default=0) or 0
    paused = db_scalar("SELECT COUNT(*) FROM projects WHERE status='incubating'", default=0) or 0
    return HTMLResponse(f"{projects} PROJECTS · {tasks} TASKS · {paused} PAUSED")


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
async def work_kanban(request: Request):
    today = datetime.date.today().isoformat()
    week_end = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()

    inbox = db_query(
        "SELECT task_id as id, title, COALESCE(category,'') as tag, priority, due_date "
        "FROM tasks WHERE status='open' AND (due_date IS NULL OR due_date > ?) ORDER BY created_at DESC LIMIT 5",
        (week_end,),
    ) or []
    this_week = db_query(
        "SELECT task_id as id, title, COALESCE(category,'') as tag, priority, due_date "
        "FROM tasks WHERE status='open' AND due_date IS NOT NULL AND due_date <= ? ORDER BY due_date LIMIT 6",
        (week_end,),
    ) or []
    in_progress = db_query(
        "SELECT task_id as id, title, COALESCE(category,'') as tag, priority, due_date "
        "FROM tasks WHERE status='in_progress' ORDER BY updated_at DESC LIMIT 4"
    ) or []
    closed = db_query(
        "SELECT task_id as id, title, COALESCE(category,'') as tag, priority, due_date "
        "FROM tasks WHERE status='done' AND updated_at >= ? ORDER BY updated_at DESC LIMIT 5",
        ((datetime.datetime.now() - datetime.timedelta(days=7)).isoformat(),),
    ) or []
    return templates.TemplateResponse(
        request,
        "partials/work_kanban.html",
        {"inbox": inbox, "this_week": this_week, "in_progress": in_progress, "closed": closed, "today": today},
    )


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
        "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done', 'cancelled')", default=0
    )
    overdue = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('done', 'cancelled') "
        "AND due_date IS NOT NULL AND due_date < ?",
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
        where = "status NOT IN ('done', 'cancelled')"
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
async def work_due_today(request: Request):
    today = str(datetime.date.today())
    rows = db_query(
        "SELECT t.task_id as id, t.title, t.status, t.due_date, "
        "COALESCE(t.priority,'medium') as priority, "
        "p.title as project "
        "FROM tasks t LEFT JOIN projects p ON p.project_id = t.project_id "
        "WHERE t.status NOT IN ('done','cancelled') "
        "AND t.due_date IS NOT NULL AND t.due_date <= ? "
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
        {"overdue": overdue, "due_today": due_today, "today": today},
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
        "WHERE t.status NOT IN ('done','cancelled') "
        "ORDER BY "
        "  CASE COALESCE(t.priority,'medium') WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
        "  CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END, "
        "  t.due_date LIMIT 40",
        default=[],
    )
    overdue_ids = {
        r["id"] for r in (db_query(
            "SELECT task_id as id FROM tasks WHERE status NOT IN ('done','cancelled') "
            "AND due_date IS NOT NULL AND due_date < ?", (today,), default=[]
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


def _parse_launchers(p: dict) -> list:
    """Return launcher list from the launchers JSON column, falling back to launcher_type."""
    raw = p.get("launchers")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    # Legacy fallback: derive from launcher_type
    lt = p.get("launcher_type") or ""
    has_path = bool(p.get("external_path"))
    if lt == "article":
        return ["explorer", "claude_chat", "claude_cowork"] if has_path else ["claude_chat", "claude_cowork"]
    if lt == "rstudio":
        return ["rstudio", "claude_code", "claude_chat", "claude_cowork", "explorer"]
    if lt == "vscode":
        return ["vscode", "claude_code", "claude_chat", "claude_cowork", "explorer"]
    if has_path:
        return ["claude_code", "claude_chat", "claude_cowork", "explorer"]
    return ["claude_code", "claude_chat", "claude_cowork"]


@router.get("/api/partial/work/projects", response_class=HTMLResponse)
async def work_projects(request: Request):
    projects = db_query(
        "SELECT project_id as id, title, description, domain, priority, next_step, status, "
        "external_path, launcher_type, github_url, launchers, dashboard_url, "
        "project_type, last_session_at "
        "FROM projects WHERE status = 'active' AND COALESCE(tracked, 1) = 1 "
        "ORDER BY COALESCE(display_order, 999) ASC LIMIT 20"
    )
    for p in (projects or []):
        p["launchers_list"] = _parse_launchers(p)
    return templates.TemplateResponse(
        request,
        "partials/work_projects.html",
        {"projects": projects},
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
        "SELECT task_id, title, status, category, updated_at, starred FROM tasks "
        "WHERE project_id=? AND status NOT IN ('done','deleted') "
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
        "tags, started_at, completed_at, image_url "
        "FROM projects WHERE project_id=? LIMIT 1",
        (project_id,),
    )
    if not rows:
        return HTMLResponse("<p>Project not found.</p>", status_code=404)
    p = rows[0]

    open_tasks = db_query(
        "SELECT task_id, title, status, category, updated_at FROM tasks "
        "WHERE project_id=? AND status NOT IN ('done','deleted') "
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
async def task_delete(task_id: int):
    try:
        db_execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        return JSONResponse({"status": "ok", "task_id": task_id})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Task create (quick-add per project)
# ---------------------------------------------------------------------------


@router.post("/api/task/create", response_class=HTMLResponse)
async def task_create(request: Request):
    data = await request.json()
    project_id = data.get("project_id", "")
    title = (data.get("title") or "").strip()
    category = (data.get("category") or "general").strip() or "general"
    if not title:
        return JSONResponse({"status": "error", "message": "Title required"}, status_code=400)
    task_id = uuid.uuid4().hex[:12]
    now = datetime.datetime.now().isoformat()
    db_execute(
        "INSERT INTO tasks (task_id, project_id, title, status, category, created_at, updated_at) "
        "VALUES (?, ?, ?, 'open', ?, ?, ?)",
        (task_id, project_id, title, category, now, now),
    )
    tasks = db_query(
        "SELECT task_id, title, status, category FROM tasks "
        "WHERE project_id=? AND status NOT IN ('done','deleted') "
        "ORDER BY category, created_at LIMIT 15",
        params=(project_id,),
    )
    done_count = db_scalar(
        "SELECT COUNT(*) FROM tasks WHERE project_id=? AND status='done'",
        params=(project_id,),
        default=0,
    )
    return templates.TemplateResponse(
        request,
        "partials/work_project_tasks.html",
        {"tasks": tasks, "done_count": done_count, "project_id": project_id},
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
        "SELECT task_id FROM tasks WHERE status NOT IN ('done','cancelled','paused') "
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
            "WHERE project_id=? AND status NOT IN ('done','cancelled','deleted') "
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
                "SELECT project_id, title, external_path, launcher_type, launcher_path "
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
        if not external_path:
            return JSONResponse(
                {
                    "status": "error",
                    "message": f"Project '{project_title or project_id}' has no external_path set. "
                               "Seed it in the DB first.",
                },
                status_code=400,
            )

    win_path = _wsl_to_windows(external_path)

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

                # Prefer bat launcher (handles R discovery, path quoting, browser)
                bat_wsl = f"{wsl_ext.rstrip('/')}/launch_hat_dashboard.bat"
                launch_r_wsl = f"{wsl_ext.rstrip('/')}/launch_dashboard.R"

                cmd_exe = "/mnt/c/Windows/System32/cmd.exe"
                if not os.path.exists(cmd_exe):
                    cmd_exe = "cmd.exe"

                if os.path.exists(bat_wsl):
                    win_bat = _windows_to_cmd(_wsl_to_windows(bat_wsl))
                    # Use shell string so cmd.exe quotes the path correctly
                    subprocess.Popen(
                        [cmd_exe, "/c", f'start "" "{win_bat}"'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                elif os.path.exists(launch_r_wsl):
                    win_proj_dir = _wsl_to_windows(wsl_ext.rstrip("/"))
                    win_proj_dir_bs = _windows_to_cmd(win_proj_dir)
                    # Build shell string so paths with spaces are quoted
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

                # Open browser after delay — cold start takes 30-60 s
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
                return JSONResponse({
                    "status": "starting",
                    "message": "Starting R Dashboard — browser opens in ~8 s. First load takes 30–60 s while R loads packages.",
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

    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Launch failed: {e}"},
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
