"""
main.py — Metis Dashboard FastAPI application.
"""

import datetime
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers import (
    capture,
    knowledge,
    learning,
    meetings,
    metis_tab,
    planner,
    teach,
    thinking,
    today,
    work,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Metis Dashboard", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

# Tab routers — all live under /tab prefix for the full-page variants;
# the partials/api routes are registered without prefix via the router itself.
app.include_router(today.router)
app.include_router(knowledge.router)
app.include_router(meetings.router)
app.include_router(learning.router)
app.include_router(work.router)
app.include_router(thinking.router)
app.include_router(planner.router)
app.include_router(teach.router)
app.include_router(metis_tab.router)
app.include_router(capture.router, prefix="/api")

# ---------------------------------------------------------------------------
# Root + named tab full-page routes
# ---------------------------------------------------------------------------

_TAB_TEMPLATES = {
    "today": "today.html",
    "knowledge": "knowledge.html",
    "meetings": "meetings.html",
    "learning": "learning.html",
    "work": "work.html",
    "thinking": "thinking.html",
    "planner": "planner.html",
    "teach": "teach.html",
    "metis": "metis_tab.html",
}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
     request, "today.html", {"active_tab": "today"}
 )


@app.get("/{tab}", response_class=HTMLResponse)
async def tab_page(request: Request, tab: str):
    template_name = _TAB_TEMPLATES.get(tab)
    if template_name is None:
        return HTMLResponse(status_code=404, content="Tab not found")
    return templates.TemplateResponse(
        request, template_name, {"active_tab": tab}
    )


# ---------------------------------------------------------------------------
# API utilities
# ---------------------------------------------------------------------------


@app.get("/api/check-db-mtime")
async def check_db_mtime():
    """Return the mtime of the SQLite database file."""
    try:
        from db import get_db_path

        db_path = get_db_path()
        mtime = db_path.stat().st_mtime
    except Exception:
        mtime = 0.0
    return JSONResponse({"mtime": mtime})


@app.get("/api/trust-badge", response_class=HTMLResponse)
async def trust_badge():
    """Return an HTML snippet with today's agent call count + network policy."""
    today = str(datetime.date.today())
    try:
        from db import db_scalar

        count = db_scalar(
            f"SELECT COUNT(*) FROM sessions WHERE started_at LIKE '{today}%'",
            default=0,
        )
    except Exception:
        count = 0

    # Read network policy
    policy = "normal"
    try:
        rc_root = os.environ.get("METIS_RC_ROOT", "")
        if rc_root:
            p = Path(rc_root) / "system" / "config" / "network-policy.json"
            if p.exists():
                import json
                data = json.loads(p.read_text(encoding="utf-8"))
                policy = data.get("policy", "normal")
    except Exception:
        pass

    policy_icon = {"strict": "bi-shield-lock", "offline": "bi-wifi-off", "normal": "bi-shield-check"}.get(policy, "bi-shield-check")
    policy_cls  = {"strict": "text-warning", "offline": "text-danger", "normal": ""}.get(policy, "")

    label = f"{count} calls today" if count else "Local-first"
    return HTMLResponse(
        f'<i class="bi {policy_icon} {policy_cls}"></i>'
        f'<span class="trust-badge-text">{label}</span>'
    )
