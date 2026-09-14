#!/usr/bin/env python3
"""scan_decks.py — index the presentation decks already on disk.

WHY THIS EXISTS. The folders can answer "where is the file". They cannot answer
the question that actually comes up: what have we already said about this, to
whom, and how did we say it differently last time. That needs the same lesson,
recognised across the collections it was delivered in — which is a join, and a
join needs an index.

READ-ONLY. Nothing here moves, renames, opens for writing or deletes a file. The
decks stay exactly where their owner put them; only the database changes. A tool
that reorganises someone's Documents folder to suit its own index is a tool they
stop running, and then the index is stale, which is worse than no index.

WHAT IS NOT HARDCODED. Collection names are DERIVED, not listed. This file ships
in a public repository, so it carries no folder names, project names or places
from any particular library. The derivation is a generic rule — the nearest
folder above the file that is not a structural word — plus an optional local
override file that is never committed:

    system/config/local/decks.yml        (gitignored)
      root: /path/to/documents           # default: two levels above the RC root
      skip: ["some/subtree"]             # relative paths to leave out entirely
      collections:                       # rel-path prefix -> the name to show
        "a/b/c": "Readable name"
      styles:                            # rel-path prefix -> style name
        "a/b": "StyleName"

Usage:
    python3 tools/scan_decks.py            # show what would change
    python3 tools/scan_decks.py --apply    # write it
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DECK_EXT = {".pptx", ".ppt", ".potx", ".ppsx"}

# Folder names that describe STRUCTURE rather than a body of work. The nearest
# folder above a deck is usually its collection — unless it is one of these, in
# which case the answer is one level further up. Kept lowercase and accent-free
# so the comparison is not defeated by how a folder happens to be typed.
STRUCTURAL = {
    "formation", "formations", "presentation", "presentations", "ppt", "ppts",
    "slides", "master", "masters", "template", "templates", "archive",
    "archives", "old", "backup", "backups", "copy", "copies", "final", "draft",
    "drafts", "docs", "documents", "files", "material", "materials",
    "ressources", "resources", "implementation", "project", "projects",
    "general", "divers", "misc", "new", "temp", "tmp", "output", "outputs",
    "version", "versions", "v1", "v2", "v3", "images", "photos",
}

# A path segment matching one of these marks the deck as something other than a
# live delivery. Order matters only for reporting; the first hit wins.
VARIANT_RULES = [
    ("archive", re.compile(r"^(archive|archives|old|backup|backups)$", re.I)),
    ("copy",    re.compile(r"(usb|cl[eé] usb|copie|copy of|duplicate)", re.I)),
]

# Leading ordinals and trailing dates carried by filenames — "05_", "3. ",
# "_2026", "_16032026". Stripped for the lesson key so the same lesson delivered
# in two years is one lesson, not two.
_LEAD_NUM = re.compile(r"^\s*\d{1,3}\s*[._)\-]\s*")
_TRAIL_DATE = re.compile(r"[_\-\s]*(\d{6,8}|\d{4}([_\-]\d{2}){0,2}|v\d+)\s*$", re.I)
_PUNCT = re.compile(r"[^a-z0-9]+")


def norm(s: str) -> str:
    """Lowercase, accent-free, punctuation-free. For comparing names only."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _PUNCT.sub(" ", s.lower()).strip()


def lesson_key(filename: str) -> str:
    """The name with its position and its date removed.

    "5_Traitement_THA_RCA_2026.pptx" and "6. Traitement THA.pptx" reduce to the
    same key, which is what makes them one lesson delivered twice. Country and
    year tokens are NOT stripped here — they are part of the name the owner
    chose, and guessing which token is a place is how a key starts merging
    lessons that are genuinely different.
    """
    stem = Path(filename).stem
    stem = _LEAD_NUM.sub("", stem)
    for _ in range(3):                       # "…_RCA_2026" then "…_16032026"
        new = _TRAIL_DATE.sub("", stem)
        if new == stem:
            break
        stem = new
    return norm(stem)


def slide_count(path: Path) -> int:
    """How many slides, read from the package without opening PowerPoint.

    A .pptx is a zip; its slides are entries under ppt/slides/. The legacy
    binary .ppt is not, and returns 0 — reported as unknown rather than as a
    deck with no slides, because those are different facts.
    """
    if path.suffix.lower() == ".ppt":
        return 0
    try:
        with zipfile.ZipFile(path) as z:
            return sum(1 for n in z.namelist()
                       if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
    except Exception:
        return 0


def variant_of(parts: tuple[str, ...]) -> str:
    for name, rx in VARIANT_RULES:
        for p in parts:
            if rx.search(p):
                return name
    return ""


def collection_of(parts: tuple[str, ...], overrides: dict) -> str:
    """The nearest folder above the deck that names a body of work.

    An override wins when one is configured — the owner knows what their
    collections are called, and a rule good enough to guess every time does not
    exist. Absent an override, walk up past the structural folders.
    """
    rel = "/".join(parts)
    for prefix, name in overrides.items():
        if rel.startswith(prefix):
            return name
    for seg in reversed(parts[:-1]):         # [:-1] — the last part is the file
        clean = _LEAD_NUM.sub("", seg).strip()
        if norm(clean) and norm(clean) not in STRUCTURAL:
            return clean
    return ""


def event_of(parts: tuple[str, ...]) -> str:
    """A folder whose name carries a year is an OCCASION, not a collection.

    Ateliers, workshops and conferences arrive as a date and a place; their decks
    were presented once, to a room. Recognising that generically means looking
    for a four-digit year in a folder name, which is what distinguishes "the 2025
    one" from a kit that gets re-delivered.
    """
    for seg in reversed(parts[:-1]):
        if re.search(r"\b(19|20)\d{2}\b", seg) and not re.fullmatch(r"[\d._\-\s]+", seg):
            return _LEAD_NUM.sub("", seg).strip()
    return ""


def load_config(rc_root: Path) -> dict:
    cfg = {"root": "", "skip": [], "collections": {}, "styles": {}}
    p = rc_root / "system" / "config" / "local" / "decks.yml"
    if not p.exists():
        return cfg
    try:
        import yaml
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for k in cfg:
            if k in raw and raw[k]:
                cfg[k] = raw[k]
    except Exception as exc:
        print(f"  ! could not read {p.name} ({exc}); using defaults", file=sys.stderr)
    return cfg


def db_path() -> Path:
    env = os.environ.get("METIS_DB")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "metis" / "metis.sqlite"


def scan(root: Path, cfg: dict) -> list[dict]:
    skip = [s.strip("/") for s in (cfg.get("skip") or [])]
    overrides = cfg.get("collections") or {}
    styles = cfg.get("styles") or {}
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Never index the tool's own repository or a hidden tree.
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        if any(rel_dir == s or rel_dir.startswith(s + "/") for s in skip):
            dirnames[:] = []
            continue
        for fn in filenames:
            if Path(fn).suffix.lower() not in DECK_EXT or fn.startswith("~$"):
                continue
            full = Path(dirpath) / fn
            rel = f"{rel_dir}/{fn}" if rel_dir else fn
            parts = tuple(rel.split("/"))
            try:
                st = full.stat()
            except OSError:
                continue
            style = ""
            for prefix, name in styles.items():
                if rel.startswith(prefix):
                    style = name
                    break
            out.append({
                "deck_id": hashlib.sha1(rel.encode("utf-8")).hexdigest()[:16],
                "rel_path": rel,
                "filename": fn,
                "title": _LEAD_NUM.sub("", Path(fn).stem).replace("_", " ").strip(),
                "lesson_key": lesson_key(fn),
                "collection": collection_of(parts, overrides),
                "event": event_of(parts),
                "slide_count": slide_count(full),
                "style": style,
                "is_master": 1 if full.suffix.lower() == ".potx" else 0,
                "variant": variant_of(parts),
                "size_bytes": st.st_size,
                "modified_at": datetime.fromtimestamp(
                    st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
            })
    return out


# Columns the scanner owns. Everything else on the row — author, register,
# audience, what changed about this delivery — is written by the person and must
# survive a rescan, so an UPSERT that overwrote the whole row would erase the
# only fields the file cannot tell you.
OWNED = ("rel_path", "filename", "title", "lesson_key", "collection", "event",
         "slide_count", "style", "is_master", "variant", "size_bytes",
         "modified_at", "scanned_at")


def write(rows: list[dict], apply: bool) -> dict:
    con = sqlite3.connect(str(db_path()))
    con.row_factory = sqlite3.Row
    have = {r["deck_id"]: dict(r) for r in con.execute(
        "SELECT deck_id, rel_path, slide_count, modified_at FROM decks")}
    now = datetime.now().isoformat(timespec="seconds")
    new = [r for r in rows if r["deck_id"] not in have]
    changed = [r for r in rows
               if r["deck_id"] in have
               and (have[r["deck_id"]]["modified_at"] != r["modified_at"]
                    or have[r["deck_id"]]["slide_count"] != r["slide_count"])]
    seen = {r["deck_id"] for r in rows}
    gone = [d for d in have if d not in seen]

    if apply:
        cols = ", ".join(OWNED)
        marks = ", ".join("?" * (len(OWNED) + 1))
        upd = ", ".join(f"{c}=excluded.{c}" for c in OWNED)
        con.executemany(
            f"INSERT INTO decks (deck_id, {cols}) VALUES ({marks}) "
            f"ON CONFLICT(deck_id) DO UPDATE SET {upd}",
            [tuple([r["deck_id"]] + [r.get(c, "") if c != "scanned_at" else now
                                     for c in OWNED]) for r in rows])
        # A deck that is no longer on disk is REMOVED from the index rather than
        # kept as a ghost: every row here is meant to point at a file you can
        # open, and a listing full of dead links is the reason people stop
        # trusting an index.
        #
        # BUT NEVER ON A SHORT WALK. "Not in this list" means "no longer on
        # disk" only if the list is a COMPLETE walk. It is also what a walk
        # looks like when the sync folder was offline, the drive was not
        # mounted, or a caller passed a subset — and in each of those cases
        # pruning throws away an index that took minutes to build and every
        # hand-written field on it. Verified the hard way on 2026-09-14: a
        # one-row call deleted 824 rows in a second.
        #
        # So a disappearance of more than half the index is treated as a bad
        # walk rather than a real deletion, and reported instead of applied.
        if gone and len(gone) > max(20, len(have) // 2) and rows:
            print(f"  ! REFUSING to prune {len(gone)} of {len(have)} indexed decks"
                  f" — only {len(rows)} were found on this walk. That looks like an"
                  f" incomplete walk, not a deletion. Nothing was removed.",
                  file=sys.stderr)
            gone = []
        elif gone:
            con.executemany("DELETE FROM decks WHERE deck_id = ?",
                            [(d,) for d in gone])
        con.commit()
    con.close()
    return {"total": len(rows), "new": len(new), "changed": len(changed),
            "gone": len(gone)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write to the database")
    ap.add_argument("--root", default="", help="folder to walk")
    args = ap.parse_args()

    rc_root = Path(os.environ.get("METIS_RC_ROOT") or Path(__file__).resolve().parent.parent)
    cfg = load_config(rc_root)
    root = Path(args.root or cfg.get("root") or rc_root.parent.parent).resolve()
    if not root.is_dir():
        print(f"no such folder: {root}", file=sys.stderr)
        return 2

    print(f"{'APPLYING' if args.apply else 'DRY RUN'} — walking {root}")
    rows = scan(root, cfg)
    r = write(rows, args.apply)
    print(f"  {r['total']} deck(s) found · {r['new']} new · {r['changed']} changed"
          f" · {r['gone']} no longer on disk")

    live = [x for x in rows if not x["variant"]]
    keys = {}
    for x in live:
        keys.setdefault(x["lesson_key"], set()).add(x["collection"])
    multi = {k: v for k, v in keys.items() if len(v) > 1}
    print(f"  {len(live)} live (the rest are snapshots or copies)")
    print(f"  {len(keys)} distinct lesson(s); {len(multi)} delivered in more than one collection")
    if not args.apply:
        print("\nre-run with --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
