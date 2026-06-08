"""
ref_miner.py — Backward citation chasing for domain literature.

For each seed DOI, fetches its reference list via CrossRef, checks which
DOIs are already in the Zotero library (literature_metadata), and returns
the missing ones with full metadata.

MCP tools exposed:
  - mine_references   : run the full pipeline for one or more seed DOIs
"""

from __future__ import annotations

import re
import time
from sqlite3 import connect as sqlite_connect

import requests

from metis_mcp.app_instance import app
from metis_mcp.config import paths
from mcp.types import TextContent

# ---------------------------------------------------------------------------
# (A curated seed corpus formerly lived here but was unused dead code. Pass seed
#  DOIs directly to mine_references(dois="10.x/...,10.y/..."). Keep your own
#  curated seeds in a local file if you like — nothing here reads them.)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# CrossRef helpers
# ---------------------------------------------------------------------------

CROSSREF_BASE = "https://api.crossref.org/works"
HEADERS = {"User-Agent": "MetisResearchCortex/1.0 (https://github.com/SVerITG/Metis)"}


def _normalize_doi(doi: str) -> str:
    """Strip URL prefix and lowercase."""
    doi = doi.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi.lower()


def _crossref_metadata(doi: str) -> dict | None:
    """Fetch CrossRef metadata for a DOI. Returns None on failure."""
    url = f"{CROSSREF_BASE}/{requests.utils.quote(doi, safe='')}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json().get("message", {})
    except Exception:
        pass
    return None


def _extract_refs_from_crossref(meta: dict) -> list[str]:
    """Extract referenced DOIs from a CrossRef work metadata object."""
    refs = meta.get("reference", [])
    dois = []
    for ref in refs:
        doi = ref.get("DOI") or ref.get("doi")
        if doi:
            dois.append(_normalize_doi(doi))
    return dois


def _library_dois() -> set[str]:
    """Return the set of normalised DOIs already in literature_metadata."""
    if not paths.db.exists():
        return set()
    with sqlite_connect(str(paths.db)) as conn:
        cur = conn.execute(
            "SELECT doi FROM literature_metadata WHERE doi IS NOT NULL AND doi != ''"
        )
        return {_normalize_doi(row[0]) for row in cur.fetchall()}


def _crossref_title_authors_year(meta: dict) -> tuple[str, str, str]:
    """Extract title, first-author surname, year from CrossRef metadata."""
    titles = meta.get("title", [])
    title = titles[0] if titles else "Unknown title"
    authors = meta.get("author", [])
    if authors:
        first = authors[0]
        author_str = first.get("family", first.get("name", ""))
        if len(authors) > 1:
            author_str += " et al."
    else:
        author_str = ""
    date_parts = meta.get("published", meta.get("published-print", meta.get("issued", {})))
    parts = date_parts.get("date-parts", [[""]])
    year = str(parts[0][0]) if parts and parts[0] else ""
    journal = ""
    for key in ("container-title", "short-container-title"):
        ct = meta.get(key, [])
        if ct:
            journal = ct[0]
            break
    return title, author_str, year, journal


# ---------------------------------------------------------------------------
# Core mining function
# ---------------------------------------------------------------------------

def _mine_dois(seed_dois: list[str], existing_dois: set[str]) -> dict:
    """
    For each seed DOI, fetch references via CrossRef.
    Returns {seed_doi: {found, missing, errors}}.
    """
    results = {}
    for doi in seed_dois:
        doi_norm = _normalize_doi(doi)
        meta = _crossref_metadata(doi_norm)
        if not meta:
            results[doi_norm] = {"error": "CrossRef lookup failed", "missing": []}
            time.sleep(0.3)
            continue

        ref_dois = _extract_refs_from_crossref(meta)
        missing = []
        for ref_doi in ref_dois:
            if ref_doi not in existing_dois:
                # Fetch metadata for the missing paper
                ref_meta = _crossref_metadata(ref_doi)
                time.sleep(0.15)
                if ref_meta:
                    title, author, year, journal = _crossref_title_authors_year(ref_meta)
                    missing.append({
                        "doi": ref_doi,
                        "title": title,
                        "author": author,
                        "year": year,
                        "journal": journal,
                    })
                else:
                    missing.append({"doi": ref_doi, "title": "?", "author": "", "year": "", "journal": ""})
            time.sleep(0.1)

        seed_title, seed_author, seed_year, _ = _crossref_title_authors_year(meta)
        results[doi_norm] = {
            "seed_title": seed_title,
            "seed_author": seed_author,
            "seed_year": seed_year,
            "total_refs": len(ref_dois),
            "missing": missing,
        }
        time.sleep(0.5)

    return results


def _format_report(results: dict, existing_count: int) -> str:
    """Format mining results as a markdown report."""
    all_missing: dict[str, dict] = {}
    for seed, data in results.items():
        for m in data.get("missing", []):
            if m["doi"] not in all_missing:
                all_missing[m["doi"]] = m

    lines = [
        "# Domain Reference Mining Report",
        "",
        f"**Seeds analysed:** {len(results)}  ",
        f"**Already in library:** {existing_count}  ",
        f"**Unique missing papers found:** {len(all_missing)}",
        "",
    ]

    # Per-seed summary
    lines += ["## Per-seed summary", ""]
    lines += ["| Seed | Year | Refs | Missing |", "|---|---|---|---|"]
    for doi, data in results.items():
        if "error" in data:
            lines.append(f"| {doi} | — | ERROR | — |")
        else:
            lines.append(
                f"| {data.get('seed_author','')} — {data.get('seed_title','')[:55]} "
                f"| {data.get('seed_year','')} "
                f"| {data.get('total_refs', 0)} "
                f"| {len(data.get('missing', []))} |"
            )

    # Full missing list
    lines += ["", "## Missing papers — import into Zotero", ""]
    if all_missing:
        lines += ["| Year | Authors | Title | Journal | DOI |", "|---|---|---|---|---|"]
        for m in sorted(all_missing.values(), key=lambda x: x.get("year", "") or "", reverse=True):
            title = (m.get("title") or "")[:70]
            lines.append(
                f"| {m.get('year','')} "
                f"| {m.get('author','')} "
                f"| {title} "
                f"| {m.get('journal','')[:40]} "
                f"| {m.get('doi','')} |"
            )
    else:
        lines.append("*No missing papers found — library is complete for these seeds.*")

    return "\n".join(lines)


def _format_ris(all_missing: dict[str, dict]) -> str:
    """Format missing papers as RIS for Zotero import."""
    lines = []
    for m in all_missing.values():
        lines += [
            "TY  - JOUR",
            f"TI  - {m.get('title', '')}",
            f"AU  - {m.get('author', '')}",
            f"PY  - {m.get('year', '')}",
            f"JO  - {m.get('journal', '')}",
            f"DO  - {m.get('doi', '')}",
            "ER  - ",
            "",
        ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@app.tool()
async def mine_references(dois: str, label: str = "") -> list[TextContent]:
    """Mine reference lists of specific articles.

    Fetches references for one or more DOIs (comma-separated) via CrossRef,
    checks against your Zotero library, and reports what's missing.

    Args:
        dois:  Comma-separated list of DOIs to mine.
        label: Optional label for the output file.
    """
    import datetime, os
    from pathlib import Path

    seed_list = [d.strip() for d in dois.split(",") if d.strip()]
    if not seed_list:
        return [TextContent(type="text", text="No DOIs provided.")]

    existing = _library_dois()
    results = _mine_dois(seed_list, existing)
    report = _format_report(results, len(existing))

    all_missing: dict[str, dict] = {}
    for data in results.values():
        for m in data.get("missing", []):
            if m["doi"] not in all_missing:
                all_missing[m["doi"]] = m

    ris = _format_ris(all_missing)
    out_dir = Path(os.environ.get("METIS_RC_ROOT", "")) / "outputs" / "reviews" / "librarian"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    slug = label.lower().replace(" ", "-")[:30] or "custom"
    report_path = out_dir / f"{today}_ref-mining-{slug}.md"
    ris_path = out_dir / f"{today}_ref-mining-{slug}.ris"
    report_path.write_text(report, encoding="utf-8")
    ris_path.write_text(ris, encoding="utf-8")

    return [TextContent(type="text", text=
        f"Done. {len(seed_list)} seeds · {len(all_missing)} missing papers.\n"
        f"Report: {report_path}\n"
        f"RIS: {ris_path}\n\n" + report[:2000]
    )]
