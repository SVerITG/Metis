"""MCP resources — standing context for every client, not just Claude Code.

WHY THIS MODULE EXISTS
    MCP has three primitives and Metis used two of them. Tools let the model ACT.
    Prompts let the user PICK. Resources let the client ATTACH context — and that
    third one is precisely what a "silent background layer" is made of.

    The consequence of skipping it was a two-tier Metis. Claude Code reads
    CLAUDE.md, the persona, the response contract and the learned-lesson ledger on
    every session because those are files in a directory it knows about. Claude
    Desktop reads none of them — it does not see CLAUDE.md at all — so everything
    that makes Metis feel like Metis had to be squeezed into the server's
    `instructions` string or fetched by a tool call the model had to think of.

    Resources close that gap with no client-specific work. A resource is
    addressable, readable, and offered to the client at connection time. Publish
    the persona as a resource and every MCP client — Desktop, Cursor, Zed,
    whatever comes next — can hold it open while it works.

WHAT IS PUBLISHED, AND WHY EACH
    metis://persona            who the researcher is, and how to speak to them
    metis://response-contract  how a reply should be shaped
    metis://learned            what Metis has learned from them — the file that
                               makes the persona GROW rather than repeat
    metis://profile            name, field, interests, style preferences
    metis://corpus             what the indexed library actually contains, so a
                               client can tell an ungrounded answer from a
                               grounded one WITHOUT running a search
    metis://project            the active project and its next step
    metis://recent-sessions    what happened last time — continuity, cheaply

DELIBERATE OMISSIONS
    No resource exposes the researcher's literature CONTENT, their notes, or
    anything from `basket/private/`. A resource is offered to the client
    automatically, so anything published here should be assumed to enter a
    context window without a human deciding. Persona and counts are safe on that
    basis; a patient dataset or a private note is not.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from metis_mcp.app_instance import app
from metis_mcp.config import paths

log = logging.getLogger("metis")

_MAX = 24_000          # a resource is context, not an archive


def _read(rel: str, limit: int = _MAX) -> str:
    """Read a config file relative to the RC root. Never raises."""
    try:
        p = paths.root / rel
        if not p.exists():
            return f"(not present: {rel})"
        return p.read_text(encoding="utf-8")[:limit]
    except Exception as exc:
        return f"(unreadable: {rel} — {type(exc).__name__})"


def _db() -> sqlite3.Connection | None:
    try:
        c = sqlite3.connect(str(paths.db), timeout=5.0)
        c.row_factory = sqlite3.Row
        return c
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Identity — the three files Claude Code reads at session start
# ---------------------------------------------------------------------------

@app.resource("metis://persona", name="Metis — who the researcher is",
              mime_type="text/markdown")
def persona() -> str:
    """The researcher's identity, expertise and voice preferences."""
    return _read("system/config/metis-persona.md")


@app.resource("metis://response-contract", name="Metis — how to shape a reply",
              mime_type="text/markdown")
def response_contract() -> str:
    """The marker set, when to reach into prior work, and the register to use."""
    return _read("system/config/metis-response-contract.md")


@app.resource("metis://learned", name="Metis — what has been learned",
              mime_type="text/markdown")
def learned() -> str:
    """Append-only ledger of confirmed preferences and corrections.

    The file that makes the persona grow rather than repeat itself. A correction
    that is only remembered as having happened is not learned.
    """
    return _read("system/config/metis-learned.md")


@app.resource("metis://profile", name="Metis — researcher profile",
              mime_type="application/json")
def profile() -> str:
    """Name, role, interests and style preferences, as JSON."""
    raw = _read("system/config/user-preferences.json")
    try:
        d = json.loads(raw)
    except Exception:
        return raw
    # Never publish credentials or absolute paths through a resource: a resource
    # is attached automatically, so it must contain nothing the researcher would
    # not hand to a client unprompted.
    for k in list(d):
        if any(s in k.lower() for s in ("key", "token", "secret", "path")):
            d.pop(k, None)
    return json.dumps(d, indent=2)


# ---------------------------------------------------------------------------
# State — what the client cannot know without asking
# ---------------------------------------------------------------------------

@app.resource("metis://corpus", name="Metis — indexed corpus",
              mime_type="text/markdown")
def corpus() -> str:
    """What the searchable library actually contains, right now.

    Published so a client can tell a grounded answer from an ungrounded one
    WITHOUT running a search first — and so it can say honestly how large the
    thing it searched was. A number nobody can see is a number nobody can check.
    """
    conn = _db()
    if conn is None:
        return "(corpus unavailable — database not reachable)"
    try:
        lines = ["# Indexed corpus", ""]
        rows = conn.execute(
            "SELECT slug, name, doc_count, chunk_count, last_built "
            "FROM knowledge_databases WHERE COALESCE(enabled,1)=1 ORDER BY layer"
        ).fetchall()
        total_d = total_c = 0
        lines.append("| layer | documents | passages | last built |")
        lines.append("|---|---|---|---|")
        for r in rows:
            total_d += r["doc_count"] or 0
            total_c += r["chunk_count"] or 0
            lines.append(f"| {r['name']} (`{r['slug']}`) | {r['doc_count']} | "
                         f"{r['chunk_count']} | {(r['last_built'] or '—')[:16]} |")
        lines += ["", f"**{total_d} documents · {total_c} passages** searchable by meaning "
                      f"via `search_pdf_knowledge`.", ""]

        cat = conn.execute("SELECT COUNT(*) FROM literature_metadata").fetchone()[0]
        lines.append(f"Catalogue (metadata, not full text): **{cat} references**.")

        lines += ["", "## How to use it", "",
                  "Search it with `search_pdf_knowledge(query=...)` before answering a "
                  "question in the researcher's field, and cite what comes back.",
                  "",
                  "A search returns the top-k most similar passages. It is NOT a "
                  "literature review — never claim the whole library was read or "
                  "checked. State what was actually consulted, e.g. "
                  "\"6 passages from " + str(total_d) + " indexed documents\".",
                  "",
                  "The corpus is trusted ground to build on, not a boundary: bring in "
                  "outside literature and general knowledge too, and mark anything not "
                  "yet in the library as such — then offer to add it."]
        return "\n".join(lines)
    except Exception as exc:
        return f"(corpus query failed: {type(exc).__name__})"
    finally:
        conn.close()


@app.resource("metis://project", name="Metis — active project",
              mime_type="text/markdown")
def project() -> str:
    """The project currently being worked on, and what comes next."""
    conn = _db()
    if conn is None:
        return "(unavailable)"
    try:
        rows = conn.execute(
            "SELECT project_id, name, description, next_step, status "
            "FROM projects WHERE COALESCE(status,'active') NOT IN "
            "('archived','done','complete') ORDER BY rowid DESC LIMIT 4"
        ).fetchall()
        if not rows:
            return "# Active projects\n\nNone registered."
        out = ["# Active projects", ""]
        for r in rows:
            out.append(f"## {r['name']} (`{r['project_id']}`)")
            if r["description"]:
                out.append(str(r["description"])[:400])
            if r["next_step"]:
                out.append(f"\n**Next step:** {str(r['next_step'])[:300]}")
            out.append("")
        return "\n".join(out)
    except Exception:
        return "(project query failed)"
    finally:
        conn.close()


@app.resource("metis://recent-sessions", name="Metis — recent sessions",
              mime_type="text/markdown")
def recent_sessions() -> str:
    """The last few sessions — continuity without a tool call.

    This is what lets a reply say "you settled this in June" honestly. Never
    invent continuity: if this resource is empty, there is nothing to reference.
    """
    conn = _db()
    if conn is None:
        return "(unavailable)"
    try:
        rows = conn.execute(
            "SELECT summary, key_topics, created_at FROM session_summaries "
            "ORDER BY rowid DESC LIMIT 5"
        ).fetchall()
        if not rows:
            return ("# Recent sessions\n\nNothing recorded yet. Say nothing about "
                    "the past — a fabricated 'as we discussed' makes the whole "
                    "memory layer feel decorative.")
        out = ["# Recent sessions", ""]
        for r in rows:
            out.append(f"### {(r['created_at'] or '')[:16]}")
            out.append(str(r["summary"] or "")[:700])
            if r["key_topics"]:
                out.append(f"*Topics:* {str(r['key_topics'])[:200]}")
            out.append("")
        return "\n".join(out)
    except Exception:
        return "(session query failed)"
    finally:
        conn.close()
