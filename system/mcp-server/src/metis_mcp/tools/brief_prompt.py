"""The briefing recipe, shared by both writers of a brief.

A brief is written either by the dashboard's own generator (an API call) or by a
Claude session through generate_daily_insight → save_daily_brief, on a machine
with no API budget. The two used to share only the table they wrote to: the
session got a thinner context and no writing rules, so its briefs came out with
headers and bullets, ignored the freshness contract, and recorded no thread
coverage. Everything both writers must agree on lives here, so they cannot
drift apart again. Pure functions — no MCP runtime, importable from the dashboard.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

from metis_mcp.domain import domain
from metis_mcp.tools.news_threads import COVERAGE_FOOTER_INSTRUCTION

# Storage contract: what each writer files a brief under, per period.
API_MODEL_TAGS = {
    "daily": "claude-haiku-brief",
    "weekly": "claude-haiku-weekly",
    "catchup": "claude-sonnet-catchup",
}
SESSION_MODEL_TAGS = {
    "daily": "desktop-brief",
    "weekly": "desktop-weekly",
    "catchup": "desktop-catchup",
}
KEY_SUFFIXES = {"daily": "", "weekly": "-weekly", "catchup": "-catchup"}

# How much context the writer is shown. The API path has always cut here.
CONTEXT_CHARS = 6000


def insight_key(period: str, date: str = "") -> str:
    return (date or datetime.date.today().isoformat()) + KEY_SUFFIXES.get(period, "")


def period_from_key(key: str) -> str:
    for period, suffix in KEY_SUFFIXES.items():
        if suffix and key.endswith(suffix):
            return period
    return "daily"


def last_brief_at(db_path: str) -> datetime.datetime | None:
    """When the last daily brief was written, as naive local time."""
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT MAX(generated_at) FROM daily_insights "
            "WHERE model IN ('claude-haiku-brief','desktop-brief')"
        ).fetchone()
        conn.close()
        if row and row[0]:
            ts = datetime.datetime.fromisoformat(row[0])
            if ts.tzinfo is not None:
                ts = ts.astimezone().replace(tzinfo=None)
            return ts
    except Exception:
        pass
    return None


def gap_label_for(days: int) -> str:
    if days >= 14:
        return f"{days // 7} WEEKS"
    if days >= 7:
        return "1 WEEK"
    if days >= 2:
        return f"{days} DAYS"
    return ""


def describe_period(period: str, days_since_last: int) -> str:
    if period == "weekly":
        return "the past week"
    if period == "daily" and days_since_last <= 1:
        return "today"
    if days_since_last <= 7:
        return f"the last {days_since_last} days"
    weeks = days_since_last // 7
    return f"the last {weeks} week{'s' if days_since_last >= 14 else ''}"


def load_profile(root: str | Path, db_path: str = "") -> dict:
    """Name, field, interests and monitored topics, with the dashboard's fallbacks."""
    root = Path(root) if root else None
    prefs: dict = {}
    if root:
        try:
            p = root / "system" / "config" / "user-preferences.json"
            if p.exists():
                prefs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            prefs = {}

    name = ""
    if db_path:
        try:
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT value FROM user_config WHERE key = 'user_name' LIMIT 1"
            ).fetchone()
            conn.close()
            name = (row[0] if row else "") or ""
        except Exception:
            pass
    name = name or prefs.get("display_name", "")
    if not name and root:
        try:
            import yaml
            cfg = root / "system" / "config" / "user-config.yaml"
            if cfg.exists():
                name = ((yaml.safe_load(cfg.read_text()) or {})
                        .get("user", {}).get("name", "")) or ""
        except Exception:
            pass

    interests = prefs.get("interests", []) or []
    topics = prefs.get("news_topics", []) or []
    fallback = brief_fallbacks()
    return {
        "name": name or "Researcher",
        "field": prefs.get("role", "") or fallback["field"],
        "interests": ", ".join(interests[:8]) if interests else fallback["interests"],
        "topics": ", ".join(topics[:6]) if topics else fallback["topics"],
    }


# What a brief says about the reader when they have told Metis nothing. Neutral
# on purpose: a person with no declared interests must not be addressed as a
# member of somebody else's field. A machine-local domain file may replace these.
_BRIEF_FALLBACKS = {
    "field": "research",
    "interests": "research developments in the reader's field, methods, science policy",
    "topics": "major science and research news, research funding and policy, AI in research",
}


def brief_fallbacks() -> dict:
    """{field, interests, topics} used when the profile leaves one empty."""
    out = dict(_BRIEF_FALLBACKS)
    local = domain("brief_fallbacks", {})
    if isinstance(local, dict):
        out.update({k: str(v) for k, v in local.items() if k in out and v})
    return out


def source_items(conn: sqlite3.Connection, days: int) -> list[dict]:
    """The news items shown as source links under a brief."""
    since = (datetime.datetime.now() - datetime.timedelta(days=max(days, 3))).isoformat()
    rows = conn.execute(
        "SELECT title, domain, source_url FROM news_briefs "
        "WHERE created_at >= ? ORDER BY "
        "CASE WHEN signal_strength='high' THEN 1 WHEN signal_strength='medium' THEN 2 ELSE 3 END, "
        "created_at DESC LIMIT 6",
        (since,),
    ).fetchall()
    return [
        {"title": (r[0] or "")[:80], "domain": r[1] or "", "url": r[2] or ""}
        for r in rows
    ]


def brief_system_prompt(
    period: str,
    name: str,
    field: str,
    interests: str,
    topics: str,
    period_desc: str,
    gap_label: str = "",
) -> str:
    """Build the system prompt for the daily/weekly/catchup brief."""

    guardrail = (
        "IMPORTANT: Write about external developments only — never about the "
        "researcher's own tools, software, or AI systems. Projects and ideas "
        "are provided as framing context only — they are relevance anchors, "
        "not briefing topics."
    )

    # Anti-repetition contract. The context groups news into story threads and
    # labels each with what the researcher has already been told; without these rules the
    # model still leads with the biggest story every day, which is exactly the
    # behaviour the thread layer exists to stop. See tools/news_threads.py.
    freshness = (
        "FRESHNESS CONTRACT — this brief is read every day, so repetition is the "
        "main failure mode:\n"
        "- Lead ONLY with a thread listed under 'ELIGIBLE TO LEAD'. Never lead with "
        "a thread under 'ALREADY DELIVERED', however large it is.\n"
        "- A long-running story that has not changed deserves silence, not a "
        "paragraph. Saying nothing about it is correct, not an omission.\n"
        "- If an already-delivered thread genuinely escalated (its line says "
        "ESCALATION), you may lead with it — say plainly what changed since last "
        "time rather than re-describing the story.\n"
        "- Take the ANGLE offered for the thread you lead with. The angles already "
        "used are listed; do not reuse them. Same story, new lens.\n"
        "- Never open with a phrase you would have used yesterday. No 'continues to', "
        "'remains a concern', 'ongoing situation' as a lead.\n"
    )

    preamble = (
        f"You are writing a research intelligence brief for {name}, "
        f"a senior researcher in {field}.\n\n"
        f"Their specific research interests: {interests}\n"
        f"Topics they monitor: {topics}\n"
        f"Briefing period: {period_desc}\n\n"
        f"{guardrail}\n\n"
        f"{freshness}\n"
    )

    # Appended to every period so coverage is recorded and cooldowns advance.
    # Without the footer no coverage is recorded, nothing ever goes on
    # cooldown, and the repetition returns silently.
    footer = f"\n\n{COVERAGE_FOOTER_INSTRUCTION}"

    if period == "weekly":
        return preamble + (
            "Write exactly four paragraphs, 400–500 words total:\n\n"
            "Paragraph 1 — THE WEEK: The two or three most significant developments "
            f"in {domain('brief_week_scope', 'research, science, or AI')} this week. "
            "State what happened and why "
            "it matters. Be specific — name papers, organisations, numbers.\n\n"
            "Paragraph 2 — PATTERNS: Step back from individual items and identify "
            "one or two emerging patterns, policy shifts, or methodological trends "
            "across the week's signals. Cross-reference items when connected.\n\n"
            "Paragraph 3 — THE BRIDGE: One concrete connection between an external "
            f"signal and {name}'s active research or interests. Be explicit about "
            "why it matters and what opportunity or risk it creates.\n\n"
            "Paragraph 4 — ONE THING: A single paper, report, or question worth "
            f"following up on next week. Name it precisely and say why {name} "
            "should prioritise it.\n\n"
            "WEEKLY-SPECIFIC RULE — this overrides the daily freshness contract "
            "above. The weekly is COMPLETE on purpose: it must cover the week's "
            "significant threads even where the dailies held them back, because "
            f"{name} reads it as an overview rather than a diff. So do not suppress "
            "anything here. What changes is the treatment:\n"
            "- A thread marked ALREADY SEEN: give its TRAJECTORY across the week — "
            "where it started, what moved, where it stands now. Never restate the "
            "daily item he already read.\n"
            "- A thread marked NOT YET SEEN: report it properly and completely. He "
            "has never been told, so this is new information however old the story.\n"
            "- Prefer a never-seen thread for Paragraph 4 (ONE THING) when one is "
            "of comparable importance.\n\n"
            f"Tone: warm, direct, occasionally dry. Like a smart colleague giving the "
            f"5-minute week-in-review. Plain language. Field-standard terms fine; "
            f"unexplained jargon is not.\n\n"
            "No greeting. No sign-off. No headers. No bullet points. Continuous prose only."
            + footer
        )

    if period == "catchup":
        gap_note = f" ({gap_label})" if gap_label else ""
        return preamble + (
            f"The researcher has been away{gap_note}. Write exactly four paragraphs, "
            "400–500 words total:\n\n"
            "Paragraph 1 — WHAT YOU MISSED: The two or three most important developments "
            "since the last brief. Lead with the highest-impact item. State facts, not "
            "opinions.\n\n"
            "Paragraph 2 — WHAT CHANGED: Any shifts in policy, emerging patterns, or "
            "new publications that alter the landscape of their field. Reference the "
            "previous brief (provided) to highlight what's genuinely new vs. continuing.\n\n"
            "Paragraph 3 — CONNECTIONS: One or two concrete links between missed signals "
            f"and {name}'s active research. Be specific about implications.\n\n"
            "Paragraph 4 — START HERE: The single most important thing to read, review, "
            "or act on first. Name it and say why it's the priority re-entry point.\n\n"
            "CATCH-UP-SPECIFIC RULE — draw your content from the threads marked "
            "NEVER DELIVERED. Those are what he actually missed. Threads marked "
            "ALREADY SEEN are for continuity: give their current state in a clause, "
            "never a paragraph.\n\n"
            f"Tone: warm, efficient. Like a trusted colleague bringing you up to speed "
            f"after time away. No filler.\n\n"
            "No greeting. No sign-off. No headers. No bullet points. Continuous prose only."
            + footer
        )

    # Default: daily
    return preamble + (
        "Write exactly three paragraphs, 270–320 words total:\n\n"
        "Paragraph 1 — THE LEAD: The most important development from a thread listed "
        "as ELIGIBLE TO LEAD. State what happened and why it matters. "
        f"If it touches {name}'s specific interests, draw that connection explicitly "
        "and plainly. Don't hint: say it directly. If the only eligible threads are "
        "modest, lead with a modest story — a smaller genuinely-new lead is better "
        "than a large one he has already read.\n\n"
        "Paragraph 2 — THE FIELD: Two or three other notable developments, grouped "
        "thematically. Cross-reference items when they are connected. Be specific — "
        "name papers, organisations, or numbers. Group by theme. This is where an "
        "already-delivered thread may earn one clause, and only if it has moved.\n\n"
        "Paragraph 3 — THE THREAD: One specific paper, news item, or open question "
        f"from the context that {name} should follow up on today. Name it precisely "
        "and say exactly why it matters for their work right now — concretely.\n\n"
        f"Tone: warm, direct, occasionally dry. Like a smart colleague who read "
        f"everything during {period_desc} and is giving you the 90-second version. "
        "Plain language. Field-standard terms fine; unexplained jargon is not.\n\n"
        "No greeting. No sign-off. No headers. No bullet points. Continuous prose only."
        + footer
    )
