"""
config_merger.py — Merge a new Metis version's default configs into an existing install.

Run after unpacking a Metis update to:
  1. Carry forward user-config.yaml and user-preferences.json (never overwritten)
  2. Merge new default keys from updated config templates (additive only — no deletions)
  3. Write a migration log so the user can see what changed

Usage:
    python config_merger.py --install-dir C:\\Users\\YourName\\Documents\\Metis

Safe to run multiple times (idempotent).
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Defaults shipped with this version — add new keys here when Metis is updated
# ---------------------------------------------------------------------------

USER_CONFIG_DEFAULTS = {
    "name": "",
    "role": "",
    "institution": "",
    "research_domain": "",
    "research_interests": [],
    "news_topics": [],
    "preferred_language": "en",
    "timezone": "UTC",
    "llm": {
        "default_model": "claude-sonnet-4-6",
        "deep_model": "claude-opus-4-7",
        "fast_model": "claude-haiku-4-5",
    },
    "specialist_contexts": {},
    "active_contexts": [],
    "dashboard": {
        "theme": "light",
        "start_tab": "today",
        "news_rail_categories": ["news", "paper", "alert"],
    },
}

USER_PREFS_DEFAULTS: dict = {
    "capture": {
        "default_type": "idea",
        "cross_pollinate": True,
    },
    "morning_brief": {
        "enabled": True,
        "run_at": "07:00",
        "include_news": True,
        "include_papers": True,
        "include_tasks": True,
    },
    "library": {
        "auto_embed": True,
        "embed_model": "nomic-embed-text-v1.5-Q",
    },
    "notifications": {
        "task_due_reminder_hours": 2,
        "meeting_reminder_minutes": 15,
    },
}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Merge overlay INTO base. Existing values in base are preserved."""
    result = dict(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        elif key not in result:
            result[key] = val
    return result


def merge_yaml(path: Path, defaults: dict, log: list) -> None:
    existing = {}
    if path.exists():
        with path.open() as f:
            existing = yaml.safe_load(f) or {}

    merged = _deep_merge(existing, defaults)

    added = [k for k in defaults if k not in existing]
    if added:
        log.append(f"{path.name}: added keys {added}")

    with path.open("w") as f:
        yaml.dump(merged, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def merge_json(path: Path, defaults: dict, log: list) -> None:
    existing = {}
    if path.exists():
        with path.open() as f:
            existing = json.load(f)

    merged = _deep_merge(existing, defaults)

    added = [k for k in defaults if k not in existing]
    if added:
        log.append(f"{path.name}: added keys {added}")

    with path.open("w") as f:
        json.dump(merged, f, indent=2)


def run(install_dir: Path) -> None:
    config_dir = install_dir / "system" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    log: list[str] = []

    # user-config.yaml
    merge_yaml(config_dir / "user-config.yaml", USER_CONFIG_DEFAULTS, log)

    # user-preferences.json
    merge_json(config_dir / "user-preferences.json", USER_PREFS_DEFAULTS, log)

    # Write migration log
    log_dir = config_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{date.today().isoformat()}-config-merge.log"
    with log_path.open("w") as f:
        if log:
            f.write(f"Config merge — {date.today().isoformat()}\n\n")
            for entry in log:
                f.write(f"  + {entry}\n")
        else:
            f.write(f"Config merge — {date.today().isoformat()}\n\nNo changes needed.\n")

    if log:
        print(f"Config updated — {len(log)} change(s):")
        for entry in log:
            print(f"  + {entry}")
        print(f"\nFull log: {log_path}")
    else:
        print("Config up to date — no changes needed.")


def main():
    p = argparse.ArgumentParser(description="Merge Metis config defaults into an existing install")
    p.add_argument("--install-dir", default=".", help="Metis install directory (default: current dir)")
    args = p.parse_args()
    run(Path(args.install_dir))


if __name__ == "__main__":
    main()
