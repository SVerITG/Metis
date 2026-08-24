#!/usr/bin/env python3
"""check_proxy.py — can Metis actually download a paywalled paper right now?

WHY THIS EXISTS
    The institutional route has four distinct ways to not work, and they look
    identical from the surface — a red dot:

        no template configured        → set LIBRARY_PROXY_TEMPLATE
        template set, no session      → paste a cookie, or use the browser link
        session present but EXPIRED   → paste a fresh cookie
        publisher not subscribed      → interlibrary loan; nothing to fix

    Only the third is time-dependent, and it is the one that will bite: a session
    cookie dies quietly, and from then on every download silently returns to the
    red dot. Being able to ask "does it work *now*" in one command is the
    difference between noticing that in a second and noticing it in a month.

WHAT IT DOES
    Picks a genuinely paywalled paper from your own new_publications table —
    not a synthetic URL — and runs the real acquisition ladder against it,
    reporting which rung answered.

USAGE
    python3 tools/check_proxy.py
    python3 tools/check_proxy.py --doi 10.1016/j.pt.2026.07.012
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "system" / "app-py"))
sys.path.insert(0, str(ROOT / "system" / "mcp-server" / "src"))
os.environ.setdefault("METIS_RC_ROOT", str(ROOT))

OK, WARN, BAD = "✓", "!", "✗"


def db() -> sqlite3.Connection:
    p = Path.home() / ".local/share/metis" / "metis.sqlite"
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    return c


def main() -> int:
    from services.acquire import (
        proxy_template, proxy_cookie, publisher_url, resolver_url, acquire_pdf,
    )

    print("Institutional download check")
    print("=" * 68)

    tmpl = proxy_template()
    if not tmpl:
        print(f" {BAD} LIBRARY_PROXY_TEMPLATE not set")
        print("     Nothing can be fetched through your institution.")
        return 1
    print(f" {OK} resolver template : {tmpl}")

    cookie = proxy_cookie()
    if cookie:
        n = sum(1 for chunk in cookie.split(";;") for p in
                chunk.rpartition("|")[2].split(";") if "=" in p)
        print(f" {OK} session cookie    : {n} cookie(s) stored")
    else:
        print(f" {WARN} session cookie    : none")
        print("     The automated download cannot authenticate without one.")
        print("     The 'GET VIA INSTITUTION' link still works — it uses your")
        print("     browser's session instead. To enable automation:")
        print("       python3 tools/set_proxy_cookie.py <copy-as-curl file>")

    # A REAL paper, from the researcher's own queue.
    conn = db()
    doi = ""
    if "--doi" in sys.argv:
        doi = sys.argv[sys.argv.index("--doi") + 1]
        row = conn.execute(
            "SELECT * FROM new_publications WHERE lower(doi)=? LIMIT 1",
            (doi.lower(),)).fetchone()
    else:
        # Prefer a paper KNOWN to be paywalled and NOT already on disk.
        #
        # Both conditions matter. An open-access paper succeeds via Unpaywall and
        # proves nothing about the institutional route; a paper already
        # downloaded returns instantly from the on-disk cache and proves even
        # less. The first run of this tool picked a cached bioRxiv preprint and
        # cheerfully reported success without making a single network request.
        row = conn.execute("""
            SELECT * FROM new_publications
            WHERE doi != '' AND acq_status = 'failed'
              AND COALESCE(pdf_path,'') = ''
              AND doi NOT LIKE '10.1371%' AND doi NOT LIKE '10.64898%'
            ORDER BY relevance DESC LIMIT 1""").fetchone()
        if row is None:
            row = conn.execute("""
                SELECT * FROM new_publications
                WHERE doi != '' AND COALESCE(pdf_path,'') = ''
                  AND doi NOT LIKE '10.1371%' AND doi NOT LIKE '10.64898%'
                ORDER BY relevance DESC LIMIT 1""").fetchone()

    if row is None:
        print(f"\n {WARN} no publication with a DOI to test against.")
        return 0

    pub = dict(row)
    print(f"\n testing with a real paper from your queue:")
    print(f"   {(pub.get('title') or '')[:64]}")
    print(f"   {pub.get('journal') or '?'}  ·  {pub.get('doi')}")

    landing = publisher_url(pub.get("doi") or "")
    print(f"\n {OK if landing else WARN} publisher URL    : "
          f"{landing[:60] or '(Crossref could not resolve it)'}")
    print(f"   link-out         : {resolver_url(pub.get('doi') or '')[:72]}…")

    # force=True: a check that can be satisfied by a file already on disk tells
    # you nothing about whether the network path works today.
    pub["pdf_path"] = ""
    print("\n running the real acquisition ladder (cache bypassed)…")
    res = acquire_pdf(conn, dict(pub), force=True)
    conn.commit()

    print()
    if res["status"] == "ok":
        via = res.get("method", "")
        if via.startswith("institutional"):
            print(f" {OK} INSTITUTIONAL DOWNLOAD WORKS — obtained via your session.")
        else:
            print(f" {OK} obtained via {via} (open access) — this did not test the")
            print(f"     institutional route. Re-run with --doi <a paywalled DOI>.")
        print(f"     saved: {res['path']}")
        rc = 0
    else:
        reason = res["reason"]
        print(f" {BAD} not obtained — {reason}")
        print()
        if "sign-in required" in reason or "not authenticated" in reason:
            print("     Expected when no cookie is stored, or when it has expired.")
            print("     Fix: sign in again in your browser, re-copy the request,")
            print("          python3 tools/set_proxy_cookie.py <file>")
        elif "entitlements" in reason:
            print("     Your institution has no subscription for this publisher.")
            print("     Nothing to configure — request it through the library.")
        elif "no open-access" in reason:
            print("     No legal open copy exists and no institutional route")
            print("     produced a PDF. The link-out is the remaining option.")
        rc = 2

    conn.close()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
