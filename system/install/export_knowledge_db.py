#!/usr/bin/env python3
"""
export_knowledge_db.py — Export the Metis knowledge index to a standalone SQLite file.

Exports three tables from the main metis.sqlite:
  - library_fulltext   (PDF text chunks with metadata)
  - vec_pdf_chunks     (sqlite-vec virtual table — binary encoded)
  - pdf_chunks         (raw chunk rows if present)

The output knowledge_db.sqlite is a self-contained file suitable for:
  - shipping with the Docker image as a pre-built index
  - distributing as a release asset for users who skip local indexing
  - seeding a fresh installation

Usage:
    python export_knowledge_db.py [--source <path>] [--out <path>] [--dry-run]

Defaults:
    source: $METIS_RC_ROOT/system/app/data/metis.sqlite
    out:    dist/knowledge_db.sqlite  (next to this script)
"""

import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path


def resolve_source(override: str | None) -> Path:
    if override:
        return Path(override)
    root_env = os.environ.get("METIS_RC_ROOT", "")
    if root_env:
        return Path(root_env) / "system" / "app" / "data" / "metis.sqlite"
    # Fallback: infer from script location (metis/system/install/ → metis/)
    script_dir = Path(__file__).resolve().parent
    metis_root = script_dir.parent.parent  # metis/system/install → metis
    return metis_root / "system" / "app" / "data" / "metis.sqlite"


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','shadow') AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def row_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM [{table}]")
        return cur.fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def export_regular_table(
    src: sqlite3.Connection, dst: sqlite3.Connection, table: str
) -> int:
    """Copy a regular table (schema + data) from src to dst."""
    schema_row = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not schema_row:
        return 0
    dst.execute(schema_row[0])

    rows = src.execute(f"SELECT * FROM [{table}]").fetchall()
    if rows:
        cols = len(rows[0])
        placeholders = ",".join(["?"] * cols)
        dst.executemany(f"INSERT INTO [{table}] VALUES ({placeholders})", rows)
    return len(rows)


def export_virtual_table(
    src: sqlite3.Connection, dst: sqlite3.Connection, table: str
) -> int:
    """Copy a sqlite-vec virtual table via its shadow tables."""
    # sqlite-vec shadow tables follow the pattern: <table>_data, <table>_index, etc.
    shadow_tables = src.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ? ORDER BY name",
        (f"{table}_%",),
    ).fetchall()

    # Re-create the virtual table declaration
    vt_row = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if vt_row and vt_row[0]:
        try:
            dst.execute(vt_row[0])
        except sqlite3.OperationalError:
            pass  # Extension may not be loaded in dst — shadow copy suffices

    copied = 0
    for (shadow_name,) in shadow_tables:
        schema_row = src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (shadow_name,),
        ).fetchone()
        if not schema_row or not schema_row[0]:
            continue
        try:
            dst.execute(schema_row[0])
        except sqlite3.OperationalError:
            pass  # Already exists
        rows = src.execute(f"SELECT * FROM [{shadow_name}]").fetchall()
        if rows:
            cols = len(rows[0])
            placeholders = ",".join(["?"] * cols)
            dst.executemany(
                f"INSERT INTO [{shadow_name}] VALUES ({placeholders})", rows
            )
            copied += len(rows)

    return copied


def run(source: Path, out: Path, dry_run: bool) -> int:
    if not source.exists():
        print(f"ERROR: Source database not found: {source}", file=sys.stderr)
        return 1

    print(f"Source : {source}")
    print(f"Output : {out}")

    src = sqlite3.connect(str(source))
    src.row_factory = sqlite3.Row

    # Load sqlite-vec extension if available (needed to read virtual table metadata)
    try:
        src.enable_load_extension(True)
        import sqlite_vec  # type: ignore
        src.load_extension(sqlite_vec.loadable_path())
    except Exception:
        pass  # Not available — shadow copy still works

    tables_to_export = ["library_fulltext", "pdf_chunks"]
    virtual_tables = ["vec_pdf_chunks"]

    print("\nTable inventory:")
    for t in tables_to_export + virtual_tables:
        exists = table_exists(src, t)
        count = row_count(src, t) if exists else 0
        status = f"{count:,} rows" if exists else "not found"
        print(f"  {t:30s} {status}")

    if dry_run:
        print("\n[DRY RUN] No files written.")
        src.close()
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    dst = sqlite3.connect(str(out))

    total = 0
    for table in tables_to_export:
        if table_exists(src, table):
            n = export_regular_table(src, dst, table)
            print(f"  Exported {table}: {n:,} rows")
            total += n
        else:
            print(f"  Skipped  {table}: not found")

    for vt in virtual_tables:
        n = export_virtual_table(src, dst, vt)
        print(f"  Exported {vt} (shadow): {n:,} rows")
        total += n

    dst.execute("PRAGMA journal_mode=WAL")
    dst.commit()
    dst.close()
    src.close()

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"\nDone. {total:,} total rows → {out.name} ({size_mb:.1f} MB)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", help="Path to source metis.sqlite")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).parent / "dist" / "knowledge_db.sqlite"),
        help="Output path (default: dist/knowledge_db.sqlite next to this script)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print inventory only; write nothing")
    args = parser.parse_args()

    source = resolve_source(args.source)
    out = Path(args.out)

    sys.exit(run(source, out, args.dry_run))


if __name__ == "__main__":
    main()
