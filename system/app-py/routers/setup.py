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
# Live DB path: always resolve via db.get_db_path() (off OneDrive, see db.py).
# Do NOT hardcode a path here — it caused split-brain reads/writes.
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
        ("News & literature",  bool(prefs.get("news_interests") or prefs.get("news_topics")
                                    or prefs.get("pubmed_query"))),
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

    # The script folders are only registered by the processor; reading them
    # takes ~30 s per few hundred scripts, so it runs after the reply.
    dmem = result.get("data_memory") or {}
    if dmem.get("registered"):
        try:
            from metis_mcp import data_memory as dm
            from db import get_db_path
            dmem["learning"] = dm.start_background_refresh(db=Path(get_db_path()))
        except Exception as exc:
            dmem["error"] = f"Folders saved; learning them failed to start ({exc})."

    return JSONResponse(result)


@router.post("/api/setup/reset-wizard", response_class=JSONResponse)
async def reset_wizard():
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _FIRST_RUN.touch()
    return {"ok": True, "message": "Wizard reset."}


@router.get("/api/setup/status", response_class=JSONResponse)
async def setup_status():
    return _wizard_status()


# The tour's stops: (link, tab name as the navigation shows it, what it is for,
# one thing to try). Kept here, next to the route, so a renamed tab is one edit.
TOUR_STOPS = [
    ("/today", "Today", "Your day on one page: what is planned, what is due, a short "
     "brief of the news and papers that matter to your work.",
     "plan one task for today and watch it appear in the plan strip."),
    ("/news", "News", "What is happening in the subjects you asked Metis to watch, "
     "grouped into threads rather than a raw feed.",
     "rate a story — Metis learns what is relevant to you."),
    ("/knowledge", "Library", "Your papers and documents: the knowledge Claude searches "
     "before it reaches for the internet.",
     "search for a topic; results are ranked by closeness to your work."),
    ("/work", "Work", "Projects and tasks, on a board where dragging a card is the edit, "
     "and a calendar.", "move a task to another column."),
    ("/meetings", "Meetings", "Meeting notes, with decisions and action items pulled out.",
     "open a meeting and look at its action items."),
    ("/thinking", "Reflection", "Ideas, notes and brainstorms — and the connections Metis "
     "finds between them and your projects.", "add an idea in one line."),
    ("/learning", "Learning", "Courses and study plans, scheduled into your week.",
     "open a course and see its next lesson."),
    ("/presentation", "Present", "Your slide decks and the lessons they were built from.",
     "browse the repository."),
    ("/metis", "Metis", "Metis itself: your profile and interests, which specialists did "
     "what, and whether everything is working.", "check your interests are the right ones."),
]


@router.get("/tour", response_class=HTMLResponse)
async def tour_page(request: Request):
    import os as _os
    demo = _DEMO_MARKER.exists() or _os.environ.get("METIS_DEMO") == "1"
    return templates.TemplateResponse(request, "tour.html", {
        "active_tab": "metis", "stops": TOUR_STOPS, "demo": demo,
    })


@router.get("/api/setup/verify", response_class=JSONResponse)
async def setup_verify():
    """Prove Metis actually works before the wizard declares success (Keystone P1.3).

    Returns {ok, checks:[{name, ok, critical, detail}]}. The wizard shows these as
    green/red ticks and only says "ready" when all CRITICAL checks pass — so a user
    is never told "done" while the data layer, tools, or profile are actually broken.
    """
    checks: list[dict] = []

    def add(name, ok, critical, detail=""):
        checks.append({"name": name, "ok": bool(ok), "critical": bool(critical), "detail": str(detail)[:140]})

    # 1) Dashboard is serving — we answered this request, so it is.
    add("Dashboard running", True, True, "")

    # 2) Data layer — the live DB is present and has tables.
    try:
        from db import get_db_path, db_scalar
        dbp = get_db_path()
        ntables = db_scalar("SELECT count(*) FROM sqlite_master WHERE type='table'", default=0)
        add("Database ready", bool(ntables), True, f"{ntables} tables ({dbp.name})")
    except Exception as e:
        add("Database ready", False, True, f"{type(e).__name__}: {e}")

    # 3) The MCP package Claude will launch is importable.
    try:
        rc_root = os.environ.get("METIS_RC_ROOT", "")
        if rc_root:
            mcp_src = str(Path(rc_root) / "system" / "mcp-server" / "src")
            if mcp_src not in sys.path:
                sys.path.insert(0, mcp_src)
        import metis_mcp  # noqa: F401
        add("Metis tools importable", True, True, "")
    except Exception as e:
        add("Metis tools importable", False, True, f"{type(e).__name__}: {e}")

    # 4) Embedding model cached → semantic search works offline from first run.
    # Every place the embedder itself looks — not one guessed folder. Looking in
    # ~/.cache/fastembed alone said "not cached" on a fresh install whose model sat
    # in the HuggingFace cache and searched perfectly well.
    try:
        try:
            from metis_mcp.embeddings import _cache_candidates
            places = list(_cache_candidates())
        except Exception:
            places = [Path.home() / ".cache" / "fastembed"]
        places.append(Path.home() / ".cache" / "huggingface" / "hub")
        cached = any(c.exists() and any(c.rglob("*.onnx")) for c in places)
        add("Search model cached", cached, False,
            "offline search ready" if cached else "will download on first online use")
    except Exception as e:
        add("Search model cached", False, False, f"{type(e).__name__}: {e}")

    # 5) Claude can see who this is. Checked in user-preferences.json — what
    # get_user_profile() and the News and Today surfaces read — not merely that
    # some config file exists: setup used to write user-config.yaml only, and this
    # check passed while Claude greeted the person as "Researcher".
    prefs: dict = {}
    try:
        prefs = json.loads(_USER_PREFS.read_text(encoding="utf-8")) if _USER_PREFS.exists() else {}
    except Exception:
        prefs = {}
    name = str(prefs.get("display_name") or "").strip()
    add("Metis knows who you are", bool(name), True,
        name if name else "no name in user-preferences.json — Claude would say 'Researcher'")
    lib = prefs.get("library_interests") or prefs.get("interests") or []
    news = prefs.get("news_interests") or prefs.get("news_topics") or []
    add("Your interests reached Metis", bool(lib), True,
        f"{len(lib)} for your library, {len(news)} for news" if lib
        else "no library interests saved — literature cannot be ranked for you")
    add("News to watch", bool(news), False,
        f"{len(news)} topic(s)" if news else "none yet — add them on the Metis tab")

    # 6) The install doctor's last verdict (non-critical extra signal). Read, not
    # re-run: it starts Metis to test it, which takes too long for this page.
    try:
        rd = json.loads((_CONFIG_DIR / "readiness.json").read_text(encoding="utf-8"))
        fails = [c.get("name") for c in rd.get("checks", []) if c.get("status") == "fail"]
        add("Full self-check", not fails, False,
            f"{rd.get('overall', '')} ({str(rd.get('run_at', ''))[:16].replace('T', ' ')})"
            if not fails else "needs attention: " + ", ".join(fails))
    except Exception:
        pass  # no check has run yet; never block the gate on it

    ok = all(c["ok"] for c in checks if c["critical"])
    return JSONResponse({"ok": ok, "checks": checks})


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
    # Also honor a key saved to system/.env even if THIS process hasn't reloaded
    # its environment — OR if the env holds a bad/leaked value (not a real key).
    # Without this the banner nags forever despite a valid key sitting in .env.
    if not (key.startswith("sk-ant-") and len(key) > 40):
        try:
            from pathlib import Path as _Path
            _rc = _os.environ.get("METIS_RC_ROOT", "")
            if _rc:
                _envf = _Path(_rc) / "system" / ".env"
                if _envf.exists():
                    for _line in _envf.read_text(encoding="utf-8").splitlines():
                        if _line.strip().startswith("ANTHROPIC_API_KEY="):
                            key = _line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
        except Exception:
            pass
    if key and key.startswith("sk-ant-") and len(key) > 40:
        return HTMLResponse("")  # key looks valid → no banner
    return HTMLResponse("""
<div id="api-key-banner" style="background:linear-gradient(180deg,#fef7e0,#fbeec0);border-bottom:1px solid #d4b659;
     padding:10px 24px;display:flex;align-items:center;gap:14px;font-family:var(--m-display);font-size:13px;color:#5b4a17;">
  <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="#7a5a13" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">
    <path d="M8 1.5L1.5 13.5h13z"/><line x1="8" y1="6" x2="8" y2="9.5"/><circle cx="8" cy="11.5" r=".7" fill="#7a5a13"/>
  </svg>
  <div style="flex:1;line-height:1.5;">
    <strong>Optional: add an Anthropic API key.</strong>
    Metis works fully in Claude Desktop and Claude Code without one. A key (paid separately)
    adds background features such as the automatic morning brief. Get one at
    <a href="https://console.anthropic.com" target="_blank" rel="noopener" style="color:#5b4a17;text-decoration:underline;">console.anthropic.com</a>
    and paste it here — Metis saves it locally for you, no setup:
    <div style="display:flex;gap:8px;margin-top:8px;align-items:center;flex-wrap:wrap;">
      <input id="inline-api-key" type="password" placeholder="sk-ant-..." autocomplete="off" spellcheck="false"
             style="font-family:var(--m-mono);font-size:12px;padding:6px 10px;border:1px solid #b8983e;border-radius:3px;min-width:300px;background:#fff;color:#3a2f10;">
      <button onclick="saveInlineApiKey(this)"
              style="background:#7a5a13;border:1px solid #7a5a13;color:#fff;font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;padding:6px 14px;border-radius:3px;cursor:pointer;">SAVE KEY</button>
      <span id="inline-api-key-msg" style="font-size:11.5px;color:#7a5a13;"></span>
    </div>
    <div style="margin-top:6px;font-size:11.5px;color:#7a5a13;font-style:italic;">
      Saved to <code style="font-family:var(--m-mono);">system/.env</code> on your machine — never uploaded.
    </div>
  </div>
  <button onclick="this.parentElement.style.display='none';try{localStorage.setItem('metisApiKeyBannerHidden','1')}catch(e){}"
          style="background:transparent;border:1px solid #b8983e;color:#5b4a17;font-family:var(--m-mono);font-size:10px;letter-spacing:0.12em;padding:6px 12px;border-radius:3px;cursor:pointer;flex-shrink:0;">
    NOT NOW
  </button>
</div>
<script>
// Optional, so a "not now" is remembered in this browser; the Metis tab keeps the setting.
try { if (localStorage.getItem('metisApiKeyBannerHidden') === '1') {
  var _b = document.getElementById('api-key-banner'); if (_b) _b.style.display = 'none'; } } catch (e) {}
function saveInlineApiKey(btn){
  var el=document.getElementById('inline-api-key'), msg=document.getElementById('inline-api-key-msg');
  var v=(el.value||'').trim();
  if(!v){ msg.textContent='Paste your key first.'; return; }
  if(v.indexOf('sk-ant-')!==0){ msg.textContent='That doesn\\'t look like an Anthropic key (starts with sk-ant-).'; return; }
  btn.disabled=true; msg.textContent='Saving…';
  fetch('/api/settings/api-key',{method:'POST',headers:{'Content-Type':'application/json','X-Metis-Confirm':'api-key'},
        body:JSON.stringify({name:'ANTHROPIC_API_KEY',value:v})})
    .then(function(r){return r.json();})
    .then(function(d){
      if(d.status==='ok'){ el.value='';
        msg.innerHTML='✓ Saved and applied — you\\'re all set.';
        var b=document.getElementById('api-key-banner'); if(b){ setTimeout(function(){ b.style.display='none'; }, 1200); } }
      else { msg.textContent='Error: '+(d.message||'could not save'); btn.disabled=false; }
    })
    .catch(function(){ msg.textContent='Error saving — try the Metis tab → API keys.'; btn.disabled=false; });
}
</script>
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
          // Straight into the tour: a page of sample data with no guide is the
          // part of the demo nobody could make sense of.
          window.location.href = '/tour';
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


def _demo_module():
    """The sample-workspace loader. It ships with Metis; if it is missing, say so —
    this route used to switch demo mode on over an empty database and report ok."""
    import importlib.util
    path = _METIS_ROOT / "system" / "install" / "seed_mockup_demo.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("seed_mockup_demo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@router.post("/api/setup/seed-demo", response_class=JSONResponse)
async def seed_demo():
    """Load the sample workspace, recording every row so Exit demo can remove it."""
    from db import get_db_path
    _db_path = get_db_path()
    if not _db_path.exists():
        return JSONResponse({"ok": False, "error": "Database not initialised. Start the dashboard first."}, status_code=503)
    mod = _demo_module()
    if mod is None:
        return JSONResponse({"ok": False, "error": "The demo is not included in this installation."}, status_code=404)
    try:
        res = mod.load(_db_path)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    if not res.get("ok"):
        return JSONResponse(res, status_code=409)
    _DEMO_MARKER.touch()
    return res


@router.post("/api/setup/exit-demo", response_class=JSONResponse)
async def exit_demo():
    """Leave demo mode: remove exactly the sample rows, then the banner."""
    removed = 0
    mod = _demo_module()
    if mod is not None:
        try:
            removed = mod.unload().get("removed", 0)
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
    _DEMO_MARKER.unlink(missing_ok=True)
    return {"ok": True, "removed": removed}


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
    Sample workspace of a fictional researcher, Dr. Amélie Fontaine (health economist).
    Exit demo removes all of it; your own setup is kept.
  </span>
  <a href="/tour" style="color:#4ade80;text-decoration:none;border:1px solid #2a5a38;
     padding:4px 12px;border-radius:3px;">TAKE THE TOUR</a>
  <a href="/setup" style="color:#4ade80;text-decoration:none;border:1px solid #2a5a38;
     padding:4px 12px;border-radius:3px;">SET UP MY WORKSPACE</a>
  <button onclick="fetch('/api/setup/exit-demo',{method:'POST'}).then(()=>location.reload())"
          style="background:transparent;border:1px solid #2a5a38;color:#6b9e7a;
          font-family:var(--m-mono);font-size:9px;letter-spacing:0.12em;padding:4px 10px;
          border-radius:3px;cursor:pointer;">EXIT DEMO</button>
</div>
""")
