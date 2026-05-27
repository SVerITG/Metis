#!/usr/bin/env python3
"""
extract_pdf_metadata.py — Batch PDF metadata extractor

Reads a folder of PDF papers and outputs a CSV with:
  title, authors, year, DOI, abstract

Usage:
  python extract_pdf_metadata.py <folder> [options]

Options:
  -o, --output   Output CSV path (default: pdf_metadata.csv)
  --crossref     Enrich missing metadata via Crossref API (requires internet)
  --max-abstract Maximum characters for abstract (default: 1500)
  --recursive    Scan subfolders recursively (default: False)
  -v, --verbose  Print progress for each file

Requirements (any one of):
  pip install pymupdf         # PyMuPDF — fastest, best layout
  pip install pypdf           # pure Python fallback
  pip install pdfminer.six    # alternative fallback

Install all three for best coverage:
  pip install pymupdf pypdf pdfminer.six requests
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PaperMeta:
    filepath: str = ""
    filename: str = ""
    title: str = ""
    authors: str = ""
    year: str = ""
    doi: str = ""
    abstract: str = ""
    source: str = ""   # where metadata came from: pdf_meta / text_parse / crossref / filename
    warnings: str = ""

    def csv_row(self) -> dict:
        return {
            "filepath": self.filepath,
            "filename": self.filename,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "abstract": self.abstract,
            "source": self.source,
            "warnings": self.warnings,
        }

CSV_FIELDS = ["filepath", "filename", "title", "authors", "year", "doi", "abstract", "source", "warnings"]


# ---------------------------------------------------------------------------
# PDF extraction backends — tried in order: PyMuPDF > pypdf > pdfminer
# ---------------------------------------------------------------------------

def _try_pymupdf(pdf_path: Path, max_abstract: int) -> Optional[PaperMeta]:
    """Extract metadata + text using PyMuPDF (fitz)."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open(str(pdf_path))
        raw_meta = doc.metadata or {}

        # Get full text of first 3 pages for parsing
        pages_text = []
        for i, page in enumerate(doc):
            if i >= 3:
                break
            pages_text.append(page.get_text())
        full_text = " ".join(pages_text)
        full_text = re.sub(r"\s+", " ", full_text).strip()
        doc.close()

        meta = PaperMeta(
            filepath=str(pdf_path),
            filename=pdf_path.name,
            source="pdf_meta",
        )

        # Prefer embedded metadata
        meta.title = _clean(raw_meta.get("title", ""))
        meta.authors = _clean(raw_meta.get("author", ""))

        creation = raw_meta.get("creationDate", "") or raw_meta.get("modDate", "")
        meta.year = _extract_year_from_date(creation)

        # Parse text to fill in gaps
        _enrich_from_text(meta, full_text, max_abstract)
        return meta

    except ImportError:
        return None
    except Exception as e:
        return None


def _try_pypdf(pdf_path: Path, max_abstract: int) -> Optional[PaperMeta]:
    """Extract metadata + text using pypdf."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        raw_meta = reader.metadata or {}

        pages_text = []
        for i, page in enumerate(reader.pages):
            if i >= 3:
                break
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                pass
        full_text = " ".join(pages_text)
        full_text = re.sub(r"\s+", " ", full_text).strip()

        meta = PaperMeta(
            filepath=str(pdf_path),
            filename=pdf_path.name,
            source="pdf_meta",
        )

        meta.title = _clean(raw_meta.get("/Title", "") or raw_meta.get("title", ""))
        meta.authors = _clean(raw_meta.get("/Author", "") or raw_meta.get("author", ""))

        creation = (
            raw_meta.get("/CreationDate", "")
            or raw_meta.get("/ModDate", "")
            or raw_meta.get("creationDate", "")
            or ""
        )
        meta.year = _extract_year_from_date(str(creation))

        _enrich_from_text(meta, full_text, max_abstract)
        return meta

    except ImportError:
        return None
    except Exception:
        return None


def _try_pdfminer(pdf_path: Path, max_abstract: int) -> Optional[PaperMeta]:
    """Extract text using pdfminer.six (no embedded metadata access)."""
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract

        text = pdfminer_extract(str(pdf_path), maxpages=3)
        text = re.sub(r"\s+", " ", text or "").strip()

        meta = PaperMeta(
            filepath=str(pdf_path),
            filename=pdf_path.name,
            source="text_parse",
        )
        _enrich_from_text(meta, text, max_abstract)
        return meta

    except ImportError:
        return None
    except Exception:
        return None


def _fallback_from_filename(pdf_path: Path) -> PaperMeta:
    """Last resort: parse metadata from filename conventions."""
    meta = PaperMeta(
        filepath=str(pdf_path),
        filename=pdf_path.name,
        source="filename",
        warnings="No PDF library available or extraction failed",
    )
    stem = pdf_path.stem

    # Pattern: 2023_Surname_Title-slug or Surname_2023_Title
    m = re.match(r"^(\d{4})_([A-Za-z]+(?:_[A-Za-z]+)?)_(.+)$", stem)
    if m:
        meta.year = m.group(1)
        meta.authors = m.group(2).replace("_", " ")
        meta.title = m.group(3).replace("-", " ").replace("_", " ")
        return meta

    m = re.match(r"^([A-Za-z]+)_(\d{4})_(.+)$", stem)
    if m:
        meta.authors = m.group(1)
        meta.year = m.group(2)
        meta.title = m.group(3).replace("-", " ").replace("_", " ")
        return meta

    # Just use stem as title
    meta.title = stem.replace("-", " ").replace("_", " ")
    return meta


# ---------------------------------------------------------------------------
# Text parsing helpers
# ---------------------------------------------------------------------------

_DOI_RE = re.compile(
    r"\b(?:doi[:\s/]*|https?://doi\.org/|http://dx\.doi\.org/)"
    r"(10\.\d{4,}[^\s\"'<>]+)",
    re.IGNORECASE,
)

_YEAR_RE = re.compile(r"\b(19[89]\d|20[012]\d)\b")

_ABSTRACT_MARKERS = [
    r"abstract[:\s]",
    r"summary[:\s]",
    r"background[:\s]",
]


def _clean(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip()
    # Remove null bytes and control characters
    s = re.sub(r"[\x00-\x1f\x7f]", "", s)
    return s


def _extract_year_from_date(date_str: str) -> str:
    """Extract 4-digit year from PDF date strings like D:20230815120000."""
    if not date_str:
        return ""
    m = re.search(r"(19[89]\d|20[012]\d)", date_str)
    return m.group(1) if m else ""


def _enrich_from_text(meta: PaperMeta, text: str, max_abstract: int):
    """Fill in missing fields by parsing document text."""
    if not text:
        meta.source = meta.source or "text_parse"
        return

    # --- DOI ---
    if not meta.doi:
        m = _DOI_RE.search(text)
        if m:
            doi = m.group(1).rstrip(".,;)")
            meta.doi = doi

    # --- Year ---
    if not meta.year:
        years = _YEAR_RE.findall(text[:3000])
        if years:
            # Most common year in the header area
            from collections import Counter
            most_common = Counter(years).most_common(1)[0][0]
            meta.year = most_common

    # --- Title (first meaningful line if not set) ---
    if not meta.title:
        lines = [l.strip() for l in text[:1500].splitlines() if len(l.strip()) > 15]
        if lines:
            # Pick longest of first 3 lines — usually the title
            candidate = max(lines[:5], key=len, default="")
            if len(candidate) > 15 and len(candidate) < 350:
                meta.title = _clean(candidate)

    # --- Abstract ---
    if not meta.abstract:
        for marker in _ABSTRACT_MARKERS:
            m = re.search(marker, text, re.IGNORECASE)
            if m:
                start = m.end()
                snippet = text[start:start + max_abstract * 2]
                # Cut at next major section header
                section_break = re.search(
                    r"\b(introduction|methods?|results?|discussion|keywords?|background)\b",
                    snippet,
                    re.IGNORECASE,
                )
                if section_break and section_break.start() > 100:
                    snippet = snippet[: section_break.start()]
                meta.abstract = _clean(snippet)[:max_abstract]
                break

    meta.source = meta.source or "text_parse"


# ---------------------------------------------------------------------------
# Crossref enrichment
# ---------------------------------------------------------------------------

def _crossref_enrich(meta: PaperMeta, email: str = "") -> PaperMeta:
    """
    Query Crossref for missing metadata using DOI or title search.
    Polite API: adds mailto if email is provided.
    """
    try:
        import requests
    except ImportError:
        meta.warnings += " | crossref: requests not installed"
        return meta

    headers = {"User-Agent": "pdf-meta-extractor/1.0 (mailto:user@example.com)"}
    if email:
        headers["User-Agent"] = f"pdf-meta-extractor/1.0 (mailto:{email})"

    try:
        if meta.doi:
            url = f"https://api.crossref.org/works/{meta.doi}"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                _apply_crossref(meta, resp.json().get("message", {}))
                return meta

        # Fall back to title search
        if meta.title:
            url = "https://api.crossref.org/works"
            params = {"query.title": meta.title, "rows": 1}
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("message", {}).get("items", [])
                if items:
                    _apply_crossref(meta, items[0])

    except Exception as e:
        meta.warnings += f" | crossref error: {e}"

    return meta


def _apply_crossref(meta: PaperMeta, work: dict):
    """Apply Crossref work record to fill missing fields."""
    if not meta.title:
        titles = work.get("title", [])
        if titles:
            meta.title = _clean(titles[0])

    if not meta.doi:
        meta.doi = work.get("DOI", "")

    if not meta.authors:
        authors_list = work.get("author", [])
        parts = []
        for a in authors_list[:6]:
            family = a.get("family", "")
            given = a.get("given", "")
            parts.append(f"{family}, {given}".strip(", "))
        if parts:
            meta.authors = "; ".join(parts)
            if len(authors_list) > 6:
                meta.authors += " et al."

    if not meta.year:
        published = work.get("published", {})
        date_parts = published.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            meta.year = str(date_parts[0][0])

    if not meta.abstract:
        meta.abstract = _clean(work.get("abstract", ""))[:1500]

    meta.source = "crossref"


# ---------------------------------------------------------------------------
# Main extraction entry point
# ---------------------------------------------------------------------------

def extract_pdf(pdf_path: Path, max_abstract: int, verbose: bool) -> PaperMeta:
    """Try all available backends in order of preference."""
    if verbose:
        print(f"  Processing: {pdf_path.name}", end=" ... ", flush=True)

    meta = None

    for backend in [_try_pymupdf, _try_pypdf, _try_pdfminer]:
        meta = backend(pdf_path, max_abstract)
        if meta is not None:
            break

    if meta is None:
        meta = _fallback_from_filename(pdf_path)

    if verbose:
        fields_found = sum([
            bool(meta.title),
            bool(meta.authors),
            bool(meta.year),
            bool(meta.doi),
            bool(meta.abstract),
        ])
        print(f"{fields_found}/5 fields [{meta.source}]")

    return meta


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch PDF metadata extractor — outputs CSV with title, authors, year, DOI, abstract",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "folder",
        type=Path,
        help="Folder containing PDF files",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("pdf_metadata.csv"),
        help="Output CSV path (default: pdf_metadata.csv)",
    )
    parser.add_argument(
        "--crossref",
        action="store_true",
        help="Enrich missing metadata via Crossref API (requires internet)",
    )
    parser.add_argument(
        "--email",
        type=str,
        default="",
        help="Your email for Crossref polite pool (used with --crossref)",
    )
    parser.add_argument(
        "--max-abstract",
        type=int,
        default=1500,
        help="Max characters for abstract (default: 1500)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subfolders recursively",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress for each file",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between Crossref API calls (default: 1.0)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    folder = args.folder.expanduser().resolve()
    if not folder.exists():
        print(f"ERROR: Folder not found: {folder}", file=sys.stderr)
        sys.exit(1)
    if not folder.is_dir():
        print(f"ERROR: Not a directory: {folder}", file=sys.stderr)
        sys.exit(1)

    # Discover PDFs
    if args.recursive:
        pdf_files = sorted(folder.rglob("*.pdf"))
    else:
        pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {folder}", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF file(s) in {folder}")
    if args.crossref:
        print("Crossref enrichment: ON")

    # Check backends
    backends_available = []
    try:
        try:
            import pymupdf
        except ImportError:
            import fitz
        backends_available.append("PyMuPDF")
    except ImportError:
        pass

    try:
        import pypdf
        backends_available.append("pypdf")
    except ImportError:
        pass

    try:
        import pdfminer
        backends_available.append("pdfminer.six")
    except ImportError:
        pass

    if not backends_available:
        print(
            "\nWARNING: No PDF library found. Install one of:\n"
            "  pip install pymupdf       (recommended)\n"
            "  pip install pypdf\n"
            "  pip install pdfminer.six\n"
            "Falling back to filename-only parsing.\n",
            file=sys.stderr,
        )
    else:
        print(f"PDF backends: {', '.join(backends_available)}")

    print()

    # Extract
    results: list[PaperMeta] = []
    for pdf_path in pdf_files:
        meta = extract_pdf(pdf_path, args.max_abstract, args.verbose)

        if args.crossref:
            if args.verbose:
                print(f"    Querying Crossref for: {meta.title[:60] or meta.doi or meta.filename}...")
            meta = _crossref_enrich(meta, args.email)
            time.sleep(args.delay)

        results.append(meta)

    # Write CSV
    output_path = args.output.expanduser().resolve()
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for meta in results:
            writer.writerow(meta.csv_row())

    # Summary
    print()
    print(f"Done. {len(results)} records written to: {output_path}")
    n_title = sum(1 for r in results if r.title)
    n_authors = sum(1 for r in results if r.authors)
    n_year = sum(1 for r in results if r.year)
    n_doi = sum(1 for r in results if r.doi)
    n_abstract = sum(1 for r in results if r.abstract)
    print(f"  title:    {n_title}/{len(results)}")
    print(f"  authors:  {n_authors}/{len(results)}")
    print(f"  year:     {n_year}/{len(results)}")
    print(f"  doi:      {n_doi}/{len(results)}")
    print(f"  abstract: {n_abstract}/{len(results)}")

    if n_doi < len(results):
        missing = len(results) - n_doi
        print(f"\nTip: {missing} record(s) missing DOI. Re-run with --crossref to try Crossref lookup.")


if __name__ == "__main__":
    main()
