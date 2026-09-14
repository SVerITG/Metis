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
