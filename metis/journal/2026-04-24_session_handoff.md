# Session handoff — 2026-04-24

> **For the next session (after `/clear` or new window).** Read this first to reorient quickly without losing nuance.

## What this session was about

User directive: *"We have in this project a whole implementation plan. Read what it is supposed to do, reflect on the strategy, on the functionality. I want something clean, academic, professional but warm that invites to use. The most important things is that at the end of your session I have a working version with my data, nothing invented (to-do, projects, courses, ...)"*

Follow-up: *"lean harder into the editorial theme, some of the fonts are a bit small, some text overlapping... next to the activity tracker there should be a whole news feed with different categories... quick action cards are not to copy a prompt, they should open the respective programs."*

## Canonical reference documents

| Artefact | Path | What's in it |
|---|---|---|
| **Full visual spec for Claude Design** | `/home/sverschaeve/.claude/plans/nifty-stargazing-sifakis.md` | Part 1 has the complete design language — palette tokens, typography scale, layout ASCII diagram, component specs. **Keep this intact.** |
| **Phase 8.7 milestones** | `metis/system/config/implementation-progress.json` | 15 milestones (11 completed, 4 pending). Authoritative status tracker. |
| **Research findings** | `metis/system/design-docs/2026-04-24_research_findings.md` | PDF-Extract-Kit (SKIP — use Docling) + Agentic OS (5 prioritized recommendations — OTel spans, Letta-style memory tiers, eval harness, scoped browser agent, skills registry). |
| **This handoff** | `metis/journal/2026-04-24_session_handoff.md` | What you're reading now. |

## What's working right now (verified 200 OK)

Server: `http://127.0.0.1:8000`, PID varies (uvicorn with --reload). Static: `/static/styles.css?v=7.1`, `/static/app.js?v=7.1`.

**Today tab (editorial layout matching Metis_Design.png):**
- Dateline strip: `Friday · April 24, 2026 · Week 17` + `Last scan · Nh ago · Scan now`
- Hero: `Good morning, Stef.` (Georgia 3.1rem) + `N threads need you today.` (Georgia italic 2.05rem teal) + 3 ambient stats right-aligned (open threads / tokens packed / gathered today)
- Three-column canvas: focus thread (1.4fr) | activity feed (1fr) | news rail (1.1fr) — collapses responsively
- Focus thread: resumed-yesterday label → project title → next-step → pull-quote from latest idea → continuous scan + [Tune scan]
- Activity feed: unified time-stamped rows (◆ news / ● agent / ◉ meeting / ○ task) clickable
- News rail: category chips with count + age ("HAT · 1 · 1d"), active filter, items clickable → modal
- Quick actions: 6 launcher cards (Capture idea opens modal; Brainstorm/Write/Meeting/Inbox launch Claude Code with prompt; Review chains VS Code + Claude Code)
- Question prompt: italic serif textarea "What are you thinking about?" + teal circle send + mode toggles

**Backend endpoints (all verified 200):**
- `GET /api/partial/today/dateline` `/hero` `/focus-thread` `/activity-feed` `/news-rail?category=X`
- `GET /api/news/brief/{id}` → summary modal HTML
- `GET /api/project/focus` → JSON of highest-priority active project
- `POST /api/project/launch` (project_id, target, prompt) → launches Windows app via cmd.exe bridge. Targets: rstudio | vscode | explorer | claude_desktop | claude_code
- `POST /api/task/{id}/done` and `/delete`

**DB state (real data only, nothing invented):**
- 5 active projects — hat-dashboard (rstudio), hat-clustering (rstudio), multilevel-analysis (vscode), phd-framework (vscode), passive-screening-drc (rstudio)
- 3 of 5 have `external_path` set (hat-dashboard, hat-clustering, multilevel-analysis)
- 30 open tasks
- 1 active course (MLM at 33%, 2/6 modules)
- 25 real Zotero literature records
- 4 real news briefs (AI, HAT, Public Health, Research — all 2026-04-22)

## What's still open (ordered by priority)

1. **Seed `external_path` for 2 projects** (M8.7.12) — need user to confirm Windows paths for `phd-framework` and `passive-screening-drc`.
2. **Verify launchers actually launch** (M8.7.13) — the WSL→cmd.exe bridge is implemented but not verified from a Windows browser session. If it fails, graceful fallback: show "Copy this command" dialog.
3. **Decide chain vs single-choice for "Review code"** (M8.7.14) — currently opens VS Code AND Claude Code (500ms apart). May be too much.
4. **News rail evaluation** (M8.7.15) — current 4 rows is too few to judge the taxonomy. Wait for user to run /news-radar a few times, then revisit.
5. **Phase 8.6 CLI commands still pending** (M8.6.5–10) — `/metis_tasks`, `/metis_phd`, `/metis_literature`, `/metis_capture`, `/metis_inbox`, `/metis_news` — designs exist, implementations don't.
6. **Observability / Phase 5.9** — Metis needs OpenTelemetry gen_ai spans per Agentic OS research recommendation. Replaces the existing Phase 5.9 plan with OTel-native approach.

## Important nuance that isn't in the JSON

**Workflow strategy discussed (three modes):**
1. **Dashboard → external programs** (morning): user opens dashboard → sees what needs attention → clicks a launcher to jump into Claude Code / VS Code / RStudio with context. The dashboard is the *launcher*, not the destination.
2. **External → dashboard** (during work): user operates in Claude Desktop with MCP tools → every tool call writes to metis.sqlite → dashboard polls `check-db-mtime` every 20s → shows reload prompt.
3. **Files → dashboard via scan** (check-in): user edited code in VS Code → clicks `Scan now` on the dateline → dashboard re-fetches all HTMX partials + runs git status on tracked projects.

These three modes should all stay first-class. Future UI work should keep each of them visible.

**Editorial design signature (do not regress):**
- Georgia serif is the voice. Italic is the emotional register.
- Ambient stats sit quietly top-right, not as loud KPI boxes
- No glassmorphism. No backdrop-filter.
- Uppercase caps-labels with 0.16em tracking mark every section.
- Pull-quote with teal left rule for important thoughts
- Launcher cards are flat-transparent in the actions strip (less boxy than elsewhere)

**Keep `metis/.claude/skills/metis-info/skill.md`** up-to-date with CLI commands — it's the power-user reference. `metis-help` is the friendly alternative for Claude Desktop.

## Known issues / things to watch

- **PyInstaller + installer (M5.5.11-13)**: still pending; no urgency.
- **Dark mode**: not started; Priority 8 in DESIGN_BRIEF.
- **Windows Terminal (wt.exe)**: required for "Open in Claude Code" — user should have it installed (comes with Win 11 by default). If missing, graceful fallback needed.
- **Claude Desktop URI (`claude://`)**: may not be registered on user's machine. If the launcher target `claude_desktop` fails, just open Claude Desktop plain.
- **DB has `brief_id`, not `id`** for news_briefs — the news rail route correctly queries `brief_id`. If you extend, use `brief_id` explicitly.

## User's explicit ask to evaluate in next session: automating handoff

> *"include in the instructions of the handoff that afterwards we need to see that we will evaluate if this can be automated (clearing and handing off for token efficiency)"*

**Evaluation topic for next session**: automate the handoff + clear flow for token efficiency. Concretely evaluate:

1. **A `/metis_handoff` auto-trigger** — when the conversation approaches a token threshold (e.g. 80% of 200k), offer to generate the handoff doc and prompt the user to `/clear`.
2. **What gets auto-persisted on clear** — extend `metis/system/mcp-server` with a tool like `persist_session_state(conversation_id, topics, open_questions, files_touched)` that writes a handoff MD without the user asking.
3. **Which things survive clear automatically** — CLAUDE.md, MEMORY.md, plan files, implementation-progress.json, project PLANNING.md files — vs which things get lost (TaskList, ambient context, unstated decisions).
4. **A "resume from handoff" prompt pattern** — a 1-click way for the next session to load the right handoff doc and orient without re-reading everything.
5. **Cost/benefit of Anthropic's native memory** (if/when available in the API) vs this file-based system.
6. **Token budget per session** — establish a target token envelope for typical sessions and automate trimming when approaching it.

This is the fifth recommendation from the Agentic OS research — skills registry + session state persistence — applied to our own workflow.

## Useful files for the next session to read

```
metis/CLAUDE.md                                                  # the canonical operating rules
metis/system/config/implementation-progress.json                 # status of all phases
metis/system/design-docs/2026-04-24_research_findings.md         # PDF + Agentic OS research
/home/sverschaeve/.claude/plans/nifty-stargazing-sifakis.md      # full visual spec
metis/system/app-py/static/styles.css                            # v7.1 — editorial design tokens + layout
metis/system/app-py/templates/today.html                         # editorial structure
metis/system/app-py/routers/today.py                             # all today partial endpoints
metis/system/app-py/routers/work.py                              # launcher + task action endpoints
metis/system/app-py/static/app.js                                # launchPrompt, runDashboardScan, filterNewsCategory
```

## First thing to say when resuming

> Hi. Picking up Phase 8.7. Editorial redesign is live at v7.1 — hero + 3-col canvas + news rail + launcher cards wired. Four open items remain: seed paths for 2 projects, verify Windows launchers work end-to-end, decide if Review-code should chain VS Code + Claude Code, evaluate news rail once more news exists. Plus — you asked me to evaluate whether we can automate this handoff flow for token efficiency. Which of those do you want to tackle first?
