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


def _ask(prompt: str, default: str = "", required: bool = False) -> str:
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
    name         = _ask("Your name", required=True)
    institution  = _ask("Institution or organisation")
    role         = _ask("Your role or title", required=True)
    email        = _ask("Email (optional — used in outputs only)")
    language     = _ask("Preferred language for Metis responses", default="English")

    # ── Section 2: Research ───────────────────────────────────────────────────
    _banner("2 / 4  Your research")
    field   = _ask("Primary research field", required=True)
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
    projects_text = _ask_multiline(
        "List your active projects:",
        hint="e.g.  Malaria prevalence survey in rural communities\n  "
             "     Systematic review on vaccine effectiveness\n  "
             "     Health facility mapping project",
    )
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
        "projects": projects_text,
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
