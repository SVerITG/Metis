"""
tools/anonymization.py — Phase 6: Data anonymization + consent ledger.

M6.1  anonymize_text(content, mode)
        Regex-based PII scrubbing. Replaces emails, phones, patient IDs,
        GPS coordinates, Belgian NIDs, and name-like tokens with labelled
        placeholders.  Returns anonymized text + a replacement map.

M6.2  diff_anonymization(original, anonymized)
        Returns a side-by-side HTML diff of original vs anonymized text
        (via difflib), suitable for embedding in the dashboard.

M6.4  log_consent_event(action, data_classification, agent_slug, notes)
        Append a row to the consent_ledger table.

M6.4  get_consent_ledger(limit)
        Retrieve recent consent events.

M6.5  set_network_policy(policy)
        Persist current network policy ('strict'|'normal'|'offline') to
        the user config so agents can read it at startup.

M6.5  get_network_policy()
        Return the current policy string.
"""

import difflib
import json
import re
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from metis_mcp.db import connect

# Re-use PII patterns already in safety.py
from metis_mcp.tools.safety import (
    _EMAIL_RE,
    _PHONE_RE,
    _PATIENT_ID_RE,
    _GPS_RE,
    _BELGIAN_NID_RE,
)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS consent_ledger (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp          TEXT    NOT NULL DEFAULT (datetime('now')),
    action             TEXT    NOT NULL,
    data_classification TEXT   NOT NULL DEFAULT 'PUBLIC',
    agent_slug         TEXT,
    notes              TEXT,
    session_id         TEXT
);
CREATE INDEX IF NOT EXISTS idx_consent_ts ON consent_ledger(timestamp DESC);
"""

_POLICY_KEY = "network_policy"
_DEFAULT_POLICY = "normal"


def _ensure_tables(conn):
    for stmt in _DDL.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()


# ---------------------------------------------------------------------------
# M6.1 — anonymize_text
# ---------------------------------------------------------------------------

# Name heuristic: 2+ consecutive CAPITALIZED words not at sentence start
_NAME_RE = re.compile(r"(?<!\.\s)(?<!\n)(?<![.!?]\s)(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)")

# HAT-context institution patterns
_INSTITUTION_RE = re.compile(
    r"\b(?:ITM|ITG|MSF|DNDi|WHO|CDC|PNLTHA|Ministry of Health|Ministère de la Santé)\b",
    re.IGNORECASE,
)

_PATTERNS = [
    ("PATIENT",     _PATIENT_ID_RE),
    ("GPS",         _GPS_RE),
    ("NID",         _BELGIAN_NID_RE),
    ("EMAIL",       _EMAIL_RE),
    ("PHONE",       _PHONE_RE),
]


@app.tool()
async def anonymize_text(
    content: str,
    mode: str = "full",
    replace_names: bool = False,
) -> list[TextContent]:
    """Scrub PII from text and return anonymized version + replacement map.

    Replaces:
      - Patient/case IDs        → [PARTICIPANT_001]
      - GPS coordinates         → [GPS_001]
      - Belgian national IDs    → [NID_001]
      - Email addresses         → [EMAIL_001]
      - Phone numbers           → [PHONE_001]
      - Name-like tokens (opt.) → [NAME_001]

    Args:
        content:        Text to anonymize.
        mode:           'full' — replace; 'preview' — mark without replacing.
        replace_names:  Also replace CAPITALIZED name-like tokens (heuristic).

    Returns JSON with keys 'anonymized' (str) and 'replacements' (dict).
    """
    replacements: dict[str, str] = {}
    counters: dict[str, int] = {}
    text = content

    def _replace(match, label: str) -> str:
        original = match.group(0)
        if original in replacements.values():
            # Already mapped — return existing placeholder
            return next(k for k, v in replacements.items() if v == original)
        counters[label] = counters.get(label, 0) + 1
        placeholder = f"[{label}_{counters[label]:03d}]"
        replacements[placeholder] = original
        return placeholder

    for label, pattern in _PATTERNS:
        text = pattern.sub(lambda m, lbl=label: _replace(m, lbl), text)

    if replace_names:
        text = _NAME_RE.sub(lambda m: _replace(m, "NAME"), text)

    if mode == "preview":
        # Mark matches without replacing
        preview = content
        for label, pattern in _PATTERNS:
            preview = pattern.sub(
                lambda m, lbl=label: f"⚠{lbl}:{m.group(0)}⚠", preview
            )
        result = {
            "mode": "preview",
            "preview": preview,
            "match_count": sum(counters.values()),
            "by_type": counters,
        }
    else:
        result = {
            "mode": "full",
            "anonymized": text,
            "replacements": replacements,
            "match_count": sum(counters.values()),
            "by_type": counters,
        }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ---------------------------------------------------------------------------
# M6.2 — diff_anonymization
# ---------------------------------------------------------------------------

@app.tool()
async def diff_anonymization(
    original: str,
    anonymized: str,
) -> list[TextContent]:
    """Return a unified diff comparing original and anonymized text.

    Args:
        original:   Original (pre-anonymization) text.
        anonymized: Anonymized text from anonymize_text().

    Returns a plain unified-diff string suitable for display.
    """
    orig_lines = original.splitlines(keepends=True)
    anon_lines = anonymized.splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        orig_lines, anon_lines,
        fromfile="original", tofile="anonymized",
        lineterm="",
    ))
    if not diff:
        return [TextContent(type="text", text="No differences — texts are identical.")]
    return [TextContent(type="text", text="".join(diff))]


# ---------------------------------------------------------------------------
# M6.4 — consent ledger
# ---------------------------------------------------------------------------

@app.tool()
async def log_consent_event(
    action: str,
    data_classification: str = "PUBLIC",
    agent_slug: str = "",
    notes: str = "",
    session_id: str = "",
) -> list[TextContent]:
    """Append a row to the consent_ledger table.

    Call this whenever an agent processes data so there is an audit trail
    of what was processed, when, and under what classification.

    Args:
        action:              Short description — e.g. 'scan_document', 'anonymize_patient_data'.
        data_classification: 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'SENSITIVE'.
        agent_slug:          Which agent performed the action.
        notes:               Free-text context.
        session_id:          Current session identifier.
    """
    with connect(paths.db) as conn:
        _ensure_tables(conn)
        conn.execute(
            """INSERT INTO consent_ledger
               (action, data_classification, agent_slug, notes, session_id)
               VALUES (?, ?, ?, ?, ?)""",
            (action, data_classification, agent_slug or None,
             notes or None, session_id or None),
        )
        conn.commit()

    return [TextContent(
        type="text",
        text=f"Consent event logged: {action} [{data_classification}]",
    )]


@app.tool()
async def get_consent_ledger(limit: int = 30) -> list[TextContent]:
    """Retrieve recent consent events from the audit ledger.

    Args:
        limit: Number of most recent rows to return (default 30).
    """
    with connect(paths.db) as conn:
        _ensure_tables(conn)
        rows = conn.execute(
            "SELECT id, timestamp, action, data_classification, agent_slug, notes "
            "FROM consent_ledger ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()

    events = [dict(r) for r in rows]
    return [TextContent(type="text", text=json.dumps(events, indent=2))]


# ---------------------------------------------------------------------------
# M6.5 — network policy
# ---------------------------------------------------------------------------

def _policy_path() -> Path:
    return paths.config / "network-policy.json"


@app.tool()
async def set_network_policy(policy: str) -> list[TextContent]:
    """Set the current network access policy for all agents.

    'strict'  — No internet access. Only local DB, files, and MCP tools.
    'normal'  — Default. Librarian and News Radar may access allowed domains.
    'offline' — Airplane mode. All external requests blocked.

    Args:
        policy: One of 'strict' | 'normal' | 'offline'.
    """
    valid = {"strict", "normal", "offline"}
    if policy not in valid:
        return [TextContent(type="text", text=f"ERROR: policy must be one of {valid}")]

    p = _policy_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"policy": policy}, indent=2), encoding="utf-8")

    return [TextContent(type="text", text=f"Network policy set to: {policy}")]


@app.tool()
async def get_network_policy() -> list[TextContent]:
    """Return the current network access policy.

    Returns 'normal' if no policy file exists (default).
    """
    p = _policy_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            policy = data.get("policy", _DEFAULT_POLICY)
        except Exception:
            policy = _DEFAULT_POLICY
    else:
        policy = _DEFAULT_POLICY

    return [TextContent(type="text", text=policy)]
