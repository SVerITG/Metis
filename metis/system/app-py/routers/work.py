"""
routers/work.py — Work tab routes + project launcher + task actions (v7.0).

Project launcher ports the logic from metis/system/app/R/mod_work.R (lines 29-160)
to FastAPI. Supports rstudio, vscode, explorer, claude_desktop, claude_code.
"""

import datetime
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
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
        {"inbox": inbox, "this_week": this_week, "in_progress": in_progress, "closed": closed},
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
# Projects list
# ---------------------------------------------------------------------------


@router.get("/api/partial/work/projects", response_class=HTMLResponse)
async def work_projects(request: Request):
    projects = db_query(
        "SELECT project_id as id, title, domain, priority, next_step, status, "
        "external_path, launcher_type, github_url "
        "FROM projects WHERE status = 'active' ORDER BY priority DESC LIMIT 10"
    )
    return templates.TemplateResponse(
        request,
        "partials/work_projects.html",
        {"projects": projects},
    )


# ---------------------------------------------------------------------------
# Task actions — mark done, delete
# ---------------------------------------------------------------------------


@router.post("/api/task/{task_id}/done")
async def task_mark_done(task_id: int):
    try:
        db_execute(
            "UPDATE tasks SET status = 'done', updated_at = ? WHERE task_id = ?",
            (datetime.datetime.now().isoformat(), task_id),
        )
        return JSONResponse({"status": "ok", "task_id": task_id})
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

        elif target == "claude_desktop":
            _run_windows_cmd(["start", "", "claude://"])

        elif target == "claude_code":
            # Launch Windows Terminal at the project path, run claude, optionally
            # pass a prompt as the initial argument.
            args = ["start", "wt.exe", "-w", "0", "new-tab", "-d", win_path, "claude"]
            if prompt:
                args.append(prompt)
            _run_windows_cmd(args)

        else:
            return JSONResponse(
                {"status": "error", "message": f"Unknown target: {target}"},
                status_code=400,
            )

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
