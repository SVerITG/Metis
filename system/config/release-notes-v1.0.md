# Metis v1.0 — Release Notes

**Released:** May 2026
**Repository:** [<your-github-username>/Metis_PH](https://github.com/<your-github-username>/Metis_PH)
**License:** AGPL-3.0 (codebase) · CC-BY-SA 4.0 (course content)

---

## What's in v1.0

### FastAPI + HTMX Dashboard — 9 Tabs

A fully local research dashboard running at `http://127.0.0.1:8080`. No account, no cloud, no JavaScript framework — pure HTMX partials over FastAPI.

| Tab | What it surfaces |
|---|---|
| **Today** | Morning brief · task priorities · focus suggestion · overnight news rail · quick capture (Ctrl+K) |
| **Knowledge** | Semantic PDF search (sqlite-vec + nomic-embed-text-v1.5-Q) · literature cards · domain notes · knowledge graph |
| **Meetings** | Transcript import · live meeting assistant · action item extraction · cross-references |
| **Learning** | Spaced repetition due today · course progress bars · competency map |
| **Work** | Task list with P1–P4 priorities · project cards · VS Code / RStudio / Claude launchers |
| **Thinking** | Quick capture · cross-pollination · brainstorm launcher · open questions |
| **Planner** | Kanban (Someday / Incubating / Active) · PhD focus board · research timeline |
| **Teach** | Course Builder · literature alerts · gap analysis · Q-bank · Quarto rendering |
| **Metis** | Agent run history · self-improvement proposals · agent registry · system health |

---

### 34 Specialist Agents — All Upgraded to Tier-1 Prompts

All agents have been fully rewritten with structured system prompts covering role definition, domain methodology, behavioural contracts, output format, and scope boundaries.

**Core research agents:**

| Agent | What it does |
|---|---|
| Librarian | Literature search, PDF indexing, Zotero/Mendeley sync, PaperQA2 semantic search |
| Epidemiologist | Study design review, surveillance evaluation, Socratic methodology challenge |
| Methods Coach | Statistical methods, regression, multilevel models, sampling, R methodology |
| Writing Partner | Manuscript editing, academic prose, argument flow, structure review |
| PhD Architect | Thesis structure, article alignment, chapter planning, timeline |
| Librarian | Cross-pollination, semantic search, literature graph |

**New in v1.0:**

| Agent | What it does |
|---|---|
| **Critic** | Independently verifies and quality-checks outputs from other agents before the user acts on them |
| **Memory Curator** | Consolidates session history into permanent memory, retrieves past context, memory health check |
| **Release Coordinator** | Manages release preparation: personal data scan, README sync, repo propagation |

**Full agent list:** Background Maker · Builder · Career Coach · Content Harvester · Course Builder · Cybersecurity · Dashboard Engineer · Data Analyst · Data Guardian · Design Auditor · DHIS2 Expert · Edu Expert · Epidemiologist · Frontend Designer Builder · HR Talent · Learning Architect · Learning Coach · Librarian · Meeting Memory · Memory Curator · Methods Coach · Metis (router) · News Aggregator · News Radar · PhD Architect · Presentation Maker · RC Builder · Release Coordinator · Research Architect · Software Engineer · UX Engineer · Visualization Maker · Writing Partner · Critic

---

### MCP Server — 165+ Registered Tools

The Metis MCP server (FastMCP, Python 3.10+) registers 165+ tools across 15 functional modules:

| Module | Tools |
|---|---|
| Memory | `write_reflexion`, `get_episodic_memory`, `search_semantic_memory`, session events |
| Agent pipeline | `run_agent`, `log_agent_run`, `validate_agent_output`, `aggregate_reflexions` |
| Self-improvement | `draft_self_improvement_proposal`, `apply_proposal`, `reject_proposal` |
| Library | `import_pdf`, `search_library`, `sync_zotero`, `sync_mendeley` |
| Knowledge graph | `add_node`, `add_edge`, `get_connections`, `cross_pollinate` |
| News & feeds | `scan_rss_feeds`, `get_news_briefs`, `tag_signals`, `check_freshness` |
| Data tools | `profile_dataset`, `suggest_cleaning`, `clean_dataset`, `compare_profiles` |
| Guardrails | `injection_probe`, `validate_pii`, `check_constitution`, `log_security_event` |
| Projects | `get_projects`, `log_project_event`, `update_project_status` |
| Tasks | `get_tasks`, `create_task`, `complete_task`, `update_priority` |
| Meetings | `ingest_transcript`, `extract_actions`, `search_meetings` |
| Voice | `transcribe_voice` (faster-whisper, fully local) |
| Handoff | `generate_handoff_brief`, `store_handoff`, `retrieve_handoff` |
| Basket | `list_basket`, `read_file`, `promote_basket_item` |
| System | `metis_doctor`, `get_user_profile`, `write_user_config`, `get_agent_registry` |

---

### Windows Installer — Inno Setup, 3 Variants

A no-terminal Windows installer built with Inno Setup and a PyInstaller-packaged `MetisTray.exe` system-tray launcher.

| Variant | Includes | Best for |
|---|---|---|
| **Full** | MCP server + dashboard + RStudio launcher + Statistics course | Everything from day one |
| **Standard** | MCP server + dashboard | Full Metis without course package |
| **Minimal / MCP-only** | MCP server only (Claude Desktop integration, no dashboard) | Lightest footprint |

All variants: configure Claude Desktop automatically, launch the 13-section config wizard on first open, set `METIS_RC_ROOT` environment variable.

Requirements: Windows 10 or 11 · Internet connection · Anthropic API key

---

### Statistics for Epidemiology — 12-Lesson Course

A complete course built with the Course Builder agent and stored in `knowledge/courses/statistics/`. Integrated with the spaced repetition system in the Learning tab.

| Lesson | Topic |
|---|---|
| 01 | Descriptive statistics |
| 02 | Probability basics |
| 03 | Probability distributions |
| 04 | Confidence intervals |
| 05 | Hypothesis testing |
| 06 | Chi-square and t-tests |
| 07 | Correlation and simple regression |
| 08 | Multiple regression |
| 09 | Logistic regression |
| 10 | Survival analysis |
| 11 | Poisson regression |
| 12 | Introduction to multilevel models |

---

### Startup Eval Suite

On every session start, Metis runs a lightweight evaluation:

- **Agent eval suite** — checks that all 34 agents have valid system prompts and skill contracts
- **News freshness check** — verifies RSS feed data is recent; flags stale feeds
- **DB integrity check** — confirms all 46 SQLite tables are accessible and schema is current
- **MCP tool count** — warns if registered tools drop below expected threshold
- **Constitution + red-lines** — confirms security config files are present and unmodified

Results surface in the Today tab and are logged to `session_events`.

---

### Auto-Handoff at 80% Context Turns

The token guardrail system now includes an auto-handoff trigger:

- Turn counter tracked in `session_events` per session
- At 80% of `max_turns` (default: 20 turns → triggers at 16), `generate_handoff_brief()` fires automatically
- Handoff brief is < 3 KB: project context, open threads, last agent output, next suggested action
- Brief stored in SQLite and rendered on the Today tab
- User sees a token pulse widget showing current usage in real time

---

### Security — 5-Layer Architecture

| Layer | Implementation |
|---|---|
| Pre-tool-use hook | `.claude/hooks/pre-tool-use.mjs` — 12 injection patterns, domain allowlist, path restrictions |
| Injection probe | `guardrails.py` — scans all external content (papers, transcripts, web fetches) before agent sees it |
| PII detection | `safety.py` — 14 checks, 4-level classification, hard block on confidential/restricted data |
| Constitution | `system/config/constitution.md` — 12 machine-readable rules applied to every deep/chain run |
| Red lines | `system/config/red-lines.md` — 5 non-overridable rules enforced at code level |

---

### Self-Improvement Loop

1. `write_reflexion()` logs what went well, what could improve, and what was missing after every agent run
2. Weekly: `aggregate_reflexions()` extracts themes (Claude Haiku)
3. `draft_self_improvement_proposal()` writes a proposed behaviour change with rationale
4. Review in the Metis tab — approve, reject, or edit
5. `apply_proposal()` writes the update with a timestamped backup

No agent behaviour changes without user review.

---

## Known Limitations

- **Docker image:** Not yet published. Manual Docker compose works — see `system/install/docker/`. An official image is planned for v1.1.
- **Phase 10 (APScheduler):** Automated daily tasks (07:00 News Radar, 07:30 Librarian scan) are scaffolded but not shipped in v1.0. Use Task Scheduler or `cron` manually in the interim — see `system/config/SETUP.md`.
- **Test suite:** Unit and integration tests exist under `tests/` but coverage is incomplete. Red-line tests are present. Full e2e suite is a v1.1 target.
- **Gemini / OpenAI support:** Experimental. Metis targets Claude Code and Claude Desktop as primary harnesses.
- **Windows installer** has been built but not yet tested on managed corporate machines with restricted PowerShell policies.

---

## Upgrade from Previous Versions

There is no automated migration. If you were running a pre-v1.0 development build:

1. Pull the latest main: `git pull origin main`
2. Re-run the MCP setup: `bash system/mcp-server/setup-mcp.sh`
3. Restart the dashboard: `bash system/app-py/run.sh`
4. The SQLite schema is forward-compatible for all tables added in Phases 0–9b. New columns added in v1.0 are applied automatically on first launch via `db.py` migration checks.

---

## What's Next (v1.1)

- APScheduler automated daily tasks (Phase 10)
- Published Docker image
- Complete e2e test suite (Phase 12)
- Telegram bot for mobile idea capture
- OpenTelemetry observability spans
- Domain packs: Biomedical Sciences · Clinical Sciences
