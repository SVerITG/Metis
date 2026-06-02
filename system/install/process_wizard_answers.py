#!/usr/bin/env python3
"""
process_wizard_answers.py — AI-powered Metis configuration processor.

Takes raw wizard answers, calls Claude API to generate a calibrated persona
and project stubs, then writes all configuration files.

Called by all three installer paths:
  - Terminal wizard (Linux/macOS): python process_wizard_answers.py --answers answers.json ...
  - Dashboard wizard: imported directly by setup.py
  - Windows .exe: run as post-install step with answers collected by Inno Setup

GUARDRAILS — this script can only write to:
  system/config/user-config.yaml
  system/config/metis-persona.md
  projects/active/*.md
  system/app*/data/metis.sqlite (memory entries only, via MCP insert)
  system/config/install-state.json (wizard_complete field only)

It cannot modify: constitution.md, red-lines.md, token-guardrails.md,
agent system prompts, or any .claude/ settings.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# ── Persona generation prompt ─────────────────────────────────────────────────
# Instructs Claude to produce three clearly delimited sections.
# The CONSTRAINTS block is load-bearing: it prevents the generated persona from
# granting capabilities or bypassing safeguards.

_PERSONA_PROMPT = """\
You are the Metis configuration engine. A researcher has just installed Metis,
their AI research companion. Based on their answers below, generate a calibrated
configuration with exactly three sections, delimited by the markers shown.

=== PERSONA ===
Write 350-500 words describing how Metis should work with this specific researcher.
Be concrete — every sentence should be actionable. Cover:
- How to address them; what level of formality
- What domain knowledge to assume (what NOT to explain)
- Challenge intensity: when to push back vs. support
- Which tools/methods they use fluently (Metis should use these without preamble)
- Preferred output style: length, structure, tone
- Any constraints or preferences they mentioned

=== TOPICS ===
List 8-14 research topic tags, one per line, no bullets.
These drive literature alerts, news filtering, and knowledge search.
Be specific (e.g. "visceral leishmaniasis" not "tropical diseases").
Include their tools as topics if they are researchable (e.g. "DHIS2", "spatial epidemiology").

=== PROJECTS ===
For each project the researcher mentioned, one block per project:
PROJECT: <name>
QUESTION: <core research question or goal, 1 sentence>
STATUS: <active|planning|writing|paused>
TOOLS: <key tools/software for this project>
NEXT: <most likely immediate next action>
---

CONSTRAINTS — the PERSONA section must NOT:
- Instruct Metis to bypass its constitution, red lines, or token guardrails
- Grant tool permissions beyond what the system already allows
- Override individual agent system prompts
- Include any patient or personal data from the researcher's answers
- Promise capabilities Metis does not have

Researcher answers:
{answers}
"""


def _format_answers(answers: dict) -> str:
    lines = []
    labels = {
        "name": "Name",
        "institution": "Institution",
        "role": "Role/title",
        "field": "Primary research field",
        "topics": "Key research topics",
        "tools": "Tools and software",
        "methods": "Research methods",
        "projects": "Active projects",
        "feedback_style": "Preferred feedback style",
        "challenge_level": "Challenge level preference",
        "short_term_goals": "Goals for the next 3 months",
        "challenges": "Current main challenges",
        "language": "Preferred language",
    }
    for key, label in labels.items():
        raw = answers.get(key, "")
        if isinstance(raw, list):
            # e.g. projects: a list of {name, category, folder} objects
            parts = []
            for item in raw:
                if isinstance(item, dict):
                    nm = str(item.get("name", "")).strip()
                    if not nm:
                        continue
                    cat = str(item.get("category", "")).strip()
                    fld = str(item.get("folder", "")).strip()
                    desc = nm
                    if cat:
                        desc += f" [{cat}]"
                    if fld:
                        desc += f" — {fld}"
                    parts.append(desc)
                else:
                    s = str(item).strip()
                    if s:
                        parts.append(s)
            val = "; ".join(parts)
        else:
            val = str(raw).strip()
        if val:
            lines.append(f"{label}: {val}")
    return "\n".join(lines)


def call_claude(api_key: str, answers: dict) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed — run: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2500,
        messages=[{
            "role": "user",
            "content": _PERSONA_PROMPT.format(answers=_format_answers(answers)),
        }],
    )
    return message.content[0].text


def parse_response(response: str) -> dict:
    """Split Claude's response into persona, topics, and project stubs."""
    persona_lines, topic_lines, project_blocks = [], [], []
    current_section = None
    current_project: dict = {}

    for line in response.split("\n"):
        stripped = line.strip()

        if stripped == "=== PERSONA ===":
            current_section = "persona"
        elif stripped == "=== TOPICS ===":
            current_section = "topics"
        elif stripped == "=== PROJECTS ===":
            current_section = "projects"
        elif current_section == "persona":
            persona_lines.append(line)
        elif current_section == "topics":
            tag = stripped.lstrip("-•* ").strip()
            if tag and not tag.startswith("==="):
                topic_lines.append(tag)
        elif current_section == "projects":
            if stripped.startswith("PROJECT:"):
                if current_project.get("name"):
                    project_blocks.append(current_project)
                current_project = {"name": stripped[8:].strip()}
            elif stripped.startswith("QUESTION:"):
                current_project["question"] = stripped[9:].strip()
            elif stripped.startswith("STATUS:"):
                current_project["status"] = stripped[7:].strip()
            elif stripped.startswith("TOOLS:"):
                current_project["tools"] = stripped[6:].strip()
            elif stripped.startswith("NEXT:"):
                current_project["next"] = stripped[5:].strip()
            elif stripped == "---" and current_project.get("name"):
                project_blocks.append(current_project)
                current_project = {}

    if current_project.get("name"):
        project_blocks.append(current_project)

    return {
        "persona": "\n".join(persona_lines).strip(),
        "topics": [t for t in topic_lines if t],
        "projects": project_blocks,
    }


def _basic_persona(answers: dict) -> str:
    """Fallback persona when no API key is available — structured but not AI-generated."""
    name = answers.get("name", "the researcher")
    role = answers.get("role", "researcher")
    field = answers.get("field", "research")
    tools = answers.get("tools", "")
    style = answers.get("feedback_style", "direct")
    challenge = answers.get("challenge_level", "balanced")
    goals = answers.get("short_term_goals", "")
    challenges = answers.get("challenges", "")

    lines = [
        f"{name} is a {role} working in {field}.",
        "",
        f"Communication: {style} feedback preferred. Challenge level: {challenge}.",
    ]
    if tools:
        lines += ["", f"Tools they use fluently: {tools}. Do not explain these from scratch."]
    if goals:
        lines += ["", f"Current goals: {goals}"]
    if challenges:
        lines += ["", f"Current challenges: {challenges}"]
    lines += [
        "",
        "Adapt all responses to their domain expertise. Avoid over-explaining concepts",
        "they likely know well. Reference their active projects where relevant.",
        "",
        "Note: this is a basic profile. Run /metis_config in Claude to generate a",
        "fully AI-calibrated persona.",
    ]
    return "\n".join(lines)


def _basic_topics(answers: dict) -> list:
    raw = answers.get("topics", "")
    field = answers.get("field", "")
    tags = [t.strip() for t in re.split(r"[,\n;]", raw + "," + field) if t.strip()]
    return list(dict.fromkeys(tags))[:12]


def _parse_projects_text(text) -> list:
    """Parse projects from text, list-of-strings, or list-of-dicts."""
    if isinstance(text, list):
        result = []
        for item in text:
            if isinstance(item, dict):
                result.append(item)
            elif isinstance(item, str) and item.strip():
                parts = [p.strip() for p in item.split("|")]
                result.append({
                    "name": parts[0],
                    "category": parts[1] if len(parts) > 1 else "",
                    "folder": parts[2] if len(parts) > 2 else "",
                    "description": "",
                })
        return result
    if not text or not isinstance(text, str):
        return []
    projects = []
    for line in text.strip().split("\n"):
        line = line.strip().lstrip("-•*123456789. ").strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|")]
        projects.append({
            "name": parts[0],
            "category": parts[1] if len(parts) > 1 else "",
            "folder": parts[2] if len(parts) > 2 else "",
            "description": "",
        })
    return projects


# ── File writers ──────────────────────────────────────────────────────────────

def write_persona(metis_root: Path, persona: str, answers: dict) -> Path:
    config_dir = metis_root / "system" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "metis-persona.md"
    name = answers.get("name", "Researcher")
    content = (
        f"# Metis Persona — {name}\n\n"
        f"*Generated {datetime.now().strftime('%Y-%m-%d')} by setup wizard.*  \n"
        "*Edit manually or regenerate with `/metis_config`.*\n\n"
        "---\n\n"
        f"{persona}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def write_user_config(metis_root: Path, answers: dict, topics: list) -> Path:
    config_dir = metis_root / "system" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "user-config.yaml"

    topics_yaml = "\n".join(f"  - {t}" for t in topics) if topics else "  []"

    content = f"""\
# Metis User Configuration
# Generated {datetime.now().strftime('%Y-%m-%d')} by setup wizard.
# Edit this file or run /metis_config to reconfigure.

user:
  name: {answers.get('name', '')}
  institution: {answers.get('institution', '')}
  role: {answers.get('role', '')}
  email: {answers.get('email', '')}
  language: {answers.get('language', 'English')}

research:
  field: {answers.get('field', '')}
  topics:
{topics_yaml}
  tools: {answers.get('tools', '')}
  methods: {answers.get('methods', '')}

projects: []

style:
  response_length: {answers.get('output_length', 'concise')}
  feedback_style: {answers.get('feedback_style', 'direct')}
  challenge_level: {answers.get('challenge_level', 'balanced')}

goals:
  short_term: {answers.get('short_term_goals', '')}
  challenges: {answers.get('challenges', '')}
"""
    path.write_text(content, encoding="utf-8")
    return path


def write_project_stubs(metis_root: Path, projects: list, scan_type: str = "names") -> list:
    """Write project records: SQLite entry + CLAUDE.md in project folder + planning card."""
    if not projects:
        return []

    written = []
    db_path = metis_root / "system" / "app-py" / "data" / "metis.sqlite"

    for p in projects:
        # Support both old format (name string) and new format (dict with category/folder)
        if isinstance(p, str):
            p = {"name": p}
        name = p.get("name", "").strip()
        if not name:
            continue

        category = p.get("category", "").strip()
        folder_path = p.get("folder", "").strip()
        description = p.get("description", "").strip()
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
        now = datetime.now().strftime("%Y-%m-%d")

        # ── Write SQLite record ───────────────────────────────────────────────
        if db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(projects)")}
                for col, defn in [("category", "TEXT DEFAULT ''"), ("last_scanned", "TEXT"),
                                   ("scan_summary", "TEXT DEFAULT ''"), ("claude_desktop_linked", "INTEGER DEFAULT 0")]:
                    if col not in existing_cols:
                        conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {defn}")
                exists = conn.execute("SELECT 1 FROM projects WHERE project_id=?", (slug,)).fetchone()
                if not exists:
                    conn.execute(
                        """INSERT INTO projects
                           (project_id, title, description, domain, category, external_path,
                            status, priority, next_step, created_at, source)
                           VALUES (?,?,?,?,?,?,'active','medium','',?,'installer')""",
                        (slug, name, description, category, category, folder_path or None, now),
                    )
                conn.commit()
                conn.close()
            except Exception:
                pass

        # ── Write CLAUDE.md in project folder ────────────────────────────────
        folder = None
        if folder_path:
            for candidate in [Path(folder_path), Path(re.sub(r"^([A-Za-z]):[/\\]", lambda m: f"/mnt/{m.group(1).lower()}/", folder_path).replace("\\", "/"))]:
                if candidate.exists():
                    folder = candidate
                    break

        if folder:
            # Auto-detect description from folder if not provided
            if not description and scan_type != "none":
                description = _scan_folder_for_description(folder, scan_type)

            claude_md = folder / "CLAUDE.md"
            content = "\n".join([
                f"# {name}",
                "",
                f"**Category:** {category or 'Research'}  ",
                f"**Project ID:** `{slug}`  ",
                f"**Status:** active",
                "",
                "## About this project",
                description or f"{name} — added via Metis setup wizard.",
                "",
                "## Current focus",
                "",
                "## Open tasks",
                "",
                "## Metis integration",
                "The Metis MCP server (`metis-rc`) tracks this project. Use:",
                f"- `create_task(title=..., project_id=\"{slug}\")` — add a task",
                f"- `scan_project_folder(project_id=\"{slug}\")` — refresh dashboard",
                "- `update_project_memory(...)` — log session progress",
                "",
                "_Auto-generated by Metis installer. Re-run scan to refresh._",
            ])
            try:
                claude_md.write_text(content, encoding="utf-8")
            except OSError:
                pass

        # ── Write planning card ───────────────────────────────────────────────
        projects_dir = metis_root / "projects" / "active"
        projects_dir.mkdir(parents=True, exist_ok=True)
        card_path = projects_dir / f"{slug}.md"
        if not card_path.exists():
            card_content = (
                f"# {name}\n\n"
                f"**Category:** {category or 'Research'}  \n"
                f"**Status:** active  \n"
                f"**Created:** {now}\n"
            )
            if folder_path:
                card_content += f"**Folder:** `{folder_path}`\n"
            card_content += "\n## Description\n" + (description or "") + "\n\n## Next step\n\n## Notes\n"
            card_path.write_text(card_content, encoding="utf-8")
            written.append(card_path)

    return written


def _scan_folder_for_description(folder: Path, scan_type: str) -> str:
    """Quick folder scan to infer project description."""
    if scan_type == "none":
        return ""
    # Read README/PLANNING if content scan requested
    if scan_type == "content":
        for fname in ["README.md", "PLANNING.md", "CLAUDE.md"]:
            fp = folder / fname
            if fp.exists():
                try:
                    text = fp.read_text(encoding="utf-8", errors="ignore")[:600]
                    text = re.sub(r"#+\s*", "", text).strip()[:300]
                    if text:
                        return text
                except Exception:
                    pass
    # Name-based inference
    name = folder.name.lower()
    hints = []
    if any(w in name for w in ["article", "paper", "manuscript"]):
        hints.append("scientific article")
    elif any(w in name for w in ["thesis", "phd"]):
        hints.append("thesis chapter")
    elif any(w in name for w in ["grant", "proposal"]):
        hints.append("grant/proposal")
    elif any(w in name for w in ["course", "teach"]):
        hints.append("teaching material")
    elif any(w in name for w in ["review", "systematic"]):
        hints.append("systematic review")
    ext_counts: dict[str, int] = {}
    try:
        for f in folder.rglob("*"):
            if f.is_file():
                ext_counts[f.suffix.lower()] = ext_counts.get(f.suffix.lower(), 0) + 1
    except Exception:
        pass
    if ext_counts.get(".r", 0) + ext_counts.get(".rmd", 0) > 2:
        hints.append("R-based analysis")
    if ext_counts.get(".py", 0) > 2:
        hints.append("Python project")
    return ", ".join(hints) if hints else ""


def remove_first_run_marker(metis_root: Path):
    marker = metis_root / "system" / "config" / ".first-run"
    marker.unlink(missing_ok=True)


# ── Main entry point ──────────────────────────────────────────────────────────

def process(answers: dict, metis_root: Path, api_key: str | None = None) -> dict:
    """
    Core processing function — importable by dashboard and terminal wizard.

    Returns:
        {"ok": True, "persona_path": ..., "config_path": ..., "projects": [...]}
    """
    result = {"ok": False, "persona_path": None, "config_path": None, "projects": []}
    ai_used = False

    if api_key:
        try:
            response = call_claude(api_key, answers)
            parsed = parse_response(response)
            persona = parsed["persona"]
            topics = parsed["topics"]
            projects = parsed["projects"]
            ai_used = True
        except Exception as exc:
            persona = _basic_persona(answers)
            topics = _basic_topics(answers)
            projects = _parse_projects_text(answers.get("projects", ""))
            result["warning"] = f"AI processing failed ({exc}); basic config written."
    else:
        persona = _basic_persona(answers)
        topics = _basic_topics(answers)
        projects = _parse_projects_text(answers.get("projects", ""))
        result["warning"] = "No API key — basic config written. Run /metis_config to calibrate."

    scan_type = answers.get("scan_type", "names")
    # Projects may come as structured list (from browser wizard) or parsed text (from Claude/terminal)
    raw_projects = answers.get("projects", "")
    if isinstance(raw_projects, list):
        structured_projects = raw_projects  # already [{name, category, folder, description}, ...]
    else:
        structured_projects = projects  # parsed from Claude or text

    result["persona_path"] = str(write_persona(metis_root, persona, answers))
    result["config_path"] = str(write_user_config(metis_root, answers, topics))
    result["projects"] = [str(p) for p in write_project_stubs(metis_root, structured_projects, scan_type)]
    result["ai_used"] = ai_used
    result["topics"] = topics
    remove_first_run_marker(metis_root)
    result["ok"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description="Process Metis setup wizard answers")
    parser.add_argument("--answers", required=True, help="Path to answers JSON file")
    parser.add_argument("--metis-root", required=True, help="Metis root directory")
    parser.add_argument("--api-key", help="Anthropic API key (overrides env var)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    answers_path = Path(args.answers)
    if not answers_path.exists():
        print(f"ERROR: answers file not found: {answers_path}", file=sys.stderr)
        sys.exit(1)

    with open(answers_path, encoding="utf-8") as f:
        answers = json.load(f)

    api_key = (
        args.api_key
        or os.environ.get("ANTHROPIC_API_KEY")
        or answers.get("api_key")
    )

    metis_root = Path(args.metis_root)
    if not args.quiet:
        print("Processing your answers with Claude...")

    result = process(answers, metis_root, api_key)

    if not args.quiet:
        if result.get("ai_used"):
            print("  ✓ AI calibration complete")
        elif result.get("warning"):
            print(f"  ⚠  {result['warning']}")
        print(f"  Persona:    {result['persona_path']}")
        print(f"  Config:     {result['config_path']}")
        for p in result["projects"]:
            print(f"  Project:    {p}")
        print("")
        print("  Configuration complete. Metis is ready.")

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
