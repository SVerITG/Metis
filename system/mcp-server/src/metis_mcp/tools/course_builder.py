"""Course Builder orchestration tools.

These tools wire up the 7-step Course Builder pipeline to the MCP layer.
The /course-builder slash command skill delegates here for state management
and persistence — the skill itself handles Claude orchestration of the steps.

Steps:
  1. start_course_build()    — intake + create DB record
  2. save_course_outline()   — approve scope plan, save module list
  3. get_course_status()     — check progress across all steps
  4. publish_course()        — finalise, register spaced rep schedule
"""

import datetime
import json
import re
from pathlib import Path

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.db import connect
from metis_mcp.app_instance import app


_COURSE_DDL = """
CREATE TABLE IF NOT EXISTS course_builds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    target_audience TEXT DEFAULT '',
    duration_hours INTEGER DEFAULT 0,
    status TEXT DEFAULT 'intake',
    step INTEGER DEFAULT 1,
    intake_json TEXT DEFAULT '{}',
    outline_json TEXT DEFAULT '[]',
    sources_dir TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_INTAKE_QUESTIONS = """
## Course Builder — Intake questionnaire

To design your course well, I need answers to these questions. Answer as many as you can — leave blanks for anything you're not sure about yet.

**1. Topic and scope**
What is this course about? What is NOT in scope?

**2. Target audience**
Who will take this course? What do they already know? What level are they at?

**3. Learning objectives**
What should learners be able to DO after completing this course? (Use action verbs: "apply", "design", "critique", "implement" — not "understand" or "know")

**4. Time budget**
How many hours should the course take? How many modules? Rough session length?

**5. Pedagogy preferences**
Heavy on readings, or more exercises? Problem-based or lecture-style? Any specific assessment format?

**6. Materials you already have**
Do you have papers, slides, or notes I should harvest from? Any URLs or file paths?

**7. Constraints**
Any topics to avoid? Any required references or frameworks?

Once you've answered these, I'll show you a draft outline (Modules, Bloom levels, estimated hours) for your approval before we start building.
"""


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:60]


def _ensure_table(conn) -> None:
    conn.execute(_COURSE_DDL)


@app.tool()
async def start_course_build(
    topic: str,
    target_audience: str = "",
    duration_hours: int = 0,
    notes: str = "",
) -> list[TextContent]:
    """Start a new course build pipeline.

    Creates a course record in the course_builds table, adds a placeholder
    row to learning_courses (status='building'), and returns the intake
    questionnaire for the user to complete.

    Args:
        topic: The subject or title of the course (e.g. "Multilevel models for epidemiologists")
        target_audience: Who this course is for (e.g. "MPH students with basic R knowledge")
        duration_hours: Estimated total course length in hours (0 = TBD)
        notes: Any initial notes or constraints the user has mentioned

    Returns:
        Course ID, a brief confirmation, and the intake questionnaire.
    """
    slug = _slugify(topic)
    now_iso = datetime.datetime.now().isoformat(timespec="seconds")

    with connect(paths.db) as conn:
        _ensure_table(conn)

        # Check for existing build with same slug
        existing = conn.execute(
            "SELECT id, status FROM course_builds WHERE slug = ?", (slug,)
        ).fetchone()
        if existing:
            return [TextContent(
                type="text",
                text=(
                    f"A course build for **{topic}** already exists "
                    f"(slug: `{slug}`, status: `{existing['status']}`).\n\n"
                    f"Use `get_course_status('{slug}')` to see where it is, "
                    f"or choose a slightly different topic title to start a new build."
                ),
            )]

        intake = {
            "topic": topic,
            "target_audience": target_audience,
            "duration_hours": duration_hours,
            "notes": notes,
            "started_at": now_iso,
        }

        conn.execute(
            """
            INSERT INTO course_builds
                (slug, title, topic, target_audience, duration_hours,
                 status, step, intake_json, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'intake', 1, ?, ?, ?, ?)
            """,
            (slug, topic, topic, target_audience, duration_hours,
             json.dumps(intake), notes, now_iso, now_iso),
        )

        # Also seed a learning_courses row so it appears on the Learning tab
        existing_lc = conn.execute(
            "SELECT id FROM learning_courses WHERE slug = ?", (slug,)
        ).fetchone()
        if not existing_lc:
            conn.execute(
                """
                INSERT INTO learning_courses
                    (title, category, progress_pct, total_modules,
                     completed_modules, status, slug, created_at)
                VALUES (?, 'building', 0, 0, 0, 'building', ?, ?)
                """,
                (topic, slug, now_iso),
            )

        conn.commit()

    return [TextContent(
        type="text",
        text=(
            f"Course build started: **{topic}**\n"
            f"Slug: `{slug}` · Status: intake · Step 1/7\n\n"
            f"{_INTAKE_QUESTIONS}"
        ),
    )]


@app.tool()
async def save_course_outline(
    slug: str,
    outline_json: str,
    approved: bool = False,
) -> list[TextContent]:
    """Save an approved course outline after Step 2 (Scope Plan).

    Call this once the user has reviewed and approved the module outline.
    Pass outline_json as a JSON array of module objects:
      [{"module": 1, "title": "...", "bloom_level": "...", "hours": 2}, ...]

    Args:
        slug: The course slug returned by start_course_build()
        outline_json: JSON array of module definitions
        approved: Must be True to advance the build to Step 3 (Harvest)

    Returns:
        Confirmation and next-step instructions.
    """
    if not approved:
        return [TextContent(
            type="text",
            text="Outline not saved — set `approved=True` to confirm the outline and advance to Step 3 (Harvest).",
        )]

    try:
        modules = json.loads(outline_json)
        if not isinstance(modules, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        return [TextContent(type="text", text=f"Invalid outline JSON: {exc}")]

    now_iso = datetime.datetime.now().isoformat(timespec="seconds")

    with connect(paths.db) as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT id FROM course_builds WHERE slug = ?", (slug,)
        ).fetchone()
        if not row:
            return [TextContent(type="text", text=f"Course `{slug}` not found.")]

        conn.execute(
            """
            UPDATE course_builds
               SET outline_json = ?,
                   status = 'harvest',
                   step = 3,
                   updated_at = ?
             WHERE slug = ?
            """,
            (json.dumps(modules), now_iso, slug),
        )
        conn.execute(
            "UPDATE learning_courses SET total_modules = ?, updated_at = ? WHERE slug = ?",
            (len(modules), now_iso, slug),
        )
        conn.commit()

    # Create sources directory scaffold
    courses_root = paths.root / "knowledge" / "courses" / slug
    sources_dir = courses_root / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    (courses_root / "course.json").write_text(
        json.dumps({"slug": slug, "modules": modules}, indent=2),
        encoding="utf-8",
    )

    return [TextContent(
        type="text",
        text=(
            f"Outline saved for **{slug}** · {len(modules)} modules · Status: harvest\n\n"
            f"Sources directory created: `knowledge/courses/{slug}/sources/`\n\n"
            f"**Step 3 — Harvest**: Delegate to Content Harvester to source materials. "
            f"Point it at each module title and ask it to populate `knowledge/courses/{slug}/sources/`."
        ),
    )]


@app.tool()
async def get_course_status(slug: str = "") -> list[TextContent]:
    """Return the current status of a course build (or all active builds).

    Args:
        slug: Course slug. Leave empty to list all active builds.

    Returns:
        Status summary including current step, modules, and next action.
    """
    STEP_LABELS = {
        1: "Intake",
        2: "Scope plan",
        3: "Harvest",
        4: "Curriculum design",
        5: "Draft",
        6: "Review",
        7: "Publish",
    }

    with connect(paths.db) as conn:
        _ensure_table(conn)

        if slug:
            rows = conn.execute(
                "SELECT * FROM course_builds WHERE slug = ?", (slug,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM course_builds WHERE status NOT IN ('published', 'cancelled') "
                "ORDER BY updated_at DESC LIMIT 10"
            ).fetchall()

    if not rows:
        msg = f"No active course build found for `{slug}`." if slug else "No active course builds."
        return [TextContent(type="text", text=msg)]

    lines = []
    for r in rows:
        r = dict(r)
        step = r.get("step", 1)
        step_label = STEP_LABELS.get(step, f"Step {step}")
        outline = json.loads(r.get("outline_json") or "[]")
        lines += [
            f"### {r['title']}",
            f"Slug: `{r['slug']}` · Step {step}/7: **{step_label}** · Status: `{r['status']}`",
            f"Modules defined: {len(outline)} · Duration: {r.get('duration_hours') or 'TBD'}h",
            f"Started: {r.get('created_at', '')[:10]} · Updated: {r.get('updated_at', '')[:10]}",
            "",
        ]
        if r.get("notes"):
            lines.append(f"Notes: {r['notes']}")

    return [TextContent(type="text", text="\n".join(lines))]


@app.tool()
async def publish_course(slug: str) -> list[TextContent]:
    """Finalise and publish a completed course build.

    Marks the learning_courses row as 'active', sets progress to 0,
    and writes a completion note. Call after all 7 steps are done.

    Args:
        slug: The course slug to publish.

    Returns:
        Confirmation with the course path and Learning tab link.
    """
    now_iso = datetime.datetime.now().isoformat(timespec="seconds")

    with connect(paths.db) as conn:
        _ensure_table(conn)

        row = conn.execute(
            "SELECT title, outline_json FROM course_builds WHERE slug = ?", (slug,)
        ).fetchone()
        if not row:
            return [TextContent(type="text", text=f"Course `{slug}` not found.")]

        row = dict(row)
        modules = json.loads(row.get("outline_json") or "[]")

        conn.execute(
            """
            UPDATE course_builds
               SET status = 'published', step = 7, updated_at = ?
             WHERE slug = ?
            """,
            (now_iso, slug),
        )
        conn.execute(
            """
            UPDATE learning_courses
               SET status = 'active', progress_pct = 0,
                   total_modules = ?, updated_at = ?
             WHERE slug = ?
            """,
            (len(modules), now_iso, slug),
        )
        conn.commit()

    return [TextContent(
        type="text",
        text=(
            f"Course **{row['title']}** published.\n"
            f"Slug: `{slug}` · {len(modules)} modules\n"
            f"Path: `knowledge/courses/{slug}/`\n\n"
            f"It now appears on the Learning tab. "
            f"Spaced repetition scheduling: open the course and use the practice buttons."
        ),
    )]
