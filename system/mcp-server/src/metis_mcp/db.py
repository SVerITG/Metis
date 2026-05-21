"""SQLite connection helper with WAL mode for safe concurrent access."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(db_path: Path):
    """Open a SQLite connection with WAL mode and Row factory.

    WAL mode allows concurrent reads from the R Shiny dashboard
    while the MCP server writes.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
