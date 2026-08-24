"""
acquire.py — obtain the PDF for a publication, and never lie about whether it worked.

THE PROBLEM THIS SOLVES
    "Add to library" used to write a metadata row and mark the paper read. No PDF
    was ever fetched, and no failure was recorded — so a paper you could not get
    was indistinguishable from one you had. That is worse than not trying: it puts
    a false negative in your own catalogue, and you only discover it months later
    when you go looking for a file that was never there.

    So the contract here is: every attempt ends in a RECORDED outcome. 'ok' with
    a path, or 'failed' with a reason a human can read. Never silence.

THE LADDER
    Attempts run cheapest-and-most-legitimate first:

    1. OPEN ACCESS. Unpaywall (a DOI → legal-OA-copy index), then PubMed Central,
       then the source URL itself when it is a known fully-OA publisher (PLOS,
       BMC, medRxiv, bioRxiv, eLife, Wellcome Open Research). No credentials, no
       licence question, and for NTD and global-health literature this alone
       succeeds a large share of the time — those fields publish OA heavily.

    2. INSTITUTIONAL RESOLVER. Only if configured, and only if step 1 found
       nothing. See the honest limits below.

    3. FAILURE, with a reason and a link-out. The red dot.

    Step 1 before step 2 is not just politeness — an OA copy is faster, needs no
    session, and cannot break when a proxy changes its login flow.

HONEST LIMITS OF STEP 2
    the researcher asked for download through his institutional login, and chose that over
    an OA-only approach after being told the trade-offs. It is implemented — and
    these are the real constraints, recorded here rather than discovered later:

      · An EZproxy/OpenURL rewrite works from a Metis process ONLY if the request
        already carries an authenticated session, or the request comes from an
        IP the institution recognises. On the ITG network the second case often
        just works; off-network it does not.
      · Where a session is needed, the only thing that reliably transfers is a
        session COOKIE the researcher pastes in. Automating a Shibboleth login with MFA
        from a background process is not something this can promise, and
        pretending otherwise would produce exactly the silent-failure class this
        module exists to remove.
      · So when step 2 cannot authenticate, the outcome is a red dot plus a
        one-click resolver link that opens in HIS browser, where his session
        already exists. The watched-folder pickup then files whatever he saves.

    Nothing here bypasses a paywall. It uses access ITG already pays for, or it
    reports that it could not.

CONFIGURATION (system/.env — never in source)
    UNPAYWALL_EMAIL         contact address Unpaywall requires (falls back to
                            the profile email)
    LIBRARY_PROXY_TEMPLATE  e.g. https://login.itg.be/login?url={url}
    LIBRARY_PROXY_COOKIE    optional pasted session cookie for that host
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Publishers whose entire output is open access, so their article URL can be
# turned into a PDF URL directly without asking Unpaywall first.
# ANCHORED AT THE SCHEME, deliberately.
#
# These patterns previously started at the hostname, so re.sub() replaced only
# the middle of the URL and left the original "https://" in front of a
# replacement that supplied its own — producing
#     https://https://elifesciences.org/articles/108688.pdf
# Every such candidate 404s. Harmless only because other candidates follow it;
# the visible cost is a wasted request and a misleading failure reason. Matching
# from ^ means the substitution replaces the WHOLE string.
_OA_PATTERNS: list[tuple[str, str]] = [
    (r"^https?://(?:www\.)?journals\.plos\.org/([a-z]+)/article\?id=(.+)$",
     r"https://journals.plos.org/\1/article/file?id=\2&type=printable"),
    (r"^https?://(?:www\.)?medrxiv\.org/content/(10\.\d+/[^v]+v\d+).*$",
     r"https://www.medrxiv.org/content/\1.full.pdf"),
    (r"^https?://(?:www\.)?biorxiv\.org/content/(10\.\d+/[^v]+v\d+).*$",
     r"https://www.biorxiv.org/content/\1.full.pdf"),
    (r"^https?://(?:www\.)?elifesciences\.org/articles/(\d+).*$",
     r"https://elifesciences.org/articles/\1.pdf"),
    (r"^https?://(?:www\.)?arxiv\.org/abs/([\d.]+).*$",
     r"https://arxiv.org/pdf/\1"),
]

# DOI-keyed open-access routes.
#
# Added after a live test: the PLOS Pathogens VSG paper arrived with
# source_url = 'https://doi.org/10.1371/journal.ppat.1014518', which matches none
# of the URL patterns above, so it fell through to Unpaywall — and Unpaywall
# handed back the HTML landing page. A PLOS paper is 100% open access and its PDF
# URL is fully derivable from the DOI, so falling back to a third-party index for
# it was both slower and wrong.
#
# This matters disproportionately here: PLOS NTDs, PLOS Medicine, PLOS Global
# Public Health and PLOS Pathogens are four of the most important journals in
# this researcher's field, and every one of them is a 10.1371 DOI.
_PLOS_JOURNALS = {
    "pntd": "plosntds",          "ppat": "plospathogens",
    "pmed": "plosmedicine",      "pone": "plosone",
    "pbio": "plosbiology",       "pgph": "globalpublichealth",
    "pcbi": "ploscompbiol",      "pgen": "plosgenetics",
    "pstr": "sustainabilitytransformation",
}


def _doi_oa_url(doi: str) -> tuple[str, str]:
    """Derive a PDF URL straight from a DOI for publishers that allow it."""
    d = (doi or "").strip().lower().replace("https://doi.org/", "")
    if not d:
        return "", ""

    # PLOS — 10.1371/journal.<code>.<id>
    m = re.match(r"^10\.1371/journal\.([a-z]+)\.\d+$", d)
    if m and m.group(1) in _PLOS_JOURNALS:
        site = _PLOS_JOURNALS[m.group(1)]
        return (f"https://journals.plos.org/{site}/article/file"
                f"?id={d}&type=printable"), "plos-doi"

    # eLife — 10.7554/eLife.<id>
    m = re.match(r"^10\.7554/elife\.(\d+)", d)
    if m:
        return f"https://elifesciences.org/articles/{m.group(1)}.pdf", "elife-doi"

    # BMC / Springer Open — 10.1186/<slug>
    m = re.match(r"^10\.1186/(.+)$", d)
    if m:
        return (f"https://link.springer.com/content/pdf/{d}.pdf", "springer-doi")

    # MDPI, Frontiers and PeerJ are also fully OA but their PDF paths are not
    # derivable from the DOI alone, so they stay with Unpaywall.
    return "", ""


# Preprint servers. Handled separately from _doi_oa_url because they need
# SEVERAL candidate URLs, not one: the PDF path carries a VERSION suffix that the
# DOI does not encode, so v1 has to be tried, then v2, then v3.
#
# Found the hard way on 2026-08-21: a bioRxiv paper on SUMOylation and antigenic
# variation in T. brucei failed with "no open-access copy found" even though the
# whole server is open access. Two reasons —
#   · bioRxiv has MOVED to a new DOI prefix (10.64898), so any rule keyed on the
#     classic 10.1101 silently stops matching new papers, and
#   · the URL patterns only matched biorxiv.org article links, while the feed
#     supplies a doi.org link.
# Preprints are an entire tab on the New Literature surface and medRxiv/bioRxiv
# are two of the configured feeds, so this was a large blind spot.
_PREPRINT_HOSTS = {
    "biorxiv": "https://www.biorxiv.org/content/",
    "medrxiv": "https://www.medrxiv.org/content/",
}
_PREPRINT_DOI_PREFIXES = ("10.1101/", "10.64898/")


def _preprint_candidates(doi: str, source_url: str, journal: str) -> list[tuple[str, str]]:
    """Candidate PDF URLs for a bioRxiv/medRxiv preprint, newest version first."""
    d = (doi or "").strip().lower().replace("https://doi.org/", "")
    hay = f"{source_url} {journal}".lower()

    host = None
    for name, base in _PREPRINT_HOSTS.items():
        if name in hay:
            host = base
            break
    if host is None and any(d.startswith(pre) for pre in _PREPRINT_DOI_PREFIXES):
        # Prefix alone cannot distinguish the two servers — both use 10.1101 —
        # so default to bioRxiv and let medRxiv be caught by the name check above.
        host = _PREPRINT_HOSTS["biorxiv"]
    if host is None or not d:
        return []

    # Most preprints are v1; a revised one is v2 or v3. Three tries covers
    # essentially all of them without hammering the server.
    return [(f"{host}{d}v{v}.full.pdf", f"preprint-v{v}") for v in (1, 2, 3)]


def oa_candidates(doi: str, source_url: str, journal: str = "") -> list[tuple[str, str]]:
    """Every open-access URL worth trying, cheapest and most certain first.

    Returns a LIST rather than one URL because preprint servers need version
    probing. Ordering is deliberate: derivable publisher URLs first (no API call,
    no third party), then preprints, then the indexes.
    """
    out: list[tuple[str, str]] = []

    url, method = _doi_oa_url(doi)
    if url:
        out.append((url, method))

    for pattern, repl in _OA_PATTERNS:
        if source_url and re.search(pattern, source_url):
            out.append((re.sub(pattern, repl, source_url), "oa-publisher"))
            break

    out.extend(_preprint_candidates(doi, source_url, journal))

    if doi:
        u, m = _unpaywall_url(doi)
        if u:
            out.append((u, m))
        u, m = _pmc_url(doi)
        if u:
            out.append((u, m))

    # Preserve order, drop duplicates.
    seen: set[str] = set()
    deduped = []
    for u, m in out:
        if u not in seen:
            seen.add(u)
            deduped.append((u, m))
    return deduped

# A PDF we accept has to actually be a PDF and a plausible size. Publishers serve
# an HTML paywall page with HTTP 200 constantly — accepting that would file a
# login form as the paper, which is the worst possible outcome: a catalogue entry
# that looks complete and is not.
_MIN_PDF_BYTES = 20_000
_MAX_PDF_BYTES = 80_000_000
_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/126.0 Safari/537.36")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _load_env() -> None:
    """Fold system/.env into the process environment, without overriding it."""
    rc = os.environ.get("METIS_RC_ROOT", "")
    if not rc:
        return
    p = Path(rc) / "system" / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def unpaywall_email() -> str:
    _load_env()
    return (os.environ.get("UNPAYWALL_EMAIL", "")
            or os.environ.get("METIS_USER_EMAIL", "")
            or "metis@research-cortex.local")


def proxy_template() -> str:
    """The institutional URL-rewriting template, or '' if not configured."""
    _load_env()
    return os.environ.get("LIBRARY_PROXY_TEMPLATE", "").strip()


def proxy_cookie() -> str:
    _load_env()
    return os.environ.get("LIBRARY_PROXY_COOKIE", "").strip()


def library_root() -> Path | None:
    """The researcher's library folder — where PDFs are filed."""
    env = os.environ.get("METIS_LIBRARY_PATH", "")
    if env and Path(env).is_dir():
        return Path(env)
    rc = os.environ.get("METIS_RC_ROOT", "")
    if rc:
        try:
            prefs = json.loads(
                (Path(rc) / "system" / "config" / "user-preferences.json")
                .read_text(encoding="utf-8"))
            lp = prefs.get("library_path", "")
            if lp and Path(lp).is_dir():
                return Path(lp)
        except Exception:
            pass
    return None


_crossref_cache: dict[str, str] = {}


def publisher_url(doi: str) -> str:
    """The publisher's landing page for a DOI, via Crossref. '' if unknown.

    WHY NOT JUST USE https://doi.org/<doi>?
        Because ITM's OpenAthens redirector REJECTS doi.org targets outright —
        measured 2026-08-21, it returns HTTP 400 "Bad request" for a doi.org URL
        and HTTP 200 for the publisher URL of the same paper. A federated
        redirector matches on the publisher's domain to choose the right
        entitlement, so an aggregator URL it cannot attribute is meaningless to
        it.

        Following the DOI with a HEAD request does not work either: Elsevier and
        Springer Nature do not honour HEAD and hand back the doi.org URL
        unchanged. Crossref publishes the landing page as structured data, which
        is both reliable and one cheap call.

    Cached per process — a DOI's landing page does not change, and the same paper
    is often resolved twice (once for the acquisition attempt, once to render the
    link-out).
    """
    d = (doi or "").strip().lower().replace("https://doi.org/", "")
    if not d:
        return ""
    if d in _crossref_cache:
        return _crossref_cache[d]
    try:
        req = urllib.request.Request(
            f"https://api.crossref.org/works/{urllib.parse.quote(d)}",
            headers={"User-Agent": f"MetisRC/1.0 (mailto:{unpaywall_email()})"})
        with urllib.request.urlopen(req, timeout=25) as r:
            msg = json.loads(r.read())["message"]
        url = ((msg.get("resource") or {}).get("primary") or {}).get("URL", "") or ""
    except Exception:
        url = ""
    _crossref_cache[d] = url
    return url


def resolver_url(doi: str, fallback: str = "") -> str:
    """The URL to open in the researcher's OWN browser for an authenticated read.

    This is the link behind the red dot's "GET VIA INSTITUTION". It deliberately
    does the thing a server cannot: hands the problem to the session that already
    exists in the browser.

    The target is the PUBLISHER's page, not the DOI — see publisher_url() for why
    the redirector refuses the latter.
    """
    target = publisher_url(doi) or (f"https://doi.org/{doi}" if doi else "") or fallback
    tmpl = proxy_template()
    if tmpl and target:
        if "{url}" in tmpl:
            return tmpl.replace("{url}", urllib.parse.quote(target, safe=""))
        return tmpl.rstrip("/") + "/" + target
    return target


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def _seed_jar(jar: "http.cookiejar.CookieJar", spec: str) -> int:
    """Load pasted cookies into a jar. Returns how many were accepted.

    Accepts either form:
        name=value; name2=value2                  → scoped to go.openathens.net
        go.openathens.net|name=value; ...         → explicit domain
        host-a|a=1 ;; host-b|b=2                  → several hosts, '; ;' separated

    An explicit domain matters because a session cookie must NOT be broadcast to
    every host in the redirect chain. Scoping is the whole reason for using a
    real cookie jar rather than a static header.
    """
    import http.cookiejar as cj

    count = 0
    for chunk in spec.split(";;"):
        chunk = chunk.strip()
        if not chunk:
            continue
        domain, _, pairs = chunk.rpartition("|")
        domain = (domain or "go.openathens.net").strip().lstrip(".")
        for pair in pairs.split(";"):
            if "=" not in pair:
                continue
            name, _, value = pair.partition("=")
            name, value = name.strip(), value.strip()
            if not name or not value:
                continue
            jar.set_cookie(cj.Cookie(
                version=0, name=name, value=value, port=None, port_specified=False,
                domain=domain, domain_specified=True, domain_initial_dot=False,
                path="/", path_specified=True, secure=True, expires=None,
                discard=False, comment=None, comment_url=None, rest={}, rfc2109=False,
            ))
            count += 1
    return count


def _http_get(url: str, cookie: str = "", timeout: int = 45) -> tuple[bytes, str, int]:
    """GET a URL, carrying cookies across the whole redirect chain.

    A COOKIE JAR, not a static header — this is what makes an institutional
    session usable at all.

    An OpenAthens fetch is a multi-hop conversation:
        go.openathens.net  (session cookie proves who you are)
          → idp.itg.be     (asserts entitlement)
            → publisher    (SETS ITS OWN session cookie, then serves the PDF)

    `urlopen` follows those redirects but throws away every `Set-Cookie` on the
    way, so the publisher's session — created in the middle of the chain — never
    reaches the final request and the download is unauthenticated. Pasting a
    cookie into LIBRARY_PROXY_COOKIE could not have worked without this.

    A jar also SCOPES cookies by domain, so the OpenAthens session is not
    broadcast to every host the chain passes through. That is a security
    property, not just a correctness one.
    """
    import http.cookiejar

    jar = http.cookiejar.CookieJar()
    if cookie:
        _seed_jar(jar, cookie)

    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": "application/pdf,text/html,*/*",
    })
    with opener.open(req, timeout=timeout) as r:
        return r.read(_MAX_PDF_BYTES + 1), (r.headers.get("Content-Type") or ""), r.status


def _looks_like_pdf(body: bytes, content_type: str) -> tuple[bool, str]:
    """Is this actually a PDF? Returns (ok, reason_if_not).

    Checks the magic bytes, not just the header: publishers routinely return
    Content-Type: application/pdf on an HTML interstitial, and the reverse.
    """
    if not body:
        return False, "empty response"
    if len(body) < _MIN_PDF_BYTES:
        return False, f"too small ({len(body)} bytes) — probably a landing page"
    if len(body) > _MAX_PDF_BYTES:
        return False, "larger than the 80 MB cap"
    if not body[:5].startswith(b"%PDF"):
        head = body[:400].decode("utf-8", "ignore").lower()
        if "<html" in head or "<!doctype" in head:
            if any(w in head for w in ("sign in", "login", "subscribe",
                                       "access denied", "purchase")):
                return False, "paywall or login page returned instead of a PDF"
            return False, "HTML returned instead of a PDF"
        return False, f"not a PDF (content-type {content_type or 'unknown'})"
    return True, ""


# ---------------------------------------------------------------------------
# Step 1 — open access
# ---------------------------------------------------------------------------

def _unpaywall_url(doi: str) -> tuple[str, str]:
    """Ask Unpaywall for a legal OA copy of this DOI. ('', '') if none."""
    try:
        url = (f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}"
               f"?email={urllib.parse.quote(unpaywall_email())}")
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read())
        best = data.get("best_oa_location") or {}
        for key in ("url_for_pdf", "url"):
            if best.get(key):
                return best[key], "unpaywall"
        for loc in (data.get("oa_locations") or []):
            if loc.get("url_for_pdf"):
                return loc["url_for_pdf"], "unpaywall"
    except Exception:
        pass
    return "", ""


def _pmc_url(doi: str) -> tuple[str, str]:
    """PubMed Central copy, via NCBI's ID converter.

    Worth trying even when Unpaywall says no: PMC holds the author manuscript for
    anything NIH- or Wellcome-funded, which covers a great deal of tropical
    medicine even where the journal itself is closed.
    """
    try:
        url = ("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?format=json"
               f"&ids={urllib.parse.quote(doi)}&tool=metis-rc"
               f"&email={urllib.parse.quote(unpaywall_email())}")
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read())
        for rec in (data.get("records") or []):
            if rec.get("pmcid"):
                return (f"https://www.ncbi.nlm.nih.gov/pmc/articles/"
                        f"{rec['pmcid']}/pdf/"), "pmc"
    except Exception:
        pass
    return "", ""


def open_access_pdf_url(doi: str, source_url: str = "") -> tuple[str, str]:
    """First open-access candidate, or ('', ''). Kept for callers wanting one URL."""
    cands = oa_candidates(doi, source_url)
    return cands[0] if cands else ("", "")


# ---------------------------------------------------------------------------
# Filing
# ---------------------------------------------------------------------------

def _slug(text: str, limit: int = 60) -> str:
    t = unicodedata.normalize("NFKD", text or "")
    t = t.encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-")
    return t[:limit].strip("-") or "untitled"


def target_path(root: Path, topic: str, year: str, authors: str,
                title: str) -> Path:
    """Where a downloaded PDF belongs.

        <library root>/_metis-downloads/<topic>/<year>/<Author>-<Year>-<title>.pdf

    Three deliberate choices, all of them about a human being able to find the
    file later and hand it to Zotero:

    · A NAMED SUBFOLDER (`_metis-downloads`) rather than scattering files through
      the existing tree. the researcher's library folder is his own, organised his way; a
      tool that interleaves its downloads into it makes "what did Metis add?"
      unanswerable, and makes an accidental deletion unrecoverable. The
      underscore sorts it to the top.
    · TOPIC/YEAR nesting, because that is how a reference collection is browsed
      when you are looking for something you half-remember.
    · Author-Year-Title filenames, matching the Zotero and BetterBibTeX
      convention, so a drag into Zotero produces a sane attachment name.
    """
    stem = f"{_slug((authors or 'Unknown').split(';')[0], 28)}-{year or 'nd'}-{_slug(title, 70)}"
    return root / "_metis-downloads" / _slug(topic or "unfiled", 40) / (year or "undated") / f"{stem}.pdf"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _log(conn: sqlite3.Connection, pub_id: int, doi: str, method: str,
         outcome: str, detail: str, size: int = 0) -> None:
    """Record one attempt. Separate from the item row on purpose — a retry must
    not erase why the previous attempt failed."""
    try:
        conn.execute(
            "INSERT INTO library_acquisition_log "
            "(pub_id, doi, method, outcome, detail, bytes, attempted_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (pub_id, doi, method, outcome, detail[:400], size,
             datetime.now().isoformat(timespec="seconds")),
        )
    except sqlite3.Error:
        pass


def acquire_pdf(conn: sqlite3.Connection, pub: dict, force: bool = False) -> dict:
    """Try to obtain and file the PDF for one publication.

    Returns {status, reason, path, method}. `status` ∈ {'ok','failed'} — and it
    is always one of those two, never absent, because an unrecorded attempt is
    the failure mode this whole module exists to remove.
    """
    pub_id = pub.get("id") or 0
    doi = (pub.get("doi") or "").strip()
    source_url = (pub.get("source_url") or "").strip()

    root = library_root()
    if root is None:
        reason = ("no library folder configured — set library_path in "
                  "system/config/user-preferences.json")
        _log(conn, pub_id, doi, "none", "failed", reason)
        return {"status": "failed", "reason": reason, "path": "", "method": ""}

    year = (pub.get("pub_iso") or "")[:4] or (pub.get("pub_date") or "")[:4]
    dest = target_path(root, (pub.get("topic_tag") or "").split(",")[0],
                       year, pub.get("authors") or "", pub.get("title") or "")

    # Already there from an earlier attempt — treat as success rather than
    # re-downloading. Cheap, and it makes the action idempotent.
    #
    # `force` skips it. Needed by tools/check_proxy.py, which must make a REAL
    # network attempt: its first two runs both picked papers that were already on
    # disk and reported success without sending a single request — a check that
    # cannot fail is not a check. Also the way to retry a truncated download.
    if not force and dest.exists() and dest.stat().st_size >= _MIN_PDF_BYTES:
        rel = str(dest.relative_to(root))
        _log(conn, pub_id, doi, "cache", "ok", "already on disk",
             dest.stat().st_size)
        return {"status": "ok", "reason": "already downloaded", "path": rel,
                "method": "cache"}

    attempts: list[tuple[str, str, str]] = []      # (method, url, cookie)

    # ALL open-access candidates, not just the first. A preprint needs its
    # version probed (v1, v2, v3), and Unpaywall's answer is worth trying even
    # after a publisher URL has been derived — stopping at the first candidate
    # is what made a fully-open bioRxiv paper report "no open-access copy found".
    for oa_url, oa_method in oa_candidates(doi, source_url, pub.get("journal") or ""):
        attempts.append((oa_method, oa_url, ""))

    tmpl = proxy_template()
    if tmpl and doi:
        attempts.append(("institutional", resolver_url(doi), proxy_cookie()))
        # NOTE ON WHAT THIS CAN AND CANNOT DO.
        # ITM authenticates through OpenAthens (federated SSO), not an IP-based
        # EZproxy. Without a session cookie the redirector answers with an HTML
        # "Please wait…" page that bounces the BROWSER to idp.itg.be — there is
        # no PDF at the end of it for a server. _looks_like_pdf rejects that
        # page, the outcome is recorded as failed, and the surface offers the
        # link-out instead. Pasting a session cookie into LIBRARY_PROXY_COOKIE
        # makes the automated path work for as long as that session lives.

    if not attempts:
        reason = ("no open-access copy found"
                  + ("" if tmpl else " and no institutional resolver configured"))
        _log(conn, pub_id, doi, "none", "failed", reason)
        return {"status": "failed", "reason": reason, "path": "", "method": ""}

    last_reason = "no attempt succeeded"
    for method, url, cookie in attempts:
        try:
            body, ctype, status = _http_get(url, cookie=cookie)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if method == "institutional" and code == 400:
                # A 400 from the OpenAthens redirector is not a transport error:
                # it means the institution has NO ENTITLEMENT for that publisher's
                # domain, so the federation refuses to build a link at all.
                # Measured 2026-08-21: cambridge.org 400s for ITM while
                # elsevier and mdpi return 200. Reporting it as "HTTPError"
                # would send the researcher looking for a broken proxy when the real
                # answer is that ITM does not subscribe — a different problem
                # with a different remedy (interlibrary loan, or asking the
                # library to add it).
                last_reason = ("publisher not in your institution's OpenAthens "
                               "entitlements — try interlibrary loan")
            else:
                last_reason = f"{method}: {type(exc).__name__}" + (
                    f" {code}" if code else "")
            _log(conn, pub_id, doi, method, "failed", last_reason)
            continue

        ok, why = _looks_like_pdf(body, ctype)
        if not ok:
            # Distinguish the two institutional failures, because they need
            # different actions from the researcher: no session means paste a cookie or be
            # on the ITG network; a genuine paywall means the subscription does
            # not cover it and there is nothing to fix.
            if method == "institutional":
                head = body[:2000].decode("utf-8", "ignore").lower()
                if "openathens" in head or "please wait" in head or "idp." in head:
                    # Distinct from a paywall, and it needs a different action:
                    # the subscription is fine, the SESSION is missing.
                    why = ("institutional sign-in required — Metis has no "
                           "OpenAthens session; open it in your browser")
                elif "paywall or login" in why:
                    why = ("institutional access not authenticated from Metis — "
                           "open it in your browser instead")
            # Don't prefix a reason that already names its own context, or the
            # surface shows "institutional: institutional sign-in required".
            last_reason = why if why.startswith(("institutional", "publisher not")) \
                else f"{method}: {why}"
            _log(conn, pub_id, doi, method, "failed", last_reason, len(body))
            continue

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
        except OSError as exc:
            last_reason = f"could not write {dest.name}: {exc}"
            _log(conn, pub_id, doi, method, "failed", last_reason, len(body))
            continue

        rel = str(dest.relative_to(root))
        _log(conn, pub_id, doi, method, "ok", rel, len(body))
        return {"status": "ok", "reason": f"obtained via {method}", "path": rel,
                "method": method}

    return {"status": "failed", "reason": last_reason, "path": "", "method": ""}
