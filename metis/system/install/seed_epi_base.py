"""
seed_epi_base.py — Seeds the Biostatistics for Epidemiologists course
into the Metis database.

This is the content pack for the "full" base install. It registers:
  - 12 biostatistics lessons as learning_courses entries
  - Spaced-repetition topics per lesson
  - A content_packs record (pack_id: biostatistics-course)

The PH content pack (HAT/NTD library cards, epi literature, domain
knowledge) is in seed_ph_database.py and is only for Metis_PH.

Toggle off: DELETE FROM content_packs WHERE pack_id = 'biostatistics-course'
            DELETE FROM learning_courses WHERE slug LIKE 'biostats-%'
Toggle on:  run this script again.

Usage:
  python seed_epi_base.py --db /path/to/metis.sqlite [--quiet] [--remove]
"""

import argparse
import datetime
import json
import sqlite3
import sys
from pathlib import Path

PACK_ID = "biostatistics-course"
PACK_VERSION = "1.0"

COURSE_SLUG = "biostatistics-for-epidemiologists"

LESSONS = [
    (1,  "01-descriptive-statistics",     "Descriptive Statistics",
     "Central tendency, spread, distributions, and graphical summaries."),
    (2,  "02-probability-basics",          "Probability Basics",
     "Events, conditional probability, Bayes' theorem, independence."),
    (3,  "03-probability-distributions",   "Probability Distributions",
     "Binomial, Poisson, normal — when to use each and key properties."),
    (4,  "04-confidence-intervals",        "Confidence Intervals",
     "Construction, interpretation, and common misconceptions."),
    (5,  "05-hypothesis-testing",          "Hypothesis Testing",
     "Null and alternative hypotheses, p-values, Type I and II errors."),
    (6,  "06-chi-square-and-t-tests",      "Chi-Square & t-Tests",
     "Tests for categorical and continuous outcomes."),
    (7,  "07-correlation-simple-regression", "Correlation & Simple Regression",
     "Pearson r, linear regression, assumptions, and interpretation."),
    (8,  "08-multiple-regression",         "Multiple Regression",
     "Confounding, model building, collinearity, and diagnostics."),
    (9,  "09-logistic-regression",         "Logistic Regression",
     "Binary outcomes, odds ratios, likelihood, ROC curves."),
    (10, "10-survival-analysis",           "Survival Analysis",
     "Kaplan-Meier, log-rank test, Cox proportional hazards model."),
    (11, "11-poisson-regression",          "Poisson & Negative Binomial Regression",
     "Count outcomes, rate ratios, overdispersion."),
    (12, "12-intro-multilevel-models",     "Introduction to Multilevel Models",
     "Clustered data, random intercepts, ICC, and when MLM is needed."),
]

SRS_TOPICS = {
    "01-descriptive-statistics":       ["mean vs median", "variance vs SD", "skewness", "IQR"],
    "02-probability-basics":           ["conditional probability", "Bayes theorem", "sensitivity vs specificity"],
    "03-probability-distributions":    ["normal distribution", "Poisson assumptions", "binomial vs Poisson"],
    "04-confidence-intervals":         ["95% CI interpretation", "CI vs p-value", "wide CIs — what they mean"],
    "05-hypothesis-testing":           ["p-value definition", "Type I vs Type II", "statistical vs clinical significance"],
    "06-chi-square-and-t-tests":       ["chi-square assumptions", "paired vs independent t", "Fisher exact"],
    "07-correlation-simple-regression": ["r² interpretation", "regression assumptions", "correlation ≠ causation"],
    "08-multiple-regression":          ["confounding control", "collinearity", "model selection criteria"],
    "09-logistic-regression":          ["odds ratio interpretation", "log-odds", "Hosmer-Lemeshow"],
    "10-survival-analysis":            ["hazard ratio", "censoring", "PH assumption"],
    "11-poisson-regression":           ["rate ratio", "offset term", "overdispersion check"],
    "12-intro-multilevel-models":      ["ICC calculation", "random vs fixed effects", "when MLM is needed"],
}


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


def seed_pack(conn: sqlite3.Connection, quiet: bool = False) -> None:
    now = datetime.datetime.now().isoformat(timespec="seconds")

    # Check if already seeded
    existing = conn.execute(
        "SELECT pack_id FROM content_packs WHERE pack_id = ?", (PACK_ID,)
    ).fetchone()
    if existing:
        if not quiet:
            print(f"Pack '{PACK_ID}' already installed — skipping.")
        return

    # Register the parent course entry
    existing_course = conn.execute(
        "SELECT id FROM learning_courses WHERE slug = ?", (COURSE_SLUG,)
    ).fetchone()

    if not existing_course:
        conn.execute(
            """INSERT INTO learning_courses
               (title, category, progress_pct, total_modules, completed_modules,
                status, created_at, slug)
               VALUES (?, 'methods', 0, 12, 0, 'active', ?, ?)""",
            ("Biostatistics for Epidemiologists", now, COURSE_SLUG),
        )
        course_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    else:
        course_id = existing_course["id"]
        # Remove stale topic rows before re-seeding
        conn.execute("DELETE FROM course_topics WHERE course_id = ?", (course_id,))

    # Seed SRS topics
    for slug, topics in SRS_TOPICS.items():
        for kw in topics:
            conn.execute(
                "INSERT INTO course_topics (course_id, keyword) VALUES (?, ?)",
                (course_id, kw),
            )

    # Register content pack
    conn.execute(
        """INSERT INTO content_packs
           (pack_id, name, version, pack_type, description, installed_at, enabled)
           VALUES (?, ?, ?, 'course', ?, ?, 1)""",
        (
            PACK_ID,
            "Biostatistics for Epidemiologists",
            PACK_VERSION,
            "12-lesson course covering descriptive stats, inference, "
            "regression, survival analysis, and multilevel models.",
            now,
        ),
    )
    conn.commit()

    if not quiet:
        print(f"✓ Biostatistics course seeded ({len(LESSONS)} lessons, "
              f"{sum(len(v) for v in SRS_TOPICS.values())} SRS topics)")
        print(f"  Pack registered: {PACK_ID} v{PACK_VERSION}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or remove the Biostatistics course pack.")
    parser.add_argument("--db", required=True, help="Path to metis.sqlite")
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
            seed_pack(conn, quiet=args.quiet)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
