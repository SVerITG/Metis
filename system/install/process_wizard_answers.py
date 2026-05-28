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
        val = answers.get(key, "").strip()
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


def _parse_projects_text(text: str) -> list:
    projects = []
    for line in text.strip().split("\n"):
        name = line.strip().lstrip("-•*123456789. ").strip()
        if name:
            projects.append({
                "name": name, "status": "active",
                "question": "", "tools": "", "next": "",
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


def write_project_stubs(metis_root: Path, projects: list) -> list:
    if not projects:
        return []
    projects_dir = metis_root / "projects" / "active"
    projects_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for p in projects:
        name = p.get("name", "").strip()
        if not name:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
        path = projects_dir / f"{slug}.md"
        if path.exists():
            continue
        content = (
            f"# {name}\n\n"
            f"**Status:** {p.get('status', 'active')}  \n"
            f"**Created:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
            "## Research question\n"
            f"{p.get('question', '')}\n\n"
            "## Tools & methods\n"
            f"{p.get('tools', '')}\n\n"
            "## Next step\n"
            f"{p.get('next', '')}\n\n"
            "## Notes\n\n"
            "## Planning\n"
        )
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


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

    result["persona_path"] = str(write_persona(metis_root, persona, answers))
    result["config_path"] = str(write_user_config(metis_root, answers, topics))
    result["projects"] = [str(p) for p in write_project_stubs(metis_root, projects)]
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
