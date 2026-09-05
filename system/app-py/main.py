"""
main.py — Metis Dashboard FastAPI application.
"""

import datetime
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers import (
    api_v1,
    capture,
    connections,
    jobs,
    knowledge,
    learning,
    meetings,
    memory_health,
    metis_tab,
    new_literature,
    planner,
    calendar_plan,
    setup,
    speakers,
    teach,
    thinking,
    focus,
    today,
    transcription,
    verification,
    work,
    shelves,
    stack,
)

log = logging.getLogger("metis")


class _SkipBootScan(Exception):
    """Internal sentinel: skip the startup news/literature scan (e.g. demo mode)."""


@asynccontextmanager
async def lifespan(app: FastAPI):
    from db import run_migrations
    applied = run_migrations()
    if applied:
        log.info("DB migrations applied: %s", ", ".join(applied))

    # Per-feature table init — fail-soft. Each runs in its own try/except so a DB
    # problem disables only that feature instead of crashing the whole app. These
    # used to run at module-import time, which meant any DB error took the entire
    # dashboard down (the 2026-06-19 outage). See stability evaluation.
    for _mod, _fn in (("routers.speakers", "_ensure_table"),
                      ("routers.meetings", "_ensure_columns")):
        try:
            import importlib
            getattr(importlib.import_module(_mod), _fn)()
        except Exception as exc:
            log.warning("[startup] %s.%s skipped (feature degraded): %s", _mod, _fn, exc)

    # Startup health check — runs after migrations so tables exist
    try:
        from startup_eval import run_startup_eval
        run_startup_eval()
    except Exception as exc:
        log.warning("Startup eval skipped: %s", exc)

    # Ensure MCP tools are findable — add src to sys.path at startup
    import sys as _sys
    _rc = os.environ.get("METIS_RC_ROOT", "")
    if _rc:
        _mcp_src = str(Path(_rc) / "system" / "mcp-server" / "src")
        if _mcp_src not in _sys.path:
            _sys.path.insert(0, _mcp_src)
        del _mcp_src
    del _rc
    # In demo mode the scheduler is NOT started: its catch-up sequence would
    # immediately run the morning news/literature scan, pulling the real user's
    # feeds and library folder into the demo database and overwriting the
    # curated demo data. The demo is a static, self-contained snapshot.
    if os.environ.get("METIS_DEMO") == "1":
        log.info("[startup] Demo mode — scheduler not started (no background scans)")
    else:
        try:
            from scheduler import scheduler, setup_jobs
            setup_jobs()
            scheduler.start()
            log.info("APScheduler started")
        except Exception as exc:
            log.warning("Scheduler could not start: %s", exc)
    try:
        from inbox_watcher import start_inbox_watcher
        start_inbox_watcher()
    except Exception as exc:
        log.warning("Inbox watcher could not start: %s", exc)
    # On startup: run news scan if last scan was more than 4 hours ago,
    # then pre-generate today's morning brief.
    #
    # In demo mode this is skipped entirely: a live scan would pull the real
    # user's news feeds and literature folder into the demo database (breaking
    # the curated, coherent demo data) and try to generate a brief via the API.
    _demo_mode = os.environ.get("METIS_DEMO") == "1"
    if _demo_mode:
        log.info("[startup] Demo mode — skipping boot scan + brief generation")
    try:
        if _demo_mode:
            raise _SkipBootScan()
        import sqlite3 as _sq3
        import threading

        def _hours_since_last_scan() -> float:
            """Return hours since last successful news scan (jobs_log), or 999 if never."""
            try:
                import datetime as _dt
                from db import get_db_path
                db_p = str(get_db_path())
                conn = _sq3.connect(db_p, timeout=5)
                row = conn.execute(
                    "SELECT created_at FROM jobs_log WHERE job_type IN ('morning_scan','news_scan') "
                    "AND status='ok' ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                conn.close()
                if row and row[0]:
                    last = _dt.datetime.fromisoformat(row[0])
                    return (_dt.datetime.now() - last).total_seconds() / 3600
            except Exception:
                pass
            return 999.0

        def _boot_scan_and_brief():
            # Let the dashboard finish opening and become responsive BEFORE the
            # news/literature scan starts competing for disk + network. The Today
            # page's morning-brief card generates itself on first view (background
            # thread, see routers/today.py), so nothing here blocks the UI.
            import time as _time
            _time.sleep(25)
            try:
                if _hours_since_last_scan() > 4:
                    log.info("[startup] Running news scan (last scan >4 h ago)")
                    from metis_mcp.tools.content_scan import scan_literature_folder, scan_news_feeds
                    scan_news_feeds(max_per_feed=10)
                    scan_literature_folder()
                    # Log success so the scheduler doesn't double-scan today
                    try:
                        import datetime as _dt
                        from db import get_db_path
                        db_p = str(get_db_path())
                        conn = _sq3.connect(db_p, timeout=5)
                        conn.execute(
                            "INSERT INTO jobs_log (job_type, status, details, created_at) VALUES (?,?,?,?)",
                            ("morning_scan", "ok", "startup scan", _dt.datetime.now().isoformat()),
                        )
                        conn.commit()
                        conn.close()
                    except Exception:
                        pass
            except Exception as exc:
                log.debug("Startup news scan skipped: %s", exc)
            # Pre-generate morning brief after scan
            try:
                from routers.today import _get_or_generate_brief
                _get_or_generate_brief()
            except Exception as exc:
                log.debug("Startup brief generation skipped: %s", exc)

        threading.Thread(target=_boot_scan_and_brief, daemon=True, name="boot-scan").start()
    except _SkipBootScan:
        pass  # demo mode — intentionally no scan
    except Exception as exc:
        log.debug("Could not start boot scan thread: %s", exc)
    yield
    try:
        from scheduler import scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Metis Dashboard", docs_url=None, redoc_url=None, lifespan=lifespan)

# ── CSRF: reject cross-origin mutating requests ──────────────────────────────
# Any website in the browser could POST to /api/capture, /api/restart, etc.
# This middleware checks the Origin header on non-safe HTTP methods. If an
# Origin is present and isn't localhost, the request is rejected with 403.
# Same-origin requests (HTMX, fetch from the dashboard) either omit the
# Origin header entirely or send http://127.0.0.1 / http://localhost.
from starlette.middleware.base import BaseHTTPMiddleware


class OriginCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin", "")
            if origin and not (
                origin.startswith("http://127.0.0.1")
                or origin.startswith("http://localhost")
            ):
                return JSONResponse({"error": "origin rejected"}, status_code=403)
        return await call_next(request)


class AddinCORSMiddleware(BaseHTTPMiddleware):
    """Attach CORS headers to /api/v1 responses for Office add-in origins.

    Only /api/v1 — the HTML dashboard must stay same-origin-only. And only the
    Office hosts: this says who may ASK, while the bearer token in api_v1.py says
    who may READ. Neither is sufficient alone.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/v1"):
            try:
                from routers.api_v1 import _cors_headers

                for k, v in _cors_headers(request.headers.get("origin", "")).items():
                    response.headers[k] = v
            except Exception:
                pass
        return response


app.add_middleware(OriginCheckMiddleware)
app.add_middleware(AddinCORSMiddleware)

# When frozen by PyInstaller (the bundled .exe), __file__ points into the temporary
# extraction dir; templates/ and static/ are shipped as bundle datas at the bundle root
# (sys._MEIPASS). Otherwise resolve relative to this source file as normal.
import sys as _sys
if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
    BASE_DIR = Path(_sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ── Rendered course sites ────────────────────────────────────────────────────
# Static Quarto sites are served directly by the dashboard: no extra process,
# no port to remember, no server to start. (The statistics course is the
# exception — it is an Express APP, not a static site, so it keeps its own
# port 3000 and a redirect. See routers/learning.py::course_reader_page.)
#
# Registered by slug so a course card's Open button can point at
# /coursesite/<slug>/ and be guaranteed to land on the real course.
# Paths are DERIVED, never absolute. A hardcoded home directory is both a
# personal-data leak on a public repo and an instant break on the second
# computer. METIS_COURSE_SITES_ROOT overrides; the default walks up from the
# repo to the sibling Education folder, the same relative shape run.sh uses.
# NOTE the double .parent (fixed 2026-09-02). "9. Education" is a sibling of
# "7. Software", NOT of the repo — the repo lives at
# <docs>/7. Software/Research Cortex, so reaching <docs> takes two steps up, not
# one. With a single .parent this resolved to "7. Software/9. Education", which
# does not exist, the mount was skipped with a log.warning nobody reads, and the
# HAT Diagnostics launch button 404'd while its _site/ sat rendered on disk.
# A path that silently resolves to nothing is worse than a hardcoded one.
_EDU_ROOT = Path(
    os.environ.get("METIS_COURSE_SITES_ROOT")
    or (Path(os.environ.get("METIS_RC_ROOT", BASE_DIR.parent.parent)).parent.parent
        / "9. Education")
)

COURSE_SITES: dict[str, Path] = {
    "hat-diagnostics": _EDU_ROOT / "3. HAT Diagnostics" / "Course"
                                 / "hat-diagnostics-course" / "_site",
    "hat-history":     _EDU_ROOT / "4. HAT History" / "Course"
                                 / "hat-history-course" / "_site",
}
for _slug, _dir in COURSE_SITES.items():
    if _dir.is_dir():
        app.mount(f"/coursesite/{_slug}",
                  StaticFiles(directory=str(_dir), html=True),
                  name=f"coursesite-{_slug}")
    else:
        # Loud, because a skipped mount renders as a 404 on a launch button and
        # nothing else says so. tools/check_course_launch.py is the real guard.
        log.error("COURSE SITE NOT MOUNTED — launch button will 404: %s -> %s "
                  "(check the path derivation and that the site is rendered)",
                  _slug, _dir)


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── `| md` — render stored markdown in a template ────────────────────────────
# Focus-area overviews are authored as markdown and stored as text, so the
# surface needs to render them. `markdown` is already a dependency (the course
# reader in routers/learning.py uses it); this exposes it once, globally, rather
# than each router converting its own strings and returning HTML.
#
# `| safe` is still required at the call site: the filter converts markdown, it
# does not assert the input was trustworthy. Only content the user authored
# should ever be passed through it.
def _md_filter(text: str) -> str:
    if not text:
        return ""
    try:
        import markdown as _mdlib
        return _mdlib.markdown(
            str(text), extensions=["fenced_code", "tables", "nl2br"])
    except Exception:
        # Never let a rendering dependency take a page down — show the source.
        from markupsafe import escape
        return f"<pre>{escape(str(text))}</pre>"


templates.env.filters["md"] = _md_filter


# ── The focus shelf, available to every render ───────────────────────────────
# base.html is the layout for every page, so the navbar needs the active shelf on
# every request. Registered as a GLOBAL CALLABLE rather than passed per-route:
# threading it through ~30 route handlers would mean any new route silently loses
# the shelf, which is the "control that depends on being remembered" pattern this
# project keeps paying for.
#
# One indexed query on a table with at most a handful of rows. Fails to an empty
# list — a missing navbar section is a far better outcome than a 500 on every page.
def _focus_shelf() -> list:
    try:
        from db import db_query
        # `n_new` is a STORED count, written when a focus's lens is scanned and
        # cleared when the focus is opened. It is read here rather than computed
        # because this runs on every page render and the lens itself is a
        # dozen LIKE terms over ~4,000 rows — 19-29 ms per focus, measured.
        return [dict(r) for r in (db_query(
            "SELECT slug, title, subtitle, shelf_slot, "
            "       COALESCE(n_new, 0) AS n_new "
            "FROM focus_areas "
            "WHERE state = 'active' ORDER BY COALESCE(shelf_slot, 99)") or [])]
    except Exception:
        return []


templates.env.globals["focus_shelf"] = _focus_shelf


# ── Shared template globals across EVERY environment ─────────────────────────
# A "template global" is not global here. This app builds SEVENTEEN separate
# Jinja2Templates instances — main.py plus one per router — and each has its own
# `env`. Registering `focus_shelf` on main's environment made the navbar work on
# every page main renders and threw `UndefinedError: 'focus_shelf' is undefined`
# on /news, which routers/today.py renders from its own instance. A 500, not a
# missing section.
#
# So shared globals get installed on all of them, from one place, after the
# routers are imported. The alternative — remembering to register on each new
# router's instance — is the same defect this project keeps paying for.
def _asset_version() -> str:
    """A cache-busting stamp derived from the assets themselves.

    It was hand-typed: `styles.css?v=14`, `app.js?v=9m`. A number you have to
    remember to change is a number that does not change — every edit shipped
    behind a stamp last touched weeks earlier, so a browser holding
    `styles.css?v=14` kept serving it and the tab showed an old Metis no matter
    how often the dashboard restarted. That is the literal "old version still
    open in my browser".

    Content hash rather than mtime, because this repository syncs through
    OneDrive across two machines and mtimes there are not trustworthy — see the
    two-computer rules. Cheap: two small files, read once per process start.
    """
    import hashlib
    h = hashlib.sha256()
    for name in ("styles.css", "app.js"):
        f = BASE_DIR / "static" / name
        try:
            h.update(f.read_bytes())
        except OSError:
            h.update(name.encode())          # missing file still yields a stamp
    return h.hexdigest()[:10]


ASSET_V = _asset_version()

import re as _re

_SHARED_GLOBALS = {"focus_shelf": _focus_shelf, "asset_v": ASSET_V}
def _due_delta(due: str):
    """Days from today to `due`, or None if there is no usable date.

    Returns None rather than 0 for an empty value — a task with no date is not
    due today, it is undated, and collapsing those two is exactly how 69 open
    tasks came to be shown as overdue.
    """
    import datetime as _d
    if not due:
        return None
    try:
        return (_d.date.fromisoformat(str(due)[:10]) - _d.date.today()).days
    except Exception:
        return None


def _clip(text, n: int = 120, ellipsis: str = "…"):
    """The Jinja filter. One implementation, in ui.py — templates and routers
    both truncate, and two copies of this rule would drift."""
    from ui import clip
    return clip(text, n, ellipsis)


# Scholarly titles legitimately contain inline markup: 113 records in one test
# library carried `<i>` around a species name, because that is how a genus and
# species are written and it is what Crossref returns. Auto-escaping printed the
# tags literally, so a title read "...reservoir hosts of &lt;i&gt;Genus
# species&lt;/i&gt; in ..." — and `striptags` would throw the italics away,
# losing real meaning rather than rendering it.
#
# So: escape EVERYTHING, then re-enable exactly six inline tags. A tag with any
# attribute cannot come back, because escaping turns `<i class=…>` into
# `&lt;i class=…&gt;` and the pattern below requires `&gt;` immediately after
# the tag name. Feed and Crossref text is untrusted, so this stays a strict
# allowlist and never `|safe`.
_SCI_ALLOWED = ("i", "em", "b", "strong", "sub", "sup")
_SCI_RE = _re.compile(r"&lt;(/?)(" + "|".join(_SCI_ALLOWED) + r")&gt;", _re.IGNORECASE)


def _sci(text):
    """Render a title's inline scientific markup, and nothing else."""
    from markupsafe import Markup, escape
    if text is None:
        return ""
    return Markup(_SCI_RE.sub(r"<\1\2>", str(escape(str(text)))))


# Feed SUMMARIES are a different problem from titles. A title's `<i>` is meaning
# (a genus and species), which is what `_sci` preserves. A summary's markup is
# junk the source shipped: of 3,947 stored summaries six carry tags, and they are
# `<img …>` and — worse — a stored `<untrusted_external_content>` injection-guard
# wrapper that the scanner wrote into the field. Escaped, those render as visible
# angle brackets in a digest row; kept, they are markup from an untrusted source.
# Both are wrong, so prose gets them removed.
# `[^>]*`, not `[^>]{0,200}`. The bound was meant as a backtracking guard and
# was simply wrong: one feed ships an <img> whose alt text is a whole paragraph,
# so the tag ran past 200 characters, the pattern did not match, and the markup
# rendered as visible text in the digest — the exact thing this filter exists to
# stop. `[^>]` cannot match `>`, so the unbounded form is linear and needs no
# guard. Measured: 115 of 3,947 stored summaries carry literal tags, not the 6
# an earlier, tighter count reported.
_PROSE_TAG_RE = _re.compile(r"<[^>]*>")
# AND THE TAG THAT NEVER CLOSES. The news scanner stores raw feed HTML cut to a
# length, and 115 of 3,947 summaries therefore END inside a tag — one <img>
# whose alt text is a whole paragraph is cut at 767 characters with no `>`
# anywhere after it. A tag pattern cannot match an unclosed tag, so the markup
# reached the reader however tight the pattern was. Whatever follows a final
# unmatched `<` is a fragment of markup, not prose, so it goes.
_PROSE_OPEN_RE = _re.compile(r"<[^>]*$")
_PROSE_WARN_RE = _re.compile(r"\[INJECTION WARNING\][^\n]*", _re.IGNORECASE)


def _prose(text, n: int = 0, ellipsis: str = "…"):
    """Plain prose from an untrusted feed: no tags, no guard banners, escaped.

    IT TRUNCATES TOO, and that is not a convenience — it is the fix for a real
    defect. Chained as `| prose | clip(120)` this returned safe Markup, `clip`
    handed back a plain str, and Jinja escaped it a SECOND time, so a stripped
    `<img>` reappeared in the page as the literal text `&amp;lt;img`. Doing both
    steps here keeps the order right (strip, then cut) and returns Markup once.

    Cutting after stripping also matters on its own: cut first and a tag can be
    severed into `<img alt="x`, which no longer matches a tag pattern and ships
    to the reader as visible markup.
    """
    from markupsafe import escape
    if text is None:
        return ""
    t = _PROSE_TAG_RE.sub(" ", str(text))
    t = _PROSE_OPEN_RE.sub(" ", t)
    t = _PROSE_WARN_RE.sub("", t)
    t = " ".join(t.split())
    if n and len(t) > n:
        cut = t[:n].rsplit(" ", 1)[0] or t[:n]
        t = cut.rstrip(" ,;:.") + ellipsis
    return escape(t)


_SHARED_FILTERS = {"md": _md_filter,
                   "due_delta": _due_delta,
                   "clip": _clip,
                   "sci": _sci,
                   "prose": _prose}




def install_shared_globals() -> int:
    """Make the shared globals/filters reach EVERY Jinja environment, now and later.

    Two mechanisms, because one is not enough:

    1. `jinja2.defaults.DEFAULT_NAMESPACE` / `DEFAULT_FILTERS`. Jinja copies these
       into every Environment it constructs, so anything registered here is
       inherited by environments created AFTER this call — a router imported
       lazily, a module reloaded, a test that builds its own. Verified against
       jinja2 3.1.6, including via Starlette's `Jinja2Templates`.

    2. A walk over environments that already exist, since those were constructed
       before step 1 ran and cannot inherit retroactively.

    Step 1 is the one that matters, and it was missing from the first version.
    That version walked existing environments only, which made correctness depend
    on this function running AFTER every environment was built — an ordering
    assumption held only by luck. The full test suite broke it immediately: four
    router environments (knowledge, learning, planner, thinking) existed as second
    instances created later and silently lacked every shared global. In production
    the ordering happened to hold, so the defect would have surfaced the first time
    a router was imported lazily. "It works if it runs last" is the same
    remember-to-do-it dependency this whole mechanism exists to remove.

    Returns the number of already-existing environments updated.
    """
    import sys as _sys

    try:
        from jinja2 import defaults as _jinja_defaults
        _jinja_defaults.DEFAULT_NAMESPACE.update(_SHARED_GLOBALS)
        _jinja_defaults.DEFAULT_FILTERS.update(_SHARED_FILTERS)
    except Exception as _exc:  # pragma: no cover
        log.warning("Could not seed Jinja defaults (%s) — falling back to a "
                    "walk of existing environments only", _exc)

    seen, n = set(), 0
    for name, mod in list(_sys.modules.items()):
        if not (name == "__main__" or name == "main" or name.startswith("routers.")):
            continue
        for attr in ("templates", "_TEMPLATES"):
            env = getattr(getattr(mod, attr, None), "env", None)
            if env is None or id(env) in seen:
                continue
            seen.add(id(env))
            env.globals.update(_SHARED_GLOBALS)
            env.filters.update(_SHARED_FILTERS)
            n += 1
    return n


# ── Global error handler — catch unhandled 500s so the dashboard never shows a
# blank page or drops the connection silently. HTMX partials get a styled error
# snippet; full page requests get a redirect to root with an error toast.
@app.exception_handler(500)
async def _handle_500(request: Request, exc: Exception):
    log.error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
    # HTMX partial requests: return an error snippet the page can display
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            '<div class="panel panel-pad" role="alert" '
            'style="margin:12px 0;border-left:3px solid var(--m-alert);">'
            "Something went wrong loading this section — I'll try again in a moment."
            '</div>',
            status_code=200,  # 200 so HTMX swaps it into the page
        )
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'><title>Metis</title></head>"
        "<body style=\"font-family:'Newsreader',Georgia,serif;background:#f5f2ea;"
        "color:#2c3a33;max-width:560px;margin:80px auto;padding:0 24px;line-height:1.65;\">"
        "<h3 style='font-weight:500;color:#1f2a24;'>Something went wrong loading this view.</h3>"
        "<p>The page hit an error and couldn&#39;t render. Nothing was lost — "
        "try again, or return to the dashboard.</p>"
        "<p><a href='/' style='color:#2d4a3a;'>Back to dashboard</a></p>"
        "</body></html>",
        status_code=500,
    )

# The user's name, in every template.
#
# It said "every template" and reached ONE environment. Measured 2026-08-24: with
# `_metis_user_name` registered only here, `/news` served
# `window.METIS_USER_NAME = "Researcher"` and an avatar initial of "R" while every
# other surface served "the researcher" and "S" — because /news is rendered from
# routers/today.py's own Jinja instance, not this one.
#
# It did not 500 only because base.html guards the call with `is defined`. So the
# failure was invisible: the personalisation silently fell back on exactly the
# surfaces that did not come through main. Registering it in _SHARED_GLOBALS below
# is what makes "every template" true.
try:
    from routers.today import _user_name as _get_metis_user_name
except Exception:
    def _get_metis_user_name() -> str:
        return "Researcher"

templates.env.globals["_metis_user_name"] = _get_metis_user_name
_SHARED_GLOBALS["_metis_user_name"] = _get_metis_user_name

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------

# Tab routers — all live under /tab prefix for the full-page variants;
# the partials/api routes are registered without prefix via the router itself.
app.include_router(today.router)
app.include_router(knowledge.router)
app.include_router(new_literature.router)
app.include_router(meetings.router)
app.include_router(learning.router)
app.include_router(work.router)
app.include_router(thinking.router)
app.include_router(planner.router)
app.include_router(calendar_plan.router)
app.include_router(teach.router)
app.include_router(metis_tab.router)
app.include_router(memory_health.router)
app.include_router(capture.router, prefix="/api")
# JSON API for non-Claude clients (Office, scripts). Carries its own /api/v1
# prefix and its own bearer-token auth — see routers/api_v1.py on why the
# dashboard's Origin check is necessary but not sufficient here.
app.include_router(api_v1.router)
app.include_router(connections.router)
app.include_router(transcription.router)
app.include_router(speakers.router)
app.include_router(jobs.router)
app.include_router(setup.router)
# The citation checker's HTTP surface — the Stop hook calls this rather than
# shelling out to Python, so a per-turn check costs milliseconds against an
# already-warm process instead of an interpreter start on every reply.
app.include_router(verification.router)
# Focus areas — user-added surfaces. One router and one template serve
# every focus, which is what makes them addable without a developer.
app.include_router(focus.router)
# READING STACK — the triage store Today feeds and the /stack surface drains.
app.include_router(stack.router)
# LIBRARY SHELVES — the reason something was kept, which the stack's `saved`
# verdict recorded without ever being able to say.
app.include_router(shelves.router)

# Must run AFTER all routers are imported, so every environment exists.
_n_envs = install_shared_globals()
log.info("Shared template globals installed on %d Jinja environment(s)", _n_envs)

# ── PWA capture page — standalone mobile-friendly route ─────────────────────
@app.get("/capture", response_class=HTMLResponse)
async def pwa_capture_page(request: Request):
    """Standalone capture page — add to phone home screen for one-tap access."""
    return templates.TemplateResponse(request, "capture.html", {})

@app.get("/manifest.json")
async def pwa_manifest():
    from fastapi.responses import JSONResponse
    return JSONResponse({
        "name": "Metis Capture",
        "short_name": "Capture",
        "description": "Capture ideas, notes, tasks, and questions for your Research Cortex",
        "start_url": "/capture",
        "display": "standalone",
        "background_color": "#1a1a1a",
        "theme_color": "#3b82f6",
        "icons": [
            {"src": "/static/metis-icon.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/metis-icon.png", "sizes": "512x512", "type": "image/png"},
        ],
    })

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


@app.get("/health")
async def health():
    """Liveness AND data-layer health.

    This endpoint is the SOLE definition of "healthy" for the whole supervision
    chain — run.sh's adopt-don't-kill check, and the 5-minute Task Scheduler
    heartbeat (tools/metis-boot.sh). It used to return {"status": "ok"}
    unconditionally, without ever touching the database. So a corrupt or empty DB
    produced a dashboard rendering zeros everywhere while every supervisor happily
    reported "nothing to do" — the 2026-06-19 corruption mode, made invisible.

    Touch the DB. If the data layer is gone, we are NOT healthy, and supervision
    must be told so it can act instead of adopting a hollow server.
    """
    # Query SQLite directly. Do NOT use db_query/db_scalar here: they catch
    # OperationalError (including "disk image is malformed") and return a default,
    # which would report a corrupt database as perfectly healthy — the very failure
    # this check exists to catch.
    import sqlite3

    from db import get_db_path

    try:
        conn = sqlite3.connect(f"file:{get_db_path()}?mode=ro", uri=True, timeout=5)
        try:
            tables = conn.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
        finally:
            conn.close()
        if not tables:
            raise sqlite3.DatabaseError("database has no tables (empty or wiped)")
    except Exception as e:
        log.error("health: data layer unhealthy — %s: %s", type(e).__name__, e)
        return JSONResponse(
            {"status": "unhealthy", "reason": "database", "error": type(e).__name__},
            status_code=503,
        )
    return JSONResponse({"status": "ok"})


@app.post("/api/restart")
async def restart_dashboard(request: Request):
    """Restart the dashboard process. Returns 202 immediately; server comes back in ~3 s.

    Requires ``X-Metis-Confirm: restart`` header to prevent accidental or
    CSRF-driven restarts.
    """
    if request.headers.get("X-Metis-Confirm") != "restart":
        return JSONResponse({"error": "confirmation header required"}, status_code=403)

    import threading, os, sys

    def _do_restart():
        import time
        time.sleep(0.6)  # Let the HTTP response be sent first
        os.execv(sys.executable, [sys.executable] + sys.argv)

    threading.Thread(target=_do_restart, daemon=False, name="restart").start()
    return JSONResponse({"status": "restarting"}, status_code=202)


# Surfaces that were merged into another surface — old URLs redirect so bookmarks
# and refreshes don't 404. Planner became the "Board" view of Work (2026-07-14).
_TAB_ALIASES = {"planner": "/work"}

# Surfaces whose full page needs server-side context, not just the HTMX shell.
# Keyed the same as _TAB_TEMPLATES; the value is called with no arguments and
# must return a dict. Add an entry when a template renders anything inline.
_TAB_CONTEXT = {
    "learning": lambda: learning._learning_context("learning"),
}


@app.get("/{tab}", response_class=HTMLResponse)
async def tab_page(request: Request, tab: str):
    if tab in _TAB_ALIASES:
        return RedirectResponse(url=_TAB_ALIASES[tab], status_code=302)
    template_name = _TAB_TEMPLATES.get(tab)
    if template_name is None:
        return RedirectResponse(url="/", status_code=302)

    # ── The context the surface's OWN router builds ────────────────────────
    # This route used to pass {"active_tab": tab} and nothing else, while the
    # matching /tab/<name> route passed the router's full context. Any content
    # rendered INLINE in the template — as opposed to arriving later over HTMX —
    # therefore saw undefined variables on the full page and real ones inside
    # the app shell. Jinja renders an undefined as empty and falsy, so it failed
    # silently and looked like an empty state.
    #
    # Found 2026-08-31 on /learning: the 14-day streak strip is inline, so the
    # full page drew fourteen blank cells and the caption "No reviews yet" while
    # 234 cards were overdue. Nothing errored; it simply told the truth about a
    # context that was never passed.
    #
    # A router opts in by exposing `page_context()`. Nothing else changes, and a
    # router without one behaves exactly as before.
    ctx = {"active_tab": tab}
    provider = _TAB_CONTEXT.get(tab)
    if provider is not None:
        try:
            ctx.update(provider())
        except Exception as exc:                       # never 500 a whole surface
            log.warning("tab %s: page_context failed: %s", tab, exc)
    return templates.TemplateResponse(request, template_name, ctx)


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

    label = f"{count} calls today" if count else "Metis \u00b7 online"
    return HTMLResponse(
        f'<i class="bi {policy_icon} {policy_cls}"></i>'
        f'<span class="trust-badge-text">{label}</span>'
    )


@app.get("/api/session/touch-planning")
async def touch_planning_files():
    """Append last-session timestamp to active project PLANNING.md files.

    Called by the stop hook at session end. Queries active projects with an
    external_path, finds PLANNING.md there, and appends a dated marker line
    (idempotent — no duplicate markers on the same day).
    """
    import json
    from pathlib import Path as _Path

    today = str(datetime.date.today())
    marker = f"\n\n---\n_Last Metis session: {today}_\n"
    updated = []

    try:
        from db import db_query

        rows = db_query(
            "SELECT project_id, title, external_path FROM projects "
            "WHERE status = 'active' AND external_path IS NOT NULL AND external_path != ''"
        )
        for row in rows:
            ext = (row.get("external_path") or "").strip()
            if not ext:
                continue
            planning = _Path(ext) / "PLANNING.md"
            if planning.exists():
                content = planning.read_text(encoding="utf-8")
                if f"_Last Metis session: {today}_" not in content:
                    planning.write_text(content + marker, encoding="utf-8")
                    updated.append(str(planning))
    except Exception:
        pass

    return JSONResponse({"updated": updated, "date": today})


# ---------------------------------------------------------------------------
# MCP server status — used by the offline banner in base.html
# ---------------------------------------------------------------------------

def _read_mcp_health() -> dict:
    """Best-effort read of the LIVE MCP server's last startup health snapshot.

    server.py::_startup_selfcheck writes system/config/mcp-health.json from the
    process Claude actually talks to (its real FAILED_MODULES + stale-install flag).
    Surfacing it lets the badge show "N tools failed" / "stale — reconnect" instead
    of only "is the package importable" — which is computed in THIS process and
    can't see what failed in the server (Keystone P0.6b / N11).
    """
    try:
        import json as _json
        rc_root = os.environ.get("METIS_RC_ROOT", "")
        base = Path(rc_root) if rc_root else Path(__file__).resolve().parent.parent.parent
        hp = base / "system" / "config" / "mcp-health.json"
        if not hp.is_file():
            return {}
        data = _json.loads(hp.read_text(encoding="utf-8"))
        failed = data.get("modules_failed") or {}
        names = list(failed.keys()) if isinstance(failed, dict) else []
        return {
            "health": data.get("status", "unknown"),
            "modules_failed": len(names),
            "failed_names": names,
            "stale_install": bool(data.get("stale_install")),
            "checked_at": data.get("checked_at", ""),
        }
    except Exception:
        return {}


@app.get("/api/mcp/status")
async def mcp_status():
    """Returns 200 if the metis_mcp package is importable (i.e. venv is active).

    Also folds in the live server's last health snapshot (modules_failed /
    stale_install) so the badge can show a degraded state, not just online/offline.
    """
    import sys
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        mcp_src = str(Path(rc_root) / "system" / "mcp-server" / "src")
        if mcp_src not in sys.path:
            sys.path.insert(0, mcp_src)
    # Clear a broken partial import — a module with no __file__ is a sign of a failed load
    mod = sys.modules.get("metis_mcp")
    if mod is not None and not getattr(mod, "__file__", None):
        del sys.modules["metis_mcp"]
    try:
        import metis_mcp  # noqa: F401
        return JSONResponse({"status": "ok", **_read_mcp_health()})
    except Exception as exc:
        return JSONResponse({"status": "offline", "reason": str(exc)}, status_code=503)


@app.post("/api/mcp/reload")
async def mcp_reload():
    """Try to connect to the MCP tools layer. Called by the Reconnect button."""
    import sys, importlib
    rc_root = os.environ.get("METIS_RC_ROOT", "")
    if rc_root:
        mcp_src = str(Path(rc_root) / "system" / "mcp-server" / "src")
        if mcp_src not in sys.path:
            sys.path.insert(0, mcp_src)
    try:
        # Force re-import in case a previous attempt left a broken partial import
        if "metis_mcp" in sys.modules:
            importlib.reload(sys.modules["metis_mcp"])
        else:
            import metis_mcp  # noqa: F401
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        return JSONResponse(
            {"status": "offline",
             "reason": "Metis tools couldn't load. Make sure you opened Metis using the desktop shortcut, then try again.",
             "detail": str(exc)},
            status_code=503,
        )
