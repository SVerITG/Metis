#!/usr/bin/env python3
"""
Metis Data Guardian — Claude Code pre-submit hook

Scans outgoing prompts for PII, sensitive data patterns, and file references
before they reach Anthropic's servers.

Usage as Claude Code hook:
  In settings.json:
  {
    "hooks": {
      "PreToolUse": [
        {
          "matcher": ".*",
          "hooks": ["python3 /path/to/data-guardian-hook.py"]
        }
      ]
    }
  }

Reads from stdin (JSON with tool_name and tool_input),
writes to stdout (JSON with decision: "allow", "block", or "ask").
"""

import json
import re
import sys
import os
from datetime import datetime
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────

RC_ROOT = os.environ.get(
    "METIS_RC_ROOT",
    "/mnt/c/Users/sverschaeve/OneDrive - ITG/Documents/7. Software/Research Cortex/metis"
)

SECURITY_DIR = Path(RC_ROOT) / "08_system" / "security"
LOG_DIR = Path(RC_ROOT) / "07_outputs" / "reviews" / "data-guardian"

# ── Load patterns ──────────────────────────────────────────────────────────

def load_patterns(filepath):
    """Load PII patterns from config file."""
    patterns = []
    path = SECURITY_DIR / filepath
    if not path.exists():
        return patterns
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) >= 2:
            name = parts[0].strip()
            regex = parts[1].strip()
            desc = parts[2].strip() if len(parts) > 2 else name
            try:
                patterns.append({"name": name, "regex": re.compile(regex, re.IGNORECASE), "desc": desc})
            except re.error:
                pass
    return patterns

def load_sensitive_columns(filepath):
    """Load sensitive column names."""
    path = SECURITY_DIR / filepath
    if not path.exists():
        return set()
    columns = set()
    for line in path.read_text().splitlines():
        line = line.strip().lower()
        if line and not line.startswith("#"):
            columns.add(line)
    return columns

PII_PATTERNS = load_patterns("pii-patterns.txt")
SENSITIVE_COLUMNS = load_sensitive_columns("sensitive-columns.txt")

# File extensions that need scrutiny
DATA_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv", ".rds", ".rdata", ".sav", ".dta", ".sqlite", ".db"}
NEVER_SEND_EXTENSIONS = {".sqlite", ".db", ".rdata"}

# Prompt injection patterns
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"new\s+system\s+prompt", re.IGNORECASE),
    re.compile(r"override\s*:", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<<SYS>>", re.IGNORECASE),
]

# ── Scanning functions ─────────────────────────────────────────────────────

def scan_for_pii(text):
    """Scan text for PII patterns. Returns list of findings."""
    findings = []
    for pattern in PII_PATTERNS:
        matches = pattern["regex"].findall(text)
        if matches:
            findings.append({
                "pattern": pattern["name"],
                "description": pattern["desc"],
                "count": len(matches),
                "sample": matches[0][:30] + "..." if len(matches[0]) > 30 else matches[0]
            })
    return findings

def scan_for_file_references(text):
    """Detect references to sensitive file types in text."""
    findings = []
    for ext in DATA_EXTENSIONS:
        pattern = re.compile(r'[\w/\\.-]+' + re.escape(ext), re.IGNORECASE)
        matches = pattern.findall(text)
        if matches:
            severity = "block" if ext in NEVER_SEND_EXTENSIONS else "warn"
            findings.append({
                "extension": ext,
                "files": matches[:5],
                "severity": severity
            })
    return findings

def scan_for_sensitive_columns(text):
    """Detect sensitive column names in text that might be data headers."""
    found = []
    text_lower = text.lower()
    for col in SENSITIVE_COLUMNS:
        if col in text_lower:
            found.append(col)
    return found

def scan_for_injection(text):
    """Detect prompt injection attempts in content."""
    findings = []
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            findings.append(pattern.pattern)
    return findings

def check_large_data_block(text):
    """Detect if text contains what looks like bulk data (many rows of tab/comma separated values)."""
    lines = text.split("\n")
    data_lines = 0
    for line in lines:
        if line.count(",") > 3 or line.count("\t") > 3:
            data_lines += 1
    return data_lines

# ── Logging ────────────────────────────────────────────────────────────────

def log_event(event_type, details, action):
    """Append to daily log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_data-guardian-log.md"

    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"| {timestamp} | {event_type} | {details} | {action} |\n"

    if not log_file.exists():
        header = f"## Data Guardian Log — {datetime.now().strftime('%Y-%m-%d')}\n\n"
        header += "| Time | Type | Details | Action |\n"
        header += "|------|------|---------|--------|\n"
        log_file.write_text(header + entry)
    else:
        with open(log_file, "a") as f:
            f.write(entry)

# ── Main hook logic ────────────────────────────────────────────────────────

def evaluate(tool_input_text):
    """Evaluate text and return (decision, reason)."""
    all_warnings = []

    # 1. Check for PII
    pii = scan_for_pii(tool_input_text)
    if pii:
        details = ", ".join(f"{p['pattern']}({p['count']})" for p in pii)
        log_event("PII detected", details, "blocked")
        return "block", f"PII detected: {details}. Remove personal data before sending."

    # 2. Check for database files (always block)
    file_refs = scan_for_file_references(tool_input_text)
    for ref in file_refs:
        if ref["severity"] == "block":
            log_event("Blocked file type", f"{ref['extension']}: {ref['files']}", "blocked")
            return "block", f"Database/binary file detected ({ref['extension']}). These must never be sent to external services."

    # 3. Check for data files (warn)
    for ref in file_refs:
        if ref["severity"] == "warn":
            all_warnings.append(f"Data file referenced: {ref['files'][0]}")

    # 4. Check for sensitive column names (could be pasting data)
    sensitive_cols = scan_for_sensitive_columns(tool_input_text)
    if len(sensitive_cols) >= 3:
        detail = ", ".join(sensitive_cols[:5])
        log_event("Sensitive columns", detail, "blocked")
        return "block", f"Text contains multiple sensitive data column names ({detail}). This looks like patient-level data. Remove or aggregate before sending."

    # 5. Check for bulk data
    data_lines = check_large_data_block(tool_input_text)
    if data_lines > 50:
        log_event("Bulk data", f"{data_lines} data-like lines", "warn")
        all_warnings.append(f"Text contains {data_lines} lines that look like tabular data. Consider sending a summary instead of raw data.")

    # 6. Check for prompt injection (in fetched content)
    injections = scan_for_injection(tool_input_text)
    if injections:
        log_event("Prompt injection", str(injections), "warn")
        all_warnings.append(f"Possible prompt injection detected in content: {injections[0]}")

    if all_warnings:
        log_event("Warnings", "; ".join(all_warnings), "allowed with warnings")
        return "allow", "Warnings: " + "; ".join(all_warnings)

    return "allow", ""

def main():
    """Read hook input from stdin, evaluate, write decision to stdout."""
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        # If we can't parse input, allow by default (don't break the workflow)
        print(json.dumps({"decision": "allow"}))
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Convert tool input to searchable text
    text_to_scan = json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input)

    # Only scan tools that send data externally
    # Read, Glob, Grep are local — skip them
    local_tools = {"Read", "Glob", "Grep", "Edit", "Write", "Bash"}
    if tool_name in local_tools:
        print(json.dumps({"decision": "allow"}))
        return

    decision, reason = evaluate(text_to_scan)

    output = {"decision": decision}
    if reason:
        output["reason"] = reason

    print(json.dumps(output))

if __name__ == "__main__":
    main()
