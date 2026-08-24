#!/usr/bin/env python3
"""mine_hat_references.py — find the HAT papers your own library keeps citing
and you do not own.

WHY THIS IS DIFFERENT FROM A FEED
    A journal feed can only show you what was published this week. A topic search
    can only show you what matches words you thought of. Neither can surface the
    1997 paper that every single one of your sources cites — the foundational
    work you never explicitly went looking for because you assumed you had it.

    Reference mining inverts the question. Instead of "what is new?", it asks
    "what does my own corpus point at that I do not hold?" — and the answer is
    ranked by the strongest relevance signal available anywhere: how many of YOUR
    papers cite it. A DOI cited by forty of your sleeping-sickness papers is
    almost certainly something you should have. No keyword search produces that
    ordering, because the ranking comes from your library's own structure.

WHAT IT DOES
    1. Collects HAT seed DOIs from the catalogue (literature_metadata) — the
       papers you actually hold.
    2. Pulls each one's reference list from CrossRef.
    3. Drops anything already in the library or already in the review queue.
    4. Counts how many distinct seeds cite each survivor.
    5. Writes the top candidates into `new_publications` under the topic tag
       `hat-references`, so they appear in the HAT tab of New Literature with
       Add / Not interested — rather than in a markdown file nobody reopens.
    6. Also writes a report and a RIS file for direct Zotero import.

DELIBERATE LIMITS
    · One hop. References of references grow combinatorially and get noisy fast.
    · CrossRef only. It has reference lists for most publishers, but NOT all —
      Elsevier in particular often withholds them. So this is a floor on what is
      missing, never a complete picture, and the report says so.
    · Nothing is added to the catalogue. Candidates land in the review queue.

USAGE
    python3 tools/mine_hat_references.py --dry-run
    python3 tools/mine_hat_references.py --max-seeds 200 --min-citations 2
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAILTO = os.environ.get("UNPAYWALL_EMAIL", "metis@research-cortex.local")
UA = f"MetisRC/1.0 (mailto:{MAILTO})"

HAT_WORDS = ("trypanosom", "sleeping sickness", "tsetse", "glossina",
             "gambiense", "rhodesiense", "brucei", "nagana")

_HAT_SQL = " OR ".join(
    f"lower(title || ' ' || COALESCE(abstract,'') || ' ' || COALESCE(tags,'')) "
    f"LIKE '%{w}%'" for w in HAT_WORDS)


def db() -> sqlite3.Connection:
    c = sqlite3.connect(str(Path.home() / ".local/share/metis" / "metis.sqlite"))
    c.row_factory = sqlite3.Row
    return c


def norm_doi(d: str) -> str:
    d = (d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d.strip()


def crossref(doi: str) -> dict | None:
    try:
        req = urllib.request.Request(
            f"https://api.crossref.org/works/{urllib.parse.quote(doi)}",
            headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read()).get("message")
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-seeds", type=int, default=500)
    ap.add_argument("--min-citations", type=int, default=2,
                    help="how many of your papers must cite it to be reported")
    ap.add_argument("--top", type=int, default=150,
                    help="how many candidates to push into the review queue")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = db()

    # ── Seeds: HAT papers you actually hold ──────────────────────────────────
    seeds = [norm_doi(r["doi"]) for r in conn.execute(
        f"SELECT DISTINCT doi FROM literature_metadata "
        f"WHERE doi != '' AND ({_HAT_SQL})")]
    seeds = [s for s in seeds if s][:args.max_seeds]

    # ── What we already have, in either place ────────────────────────────────
    have = {norm_doi(r[0]) for r in conn.execute(
        "SELECT doi FROM literature_metadata WHERE doi != ''")}
    have |= {norm_doi(r[0]) for r in conn.execute(
        "SELECT doi FROM new_publications WHERE doi != ''")}
    have.discard("")

    # ALSO by title. 248 catalogue rows have no DOI at all — they came from
    # filename scans — so a DOI-only "have" set cannot see them. The first run of
    # this tool reported 212 missing papers of which 68 were already on the
    # shelf, including canonical ones like "Options for Field Diagnosis of HAT".
    # Telling a researcher he is missing a paper he owns is worse than saying
    # nothing: it costs him the time to go and check.
    have_titles: set[str] = set()
    for r in conn.execute("SELECT title FROM literature_metadata WHERE title IS NOT NULL"):
        k = re.sub(r"[^a-z0-9]+", " ", re.sub(r"<[^>]+>", " ", r[0] or "").lower()).strip()
        if len(k) >= 18:
            have_titles.add(k)

    print(f"seeds        : {len(seeds)} HAT papers with a DOI")
    print(f"already held : {len(have)} DOIs across catalogue + queue")
    print(f"mining references (CrossRef)…\n")

    cited_by: dict[str, set[str]] = defaultdict(set)   # missing doi -> seeds
    meta_cache: dict[str, dict] = {}
    no_refs = 0

    for i, seed in enumerate(seeds, 1):
        m = crossref(seed)
        if not m:
            continue
        refs = m.get("reference") or []
        if not refs:
            no_refs += 1
        for ref in refs:
            rd = norm_doi(ref.get("DOI", ""))
            if not rd or rd in have:
                continue
            cited_by[rd].add(seed)
        if i % 25 == 0:
            print(f"   {i}/{len(seeds)} seeds · {len(cited_by)} distinct "
                  f"missing DOIs so far")
        time.sleep(0.12)          # polite; CrossRef allows far more with a mailto

    ranked = sorted(cited_by.items(), key=lambda kv: -len(kv[1]))
    strong = [(d, s) for d, s in ranked if len(s) >= args.min_citations]

    print(f"\n{'=' * 70}")
    print(f"  seeds queried            : {len(seeds)}")
    print(f"  seeds with NO references : {no_refs}  (publisher withholds them)")
    print(f"  distinct missing DOIs    : {len(ranked)}")
    print(f"  cited by >= {args.min_citations} of your papers : {len(strong)}")
    print(f"{'=' * 70}\n")

    # ── Fetch metadata only for what we will actually report ─────────────────
    picks = strong[:args.top]
    print(f"fetching metadata for the top {len(picks)}…")
    rows = []
    for n, (doi, seeds_citing) in enumerate(picks, 1):
        m = meta_cache.get(doi) or crossref(doi)
        time.sleep(0.12)
        if not m:
            continue
        title = " ".join(m.get("title") or []) or ""
        if not title:
            continue
        authors = "; ".join(
            f"{a.get('family','')}, {a.get('given','')[:1]}."
            for a in (m.get("author") or [])[:8] if a.get("family"))
        journal = " ".join(m.get("container-title") or []) or ""
        parts = ((m.get("issued") or {}).get("date-parts") or [[None]])[0]
        year = str(parts[0]) if parts and parts[0] else ""
        rows.append({
            "doi": doi, "title": title[:500], "authors": authors[:400],
            "journal": journal[:200], "year": year,
            "n_citing": len(seeds_citing),
            "type": m.get("type", ""),
        })
        if n % 25 == 0:
            print(f"   {n}/{len(picks)}")

    # Only keep things that look like HAT-relevant literature. A seed's
    # reference list also contains statistics texts and unrelated methods
    # papers; those are real references but they are not the HAT gap.
    def hatish(r: dict) -> bool:
        hay = f"{r['title']} {r['journal']}".lower()
        return any(w in hay for w in HAT_WORDS)

    def already_held(r: dict) -> bool:
        k = re.sub(r"[^a-z0-9]+", " ",
                   re.sub(r"<[^>]+>", " ", r["title"]).lower()).strip()
        if k in have_titles:
            return True
        # A catalogue title may be a truncated filename stem, so allow
        # containment either way rather than requiring an exact match.
        return any(len(h) > 24 and (h in k or k[:60] in h) for h in have_titles)

    before_title_filter = len(rows)
    rows = [r for r in rows if not already_held(r)]
    if before_title_filter != len(rows):
        print(f"  {before_title_filter - len(rows)} dropped — already in your "
              f"catalogue under a title-only entry (no DOI recorded)")

    hat_rows = [r for r in rows if hatish(r)]
    other_rows = [r for r in rows if not hatish(r)]

    print(f"\n  of the top {len(rows)} resolved: {len(hat_rows)} are HAT-specific, "
          f"{len(other_rows)} are adjacent (methods, other diseases)\n")

    print("  MOST-CITED MISSING PAPERS (by your own corpus):")
    for r in hat_rows[:25]:
        print(f"   {r['n_citing']:>3}× cited  {r['year']:<5} {r['title'][:66]}")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    # ── Into the review queue, where the surface can act on them ─────────────
    now = datetime.now().isoformat(timespec="seconds")
    sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))
    try:
        from metis_mcp.tools.content_scan import publication_title_key
    except Exception:
        def publication_title_key(t):  # minimal fallback
            t = re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()
            return t if len(t) >= 18 else ""

    added = 0
    for r in hat_rows:
        tkey = publication_title_key(r["title"])
        if tkey and conn.execute(
                "SELECT 1 FROM new_publications WHERE title_key=? LIMIT 1",
                (tkey,)).fetchone():
            continue
        conn.execute(
            "INSERT INTO new_publications (title, journal, pub_date, doi, topic_tag,"
            " source_url, discovered_at, authors, abstract, feed_name, entry_kind,"
            " lane, relevance, pub_iso, pub_precision, title_key, relevance_note)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["title"], r["journal"], r["year"], r["doi"], "hat-references",
             f"https://doi.org/{r['doi']}", now, r["authors"], "",
             "reference mining", "article", "field",
             # Rank inside the tab by how many of his own papers cite it.
             min(0.99, 0.80 + 0.01 * r["n_citing"]),
             f"{r['year']}-01-01" if r["year"] else "", "year" if r["year"] else "",
             tkey, f"cited by {r['n_citing']} papers in your library"),
        )
        added += 1
    conn.commit()

    # ── Report + RIS ─────────────────────────────────────────────────────────
    out = ROOT / "outputs" / "reviews" / "librarian"
    out.mkdir(parents=True, exist_ok=True)
    today = datetime.now().date().isoformat()

    md = [f"# HAT reference mining — {today}", "",
          f"- Seeds: **{len(seeds)}** HAT papers from your catalogue",
          f"- Seeds whose publisher withholds reference lists: **{no_refs}**",
          f"- Distinct cited DOIs you do not hold: **{len(ranked)}**",
          f"- Cited by ≥{args.min_citations} of your papers: **{len(strong)}**",
          f"- Added to the review queue (HAT tab): **{added}**", "",
          "> CrossRef does not have reference lists for every publisher — Elsevier",
          "> in particular often withholds them. This is a FLOOR on what is",
          "> missing, not a complete picture.", "",
          "## Most cited by your own corpus", "",
          "| Cited by | Year | Title | Journal | DOI |",
          "|---|---|---|---|---|"]
    for r in hat_rows[:100]:
        t = r["title"].replace("|", "/")[:90]
        md.append(f"| {r['n_citing']} | {r['year']} | {t} | "
                  f"{r['journal'][:34]} | {r['doi']} |")
    if other_rows:
        md += ["", "## Adjacent (methods, other diseases) — not queued", "",
               "| Cited by | Year | Title |", "|---|---|---|"]
        for r in other_rows[:40]:
            md.append(f"| {r['n_citing']} | {r['year']} | "
                      f"{r['title'].replace('|','/')[:90]} |")
    (out / f"{today}_hat-reference-mining.md").write_text(
        "\n".join(md), encoding="utf-8")

    ris = []
    for r in hat_rows:
        ris += ["TY  - JOUR", f"TI  - {r['title']}"]
        ris += [f"AU  - {a.strip()}" for a in r["authors"].split(";") if a.strip()]
        if r["year"]:
            ris.append(f"PY  - {r['year']}")
        if r["journal"]:
            ris.append(f"JO  - {r['journal']}")
        ris += [f"DO  - {r['doi']}", "ER  - ", ""]
    (out / f"{today}_hat-reference-mining.ris").write_text(
        "\n".join(ris), encoding="utf-8")

    print(f"\n  ✓ {added} candidate(s) added to the HAT tab of New Literature")
    print(f"  ✓ report: outputs/reviews/librarian/{today}_hat-reference-mining.md")
    print(f"  ✓ RIS   : outputs/reviews/librarian/{today}_hat-reference-mining.ris")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
