"""
seed_epi_base.py — Seeds the Statistics for Epidemiology course
into the Metis database.

This is the content pack for the "full" base install. It registers:
  - All statistics lessons from knowledge/courses/statistics/ (count is dynamic)
  - Spaced-repetition topics per lesson
  - A content_packs record (pack_id: statistics-course)

The PH content pack (Metis_PH: specialist/NTD library cards, epi literature,
domain knowledge) is in seed_ph_database.py and is only for Metis_PH.

Toggle off: DELETE FROM content_packs WHERE pack_id = 'statistics-course'
            DELETE FROM learning_courses WHERE slug = 'statistics-for-epidemiology'
Toggle on:  run this script again.

Usage:
  python seed_epi_base.py --db /path/to/metis.sqlite [--quiet] [--remove]
                          [--course-dir /path/to/knowledge/courses/statistics]
"""

import argparse
import datetime
import json
import sqlite3
import sys
from pathlib import Path

PACK_ID = "statistics-course"
PACK_VERSION = "1.0"

COURSE_SLUG = "statistics-for-epidemiology"
COURSE_TITLE = "Statistics for Epidemiology"

# Default course folder — can be overridden via --course-dir argument.
# The script reads lessons.json (and counts .md files) dynamically so the
# lesson count is never hardcoded here.
_DEFAULT_COURSE_DIRS = [
    # Canonical location after rename
    "knowledge/courses/statistics",
    # Legacy location (folder was originally named biostatistics/)
    "knowledge/courses/biostatistics",
]


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, category TEXT, progress_pct REAL DEFAULT 0,
            total_modules INTEGER DEFAULT 0, completed_modules INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active', completed_at TEXT, created_at TEXT,
            slug TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content_packs (
            pack_id TEXT PRIMARY KEY, name TEXT NOT NULL,
            version TEXT DEFAULT '1.0', pack_type TEXT DEFAULT 'course',
            description TEXT DEFAULT '', installed_at TEXT, enabled INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS course_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL, keyword TEXT NOT NULL
        )
    """)
    conn.commit()


def remove_pack(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM content_packs WHERE pack_id = ?", (PACK_ID,))
    conn.execute("DELETE FROM learning_courses WHERE slug = ?", (COURSE_SLUG,))
    conn.commit()
    print("Biostatistics course removed.")


def _find_course_dir(override: str = "") -> Path | None:
    """Locate the statistics course folder."""
    if override:
        p = Path(override)
        return p if p.exists() else None
    # Search relative to this script (works from installer/ or repo root)
    script_dir = Path(__file__).parent
    for rel in _DEFAULT_COURSE_DIRS:
        # Try relative to script's parent chain up to 5 levels
        base = script_dir
        for _ in range(6):
            candidate = base / rel
            if candidate.exists():
                return candidate
            base = base.parent
    return None


def _read_lessons(course_dir: Path) -> tuple[int, list[str]]:
    """Return (total_lessons, list_of_srs_keywords) from lessons.json + .md files."""
    lessons_json = course_dir / "lessons.json"
    md_files = sorted((course_dir / "lessons").glob("*.md")) if (course_dir / "lessons").exists() else []

    total = len(md_files)
    keywords: list[str] = []

    if lessons_json.exists():
        try:
            data = json.loads(lessons_json.read_text(encoding="utf-8"))
            lesson_list = data.get("lessons", [])
            total = max(total, len(lesson_list))
            for lesson in lesson_list:
                title = lesson.get("title", "")
                desc = lesson.get("description", "")
                if title:
                    keywords.append(title)
                if desc:
                    keywords.append(desc[:60])
        except Exception:
            pass

    return total, keywords


def seed_pack(conn: sqlite3.Connection, quiet: bool = False,
              course_dir_override: str = "") -> None:
    now = datetime.datetime.now().isoformat(timespec="seconds")

    # Check if already seeded
    existing = conn.execute(
        "SELECT pack_id FROM content_packs WHERE pack_id = ?", (PACK_ID,)
    ).fetchone()
    if existing:
        if not quiet:
            print(f"Pack '{PACK_ID}' already installed — skipping.")
        return

    # Locate course directory and read lesson count dynamically
    course_dir = _find_course_dir(course_dir_override)
    total_lessons = 0
    srs_keywords: list[str] = []
    if course_dir:
        total_lessons, srs_keywords = _read_lessons(course_dir)

    # Register the parent course entry
    existing_course = conn.execute(
        "SELECT id FROM learning_courses WHERE slug = ?", (COURSE_SLUG,)
    ).fetchone()

    if not existing_course:
        conn.execute(
            """INSERT INTO learning_courses
               (title, category, progress_pct, total_modules, completed_modules,
                status, created_at, slug)
               VALUES (?, 'methods', 0, ?, 0, 'active', ?, ?)""",
            (COURSE_TITLE, total_lessons, now, COURSE_SLUG),
        )
        course_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    else:
        course_id = existing_course["id"]
        # Refresh module count and remove stale SRS topics
        conn.execute(
            "UPDATE learning_courses SET total_modules=?, title=? WHERE id=?",
            (total_lessons, COURSE_TITLE, course_id),
        )
        conn.execute("DELETE FROM course_topics WHERE course_id = ?", (course_id,))

    # Seed SRS topics from the actual lesson content
    for kw in srs_keywords:
        conn.execute(
            "INSERT INTO course_topics (course_id, keyword) VALUES (?, ?)",
            (course_id, kw),
        )

    desc = f"Statistics course for epidemiologists covering statistical inference, regression, survival analysis, and multilevel models."
    if total_lessons:
        desc = f"{total_lessons}-lesson statistics course for epidemiologists."

    # Register content pack
    conn.execute(
        """INSERT INTO content_packs
           (pack_id, name, version, pack_type, description, installed_at, enabled)
           VALUES (?, ?, ?, 'course', ?, ?, 1)""",
        (PACK_ID, COURSE_TITLE, PACK_VERSION, desc, now),
    )
    conn.commit()

    if not quiet:
        print(f"✓ Statistics course seeded ({total_lessons} lessons, "
              f"{len(srs_keywords)} SRS topics)")
        print(f"  Pack registered: {PACK_ID} v{PACK_VERSION}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or remove the Statistics for Epidemiology course pack.")
    parser.add_argument("--db", required=True, help="Path to metis.sqlite")
    parser.add_argument("--course-dir", default="",
                        help="Path to the statistics course folder (auto-detected if omitted)")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--remove", action="store_true",
                        help="Remove the pack instead of installing it")
    parser.add_argument("--schema-only", action="store_true",
                        help="Only create tables, don't seed any data")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect(str(db_path))
    try:
        ensure_tables(conn)
        if args.schema_only:
            if not args.quiet:
                print("Schema tables ensured.")
            return
        if args.remove:
            remove_pack(conn)
        else:
            seed_pack(conn, quiet=args.quiet, course_dir_override=args.course_dir)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
