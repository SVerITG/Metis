"""Contextual discovery — proactive, dismissible feature tips.

Metis has grown a lot of surface area; new users can't find it all. Rather than a
one-time tour (which nobody remembers), this surfaces ONE relevant tip at the
*moment* a capability becomes useful — the just-in-time pattern used by Slack,
Linear, VS Code: progressive disclosure, contextual, dismissible, frequency-capped.

How it works: at natural trigger moments Metis calls `next_discovery_tip(context)`.
It returns at most one unseen tip matching the context (and records it so it never
repeats), or "" if tips are off / all seen. The user can turn tips off entirely with
`set_discovery_tips(enabled=False)`. Persisted in the DB so it's shared across Claude
Code and Desktop and survives sessions.
"""
import sqlite3
import datetime

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths

# ── Tip registry ─────────────────────────────────────────────────────────────
# Each tip: id → {tags, text}. `tags` are the trigger moments the caller passes.
# Keep tips to ONE actionable sentence. Edit freely — this is the content layer.
TIPS: dict[str, dict] = {
    "basket-intro": {
        "tags": ["basket", "documents", "files", "onboarding"],
        "text": "Tip: drop any documents into the `basket/` folder and run `/basket` — I'll inventory them, ask what each is, and file them into the right place.",
    },
    "basket-on-library": {
        "tags": ["library", "background", "knowledge-layer", "indexing"],
        "text": "Tip: building your library? You can also drop your *own* PDFs/notes into the basket (`/basket`) and I'll add them to the layer — not just what's scraped from the web.",
    },
    "basket-r-style": {
        "tags": ["r-code", "rscript", "coding", "first-code"],
        "text": "Tip: want me to learn your R style? Put your existing R scripts in the basket — I'll analyse how you write code so future scripts match your conventions.",
    },
    "basket-on-project": {
        "tags": ["project", "new-project", "working-on-project"],
        "text": "Tip: for this project, drop related literature, notes, ideas, and similar scripts into the basket — I'll inventory each one and ask what it is, so everything's connected.",
    },
    "safe-analysis": {
        "tags": ["data", "dataset", "patient", "sensitive", "csv", "excel"],
        "text": "Tip: working with sensitive data? `/safe-analysis` lets me help (build a dashboard, run a model) without the raw data ever leaving your machine.",
    },
    "research-mode": {
        "tags": ["question", "what-does-evidence-say", "look-up", "literature-question"],
        "text": "Tip: ask with `/research-mode` and I'll check your own library first, complement from the web only if there's a gap (with your OK), and link the answer to your work.",
    },
    "librarian-index": {
        "tags": ["paper", "pdf", "new-paper", "reference"],
        "text": "Tip: `/librarian` can index this paper into your knowledge layer, so you get cited answers from it later (\"what do my papers say about X?\").",
    },
    "meeting-memory": {
        "tags": ["meeting", "transcript", "notes"],
        "text": "Tip: paste a meeting transcript and `/meeting-memory` extracts decisions, action items, and links to your projects automatically.",
    },
    "verify-work": {
        "tags": ["code-change", "wrote-code", "edited-code", "fix"],
        "text": "Tip: before trusting a code change, `/verify-work` runs the tests + an independent skeptic on the diff so \"done\" actually means done.",
    },
    "background-maker": {
        "tags": ["domain", "corpus", "specialist-knowledge"],
        "text": "Tip: `/background build <topic>` creates a permanent specialist knowledge layer from the web that every agent can then retrieve from.",
    },
    "help": {
        "tags": ["onboarding", "first-session", "unsure", "what-can-you-do"],
        "text": "Tip: type `/metis-help` anytime to see everything I can do — there's a lot, and it grows.",
    },
}


def _con() -> sqlite3.Connection:
    c = sqlite3.connect(str(paths.db))
    c.execute("CREATE TABLE IF NOT EXISTS discovery_shown (tip_id TEXT PRIMARY KEY, shown_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS discovery_state (key TEXT PRIMARY KEY, value TEXT)")
    return c


def _tips_enabled(con: sqlite3.Connection) -> bool:
    row = con.execute("SELECT value FROM discovery_state WHERE key='enabled'").fetchone()
    return True if row is None else (row[0] != "0")


@app.tool()
async def next_discovery_tip(context: str = "") -> list[TextContent]:
    """Return ONE relevant, not-yet-shown feature tip for the current moment (or '').

    Call this at natural trigger moments — when the user starts a project, writes R
    code for the first time, builds a library, asks a knowledge question, handles a
    dataset, etc. Pass `context` as comma-separated trigger tags (e.g. "project,r-code").
    Returns at most one tip and records it so it never repeats. Returns an empty body
    if tips are disabled or every matching tip has already been shown. Weave the tip in
    naturally — do not dump it robotically.

    Args:
        context: comma-separated trigger tags describing what the user is doing.
    """
    tags = {t.strip().lower() for t in context.split(",") if t.strip()}
    try:
        con = _con()
        if not _tips_enabled(con):
            return [TextContent(type="text", text="")]
        shown = {r[0] for r in con.execute("SELECT tip_id FROM discovery_shown")}
        for tip_id, tip in TIPS.items():
            if tip_id in shown:
                continue
            if not tags or (tags & set(tip["tags"])):
                con.execute(
                    "INSERT OR IGNORE INTO discovery_shown (tip_id, shown_at) VALUES (?, ?)",
                    (tip_id, datetime.datetime.now(datetime.timezone.utc).isoformat()),
                )
                con.commit()
                con.close()
                return [TextContent(type="text", text=tip["text"])]
        con.close()
    except Exception:
        pass
    return [TextContent(type="text", text="")]


@app.tool()
async def set_discovery_tips(enabled: bool) -> list[TextContent]:
    """Turn proactive feature tips on or off (the user's 'stop showing me tips' switch)."""
    try:
        con = _con()
        con.execute(
            "INSERT INTO discovery_state (key, value) VALUES ('enabled', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ("1" if enabled else "0",),
        )
        con.commit()
        con.close()
        state = "on" if enabled else "off"
        return [TextContent(type="text", text=f"Feature tips are now {state}.")]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not update tips setting: {e}")]


@app.tool()
async def discovery_status() -> list[TextContent]:
    """Report whether tips are on, and how many have been shown / remain."""
    try:
        con = _con()
        on = _tips_enabled(con)
        shown = con.execute("SELECT COUNT(*) FROM discovery_shown").fetchone()[0]
        con.close()
        return [TextContent(type="text", text=(
            f"Feature tips: {'on' if on else 'off'} · {shown}/{len(TIPS)} shown, "
            f"{len(TIPS) - shown} remaining."
        ))]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not read tips status: {e}")]
