"""Metis for ITM — smoke test, run inside the test image (docker/Dockerfile).

Plays a new colleague the morning after installing: does every surface open,
is the ITM pack where it should be, does Claude get the ITM actions, can the
institute's IRB letter actually be filled, and is what the edition leaves out
really gone. Exit code 0 only when every check passes; each check prints one
line, so a failure says which promise broke.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("METIS_RC_ROOT", "/metis"))
results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((bool(ok), name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))


# ── The dashboard, as the colleague opens it ────────────────────────────────
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(ROOT / "system" / "app-py"))
import main  # noqa: E402

with TestClient(main.app) as c:  # runs startup: migrations, the ITM focus
    for path in ("/health", "/today", "/news", "/thinking", "/work", "/meetings",
                 "/presentation", "/knowledge", "/metis", "/focus", "/pack"):
        r = c.get(path)
        check(f"page {path} opens", r.status_code == 200, f"status {r.status_code}")

    page = c.get("/today").text
    check("the ITM section is in the sidebar", "nav-sec--pack" in page)
    check("the learning surface is not offered", 'data-tab="learning"' not in page)
    check("the ITM focus is on the shelf", 'data-tab="focus:itm"' in page)

    pack_page = c.get("/pack").text
    for title in ("Prepare an IRB submission", "Make an ITM presentation", "Make an ITM poster"):
        check(f"ITM action shown: {title}", title in pack_page)
    for tid in ("irb-cover-letter", "presentation", "poster-portrait"):
        r = c.get(f"/pack/template/{tid}")
        check(f"template downloads: {tid}", r.status_code == 200 and len(r.content) > 10_000,
              f"status {r.status_code}, {len(r.content)} bytes")
    check("a path outside the pack is refused",
          c.get("/pack/template/..%2F..%2Fpack.json").status_code == 404)

# ── The profile the wizard wrote ────────────────────────────────────────────
prefs_path = ROOT / "system" / "config" / "user-preferences.json"
prefs = json.loads(prefs_path.read_text(encoding="utf-8")) if prefs_path.exists() else {}
check("the wizard's answers became the profile",
      "Test Colleague" in json.dumps(prefs), f"{prefs_path} has {list(prefs)[:6]}")

# ── Claude's side: the MCP server as Claude Desktop starts it ───────────────
from metis_mcp import server  # noqa: E402

tools = set(server.app._tool_manager._tools)
check("the server loaded its modules", not server.FAILED_MODULES, ", ".join(server.FAILED_MODULES))
check("the edition switched its modules off",
      set(server.EDITION_SKIPPED) == {"dhis2", "course_builder", "background_packs",
                                      "voice_capture", "accounts"},
      ", ".join(server.EDITION_SKIPPED))
check("Claude gets the ITM actions", {"institution_actions", "institution_procedure"} <= tools)
prompts = set(server.app._prompt_manager._prompts)
check("the ITM actions are in Claude Desktop's menu",
      {"itm-irb-request", "itm-presentation", "itm-poster"} <= prompts)
left_out = {"dhis2-expert", "dashboard-engineer", "course-builder", "rc-builder"} & prompts
check("left-out specialists are not offered", not left_out, ", ".join(sorted(left_out)))

# ── The real thing: fill the institute's IRB letter ─────────────────────────
from metis_mcp.tools import authoring  # noqa: E402
from metis_mcp.tools import pack as P  # noqa: E402

proc = asyncio.run(P.institution_procedure("irb"))[0].text
check("the IRB procedure is handed over", "UZA" in proc and "TO COMPLETE" in proc)
read = asyncio.run(authoring.read_document_template("IRB cover letter"))[0].text
check("the IRB letter can be read paragraph by paragraph", "p5:" in read, read[:120])
out_name = "smoke-test-irb-letter.docx"
filled = asyncio.run(authoring.fill_document_template(
    json.dumps({"p5": "Antwerp, 1 January 2027"}), template="IRB cover letter",
    filename=out_name))[0].text
# The tool dates the file ("2026-10-26_<name>") so letters never overwrite each other.
made = list(ROOT.rglob(f"*{out_name}"))
check("the IRB letter is filled and saved", bool(made), filled[:160])
if made:
    import docx
    text = "\n".join(p.text for p in docx.Document(made[0]).paragraphs)
    check("the filled letter carries the new date", "1 January 2027" in text)
    for m in made:
        m.unlink()

# ── Verdict ─────────────────────────────────────────────────────────────────
failed = [n for ok, n, _ in results if not ok]
print()
print(f"{len(results) - len(failed)} of {len(results)} checks passed.")
sys.exit(1 if failed else 0)
