#!/usr/bin/env python3
"""Is everything on a Today board actually the kind of thing that board is for?

WHY
    The Outbreaks board stopped being about outbreaks. Measured 2026-09-21: of
    the twelve most recently harvested rows, four were an outbreak — and all
    four were instalments of the same one. The rest were a committee session, a
    declaration, a governance report, an infodemic trends report, a
    surveillance bulletin and two country-office newsletters.

    The corroborating measurement is quieter and worse: `pin_order` was 0 on
    every row of all three boards. The pin machinery had shipped two weeks
    earlier and had never once been used. Nobody pins a feed they have stopped
    reading.

WHAT IT REPORTS
    1. FIT       — every live row, and whether the classifier agrees it belongs
                   on the board it is sitting on.
    2. REFUSED   — every row turned away, with the stored reason. Rejections are
                   kept, not deleted, precisely so this section can exist.
    3. THREADS   — which pin owns which rows, so "these should have nested and
                   did not" is a visible defect rather than a vague impression.

WHAT IT CANNOT TELL YOU
    Whether a link goes where its title says — that is check_board_links.py, and
    the two answer different questions. A correctly-classified outbreak row can
    still point at a landing page.

    It also does not judge CURATED rows (auto_added=0). Those were put there by
    hand and a rule does not get to overrule a person; they are listed apart.

EXIT CODE
    0 when every auto-added live row is on the board the rules would choose,
    1 otherwise — so it can gate a change the way the other checkers do.

USAGE
    python3 tools/check_board_fit.py
    python3 tools/check_board_fit.py --board outbreaks
    python3 tools/check_board_fit.py --refused        # just the rejection log
    python3 tools/check_board_fit.py --apply          # re-file what is already there

    --apply is the only writing mode. It moves a misfiled row to the board the
    rules choose, or marks it refused with its reason. It deletes nothing, so
    every decision it makes can be read back and undone.
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "system" / "mcp-server" / "src"))

DB = Path(os.environ.get("METIS_DB")
          or (Path.home() / ".local/share/metis/metis.sqlite"))
BOARDS = ("outbreaks", "events", "funding")

try:
    from metis_mcp.tools.board_fit import classify
except Exception as exc:                                    # pragma: no cover
    print(f"cannot import the board rules: {exc}")
    raise SystemExit(2)


# A DELIBERATE SECOND COPY of the rule the dashboard uses to decide what a pin
# follows (routers/today.py::_follow_terms). Restated rather than imported,
# because importing it would drag in the whole web application — and because a
# checker that shares its subject's code cannot detect drift in it. If these two
# ever disagree, that disagreement is the finding.
_STOP = {
    "the", "and", "for", "with", "from", "that", "this", "disease", "virus",
    "outbreak", "cases", "case", "report", "situation", "update", "republic",
    "democratic", "national", "annual", "meeting", "call", "calls", "proposals",
    "award", "development", "programme", "program", "research", "health",
    "global", "international", "conference", "congress", "grant", "grants",
}


def follow_terms(title: str, explicit: str = "") -> list[str]:
    if (explicit or "").strip():
        return [w.strip().lower() for w in explicit.split(",") if w.strip()]
    words = re.findall(r"[A-Za-z][A-Za-z'-]{3,}", title or "")
    keep = [w for w in words if w.lower() not in _STOP]
    proper = [w for w in keep if w[:1].isupper()]
    return [w.lower() for w in (proper or keep)[:2]]


def rows(con, board: str, dismissed: int, has_reason: bool):
    # The reason column arrives with this change, and the checker has to work on
    # a database that predates it — otherwise the first thing it does on the
    # other computer is crash, and a checker that crashes teaches nothing.
    reason = "COALESCE(fit_reason,'')" if has_reason else "''"
    return con.execute(
        "SELECT id, title, description, source, auto_added, dismissed, "
        "       COALESCE(pin_order,0) AS pin_order, COALESCE(follow_terms,'') AS ft, "
        f"      {reason} AS fit_reason "
        "FROM today_board_items WHERE board=? AND dismissed=? ORDER BY id",
        (board, dismissed)).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--board", choices=BOARDS, help="check one board only")
    ap.add_argument("--refused", action="store_true", help="show only the rejection log")
    ap.add_argument("--apply", action="store_true",
                    help="re-file the rows already on the boards, not just report them")
    args = ap.parse_args()

    if not DB.exists():
        print(f"no database at {DB}")
        return 2
    # Read-only unless asked to write. The gate added with these rules applies to
    # what arrives NEXT; the rows already sitting on a board predate it, and
    # without --apply nothing on screen would change no matter how good the
    # rules are. Re-filing is reversible — a refused row keeps its title, URL
    # and reason and is one flag away from coming back.
    con = sqlite3.connect(str(DB) if args.apply else f"file:{DB}?mode=ro", uri=not args.apply)
    con.row_factory = sqlite3.Row
    have = {r[1] for r in con.execute("PRAGMA table_info(today_board_items)")}
    has_reason = "fit_reason" in have
    if not has_reason:
        if args.apply:
            con.execute("ALTER TABLE today_board_items ADD COLUMN fit_reason TEXT DEFAULT ''")
            con.commit()
            has_reason = True
        else:
            print("NOTE: fit_reason column not present yet — reasons will be blank "
                  "until the dashboard or the MCP tool has run once.")

    boards = [args.board] if args.board else list(BOARDS)
    bad = 0
    grand = {"fits": 0, "misfiled": 0, "curated": 0, "refused": 0, "nested": 0}

    for board in boards:
        live = rows(con, board, 0, has_reason)
        gone = rows(con, board, 1, has_reason)

        if not args.refused:
            print(f"\n=== {board.upper()} — {len(live)} live, {len(gone)} refused ===")
            for r in live:
                fit, why = classify(r["title"], r["description"] or "")
                if not r["auto_added"]:
                    grand["curated"] += 1
                    mark = "curated"
                elif fit == board:
                    grand["fits"] += 1
                    mark = "ok"
                else:
                    grand["misfiled"] += 1
                    mark = f"MISFILED -> {fit or 'no board'}"
                    if args.apply:
                        if fit:
                            con.execute(
                                "UPDATE today_board_items SET board=?, fit_reason=?, "
                                "updated_at=datetime('now') WHERE id=?",
                                (fit, f"re-filed from {board} — {why}", r["id"]))
                            mark = f"re-filed -> {fit}"
                        else:
                            con.execute(
                                "UPDATE today_board_items SET dismissed=1, fit_reason=?, "
                                "updated_at=datetime('now') WHERE id=?", (why, r["id"]))
                            mark = "refused (kept, reversible)"
                    else:
                        bad += 1
                if mark != "ok":
                    print(f"  {r['id']:>5}  {mark:<22} {r['title'][:58]}")
                    print(f"         {why}")
                else:
                    print(f"  {r['id']:>5}  ok                     {r['title'][:58]}")

        if gone:
            print(f"\n  --- refused on {board} ---")
            for r in gone:
                grand["refused"] += 1
                reason = r["fit_reason"] or "(no reason recorded — predates the rules)"
                print(f"  {r['id']:>5}  {r['title'][:58]}")
                print(f"         {reason}")

        if args.refused:
            continue

        # THREADS — who owns whom.
        pins = [r for r in live if r["pin_order"]]
        if not pins:
            print(f"\n  no pins on {board} — nothing nests, every row competes "
                  f"for the top on its own")
            continue
        claimed: set[int] = set()
        for pin in sorted(pins, key=lambda r: r["pin_order"]):
            terms = follow_terms(pin["title"], pin["ft"])
            kids = []
            for r in live:
                if r["id"] == pin["id"] or r["pin_order"] or r["id"] in claimed:
                    continue
                hay = f"{r['title']} {r['description'] or ''}".lower()
                if terms and all(t in hay for t in terms):
                    claimed.add(r["id"])
                    kids.append(r)
            n_news = con.execute(
                "SELECT COUNT(*) FROM news_briefs WHERE " +
                " AND ".join(["LOWER(title || ' ' || COALESCE(summary,'')) LIKE ?"] * len(terms)),
                tuple(f"%{t}%" for t in terms)).fetchone()[0] if terms else 0
            grand["nested"] += len(kids)
            print(f"\n  PIN #{pin['pin_order']} [{pin['id']}] {pin['title'][:56]}")
            print(f"       follows: {' + '.join(terms) or '(no usable terms)'}"
                  f"  ·  {len(kids)} board row(s), {n_news} news report(s)")
            for k in kids:
                print(f"       └ [{k['id']}] {k['title'][:56]}")

    if args.apply:
        con.commit()
    con.close()
    print("\n" + "-" * 68)
    print("fits {fits} · misfiled {misfiled} · curated (not judged) {curated} · "
          "refused {refused} · nested under a pin {nested}".format(**grand))
    if args.apply:
        print("APPLIED: the misfiled rows above were moved or refused. Nothing was "
              "deleted — re-run without --apply to confirm.")
        return 0
    if bad:
        print(f"FAIL: {bad} auto-added row(s) are on the wrong board. "
              f"Re-file them with --apply.")
    else:
        print("PASS: every auto-added live row is on the board the rules choose.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
