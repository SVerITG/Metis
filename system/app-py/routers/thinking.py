"""
routers/thinking.py — Thinking tab routes.
"""

import datetime
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ui import clip
from db import db_execute, db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/thinking", response_class=HTMLResponse)
async def thinking_tab(request: Request):
    return templates.TemplateResponse(
     request, "thinking.html", {"active_tab": "thinking"}
 )


@router.get("/api/tab/thinking", response_class=HTMLResponse)
async def thinking_tab_partial(request: Request):
    return templates.TemplateResponse(
     request, "thinking.html", {"active_tab": "thinking"}
 )


# ---------------------------------------------------------------------------
# Archive-layout partials
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/meta", response_class=HTMLResponse)
async def thinking_meta(request: Request):
    open_count = db_scalar("SELECT COUNT(*) FROM ideas WHERE tags NOT LIKE '%archived%'", default=0) or 0
    last_row = db_query("SELECT created_at FROM ideas ORDER BY created_at DESC LIMIT 1") or []
    last = last_row[0]["created_at"][:10] if last_row else "—"
    return HTMLResponse(f"{open_count} OPEN · LAST TOUCHED {last}")


@router.get("/api/partial/thinking/threads", response_class=HTMLResponse)
async def thinking_threads(request: Request):
    """The Open threads rail.

    The markup used to be assembled here as f-strings — inline styles, inline
    mouse handlers, no classes. It now lives in partials/thinking_threads.html;
    this function's job is to hand it data. See that file for why "OPEN" and the
    age colour ramp were dropped.
    """
    rows = db_query(
        "SELECT idea_id AS id, text AS content, tags, created_at FROM ideas "
        "WHERE tags NOT LIKE '%archived%' ORDER BY created_at DESC LIMIT 12"
    ) or []
    today = datetime.date.today()
    threads = []
    for r in rows:
        date_str = (r.get("created_at") or "")[:10]
        try:
            age = (today - datetime.date.fromisoformat(date_str)).days
        except Exception:
            age = None
        threads.append({
            "id": r.get("id"),
            "title": clip(r.get("content") or "", 45),
            "age": age,
        })
    return templates.TemplateResponse(
        request, "partials/thinking_threads.html", {"threads": threads}
    )


@router.get("/api/partial/thinking/dialogue", response_class=HTMLResponse)
async def thinking_dialogue(request: Request):
    ideas = db_query(
        "SELECT text AS content, created_at FROM ideas ORDER BY created_at DESC LIMIT 5"
    ) or []
    if not ideas:
        return HTMLResponse(
            '<div style="padding:24px 0;font-family:var(--m-display);font-style:italic;font-size:15px;color:var(--m-muted);text-align:center;">'
            'No ideas yet. Capture one with ⌘K.</div>'
        )
    items = ""
    for idea in ideas:
        content = clip(idea.get("content") or "", 300)
        date = (idea.get("created_at") or "")[:10]
        items += (
            f'<div style="padding:18px 0;border-bottom:1px solid var(--m-rule-soft);">'
            f'<div style="font-family:var(--m-display);font-size:15px;color:var(--m-text);line-height:1.6;">{content}</div>'
            f'<div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.14em;color:var(--m-muted);margin-top:8px;">{date}</div>'
            f'</div>'
        )
    return HTMLResponse(f'<div>{items}</div>')


@router.get("/api/partial/thinking/marginalia", response_class=HTMLResponse)
async def thinking_marginalia(request: Request):
    """The notes rail. Markup moved to partials/thinking_marginalia.html."""
    rows = db_query(
        "SELECT content, created_at FROM personal_notes ORDER BY created_at DESC LIMIT 4"
    ) or []
    notes = [{"content": clip(r.get("content") or "", 120),
              "date": (r.get("created_at") or "")[:10]} for r in rows]
    return templates.TemplateResponse(
        request, "partials/thinking_marginalia.html", {"notes": notes}
    )


# ---------------------------------------------------------------------------
# Ideas
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/ideas", response_class=HTMLResponse)
async def thinking_ideas(request: Request):
    ideas = db_query(
        "SELECT idea_id AS id, text AS content, tags, created_at "
        "FROM ideas ORDER BY created_at DESC LIMIT 30"
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_ideas.html",
        {
            "ideas": ideas
        },
    )


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/notes", response_class=HTMLResponse)
async def thinking_notes(request: Request):
    notes = db_query(
        "SELECT note_id AS id, content, tags, created_at "
        "FROM personal_notes ORDER BY created_at DESC LIMIT 20"
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_notes.html",
        {
            "notes": notes
        },
    )


# ---------------------------------------------------------------------------
# Open questions
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/questions", response_class=HTMLResponse)
async def thinking_questions(request: Request):
    questions = db_query(
        "SELECT idea_id AS id, text AS content, created_at "
        "FROM ideas WHERE tags LIKE '%question%' "
        "ORDER BY created_at DESC LIMIT 15"
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_questions.html",
        {
            "questions": questions
        },
    )


# ---------------------------------------------------------------------------
# Brainstorm sessions (Phase 8)
# ---------------------------------------------------------------------------


@router.get("/api/partial/thinking/brainstorm", response_class=HTMLResponse)
async def thinking_brainstorm(request: Request):
    """Brainstorm launcher — recent sessions plus invitation to start a new one."""
    sessions: list[dict] = []
    has_table = db_scalar(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='brainstorm_sessions'",
        default=None,
    )
    if has_table:
        # Pull the 3 most recent. Use sources_used as a proxy for "messages
        # exchanged" — older schemas don't have message_count.
        rows = db_query(
            "SELECT session_id, session_uuid, topic, summary, sources_used, "
            "created_at FROM brainstorm_sessions ORDER BY created_at DESC LIMIT 3",
            default=[],
        ) or []
        for r in rows:
            # Try a few possible companion tables for an accurate count
            sid = r.get("session_uuid") or r.get("session_id")
            msg_count = 0
            for tbl, col in (("brainstorm_turns", "session_uuid"),
                             ("brainstorm_turns", "session_id")):
                try:
                    n = db_scalar(
                        f"SELECT COUNT(*) FROM {tbl} WHERE {col} = ?",
                        (sid,),
                        default=0,
                    ) or 0
                    if n:
                        msg_count = n
                        break
                except Exception:
                    continue
            # Fall back to length of sources_used JSON list if no turns table
            if not msg_count:
                src = r.get("sources_used") or ""
                msg_count = src.count(",") + 1 if src else 0
            sessions.append({
                "session_uuid": r.get("session_uuid") or "",
                "topic": r.get("topic") or "Untitled brainstorm",
                "summary": clip(r.get("summary") or "", 160),
                "started_at": (r.get("created_at") or "")[:10],
                "message_count": msg_count,
            })
    return templates.TemplateResponse(
        request,
        "partials/thinking_brainstorm.html",
        {"sessions": sessions},
    )


@router.get("/api/partial/thinking/brainstorm-sessions", response_class=HTMLResponse)
async def thinking_brainstorm_sessions(request: Request):
    sessions = db_query(
        "SELECT bs.session_uuid, bs.title, bs.status, bs.started_at, bs.updated_at, "
        "COUNT(bt.id) as turn_count "
        "FROM brainstorm_sessions bs "
        "LEFT JOIN brainstorm_turns bt ON bs.session_uuid = bt.session_uuid "
        "GROUP BY bs.id ORDER BY bs.updated_at DESC LIMIT 10",
        default=[],
    )
    return templates.TemplateResponse(
        request,
        "partials/thinking_brainstorm_sessions.html",
        {"sessions": [dict(s) for s in (sessions or [])]},
    )


# ---------------------------------------------------------------------------
# Export latest idea as a personal note (Phase 9)
# ---------------------------------------------------------------------------


@router.post("/api/note/from-latest-idea")
async def note_from_latest_idea():
    rows = db_query(
        "SELECT idea_id AS id, text AS content FROM ideas ORDER BY created_at DESC LIMIT 1"
    ) or []
    if not rows:
        return JSONResponse(
            {"status": "empty", "message": "No ideas to export."},
            status_code=200,
        )
    idea = rows[0]
    content = idea.get("content") or ""
    now = datetime.datetime.now().isoformat()
    try:
        db_execute(
            "INSERT INTO personal_notes (content, tags, created_at) VALUES (?, ?, ?)",
            (content, "exported-from-idea", now),
        )
        return JSONResponse(
            {"status": "ok", "preview": content[:120], "source_idea_id": idea.get("id")}
        )
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"I couldn't save note: {e}"},
            status_code=500,
        )


# ---------------------------------------------------------------------------
# Idea mindmap — renders the user's ideas + idea_links as a clustered radial
# mindmap (themes as branches, ideas as leaves, links as cross-connections).
# Pure server-side SVG, no JS graph library.
# ---------------------------------------------------------------------------

_IDEA_TYPE_COLOR = {
    "research": "var(--m-accent)",
    "question": "#c98a2b",
    "note": "#8a8a8a",
    "method": "#3a8f7a",
    "literature": "#7a5ea8",
    "teaching": "#4a8f4a",
}


def _xml(s) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _mm_clean(text: str) -> str:
    t = (text or "").strip()
    # strip a leading "i: " / "q: " / "n: " marker
    if len(t) > 2 and t[1] == ":" and t[0].lower() in "iqnlm":
        t = t[2:].strip()
    return t


def _mm_label(text: str, n: int = 34) -> str:
    t = _mm_clean(text)
    return (t[: n - 1] + "…") if len(t) > n else t


def _build_mindmap_svg(ideas: list, links: list) -> str:
    """Ideas as a radial map, laid out so the labels can be read.

    WHAT WAS WRONG. Every domain got an equal angular share, and the sector each
    one could use was capped at 1.1 radians. With two domains — which is the real
    data, `ai-in-health-epidemiology` and `Other` — that put 28 ideas into 63
    degrees at a single radius. Every label was drawn on top of its neighbours,
    and the result was an illegible pile. Found by looking at a screenshot; the
    code reads as perfectly reasonable.

    Three changes, and the first is the one that matters:

      · A domain's angular share is PROPORTIONAL to how many ideas it holds. A
        branch with 28 gets most of the circle; a branch with 1 gets a sliver.
        Equal shares are only correct when the groups are equal.
      · Labels alternate between two radii, so neighbours are never on the same
        ring and cannot collide even when the arc is tight.
      · A branch is capped, with the remainder named rather than dropped. Past
        about eight labels on one arc nothing is readable at any radius, and a
        map that silently omits is worse than one that says "+14 more".
    """
    import math

    MAX_PER_BRANCH = 8
    W, H = 900, 620
    cx, cy = W / 2, H / 2
    R1 = 128                      # hub ring
    R_IN, R_OUT = 214, 262        # the two leaf rings labels alternate between

    groups: dict = {}
    for it in ideas:
        groups.setdefault((it.get("domain") or "Other"), []).append(it)
    # Biggest branch first, so the largest arc starts at the top where there is
    # the most room for a long label.
    domains = sorted(groups, key=lambda d: -len(groups[d]))
    if not domains:
        return ""

    shown = {d: groups[d][:MAX_PER_BRANCH] for d in domains}
    total = sum(len(shown[d]) for d in domains) or 1

    pos: dict = {}
    branch_svg, hub_svg, nodes_svg = [], [], []

    # Walk the circle handing each domain a slice sized by its own count.
    cursor = -math.pi / 2
    GAP = 0.16                                  # breathing room between branches
    free = 2 * math.pi - GAP * len(domains)

    for dom in domains:
        items = shown[dom]
        span = free * (len(items) / total)
        a = cursor + span / 2                   # the hub sits mid-slice
        hx, hy = cx + R1 * math.cos(a), cy + R1 * math.sin(a)

        branch_svg.append(
            f'<path d="M{cx:.0f},{cy:.0f} Q{(cx+hx)/2:.0f},{(cy+hy)/2:.0f} {hx:.0f},{hy:.0f}" '
            f'fill="none" stroke="var(--m-rule-strong)" stroke-width="1"/>')
        anchor = "start" if math.cos(a) >= 0 else "end"
        hub_svg.append(f'<circle cx="{hx:.0f}" cy="{hy:.0f}" r="3.5" fill="var(--m-ink)"/>')
        n_hidden = len(groups[dom]) - len(items)
        hub_label = _xml(dom.upper()) + (f"  +{n_hidden}" if n_hidden else "")
        hub_svg.append(
            f'<text x="{hx + (6 if anchor=="start" else -6):.0f}" y="{hy+3:.0f}" '
            f'text-anchor="{anchor}" font-family="var(--m-mono)" font-size="9" '
            f'fill="var(--m-ink)" letter-spacing="0.04em">{hub_label}</text>')

        k = len(items)
        for ii, it in enumerate(items):
            # Spread across the slice, inset so the first and last are not on
            # the seam with the neighbouring branch.
            frac = 0.5 if k == 1 else (ii + 0.5) / k
            ia = cursor + span * frac
            R2 = R_IN if ii % 2 == 0 else R_OUT
            ix, iy = cx + R2 * math.cos(ia), cy + R2 * math.sin(ia)
            pos[it.get("idea_id")] = (ix, iy)
            branch_svg.append(
                f'<path d="M{hx:.0f},{hy:.0f} Q{(hx+ix)/2:.0f},{(hy+iy)/2:.0f} {ix:.0f},{iy:.0f}" '
                f'fill="none" stroke="var(--m-rule)" stroke-width="1"/>')
            color = _IDEA_TYPE_COLOR.get(it.get("idea_type") or "", "var(--m-accent)")
            ianchor = "start" if math.cos(ia) >= 0 else "end"
            lx = ix + (9 if ianchor == "start" else -9)
            nodes_svg.append(
                f'<circle cx="{ix:.0f}" cy="{iy:.0f}" r="5" fill="{color}">'
                f'<title>{_xml(_mm_clean(it.get("text","")))}</title></circle>')
            nodes_svg.append(
                f'<text x="{lx:.0f}" y="{iy+3:.0f}" text-anchor="{ianchor}" '
                f'font-family="var(--m-display)" font-size="11" fill="var(--m-text)">'
                f'{_xml(_mm_label(it.get("text","")))}</text>')
        cursor += span + GAP

    link_svg = []
    for ln in links:
        a_id, b_id = ln.get("idea_id_a"), ln.get("idea_id_b")
        if a_id in pos and b_id in pos:
            x1, y1 = pos[a_id]
            x2, y2 = pos[b_id]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ctrlx, ctrly = mx + (cx - mx) * 0.30, my + (cy - my) * 0.30
            link_svg.append(
                f'<path d="M{x1:.0f},{y1:.0f} Q{ctrlx:.0f},{ctrly:.0f} {x2:.0f},{y2:.0f}" '
                f'fill="none" stroke="var(--m-accent)" stroke-width="1.1" '
                f'stroke-dasharray="3 3" opacity="0.55">'
                f'<title>{_xml(ln.get("link_label",""))}</title></path>')

    center_svg = (
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="26" fill="var(--m-surface-2)" '
        f'stroke="var(--m-rule-strong)" stroke-width="1"/>'
        f'<text x="{cx:.0f}" y="{cy-1:.0f}" text-anchor="middle" font-family="var(--m-mono)" '
        f'font-size="8.5" fill="var(--m-muted)" letter-spacing="0.1em">MY</text>'
        f'<text x="{cx:.0f}" y="{cy+9:.0f}" text-anchor="middle" font-family="var(--m-mono)" '
        f'font-size="8.5" fill="var(--m-muted)" letter-spacing="0.1em">IDEAS</text>'
    )

    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:100%;height:auto;display:block;" '
        f'role="img" aria-label="Your open ideas, grouped by domain">'
        + "".join(branch_svg) + "".join(link_svg) + "".join(hub_svg) + center_svg
        + "".join(nodes_svg) + "</svg>"
    )


@router.get("/api/partial/thinking/mindmap", response_class=HTMLResponse)
async def thinking_mindmap(request: Request):
    """Render the user's ideas + idea_links as a clustered mindmap (SVG)."""
    ideas = db_query(
        "SELECT idea_id, text, domain, idea_type, tags FROM ideas "
        "ORDER BY created_at DESC LIMIT 24"
    ) or []
    try:
        links = db_query("SELECT idea_id_a, idea_id_b, link_label FROM idea_links") or []
    except Exception:
        links = []
    if not ideas:
        return HTMLResponse(
            '<p style="color:var(--m-muted);font-style:italic;font-family:var(--m-display);'
            'font-size:13px;margin:0;">No ideas captured yet — capture a few and they\'ll map here.</p>')
    svg = _build_mindmap_svg(ideas, links)
    legend_items = [
        ("research", "var(--m-accent)"), ("question", "#c98a2b"), ("method", "#3a8f7a"),
        ("note", "#8a8a8a"), ("literature", "#7a5ea8"), ("teaching", "#4a8f4a"),
    ]
    legend = (
        '<div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;padding-top:10px;'
        'border-top:1px solid var(--m-rule-soft);font-family:var(--m-mono);font-size:8.5px;'
        'letter-spacing:0.08em;color:var(--m-muted);">'
        + "".join(
            f'<span style="display:inline-flex;align-items:center;gap:5px;">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{c};display:inline-block;"></span>'
            f'{k.upper()}</span>'
            for k, c in legend_items)
        + '<span style="display:inline-flex;align-items:center;gap:5px;">'
        '<span style="width:14px;border-top:1.5px dashed var(--m-accent);display:inline-block;"></span>'
        'CONNECTION</span></div>'
    )
    return HTMLResponse(svg + legend)


# ---------------------------------------------------------------------------
# Graphify Knowledge Analysis
# ---------------------------------------------------------------------------

# Type → dot colour (matches Archive palette)
_GRAPHIFY_TYPE_COLORS = {
    "paper": "var(--m-accent)",
    "idea": "#c98a2b",
    "project": "#3a8f7a",
    "task": "#8a8a8a",
    "meeting": "#7a5ea8",
    "concept": "#4a8f4a",
    "journal": "#b05a5a",
    "session": "#6a7f9a",
    "corpus": "#9a7a5a",
    "memory": "#5a7a9a",
    "knowledge": "var(--m-muted)",
}


def _rc_root() -> Path:
    return Path(os.environ.get("METIS_RC_ROOT", ""))


def _graphify_bin() -> str | None:
    """Find the graphify CLI binary."""
    found = shutil.which("graphify")
    if found:
        return found
    # Fallback to known pipx location
    pipx_path = Path.home() / ".local" / "bin" / "graphify"
    return str(pipx_path) if pipx_path.exists() else None


def _graphify_python() -> str | None:
    """Find the pipx Python with graphify installed."""
    p = Path.home() / ".local" / "share" / "pipx" / "venvs" / "graphifyy" / "bin" / "python3"
    return str(p) if p.exists() else None


def _graphify_out(rc: Path) -> Path:
    """Path to the Graphify output directory."""
    return rc / "graphify-out"


def _run_analytics(rc: Path) -> dict:
    """Run the analytics script and return parsed JSON."""
    graph_json = _graphify_out(rc) / "graph.json"
    if not graph_json.exists():
        return {"graph_exists": False}

    script = rc / "tools" / "graphify_analytics.py"
    if not script.exists():
        return {"graph_exists": True, "error": "Analytics script not found"}

    # Use system python — the script uses only stdlib (json, pathlib, collections)
    try:
        result = subprocess.run(
            ["python3", str(script), str(graph_json)],
            capture_output=True, text=True, timeout=30,
            cwd=str(rc),
        )
        if result.returncode != 0:
            return {"graph_exists": True, "error": result.stderr[:200]}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"graph_exists": True, "error": "Analytics timed out"}
    except Exception as e:
        return {"graph_exists": True, "error": str(e)[:200]}


@router.get("/api/partial/thinking/graphify-analytics", response_class=HTMLResponse)
async def thinking_graphify_analytics(request: Request):
    """Render the Graphify knowledge analytics panel."""
    rc = _rc_root()
    data = _run_analytics(rc)

    # How OLD is this analysis? (2026-09-02) The panel printed a build date and
    # nothing else, so a snapshot from eleven weeks earlier looked exactly like
    # one from this morning — and the "Rebuild & view" button re-exports the
    # source markdown but SKIPS the graph step whenever graph.json already
    # exists, then reports success. So pressing it changed nothing and said it
    # had. Naming the age is the smallest honest fix; `stale` drives the warning.
    age_days = None
    try:
        gj = _graphify_out(rc) / "graph.json"
        if gj.is_file():
            import time as _t
            age_days = int((_t.time() - gj.stat().st_mtime) // 86400)
    except Exception:
        age_days = None

    ctx = {
        "graph_exists": data.get("graph_exists", False),
        "built_at": data.get("built_at", ""),
        "age_days": age_days,
        "stale": age_days is not None and age_days > 14,
        "error": data.get("error", ""),
        "stats": data.get("stats", {}),
        "god_nodes": data.get("god_nodes", []),
        "surprising": data.get("surprising", []),
        "communities": data.get("communities", []),
        "type_colors": _GRAPHIFY_TYPE_COLORS,
    }
    return templates.TemplateResponse(
        request, "partials/thinking_graphify.html", ctx
    )


def _rebuild_graphify(rc: Path) -> dict:
    """Run the export + graphify update pipeline. Blocking — call via to_thread."""
    import time
    t0 = time.time()
    errors = []

    # Step 1: Export SQLite → markdown files
    export_script = rc / "tools" / "export_knowledge_graph.py"
    if export_script.exists():
        try:
            r = subprocess.run(
                ["python3", str(export_script)],
                capture_output=True, text=True, timeout=60,
                cwd=str(rc),
            )
            if r.returncode != 0:
                errors.append(f"Export: {r.stderr[:200]}")
        except subprocess.TimeoutExpired:
            errors.append("Export timed out (60s)")
    else:
        errors.append("Export script not found")

    # Step 2: If no graph exists yet, run graphify update (AST-only, free).
    # If the graph already exists, skip the slow rebuild — just use it as-is.
    # Full rebuilds can be triggered via terminal: graphify update .
    gout = rc / "graphify-out"
    if not (gout / "graph.json").exists():
        gbin = _graphify_bin()
        if gbin:
            try:
                r = subprocess.run(
                    [gbin, "update", "."],
                    capture_output=True, text=True, timeout=300,
                    cwd=str(rc),
                )
                if r.returncode != 0 and not (gout / "graph.json").exists():
                    errors.append(f"Graphify: {r.stderr[:200]}")
            except subprocess.TimeoutExpired:
                errors.append("Graphify update timed out — run `graphify update .` from terminal")
        else:
            errors.append("Graphify binary not found — install with: pip install graphifyy")

    duration = round(time.time() - t0, 1)

    # Check result
    gout = _graphify_out(rc)
    graph_html = gout / "graph.html"
    graph_json = gout / "graph.json"

    if errors:
        return {"status": "error", "message": "; ".join(errors), "duration": duration}

    stats = {}
    if graph_json.exists():
        try:
            with open(graph_json) as f:
                g = json.load(f)
            stats["nodes"] = len(g.get("nodes", []))
            stats["edges"] = len(g.get("links", []))
        except Exception:
            pass

    return {
        "status": "ok",
        "duration": duration,
        "has_html": graph_html.exists(),
        **stats,
    }


@router.post("/api/thinking/graphify-rebuild")
async def thinking_graphify_rebuild():
    """Run export + graphify update pipeline. Returns JSON status."""
    import asyncio
    rc = _rc_root()
    if not rc or not rc.exists():
        return JSONResponse(
            {"status": "error", "message": "METIS_RC_ROOT not set"},
            status_code=500,
        )
    result = await asyncio.to_thread(_rebuild_graphify, rc)
    status_code = 200 if result["status"] == "ok" else 500
    return JSONResponse(result, status_code=status_code)


@router.get("/api/graphify/view")
async def graphify_view():
    """Serve the interactive graph.html file."""
    rc = _rc_root()
    graph_html = _graphify_out(rc) / "graph.html"
    if not graph_html.exists():
        return HTMLResponse(
            "<h2>No graph available</h2>"
            "<p>Click <em>Graphify my knowledge</em> on the Reflection surface to build one.</p>",
            status_code=404,
        )
    return FileResponse(
        str(graph_html),
        media_type="text/html",
        filename="graphify-knowledge-graph.html",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# REFLECTION — ideas, notes, threads
# ═══════════════════════════════════════════════════════════════════════════════
# Asked for on 2026-09-13: "value boxes for Ideas, notes and threads and they show
# the amount and last worked on them ... when you click on ideas its a specific
# site for recording ideas ... when 'Notes' is selected there should be a specific
# journalling app ... 'Threads' is like i explained you before".
#
# WHY THE SURFACE READ AS FLAT. It was not a layout problem. `thinking/threads`
# and `thinking/dialogue` both selected from `ideas` — the rail and the centre
# panel were two views of one table, so "thread" and "idea" could not mean
# different things however they were labelled.
#
# So a thread is now a DISTINCT KIND rather than a second rendering: an `ideas`
# row with `idea_type='thread'`. That follows the pattern this codebase already
# set for focus questions (`idea_type='question'`) instead of adding a table, and
# it means a thread the researcher later stops pursuing still surfaces in idea
# search rather than disappearing into a store nothing else reads.
#
# ARCHIVE is a tag, not a delete. Nothing on this surface is ever removed.

THREAD_KIND = "thread"
ARCHIVE_TAG = "archived"

# Words too common to link on. A link store built on "research" and "analysis"
# connects everything to everything, which is the failure the whole thread-scoped
# graph exists to avoid.
_STOP = {
    "about", "after", "again", "against", "because", "been", "before", "being",
    "between", "both", "could", "does", "doing", "down", "during", "each",
    "from", "further", "have", "having", "here", "into", "itself", "just",
    "more", "most", "only", "other", "over", "same", "should", "some", "such",
    "than", "that", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "under", "until", "very", "what", "when", "where",
    "which", "while", "with", "would", "your", "make", "made", "much", "also",
    "like", "well", "need", "want", "work", "thing", "things", "something",
    "research", "analysis", "study", "data", "paper", "note", "idea",
}


def _terms(text: str, cap: int = 8) -> list[str]:
    """The words worth linking on, longest first — specificity beats frequency."""
    import re as _re
    words = {w for w in _re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", (text or "").lower())
             if w not in _STOP}
    return sorted(words, key=len, reverse=True)[:cap]


def _last_touched(sql: str, params=()) -> str:
    row = db_query(sql, params, default=[]) or []
    return (row[0].get("t") or "")[:10] if row else ""


def _reflection_boxes() -> list[dict]:
    """The three counts, each with when it was last worked on.

    "the amount and last worked on them" — both, because a count alone cannot
    tell you whether a pile is growing or abandoned.
    """
    live = f"COALESCE(tags,'') NOT LIKE '%{ARCHIVE_TAG}%'"
    n_ideas = db_scalar(
        f"SELECT COUNT(*) FROM ideas WHERE {live} "
        f"AND COALESCE(idea_type,'') != '{THREAD_KIND}'", default=0) or 0
    n_threads = db_scalar(
        f"SELECT COUNT(*) FROM ideas WHERE {live} "
        f"AND COALESCE(idea_type,'') = '{THREAD_KIND}'", default=0) or 0
    n_notes = (db_scalar("SELECT COUNT(*) FROM personal_notes", default=0) or 0) \
        + (db_scalar("SELECT COUNT(*) FROM journal_entries", default=0) or 0)

    last_note = max(
        _last_touched("SELECT MAX(COALESCE(updated_at, created_at)) AS t FROM personal_notes"),
        _last_touched("SELECT MAX(created_at) AS t FROM journal_entries"))
    return [
        {"key": "ideas", "label": "Ideas", "n": n_ideas,
         "note": "exploration of thoughts",
         "last": _last_touched(
             f"SELECT MAX(created_at) AS t FROM ideas WHERE {live} "
             f"AND COALESCE(idea_type,'') != '{THREAD_KIND}'")},
        {"key": "notes", "label": "Notes", "n": n_notes,
         "note": "the journal",
         "last": last_note},
        {"key": "threads", "label": "Threads", "n": n_threads,
         "note": "lines of enquiry, with their sources",
         "last": _last_touched(
             f"SELECT MAX(created_at) AS t FROM ideas WHERE {live} "
             f"AND COALESCE(idea_type,'') = '{THREAD_KIND}'")},
    ]


@router.get("/api/partial/reflection/boxes", response_class=HTMLResponse)
async def reflection_boxes(request: Request):
    return templates.TemplateResponse(
        request, "partials/reflection_boxes.html", {"boxes": _reflection_boxes()})


# ── Ideas: a place to record and re-read thoughts ────────────────────────────
@router.get("/api/partial/reflection/ideas", response_class=HTMLResponse)
async def reflection_ideas(request: Request):
    rows = db_query(
        f"SELECT idea_id AS id, text, COALESCE(tags,'') AS tags, created_at, "
        f"       COALESCE(project_id,'') AS project_id, "
        f"       COALESCE(idea_type,'idea') AS kind "
        f"FROM ideas WHERE COALESCE(tags,'') NOT LIKE '%{ARCHIVE_TAG}%' "
        f"AND COALESCE(idea_type,'') != '{THREAD_KIND}' "
        f"ORDER BY created_at DESC LIMIT 60", default=[]) or []
    return templates.TemplateResponse(
        request, "partials/reflection_ideas.html", {"ideas": rows})


@router.post("/api/reflection/idea", response_class=HTMLResponse)
async def reflection_add_idea(request: Request):
    form = await request.form()
    text = (form.get("text") or "").strip()
    if text:
        db_execute(
            "INSERT INTO ideas (idea_id, text, idea_type, created_at) VALUES (?,?,?,?)",
            (f"idea-{uuid.uuid4().hex[:12]}", text, "idea",
             datetime.datetime.now().isoformat(timespec="seconds")))
    return await reflection_ideas(request)


# ── Notes: the journal ───────────────────────────────────────────────────────
@router.get("/api/partial/reflection/journal", response_class=HTMLResponse)
async def reflection_journal(request: Request):
    """One dated stream, from the two stores that hold the researcher's own writing.

    `journal_entries` and `personal_notes` are kept apart in the database for a
    reason — an entry carries a mood and an energy score, a note carries a title
    and a project — but on screen they are the same act on two different days,
    and splitting them would mean remembering which panel a thought went into.
    Each row says which store it came from, so nothing is silently merged.
    """
    entries = db_query(
        "SELECT entry_id AS id, content, COALESCE(mood,'') AS mood, "
        "       COALESCE(energy_score,0) AS energy, COALESCE(summary,'') AS summary, "
        "       created_at, 'journal' AS store, '' AS title "
        "FROM journal_entries ORDER BY created_at DESC LIMIT 40", default=[]) or []
    notes = db_query(
        "SELECT note_id AS id, content, '' AS mood, 0 AS energy, '' AS summary, "
        "       COALESCE(updated_at, created_at) AS created_at, 'note' AS store, "
        "       COALESCE(title,'') AS title "
        "FROM personal_notes ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 40",
        default=[]) or []
    stream = sorted(entries + notes,
                    key=lambda r: (r.get("created_at") or ""), reverse=True)[:50]

    # Grouped by day, because a journal is read by day. The template renders the
    # heading once per date rather than stamping every entry.
    days: list[dict] = []
    for r in stream:
        d = (r.get("created_at") or "")[:10]
        if not days or days[-1]["date"] != d:
            days.append({"date": d, "items": []})
        days[-1]["items"].append(r)
    return templates.TemplateResponse(
        request, "partials/reflection_journal.html",
        {"days": days, "n": len(stream)})


@router.post("/api/reflection/journal", response_class=HTMLResponse)
async def reflection_add_journal(request: Request):
    form = await request.form()
    text = (form.get("content") or "").strip()
    mood = (form.get("mood") or "").strip()
    if text:
        db_execute(
            "INSERT INTO journal_entries (entry_id, content, mood, created_at) "
            "VALUES (?,?,?,?)",
            (f"jrn-{uuid.uuid4().hex[:12]}", text, mood,
             datetime.datetime.now().isoformat(timespec="seconds")))
    return await reflection_journal(request)


# ── Threads: a line of enquiry, and what it touches ──────────────────────────
# THE GRAPH PROBLEM, AND WHY THIS IS THE ANSWER.
#
# "graphify doesnt make sense because its too much information, should be
# smaller" (2026-09-13), with the good question attached: how do Obsidian and
# NotebookLM do this? They reached the same answer from opposite directions.
# Obsidian never draws the whole vault by default — its local graph shows ONE
# note and its neighbours at a chosen depth. NotebookLM draws no graph at all: it
# answers a question and lists the sources it used, which is a neighbour list in
# different clothes.
#
# The shared lesson is that the graph needs a QUERY, and a thread is one. So the
# picture here is never of everything: open a thread and you see that thread and
# what it touches, one hop out. A graph of everything is a picture of nothing.
#
# Sources are found by vocabulary and CONFIRMED BY THE READER. A suggestion is
# not a link — `knowledge_links` only gains a row when the thread is told to keep
# one, which is what keeps the picture worth looking at a month later.

# The stores a thread can reach, and how to read each one. Adding a store here is
# the whole change — the search, the link list and the graph all walk this table,
# so they cannot come to disagree about what a thread is allowed to touch.
THREAD_SOURCES = [
    ("news",    "News",       "news_briefs",         "brief_id", "title",
     "COALESCE(brief_date,'')", "source_url"),
    ("paper",   "Literature", "literature_metadata", "id",       "title",
     "COALESCE(year,'')",       "url"),
    ("pub",     "New papers", "new_publications",    "id",       "title",
     "COALESCE(pub_iso, pub_date, '')", "source_url"),
    ("note",    "Notes",      "personal_notes",      "note_id",  "content",
     "COALESCE(updated_at, created_at)", "''"),
    ("meeting", "Meetings",   "meetings",            "meeting_id", "title",
     "COALESCE(meeting_date,'')", "''"),
    ("project", "Projects",   "projects",            "project_id", "title",
     "COALESCE(created_at,'')", "''"),
]
_SRC_BY_KIND = {s[0]: s for s in THREAD_SOURCES}


def _thread_row(thread_id: str) -> dict | None:
    rows = db_query(
        "SELECT idea_id AS id, text, COALESCE(tags,'') AS tags, created_at "
        "FROM ideas WHERE idea_id = ?", (thread_id,), default=[]) or []
    return rows[0] if rows else None


def _thread_links(thread_id: str) -> list[dict]:
    """The links the reader kept, resolved back to titles they can open."""
    rows = db_query(
        "SELECT link_id, target_type AS kind, target_id, "
        "       COALESCE(link_label,'') AS label, created_at "
        "FROM knowledge_links WHERE source_type = 'thread' AND source_id = ? "
        "ORDER BY created_at DESC", (thread_id,), default=[]) or []
    out = []
    for r in rows:
        src = _SRC_BY_KIND.get(r["kind"])
        if not src:
            continue
        _k, label, table, idcol, titlecol, datecol, urlcol = src
        hit = db_query(
            f"SELECT {titlecol} AS title, {datecol} AS dated, {urlcol} AS url "
            f"FROM {table} WHERE {idcol} = ?", (r["target_id"],), default=[]) or []
        if not hit:
            # The row is gone but the link is not a lie — say so rather than
            # dropping it, or the count above the list stops matching the list.
            out.append({**r, "label_kind": label, "title": "(no longer in the library)",
                        "dated": "", "url": "", "missing": True})
            continue
        out.append({**r, "label_kind": label, "title": clip(hit[0]["title"] or "", 110),
                    "dated": (hit[0]["dated"] or "")[:10],
                    "url": hit[0]["url"] or "", "missing": False})
    return out


def _thread_suggestions(text: str, have: set, limit_per: int = 4) -> list[dict]:
    """What this thread's words also appear in, across every store it can reach.

    Ranked by how many of the thread's terms a row matches, so a row sharing
    three words outranks one sharing a single common word. Rows already linked
    are dropped — a suggestion you have already accepted is noise.
    """
    terms = _terms(text)
    if not terms:
        return []
    out = []
    for kind, label, table, idcol, titlecol, datecol, urlcol in THREAD_SOURCES:
        score = " + ".join([f"(CASE WHEN LOWER({titlecol}) LIKE ? THEN 1 ELSE 0 END)"
                            for _ in terms])
        params = tuple(f"%{t}%" for t in terms)
        rows = db_query(
            f"SELECT {idcol} AS target_id, {titlecol} AS title, "
            f"       {datecol} AS dated, {urlcol} AS url, ({score}) AS hits "
            f"FROM {table} WHERE ({score}) > 0 "
            f"ORDER BY hits DESC, {datecol} DESC LIMIT ?",
            params + params + (limit_per * 3,), default=[]) or []
        kept = 0
        for r in rows:
            if (kind, str(r["target_id"])) in have:
                continue
            out.append({"kind": kind, "label_kind": label,
                        "target_id": str(r["target_id"]),
                        "title": clip(r["title"] or "", 110),
                        "dated": (r["dated"] or "")[:10],
                        "url": r["url"] or "", "hits": r["hits"]})
            kept += 1
            if kept >= limit_per:
                break
    out.sort(key=lambda r: -r["hits"])
    return out[:18]


@router.get("/api/partial/reflection/threads", response_class=HTMLResponse)
async def reflection_threads(request: Request, thread: str = ""):
    rows = db_query(
        f"SELECT idea_id AS id, text, created_at FROM ideas "
        f"WHERE COALESCE(idea_type,'') = '{THREAD_KIND}' "
        f"AND COALESCE(tags,'') NOT LIKE '%{ARCHIVE_TAG}%' "
        f"ORDER BY created_at DESC LIMIT 40", default=[]) or []
    threads = [{"id": r["id"], "title": clip(r["text"] or "", 70),
                "dated": (r["created_at"] or "")[:10]} for r in rows]
    active = thread or (threads[0]["id"] if threads else "")
    return templates.TemplateResponse(
        request, "partials/reflection_threads.html",
        {"threads": threads, "active": active})


def _thread_detail(thread_id: str) -> dict | None:
    row = _thread_row(thread_id)
    if not row:
        return None
    links = _thread_links(thread_id)
    have = {(l["kind"], str(l["target_id"])) for l in links}
    by_kind: dict[str, list] = {}
    for l in links:
        by_kind.setdefault(l["label_kind"], []).append(l)
    return {
        "thread": {"id": row["id"], "text": row["text"],
                   "dated": (row["created_at"] or "")[:10]},
        "links": links,
        "by_kind": by_kind,
        "suggestions": _thread_suggestions(row["text"] or "", have),
        "terms": _terms(row["text"] or ""),
        "graph": _thread_graph(links),
    }


# The picture: one hop, laid out here rather than in the browser.
#
# Server-side because the layout is deterministic — N nodes on a circle — and a
# force simulation would spend a frame budget arriving at an arrangement that is
# already known. It also means the graph is in the HTML: it prints, it survives
# JavaScript being slow, and there is no library to pin.
GRAPH_W, GRAPH_H, GRAPH_R = 460, 300, 112


def _thread_graph(links: list[dict]) -> dict:
    """Node positions for the thread and its kept links, one hop out."""
    import math
    cx, cy = GRAPH_W / 2, GRAPH_H / 2
    n = len(links)
    nodes = []
    for i, l in enumerate(links):
        # Start at the top and go clockwise, so adding a link moves the picture
        # predictably instead of reshuffling it.
        a = (-math.pi / 2) + (2 * math.pi * i / n) if n else 0.0
        # Slight squash: the box is wider than it is tall, and a true circle
        # wastes the sides while crowding the top.
        nodes.append({
            "x": round(cx + GRAPH_R * 1.45 * math.cos(a), 1),
            "y": round(cy + GRAPH_R * 0.92 * math.sin(a), 1),
            "kind": l["kind"], "label_kind": l["label_kind"],
            "title": l["title"], "url": l["url"],
        })
    return {"w": GRAPH_W, "h": GRAPH_H, "cx": cx, "cy": cy, "nodes": nodes,
            "n": n}


@router.get("/api/partial/reflection/thread/{thread_id}", response_class=HTMLResponse)
async def reflection_thread(request: Request, thread_id: str):
    detail = _thread_detail(thread_id)
    if not detail:
        return HTMLResponse("")
    return templates.TemplateResponse(
        request, "partials/reflection_thread.html", detail)


@router.post("/api/reflection/thread", response_class=HTMLResponse)
async def reflection_add_thread(request: Request):
    form = await request.form()
    text = (form.get("text") or "").strip()
    new_id = ""
    if text:
        new_id = f"thr-{uuid.uuid4().hex[:12]}"
        db_execute(
            "INSERT INTO ideas (idea_id, text, idea_type, created_at) VALUES (?,?,?,?)",
            (new_id, text, THREAD_KIND,
             datetime.datetime.now().isoformat(timespec="seconds")))
    return await reflection_threads(request, thread=new_id)


@router.post("/api/reflection/thread/{thread_id}/link", response_class=HTMLResponse)
async def reflection_link(request: Request, thread_id: str):
    form = await request.form()
    kind = (form.get("kind") or "").strip()
    target_id = (form.get("target_id") or "").strip()
    drop = (form.get("drop") or "") == "1"
    if kind in _SRC_BY_KIND and target_id:
        if drop:
            db_execute(
                "DELETE FROM knowledge_links WHERE source_type='thread' "
                "AND source_id=? AND target_type=? AND target_id=?",
                (thread_id, kind, target_id))
        else:
            # Idempotent: the same suggestion can be clicked twice on a stale
            # panel, and a duplicated edge would double a count on the graph.
            n = db_scalar(
                "SELECT COUNT(*) FROM knowledge_links WHERE source_type='thread' "
                "AND source_id=? AND target_type=? AND target_id=?",
                (thread_id, kind, target_id), default=0) or 0
            if not n:
                db_execute(
                    "INSERT INTO knowledge_links (source_type, source_id, "
                    "target_type, target_id, link_label, created_at) "
                    "VALUES ('thread',?,?,?,'',?)",
                    (thread_id, kind, target_id,
                     datetime.datetime.now().isoformat(timespec="seconds")))
    return await reflection_thread(request, thread_id)


# ── Archive ──────────────────────────────────────────────────────────────────
@router.post("/api/reflection/archive", response_class=HTMLResponse)
async def reflection_archive_item(request: Request):
    """Archiving appends a tag. Nothing on this surface is ever deleted."""
    form = await request.form()
    idea_id = (form.get("idea_id") or "").strip()
    restore = (form.get("restore") or "") == "1"
    row = _thread_row(idea_id) if idea_id else None
    if row:
        tags = [t for t in (row["tags"] or "").split(",") if t.strip()]
        tags = [t for t in tags if t.strip() != ARCHIVE_TAG]
        if not restore:
            tags.append(ARCHIVE_TAG)
        db_execute("UPDATE ideas SET tags = ? WHERE idea_id = ?",
                   (",".join(tags), idea_id))
    back = (form.get("back") or "").strip()
    if back == "threads":
        return await reflection_threads(request)
    if back == "archive":
        return await reflection_archive(request)
    return await reflection_ideas(request)


@router.get("/api/partial/reflection/archive", response_class=HTMLResponse)
async def reflection_archive(request: Request):
    rows = db_query(
        f"SELECT idea_id AS id, text, created_at, "
        f"       COALESCE(idea_type,'idea') AS kind "
        f"FROM ideas WHERE COALESCE(tags,'') LIKE '%{ARCHIVE_TAG}%' "
        f"ORDER BY created_at DESC LIMIT 100", default=[]) or []
    return templates.TemplateResponse(
        request, "partials/reflection_archive.html",
        {"items": rows, "n_thread": sum(1 for r in rows if r["kind"] == THREAD_KIND)})


# ═══════════════════════════════════════════════════════════════════════════════
# FOCUS — is your attention where you said it matters?
# ═══════════════════════════════════════════════════════════════════════════════
# A knowledge graph of everything is a picture of nothing; that lesson is already
# recorded in the thread view above. This answers a different question, and it is
# the one worth drawing: not "what is connected to what" but "what have I
# actually been touching, and is it the work I committed to".
#
# HOW IT READS. You are the centre. Every ring outward is more time since the
# thing was last touched. A commitment drifting to the outer rings is the finding
# — and so is the inverse, which is easier to miss: when the things nearest you
# are TOPICS (subjects you follow) rather than COMMITMENTS (projects, courses,
# the subjects you chose to track), your attention has slid from doing to reading.
#
# EVERY POSITION IS EVIDENCE, NOT A GUESS. Each kind has one signal, named on
# screen, and a thing with no signal is drawn as unplaced rather than parked at
# the rim — "never touched" and "touched long ago" are different facts and only
# one of them is a drift.
#
#   project   the last working session on it, or the last time one of its tasks moved
#   course    the last time its progress changed
#   subject   the last time you opened it        (a focus area IS attention)
#   topic     the last paper or brief you read that names it
#
# Layout is computed here rather than simulated in the browser: rings and arcs
# are deterministic, so a force layout would spend frames arriving somewhere
# already known. It also means the picture prints and pins no library.

FOCUS_BANDS = [
    (2,   "today"),
    (7,   "this week"),
    (30,  "this month"),
    (90,  "this quarter"),
    (10**6, "longer ago"),
]
FOCUS_W, FOCUS_H = 640, 460
FOCUS_R0, FOCUS_R1 = 46, 196          # innermost and outermost ring radius

# A commitment untouched for longer than this is drifting. Thirty days is one
# reporting cycle — long enough that a quiet fortnight is not an alarm, short
# enough that a quarter has not passed unnoticed.
DRIFT_DAYS = 30


def _days_since(stamp: str) -> int | None:
    if not stamp:
        return None
    try:
        d = datetime.date.fromisoformat(str(stamp)[:10])
    except ValueError:
        return None
    return max(0, (datetime.date.today() - d).days)


def _band_of(days: int | None) -> int:
    if days is None:
        return len(FOCUS_BANDS)          # unplaced
    for i, (cap, _label) in enumerate(FOCUS_BANDS):
        if days <= cap:
            return i
    return len(FOCUS_BANDS) - 1


def _focus_entities() -> list[dict]:
    """Everything that competes for attention, with the date it last had some."""
    out: list[dict] = []

    # ── Projects ────────────────────────────────────────────────────────────
    # Two signals, and the LATER wins: a session is the stronger evidence, but a
    # task moving is evidence too, and a project worked on only through its task
    # list would otherwise look abandoned.
    #
    # BUT A BULK WRITE IS NOT ATTENTION, and this panel is worthless if it cannot
    # tell them apart. One value in this column — a bare date, no time — covers 51
    # tasks across 10 projects: a backfill. Taken at face value it dated ten
    # abandoned projects to that day and reported them as touched a month ago when
    # the last real session on several was three months back. The feature would
    # have UNDER-reported drift, which is precisely the opposite of its purpose.
    #
    # The rule is stated generally rather than against that date, because the next
    # migration will carry a different one: a timestamp shared across three or
    # more projects is a write event, not nine people sitting down to work at the
    # same instant.
    _shared = {r["u"] for r in db_query(
        "SELECT updated_at AS u, COUNT(DISTINCT COALESCE(project_id,'')) AS p "
        "FROM tasks WHERE COALESCE(updated_at,'') != '' "
        "GROUP BY updated_at HAVING p >= 3", default=[]) or []}
    task_touch: dict[str, str] = {}
    for r in db_query(
            "SELECT COALESCE(project_id,'') AS project_id, updated_at AS u "
            "FROM tasks WHERE COALESCE(updated_at,'') != ''", default=[]) or []:
        if r["u"] in _shared:
            continue
        pid = r["project_id"]
        if r["u"] > task_touch.get(pid, ""):
            task_touch[pid] = r["u"]
    for r in db_query(
            "SELECT project_id, title, COALESCE(status,'') AS status, "
            "       COALESCE(last_session_at,'') AS sess "
            "FROM projects WHERE COALESCE(status,'') IN ('active','in_progress')",
            default=[]) or []:
        stamp = max(r["sess"][:10], (task_touch.get(r["project_id"]) or "")[:10])
        out.append({"kind": "project", "label": r["title"],
                    "href": f"/work#{r['project_id']}",
                    "stamp": stamp, "commitment": True,
                    "why": "last working session, or a task moving"})

    # ── Courses ─────────────────────────────────────────────────────────────
    for r in db_query(
            "SELECT slug, title, COALESCE(updated_at,'') AS u FROM learning_courses "
            "WHERE status IN ('active','in_progress')", default=[]) or []:
        out.append({"kind": "course", "label": r["title"],
                    "href": "/tab/learning#" + r["slug"],
                    "stamp": r["u"][:10], "commitment": True,
                    "why": "the last time its progress changed"})

    # ── Subjects you chose to track ─────────────────────────────────────────
    for r in db_query(
            "SELECT slug, title, COALESCE(last_visited_at,'') AS v FROM focus_areas "
            "WHERE COALESCE(state,'') = 'active'", default=[]) or []:
        out.append({"kind": "subject", "label": r["title"],
                    "href": "/focus/" + r["slug"],
                    "stamp": r["v"][:10], "commitment": True,
                    "why": "the last time you opened it"})

    # ── Declared interests ──────────────────────────────────────────────────
    # A topic has no clock of its own — nothing writes to it. Its attention is
    # whatever you last READ that names it, which is the honest signal and the
    # one that makes the contrast meaningful: a topic near the centre while the
    # projects sit at the rim is reading instead of doing.
    for r in db_query("SELECT topic FROM user_topics", default=[]) or []:
        term = (r["topic"] or "").strip()
        if not term:
            continue
        like = f"%{term.lower()}%"
        stamps = [
            db_scalar("SELECT MAX(read_at) FROM new_publications "
                      "WHERE COALESCE(read_at,'') != '' AND LOWER(title) LIKE ?",
                      (like,), default="") or "",
            db_scalar("SELECT MAX(seen_at) FROM news_briefs "
                      "WHERE COALESCE(seen_at,'') != '' AND LOWER(title) LIKE ?",
                      (like,), default="") or "",
        ]
        out.append({"kind": "topic", "label": term, "href": "/news",
                    "stamp": max(s[:10] for s in stamps), "commitment": False,
                    "why": "the last paper or brief you read that names it"})

    for e in out:
        e["days"] = _days_since(e["stamp"])
        e["band"] = _band_of(e["days"])
    return out


def _focus_layout(entities: list[dict]) -> dict:
    """Rings and arcs. Grouped by kind so the picture can be read, not decoded."""
    import math
    cx, cy = FOCUS_W / 2, FOCUS_H / 2
    n_bands = len(FOCUS_BANDS)
    rings = [{"r": round(FOCUS_R0 + (FOCUS_R1 - FOCUS_R0) * i / (n_bands - 1), 1),
              "label": FOCUS_BANDS[i][1]} for i in range(n_bands)]

    # Each kind gets its own arc of the circle, so like sits beside like.
    order = ["project", "course", "subject", "topic"]
    placed = [e for e in entities if e["band"] < n_bands]
    unplaced = [e for e in entities if e["band"] >= n_bands]
    by_kind = {k: [e for e in placed if e["kind"] == k] for k in order}
    live = [k for k in order if by_kind[k]]

    nodes = []
    span = (2 * math.pi) / max(1, len(live))
    for ki, k in enumerate(live):
        group = sorted(by_kind[k], key=lambda e: (e["band"], e["label"]))
        arc0 = -math.pi / 2 + ki * span
        for i, e in enumerate(group):
            # Spread within the arc, insetting from its edges so neighbouring
            # kinds do not touch.
            frac = (i + 1) / (len(group) + 1)
            a = arc0 + span * (0.12 + 0.76 * frac)
            r = rings[e["band"]]["r"]
            nodes.append({**e,
                          "x": round(cx + r * 1.28 * math.cos(a), 1),
                          "y": round(cy + r * 0.92 * math.sin(a), 1)})
    return {"w": FOCUS_W, "h": FOCUS_H, "cx": cx, "cy": cy,
            "rings": rings, "nodes": nodes, "unplaced": unplaced}


def _focus_verdict(entities: list[dict]) -> dict:
    """The sentence the picture is for. Counts only; nothing is inferred."""
    commitments = [e for e in entities if e["commitment"]]
    topics = [e for e in entities if not e["commitment"]]
    drifting = [e for e in commitments
                if e["days"] is not None and e["days"] > DRIFT_DAYS]
    never = [e for e in commitments if e["days"] is None]

    # The inverse finding, and the one that is easy to miss: among everything
    # touched in the last week, are the topics outnumbering the commitments?
    recent_c = [e for e in commitments if e["days"] is not None and e["days"] <= 7]
    recent_t = [e for e in topics if e["days"] is not None and e["days"] <= 7]
    return {
        "n_commit": len(commitments), "n_topic": len(topics),
        "drifting": sorted(drifting, key=lambda e: -(e["days"] or 0)),
        "never": never,
        "recent_c": len(recent_c), "recent_t": len(recent_t),
        "reading_over_doing": len(recent_t) > len(recent_c) and bool(recent_t),
        "drift_days": DRIFT_DAYS,
    }


@router.get("/api/partial/reflection/focus", response_class=HTMLResponse)
async def reflection_focus(request: Request):
    ents = _focus_entities()
    return templates.TemplateResponse(
        request, "partials/reflection_focus.html",
        {"graph": _focus_layout(ents), "v": _focus_verdict(ents),
         "bands": FOCUS_BANDS})


# ═══════════════════════════════════════════════════════════════════════════════
# BRAINSTORM — choose the material, then go and think about it
# ═══════════════════════════════════════════════════════════════════════════════
# Asked for 2026-09-14. Three ways in, and the second half is the point:
#
#   wild      reflect on everything from the last month
#   project   one project, and what surrounds it
#   idea      one idea, and what it touches
#
# Then the material is SHOWN AND CHOSEN before the conversation starts, instead
# of a prompt telling Claude to "pull my context" and hoping. That difference is
# the whole feature: a brainstorm is only as good as what it has in front of it,
# and the researcher knows which five things matter better than a LIKE query does.
#
# WHY THE SELECTION IS EXPLICIT IN THE PROMPT. The old launcher said "first pull
# its context with your Metis tools". That is an instruction to go and look,
# which succeeds or fails silently depending on which tools happen to be loaded —
# the failure this codebase spent today diagnosing. Naming the chosen items in
# the prompt text means the conversation starts with them whether or not a single
# tool call works.

BRAINSTORM_WINDOW = 30          # days, for the "wild" mode
BRAINSTORM_CAP = 40             # candidates offered; more is a list nobody reads


def _bs_row(kind: str, rid: str, label: str, detail: str = "", when: str = "") -> dict:
    return {"kind": kind, "id": f"{kind}:{rid}", "label": clip(label or "", 90),
            "detail": clip(detail or "", 110), "when": (when or "")[:10]}


def _brainstorm_candidates(mode: str, ref: str = "") -> list[dict]:
    """The material this brainstorm could be built from."""
    out: list[dict] = []

    if mode == "wild":
        # Everything the last month actually contains. Not a summary of it — the
        # pieces, so a month can be re-read rather than remembered.
        since = (datetime.date.today()
                 - datetime.timedelta(days=BRAINSTORM_WINDOW)).isoformat()
        for r in db_query(
                "SELECT project_id, title, COALESCE(next_step,'') AS next_step, "
                "       COALESCE(last_session_at,'') AS w FROM projects "
                "WHERE COALESCE(status,'') IN ('active','in_progress') "
                "AND COALESCE(last_session_at,'') >= ? ORDER BY w DESC",
                (since,), default=[]) or []:
            out.append(_bs_row("project", r["project_id"], r["title"],
                               r["next_step"], r["w"]))
        for r in db_query(
                "SELECT idea_id, text, COALESCE(created_at,'') AS w FROM ideas "
                "WHERE COALESCE(created_at,'') >= ? ORDER BY w DESC LIMIT 14",
                (since,), default=[]) or []:
            out.append(_bs_row("idea", r["idea_id"], r["text"], "", r["w"]))
        for r in db_query(
                "SELECT note_id, COALESCE(title,'') AS t, content, "
                "       COALESCE(updated_at, created_at) AS w FROM personal_notes "
                "WHERE COALESCE(updated_at, created_at) >= ? ORDER BY w DESC LIMIT 8",
                (since,), default=[]) or []:
            out.append(_bs_row("note", r["note_id"], r["t"] or r["content"],
                               r["content"] if r["t"] else "", r["w"]))
        for r in db_query(
                "SELECT entry_id, content, created_at AS w FROM journal_entries "
                "WHERE created_at >= ? ORDER BY w DESC LIMIT 8",
                (since,), default=[]) or []:
            out.append(_bs_row("journal", r["entry_id"], r["content"], "", r["w"]))
        for r in db_query(
                "SELECT id, title, COALESCE(journal,'') AS j, read_at AS w "
                "FROM new_publications WHERE COALESCE(read_at,'') >= ? "
                "ORDER BY w DESC LIMIT 10", (since,), default=[]) or []:
            out.append(_bs_row("paper", str(r["id"]), r["title"], r["j"], r["w"]))
        for r in db_query(
                "SELECT meeting_id, title, COALESCE(meeting_date,'') AS w FROM meetings "
                "WHERE COALESCE(meeting_date,'') >= ? ORDER BY w DESC LIMIT 6",
                (since,), default=[]) or []:
            out.append(_bs_row("meeting", r["meeting_id"], r["title"], "", r["w"]))
        for r in db_query(
                "SELECT decision_id, decision, COALESCE(category,'') AS c, "
                "       COALESCE(created_at,'') AS w FROM user_decisions "
                "WHERE COALESCE(created_at,'') >= ? ORDER BY w DESC LIMIT 8",
                (since,), default=[]) or []:
            out.append(_bs_row("decision", str(r["decision_id"]), r["decision"],
                               r["c"], r["w"]))

    elif mode == "project" and ref:
        p = (db_query("SELECT project_id, title, COALESCE(next_step,'') AS n, "
                      "COALESCE(description,'') AS d FROM projects WHERE project_id = ?",
                      (ref,), default=[]) or [None])[0]
        if p:
            if p["n"]:
                out.append(_bs_row("next", p["project_id"], "Next step: " + p["n"]))
            for r in db_query(
                    "SELECT task_id, title, COALESCE(status,'') AS s, "
                    "       COALESCE(updated_at,'') AS w FROM tasks "
                    "WHERE project_id = ? AND COALESCE(status,'') NOT IN "
                    "('done','cancelled') ORDER BY w DESC LIMIT 12",
                    (ref,), default=[]) or []:
                out.append(_bs_row("task", r["task_id"], r["title"], r["s"], r["w"]))
            for r in db_query(
                    "SELECT idea_id, text, COALESCE(created_at,'') AS w FROM ideas "
                    "WHERE COALESCE(project_id,'') = ? ORDER BY w DESC LIMIT 10",
                    (ref,), default=[]) or []:
                out.append(_bs_row("idea", r["idea_id"], r["text"], "", r["w"]))
            for r in db_query(
                    "SELECT note_id, COALESCE(title,'') AS t, content, "
                    "       COALESCE(updated_at, created_at) AS w FROM personal_notes "
                    "WHERE COALESCE(project_id,'') = ? ORDER BY w DESC LIMIT 8",
                    (ref,), default=[]) or []:
                out.append(_bs_row("note", r["note_id"], r["t"] or r["content"],
                                   "", r["w"]))
            for r in db_query(
                    "SELECT run_id, agent_slug, COALESCE(task_summary,'') AS s, "
                    "       created_at AS w FROM agent_runs "
                    "WHERE COALESCE(task_summary,'') LIKE ? ORDER BY w DESC LIMIT 5",
                    (f"%{(p['title'] or '')[:24]}%",), default=[]) or []:
                out.append(_bs_row("run", str(r["run_id"]), r["s"], r["agent_slug"],
                                   r["w"]))
            out += _bs_matches(f"{p['title']} {p['d']}", exclude_idea="")

    elif mode == "idea" and ref:
        i = (db_query("SELECT idea_id, text, COALESCE(project_id,'') AS p "
                      "FROM ideas WHERE idea_id = ?", (ref,), default=[]) or [None])[0]
        if i:
            for r in db_query(
                    "SELECT idea_id, text, COALESCE(created_at,'') AS w FROM ideas "
                    "WHERE idea_id != ? ORDER BY w DESC LIMIT 60",
                    (ref,), default=[]) or []:
                if _bs_overlap(i["text"], r["text"]) >= 2:
                    out.append(_bs_row("idea", r["idea_id"], r["text"], "", r["w"]))
            if i["p"]:
                pr = (db_query("SELECT project_id, title, COALESCE(next_step,'') AS n "
                               "FROM projects WHERE project_id = ?", (i["p"],),
                               default=[]) or [None])[0]
                if pr:
                    out.append(_bs_row("project", pr["project_id"], pr["title"],
                                       pr["n"]))
            out += _bs_matches(i["text"], exclude_idea=ref)

    return out[:BRAINSTORM_CAP]


def _bs_overlap(a: str, b: str) -> int:
    """How many significant words two texts share. Cheap, and good enough to rank."""
    return len(set(_terms(a, cap=14)) & set(_terms(b, cap=14)))


def _bs_matches(text: str, exclude_idea: str = "") -> list[dict]:
    """Library and news that use this text's words.

    Suggestions, never links — the same rule the thread view follows. Nothing
    here enters a brainstorm unless it is ticked.
    """
    terms = _terms(text, cap=5)
    if not terms:
        return []
    out: list[dict] = []
    score = " + ".join(["(CASE WHEN LOWER(title) LIKE ? THEN 1 ELSE 0 END)"
                        for _ in terms])
    params = tuple(f"%{t}%" for t in terms)
    for r in db_query(
            f"SELECT id, title, COALESCE(journal,'') AS j, ({score}) AS hits "
            f"FROM literature_metadata WHERE ({score}) > 0 "
            f"ORDER BY hits DESC LIMIT 6", params + params, default=[]) or []:
        out.append(_bs_row("paper", str(r["id"]), r["title"], r["j"]))
    for r in db_query(
            f"SELECT brief_id, title, COALESCE(brief_date,'') AS w, ({score}) AS hits "
            f"FROM news_briefs WHERE ({score}) > 0 "
            f"ORDER BY hits DESC, brief_date DESC LIMIT 5", params + params,
            default=[]) or []:
        out.append(_bs_row("news", str(r["brief_id"]), r["title"], "", r["w"]))
    return out


# The instruction that makes it a brainstorm rather than an answer.
#
# "a kind of plan mode where she keeps asking you questions" (2026-09-14). The
# failure mode this exists to prevent is the ordinary one: a model handed rich
# context produces a confident synthesis in its first reply, the researcher reads
# it, agrees, and the thinking never happens. So the contract is explicit about
# the ORDER — understand, then diverge, then converge — and about the one rule
# that enforces it: no conclusions in the opening reply.
BRAINSTORM_MODE = """You are Metis, and this is a BRAINSTORM, not a request for an answer.

Work in three movements and say which one you are in:

1. UNDERSTAND — before proposing anything, ask me questions about the material
   below. One question at a time, and wait. Ask what I was actually trying to do,
   what I abandoned and why, what surprised me. Do not summarise the material
   back to me; I wrote it. Keep this up until you could argue my position better
   than I can.
2. DIVERGE — only then, put forward connections I have not made. Say plainly when
   something is a stretch. Surprising and wrong is more useful here than safe and
   obvious, provided you label which is which.
3. CONVERGE — at the end, and only when I ask: what would you do next, and what
   would change your mind.

Rules for this conversation:
- No conclusions in your first reply. A first reply that answers is a failed
  brainstorm.
- Ground everything in the material below and in my own library. Never invent a
  citation; if you reach for something I do not have, say so.
- If I go quiet or give a thin answer, ask a sharper question rather than filling
  the silence yourself.
- When we finish, offer to save the session and write anything worth keeping back
  into my ideas."""


@router.get("/api/partial/reflection/brainstorm", response_class=HTMLResponse)
async def reflection_brainstorm(request: Request, mode: str = "", ref: str = ""):
    """The launcher: three ways in, then the material to choose from."""
    mode = mode if mode in ("wild", "project", "idea") else ""
    # The pickers only when the mode needs one — a project brainstorm has to know
    # which project before it can propose anything.
    projects = idea_list = []
    if mode == "project":
        projects = db_query(
            "SELECT project_id, title FROM projects "
            "WHERE COALESCE(status,'') IN ('active','in_progress') ORDER BY "
            "COALESCE(last_session_at,'') DESC", default=[]) or []
    if mode == "idea":
        idea_list = db_query(
            f"SELECT idea_id, text FROM ideas "
            f"WHERE COALESCE(tags,'') NOT LIKE '%{ARCHIVE_TAG}%' "
            f"AND COALESCE(idea_type,'') != '{THREAD_KIND}' "
            f"ORDER BY created_at DESC LIMIT 40", default=[]) or []

    cands = _brainstorm_candidates(mode, ref) if mode else []
    return templates.TemplateResponse(
        request, "partials/reflection_brainstorm.html",
        {"mode": mode, "ref": ref, "projects": projects, "ideas": idea_list,
         "cands": cands, "chart": _bs_chart(cands),
         "window": BRAINSTORM_WINDOW})


# The chart is the same visual language as the Focus view — rings and shapes —
# but here the rings group by KIND rather than by time, because what you are
# choosing is a mixture, and seeing the mixture is the point: five papers and no
# notes is a different conversation from five notes and no papers.
BS_W, BS_H, BS_R = 520, 300, 108


def _bs_chart(cands: list[dict]) -> dict:
    import math
    cx, cy = BS_W / 2, BS_H / 2
    order = ["project", "next", "task", "idea", "note", "journal",
             "paper", "news", "meeting", "decision", "run"]
    present = [k for k in order if any(c["kind"] == k for c in cands)]
    nodes = []
    span = (2 * math.pi) / max(1, len(present))
    for ki, k in enumerate(present):
        group = [c for c in cands if c["kind"] == k]
        a0 = -math.pi / 2 + ki * span
        for i, c in enumerate(group):
            frac = (i + 1) / (len(group) + 1)
            a = a0 + span * (0.15 + 0.7 * frac)
            # Rings outward within a kind, so a long list stays readable instead
            # of piling every node onto one arc.
            r = BS_R * (0.62 + 0.38 * ((i % 3) / 2))
            nodes.append({**c,
                          "x": round(cx + r * 1.55 * math.cos(a), 1),
                          "y": round(cy + r * 0.95 * math.sin(a), 1)})
    return {"w": BS_W, "h": BS_H, "cx": cx, "cy": cy,
            "nodes": nodes, "kinds": present}


@router.post("/api/reflection/brainstorm/prompt", response_class=JSONResponse)
async def brainstorm_prompt(request: Request):
    """Assemble the prompt from what was actually ticked."""
    form = await request.form()
    mode = (form.get("mode") or "").strip()
    ref = (form.get("ref") or "").strip()
    picked = [p for p in (form.get("picked") or "").split("|") if p.strip()]
    level = (form.get("level") or "balanced").strip()

    lookup = {c["id"]: c for c in _brainstorm_candidates(mode, ref)}
    chosen = [lookup[p] for p in picked if p in lookup]

    if mode == "wild":
        head = (f"Let's think about everything I have done in the last "
                f"{BRAINSTORM_WINDOW} days. Not a summary — I want to find what I "
                f"missed while I was in it.")
    elif mode == "project":
        pr = (db_query("SELECT title FROM projects WHERE project_id = ?", (ref,),
                       default=[]) or [{}])
        head = (f"Let's brainstorm about my project "
                f"\"{(pr[0].get('title') if pr else ref)}\".")
    else:
        idea = (db_query("SELECT text FROM ideas WHERE idea_id = ?", (ref,),
                         default=[]) or [{}])
        head = (f"Let's brainstorm this idea of mine: "
                f"\"{(idea[0].get('text') if idea else ref)}\"")

    creativity = {
        "grounded": "Stay close to the evidence — feasible, well-supported connections.",
        "bold": "Push for surprising, cross-disciplinary connections; I will prune.",
    }.get(level, "Mix grounded connections with a few non-obvious ones.")

    lines = ["Metis — brainstorm mode.", "", head, "", creativity, "",
             BRAINSTORM_MODE, ""]
    if chosen:
        lines.append(f"## The material I have chosen ({len(chosen)} items)")
        lines.append("These are the pieces I want in front of us. Start here.")
        by_kind: dict[str, list] = {}
        for c in chosen:
            by_kind.setdefault(c["kind"], []).append(c)
        for k, items in by_kind.items():
            lines.append("")
            lines.append(f"### {k}")
            for c in items:
                bits = [c["label"]]
                if c["detail"]:
                    bits.append(c["detail"])
                if c["when"]:
                    bits.append(c["when"])
                lines.append("- " + " · ".join(bits))
        lines.append("")
        lines.append("You can pull more around these with your Metis tools, but "
                     "do not replace them — these are what I chose.")
    else:
        lines.append("I have not picked specific material. Use your Metis tools to "
                     "pull my recent projects, ideas, notes and reading first.")

    return JSONResponse({"status": "ok", "prompt": "\n".join(lines),
                         "n": len(chosen)})
