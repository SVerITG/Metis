#!/usr/bin/env python3
"""normalise_pub_dates.py — give every publication one sortable date.

WHY THIS EXISTS
    `new_publications.pub_date` holds whatever its source handed over:

        2026-08-18      (feeds, OpenAlex — ISO)
        2026 Jul 1      (PubMed esummary)
        2026 Aug        (PubMed, month precision)
        2026            (year only)
        ''              (feeds with no date at all)

    A time window cannot be built on that. `WHERE pub_date >= '2026-08-20'` sorts
    "2026 Jul 1" as LATER than "2026-08-20", because it compares strings — so a
    July paper appears under Today and an August one does not. Silently.

    That matters more than usual here. The retrospective HAT sweep added 400+
    papers going back four years, all discovered on the same day. Filtering on
    `discovered_at` would file every one of them under "Today"; filtering on the
    raw `pub_date` string would file them arbitrarily. Neither is usable.

THE RULE
    `pub_iso` = the publication date normalised to ISO, at whatever precision the
    source gave (a month becomes its first day; a year becomes 1 January). If no
    publication date is recoverable at all, `pub_iso` stays empty and readers fall
    back to `discovered_at` — which is honest: for an undated item, "when Metis
    found it" is genuinely the only date there is.

    Month-precision dates are marked in `pub_precision` so a surface can say
    "Aug 2026" rather than implying the 1st.

USAGE
    python3 tools/normalise_pub_dates.py --dry-run
    python3 tools/normalise_pub_dates.py
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

_ISO_RE   = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_YMD_RE   = re.compile(r"^(\d{4})\s+([A-Za-z]{3,9})\s+(\d{1,2})")
_YM_RE    = re.compile(r"^(\d{4})\s+([A-Za-z]{3,9})")
_YEAR_RE  = re.compile(r"^(\d{4})")
_SLASH_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})")


def normalise(raw: str) -> tuple[str, str]:
    """Return (iso_date, precision). precision ∈ {'day','month','year',''}."""
    s = (raw or "").strip()
    if not s:
        return "", ""

    m = _ISO_RE.match(s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo}-{d}", "day"

    m = _SLASH_RE.match(s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}", "day"

    m = _YMD_RE.match(s)
    if m:
        y, mon, d = m.groups()
        mi = MONTHS.get(mon[:3].lower())
        if mi:
            day = min(max(int(d), 1), 28 if mi == 2 else 30)
            return f"{y}-{mi:02d}-{day:02d}", "day"

    m = _YM_RE.match(s)
    if m:
        y, mon = m.groups()
        mi = MONTHS.get(mon[:3].lower())
        if mi:
            return f"{y}-{mi:02d}-01", "month"

    m = _YEAR_RE.match(s)
    if m:
        y = int(m.group(1))
        # A four-digit number that is not a plausible publication year is almost
        # certainly something else that leaked into the field (a page count, an
        # accession number), and guessing would be worse than admitting ignorance.
        if 1800 <= y <= 2100:
            return f"{y}-01-01", "year"
    return "", ""


def db_path() -> Path:
    env = os.environ.get("METIS_DB_PATH", "")
    if env and Path(env).exists():
        return Path(env)
    return Path.home() / ".local/share/metis" / "metis.sqlite"


def main() -> int:
    dry = "--dry-run" in sys.argv
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row

    cols = {r[1] for r in con.execute("PRAGMA table_info(new_publications)")}
    for col, decl in (("pub_iso", "TEXT DEFAULT ''"),
                      ("pub_precision", "TEXT DEFAULT ''")):
        if col not in cols:
            print(f"  + adding column {col}")
            if not dry:
                con.execute(f"ALTER TABLE new_publications ADD COLUMN {col} {decl}")
    if not dry:
        con.execute("CREATE INDEX IF NOT EXISTS idx_newpub_pubiso "
                    "ON new_publications(pub_iso)")

    rows = con.execute(
        "SELECT id, pub_date, discovered_at FROM new_publications"
    ).fetchall()

    counts = {"day": 0, "month": 0, "year": 0, "": 0}
    updates = []
    for r in rows:
        iso, prec = normalise(r["pub_date"] or "")
        counts[prec] = counts.get(prec, 0) + 1
        updates.append((iso, prec, r["id"]))

    if not dry:
        con.executemany(
            "UPDATE new_publications SET pub_iso=?, pub_precision=? WHERE id=?",
            updates)
        con.commit()

    total = len(rows)
    resolved = total - counts.get("", 0)
    print(f"  {total} row(s): {resolved} with a publication date "
          f"({counts['day']} day, {counts['month']} month, {counts['year']} year), "
          f"{counts.get('', 0)} undated → fall back to discovered_at")

    if not dry:
        sample = con.execute(
            "SELECT pub_date, pub_iso, pub_precision FROM new_publications "
            "WHERE pub_date != '' AND pub_precision != 'day' LIMIT 6"
        ).fetchall()
        if sample:
            print("  sample of non-ISO inputs resolved:")
            for s in sample:
                print(f"      {s['pub_date']!r:<18} → {s['pub_iso']} ({s['pub_precision']})")
    con.close()
    print(f"\n  {'DRY RUN — nothing written' if dry else '✓ normalised'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
