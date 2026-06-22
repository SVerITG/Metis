"""
routers/memory_health.py — Memory Health dashboard tab.

Shows memory system health: entry counts by layer, topic coverage,
agent wisdom accumulation, staleness, and project memory depth.
"""

import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import db_query, db_scalar

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)


@router.get("/tab/memory", response_class=HTMLResponse)
async def memory_tab(request: Request):
    return templates.TemplateResponse(
        request, "memory_health.html", {"active_tab": "memory"}
    )


@router.get("/api/tab/memory", response_class=HTMLResponse)
async def memory_tab_partial(request: Request):
    return templates.TemplateResponse(
        request, "memory_health.html", {"active_tab": "memory"}
    )


# ── Partials ──────────────────────────────────────────────────────────────


@router.get("/api/partial/memory/overview", response_class=HTMLResponse)
async def memory_overview(request: Request):
    """Summary cards for each memory layer."""
    layers = []

    # Memory palace
    palace = db_scalar(
        "SELECT COUNT(*) FROM memory_entries", default=0
    ) or 0
    layers.append({"name": "Memory Palace", "kicker": "CURATED", "count": palace,
                    "desc": "Entries you and Metis chose to keep"})

    # Episodic
    episodic = db_scalar(
        "SELECT COUNT(*) FROM episodic_memory", default=0
    ) or 0
    layers.append({"name": "Episodic", "kicker": "EVENTS", "count": episodic,
                    "desc": "What happened, and what was found"})

    # Semantic
    semantic = db_scalar(
        "SELECT COUNT(*) FROM semantic_memory", default=0
    ) or 0
    layers.append({"name": "Semantic", "kicker": "CONCEPTS", "count": semantic,
                    "desc": "Settled facts and understanding"})

    # Procedural
    procedural = db_scalar(
        "SELECT COUNT(*) FROM procedural_memory", default=0
    ) or 0
    layers.append({"name": "Procedural", "kicker": "PRACTICE", "count": procedural,
                    "desc": "How things are done here"})

    # Session summaries
    sessions = db_scalar(
        "SELECT COUNT(*) FROM session_summaries", default=0
    ) or 0
    layers.append({"name": "Sessions", "kicker": "CONVERSATIONS", "count": sessions,
                    "desc": "The record of each working session"})

    # Ideas
    ideas = db_scalar(
        "SELECT COUNT(*) FROM ideas", default=0
    ) or 0
    layers.append({"name": "Ideas", "kicker": "THREADS", "count": ideas,
                    "desc": "Thoughts captured for later"})

    # Reflexions
    reflexions = db_scalar(
        "SELECT COUNT(*) FROM reflexion_log", default=0
    ) or 0
    layers.append({"name": "Reflexions", "kicker": "SELF-REVIEW", "count": reflexions,
                    "desc": "Where the work could improve"})

    # Knowledge (indexed library)
    chunks = db_scalar(
        "SELECT COUNT(*) FROM pdf_chunks", default=0
    ) or 0
    layers.append({"name": "Library", "kicker": "INDEXED", "count": chunks,
                    "desc": "Passages from your reading, searchable"})

    total = sum(l["count"] for l in layers)

    cards = ""
    for l in layers:
        pct = round(l["count"] / total * 100, 1) if total > 0 else 0
        bar_color = "var(--m-accent)" if l["count"] > 0 else "var(--m-rule)"
        kick_color = "var(--m-accent)" if l["count"] > 0 else "var(--m-muted)"
        cards += f"""
        <div class="panel" style="padding:16px 18px;">
          <div style="display:flex;justify-content:space-between;align-items:baseline;">
            <span class="kicker" style="padding:0;color:{kick_color};">{l['kicker']}</span>
            <span class="tnum" style="font-family:var(--m-mono);font-size:18px;
                         font-weight:600;color:var(--m-ink);">{l['count']:,}</span>
          </div>
          <div style="font-family:var(--m-display);font-size:17px;font-weight:500;
                      letter-spacing:-0.01em;color:var(--m-ink);margin:8px 0 4px;">{l['name']}</div>
          <div style="font-family:var(--m-display);font-size:12.5px;color:var(--m-muted);
                      line-height:1.4;margin-bottom:12px;text-wrap:pretty;">{l['desc']}</div>
          <div style="height:3px;background:var(--m-rule-soft);border-radius:2px;overflow:hidden;">
            <div style="height:100%;width:{min(pct * 2, 100)}%;background:{bar_color};
                        border-radius:2px;transition:width 0.4s;"></div>
          </div>
        </div>"""

    return HTMLResponse(f"""
    <div class="grid grid-4" style="margin-bottom:14px;">
      {cards}
    </div>
    <div style="font-family:var(--m-mono);font-size:10px;letter-spacing:0.18em;
                text-transform:uppercase;color:var(--m-muted);text-align:right;">
      {total:,} entries held across every layer
    </div>
    """)


@router.get("/api/partial/memory/agents", response_class=HTMLResponse)
async def memory_agents(request: Request):
    """Agent wisdom accumulation — which agents have built up memory."""
    rows = db_query(
        """SELECT agent_id, scope, COUNT(*) as cnt
           FROM episodic_memory
           WHERE agent_id != '' AND agent_id IS NOT NULL
           GROUP BY agent_id
           ORDER BY cnt DESC LIMIT 20"""
    ) or []

    if not rows:
        return HTMLResponse(
            '<div class="sec-label" style="margin-bottom:14px;"><span>Where wisdom gathers</span>'
            '<span class="tail">BY SPECIALIST</span></div>'
            '<div class="ed" style="font-family:var(--m-display);font-style:italic;'
            'font-size:14px;color:var(--m-muted);">'
            'No specialist has built up memory yet. It accumulates quietly as the work gets done.</div>'
        )

    max_count = max(r["cnt"] for r in rows) if rows else 1
    items = ""
    for r in rows:
        pct = round(r["cnt"] / max_count * 100)
        items += f"""
        <div style="display:flex;align-items:center;gap:14px;padding:9px 0;
                    border-bottom:1px solid var(--m-rule-soft);">
          <span style="font-family:var(--m-display);font-size:14px;color:var(--m-ink);
                       min-width:150px;">{r['agent_id']}</span>
          <div style="flex:1;height:5px;background:var(--m-rule-soft);border-radius:3px;overflow:hidden;">
            <div style="height:100%;width:{pct}%;background:var(--m-accent);
                        border-radius:3px;transition:width 0.4s;"></div>
          </div>
          <span class="tnum" style="font-family:var(--m-mono);font-size:13px;font-weight:600;
                       color:var(--m-ink);min-width:40px;text-align:right;">{r['cnt']}</span>
        </div>"""

    return HTMLResponse(f"""
    <div class="sec-label" style="margin-bottom:14px;"><span>Where wisdom gathers</span>
      <span class="tail">BY SPECIALIST</span></div>
    {items}""")


@router.get("/api/partial/memory/topics", response_class=HTMLResponse)
async def memory_topics(request: Request):
    """Topic coverage — which areas have deep memory."""
    # Gather topics from memory_entries
    rows = db_query(
        """SELECT topics FROM memory_entries
           WHERE topics IS NOT NULL AND topics != ''"""
    ) or []

    topic_counts: dict[str, int] = {}
    for r in rows:
        for t in (r["topics"] or "").split(","):
            t = t.strip().lower()
            if t and len(t) > 1:
                topic_counts[t] = topic_counts.get(t, 0) + 1

    # Also count from episodic memory metadata
    epi_rows = db_query(
        """SELECT metadata FROM episodic_memory
           WHERE metadata IS NOT NULL AND metadata != '{}'
           LIMIT 200"""
    ) or []
    import json
    for r in epi_rows:
        try:
            meta = json.loads(r["metadata"] or "{}")
            for t in (meta.get("tags") or "").split(","):
                t = t.strip().lower()
                if t and len(t) > 1:
                    topic_counts[t] = topic_counts.get(t, 0) + 1
        except Exception:
            pass

    if not topic_counts:
        return HTMLResponse(
            '<div style="padding:20px;text-align:center;color:var(--m-muted);'
            'font-family:var(--m-display);font-size:13px;">'
            'No topic tags found in memory entries.</div>'
        )

    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:30]
    max_count = sorted_topics[0][1] if sorted_topics else 1

    tags = ""
    for topic, count in sorted_topics:
        # Scale font size by count
        size = min(16, max(10, 10 + (count / max_count) * 6))
        opacity = max(0.5, min(1.0, 0.4 + (count / max_count) * 0.6))
        tags += (
            f'<span style="display:inline-block;padding:3px 10px;margin:3px;'
            f'border-radius:12px;background:var(--m-accent);color:white;'
            f'font-family:var(--m-mono);font-size:{size:.0f}px;opacity:{opacity:.2f};'
            f'letter-spacing:0.03em;">{topic} ({count})</span>'
        )

    return HTMLResponse(f"""
    <div>
      <div style="font-family:var(--m-display);font-size:13px;font-weight:600;
                  color:var(--m-ink);margin-bottom:12px;">Topic Coverage</div>
      <div style="line-height:2;">{tags}</div>
    </div>""")


@router.get("/api/partial/memory/staleness", response_class=HTMLResponse)
async def memory_staleness(request: Request):
    """Memory freshness — how recent are the entries in each layer."""
    today = datetime.date.today()
    layers_info = []

    # Check each layer's most recent entry
    checks = [
        ("Memory Palace", "SELECT MAX(created_at) FROM memory_entries"),
        ("Episodic", "SELECT MAX(created_at) FROM episodic_memory"),
        ("Semantic", "SELECT MAX(created_at) FROM semantic_memory"),
        ("Procedural", "SELECT MAX(created_at) FROM procedural_memory"),
        ("Sessions", "SELECT MAX(created_at) FROM session_summaries"),
        ("Reflexions", "SELECT MAX(created_at) FROM reflexion_log"),
    ]

    for name, sql in checks:
        try:
            val = db_scalar(sql, default="")
            if val:
                last_date = val[:10]
                try:
                    d = datetime.date.fromisoformat(last_date)
                    age = (today - d).days
                except Exception:
                    age = -1
                layers_info.append({"name": name, "last": last_date, "age": age})
            else:
                layers_info.append({"name": name, "last": "never", "age": 9999})
        except Exception:
            layers_info.append({"name": name, "last": "error", "age": -1})

    items = ""
    for l in layers_info:
        if l["age"] == 9999:
            color = "var(--m-alert,#dc2626)"
            label = "never written"
        elif l["age"] > 30:
            color = "var(--m-alert,#dc2626)"
            label = f"{l['age']}d ago"
        elif l["age"] > 7:
            color = "var(--m-warn,#b45309)"
            label = f"{l['age']}d ago"
        elif l["age"] >= 0:
            color = "var(--m-ok,#16a34a)"
            label = f"{l['age']}d ago" if l["age"] > 0 else "today"
        else:
            color = "var(--m-muted)"
            label = l["last"]

        items += f"""
        <div style="display:flex;align-items:center;gap:12px;padding:6px 0;">
          <span style="width:10px;height:10px;border-radius:50%;background:{color};
                       flex-shrink:0;"></span>
          <span style="font-family:var(--m-display);font-size:12px;color:var(--m-ink);
                       min-width:110px;">{l['name']}</span>
          <span style="font-family:var(--m-mono);font-size:11px;color:{color};">{label}</span>
          <span style="margin-left:auto;font-family:var(--m-mono);font-size:10px;
                       color:var(--m-muted);">{l['last']}</span>
        </div>"""

    return HTMLResponse(f"""
    <div>
      <div style="font-family:var(--m-display);font-size:13px;font-weight:600;
                  color:var(--m-ink);margin-bottom:12px;">Memory Freshness</div>
      {items}
    </div>""")
