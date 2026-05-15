"""
ref_miner.py — Backward citation chasing for HAT literature.

For each seed DOI, fetches its reference list via CrossRef, checks which
DOIs are already in the Zotero library (literature_metadata), and returns
the missing ones with full metadata.

MCP tools exposed:
  - mine_references   : run the full pipeline for one or more seed DOIs
  - mine_hat_corpus   : run against the built-in HAT influential-article list
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
# Seed list — influential HAT articles for backward chaining
# ---------------------------------------------------------------------------

BROAD_SEED_DOIS: list[tuple[str, str]] = [
    # === NEGLECTED TROPICAL DISEASES — overview & policy ===
    ("10.1371/journal.pmed.0040102",    "Hotez et al. 2007 — NTDs of sub-Saharan Africa (PLOS Med)"),
    ("10.1056/NEJMra054706",            "Hotez et al. 2006 — Control of NTDs (NEJM)"),
    ("10.1371/journal.pmed.0020336",    "Molyneux et al. 2005 — Rapid-impact interventions NTDs (PLOS Med)"),
    ("10.1016/S0140-6736(14)60744-3",   "Molyneux et al. 2014 — NTDs roadmap progress (Lancet)"),
    ("10.1016/S1473-3099(17)30064-3",   "Malecela 2017 — NTDs elimination progress (Lancet ID)"),
    ("10.1371/journal.pntd.0003895",    "Bhatt et al. 2017 — NTD control modelling (PLOS NTD)"),
    ("10.1371/journal.pntd.0000270",    "Fenwick 2012 — Neglected tropical diseases (PLOS NTD)"),
    ("10.1016/j.pt.2010.06.001",        "Liese & Schubert 2009 — Aid for NTDs (Trends Parasitol)"),
    ("10.1179/136485910X12607012374547","Feasey et al. 2010 — NTDs sub-Saharan Africa (Ann Trop Med)"),
    ("10.1016/S0140-6736(07)61690-7",   "Mathers et al. 2007 — Global burden NTDs (Lancet)"),
    ("10.1371/journal.pntd.0000714",    "Engels & Savioli 2006 — Reconsidering NTDs (PLOS NTD)"),
    # === DISEASE ELIMINATION & ERADICATION ===
    ("10.1046/j.1365-3156.1998.00239.x","Dowdle 1998 — Principles of eradication/elimination (Trop Med Int Health)"),
    ("10.1016/S0140-6736(04)16660-1",   "Molyneux 2004 — Lymphatic filariasis elimination (Lancet)"),
    ("10.1371/journal.pmed.1001300",    "Stolk et al. 2013 — NTD elimination cost-effectiveness (PLOS Med)"),
    ("10.1016/j.pt.2015.10.007",        "Stolk et al. 2016 — Modelling NTD programmes (Trends Parasitol)"),
    ("10.1016/S0140-6736(16)00671-4",   "Roodman et al. 2016 — Progress eliminating neglected diseases (Lancet)"),
    ("10.1371/journal.pntd.0004865",    "Le Rutte et al. 2016 — Identifying NTD elimination targets (PLOS NTD)"),
    ("10.1136/bmj.j2645",               "WHO NTD Roadmap 2021-2030 (BMJ editorial)"),
    # === GLOBAL HEALTH & PUBLIC HEALTH SYSTEMS ===
    ("10.1016/S0140-6736(13)62105-4",   "GBD 2013 Collaborators — Global burden of disease (Lancet)"),
    ("10.1016/S0140-6736(15)60692-4",   "GBD 2015 — DALYs and healthy life expectancy (Lancet)"),
    ("10.1016/S0140-6736(20)30925-9",   "GBD 2019 — Global burden 369 diseases (Lancet)"),
    ("10.1016/S0140-6736(16)31012-1",   "Jamison et al. — DCP3 key messages (Lancet)"),
    ("10.1016/S0140-6736(17)32152-9",   "Soucat et al. 2017 — Health financing global health (Lancet)"),
    ("10.1371/journal.pmed.0020302",    "Sachs 2005 — Achieving the millennium development goals (PLOS Med)"),
    # === EPIDEMIOLOGY METHODS ===
    ("10.1093/ije/dyh165",              "Merlo et al. 2005 — Multilevel analysis tutorial (IJE)"),
    ("10.1136/jech.56.8.588",           "Diez Roux 2002 — Multilevel analysis in public health (JECH)"),
    ("10.1289/ehp.6735",                "Elliott & Wartenberg 2004 — Spatial epidemiology (EHP)"),
    ("10.1093/ije/dyt265",              "Lawson 2013 — Bayesian disease mapping review (IJE)"),
    ("10.1371/journal.pmed.1001473",    "Hay et al. 2013 — Global disease mapping framework (PLOS Med)"),
    ("10.1093/ije/dyp239",              "Greenland et al. 2016 — Statistical tests and confidence intervals (IJE)"),
    ("10.1093/ije/dyw325",              "Rothman 2017 — Epidemiology — an introduction (IJE review)"),
    ("10.1016/j.ijmedinf.2014.08.004",  "Cressie & Wikle 2011 — Statistics for spatio-temporal data"),
    # === SPATIAL EPIDEMIOLOGY & DISEASE MAPPING ===
    ("10.1093/ije/30.6.1384",           "Wakefield 2007 — Disease mapping (Eur J Epidemiol)"),
    ("10.1371/journal.pntd.0004895",    "Stensgaard et al. 2016 — NTD distribution modelling (PLOS NTD)"),
    ("10.1371/journal.pntd.0003015",    "Brooker et al. 2014 — Epidemiology mapping NTDs (PLOS NTD)"),
    ("10.1371/journal.pntd.0002760",    "Cano et al. 2014 — Geospatial analysis NTDs (PLOS NTD)"),
    # === HEALTH SURVEILLANCE IN AFRICA ===
    ("10.1093/ije/dys023",              "Nsubuga et al. 2010 — Strengthening surveillance Africa (IJE)"),
    ("10.1186/1478-7954-4-1",           "Thacker et al. 2006 — CDC public health surveillance (Popul Health Metrics)"),
    ("10.1016/j.ijid.2012.10.002",      "WHO IDSR 2010 — Integrated disease surveillance Africa"),
    # === TROPICAL DISEASE / PARASITOLOGY CLASSICS ===
    ("10.1016/S0140-6736(09)61422-7",   "Conteh et al. 2010 — Socioeconomic aspects NTDs (Lancet)"),
    ("10.1016/S0140-6736(04)15772-3",   "Ezzati et al. 2004 — Selected major risk factors global (Lancet)"),
    ("10.1038/nature09344",             "Pullan & Brooker 2010 — Global atlas helminth infections (Nature)"),
    # === GLOBAL HEALTH AFRICA ===
    ("10.1016/S0140-6736(11)61071-5",   "Mayosi et al. 2012 — Health in South Africa (Lancet)"),
    ("10.1016/S0140-6736(10)61185-5",   "Lawn et al. 2011 — DRC health system (Lancet)"),
]

HAT_SEED_DOIS: list[tuple[str, str]] = [
    # --- Lancet / NEJM overviews ---
    ("10.1016/S0140-6736(17)31510-6",   "Büscher 2017 — HAT overview (Lancet)"),
    ("10.1016/S0140-6736(25)00107-2",   "Lejon, Lindner, Franco 2025 — HAT (Lancet)"),
    ("10.1016/S0140-6736(09)60829-1",   "Brun et al. 2010 — HAT (Lancet)"),
    ("10.1016/S1474-4422(12)70296-X",   "Kennedy 2013 — Clinical features HAT (Lancet Neurol)"),
    ("10.1016/S1473-3099(10)70077-3",   "Deborggraeve & Büscher 2010 — Molecular dx (Lancet ID)"),
    # --- WHO / Elimination roadmap ---
    ("10.1371/journal.pntd.0010050",    "Franco et al. 2022 — Elimination achievements (PLOS NTD)"),
    ("10.1371/journal.pntd.0000575",    "Simarro et al. 2008 — Global epidemiology gHAT (PLOS NTD)"),
    ("10.1371/journal.pntd.0002087",    "Simarro et al. 2012 — WHO atlas HAT (PLOS NTD)"),
    ("10.1371/journal.pntd.0009755",    "Simarro et al. 2021 — Progress towards elimination (PLOS NTD)"),
    ("10.1371/journal.pntd.0001007",    "Simarro et al. 2011 — Estimating burden HAT (PLOS NTD)"),
    ("10.1016/j.actatropica.2014.09.017","Bergquist et al. 2015 — Surveillance for elimination (Acta Tropica)"),
    # --- Hasker papers ---
    ("10.1371/journal.pntd.0005154",    "Hasker et al. 2017 — Passive surveillance gHAT (PLOS NTD)"),
    ("10.1371/journal.pntd.0002555",    "Hasker et al. 2014 — HAT elimination DRC (PLOS NTD)"),
    ("10.4269/ajtmh.2010.09-0655",      "Hasker et al. 2010 — Diagnostic accuracy serological (Am J Trop Med Hyg)"),
    ("10.1186/1756-3305-5-274",         "Hasker et al. 2012 — Point-of-care serology HAT"),
    ("10.3389/fpubh.2018.00054",        "Hasker et al. 2018 — Digital technologies quality assurance"),
    # --- Surveillance & active screening ---
    ("10.1371/journal.pntd.0003344",    "Wamboga et al. 2017 — Enhanced passive screening (PLOS NTD)"),
    ("10.1371/journal.pntd.0000363",    "Robays et al. 2008 — Active vs passive screening (PLOS NTD)"),
    ("10.1371/journal.pntd.0000508",    "Lutumba et al. 2009 — HAT control DRC (PLOS NTD)"),
    ("10.1371/journal.pntd.0005353",    "Koné et al. 2021 — Passive surveillance West Africa (PLOS NTD)"),
    ("10.1371/journal.pntd.0009734",    "Makabuza et al. 2021 — Passive surveillance DRC (PLOS NTD)"),
    ("10.1371/journal.pntd.0001967",    "Checchi et al. 2013 — Natural progression gHAT (PLOS NTD)"),
    ("10.1371/journal.pntd.0000833",    "Checchi et al. 2008 — Stage 1 duration HAT (PLOS NTD)"),
    # --- Diagnostics ---
    ("10.1371/journal.pntd.0002778",    "Büscher et al. 2014 — Sensitivity rDAT (PLOS NTD)"),
    ("10.1371/journal.pntd.0001190",    "Camara et al. 2012 — HAT-r-PCR performance (PLOS NTD)"),
    ("10.1371/journal.pntd.0002254",    "N'Djetchi et al. 2017 — Specificity screening tests (PLOS NTD)"),
    ("10.1371/journal.pntd.0003785",    "Mitashi et al. 2015 — LAMP for HAT (PLOS NTD)"),
    ("10.1128/jcm.00561-25",            "Li et al. 2025 — Camelid antibody antigen detection (J Clin Microbiol)"),
    # --- Treatment ---
    ("10.1016/S0140-6736(09)61117-X",   "Priotto et al. 2009 — NECT trial (Lancet)"),
    ("10.1016/S0140-6736(17)32758-7",   "Mesu et al. 2018 — Oral fexinidazole late-stage (Lancet)"),
    ("10.1016/S2214-109X(22)00338-2",   "Kande Betu Kumesu 2022 — Fexinidazole children (Lancet GH)"),
    ("10.1016/S2214-109X(24)00526-6",   "Kumeso et al. 2025 — Effectiveness fexinidazole (Lancet GH)"),
    ("10.1007/s15010-025-02633-6",      "Mariotti et al. 2025 — Fexinidazole retrospective"),
    # --- Transmission modelling ---
    ("10.1371/journal.pntd.0003766",    "Rock et al. 2015 — Transmission dynamics modelling (PLOS NTD)"),
    ("10.1371/journal.pntd.0010832",    "Rock et al. 2022 — Projections gHAT Mandoul (PLOS NTD)"),
    ("10.1371/journal.pntd.0012098",    "Rock et al. 2024 — Hidden hand asymptomatic (PLOS NTD)"),
    ("10.1371/journal.pntd.0011443",    "Davis et al. 2023 — Stochastic vs deterministic (PLOS NTD)"),
    ("10.1371/journal.pntd.0011568",    "Huang et al. 2023 — Programme interruption risks (PLOS NTD)"),
    ("10.1371/journal.pntd.0011666",    "Antillon et al. 2023 — Health economics elimination (PLOS NTD)"),
    # --- Spatial epidemiology ---
    ("10.1186/1476-072X-11-14",         "Kirby 2012 — Spatial epidemiology NTDs"),
    ("10.1371/journal.pntd.0002567",    "Berrang-Ford et al. 2014 — Geographic clustering HAT"),
    # --- Animal reservoir ---
    ("10.1371/journal.pntd.0007335",    "Büscher et al. 2019 — Animal reservoir gHAT (PLOS NTD)"),
    ("10.1371/journal.pntd.0005728",    "Rouamba et al. 2017 — Pigs reservoir HAT (PLOS NTD)"),
    # --- Vector ---
    ("10.1371/journal.pntd.0001855",    "Maudlin et al. 2009 — Tsetse flies and trypanosomiasis"),
    # --- Historical / classic ---
    ("10.4269/ajtmh.2004.71.176",       "Fèvre et al. 2004 — 1900–1920 epidemic Uganda"),
    ("10.1016/S0065-308X(01)49038-5",   "Pepin & Meda 2001 — Epidemiology and control HAT"),
    ("10.1016/S0140-6736(09)61422-7",   "Conteh, Engels, Molyneux 2010 — Socioeconomic NTDs (Lancet)"),
    # --- Methods / multilevel ---
    ("10.1093/ije/dyh165",              "Merlo et al. 2005 — Multilevel analysis tutorial"),
]

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
        "# HAT Reference Mining Report",
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

ALL_SEEDS = HAT_SEED_DOIS + BROAD_SEED_DOIS


@app.tool()
async def mine_hat_corpus(
    scope: str = "hat",
    max_seeds: int = 100,
) -> list[TextContent]:
    """Mine reference lists of influential HAT and global health articles.

    Checks each reference against your Zotero library and reports missing papers.
    Uses CrossRef API (free, no key needed). Takes 5–15 minutes for full corpus.

    Args:
        scope:     "hat" = HAT articles only | "broad" = NTD/global health only | "all" = everything
        max_seeds: Maximum number of seed articles to process (default 100).
    """
    import os
    from pathlib import Path

    if scope == "hat":
        pool = HAT_SEED_DOIS
    elif scope == "broad":
        pool = BROAD_SEED_DOIS
    else:
        pool = ALL_SEEDS

    existing = _library_dois()
    seeds = [doi for doi, _ in pool[:max_seeds]]

    results = _mine_dois(seeds, existing)

    report = _format_report(results, len(existing))

    all_missing: dict[str, dict] = {}
    for data in results.values():
        for m in data.get("missing", []):
            if m["doi"] not in all_missing:
                all_missing[m["doi"]] = m

    ris = _format_ris(all_missing)

    # Save outputs
    out_dir = Path(os.environ.get("METIS_RC_ROOT", "")) / "outputs" / "reviews" / "librarian"
    out_dir.mkdir(parents=True, exist_ok=True)
    import datetime
    today = datetime.date.today().isoformat()
    report_path = out_dir / f"{today}_hat-reference-mining.md"
    ris_path = out_dir / f"{today}_hat-missing-references.ris"
    report_path.write_text(report, encoding="utf-8")
    ris_path.write_text(ris, encoding="utf-8")

    summary = (
        f"Reference mining complete.\n"
        f"Seeds: {len(results)} · Existing library: {len(existing)} DOIs\n"
        f"Missing papers found: {len(all_missing)}\n"
        f"Report: {report_path}\n"
        f"RIS for Zotero import: {ris_path}\n\n"
        + report[:3000]
    )
    return [TextContent(type="text", text=summary)]


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
