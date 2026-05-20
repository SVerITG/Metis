# Metis Comprehensive Test Protocol
**Version:** 2026-05-20
**Use in:** Claude Code (this folder), or paste into a new Claude Chat session
**Purpose:** Verify that every aspect of Metis works — installation, MCP wiring, dashboard, agent workflows, Claude Desktop integration, and interconnectedness — for all 10 researcher personas.

---

## How to use this prompt

1. Open a fresh Claude Code session in the Research Cortex root
2. Paste the entire content below the horizontal rule as your first message
3. Claude will work through each section, come back with findings, and flag every failure
4. After Claude finishes, ask: **"Now challenge every finding — what did you miss?"**

---

---

# METIS MASTER TEST — Full System Verification

You are running the Metis Master Test Protocol. Work through every section below. For each test:
- **PASS**: state what you verified
- **FAIL**: state the exact problem, the file/line, and the fix required
- **SKIP**: state why (e.g., requires running dashboard)

Challenge your own findings after each section. If something passes, ask yourself: "Is this genuinely working end-to-end, or just present on disk?"

---

## SECTION 1: MCP Server — Installation & Registration

**Test objective:** Verify the MCP server is installed, correctly wired into both Claude Code and Claude Desktop, and actually importable without errors.

```
1. Read ~/.local/share/metis-mcp/run.sh
   - Does it export METIS_RC_ROOT (not METIS_PKM_ROOT)?
   - Does METIS_RC_ROOT point to this Research Cortex folder (not a /metis subfolder)?

2. Read ~/.claude/settings.json
   - Is "metis-rc" in mcpServers?
   - Is "metis-pkm" absent (stale entry removed)?
   - Is "mcp__metis-rc__*" in permissions.allow?

3. Read /mnt/c/Users/{username}/AppData/Roaming/Claude/claude_desktop_config.json
   - Is "metis-rc" in mcpServers with the correct wsl run.sh path?
   - Is "metis-pkm" absent?
   - Is Zotero still registered (should not be removed)?

4. Import test — run:
   ~/.local/share/metis-mcp/.venv/bin/python3 -c "import metis_mcp.server; print('ok')"
   - Does it print "ok" with no ImportError?
   - Count the tools registered (should be 157).

5. Check server.py for stale imports:
   - Is "research" absent from the tools import list?
   - Are all other imported modules present in system/mcp-server/src/metis_mcp/tools/?

Challenge: What happens when Claude Desktop restarts and loads this MCP config? Will it find the run.sh? Does the METIS_RC_ROOT path survive the WSL→Windows round-trip?
```

---

## SECTION 2: Desktop Shortcut Chain

**Test objective:** The desktop shortcut must launch the Python FastAPI dashboard on port 8080, not the old R Shiny app on port 3939.

```
1. Read system/launch-metis.bat
   - Does it call launch-metis-silent.vbs?

2. Read system/launch-metis-silent.vbs
   - Does it run app-py/run.sh (not app/launch.R)?
   - Does it open http://127.0.0.1:8080 (not 3939)?
   - Does it use wsl.exe to convert the Windows path to a WSL path?

3. Read system/app-py/run.sh
   - Does it use ~/.local/share/metis-mcp/.venv?
   - Does it auto-select a port in range 8080–8090?
   - Does it set METIS_RC_ROOT?

4. Check the old R Shiny launcher still exists but is NOT in the shortcut chain:
   - system/app/launch_metis.bat should mention "3939" and "Rscript"
   - The desktop shortcut should NOT point here

5. Check create_shortcuts.ps1 in system/app/ — warn if it would create a shortcut to the R Shiny launcher

Challenge: On a fresh install, which shortcut creation script runs? Does setup-mcp.sh always win over create_shortcuts.ps1? What if the user double-clicks create_shortcuts.ps1 by mistake?
```

---

## SECTION 3: Dashboard — 9 Tabs

**Test objective:** All 9 dashboard tabs must return non-500 responses and contain expected content.

```
Run the automated test suite:
  ~/.local/share/metis-mcp/.venv/bin/python3 -m pytest \
    system/tests/e2e/test_smoke.py -v

Then manually verify each tab's key content:

Tab 1: /today
- Morning brief partial loads (or returns graceful 404 with seed data missing)
- No raw Python errors visible

Tab 2: /knowledge
- Library stats widget present
- Search input exists
- Literature list loads

Tab 3: /meetings
- Meeting list partial loads
- Recording button exists in template

Tab 4: /learning
- Spaced repetition cards section visible
- Streak tracker present

Tab 5: /work
- Workbench panel has three Claude buttons: Chat, Cowork, Code
- Projects list loads
- Task kanban renders

Tab 6: /thinking
- Capture modal accessible (Ctrl+K wired in app.js)
- Ideas list loads

Tab 7: /planner
- Weekly intentions section present

Tab 8: /teach
- Course builder form loads

Tab 9: /metis
- Agent registry visible
- Tool count displayed

Challenge: Which tabs genuinely need database rows to show anything useful? Which tabs fail gracefully when the DB is empty? Tab 1 (Today) is the most critical for first-run experience — does it show something useful even with no data?
```

---

## SECTION 4: Claude Desktop Integration — Chat / Cowork / Code

**Test objective:** Every project must have three Claude launcher buttons, and each must route to the right interface.

```
1. Read system/app-py/templates/work.html
   - Does the Workbench panel contain launchProjectTarget(...,'claude_chat')?
   - Does it contain launchProjectTarget(...,'claude_cowork')?
   - Does it contain launchProjectTarget(...,'claude_code')?
   - Are all three buttons clearly labeled (Chat / Cowork / Code)?

2. Read system/app-py/templates/partials/work_projects.html
   - Do per-project cards have Chat, Cowork, and Code buttons?
   - Is the old 'claude_desktop' label replaced by 'claude_chat'?

3. Read system/app-py/routers/work.py, function launcher_links()
   - Does every launcher_type (article, rstudio, vscode, generic) include
     claude_chat AND claude_cowork AND claude_code?

4. Read the /api/project/launch handler in work.py
   - claude_chat → opens claude:// protocol ✓
   - claude_cowork → copies project path to clipboard, then opens claude:// ✓
   - claude_code → opens Windows Terminal with WSL, runs 'claude' in project folder ✓

5. Decision guide — explain which interface to use for which task:

   | Task | Use |
   |---|---|
   | Ask a question about a paper | Claude Chat |
   | Work on a long document with context | Claude Chat (new conversation) |
   | Collaborative session with memory | Claude Cowork (paste project path) |
   | Code review, R script debugging | Claude Code (terminal) |
   | Metis agent workflows (/metis commands) | Claude Code |
   | Morning brief, quick capture | Claude Chat |
   | Multi-session PhD article work | Claude Cowork |

Challenge: The Cowork clipboard-copy approach is a workaround — Claude Desktop doesn't have a URL scheme that opens a specific project directly. Is there a better approach? What would need to change in Claude Desktop's URL scheme to support direct project loading?
```

---

## SECTION 5: All 10 Persona Workflows

**Test objective:** Run the persona test suite. For each persona, state whether their critical features are present.

```
Run:
  ~/.local/share/metis-mcp/.venv/bin/python3 -m pytest \
    system/tests/personas/test_all_personas.py -v --tb=short

For each persona, verify their key dependency manually:

P1 — Fatou Diallo (PhD, Windows, beginner)
  Must have: librarian + epidemiologist + writing-partner skill files
  Must have: Ctrl+K capture in app.js
  Risk: university-managed Windows may block Python install

P2 — Dr. Elena Marchetti (Senior researcher, meetings-heavy)
  Must have: meeting-memory + transcription + voice_capture MCP tools
  Must have: /api/partial/meetings/list endpoint
  Risk: live meeting browser assistant may be partial

P3 — Kwame Asante (Data analyst, Linux)
  Must have: data-analyst + data_tools + visualization-maker
  Must have: Data Guardian does NOT block internal research data
  Risk: bash install on Ubuntu 22.04 without sudo

P4 — Prof. Sarah Okonkwo (Medical educator, course builder)
  Must have: course-builder + presentation-maker + learning-architect
  Must have: /teach tab loads without error
  Risk: PowerPoint export requires python-pptx

P5 — Thomas Weber (Early-career, macOS)
  Must have: learning-coach + career-coach + methods-coach
  Must have: spaced repetition cards in /learning tab
  Risk: Homebrew Python detection in setup-mcp.sh

P6 — Dr. Aminata Sow (Global health consultant, policy)
  Must have: news-radar + meeting-memory + writing-partner
  Must have: Morning brief covers WHO/global health signals
  Risk: WHO website access requires internet permission

P7 — Dr. James Obi (Clinical researcher, strict IT)
  Must have: data-guardian tool blocks patient data
  Must have: librarian searches Cochrane sources
  Risk: hospital proxy may block outbound HTTPS

P8 — Marta Gonzalez (Dev, Docker, Linux expert)
  Must have: rc-builder + builder + cybersecurity agents
  Must have: Docker entrypoint at system/install/docker/docker-entrypoint.sh
  Risk: RC Builder modifies local files with no git commit automation

P9 — Prof. Robert Kim (Department head, overview only)
  Must have: Today tab gives useful overview with no required input
  Must have: Morning brief is short (< 3 paragraphs)
  Risk: first-run wizard must be smooth (won't debug)

P10 — Amara Diarra (Field epidemiologist, mobile)
  Must have: Dashboard accessible on local network (0.0.0.0 binding in run.sh)
  Must have: Large tap targets in capture page
  Risk: Voice capture requires desktop Metis running

Challenge: Which persona has the highest installation failure risk? Which persona would find Metis most confusing on day one without documentation? Test P9 specifically — can the Today tab render anything useful with a completely empty database?
```

---

## SECTION 6: Knowledge Layer (RAG) — Metis as Orchestrator

**Test objective:** Verify F001 (Metis as RAG orchestrator) is properly implemented.

```
1. Read agents/metis/system-prompt.md
   - Does it contain a "Knowledge pre-fetch (RAG)" section?
   - Does it list when to call search_pdf_knowledge() and when to skip?
   - Does it define the [KNOWLEDGE CONTEXT] injection format?
   - Does it define citation tone (e.g., Leyland 2020, p.42)?

2. Read .claude/skills/metis/skill.md
   - Does the routing flow have a step 3 for RAG pre-fetch?
   - Does it say "before routing, call search_pdf_knowledge() if applicable"?

3. Check the knowledge databases are indexed:
   ~/.local/share/metis-mcp/.venv/bin/python3 -c "
   import sqlite3
   db = 'system/app/data/metis.sqlite'
   conn = sqlite3.connect(db)
   rows = conn.execute('SELECT id, doc_count, chunk_count FROM knowledge_databases').fetchall()
   for r in rows: print(r)
   "
   - ph-background: should be ~34 docs, ~5979 chunks
   - epi-methods: should be ~10 docs, ~1129 chunks

4. Test a RAG query:
   ~/.local/share/metis-mcp/.venv/bin/python3 -c "
   import os; os.environ['METIS_RC_ROOT'] = '$(pwd)'
   from metis_mcp.tools.knowledge_db import *
   " 2>&1 | head -5
   (should import without error)

5. Check basket intake procedure:
   - agents/metis/system-prompt.md should describe the basket→library workflow
   - list_basket() → read_file() → promote_basket_item() → build_pdf_knowledge_db()

Challenge: The RAG pre-fetch adds latency to every Metis routing decision. Is the score threshold (≥ 0.4) set correctly? What happens when search_pdf_knowledge() returns 0 results — does Metis still route cleanly? Test with a query that should NOT trigger RAG (e.g., "what is the weather today").
```

---

## SECTION 7: Agent System — Completeness Check

**Test objective:** Every agent invocable from CLAUDE.md must have both a system-prompt.md and a skill.md.

```
Run:
  ~/.local/share/metis-mcp/.venv/bin/python3 -m pytest \
    system/tests/integration/test_claude_integration.py::TestInterconnectedness -v

Then manually cross-check the CLAUDE.md agent table:
- List every /agent-slug from the invocation table
- For each: verify agents/{slug}/system-prompt.md AND .claude/skills/{slug}/skill.md exist
- Flag any agent in CLAUDE.md with no system-prompt or no skill file

Special cases to verify:
- edu-expert: marked RETIRED (has RETIRED.md) — must NOT appear in active agent routing
- hr-talent: lightweight routing agent — system-prompt.md now created ✓
- release-coordinator: private agent — system-prompt.md now a stub pointing to skill.md ✓

Challenge: Are there agents with system-prompts but no skill.md? Those can't be invoked directly by the user. Are there skill.md files in .claude/skills/ with no corresponding agents/ directory? Those would silently fail.
```

---

## SECTION 8: Full Automated Test Suite

**Test objective:** Run all test suites and report the full results matrix.

```
Run the complete test suite:
  ~/.local/share/metis-mcp/.venv/bin/python3 -m pytest system/tests/ \
    -v --tb=short --ignore=system/tests/e2e \
    2>&1 | tail -40

Expected coverage:
  personas/     — 10 persona workflow tests
  audit/        — critical realism, config wizard, UX audit
  integration/  — Claude integration, MCP registration, launcher buttons
  unit/         — individual MCP tool unit tests (if present)

Report:
  - Total passed / failed / skipped
  - Any new failures not present before this session
  - The three path-bug fixes (conftest parents[3]) — confirm they resolved the import issues

Challenge: The audit/test_ux_audit.py has 1249 lines — it tests many UI details. How many of those tests are actually automated vs. documented-but-manual? Run it and count the @pytest.mark.manual skips vs real assertions.
```

---

## SECTION 9: Interconnectedness Verification

**Test objective:** Verify the three layers (Dashboard → MCP → Agents) genuinely talk to each other, not just exist side-by-side.

```
Trace a complete request through the system:

REQUEST: "Review my Article 1 methods section for STROBE compliance"

Step 1 — Routing (Metis)
  - CLAUDE.md agent routing table: routes to Epidemiologist + Writing Partner
  - Metis system-prompt.md RAG pre-fetch: should query epi-methods database
  - Expected output location: outputs/reviews/epidemiologist/ + outputs/reviews/writing-partner/

Step 2 — MCP tools called
  - search_pdf_knowledge() → retrieves relevant epi methods chunks
  - log_agent_run() → logs to agent_runs table
  - read_file() → reads the article draft from inputs/

Step 3 — Dashboard visibility
  - agent_runs table → visible in /metis tab (Agents tab)
  - output files → visible in Work tab if project is configured

Step 4 — Verify each link:
  a. Does agents/metis/system-prompt.md specify which RAG database to query for STROBE?
  b. Does agents/epidemiologist/system-prompt.md reference epi methods knowledge?
  c. Is log_agent_run() implemented in an MCP tool? Which file?
  d. Does the Agents tab in the dashboard read from agent_runs table?
  e. Is the output path convention (outputs/reviews/{slug}/{date}_{slug}.md) enforced anywhere?

Also trace the basket intake workflow:
  - User drops a paper into basket/
  - User asks Metis: "process the paper in my basket"
  - Metis calls list_basket() → read_file() → decide domain → promote_basket_item()
  - Metis calls build_pdf_knowledge_db(database="ph-background")
  - Dashboard shows updated chunk count

Challenge: Is log_agent_run() actually called by any agent systematically, or is it aspirational? Check the agent system prompts for actual MCP tool calls. Is the "self-improvement loop" (reflexions table) populated automatically after agent runs, or only when manually triggered?
```

---

## SECTION 10: Fresh Install Simulation

**Test objective:** Would a researcher succeed if they installed Metis today for the first time?

```
For each install path, describe what the researcher experiences and flag any friction:

Path A — Windows researcher (Personas 1, 2, 4, 6, 7, 9)
  1. Downloads .exe installer or runs install.bat
  2. Installer creates shortcuts → Desktop "Metis" shortcut created
  3. Double-clicks shortcut → VBS fires → WSL/bash runs app-py/run.sh
  4. Browser opens http://127.0.0.1:8080
  5. First run: config wizard (13 sections)
  6. MCP registered with Claude Code + Claude Desktop automatically

  Friction points to identify:
  - Does the Windows installer exist? (check system/installer/ or system/install/windows/)
  - Does it call setup-mcp.sh internally?
  - If WSL is not installed, does the error message tell them how to fix it?
  - Does the first-run config wizard appear without a populated database?

Path B — Linux/macOS researcher (Personas 3, 5)
  1. Clones repo or downloads zip
  2. Runs: bash system/mcp-server/setup-mcp.sh
  3. Chooses standard profile
  4. MCP registered with Claude Code and Claude Desktop (if installed)
  5. Runs app-py/run.sh to start dashboard

  Friction points:
  - macOS: does Homebrew Python detection work?
  - Does setup-mcp.sh handle Python 3.10 (Ubuntu 22.04) AND 3.12 (24.04)?
  - Are all pip install errors non-fatal?

Path C — Docker researcher (Persona 8)
  1. docker compose up -d
  2. Browser opens http://localhost:8080

  Friction points:
  - Does a docker-compose.yml exist?
  - Does the container have the MCP server AND dashboard?

Path D — Mobile researcher (Persona 10)
  1. Opens http://[local-IP]:8080 on phone browser
  2. Dashboard must be accessible on local network, not just localhost

  Friction points:
  - Does app-py/run.sh bind to 0.0.0.0? (check --host flag in uvicorn command)
  - Is there a mobile-optimized capture page?

Challenge: Of the four paths, which one is most likely to fail silently — no error, but also nothing works? Which one requires the most prior technical knowledge to complete?
```

---

## SECTION 11: Self-Critique — What Did You Miss?

After completing all sections above, pause and answer:

```
1. Which of the 10 persona workflows did you NOT actually trace end-to-end —
   you only checked files existed but didn't simulate a real task?

2. Which MCP tools have no test coverage at all (not in unit/ or integration/)?

3. The "interconnectedness" you verified — is it genuine (code calls code)
   or nominal (both files exist)? Identify the three weakest links.

4. What is the single most likely reason a first-time user would give up
   within 30 minutes of installing Metis?

5. What is the single highest-value improvement to recommend?

Report your findings as:
   GENUINE GAPS: [list]
   NOMINAL TESTS (file-exists but not wired): [list]
   TOP RECOMMENDATION: [one sentence]
```

---

## After running this test

Once you have results from all 11 sections:

1. Write a summary to `journal/sessions/test-report-{date}.md`
2. Add any new failures as items to `system/config/feature-backlog.md`
3. Mark this test prompt's date in the filename if you re-run it: `MASTER_TEST_PROMPT-{date}.md`
4. If any persona test fails due to a missing agent: invoke `/hr-talent` with the gap description

---

*End of Master Test Protocol*
