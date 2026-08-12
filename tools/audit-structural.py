#!/usr/bin/env python3
"""audit-structural.py — find code that LOOKS structural but never runs.

WHY THIS EXISTS
    On 2026-08-12 four separate defects turned out to share one shape: a control or
    feature that was correctly written, visibly present, and never reached. None of
    them raised an error; several had passing tests.

      · the tool guard wrapped `app.call_tool`, but FastMCP had already captured the
        original method at construction — so no real MCP request ever hit the guard.
        `tool_guard_log` held 3 rows, all from the day it was written, none since.
      · `@app.tool()` bound to a helper inserted beneath it, silently de-registering
        `session_bootstrap` and `kg_index_notes`. The tool COUNT was unchanged.
      · `_check_output_stage` — an output red-line security scan — was defined and
        called by nothing.
      · memory write-backs sat behind `run_metis`, which is almost never invoked,
        so `session_events` had zero rows for its entire existence.

    The common lesson: **absence of an error is not evidence of execution.** These
    are found by asking "what has no caller, no writer, or no rows?", not by reading
    the code, which looks correct in every case.

WHAT IT CHECKS
    1. UNREACHED FUNCTIONS — guards/probes/validators defined but never referenced.
    2. DECORATOR DRIFT     — @app.tool() bound to a private (`_`-prefixed) function.
    3. LATE MONKEY-PATCH   — attribute reassignment on an object that may already
                             have handed the original out. Advisory: needs a human.
    4. UNFILLABLE TABLES   — the code reads a table nothing can write.
    5. SILENT LAYERS       — a writer exists, but the table is empty (informational:
                             often just an unused feature, sometimes a dead control).

EXIT CODE
    1 if a HIGH-severity finding exists (1, 2, or 4), else 0.
    Categories 3 and 5 always report but never fail — they need judgement.

USAGE
    python3 tools/audit-structural.py [--all]      # --all shows informational rows
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = [
    ROOT / "system/mcp-server/src/metis_mcp",
    ROOT / "system/app-py",
    ROOT / "tools",
    ROOT / "system/install",
]
SKIP = ("build/lib", ".venv", "site-packages", "node_modules", "__pycache__")

# Function-name fragments worth policing. A dead formatting helper is untidy; a dead
# guard is a security control everyone believes is running.
GUARD_WORDS = ("scan", "check", "guard", "probe", "verify", "validate", "sanitize",
               "sanitise", "persist", "record", "audit", "enforce", "mask", "detect",
               "block", "refuse")


def source_files() -> list[Path]:
    out = []
    for base in SRC_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(s in str(p) for s in SKIP):
                continue
            out.append(p)
    return out


def resolve_db() -> Path | None:
    for c in (Path.home() / ".local/share/metis/metis.sqlite",
              ROOT / "system/app/data/metis.sqlite"):
        if c.is_file() and c.stat().st_size > 0:
            return c
    return None


def main() -> int:
    show_all = "--all" in sys.argv
    files = source_files()
    text = {p: p.read_text(encoding="utf-8", errors="replace") for p in files}
    ALL = "\n".join(text.values())

    high: list[str] = []
    info: list[str] = []

    # ── 1 + 2: AST scan ─────────────────────────────────────────────────────
    # AST, not regex. A look-back window over raw text cannot tell which function a
    # decorator belongs to, and reports every helper that merely FOLLOWS a decorated
    # route as if it were decorated itself. ast.decorator_list is exact — and
    # exactness is the whole point of an audit whose job is to be believed.
    import ast

    unreached, drift, hollow = [], [], []
    for p, src in text.items():
        rel = p.relative_to(ROOT)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            info.append(f"NOTE — could not parse {rel}; skipped.")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name
            if name.startswith("__"):
                continue
            decorators = " ".join(ast.unparse(d) for d in node.decorator_list)
            is_tool = "app.tool" in decorators
            is_route = bool(re.search(r"\b(router|app)\.(get|post|put|delete)\b", decorators))

            # 2. decorator drift — ONLY meaningful for @app.tool().
            # There the function NAME becomes the public tool name, so a private
            # name means the decorator slid onto the wrong function. For an HTTP
            # route the URL PATH is the identifier and a `_name` is merely style —
            # flagging those produced four false positives in teach.py.
            if is_tool and name.startswith("_"):
                drift.append(f"{rel}:{node.lineno}  @app.tool() bound to private {name}()")
                continue

            # 6. hollow route — registered, reachable, and returns nothing real.
            # This is the UI dialect of the same disease: the endpoint exists, the
            # tab renders, and the panel is a placeholder returning an empty div.
            if is_route:
                body = [n for n in node.body if not isinstance(n, ast.Expr)
                        or not isinstance(getattr(n, "value", None), ast.Constant)]
                if len(body) == 1 and isinstance(body[0], ast.Return):
                    ret = ast.unparse(body[0]).strip()
                    if re.search(r"""^return\s+\w*\(?\s*['"](\s*|<div>\s*</div>|<span>\s*</span>|)['"]""",
                                 ret) or re.search(r"<div>\s*</div>|<span>\s*</span>", ret):
                        path = re.search(r"""['"]([^'"]+)['"]""", decorators)
                        hollow.append(f"{rel}:{node.lineno}  {path.group(1) if path else name}"
                                      f"  →  {ret[:52]}")
                continue

            if is_route or is_tool or decorators:
                continue  # invoked by a framework, not by name

            if not any(w in name.lower() for w in GUARD_WORDS):
                continue
            # Count BOTH call sites and bare-name references (thread targets, registry
            # dicts). Missing the bare-name form produced three false positives on the
            # first run of this audit — `_startup_selfcheck` is passed to a Thread as
            # `target=`, and `job_morning_scan` lives in a schedule dict.
            refs = len(re.findall(rf"(?<![\w.]){re.escape(name)}(?![\w])", ALL))
            if refs <= 1:                       # only its own definition
                unreached.append(f"{rel}:{node.lineno}  {name}()")

    if drift:
        high.append("DECORATOR DRIFT — a private helper is registered as a tool, which means\n"
                    "the real tool below it lost its registration:")
        high += [f"    {d}" for d in drift]
    if hollow:
        info.append("HOLLOW ROUTES (informational) — the endpoint is registered and returns 200,\n"
                    "but the body is a placeholder. The surface looks built; nothing is behind it:")
        info += [f"    {h}" for h in hollow]
    if unreached:
        high.append("UNREACHED — defined, referenced nowhere else. A guard nobody calls is not a guard:")
        high += [f"    {u}" for u in unreached]

    # ── 3: late monkey-patching (advisory) ──────────────────────────────────
    patches = []
    for p, src in text.items():
        for m in re.finditer(r"^\s*([a-z_][\w.]*)\.([a-z_]\w*) *= *([a-z_]\w*)\s*(?:#|$)",
                             src, re.M | re.I):
            obj, attr, val = m.groups()
            if obj in ("self", "cls") or val in ("None", "True", "False"):
                continue
            if not re.search(rf"(async +)?def +{re.escape(val)}\b", src):
                continue                        # only when assigning a function
            patches.append(f"{p.relative_to(ROOT)}:{src[:m.start()].count(chr(10))+1}  "
                           f"{obj}.{attr} = {val}")
    if patches:
        info.append("LATE MONKEY-PATCH (advisory) — replacing a method AFTER something may have\n"
                    "captured the original silently does nothing. Confirm the owner re-reads it:")
        info += [f"    {x}" for x in patches]

    # ── 4 + 5: table reachability ───────────────────────────────────────────
    db = resolve_db()
    if db:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=180)
        tables = sorted(r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        unfillable, silent = [], []
        for t in tables:
            if t.startswith("vec_") or t.endswith(("_fts", "_data", "_idx", "_content",
                                                   "_docsize", "_config", "_vocab")):
                continue
            writers = len(re.findall(rf"INSERT\s+(?:OR\s+\w+\s+)?INTO\s+{t}\b", ALL, re.I)) \
                    + len(re.findall(rf"UPDATE\s+{t}\b", ALL, re.I))
            readers = len(re.findall(rf"FROM\s+{t}\b", ALL, re.I))
            try:
                n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except Exception:
                continue
            if writers == 0 and readers > 0:
                unfillable.append(f"{t:32} rows={n:<7} read in {readers}, written in 0")
            elif writers > 0 and n == 0:
                silent.append(f"{t:32} {writers} writer(s), 0 rows")
        con.close()
        if unfillable:
            high.append("UNFILLABLE — the code READS these tables but nothing can WRITE them:")
            high += [f"    {u}" for u in unfillable]
        if silent:
            info.append("SILENT (informational) — a writer exists but the table is empty. Often an\n"
                        "unused feature; sometimes a control that has never once fired:")
            info += [f"    {s}" for s in silent]
    else:
        info.append("NOTE — no database found; table checks skipped.")

    print("=" * 78)
    print("  Metis structural audit — what looks wired but isn't")
    print("=" * 78)
    if high:
        for line in high:
            print(("\n" if not line.startswith("    ") else "") + line)
    else:
        print("\n  ✓ no high-severity findings")
    if info and (show_all or not high):
        for line in info:
            print(("\n" if not line.startswith("    ") else "") + line)
    elif info:
        print(f"\n  ({sum(1 for i in info if i.startswith('    '))} informational rows — re-run with --all)")
    print()
    return 1 if high else 0


if __name__ == "__main__":
    raise SystemExit(main())
