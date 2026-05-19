#!/usr/bin/env python3
"""
init_db.py — Create metis.sqlite from schema.sql on a fresh install.

Skips silently if the DB already exists.
"""
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    installer_dir = Path(__file__).parent
    metis_root    = installer_dir.parent.parent   # installer/ -> system/ -> metis/

    db_dir        = metis_root / "system" / "app" / "data"
    db_path       = db_dir / "metis.sqlite"
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
