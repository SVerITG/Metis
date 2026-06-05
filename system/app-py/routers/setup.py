"""
routers/setup.py — /setup page for first-run wizard and reconfiguration.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)

_METIS_ROOT  = Path(os.environ.get("METIS_RC_ROOT", Path(__file__).parent.parent.parent.parent))
_CONFIG_DIR  = _METIS_ROOT / "system" / "config"
_FIRST_RUN   = _CONFIG_DIR / ".first-run"
_DEMO_MARKER = _CONFIG_DIR / ".demo-mode"
_USER_CONFIG = _CONFIG_DIR / "user-config.yaml"
_USER_PREFS  = _CONFIG_DIR / "user-preferences.json"
_DB_PATH     = _METIS_ROOT / "system" / "app-py" / "data" / "metis.sqlite"
_DEMO_DIR    = _METIS_ROOT / "inputs" / "demo"


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


@router.post("/api/setup/configure", response_class=JSONResponse)
async def configure(request: Request):
    """
    Receive wizard answers from the browser, process with Claude API,
    write user-config.yaml + metis-persona.md + project stubs.
    """
    try:
        answers = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid JSON body"}, status_code=400)

    required = ["name", "role", "field"]
    missing = [k for k in required if not str(answers.get(k, "")).strip()]
    if missing:
        return JSONResponse(
            {"ok": False, "error": f"Missing required fields: {', '.join(missing)}"},
            status_code=422,
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip() or answers.get("api_key", "")

    # Import processor — lives alongside the installer scripts
    try:
        import importlib.util
        processor_path = _METIS_ROOT / "system" / "install" / "process_wizard_answers.py"
        spec = importlib.util.spec_from_file_location("process_wizard_answers", processor_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.process(answers, _METIS_ROOT, api_key or None)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

    return JSONResponse(result)


@router.post("/api/setup/reset-wizard", response_class=JSONResponse)
async def reset_wizard():
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _FIRST_RUN.touch()
    return {"ok": True, "message": "Wizard reset."}


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


@router.get("/api/partial/api-key-status", response_class=HTMLResponse)
async def api_key_status(request: Request):
    """Top-of-dashboard banner if ANTHROPIC_API_KEY is missing.

    Without a key, the morning brief generator, RAG retrieval, and any
    Claude-backed agent will silently fail. Surface this prominently.
    """
    import os as _os
    # Demo mode never shows the key banner — the demo serves canned content and
    # makes no live API calls, so the warning would only be noise in screenshots.
    if _os.environ.get("METIS_DEMO") == "1":
        return HTMLResponse("")
    key = _os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key and key.startswith("sk-ant-") and len(key) > 40:
        return HTMLResponse("")  # key looks valid → no banner
    return HTMLResponse("""
<div style="background:linear-gradient(180deg,#fef7e0,#fbeec0);border-bottom:1px solid #d4b659;
     padding:10px 24px;display:flex;align-items:center;gap:14px;font-family:var(--m-display);font-size:13px;color:#5b4a17;">
  <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#7a5a13" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
    <path d="M8 1.5L1.5 13.5h13z"/><line x1="8" y1="6" x2="8" y2="9.5"/><circle cx="8" cy="11.5" r=".7" fill="#7a5a13"/>
  </svg>
  <div style="flex:1;line-height:1.5;">
    <strong>I'm running without an API key.</strong>
    The morning brief, retrieval, and Claude-backed agents need
    <code style="font-family:var(--m-mono);font-size:12px;background:rgba(0,0,0,.06);padding:1px 5px;border-radius:3px;">ANTHROPIC_API_KEY</code>
    to work. Get a key at <a href="https://console.anthropic.com" target="_blank" rel="noopener" style="color:#5b4a17;text-decoration:underline;">console.anthropic.com</a>, then set it as a Windows user env variable (Start → Edit environment variables for your account → New).
    <div style="margin-top:6px;font-size:11.5px;color:#7a5a13;font-style:italic;">
      Already set it? Close and reopen Claude Code — the WSL session inherits the value at startup, not while it's running.
    </div>
  </div>
  <button onclick="this.parentElement.style.display='none'"
          style="background:transparent;border:1px solid #b8983e;color:#5b4a17;font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;padding:6px 12px;border-radius:3px;cursor:pointer;flex-shrink:0;">
    HIDE
  </button>
</div>
""")


@router.get("/api/partial/welcome-banner", response_class=HTMLResponse)
async def welcome_banner(request: Request):
    """Return first-run onboarding modal if no user is configured, else empty."""
    from db import db_scalar
    count = db_scalar("SELECT COUNT(*) FROM user_config", default=0) or 0
    if count > 0:
        return HTMLResponse("")
    return HTMLResponse("""
<div id="first-run-overlay" style="position:fixed;inset:0;background:rgba(15,20,18,0.72);
     z-index:9000;display:flex;align-items:center;justify-content:center;padding:24px;
     backdrop-filter:blur(2px);">
  <div style="background:var(--m-surface);border-radius:8px;max-width:580px;width:100%;
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
      I'm your research companion — literature, meetings, ideas, and projects, all in one place,
      personalised to the work you're actually doing. How would you like to start?
    </div>

    <!-- Two-path choice -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:24px;">

      <!-- Path A: Demo -->
      <div style="border:1px solid var(--m-line);border-radius:6px;padding:18px 16px;cursor:pointer;
           transition:border-color 0.15s;"
           onmouseover="this.style.borderColor='var(--m-accent)'" onmouseout="this.style.borderColor='var(--m-line)'"
           onclick="loadDemoMode()">
        <div style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.16em;color:var(--m-accent);margin-bottom:8px;">
          EXPLORE THE DEMO
        </div>
        <div style="font-size:13px;font-weight:500;margin-bottom:6px;">See Metis in action</div>
        <div style="font-size:12px;color:var(--m-muted);line-height:1.55;">
          Load a realistic sample workspace — an epidemiologist running an Ebola outbreak investigation.
          Every tab, every feature, filled with real-looking data. No setup required.
        </div>
        <div style="margin-top:12px;">
          <span id="demo-btn-label" style="display:inline-block;background:var(--m-surface-2);border:1px solid var(--m-line);
               font-family:var(--m-mono);font-size:9px;letter-spacing:0.14em;padding:7px 14px;border-radius:3px;color:var(--m-ink);">
            LOAD DEMO →
          </span>
        </div>
      </div>

      <!-- Path B: Setup -->
      <div style="border:1px solid var(--m-accent);border-radius:6px;padding:18px 16px;background:rgba(32,160,80,0.04);">
        <div style="font-family:var(--m-mono);font-size:9px;letter-spacing:0.16em;color:var(--m-accent);margin-bottom:8px;">
          SET UP MY WORKSPACE
        </div>
        <div style="font-size:13px;font-weight:500;margin-bottom:6px;">Start with your own work</div>
        <div style="font-size:12px;color:var(--m-muted);line-height:1.55;">
          Tell me your name, research focus, and projects. Takes 5 minutes.
          Everything Metis does from then on is personalised to you.
        </div>
        <div style="margin-top:12px;">
          <a href="/setup" style="display:inline-block;background:var(--m-accent);color:white;
             font-family:var(--m-mono);font-size:9px;letter-spacing:0.14em;
             padding:7px 14px;border-radius:3px;text-decoration:none;">
            START SETUP →
          </a>
        </div>
      </div>
    </div>

    <div style="display:flex;justify-content:center;">
      <button onclick="document.getElementById('first-run-overlay').remove();sessionStorage.setItem('metisWelcomeDismissed','1');"
              style="background:transparent;border:none;color:var(--m-muted);
              font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;
              padding:8px 14px;cursor:pointer;">I'LL DO THIS LATER</button>
    </div>

    <div style="margin-top:14px;font-size:11px;color:var(--m-muted);text-align:center;
         font-family:var(--m-display);font-style:italic;">
      You can always restart setup from the Metis tab → Configuration.
    </div>
  </div>
</div>
<script>
  // Auto-dismiss overlay on the setup page — the wizard is right behind it
  if (sessionStorage.getItem('metisWelcomeDismissed') === '1' ||
      window.location.pathname === '/setup') {
    var ov = document.getElementById('first-run-overlay');
    if (ov) ov.remove();
  }

  function loadDemoMode() {
    var btn = document.getElementById('demo-btn-label');
    if (btn) { btn.textContent = 'Loading…'; btn.style.opacity = '0.6'; }
    fetch('/api/setup/seed-demo', { method: 'POST' })
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          document.getElementById('first-run-overlay').remove();
          window.location.reload();
        } else {
          if (btn) { btn.textContent = 'Error — ' + (d.error || 'try again'); btn.style.opacity = '1'; }
        }
      })
      .catch(() => {
        if (btn) { btn.textContent = 'Network error'; btn.style.opacity = '1'; }
      });
  }
</script>
""")


@router.post("/api/setup/seed-demo", response_class=JSONResponse)
async def seed_demo():
    """Seed the database with the demo persona and generate the demo linelist CSV."""
    if not _DB_PATH.exists():
        return JSONResponse({"ok": False, "error": "Database not initialised. Start the dashboard first."}, status_code=503)
    try:
        seed_script = _METIS_ROOT / "system" / "install" / "seed_mockup_demo.py"
        if seed_script.exists():
            sys.path.insert(0, str(seed_script.parent))
            import importlib.util
            spec = importlib.util.spec_from_file_location("seed_mockup_demo", seed_script)
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            conn = sqlite3.connect(str(_DB_PATH))
            mod.seed(conn)
            conn.close()
            if hasattr(mod, "generate_linelist"):
                _DEMO_DIR.mkdir(parents=True, exist_ok=True)
                mod.generate_linelist(_DEMO_DIR / "linelist_ebola_equateur_2025.csv")
        _DEMO_MARKER.touch()
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/setup/exit-demo", response_class=JSONResponse)
async def exit_demo():
    """Remove demo mode marker."""
    _DEMO_MARKER.unlink(missing_ok=True)
    return {"ok": True}


@router.get("/api/partial/demo-banner", response_class=HTMLResponse)
async def demo_banner():
    """Slim persistent banner shown while in demo mode."""
    import os as _os
    if not (_DEMO_MARKER.exists() or _os.environ.get("METIS_DEMO") == "1"):
        return HTMLResponse("")
    return HTMLResponse("""
<div id="demo-mode-banner" style="background:linear-gradient(90deg,#0f2a1e,#1a3d28);
     border-bottom:1px solid #2a5a38;padding:8px 24px;display:flex;align-items:center;
     gap:16px;font-family:var(--m-mono);font-size:10px;letter-spacing:0.14em;">
  <span style="color:#4ade80;">▲ DEMO MODE</span>
  <span style="color:#6b9e7a;flex:1;">
    Showing sample data for Dr. Amélie Fontaine — health economist &amp; global health policy researcher.
    This is not your real workspace.
  </span>
  <a href="/setup" style="color:#4ade80;text-decoration:none;border:1px solid #2a5a38;
     padding:4px 12px;border-radius:3px;">SET UP MY WORKSPACE</a>
  <button onclick="fetch('/api/setup/exit-demo',{method:'POST'}).then(()=>location.reload())"
          style="background:transparent;border:1px solid #2a5a38;color:#6b9e7a;
          font-family:var(--m-mono);font-size:9px;letter-spacing:0.12em;padding:4px 10px;
          border-radius:3px;cursor:pointer;">EXIT DEMO</button>
</div>
""")
