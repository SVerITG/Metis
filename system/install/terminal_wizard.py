#!/usr/bin/env python3
"""
terminal_wizard.py — Interactive terminal setup wizard for Metis.

Runs at the end of setup-mcp.sh on Linux and macOS.
Collects answers, calls process_wizard_answers.py to generate configuration.

Usage (called by setup-mcp.sh):
    python3 terminal_wizard.py --metis-root /path/to/metis [--api-key sk-ant-...]
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def _banner(text: str):
    width = 66
    print()
    print("━" * width)
    print(f"  {text}")
    print("━" * width)


def _ask(prompt: str, default: str = "", required: bool = False, min_len: int = 0) -> str:
    display = f"  {prompt}"
    if default:
        display += f" [{default}]"
    display += ": "
    while True:
        try:
            val = input(display).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not val and default:
            return default
        # Reject obvious placeholder input (e.g. a single letter) for identity
        # fields — this is what produced the "jon is a k working in ntd" persona.
        if val and min_len and len(val) < min_len:
            print(f"  (please enter at least {min_len} characters — that looks like a placeholder)")
            continue
        if val or not required:
            return val
        print("  (required — please enter a value)")


def _ask_choice(prompt: str, options: list[tuple[str, str]], default: str) -> str:
    print(f"\n  {prompt}")
    for key, label in options:
        marker = "●" if key == default else "○"
        print(f"    [{key}]  {marker}  {label}")
    keys = [k for k, _ in options]
    default_key = default
    while True:
        try:
            raw = input(f"\n  Choose [{'/'.join(keys)}, Enter for {default_key}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not raw:
            return default_key
        if raw in keys:
            return raw
        print(f"  Please enter one of: {', '.join(keys)}")


def _ask_multiline(prompt: str, hint: str = "") -> str:
    print(f"\n  {prompt}")
    if hint:
        print(f"  ({hint})")
    print("  Enter one item per line. Press Enter twice when done.")
    lines = []
    while True:
        try:
            line = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line and lines:
            break
        if line:
            lines.append(line)
    return "\n".join(lines)


def _detect_name() -> str:
    """Try to detect the user's name from git config or OS."""
    import subprocess
    # Try git config first
    try:
        result = subprocess.run(
            ["git", "config", "--global", "user.name"],
            capture_output=True, text=True, timeout=3,
        )
        name = result.stdout.strip()
        if name and len(name) >= 2:
            return name
    except Exception:
        pass
    # Fall back to OS username (capitalised)
    try:
        import getpass
        uname = getpass.getuser()
        if uname and len(uname) >= 2:
            return uname.capitalize()
    except Exception:
        pass
    return ""


def run_wizard(metis_root: Path, api_key: str | None) -> dict:
    _banner("Welcome to Metis — let's set up your workspace")
    print()
    print("  I'll ask you a few questions to personalise Metis to your work.")
    print("  Your answers are processed by Claude and written to your local")
    print("  config files. Nothing leaves your machine.")
    print()
    print("  Takes about 3 minutes. Press Ctrl+C any time to cancel.")

    # ── Section 1: Who are you ────────────────────────────────────────────────
    _banner("1 / 4  About you")
    detected_name = _detect_name()
    name         = _ask("Your name", default=detected_name, required=True, min_len=2)
    institution  = _ask("Institution or organisation")
    role         = _ask("Your role or title", required=True, min_len=2)
    email        = _ask("Email (optional — used in outputs only)")
    language     = _ask("Preferred language for Metis responses", default="English")

    # ── Section 2: Research ───────────────────────────────────────────────────
    _banner("2 / 4  Your research")
    field   = _ask("Primary research field", required=True, min_len=3)
    topics  = _ask(
        "Key research topics (comma-separated)",
        required=True
    )
    tools   = _ask(
        "Tools and software you use daily",
        default="R, Python"
    )
    methods = _ask("Research methods (e.g. cohort study, RCT, spatial analysis)")

    # ── Section 3: Working style ──────────────────────────────────────────────
    _banner("3 / 4  How you like to work")
    feedback_style = _ask_choice(
        "How direct should Metis be with feedback?",
        [
            ("gentle",   "Supportive — always encouraging, soften critique"),
            ("direct",   "Direct — honest and clear, skip the padding"),
            ("blunt",    "Blunt — no hedging, challenge everything"),
        ],
        default="direct",
    )
    challenge_level = _ask_choice(
        "How much should Metis challenge your thinking?",
        [
            ("supportive", "Supportive — help me execute my plans"),
            ("balanced",   "Balanced — push back when something looks off"),
            ("socratic",   "Socratic — question my assumptions proactively"),
        ],
        default="balanced",
    )
    output_length = _ask_choice(
        "Preferred output length?",
        [
            ("concise",   "Concise — get to the point, use bullets"),
            ("moderate",  "Moderate — some context, then the answer"),
            ("detailed",  "Detailed — full explanation with background"),
        ],
        default="concise",
    )

    # ── Section 4: Projects ───────────────────────────────────────────────────
    _banner("4 / 4  Your active projects")
    print("  Add your active projects one by one. Press Enter with an empty name to finish.")
    print("  For each project you can optionally give a folder path — Metis will")
    print("  create a CLAUDE.md there and register it in Claude Desktop.\n")

    default_categories = ["Article", "Grant", "Teaching", "Software", "Review"]
    print(f"  Default categories: {', '.join(default_categories)}")
    cats_raw = _ask("  Add or remove categories (comma-separated, Enter to keep defaults)", default="")
    if cats_raw.strip():
        custom = [c.strip() for c in cats_raw.split(",") if c.strip()]
        categories = list(dict.fromkeys(default_categories + custom))
    else:
        categories = default_categories
    print(f"  Categories: {', '.join(categories)}\n")

    scan_type = _ask_choice(
        "How should Metis detect project purpose from folder contents?",
        [
            ("names",   "File names only (fast)"),
            ("content", "Read README/notes (more accurate)"),
            ("none",    "I will describe each project manually"),
        ],
        default="names",
    )

    projects = []
    project_num = 0
    while True:
        project_num += 1
        print(f"\n  ── Project {project_num} ──")
        pname = _ask("  Project name (Enter to finish)", required=False)
        if not pname:
            break
        cat_display = " / ".join(f"[{i+1}] {c}" for i, c in enumerate(categories))
        print(f"  Category: {cat_display} / [N] New")
        cat_choice = input("  Choose [1-{}/N, Enter for 1]: ".format(len(categories))).strip()
        if cat_choice.upper() == "N":
            new_cat = input("  New category name: ").strip()
            if new_cat:
                categories.append(new_cat)
                category = new_cat
            else:
                category = categories[0]
        else:
            try:
                idx = int(cat_choice) - 1
                category = categories[idx] if 0 <= idx < len(categories) else categories[0]
            except (ValueError, IndexError):
                category = categories[0]
        folder = _ask("  Folder path (optional, e.g. /mnt/c/Users/you/my-project)")
        description = ""
        if scan_type == "none":
            description = _ask("  Describe this project (1-2 sentences)")
        projects.append({
            "name": pname,
            "category": category,
            "folder": folder,
            "description": description,
        })
        print(f"  Added: {pname} [{category}]")

    short_term_goals = _ask(
        "\n  What are you trying to accomplish in the next 3 months?"
    )
    challenges = _ask(
        "What are your main challenges right now?"
    )

    return {
        "name": name,
        "institution": institution,
        "role": role,
        "email": email,
        "language": language,
        "field": field,
        "topics": topics,
        "tools": tools,
        "methods": methods,
        "feedback_style": feedback_style,
        "challenge_level": challenge_level,
        "output_length": output_length,
        "projects": projects,
        "scan_type": scan_type,
        "short_term_goals": short_term_goals,
        "challenges": challenges,
    }


def main():
    parser = argparse.ArgumentParser(description="Metis terminal setup wizard")
    parser.add_argument("--metis-root", required=True)
    parser.add_argument("--api-key", help="Anthropic API key")
    parser.add_argument("--skip-if-configured", action="store_true",
                        help="Exit silently if user-config.yaml already exists")
    args = parser.parse_args()

    metis_root = Path(args.metis_root)
    config_file = metis_root / "system" / "config" / "user-config.yaml"

    if args.skip_if_configured and config_file.exists():
        return  # already configured — don't re-run

    api_key = (
        args.api_key
        or os.environ.get("ANTHROPIC_API_KEY")
    )

    answers = run_wizard(metis_root, api_key)

    # Write answers to a temp file and call the processor
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)
        answers_path = f.name

    try:
        # Import processor from the same directory
        processor_path = Path(__file__).parent / "process_wizard_answers.py"
        sys.path.insert(0, str(processor_path.parent))

        print()
        print("━" * 66)
        print("  Processing your answers with Claude...")
        print("━" * 66)

        from process_wizard_answers import process
        result = process(answers, metis_root, api_key)

        print()
        if result.get("ai_used"):
            print("  ✓  AI calibration complete — Metis knows how to work with you")
        elif result.get("warning"):
            print(f"  ⚠  {result['warning']}")

        print(f"  ✓  Persona written")
        print(f"  ✓  User config written")
        for p in result["projects"]:
            name = Path(p).stem.replace("-", " ").title()
            print(f"  ✓  Project: {name}")

        print()
        print("━" * 66)
        print("  Setup complete.")
        print()
        print("  Next:")
        print("  1. Open Claude Code in this folder")
        print("  2. Metis is ready — your config is baked in")
        print("  3. To fine-tune later: /metis_config")
        print("━" * 66)
        print()

    finally:
        Path(answers_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
