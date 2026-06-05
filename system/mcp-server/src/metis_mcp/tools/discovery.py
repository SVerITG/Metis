"""Contextual discovery — proactive, dismissible, EARNED feature tips.

Metis has grown a lot of surface area; new users can't find it all. Rather than a
one-time tour (which nobody remembers — most product tours fail), this surfaces ONE
relevant tip at the *moment* a capability becomes useful — the just-in-time /
progressive-disclosure pattern (Slack, Linear, VS Code, Notion). Research-backed:
progressive disclosure cuts cognitive load ~45-60% yet *raises* long-term feature
adoption.

Design (v2):
- EARNED discovery: never tip a feature the user already uses (usage signals).
- Frequency cap: at most one tip per ~20 min, max a few per day — overuse trains
  users to ignore tips.
- Snooze ("remind me later") AND a power-user mode (experts get silence), not just
  a hard on/off.
- Adoption measurement: we record what was shown and can see what later got used.
- Persisted in the DB → shared across Claude Code + Claude Desktop, survives sessions.
"""
import datetime
import sqlite3

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths

# ── Tuning ───────────────────────────────────────────────────────────────────
_MIN_GAP_MINUTES = 20      # at most one tip per this window (across Code + Desktop)
_DAILY_CAP = 3             # at most this many tips surfaced per calendar day

# ── Tip registry ─────────────────────────────────────────────────────────────
# id → {tags, text, adopted_if?: (table, where-clause)}.  `adopted_if` is the EARNED-
# discovery signal: if that row exists, the user already uses the feature → skip its
# tip. Tips without it are always eligible until shown. Keep text to one sentence.
TIPS: dict[str, dict] = {
    "help": {
        "tags": ["onboarding", "first-session", "unsure", "what-can-you-do"],
        "text": "Tip: type `/metis-help` anytime to see everything I can do — there's a lot, and it grows.",
    },
    "basket-intro": {
        "tags": ["basket", "documents", "files", "onboarding"],
        "text": "Tip: drop any documents into the `basket/` folder and run `/basket` — I'll inventory them, ask what each is, and file them into the right place.",
    },
    "basket-on-library": {
        "tags": ["library", "background", "knowledge-layer", "indexing"],
        "text": "Tip: building your library? Drop your *own* PDFs/notes into the basket (`/basket`) and I'll add them to the layer — not just what's scraped from the web.",
        "adopted_if": ("knowledge_databases", "1=1"),
    },
    "basket-r-style": {
        "tags": ["r-code", "rscript", "coding", "first-code"],
        "text": "Tip: want me to learn your R style? Put your existing R scripts in the basket — I'll analyse how you write code so future scripts match your conventions.",
    },
    "basket-on-project": {
        "tags": ["project", "new-project", "working-on-project"],
        "text": "Tip: for this project, drop related literature, notes, ideas, and similar scripts into the basket — I'll inventory each and ask what it is, so everything's connected.",
    },
    "safe-analysis": {
        "tags": ["data", "dataset", "patient", "sensitive", "csv", "excel"],
        "text": "Tip: working with sensitive data? `/safe-analysis` lets me help — build a dashboard, run a model — without the raw data ever leaving your machine.",
        "adopted_if": ("agent_runs", "agent_slug='data-guardian'"),
    },
    "research-mode": {
        "tags": ["question", "look-up", "literature-question"],
        "text": "Tip: ask with `/research-mode` and I'll check your own library first, complement from the web only if there's a gap (with your OK), and link the answer to your work.",
    },
    "librarian-index": {
        "tags": ["paper", "pdf", "new-paper", "reference"],
        "text": "Tip: `/librarian` can index this paper into your knowledge layer, so you get cited answers from it later (\"what do my papers say about X?\").",
        "adopted_if": ("literature_metadata", "1=1"),
    },
    "meeting-memory": {
        "tags": ["meeting", "transcript", "notes"],
        "text": "Tip: paste a meeting transcript and `/meeting-memory` extracts decisions, action items, and links to your projects automatically.",
        "adopted_if": ("meetings", "1=1"),
    },
    "verify-work": {
        "tags": ["code-change", "wrote-code", "edited-code", "fix"],
        "text": "Tip: before trusting a code change, `/verify-work` runs the tests + an independent skeptic on the diff so \"done\" actually means done.",
    },
    "background-maker": {
        "tags": ["domain", "corpus", "specialist-knowledge"],
        "text": "Tip: `/background build <topic>` creates a permanent specialist knowledge layer from the web that every agent can then retrieve from.",
        "adopted_if": ("knowledge_databases", "1=1"),
    },
}

# First-run orientation — the 3-5 highest-value capabilities only (research: cap a
# first intro at 3-5 steps; the rest is handled by contextual tips over time).
INTRO_IDS = ["help", "research-mode", "basket-intro", "safe-analysis"]


def _con() -> sqlite3.Connection:
    c = sqlite3.connect(str(paths.db))
    c.execute("CREATE TABLE IF NOT EXISTS discovery_shown (tip_id TEXT PRIMARY KEY, shown_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS discovery_state (key TEXT PRIMARY KEY, value TEXT)")
    return c


def _state(con: sqlite3.Connection, key: str, default: str = "") -> str:
    row = con.execute("SELECT value FROM discovery_state WHERE key=?", (key,)).fetchone()
    return default if row is None else (row[0] or default)


def _set_state(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        "INSERT INTO discovery_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _adopted(con: sqlite3.Connection, tip: dict) -> bool:
    a = tip.get("adopted_if")
    if not a:
        return False
    table, where = a
    try:
        return con.execute(f"SELECT 1 FROM {table} WHERE {where} LIMIT 1").fetchone() is not None
    except Exception:
        return False


def _suppressed(con: sqlite3.Connection) -> str | None:
    """Return a reason string if tips should be suppressed right now, else None."""
    if _state(con, "enabled", "1") == "0":
        return "off"
    if _state(con, "mode") == "power":
        return "power-user mode"
    snooze = _state(con, "snooze_until")
    if snooze:
        try:
            if _now() < datetime.datetime.fromisoformat(snooze):
                return "snoozed"
        except Exception:
            pass
    # Frequency cap: one tip per _MIN_GAP_MINUTES
    last = _state(con, "last_tip_at")
    if last:
        try:
            if (_now() - datetime.datetime.fromisoformat(last)).total_seconds() < _MIN_GAP_MINUTES * 60:
                return "rate-capped"
        except Exception:
            pass
    # Daily cap
    today = _now().date().isoformat()
    n_today = con.execute(
        "SELECT COUNT(*) FROM discovery_shown WHERE substr(shown_at,1,10)=?", (today,)
    ).fetchone()[0]
    if n_today >= _DAILY_CAP:
        return "daily-cap"
    return None


@app.tool()
async def next_discovery_tip(context: str = "") -> list[TextContent]:
    """Return ONE earned, not-yet-shown feature tip for the current moment (or '').

    Call at natural trigger moments (user starts a project, writes R code, builds a
    library, asks a knowledge question, handles a dataset…). Pass `context` as
    comma-separated trigger tags. Returns at most one tip — and ONLY for a feature the
    user does NOT already use (earned discovery), respecting the off/snooze/power-user
    settings and a frequency cap (≤1 tip / 20 min, ≤3 / day). Records it so it never
    repeats. Returns '' when nothing should be shown. Weave the tip in naturally.

    Args:
        context: comma-separated trigger tags describing what the user is doing.
    """
    tags = {t.strip().lower() for t in context.split(",") if t.strip()}
    try:
        con = _con()
        if _suppressed(con):
            con.close()
            return [TextContent(type="text", text="")]
        shown = {r[0] for r in con.execute("SELECT tip_id FROM discovery_shown")}
        for tip_id, tip in TIPS.items():
            if tip_id in shown:
                continue
            if _adopted(con, tip):                 # earned discovery: skip what they use
                continue
            if not tags or (tags & set(tip["tags"])):
                now = _now().isoformat()
                con.execute("INSERT OR IGNORE INTO discovery_shown (tip_id, shown_at) VALUES (?, ?)", (tip_id, now))
                _set_state(con, "last_tip_at", now)
                con.commit()
                con.close()
                return [TextContent(type="text", text=tip["text"])]
        con.close()
    except Exception:
        pass
    return [TextContent(type="text", text="")]


@app.tool()
async def discovery_intro() -> list[TextContent]:
    """Return the tiny first-run orientation — the 3-5 highest-value capabilities.

    Use ONCE for a brand-new user (or when they ask 'what can you do?'). After this,
    rely on `next_discovery_tip` for the long tail. No-op (returns '') if the intro was
    already given or tips are off.
    """
    try:
        con = _con()
        if _state(con, "enabled", "1") == "0" or _state(con, "intro_done") == "1":
            con.close()
            return [TextContent(type="text", text="")]
        lines = ["Here are a few things I can do — I'll mention the rest as they become useful:"]
        for tid in INTRO_IDS:
            if tid in TIPS:
                lines.append("• " + TIPS[tid]["text"].replace("Tip: ", ""))
        lines.append("(Say \"stop the tips\" anytime, or \"I'm a power user\" to keep them minimal.)")
        _set_state(con, "intro_done", "1")
        con.commit()
        con.close()
        return [TextContent(type="text", text="\n".join(lines))]
    except Exception:
        return [TextContent(type="text", text="")]


@app.tool()
async def set_discovery_tips(enabled: bool | None = None,
                             power_user: bool | None = None,
                             snooze_days: int = 0) -> list[TextContent]:
    """Adjust the feature-tips preference (the user's control).

    Args:
        enabled:     True/False to turn tips on/off entirely.
        power_user:  True = expert mode (tips stay quiet); False = guided mode.
        snooze_days: >0 to snooze ALL tips for N days ("remind me later").
    """
    try:
        con = _con()
        msg = []
        if enabled is not None:
            _set_state(con, "enabled", "1" if enabled else "0")
            msg.append(f"tips {'on' if enabled else 'off'}")
        if power_user is not None:
            _set_state(con, "mode", "power" if power_user else "guided")
            msg.append("power-user mode" if power_user else "guided mode")
        if snooze_days and snooze_days > 0:
            until = (_now() + datetime.timedelta(days=snooze_days)).isoformat()
            _set_state(con, "snooze_until", until)
            msg.append(f"snoozed for {snooze_days} day(s)")
        con.commit()
        con.close()
        return [TextContent(type="text", text="Discovery: " + (", ".join(msg) if msg else "no change") + ".")]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not update tips setting: {e}")]


@app.tool()
async def discovery_status() -> list[TextContent]:
    """Report tips state + a simple adoption read (which shown tips' features are now used)."""
    try:
        con = _con()
        enabled = _state(con, "enabled", "1") != "0"
        mode = _state(con, "mode", "guided")
        snooze = _state(con, "snooze_until")
        shown_rows = [r[0] for r in con.execute("SELECT tip_id FROM discovery_shown")]
        adopted = sum(1 for tid in shown_rows if tid in TIPS and _adopted(con, TIPS[tid]))
        con.close()
        snooze_note = ""
        if snooze:
            try:
                if _now() < datetime.datetime.fromisoformat(snooze):
                    snooze_note = f" · snoozed until {snooze[:10]}"
            except Exception:
                pass
        return [TextContent(type="text", text=(
            f"Feature tips: {'on' if enabled else 'off'} · mode={mode}{snooze_note} · "
            f"{len(shown_rows)}/{len(TIPS)} shown · {adopted} of those features now in use (adopted)."
        ))]
    except Exception as e:
        return [TextContent(type="text", text=f"Could not read tips status: {e}")]
