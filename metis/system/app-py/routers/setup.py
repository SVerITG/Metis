"""
routers/setup.py — /setup page for first-run wizard and reconfiguration.
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)

_METIS_ROOT = Path(os.environ.get("METIS_RC_ROOT", Path(__file__).parent.parent.parent.parent))
_CONFIG_DIR = _METIS_ROOT / "system" / "config"
_FIRST_RUN  = _CONFIG_DIR / ".first-run"
_USER_CONFIG = _CONFIG_DIR / "user-config.yaml"
_USER_PREFS  = _CONFIG_DIR / "user-preferences.json"


def _wizard_status() -> dict:
    """Return which wizard sections have been completed."""
    config: dict = {}
    prefs: dict  = {}

    if _USER_CONFIG.exists():
        try:
            import yaml
            config = yaml.safe_load(_USER_CONFIG.read_text(encoding="utf-8")) or {}
        except Exception:
            pass

    if _USER_PREFS.exists():
        try:
            prefs = json.loads(_USER_PREFS.read_text(encoding="utf-8"))
        except Exception:
            pass

    user     = config.get("user", {})
    research = config.get("research", {})
    style    = config.get("style", {})
    teaching = config.get("teaching", {})

    sections = [
        ("About you",          bool(user.get("name") and user.get("role"))),
        ("Research domain",    bool(research.get("field"))),
        ("News & literature",  bool(prefs.get("news_topics") or prefs.get("pubmed_query"))),
        ("Current projects",   bool(config.get("projects"))),
        ("Seed knowledge",     False),  # no persistent marker — user-driven
        ("Ideas & notes",      False),  # no persistent marker
        ("Meeting notes",      False),  # no persistent marker
        ("Working style",      bool(style.get("response_length") or style.get("tools"))),
        ("Teaching",           bool(teaching.get("courses"))),
        ("Data sensitivity",   bool(config.get("data_sensitivity"))),
        ("Appearance",         bool(prefs.get("theme"))),
        ("How Metis works",    True),   # informational — always shown as complete after wizard
        ("Finish",             not _FIRST_RUN.exists()),
    ]
    return {
        "sections": sections,
        "first_run": _FIRST_RUN.exists(),
        "has_config": _USER_CONFIG.exists(),
        "display_name": user.get("name", ""),
        "domain": research.get("field", ""),
    }


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    status = _wizard_status()
    return templates.TemplateResponse(request, "setup.html", {
        "active_tab": "metis",
        **status,
    })


@router.post("/api/setup/reset-wizard", response_class=JSONResponse)
async def reset_wizard():
    """Re-create the .first-run marker so the wizard runs again on next Claude open."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _FIRST_RUN.touch()
    return {"ok": True, "message": "First-run marker created. Open Claude to start the wizard."}


@router.get("/api/setup/status", response_class=JSONResponse)
async def setup_status():
    return _wizard_status()


@router.get("/api/setup/project-instructions")
async def project_instructions():
    """Return the Claude Project wizard instructions as plain text for clipboard copy."""
    from fastapi.responses import PlainTextResponse
    instructions_file = _CONFIG_DIR / "claude-project-wizard.md"
    if instructions_file.exists():
        return PlainTextResponse(instructions_file.read_text(encoding="utf-8"))
    return PlainTextResponse("Instructions file not found.", status_code=404)
