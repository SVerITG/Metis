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
from metis_mcp.local_overrides import load_overrides
from metis_mcp.db import connect

# Re-use PII patterns already in safety.py
from metis_mcp.tools.safety import (
    _EMAIL_RE,
    _PHONE_RE,
    _PATIENT_ID_RE,
    _GPS_RE,
    _BELGIAN_NID_RE,
    _SENSITIVE_COLUMNS,
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

# Research-context institution patterns. Generic global orgs ship in the public
# source; any field- or institution-specific names (e.g. your own institute or
# national programme) are kept private in the local override file and merged in
# at runtime — so they never appear in the published source.
_INSTITUTIONS = ["MSF", "DNDi", "WHO", "CDC", "Ministry of Health"]
_INSTITUTIONS += [str(o) for o in load_overrides().get("extra_institutions", [])]
_INSTITUTION_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(o) for o in _INSTITUTIONS) + r")\b",
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


@app.tool()
async def scan_outgoing(text: str) -> list[TextContent]:
    """Output rail: check a drafted response for leaked PII before it's sent.

    The output-side complement to the read-side hook. Agents call this on any
    response that might contain individual-level data; it enforces the
    constitution's no-pii-output rule. Returns a verdict, what was found, and a
    masked version safe to send.

    Args:
        text: The drafted response text to check.

    Returns JSON: {safe: bool, found: {type: count}, masked: str}.
    """
    found: dict = {}
    masked = text
    for label, pattern in _PATTERNS:
        def _r(m, lbl=label):
            found[lbl] = found.get(lbl, 0) + 1
            return f"[{lbl}]"
        masked = pattern.sub(_r, masked)

    safe = not found
    result = {
        "safe": safe,
        "found": found,
        "masked": masked if not safe else text,
        "verdict": (
            "PASS — no PII patterns detected; safe to send."
            if safe else
            "BLOCK — PII detected. Send the 'masked' version, or remove the identifiers."
        ),
    }
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


@app.tool()
async def redact_data_file(
    path: str,
    max_rows: int = 20,
) -> list[TextContent]:
    """Read a sensitive data file and return a REDACTED preview (masked values).

    The redaction half of /safe-analysis: where check_data_safety only *detects*
    sensitive data and the read-hook *asks*, this returns a masked version so an
    approved read shares no raw identifiers. Sensitive columns (patient/case IDs,
    names, GPS, etc.) are pseudonymised consistently — the same value always maps
    to the same placeholder, so record linkage survives while identity does not.
    PII patterns (emails, phones, IDs) are scrubbed from all remaining cells.

    Local I/O only — nothing leaves the machine except the masked preview you see.

    Args:
        path:     Absolute local path to a CSV/TSV/text data file.
        max_rows: Rows to include in the masked preview (default 20).

    Returns JSON: redacted preview rows, the columns masked, and a per-type count.
    """
    import csv as _csv
    import io as _io
    import os as _os

    if not _os.path.exists(path):
        return [TextContent(type="text", text=json.dumps({"error": f"File not found: {path}"}))]

    ext = (path.rsplit(".", 1)[-1] if "." in path else "").lower()
    if ext not in ("csv", "tsv", "tab", "txt", "psv"):
        return [TextContent(type="text", text=json.dumps({
            "error": f"redact_data_file handles delimited text (csv/tsv/txt). "
                     f"For {ext}, convert to CSV first or use /safe-analysis.",
        }))]

    delim = "\t" if ext in ("tsv", "tab") else ("|" if ext == "psv" else ",")
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = _csv.reader(fh, delimiter=delim)
            rows = []
            for i, r in enumerate(reader):
                rows.append(r)
                if i >= max_rows:  # header + max_rows data rows
                    break
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": f"Read failed: {e}"}))]

    if not rows:
        return [TextContent(type="text", text=json.dumps({"error": "Empty file."}))]

    header = rows[0]
    data_rows = rows[1:]
    # Which columns are sensitive (by header name)?
    sensitive_idx = {
        i: h for i, h in enumerate(header)
        if (h or "").strip().strip('"\'').lower() in _SENSITIVE_COLUMNS
    }

    pseudonyms: dict = {}        # (col, value) -> placeholder
    col_counters: dict = {}
    by_type: dict = {}

    def _scrub_cell(value: str) -> str:
        out = value
        for label, pattern in _PATTERNS:
            def _r(m, lbl=label):
                by_type[lbl] = by_type.get(lbl, 0) + 1
                return f"[{lbl}]"
            out = pattern.sub(_r, out)
        return out

    redacted = []
    for r in data_rows:
        new_row = []
        for i, cell in enumerate(r):
            if i in sensitive_idx:
                col = sensitive_idx[i]
                if cell.strip() == "":
                    new_row.append(cell)
                    continue
                key = (col, cell)
                if key not in pseudonyms:
                    col_counters[col] = col_counters.get(col, 0) + 1
                    pseudonyms[key] = f"[{col.upper()}_{col_counters[col]:03d}]"
                    by_type["COLUMN_MASK"] = by_type.get("COLUMN_MASK", 0) + 1
                new_row.append(pseudonyms[key])
            else:
                new_row.append(_scrub_cell(cell))
        redacted.append(new_row)

    # Re-emit as CSV text for a readable preview.
    buf = _io.StringIO()
    w = _csv.writer(buf, delimiter=delim)
    w.writerow(header)
    w.writerows(redacted)

    result = {
        "path": path,
        "rows_previewed": len(redacted),
        "masked_columns": sorted(set(sensitive_idx.values())),
        "redactions_by_type": by_type,
        "redacted_preview": buf.getvalue(),
        "note": "Sensitive columns pseudonymised (consistent per value); PII patterns scrubbed. Raw values never left the machine.",
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

    Returns the data-handling consent trail — what data was approved or
    classified, by which agent, and when — so you can review or report on how
    sensitive data has been treated. Reads the consent_ledger that
    log_consent_event writes to.

    Args:
        limit: Number of most recent ledger rows to return, newest first
            (default 30).

    Returns:
        A JSON text block listing the consent events (id, timestamp, action,
        data_classification, agent_slug, notes).
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
