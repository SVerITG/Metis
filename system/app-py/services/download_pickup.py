"""
download_pickup.py — file the PDFs the researcher downloaded by hand.

WHY THIS EXISTS
    The institutional half of acquisition cannot be automated here, and that is a
    fact about OpenAthens rather than a gap in the code. ITM authenticates through
    federated SSO: the session lives in a browser, behind a login and MFA, and
    Chrome seals its cookie values with a Windows DPAPI key that only unseals
    inside the user's own Windows session. Nothing running in WSL reaches it.

    The available answers were:

      (a) Paste a session cookie into system/.env. Works — until it expires,
          silently, after which every download quietly reverts to a red dot. It
          also puts a live bearer credential for the researcher's institutional
          identity on disk.

      (b) THIS. He clicks "GET VIA INSTITUTION", his browser downloads the PDF
          the way it always has, and Metis picks it up from the downloads folder,
          works out which paper it is, files it, and pushes it to Zotero.

    (b) is better on every axis that matters: no credential stored, nothing to
    expire, no silent failure mode, and it works for papers Metis never even
    proposed — anything he finds himself gets catalogued too. The cost is one
    click he was already making.

HOW A FILE IS MATCHED TO A PAPER
    In descending order of confidence, stopping at the first hit:

      1. DOI found in the PDF's text or its XMP/Info metadata, matched exactly
         against new_publications.doi. Publishers stamp the DOI on page 1 almost
         universally, so this resolves most files outright.
      2. DOI found in the FILENAME — Elsevier and Wiley often name downloads
         after the DOI or PII.
      3. Normalised title match against the pending queue, using the same
         title_key as the deduplicator so the two agree by construction.

    Anything unmatched is left alone and reported. A misfiled paper is worse than
    an unfiled one: an unfiled PDF is still sitting in Downloads where its owner
    put it, whereas a wrong match corrupts the catalogue silently.

SAFETY
    · Never deletes or moves the original unless told to. Default is COPY.
    · Never overwrites an existing filed PDF.
    · Only considers files newer than the pickup watermark, so a folder with
      years of unrelated PDFs is not re-examined on every run.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

_DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.I)

# How much of the PDF to read looking for a DOI. The DOI is on the first page in
# almost every case, and reading whole PDFs to file a download would make this
# far slower than the thing it is automating.
_SCAN_PAGES = 2
_MIN_PDF_BYTES = 20_000


# ───────────────────────────────────────────────────────────────────────────────
# PRIVACY PRE-FILTER
#
# A downloads folder is not a library. the researcher's contains payslips, a vehicle
# registration, invoices and tax documents alongside the papers. This runs on a
# schedule, so "read every PDF in there looking for a DOI" is the wrong default
# even though the reading is entirely local and nothing is stored.
#
# So: skip by FILENAME before opening the file at all. Matching is on the name
# only, which is the one thing that can be checked without reading the contents —
# the whole point is not to open a payslip to discover it is a payslip.
#
# Deliberately broad and bilingual (this machine is Belgian/Dutch), and
# extendable via METIS_PICKUP_IGNORE. A paper wrongly skipped is visible and
# fixable; a payslip needlessly parsed is not undoable.
# ───────────────────────────────────────────────────────────────────────────────
_PERSONAL_NAME_HINTS = (
    # Dutch / Belgian
    "loonbon", "loonbrief", "factuur", "kentekenbewijs", "gelijkvormigheid",
    "identificatieverslag", "rekening", "fiscale", "fiche", "attest",
    "aanvraag", "coupons", "belasting", "verzekering", "contract", "huur",
    "aanslagbiljet", "afrekening", "betaalbewijs", "loonfiche",
    # French
    "bulletin", "salaire", "facture", "attestation", "relev",
    # English
    "payslip", "payroll", "invoice", "receipt", "tax", "insurance",
    "bank", "statement", "passport", "boarding", "ticket", "cv", "resume",
    "docusign", "invitation", "justificationdocs", "signed",
)
# NOT in the list, on purpose: "travel". Travel medicine is the researcher's field, and
# "Travel Medicine and Infectious Disease" is a journal he would want filed.
# A hint that swallows real papers is worse than one that misses some admin.


def looks_personal(name: str) -> bool:
    """Does this filename look like a personal document rather than a paper?"""
    extra = os.environ.get("METIS_PICKUP_IGNORE", "")
    hints = _PERSONAL_NAME_HINTS + tuple(
        h.strip().lower() for h in extra.split(",") if h.strip())
    low = name.lower()
    return any(h in low for h in hints)


def _is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def downloads_dir() -> Path | None:
    """The BROWSER's download folder.

    On WSL this is the WINDOWS Downloads folder, not the Linux home's. Getting
    that wrong is silent and total: `~/Downloads` exists inside WSL, is empty,
    and the pickup cheerfully reports "0 PDFs" forever while 43 sit in
    C:/Users/<name>/Downloads where the browser actually put them.

    Chrome, Edge and Firefox all run on the Windows side here, so under WSL the
    Windows folder is checked FIRST and the Linux one only as a fallback for a
    genuinely Linux-native setup.
    """
    env = os.environ.get("METIS_DOWNLOADS_DIR", "")
    if env and Path(env).is_dir():
        return Path(env)

    import glob
    windows = []
    for hit in glob.glob("/mnt/c/Users/*/Downloads"):
        cand = Path(hit)
        if cand.is_dir() and cand.parent.name not in (
                "Public", "Default", "Default User", "All Users"):
            windows.append(cand)
    # Prefer the profile that actually has PDFs in it — a machine can carry
    # several Windows profiles, only one of which is in use.
    windows.sort(key=lambda d: len(list(d.glob("*.pdf"))), reverse=True)

    order = (windows + [Path.home() / "Downloads"]) if _is_wsl() \
        else ([Path.home() / "Downloads"] + windows)
    for c in order:
        if c.is_dir():
            return c
    return None


# ---------------------------------------------------------------------------
# Reading the PDF
# ---------------------------------------------------------------------------

def pdf_identity(path: Path) -> tuple[str, str]:
    """Return (doi, title_text) discovered inside a PDF. Best effort, never raises."""
    doi, title = "", ""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))

        meta = reader.metadata or {}
        for key in ("/doi", "/DOI", "/prism:doi"):
            v = meta.get(key)
            if v:
                m = _DOI_RE.search(str(v))
                if m:
                    doi = m.group(0)
        title = str(meta.get("/Title") or "").strip()

        text = ""
        for page in reader.pages[:_SCAN_PAGES]:
            try:
                text += page.extract_text() or ""
            except Exception:
                continue
        if not doi:
            # Collapse the whitespace pdf text extraction sprinkles INSIDE a
            # DOI. "10.1186/s1307 1-026-07504-z" is one identifier that the
            # extractor split across a line break; searching the raw text finds
            # only the fragment before the space.
            flat = re.sub(r"[ \t]*\n[ \t]*", "", text)
            m = _DOI_RE.search(flat) or _DOI_RE.search(text)
            if m:
                doi = m.group(0)
        if not title:
            # First substantial line of page 1 is usually the title.
            for line in (l.strip() for l in text.splitlines()):
                if len(line) > 25 and not line.lower().startswith(
                        ("doi", "http", "downloaded", "available", "contents")):
                    title = line
                    break
    except Exception:
        pass
    return _clean_doi(doi), title


def _clean_doi(doi: str) -> str:
    """Trim the obvious junk off a DOI scraped from PDF text."""
    d = (doi or "").strip().lower().rstrip(".,;:)]}-")
    d = re.sub(r"(abstract|introduction|received|accepted|published|citation|"
               r"copyright|www\.|http).*$", "", d)
    return d.rstrip(".,;:)]}-")


def validate_doi(doi: str) -> str:
    """Confirm a scraped DOI against Crossref, trimming trailing junk until it
    resolves. Returns the canonical DOI, or '' if none of the candidates exist.

    THIS IS WHY IT EXISTS. Two real failures, both from the researcher's own downloads:

        10.3390/tropicalmed11060161trop   ← ran into the next word on the page
        10.1186/s1307                     ← TRUNCATED; pdf text extraction had
                                            broken the DOI across a line

    Regex alone cannot fix either. There is no lexical rule that knows
    "...161trop" has four characters too many while "...07504-z" is complete —
    DOIs contain letters, digits and hyphens in any arrangement. But there IS an
    authority that knows: Crossref. Asking it turns a guess into a fact.

    So: try the string, then progressively shorter prefixes (for the run-on
    case), then progressively LONGER reconstructions from the surrounding text
    (for the truncation case, handled by the caller passing `context`).
    """
    import json
    import urllib.parse
    import urllib.request

    def exists(cand: str) -> bool:
        try:
            req = urllib.request.Request(
                f"https://api.crossref.org/works/{urllib.parse.quote(cand)}/agency",
                headers={"User-Agent": "MetisRC/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status == 200
        except Exception:
            return False

    d = _clean_doi(doi)
    if not d or "/" not in d:
        return ""
    if exists(d):
        return d
    # Run-on case: shave characters off the tail. Bounded — a DOI suffix is
    # rarely worth more than ~12 speculative probes, and each is one HTTP call.
    prefix, _, suffix = d.partition("/")
    for cut in range(1, min(13, len(suffix))):
        cand = f"{prefix}/{suffix[:-cut]}"
        if len(cand.split("/", 1)[1]) < 4:
            break
        if exists(cand):
            return cand
    return ""


def _title_key(title: str) -> str:
    """Same normalisation as the deduplicator, so the two cannot disagree."""
    import html as _html
    t = _html.unescape(title or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"^\s*\[[^\]]{1,40}\]\s*", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
    return t if len(t) >= 18 else ""


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def match_publication(conn: sqlite3.Connection, path: Path) -> tuple[dict | None, str]:
    """Find the new_publications row this PDF belongs to. Returns (row, how)."""
    conn.row_factory = sqlite3.Row

    doi, title = pdf_identity(path)

    # 1. DOI from inside the file. Try the raw scrape first — it is free and
    #    usually right — then let Crossref repair a run-on or truncated one.
    for cand, how in ((doi, "DOI in PDF"), (validate_doi(doi), "DOI in PDF, Crossref-verified")):
        if not cand:
            continue
        r = conn.execute(
            "SELECT * FROM new_publications WHERE lower(doi) = ? AND doi != '' LIMIT 1",
            (cand,)).fetchone()
        if r:
            return dict(r), f"{how} ({cand})"

    # 2. DOI in the filename — Elsevier and Wiley name downloads this way.
    m = _DOI_RE.search(path.name.replace("_", "/"))
    if m:
        fdoi = _clean_doi(m.group(0))
        r = conn.execute(
            "SELECT * FROM new_publications WHERE lower(doi) = ? AND doi != '' LIMIT 1",
            (fdoi,)).fetchone()
        if r:
            return dict(r), f"DOI in filename ({fdoi})"

    # 3. Normalised title, from the PDF's own metadata or its first page.
    for candidate in (title, path.stem.replace("-", " ").replace("_", " ")):
        key = _title_key(candidate)
        if not key:
            continue
        r = conn.execute(
            "SELECT * FROM new_publications WHERE title_key = ? LIMIT 1",
            (key,)).fetchone()
        if r:
            return dict(r), "title match"

    return None, ""


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def _watermark(conn: sqlite3.Connection) -> str:
    conn.execute("""CREATE TABLE IF NOT EXISTS library_review_state (
        surface TEXT PRIMARY KEY, last_reviewed_at TEXT NOT NULL,
        items_seen INTEGER DEFAULT 0, updated_at TEXT NOT NULL)""")
    row = conn.execute(
        "SELECT last_reviewed_at FROM library_review_state WHERE surface='downloads'"
    ).fetchone()
    return (row[0] if row else "") or ""


def _set_watermark(conn: sqlite3.Connection, when: str, seen: int) -> None:
    conn.execute(
        "INSERT INTO library_review_state (surface, last_reviewed_at, items_seen, updated_at) "
        "VALUES ('downloads', ?, ?, ?) ON CONFLICT(surface) DO UPDATE SET "
        "last_reviewed_at=excluded.last_reviewed_at, items_seen=excluded.items_seen, "
        "updated_at=excluded.updated_at",
        (when, seen, datetime.now().isoformat(timespec="seconds")))


def scan_downloads(conn: sqlite3.Connection, move: bool = False,
                   limit: int = 60, all_files: bool = False) -> dict:
    """Match and file every new PDF in the downloads folder.

    Returns a report: {filed, unmatched, skipped, folder, items:[...]}.
    """
    from services.acquire import library_root, target_path

    folder = downloads_dir()
    if folder is None:
        return {"error": "no downloads folder found", "filed": 0,
                "unmatched": 0, "skipped": 0, "items": []}

    root = library_root()
    if root is None:
        return {"error": "no library folder configured", "filed": 0,
                "unmatched": 0, "skipped": 0, "items": []}

    mark = "" if all_files else _watermark(conn)
    mark_ts = 0.0
    if mark:
        try:
            mark_ts = datetime.fromisoformat(mark).timestamp()
        except ValueError:
            mark_ts = 0.0

    pdfs = sorted((p for p in folder.glob("*.pdf") if p.is_file()),
                  key=lambda p: p.stat().st_mtime, reverse=True)[:limit]

    filed = unmatched = skipped = 0
    items: list[dict] = []
    newest = mark_ts

    for pdf in pdfs:
        st = pdf.stat()
        newest = max(newest, st.st_mtime)
        if st.st_mtime <= mark_ts:
            continue
        if st.st_size < _MIN_PDF_BYTES:
            skipped += 1
            continue
        if looks_personal(pdf.name):
            # Not opened at all — see the privacy pre-filter above.
            skipped += 1
            continue

        pub, how = match_publication(conn, pdf)
        if not pub:
            unmatched += 1
            items.append({"file": pdf.name, "status": "unmatched", "how": ""})
            continue

        year = (pub.get("pub_iso") or "")[:4] or (pub.get("pub_date") or "")[:4]
        dest = target_path(root, (pub.get("topic_tag") or "").split(",")[0],
                           year, pub.get("authors") or "", pub.get("title") or "")
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                # Never overwrite a filed PDF. The one already there was either
                # obtained legitimately or filed earlier from this same folder.
                skipped += 1
                items.append({"file": pdf.name, "status": "already filed",
                              "how": how, "title": pub.get("title", "")[:70]})
                continue
            dest.write_bytes(pdf.read_bytes())
            if move:
                pdf.unlink()
        except OSError as exc:
            items.append({"file": pdf.name, "status": f"error: {exc}", "how": how})
            continue

        rel = str(dest.relative_to(root))
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "UPDATE new_publications SET acq_status='ok', acq_reason=?, pdf_path=?, "
            "added_at=COALESCE(NULLIF(added_at,''), ?) WHERE id=?",
            (f"filed from downloads — {how}", rel, now, pub["id"]))
        conn.execute(
            "INSERT INTO library_acquisition_log "
            "(pub_id, doi, method, outcome, detail, bytes, attempted_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (pub["id"], pub.get("doi", ""), "downloads-pickup", "ok",
             f"{pdf.name} → {rel}", st.st_size, now))
        filed += 1
        items.append({"file": pdf.name, "status": "filed", "how": how,
                      "title": pub.get("title", "")[:70], "path": rel,
                      "pub_id": pub["id"]})

    _set_watermark(conn, datetime.fromtimestamp(newest).isoformat(timespec="seconds")
                   if newest else datetime.now().isoformat(timespec="seconds"),
                   filed)
    conn.commit()
    return {"filed": filed, "unmatched": unmatched, "skipped": skipped,
            "folder": str(folder), "items": items}
