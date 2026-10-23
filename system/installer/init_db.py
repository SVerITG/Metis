#!/usr/bin/env python3
"""
init_db.py — Create metis.sqlite from schema.sql on a fresh install.

Skips silently if the DB already exists.
"""
import sqlite3
import sys
from pathlib import Path


def live_db_path(root: Path) -> Path:
    """The database the server and dashboard actually read.

    NOT system/app/data/metis.sqlite: that location was retired in June (OneDrive
    corrupts SQLite's write-ahead log), and a database created or written there is
    an orphan. The MCP package owns the rule; this mirrors it when the package is
    not importable: METIS_DB → METIS_DATA_DIR → ~/.local/share/metis/metis.sqlite.
    """
    try:
        from metis_mcp.config import resolve_live_db
        return resolve_live_db(root)
    except ImportError:
        import os
        if os.environ.get("METIS_DB"):
            return Path(os.environ["METIS_DB"])
        data_dir = os.environ.get("METIS_DATA_DIR") or os.path.join(
            os.path.expanduser("~"), ".local", "share", "metis")
        return Path(data_dir) / "metis.sqlite"


def main() -> int:
    installer_dir = Path(__file__).parent
    metis_root    = installer_dir.parent.parent   # installer/ -> system/ -> metis/

    db_path       = live_db_path(metis_root)
    db_dir        = db_path.parent
    schema_path   = installer_dir / "schema.sql"

    if db_path.exists():
        print(f"[OK] DB already exists: {db_path}")
        return 0

    if not schema_path.exists():
        print(f"[ERROR] schema.sql not found at {schema_path}")
        return 1

    db_dir.mkdir(parents=True, exist_ok=True)
    schema = schema_path.read_text(encoding="utf-8")

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()

    print(f"[OK] Created: {db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
