"""verification.py — HTTP surface for the citation checker.

WHY OVER HTTP AND NOT A SCRIPT
    Same reasoning as the corpus-grounding hook, for the same reason. The Stop
    hook fires on every turn, so its worst case is what matters. A Node hook
    shelling out to Python would pay interpreter startup plus a sqlite-vec load
    on every single reply, and a background check that makes Metis feel slow gets
    switched off within a week.

    The dashboard is already running with the database open. Asking it over
    localhost costs milliseconds. When the dashboard is not up the hook simply
    gets a connection error and stays silent — the correct degradation.

WHAT THIS DOES NOT DO
    It never blocks a reply by default. A wrong claim in conversation is cheap to
    correct in the next sentence; the expensive case is a claim written into a
    course or a manuscript, and that is gated by `tools/verify_citations.py`
    instead. Here the job is to RECORD, so the ledger accumulates and
    `citation_debt` can answer "what rests on unverified citations?".
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from ui import clip

router = APIRouter()
log = logging.getLogger("metis.verification")


def _tools():
    """Import the checker lazily so a broken MCP tree cannot break dashboard boot."""
    from metis_mcp.tools import verification as v
    return v


@router.post("/api/verify/turn")
async def verify_turn(request: Request):
    """Check the citations in one assistant reply. Records; does not block.

    Body: {"text": "...", "session_id": "...", "artifact_path": "..."}
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "bad json"}, status_code=400)

    text = (body.get("text") or "").strip()
    if not text:
        return JSONResponse({"ok": True, "checked": 0, "results": []})

    try:
        v = _tools()
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                            status_code=503)

    session_id = (body.get("session_id") or "")[:80]
    artifact = clip(body.get("artifact_path") or "", 400)

    results = []
    try:
        for c in v.extract_citations(text):
            if c.get("doi"):
                # Tier B costs a network round trip, so the per-turn path never
                # takes it. The nightly job resolves the backlog instead.
                res = {**c, "tier": "B", "verdict": "doi_unchecked",
                       "detail": "queued for the nightly DOI resolution"}
            else:
                res = {**c, **v.check_claim(c["claim"], c["source"], c["page"],
                                            c.get("quote", ""))}
            v.record_check(res, artifact_path=artifact, session_id=session_id)
            results.append({
                "verdict": res["verdict"], "source": res.get("source", ""),
                "page": res.get("page"), "doi": res.get("doi", ""),
                "detail": res.get("detail", ""),
                "hard": res["verdict"] in v.HARD_FAILURES,
            })
    except Exception as exc:
        log.warning("[verify] turn check failed: %s", exc)
        return JSONResponse({"ok": False, "error": str(exc)[:200]}, status_code=500)

    hard = [r for r in results if r["hard"]]
    return JSONResponse({
        "ok": True, "checked": len(results),
        "hard_failures": len(hard), "results": results,
    })


@router.get("/api/verify/coverage")
async def verify_coverage():
    """Per-layer quotable counts and the reference-library quotable fraction.

    The honest denominator for every grounding claim Metis makes. There are three
    states, not two: quotable (indexed full text), known-but-unquotable (metadata
    only), and absent. Without the middle one, "not in your corpus" gets read as
    "not in your literature".
    """
    try:
        from db import db_query, db_scalar
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:150]}, status_code=503)

    layers = db_query(
        "SELECT COALESCE(k.slug,'(unfiled)') AS layer, "
        "       COUNT(DISTINCT p.source_file) AS docs, COUNT(*) AS chunks "
        "FROM pdf_chunks p LEFT JOIN knowledge_databases k ON k.id = p.db_id "
        "GROUP BY 1 ORDER BY 3 DESC"
    ) or []
    meta = db_scalar("SELECT COUNT(*) FROM literature_metadata", (), default=0) or 0
    quotable = db_scalar(
        "SELECT COUNT(DISTINCT p.source_file) FROM pdf_chunks p "
        "JOIN knowledge_databases k ON k.id = p.db_id WHERE k.slug = 'my-library'",
        (), default=0) or 0

    return JSONResponse({
        "ok": True,
        "layers": [dict(r) for r in layers],
        "documents": sum(r["docs"] for r in layers),
        "chunks": sum(r["chunks"] for r in layers),
        "library_total": meta,
        "library_quotable": quotable,
        "library_unquotable": max(0, meta - quotable),
        "quotable_pct": round(100.0 * quotable / meta, 1) if meta else 0.0,
    })


@router.get("/api/verify/debt")
async def verify_debt(limit: int = 20, artifact: str = ""):
    """The citation ledger, summarised — what has been checked and what failed."""
    try:
        from db import db_query
        from metis_mcp.tools import verification as v
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)[:150]}, status_code=503)

    where, params = "", []
    if artifact:
        where = "WHERE artifact_path LIKE ?"
        params = [f"%{artifact}%"]

    counts = db_query(
        f"SELECT verdict, COUNT(*) n FROM citation_checks {where} "
        "GROUP BY verdict ORDER BY n DESC", tuple(params)) or []
    placeholders = ",".join("?" * len(v.HARD_FAILURES))
    worst = db_query(
        f"SELECT verdict, source_cited, page_cited, doi, detail, artifact_path, "
        f"checked_at FROM citation_checks {where} "
        f"{'AND' if where else 'WHERE'} verdict IN ({placeholders}) "
        "ORDER BY checked_at DESC LIMIT ?",
        tuple(params + list(v.HARD_FAILURES) + [limit])) or []

    return JSONResponse({
        "ok": True,
        "total": sum(r["n"] for r in counts),
        "by_verdict": [dict(r) for r in counts],
        "hard_failures": [dict(r) for r in worst],
        "meaning": v.VERDICT_MEANING,
    })


@router.get("/api/partial/knowledge/quotable", response_class=HTMLResponse)
async def knowledge_quotable(request: Request):
    """The quotable-coverage panel for the Knowledge surface.

    The number belongs on the surface and not only in an endpoint: a denominator
    nobody sees does not stop an overclaim. Fails soft — if the counts cannot be
    read, the panel simply does not render rather than breaking the tab.
    """
    try:
        from db import db_query, db_scalar
        from main import templates
    except Exception as exc:
        log.warning("[verify] quotable panel imports failed: %s", exc)
        return HTMLResponse("")

    try:
        layers = db_query(
            "SELECT COALESCE(k.slug,'(unfiled)') AS layer, "
            "       COUNT(DISTINCT p.source_file) AS docs "
            "FROM pdf_chunks p LEFT JOIN knowledge_databases k ON k.id = p.db_id "
            "GROUP BY 1") or []
        meta = db_scalar("SELECT COUNT(*) FROM literature_metadata", (), default=0) or 0
        quotable = db_scalar(
            "SELECT COUNT(DISTINCT p.source_file) FROM pdf_chunks p "
            "JOIN knowledge_databases k ON k.id = p.db_id WHERE k.slug='my-library'",
            (), default=0) or 0
        prov = {
            "verified": db_scalar(
                "SELECT COUNT(*) FROM pdf_index_state WHERE provenance='verified'",
                (), default=0) or 0,
            "unresolved": db_scalar(
                "SELECT COUNT(*) FROM pdf_index_state WHERE provenance='unresolved'",
                (), default=0) or 0,
            "total": db_scalar("SELECT COUNT(*) FROM pdf_index_state", (), default=0) or 0,
        }
    except Exception as exc:
        # Say WHY. A panel that vanishes without a log line is the failure mode
        # this whole layer was built to remove.
        log.warning("[verify] quotable panel query failed: %s: %s",
                    type(exc).__name__, exc)
        return HTMLResponse("")

    cov = {
        "layers": [dict(r) for r in layers],
        "documents": sum(r["docs"] for r in layers),
        "library_total": meta,
        "library_quotable": quotable,
        "library_unquotable": max(0, meta - quotable),
        "quotable_pct": round(100.0 * quotable / meta, 1) if meta else 0.0,
    }
    return templates.TemplateResponse(
        request, "partials/knowledge_quotable.html", {"cov": cov, "prov": prov})
