"""
routers/setup.py — /setup page for first-run wizard and reconfiguration.
"""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
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
    instructions_file = _CONFIG_DIR / "claude-project-wizard.md"
    if instructions_file.exists():
        return PlainTextResponse(instructions_file.read_text(encoding="utf-8"))
    return PlainTextResponse("Instructions file not found.", status_code=404)


@router.get("/api/partial/welcome-banner", response_class=HTMLResponse)
async def welcome_banner(request: Request):
    """Return first-run onboarding modal if no user is configured, else empty.

    Addresses install-experience F-INSTALL-01: a non-technical researcher landing
    on a blank dashboard should immediately see what to do next, in Metis's voice.
    """
    from db import db_scalar
    count = db_scalar("SELECT COUNT(*) FROM user_config", default=0) or 0
    if count > 0:
        return HTMLResponse("")  # already configured — show nothing
    return HTMLResponse("""
<div id="first-run-overlay" style="position:fixed;inset:0;background:rgba(15,20,18,0.72);
     z-index:9000;display:flex;align-items:center;justify-content:center;padding:24px;
     backdrop-filter:blur(2px);">
  <div style="background:var(--m-surface);border-radius:8px;max-width:560px;width:100%;
       box-shadow:0 24px 64px rgba(0,0,0,0.32);padding:36px 40px 32px;
       font-family:var(--m-display);color:var(--m-ink);">

    <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
      <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--m-accent) 0%,#1a4a2e 100%);
           display:flex;align-items:center;justify-content:center;">
        <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="white" stroke-width="1.5"
             stroke-linecap="round" stroke-linejoin="round">
          <circle cx="10" cy="10" r="8.5"/><path d="M10 6v5l3 3"/>
        </svg>
      </div>
      <div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.18em;color:var(--m-muted);">
        WELCOME TO METIS
      </div>
    </div>

    <div style="font-size:22px;font-weight:500;line-height:1.3;margin-bottom:8px;">
      Hello — I'm Metis.
    </div>
    <div style="font-size:15px;line-height:1.55;color:var(--m-muted);margin-bottom:24px;">
      I'm your research companion. I keep track of your literature, meetings, ideas, and
      ongoing projects — so every question gets answered in the context of what you're
      actually working on. Take a minute to tell me about your work, and everything I do
      from here on becomes personalised to you.
    </div>

    <div style="border-top:1px solid var(--m-rule-soft);padding-top:20px;margin-bottom:24px;">
      <div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.16em;color:var(--m-muted);
           margin-bottom:14px;">YOUR FIRST THREE STEPS</div>

      <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:14px;">
        <div style="width:22px;height:22px;border-radius:50%;background:var(--m-accent);color:white;
             display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;
             flex-shrink:0;">1</div>
        <div>
          <div style="font-size:14px;font-weight:500;margin-bottom:2px;">Set up your profile</div>
          <div style="font-size:13px;color:var(--m-muted);line-height:1.5;">
            Tell me your name, your research focus, and a few projects you're working on. Takes 5 minutes.
          </div>
        </div>
      </div>

      <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:14px;">
        <div style="width:22px;height:22px;border-radius:50%;background:var(--m-surface-2);
             color:var(--m-muted);display:flex;align-items:center;justify-content:center;
             font-size:11px;font-weight:600;flex-shrink:0;border:1px solid var(--m-line);">2</div>
        <div>
          <div style="font-size:14px;font-weight:500;margin-bottom:2px;">Connect your library</div>
          <div style="font-size:13px;color:var(--m-muted);line-height:1.5;">
            Point me at your Zotero or Mendeley library, or drop some PDFs into your inbox folder. I'll index them.
          </div>
        </div>
      </div>

      <div style="display:flex;gap:12px;align-items:flex-start;">
        <div style="width:22px;height:22px;border-radius:50%;background:var(--m-surface-2);
             color:var(--m-muted);display:flex;align-items:center;justify-content:center;
             font-size:11px;font-weight:600;flex-shrink:0;border:1px solid var(--m-line);">3</div>
        <div>
          <div style="font-size:14px;font-weight:500;margin-bottom:2px;">Try a real question</div>
          <div style="font-size:13px;color:var(--m-muted);line-height:1.5;">
            Open Claude Code or Claude Desktop and type <code style="font-family:var(--m-mono);font-size:11px;background:var(--m-surface-2);padding:1px 5px;border-radius:3px;">/metis</code> followed by anything you'd ask a colleague. I'll route it to the right specialist.
          </div>
        </div>
      </div>
    </div>

    <div style="display:flex;gap:10px;align-items:center;justify-content:flex-end;">
      <button onclick="document.getElementById('first-run-overlay').remove();sessionStorage.setItem('metisWelcomeDismissed','1');"
              style="background:transparent;border:none;color:var(--m-muted);
              font-family:var(--m-mono);font-size:10px;letter-spacing:0.14em;
              padding:10px 14px;cursor:pointer;">I'LL DO THIS LATER</button>
      <a href="/setup" style="background:var(--m-accent);color:white;
         font-family:var(--m-mono);font-size:10px;letter-spacing:0.16em;
         padding:12px 22px;border-radius:4px;text-decoration:none;font-weight:600;">
         START THE 5-MINUTE SETUP →
      </a>
    </div>

    <div style="margin-top:18px;font-size:11px;color:var(--m-muted);text-align:center;
         font-family:var(--m-display);font-style:italic;">
      You can always reach this from the Metis tab → Configuration.
    </div>
  </div>
</div>
<script>
  // Don't re-show within the same browser session if user dismissed it
  if (sessionStorage.getItem('metisWelcomeDismissed') === '1') {
    var ov = document.getElementById('first-run-overlay');
    if (ov) ov.remove();
  }
</script>
""")
