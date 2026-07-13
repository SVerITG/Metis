#!/usr/bin/env python3
"""
Export Metis knowledge to markdown files for Graphify ingestion.

Creates a `graphify-knowledge/` directory at the repo root with richly
cross-referenced markdown files (YAML front-matter + body) so Graphify
can build a unified knowledge graph linking literature, ideas, projects,
tasks, meetings, concepts, sessions, and journal entries.

Usage:
    python3 tools/export_knowledge_graph.py          # full export
    python3 tools/export_knowledge_graph.py --quick   # skip sessions/memory (faster)
"""

import json
import os
import re
import sqlite3
import sys
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path.home() / ".local/share/metis/metis.sqlite"
OUT_DIR = REPO_ROOT / "graphify-knowledge"

QUICK_MODE = "--quick" in sys.argv


def slugify(text, max_len: int = 60) -> str:
    """Turn text into a filesystem-safe slug."""
    if not text:
        return "untitled"
    s = str(text).lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:max_len] or "untitled"


def yaml_str(val) -> str:
    """Escape a value for YAML front-matter."""
    if val is None:
        return '""'
    s = str(val).replace('"', '\\"')
    if any(c in s for c in ":#{}[]&*?|>!%@`,\n"):
        return f'"{s}"'
    return f'"{s}"'


def write_md(subdir: str, filename: str, frontmatter: dict, body: str):
    """Write a markdown file with YAML front-matter."""
    d = OUT_DIR / subdir
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{filename}.md"

    lines = ["---"]
    for k, v in frontmatter.items():
        if isinstance(v, list):
            if v:
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {yaml_str(item)}")
            else:
                lines.append(f"{k}: []")
        else:
            lines.append(f"{k}: {yaml_str(v)}")
    lines.append("---")
    lines.append("")
    lines.append(body.strip())
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def connect():
    """Connect to the Metis SQLite database."""
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}")
        sys.exit(1)
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    return db


def parse_tags(raw) -> list:
    """Parse comma/semicolon-separated tags or JSON array."""
    if not raw:
        return []
    raw = str(raw).strip()
    if raw.startswith("["):
        try:
            return [str(t).strip() for t in json.loads(raw) if t]
        except json.JSONDecodeError:
            pass
    return [t.strip() for t in re.split(r"[,;]+", raw) if t.strip()]


# ── Exporters ────────────────────────────────────────────────────────────

def export_literature(db):
    """Export literature_metadata → papers/."""
    rows = db.execute(
        "SELECT * FROM literature_metadata ORDER BY year DESC, title"
    ).fetchall()
    print(f"  Literature: {len(rows)} papers")
    for r in rows:
        slug = slugify(r["title"])
        fid = f"{r['year'] or 'nd'}-{slug}"
        tags = parse_tags(r["tags"])
        collections = parse_tags(r["collection"])

        fm = {
            "type": "paper",
            "title": r["title"],
            "authors": r["authors"] or "",
            "year": r["year"] or "",
            "journal": r["journal"] or "",
            "item_type": r["item_type"] or "journalArticle",
            "doi": r["doi"] or "",
            "library_source": r["library_source"] or "manual",
            "tags": tags,
            "collections": collections,
            "metis_id": r["id"],
        }

        body_parts = [f"# {r['title']}\n"]
        if r["authors"]:
            body_parts.append(f"**Authors:** {r['authors']}\n")
        if r["journal"]:
            body_parts.append(f"**Journal:** {r['journal']} ({r['year'] or '?'})\n")
        if r["doi"]:
            body_parts.append(f"**DOI:** {r['doi']}\n")
        if r["abstract"]:
            body_parts.append(f"\n## Abstract\n\n{r['abstract']}\n")
        if tags:
            body_parts.append(f"\n**Tags:** {', '.join(tags)}\n")
        if collections:
            body_parts.append(f"**Collections:** {', '.join(collections)}\n")

        write_md("papers", fid, fm, "\n".join(body_parts))


def export_library_cards(db):
    """Export library_cards → library-cards/."""
    rows = db.execute("SELECT * FROM library_cards ORDER BY created_at DESC").fetchall()
    print(f"  Library cards: {len(rows)} cards")
    for r in rows:
        slug = slugify(r["title"] or f"card-{r['id']}")
        fm = {
            "type": "library-card",
            "title": r["title"] or "",
            "domain": r["domain"] or "",
            "authors": r["authors"] or "",
            "year": r["year"] or "",
            "status": r["status"] or "unread",
            "tags": parse_tags(r["tags"]),
            "source_path": r["source_path"] or "",
            "metis_id": r["id"],
        }
        body_parts = [f"# {r['title']}\n"]
        if r["domain"]:
            body_parts.append(f"**Domain:** {r['domain']}\n")
        if r["summary"]:
            body_parts.append(f"\n{r['summary']}\n")
        write_md("library-cards", slug, fm, "\n".join(body_parts))


def export_projects(db):
    """Export projects → projects/."""
    rows = db.execute("SELECT * FROM projects ORDER BY display_order, title").fetchall()
    print(f"  Projects: {len(rows)} projects")
    for r in rows:
        slug = slugify(r["project_id"])
        tags = parse_tags(r["tags"])
        fm = {
            "type": "project",
            "project_id": r["project_id"],
            "title": r["title"] or r["project_id"],
            "domain": r["domain"] or "",
            "status": r["status"] or "",
            "priority": r["priority"] or "",
            "project_type": r["project_type"] or "research",
            "category": r["category"] or "",
            "tags": tags,
            "github_url": r["github_url"] or "",
        }
        body_parts = [f"# {r['title'] or r['project_id']}\n"]
        if r["description"]:
            body_parts.append(f"{r['description']}\n")
        if r["next_step"]:
            body_parts.append(f"\n## Next Step\n\n{r['next_step']}\n")
        if r["notes"]:
            body_parts.append(f"\n## Notes\n\n{r['notes']}\n")

        # Link tasks to this project
        tasks = db.execute(
            "SELECT title, status FROM tasks WHERE project_id = ? ORDER BY display_order",
            (r["project_id"],),
        ).fetchall()
        if tasks:
            body_parts.append("\n## Tasks\n")
            for t in tasks:
                check = "x" if t["status"] == "done" else " "
                body_parts.append(f"- [{check}] {t['title']} ({t['status']})")

        # Link ideas to this project
        ideas = db.execute(
            "SELECT text, idea_type FROM ideas WHERE project_id = ?",
            (r["project_id"],),
        ).fetchall()
        if ideas:
            body_parts.append("\n\n## Linked Ideas\n")
            for idea in ideas:
                body_parts.append(f"- **{idea['idea_type'] or 'idea'}:** {idea['text']}")

        write_md("projects", slug, fm, "\n".join(body_parts))


def export_ideas(db):
    """Export ideas → ideas/."""
    rows = db.execute("SELECT * FROM ideas ORDER BY created_at DESC").fetchall()
    print(f"  Ideas: {len(rows)} ideas")
    for r in rows:
        slug = slugify(r["text"][:60] if r["text"] else r["idea_id"])
        fm = {
            "type": "idea",
            "idea_id": r["idea_id"],
            "idea_type": r["idea_type"] or "",
            "domain": r["domain"] or "",
            "project_id": r["project_id"] or "",
            "feasibility": r["feasibility"] or "",
            "novelty": r["novelty_status"] or "",
            "phd_relevance": r["phd_relevance"] or "",
            "tags": parse_tags(r["tags"]),
            "linked_papers": parse_tags(r["linked_papers"]),
            "created_at": r["created_at"] or "",
        }
        body = f"# Idea: {r['text']}\n"
        if r["project_id"]:
            body += f"\n**Project:** {r['project_id']}\n"
        if r["feasibility"]:
            body += f"**Feasibility:** {r['feasibility']}\n"
        if r["novelty_status"]:
            body += f"**Novelty:** {r['novelty_status']}\n"
        write_md("ideas", slug, fm, body)


def export_tasks(db):
    """Export tasks → tasks/."""
    rows = db.execute(
        "SELECT t.*, p.title as project_title FROM tasks t "
        "LEFT JOIN projects p ON t.project_id = p.project_id "
        "ORDER BY t.project_id, t.display_order"
    ).fetchall()
    print(f"  Tasks: {len(rows)} tasks")
    for r in rows:
        slug = slugify(r["title"] or r["task_id"])
        fm = {
            "type": "task",
            "task_id": r["task_id"],
            "project_id": r["project_id"] or "",
            "project_title": r["project_title"] or "",
            "status": r["status"] or "",
            "category": r["category"] or "",
            "due_date": r["due_date"] or "",
            "starred": bool(r["starred"]),
            "created_at": r["created_at"] or "",
        }
        body = f"# {r['title']}\n"
        if r["project_title"]:
            body += f"\n**Project:** {r['project_title']}\n"
        if r["status"]:
            body += f"**Status:** {r['status']}\n"
        if r["notes"]:
            body += f"\n{r['notes']}\n"
        write_md("tasks", slug, fm, body)


def export_meetings(db):
    """Export meetings → meetings/."""
    rows = db.execute("SELECT * FROM meetings ORDER BY meeting_date DESC").fetchall()
    print(f"  Meetings: {len(rows)} meetings")
    for r in rows:
        slug = slugify(r["title"] or r["meeting_id"])
        date = r["meeting_date"] or ""
        fm = {
            "type": "meeting",
            "meeting_id": r["meeting_id"],
            "date": date,
            "domain": r["domain"] or "",
            "project": r["project"] or "",
            "meeting_type": r["meeting_type"] or "",
            "attendees": parse_tags(r["attendees"]),
            "status": r["status"] or "",
        }
        body_parts = [f"# {r['title']}\n"]
        if date:
            body_parts.append(f"**Date:** {date}\n")
        if r["attendees"]:
            body_parts.append(f"**Attendees:** {r['attendees']}\n")
        if r["decisions"]:
            body_parts.append(f"\n## Decisions\n\n{r['decisions']}\n")
        if r["action_items"]:
            body_parts.append(f"\n## Action Items\n\n{r['action_items']}\n")
        if r["follow_ups"]:
            body_parts.append(f"\n## Follow-ups\n\n{r['follow_ups']}\n")
        if r["transcript"]:
            # Truncate very long transcripts
            transcript = r["transcript"][:3000]
            body_parts.append(f"\n## Transcript (excerpt)\n\n{transcript}\n")
        write_md("meetings", f"{date}-{slug}" if date else slug, fm, "\n".join(body_parts))


def export_concepts(db):
    """Export semantic_memory → concepts/."""
    rows = db.execute("SELECT * FROM semantic_memory ORDER BY concept").fetchall()
    print(f"  Concepts: {len(rows)} semantic memory entries")
    for r in rows:
        slug = slugify(r["concept"])
        related = parse_tags(r["related_concepts"])
        fm = {
            "type": "concept",
            "concept": r["concept"],
            "source_type": r["source_type"] or "",
            "project_id": r["project_id"] or "",
            "agent_id": r["agent_id"] or "",
            "scope": r["scope"] or "global",
            "related_concepts": related,
            "created_at": r["created_at"] or "",
        }
        body = f"# {r['concept']}\n\n{r['definition']}\n"
        if related:
            body += f"\n**Related:** {', '.join(related)}\n"
        write_md("concepts", slug, fm, body)


def export_journal(db):
    """Export journal_entries → journal-entries/."""
    rows = db.execute("SELECT * FROM journal_entries ORDER BY created_at DESC").fetchall()
    print(f"  Journal: {len(rows)} entries")
    for r in rows:
        date = (r["created_at"] or "")[:10]
        slug = slugify(r["summary"] or r["entry_id"])
        fm = {
            "type": "journal-entry",
            "entry_id": r["entry_id"],
            "date": date,
            "mood": r["mood"] or "",
            "tags": parse_tags(r["tags"]),
        }
        body_parts = [f"# Journal — {date}\n"]
        if r["mood"]:
            body_parts.append(f"**Mood:** {r['mood']}\n")
        if r["summary"]:
            body_parts.append(f"**Summary:** {r['summary']}\n")
        body_parts.append(f"\n{r['content']}\n")
        write_md("journal-entries", f"{date}-{slug}", fm, "\n".join(body_parts))


def export_sessions(db, limit=150):
    """Export recent session_summaries → sessions/."""
    rows = db.execute(
        "SELECT * FROM session_summaries ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    print(f"  Sessions: {len(rows)} recent summaries (of total in DB)")
    for r in rows:
        date = (r["created_at"] or "")[:10]
        sid = (r["session_id"] or "")[:12]
        topics = parse_tags(r["key_topics"])
        decisions = parse_tags(r["decisions"])
        fm = {
            "type": "session",
            "session_id": r["session_id"] or "",
            "date": date,
            "topics": topics,
            "decisions": decisions,
        }
        summary_text = r["summary"] or ""
        first_line = summary_text.split(".")[0][:50] if summary_text else sid
        body = f"# Session — {date}\n\n{summary_text}\n"
        if topics:
            body += f"\n**Topics:** {', '.join(topics)}\n"
        if decisions:
            body += f"\n**Decisions:** {'; '.join(decisions)}\n"
        write_md("sessions", f"{date}-{slugify(first_line)}-{sid}", fm, body)


def export_episodic_highlights(db, limit=200):
    """Export episodic_memory decision/insight events → memory-events/."""
    rows = db.execute(
        "SELECT * FROM episodic_memory "
        "WHERE event_type IN ('decision', 'insight', 'milestone', 'connection', 'discovery') "
        "ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    print(f"  Episodic highlights: {len(rows)} decision/insight/milestone events")
    for i, r in enumerate(rows):
        date = (r["created_at"] or "")[:10]
        etype = r["event_type"] or "event"
        meta = {}
        try:
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
        except (json.JSONDecodeError, TypeError):
            pass
        fm = {
            "type": f"memory-{etype}",
            "event_type": etype,
            "date": date,
            "project_id": r["project_id"] or meta.get("project_id", ""),
            "agent_id": r["agent_id"] or meta.get("agent_slug", ""),
            "scope": r["scope"] or "global",
        }
        content = r["content"] or ""
        slug = slugify(content[:50]) or f"event-{i}"
        body = f"# {etype.title()} — {date}\n\n{content}\n"
        write_md("memory-events", f"{date}-{etype}-{slug}", fm, body)


def export_knowledge_links(db):
    """Export knowledge_links + note_links → _links.md index file."""
    klinks = db.execute("SELECT * FROM knowledge_links ORDER BY created_at DESC").fetchall()
    nlinks = db.execute("SELECT * FROM note_links ORDER BY created_at DESC").fetchall()
    print(f"  Knowledge links: {len(klinks)} edges")
    print(f"  Note links: {len(nlinks)} edges")

    body_parts = ["# Knowledge Graph — Explicit Links\n"]
    body_parts.append("This file records all explicit relationships captured in Metis.\n")

    if klinks:
        body_parts.append("\n## Knowledge Links\n")
        body_parts.append("| Source Type | Source ID | → | Target Type | Target ID | Label |")
        body_parts.append("|---|---|---|---|---|---|")
        for r in klinks:
            body_parts.append(
                f"| {r['source_type']} | {r['source_id']} | → | "
                f"{r['target_type']} | {r['target_id']} | {r['link_label']} |"
            )

    if nlinks:
        body_parts.append("\n\n## Note Links\n")
        body_parts.append("| Source | → | Target | Type |")
        body_parts.append("|---|---|---|---|")
        for r in nlinks:
            body_parts.append(
                f"| {r['source_title'] or r['source_path']} | → | "
                f"{r['target_title'] or r['target_path']} | {r['link_type']} |"
            )

    fm = {"type": "link-index", "knowledge_links": len(klinks), "note_links": len(nlinks)}
    write_md(".", "_links", fm, "\n".join(body_parts))


def export_library_seeded(db):
    """Export library_seeded classified files → library-corpus/."""
    rows = db.execute(
        "SELECT * FROM library_seeded ORDER BY top_folder, basename"
    ).fetchall()
    print(f"  Library corpus: {len(rows)} classified files")

    # Group by top_folder for a directory-style index
    folders = {}
    for r in rows:
        folder = r["top_folder"] or "uncategorized"
        folders.setdefault(folder, []).append(r)

    for folder, items in folders.items():
        fm = {
            "type": "library-corpus-index",
            "folder": folder,
            "file_count": len(items),
            "diseases": list({r["disease"] for r in items if r["disease"]}),
            "methods": list({r["method"] for r in items if r["method"]}),
            "geographies": list({r["geography"] for r in items if r["geography"]}),
        }
        body_parts = [f"# Library Corpus: {folder}\n"]
        body_parts.append(f"**{len(items)} files** in this collection.\n")
        for r in items:
            labels = []
            if r["disease"]:
                labels.append(f"disease:{r['disease']}")
            if r["method"]:
                labels.append(f"method:{r['method']}")
            if r["geography"]:
                labels.append(f"geo:{r['geography']}")
            if r["project_link"]:
                labels.append(f"project:{r['project_link']}")
            tag_str = f" — {', '.join(labels)}" if labels else ""
            status = f" [{r['status']}]" if r["status"] else ""
            body_parts.append(f"- **{r['basename']}**{status}{tag_str}")
            if r["relevance_note"]:
                body_parts.append(f"  _{r['relevance_note']}_")

        write_md("library-corpus", slugify(folder), fm, "\n".join(body_parts))


def export_summary_index(db, counts: dict):
    """Write a top-level _index.md summarizing the entire knowledge export."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    fm = {
        "type": "knowledge-graph-index",
        "generated_at": now,
        "total_files": sum(counts.values()),
    }
    body_parts = [
        f"# Metis Knowledge Graph Export\n",
        f"Generated: {now}\n",
        "\n## Content Summary\n",
    ]
    for category, count in sorted(counts.items()):
        body_parts.append(f"- **{category}:** {count} files")

    body_parts.append("\n\n## How to Use\n")
    body_parts.append(
        "This directory is designed to be ingested by Graphify alongside the\n"
        "Metis codebase. Each markdown file has YAML front-matter with explicit\n"
        "cross-references (project_id, tags, linked_papers, related_concepts)\n"
        "that Graphify's semantic extraction will turn into graph edges.\n"
    )
    body_parts.append("\n## Entity Types\n")
    body_parts.append("- `paper` — Literature from Zotero and manual imports")
    body_parts.append("- `library-card` — Curated knowledge summaries")
    body_parts.append("- `project` — Research projects with linked tasks and ideas")
    body_parts.append("- `idea` — Research ideas with feasibility and novelty scores")
    body_parts.append("- `task` — Project tasks with status tracking")
    body_parts.append("- `meeting` — Meeting notes with decisions and action items")
    body_parts.append("- `concept` — Semantic memory entries (named concepts)")
    body_parts.append("- `journal-entry` — Personal journal with mood and reflections")
    body_parts.append("- `session` — Work session summaries with decisions")
    body_parts.append("- `memory-*` — Episodic memory highlights (decisions, insights)")
    body_parts.append("- `library-corpus-index` — Classified PDF collections")
    body_parts.append("- `link-index` — Explicit cross-entity relationships")

    write_md(".", "_index", fm, "\n".join(body_parts))


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    print(f"Metis Knowledge Graph Export")
    print(f"{'─' * 45}")
    print(f"Database: {DB_PATH}")
    print(f"Output:   {OUT_DIR}")
    print(f"Mode:     {'quick (skip sessions/memory)' if QUICK_MODE else 'full'}")
    print()

    # Clean previous export
    if OUT_DIR.exists():
        import shutil
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    db = connect()
    counts = {}

    # Core knowledge
    export_literature(db)
    counts["papers"] = db.execute("SELECT COUNT(*) FROM literature_metadata").fetchone()[0]

    export_library_cards(db)
    counts["library-cards"] = db.execute("SELECT COUNT(*) FROM library_cards").fetchone()[0]

    export_projects(db)
    counts["projects"] = db.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

    export_ideas(db)
    counts["ideas"] = db.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]

    export_tasks(db)
    counts["tasks"] = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    export_meetings(db)
    counts["meetings"] = db.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]

    export_concepts(db)
    counts["concepts"] = db.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]

    export_journal(db)
    counts["journal-entries"] = db.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]

    # Corpus classification
    export_library_seeded(db)
    counts["library-corpus"] = len(
        {r[0] for r in db.execute("SELECT DISTINCT top_folder FROM library_seeded").fetchall()}
    )

    # Links index
    export_knowledge_links(db)
    counts["link-index"] = 1

    if not QUICK_MODE:
        export_sessions(db, limit=150)
        counts["sessions"] = 150

        export_episodic_highlights(db, limit=200)
        counts["memory-events"] = min(
            200,
            db.execute(
                "SELECT COUNT(*) FROM episodic_memory "
                "WHERE event_type IN ('decision','insight','milestone','connection','discovery')"
            ).fetchone()[0],
        )

    # Top-level index
    export_summary_index(db, counts)

    db.close()

    # Count files written
    total_files = sum(1 for _ in OUT_DIR.rglob("*.md"))
    print(f"\n{'─' * 45}")
    print(f"✓ Exported {total_files} markdown files to {OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"\nNext steps:")
    print(f"  1. Update .graphifyignore to include graphify-knowledge/")
    print(f"  2. Run: graphify update .")
    print(f"  3. Query: graphify query 'sleeping sickness literature'")


if __name__ == "__main__":
    main()
