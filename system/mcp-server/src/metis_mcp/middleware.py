"""middleware.py — the tool-dispatch chokepoint.

THE PROBLEM (security audit, 2026-07-14)
    Metis has a real Data Guardian: a genuine PII scanner, a hard-deny on secrets,
    a path-confinement guard. But they were wired in at *individual call sites*.
    The Guardian itself only inspected the `run_metis` request string, and the
    other ~212 tools were callable straight around it.

        "A front-door mat in a building with 212 side doors."

    Every fix at a call site is one more door locked. It does not stop a NEW tool
    from opening a new door tomorrow. A security control that depends on being
    remembered is not a control — it is a convention.

THE FIX
    FastMCP funnels EVERY tool call through `FastMCP.call_tool`. Wrapping that one
    method makes the guard structural: a tool cannot opt out, and a tool added next
    year is covered the day it is written, by nobody remembering anything.

THE POLICY, and why it is calibrated rather than blunt
    1. PATHS — BLOCK. Any argument that resolves into a credential store or
       `basket/private/` (patient data) refuses the call outright, for all 213
       tools. Zero false positives on legitimate research, and it is the actual
       "212 side doors" fix: previously only files.py checked.

    2. EGRESS PII — MASK on the tools where patient data physically ENTERS
       (file readers, data profilers, script analysers), LOG everywhere else.

       Blanket-masking every tool's output was the obvious move and it is WRONG.
       Stan is an epidemiologist: GPS coordinates in HAT surveillance data are the
       object of study, not a leak. Masking them everywhere would break the real
       work and train him to switch the rail off — which is worse than not having
       one. So we mask where untrusted patient files enter, and elsewhere we make
       the leak VISIBLE (it was previously invisible: `scan_outgoing` had zero
       callers). Visibility first; enforcement where it is unambiguous.

    3. AUDIT — every call is logged, so "which tool touched patient data" stops
       being unanswerable.

    Never blocks on a scanner failure in a way that bricks Metis: a crash in the
    guard logs ERROR and lets the call through, EXCEPT for the path deny, which
    fails closed. Confidentiality of secrets is worth an outage; a flaky regex is
    not.

Disable in an emergency: METIS_NO_TOOL_GUARD=1
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("metis.guard")

# Tools whose output is SUPPOSED to contain personal data — masking them would
# destroy the feature (a contact with a masked email is not a contact).
_PII_IS_THE_PAYLOAD = {
    "get_contacts",
    "update_contact",
    "anonymize_text",     # its whole job is to show you the PII it found
    "scan_outgoing",
    "diff_anonymization",
    "check_data_safety",
    "get_consent_ledger",
}

# Tools where an untrusted file's contents physically enter the model's context.
# This is where patient data actually arrives, so this is where we ENFORCE.
_MASK_EGRESS = {
    "read_file",
    "list_folder",
    "analyze_script",
    "scan_project_scripts",
    "scan_inbox",
    "list_basket",
    "promote_basket_item",
    "ingest_profiling_output",
    "search_notes",
    "kitchen_search",
}

# Argument names that carry a filesystem path.
_PATH_ARGS = {
    "path", "file_path", "folder", "folder_path", "dir", "directory",
    "source", "target", "script_path", "filename", "file",
}


def _texts_of(result: Any) -> list[Any]:
    """The TextContent blocks in a tool result, whatever shape it came back in."""
    if result is None:
        return []
    seq = result if isinstance(result, (list, tuple)) else [result]
    return [b for b in seq if hasattr(b, "text") and isinstance(getattr(b, "text", None), str)]


def install(app: Any) -> None:
    """Wrap app.call_tool so no tool can bypass the guard."""
    if os.environ.get("METIS_NO_TOOL_GUARD") == "1":
        log.warning("tool guard DISABLED via METIS_NO_TOOL_GUARD=1")
        return

    original = app.call_tool

    async def guarded_call_tool(name: str, arguments: dict[str, Any]):
        # ── 1. PATH DENY — fails CLOSED ──────────────────────────────────────
        # The one rule worth an outage. A secret or a patient file disclosed to
        # the API cannot be un-disclosed.
        try:
            from metis_mcp.tools.files import _path_refusal
            from pathlib import Path

            for key, value in (arguments or {}).items():
                if not isinstance(value, str) or not value:
                    continue
                looks_like_path = key.lower() in _PATH_ARGS or value.startswith(("/", "~", "./", "../"))
                if not looks_like_path:
                    continue
                refusal = _path_refusal(Path(value))
                if refusal:
                    log.error("guard: BLOCKED %s(%s=%r) — %s", name, key, value[:80], refusal)
                    _audit(name, "BLOCKED", refusal[:120])
                    from mcp.types import TextContent
                    return [TextContent(type="text", text=refusal)]
        except ImportError:
            log.error("guard: path confinement UNAVAILABLE — refusing %s (fail-closed)", name)
            from mcp.types import TextContent
            return [TextContent(
                type="text",
                text="Refused: the path-confinement guard could not load. Nothing was read.",
            )]
        except Exception as exc:  # a bug in OUR guard must not brick Metis
            log.error("guard: path check errored on %s (%s) — allowing", name, exc)

        # ── 2. Run the tool ──────────────────────────────────────────────────
        result = await original(name, arguments)

        # ── 3. EGRESS PII RAIL ───────────────────────────────────────────────
        if name in _PII_IS_THE_PAYLOAD:
            return result
        try:
            from metis_mcp.tools.anonymization import mask_pii

            enforce = name in _MASK_EGRESS
            for block in _texts_of(result):
                masked, found = mask_pii(block.text)
                if not found:
                    continue
                if enforce:
                    block.text = masked
                    log.warning("guard: masked %s in %s output before it reached the model", found, name)
                    _audit(name, "MASKED", str(found))
                else:
                    # Not masked — but no longer invisible. This is the data that
                    # used to leave with nobody able to say so afterwards.
                    log.warning("guard: %s output contains PII %s (not masked — review)", name, found)
                    _audit(name, "PII_SEEN", str(found))
        except Exception as exc:
            # Fail OPEN here on purpose: a regex bug must not take the whole
            # assistant down. It is logged loudly instead.
            log.error("guard: egress rail failed on %s (%s) — output NOT scanned", name, exc)

        return result

    app.call_tool = guarded_call_tool  # type: ignore[method-assign]
    log.info("tool guard installed — path deny + egress PII rail on every tool call")


def _audit(tool: str, verdict: str, detail: str) -> None:
    """Record what the guard did. 'Which tool touched patient data' must be answerable."""
    try:
        from metis_mcp.config import paths
        from metis_mcp.db import connect

        with connect(paths.db) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS tool_guard_log (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       ts TEXT DEFAULT (datetime('now')),
                       tool TEXT, verdict TEXT, detail TEXT)"""
            )
            conn.execute(
                "INSERT INTO tool_guard_log (tool, verdict, detail) VALUES (?,?,?)",
                (tool, verdict, detail[:300]),
            )
    except Exception as exc:
        log.debug("guard: could not write audit row: %s", exc)
