#!/usr/bin/env python3
"""verify_citations.py — the artifact gate. Check what a document actually cites.

WHY A SEPARATE CLI AND NOT JUST THE MCP TOOL
    Conversation and artifacts deserve different treatment, and conflating them
    is how verification gets switched off:

      · A wrong claim in chat is cheap — the next sentence corrects it. So
        conversation gets ASYNC ANNOTATION (the Stop hook records to the ledger).
      · A wrong claim written into a course, a manuscript, or `outputs/` is
        durable. It propagates for months and nobody re-reads it. So artifacts
        get a HARD GATE — this file, which exits non-zero.

    A gate that added seconds to every conversational turn would be disabled
    within a week, and then nothing would be verified at all.

WHAT IT CHECKS
    Tier A (default, offline, free): is the cited document indexed, does the
    cited page exist, do the claim's figures and quoted strings appear on it.
    Deterministic — there is no model in the path, so it cannot invent a verdict.

    Tier B (--doi, network): does each DOI resolve at Crossref, does it match the
    citation, and IS IT RETRACTED. Metadata only; nothing local is transmitted.

THE FIRST JOB IT HAS
    The AI in Public Health course — 16 lessons, 97 questions — shipped with the
    note "every citation is an unverified lead", because verification results had
    nowhere to accumulate and no one mechanism to produce them.

USAGE
    python3 tools/verify_citations.py knowledge/courses/ai-in-public-health
    python3 tools/verify_citations.py outputs/reviews/ --doi
    python3 tools/verify_citations.py draft.md --quiet      # exit code only

EXIT CODES
    0  no hard failures
    1  at least one citation points at a page that does not contain the claim,
       or at a retracted or non-existent DOI
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "system" / "mcp-server" / "src"))
os.environ.setdefault("METIS_RC_ROOT", str(_ROOT))
# The scholarly APIs sit behind the ITG proxy, which re-signs TLS with a local
# root CA that certifi does not carry. Same fix as run.sh.
_CA = "/etc/ssl/certs/ca-certificates.crt"
if os.path.isfile(_CA):
    os.environ.setdefault("SSL_CERT_FILE", _CA)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _CA)

from metis_mcp.tools.verification import (  # noqa: E402
    HARD_FAILURES, VERDICT_MEANING, check_claim, check_doi,
    extract_citations, find_unverifiable_references, record_check,
    reference_in_library,
)

_EXTS = {".md", ".qmd", ".html", ".txt", ".rmd"}
# Course and output trees carry generated siblings; checking a rendered copy of
# a file already checked doubles the ledger and the noise.
_SKIP_DIRS = {"_site", "_book", "node_modules", ".git", "__pycache__", ".quarto",
              "site_libs", "_freeze"}


def _targets(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    out = []
    for p in sorted(path.rglob("*")):
        if p.is_dir() or p.suffix.lower() not in _EXTS:
            continue
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verify the citations in a document or tree against the corpus.")
    ap.add_argument("path", help="file or directory to check")
    ap.add_argument("--doi", action="store_true",
                    help="also resolve DOIs at Crossref and check for retractions "
                         "(requires network; metadata only)")
    ap.add_argument("--no-record", action="store_true",
                    help="do not write verdicts to the citation ledger")
    ap.add_argument("--quiet", action="store_true", help="exit code only")
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"not found: {root}", file=sys.stderr)
        return 2

    files = _targets(root)
    if not files:
        print(f"no checkable files under {root}", file=sys.stderr)
        return 2

    counts: dict[str, int] = {}
    hard: list[tuple[Path, dict]] = []
    checked = files_with_cites = 0
    # THE DENOMINATOR. Counted for every file, whether or not it has a checkable
    # citation, because the number that matters is what the report did NOT cover.
    ref_counts: dict[str, int] = {}
    uncheckable = 0

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for ref in find_unverifiable_references(text):
            uncheckable += 1
            v = reference_in_library(ref)["verdict"]
            ref_counts[v] = ref_counts.get(v, 0) + 1

        cites = extract_citations(text)
        if not cites:
            continue
        files_with_cites += 1
        rel = str(f.relative_to(_ROOT)) if str(f).startswith(str(_ROOT)) else str(f)

        for c in cites:
            if c.get("doi"):
                if not args.doi:
                    res = {**c, "tier": "B", "verdict": "doi_unchecked",
                           "detail": "re-run with --doi to resolve"}
                else:
                    res = {**c, **check_doi(c["doi"])}
            else:
                res = {**c, **check_claim(c["claim"], c["source"], c["page"],
                                          c.get("quote", ""))}
            checked += 1
            v = res["verdict"]
            counts[v] = counts.get(v, 0) + 1
            if v in HARD_FAILURES:
                hard.append((f, res))
            if not args.no_record:
                record_check(res, artifact_path=rel)

    if args.quiet:
        return 1 if hard else 0

    print(f"\n  {root}")
    print(f"  {len(files)} file(s) scanned · {files_with_cites} with citations · "
          f"{checked} citation(s) checked\n")

    if not checked:
        print("  No citation states a source and a page, so Tier A has nothing to")
        print("  test. That is NOT a clean bill of health — it means the prose")
        print("  makes claims without pointing at anything checkable.\n")
        return 0

    width = max(len(v) for v in counts)
    for v, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        flag = "  <-- HARD" if v in HARD_FAILURES else ""
        print(f"  {n:>4}  {v:<{width}}  {VERDICT_MEANING.get(v, '')}{flag}")

    if hard:
        print(f"\n  {len(hard)} HARD FAILURE(S) — the cited page does not contain "
              f"what was claimed:\n")
        for f, r in hard[:40]:
            loc = f"p.{r['page']}" if r.get("page") else (r.get("doi") or "")
            try:
                name = f.relative_to(_ROOT)
            except ValueError:
                name = f
            print(f"    {name}")
            print(f"      {r['verdict']} · {(r.get('source') or r.get('doi') or '')[:70]} {loc}")
            print(f"      {(r.get('detail') or '')[:150]}")
            print(f"      claim: {(r.get('claim') or '')[:150]}\n")
        if len(hard) > 40:
            print(f"    … and {len(hard) - 40} more (all recorded in the ledger)\n")
    else:
        print("\n  No hard failures.\n")

    if not args.doi and counts.get("doi_unchecked"):
        print(f"  {counts['doi_unchecked']} DOI(s) not resolved — re-run with --doi "
              f"to check existence and retractions.\n")

    unquotable = counts.get("source_not_indexed", 0)
    if unquotable:
        print(f"  {unquotable} citation(s) name a source that is not in the corpus.")
        print("  Those are ATTRIBUTED, not quoted: Metis cannot verify a page in")
        print("  them. Index the document to make them checkable.\n")

    # ── The denominator, always printed ───────────────────────────────────────
    # Without this the report reads as a clean bill of health for the whole
    # bibliography, when it covered only the citations that named a DOI or a
    # page. On the AI in Public Health course that was 18 of ~187.
    if uncheckable:
        total = checked + uncheckable
        pct = 100.0 * checked / total if total else 0.0
        print(f"  COVERAGE — {checked} of {total} citation-shaped items were")
        print(f"  checkable as written ({pct:.0f}%). The other {uncheckable} carry no DOI,")
        print("  page pointer, PMID or arXiv id, so nothing deterministic can be")
        print("  said about what they claim. Of those:\n")
        for v, n in sorted(ref_counts.items(), key=lambda kv: -kv[1]):
            print(f"    {n:>4}  {v:<28}{VERDICT_MEANING.get(v, '')}")
        print()
        print("  This is a report about what was checked, not a clean bill of health.")
        print("  To make a reference checkable: add its DOI, or cite a page in a")
        print("  document that is indexed.\n")

    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
